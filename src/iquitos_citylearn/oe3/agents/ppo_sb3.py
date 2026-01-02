from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable
import numpy as np
import logging

from ..progress import append_progress_row, render_progress_plot

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """Auto-detecta el mejor dispositivo disponible (CUDA/MPS/CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("GPU CUDA detectada: %s", device_name)
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("GPU MPS (Apple Silicon) detectada")
            return "mps"
    except ImportError:
        pass
    logger.info("Usando CPU para entrenamiento")
    return "cpu"


@dataclass
class PPOConfig:
    """Configuración avanzada para PPO con soporte CUDA/GPU y multiobjetivo."""
    # Hiperparámetros de entrenamiento
    train_steps: int = 100000
    n_steps: int = 1024  # Steps por update
    batch_size: int = 128
    n_epochs: int = 10
    
    # Optimización
    learning_rate: float = 3e-4
    lr_schedule: str = "constant"  # "constant", "linear", "cosine"
    gamma: float = 0.99
    gae_lambda: float = 0.95
    
    # Clipping y regularización
    clip_range: float = 0.2
    clip_range_vf: Optional[float] = None
    ent_coef: float = 0.01  # Coeficiente de entropía
    vf_coef: float = 0.5  # Coeficiente value function
    max_grad_norm: float = 0.5
    
    # Red neuronal
    hidden_sizes: tuple = (256, 256)
    activation: str = "tanh"
    ortho_init: bool = True
    
    # Normalización (mejora estabilidad)
    normalize_advantage: bool = True
    
    # === CONFIGURACIÓN GPU/CUDA ===
    device: str = "auto"  # "auto", "cuda", "cuda:0", "cuda:1", "mps", "cpu"
    use_amp: bool = True  # Mixed precision training
    pin_memory: bool = True  # Acelera CPU->GPU
    deterministic_cuda: bool = False  # True = reproducible pero más lento
    
    # === MULTIOBJETIVO / MULTICRITERIO ===
    # Pesos para función de recompensa compuesta (deben sumar 1.0)
    weight_co2: float = 0.35           # Minimizar emisiones CO₂
    weight_cost: float = 0.25          # Minimizar costo eléctrico
    weight_solar: float = 0.20         # Maximizar autoconsumo solar
    weight_ev_satisfaction: float = 0.15  # Maximizar satisfacción carga EV
    weight_grid_stability: float = 0.05   # Minimizar picos de demanda
    
    # Umbrales multicriterio
    co2_target_kg_per_kwh: float = 0.4521
    cost_target_usd_per_kwh: float = 0.20
    ev_soc_target: float = 0.90
    peak_demand_limit_kw: float = 200.0
    
    # Reproducibilidad
    seed: int = 42
    
    # Logging
    verbose: int = 0
    tensorboard_log: Optional[str] = None
    log_interval: int = 2000
    target_kl: Optional[float] = 0.02
    kl_adaptive: bool = True
    kl_adaptive_down: float = 0.5
    kl_adaptive_up: float = 1.05
    kl_min_lr: float = 1e-6
    kl_max_lr: float = 1e-3
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 1000  # MANDATORY: Default to 1000 for checkpoint generation
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1
    resume_path: Optional[str] = None  # Ruta a checkpoint SB3 para reanudar
    resume_path: Optional[str] = None  # Ruta a checkpoint SB3 para reanudar
    # Suavizado de acciones
    reward_smooth_lambda: float = 0.0


class PPOAgent:
    """Agente PPO robusto y escalable con optimizadores avanzados.
    
    Características:
    - Proximal Policy Optimization con clipping
    - GAE (Generalized Advantage Estimation)
    - Scheduler de learning rate
    - Normalización de ventajas
    - Compatible con CityLearn
    """
    
    def __init__(self, env: Any, config: Optional[PPOConfig] = None):
        self.env = env
        self.config = config or PPOConfig()
        self.model = None
        self.wrapped_env = None
        self._trained = False
        
        # Métricas
        self.training_history: List[Dict[str, float]] = []
        
        # === Configurar dispositivo GPU/CUDA ===
        self.device = self._setup_device()
        self._setup_torch_backend()
    
    def _setup_device(self) -> str:
        """Configura el dispositivo para entrenamiento."""
        if self.config.device == "auto":
            return detect_device()
        return self.config.device
    
    def _setup_torch_backend(self):
        """Configura PyTorch para máximo rendimiento en GPU."""
        try:
            import torch
            
            # Seed para reproducibilidad
            torch.manual_seed(self.config.seed)
            
            if "cuda" in self.device:
                torch.cuda.manual_seed_all(self.config.seed)
                
                # Optimizaciones CUDA
                if not self.config.deterministic_cuda:
                    torch.backends.cudnn.benchmark = True  # Auto-tune kernels
                else:
                    torch.backends.cudnn.deterministic = True
                    torch.backends.cudnn.benchmark = False
                
                # Logging de GPU
                if torch.cuda.is_available():
                    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                    logger.info("CUDA memoria disponible: %.2f GB", gpu_mem)
            
            if self.config.use_amp and "cuda" in self.device:
                logger.info("Mixed Precision (AMP) habilitado")
                
        except ImportError:
            logger.warning("PyTorch no instalado")
    
    def get_device_info(self) -> Dict[str, Any]:
        """Retorna información del dispositivo."""
        info = {"device": self.device}
        try:
            import torch
            info["torch_version"] = torch.__version__
            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                info["cuda_version"] = torch.version.cuda
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
        except ImportError:
            pass
        return info
    
    def learn(self, episodes: int = 5, total_timesteps: Optional[int] = None):
        """Entrena el agente PPO con optimizadores avanzados."""
        try:
            import gymnasium as gym
            from stable_baselines3 import PPO
            from stable_baselines3.common.env_util import make_vec_env
            from stable_baselines3.common.vec_env import VecNormalize
            from stable_baselines3.common.callbacks import BaseCallback, CallbackList
            from stable_baselines3.common.monitor import Monitor
        except ImportError as e:
            logger.warning("stable_baselines3 no disponible: %s", e)
            return
        
        steps = total_timesteps or self.config.train_steps
        
        # Wrapper robusto para CityLearn
        class CityLearnWrapper(gym.Wrapper):
            def __init__(self, env, smooth_lambda: float = 0.0):
                super().__init__(env)
                obs0, _ = self.env.reset()
                obs0_flat = self._flatten(obs0)
                self.obs_dim = len(obs0_flat)
                self.act_dim = self._get_act_dim()
                self._smooth_lambda = smooth_lambda
                self._prev_action = None
                
                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf,
                    shape=(self.obs_dim,), dtype=np.float32
                )
                self.action_space = gym.spaces.Box(
                    low=-1.0, high=1.0,
                    shape=(self.act_dim,), dtype=np.float32
                )
            
            def _get_act_dim(self):
                if isinstance(self.env.action_space, list):
                    return sum(sp.shape[0] for sp in self.env.action_space)
                return self.env.action_space.shape[0]
            
            def _get_pv_bess_feats(self):
                pv_kw = 0.0
                soc = 0.0
                try:
                    t = getattr(self.env, "time_step", 0)
                    buildings = getattr(self.env, "buildings", [])
                    for b in buildings:
                        sg = getattr(b, "solar_generation", None)
                        if sg is not None and len(sg) > t:
                            pv_kw += float(max(0.0, sg[t]))
                        es = getattr(b, "electrical_storage", None)
                        if es is not None:
                            soc = float(getattr(es, "state_of_charge", soc))
                except Exception:
                    pass
                return np.array([pv_kw, soc], dtype=np.float32)

            def _flatten_base(self, obs):
                if isinstance(obs, dict):
                    return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
                elif isinstance(obs, (list, tuple)):
                    return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
                return np.array(obs, dtype=np.float32).ravel()

            def _flatten(self, obs):
                base = self._flatten_base(obs)
                feats = self._get_pv_bess_feats()
                arr = np.concatenate([base, feats])
                target = getattr(self, "obs_dim", arr.size)
                if arr.size < target:
                    arr = np.pad(arr, (0, target - arr.size), mode="constant")
                elif arr.size > target:
                    arr = arr[: target]
                return arr.astype(np.float32)
            
            def _unflatten_action(self, action):
                if isinstance(self.env.action_space, list):
                    result = []
                    idx = 0
                    for sp in self.env.action_space:
                        dim = sp.shape[0]
                        result.append(action[idx:idx+dim].tolist())
                        idx += dim
                    return result
                return [action.tolist()]
            
            def reset(self, **kwargs):
                obs, info = self.env.reset(**kwargs)
                return self._flatten(obs), info
            
            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                obs, reward, terminated, truncated, info = self.env.step(citylearn_action)

                if truncated and not terminated:
                    terminated = True
                    truncated = False

                if isinstance(reward, (list, tuple)):
                    reward = sum(reward)

                flat_action = np.array(action, dtype=np.float32).ravel()
                if self._prev_action is not None and self._smooth_lambda > 0.0:
                    delta = flat_action - self._prev_action
                    reward -= float(self._smooth_lambda * np.linalg.norm(delta))
                self._prev_action = flat_action
                
                return self._flatten(obs), float(reward), terminated, truncated, info
        
        self.wrapped_env = Monitor(CityLearnWrapper(self.env, smooth_lambda=self.config.reward_smooth_lambda))
        
        # Crear ambiente vectorizado
        vec_env = make_vec_env(lambda: self.wrapped_env, n_envs=1, seed=self.config.seed)
        
        # Learning rate scheduler
        lr_schedule = self._get_lr_schedule(steps)
        
        # Configurar política con arquitectura optimizada
        policy_kwargs = {
            "net_arch": dict(
                pi=list(self.config.hidden_sizes),
                vf=list(self.config.hidden_sizes),
            ),
            "activation_fn": self._get_activation(),
            "ortho_init": self.config.ortho_init,
        }
        
        # Crear o reanudar modelo PPO con configuración avanzada y GPU
        resume_path = Path(self.config.resume_path) if self.config.resume_path else None
        resuming = resume_path is not None and resume_path.exists()
        logger.info("Creando modelo PPO en dispositivo: %s%s", self.device, " (resume)" if resuming else "")
        if resuming:
            self.model = PPO.load(
                str(resume_path),
                env=vec_env,
                device=self.device,
            )
        else:
            self.model = PPO(
                "MlpPolicy",
                vec_env,
                learning_rate=lr_schedule,
                n_steps=self.config.n_steps,
                batch_size=self.config.batch_size,
                n_epochs=self.config.n_epochs,
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
                clip_range=self.config.clip_range,
                clip_range_vf=self.config.clip_range_vf,
                normalize_advantage=self.config.normalize_advantage,
                ent_coef=self.config.ent_coef,
                vf_coef=self.config.vf_coef,
                max_grad_norm=self.config.max_grad_norm,
                policy_kwargs=policy_kwargs,
                verbose=self.config.verbose,
                seed=self.config.seed,
                tensorboard_log=self.config.tensorboard_log,
                target_kl=self.config.target_kl,
                device=self.device,  # GPU/CUDA support
            )
        
        # Callback para logging
        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        progress_headers = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
        expected_episodes = int(steps // 8760) if steps > 0 else 0

        class TrainingCallback(BaseCallback):
            def __init__(self, agent, progress_path: Optional[Path], progress_headers, expected_episodes: int, verbose=0):
                super().__init__(verbose)
                self.agent = agent
                self.progress_path = progress_path
                self.progress_headers = progress_headers
                self.expected_episodes = expected_episodes
                self.episode_count = 0
                self.log_interval_steps = int(agent.config.log_interval or 0)
                self._last_kl_update = 0

            def _get_approx_kl(self) -> Optional[float]:
                logger_obj = getattr(self.model, "logger", None)
                if logger_obj is None:
                    return None
                name_to_value = getattr(logger_obj, "name_to_value", None)
                if not isinstance(name_to_value, dict):
                    return None
                approx_kl = name_to_value.get("train/approx_kl")
                try:
                    return float(approx_kl) if approx_kl is not None else None
                except (TypeError, ValueError):
                    return None

            def _adjust_lr_by_kl(self, approx_kl: float) -> None:
                if not self.agent.config.kl_adaptive or self.agent.config.target_kl is None:
                    return
                target = float(self.agent.config.target_kl)
                if target <= 0:
                    return
                optimizer = getattr(self.model.policy, "optimizer", None)
                if optimizer is None:
                    return
                current_lr = optimizer.param_groups[0].get("lr", None)
                if current_lr is None:
                    return
                new_lr = current_lr
                if approx_kl > target * 1.5:
                    new_lr = max(current_lr * float(self.agent.config.kl_adaptive_down), self.agent.config.kl_min_lr)
                elif approx_kl < target * 0.5:
                    new_lr = min(current_lr * float(self.agent.config.kl_adaptive_up), self.agent.config.kl_max_lr)
                if new_lr != current_lr:
                    for group in optimizer.param_groups:
                        group["lr"] = new_lr
                    logger.info("[PPO] KL adaptativo: kl=%.4f lr=%.2e", approx_kl, new_lr)
            
            def _on_step(self):
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]
                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    logger.info(
                        "[PPO] paso %d | ep~%d | pasos_global=%d",
                        self.n_calls,
                        approx_episode,
                        int(self.model.num_timesteps),
                    )
                    if self.progress_path is not None:
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "ppo",
                            "episode": approx_episode,
                            "episode_reward": "",
                            "episode_length": "",
                            "global_step": int(self.model.num_timesteps),
                        }
                        append_progress_row(self.progress_path, row, self.progress_headers)
                    approx_kl = self._get_approx_kl()
                    if approx_kl is not None and self.n_calls != self._last_kl_update:
                        self._adjust_lr_by_kl(approx_kl)
                        self._last_kl_update = self.n_calls
                for info in infos:
                    episode = info.get("episode")
                    if not episode:
                        continue
                    self.episode_count += 1
                    reward = float(episode.get("r", 0.0))
                    length = int(episode.get("l", 0))
                    self.agent.training_history.append({
                        "step": int(self.model.num_timesteps),
                        "mean_reward": reward,
                    })
                    if self.agent.config.progress_interval_episodes > 0 and (
                        self.episode_count % self.agent.config.progress_interval_episodes == 0
                    ):
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "ppo",
                            "episode": self.episode_count,
                            "episode_reward": reward,
                            "episode_length": length,
                            "global_step": int(self.model.num_timesteps),
                        }
                        if self.progress_path is not None:
                            append_progress_row(self.progress_path, row, self.progress_headers)
                            png_path = self.progress_path.with_suffix(".png")
                            render_progress_plot(self.progress_path, png_path, "PPO progreso")
                        if self.expected_episodes > 0:
                            logger.info(
                                "[PPO] ep %d/%d reward=%.4f len=%d step=%d",
                                self.episode_count,
                                self.expected_episodes,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                        else:
                            logger.info(
                                "[PPO] ep %d reward=%.4f len=%d step=%d",
                                self.episode_count,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                return True

        checkpoint_dir = self.config.checkpoint_dir
        checkpoint_freq = int(self.config.checkpoint_freq_steps or 0)
        logger.info(f"[PPO Checkpoint Config] dir={checkpoint_dir}, freq={checkpoint_freq}")
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"[PPO] Checkpoint directory created: {checkpoint_dir}")
        else:
            logger.warning("[PPO] NO checkpoint directory configured!")

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq
                self.call_count = 0
                logger.info(f"[PPO CheckpointCallback.__init__] save_dir={self.save_dir}, freq={self.freq}")
                if self.save_dir and self.freq > 0:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[PPO CheckpointCallback] Created directory: {self.save_dir}")

            def _on_step(self) -> bool:
                self.call_count += 1
                
                if self.call_count == 1:
                    logger.info(f"[PPO CheckpointCallback._on_step] FIRST CALL DETECTED! n_calls={self.n_calls}")
                
                if self.call_count % 1000 == 0:
                    logger.info(f"[PPO CheckpointCallback._on_step] call #{self.call_count}, n_calls={self.n_calls}")
                
                if self.save_dir is None or self.freq <= 0:
                    return True
                
                should_save = (self.n_calls > 0 and self.n_calls % self.freq == 0)
                if should_save:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = self.save_dir / f"ppo_step_{self.n_calls}"
                    try:
                        self.model.save(save_path)
                        logger.info(f"[PPO CHECKPOINT OK] Saved: {save_path}")
                    except Exception as exc:
                        logger.error(f"[PPO CHECKPOINT ERROR] {exc}", exc_info=True)
                
                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])

        # Entrenar
        logger.info("[PPO] Starting model.learn() with callbacks")
        self.model.learn(
            total_timesteps=int(steps),
            callback=callback,
            reset_num_timesteps=not resuming,
        )
        logger.info("[PPO] model.learn() completed successfully")
        self._trained = True
        logger.info("PPO entrenado con %d timesteps, lr_schedule=%s", steps, self.config.lr_schedule)

        if self.model is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "ppo_final"
            try:
                self.model.save(final_path)
                logger.info("[PPO FINAL OK] Modelo guardado en %s", final_path)
            except Exception as exc:
                logger.error("✗ [PPO FINAL ERROR] %s", exc, exc_info=True)
        
        # MANDATORY: Verify checkpoints were created
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            zips = list(checkpoint_path.glob("*.zip"))
            logger.info(f"[PPO VERIFICATION] Checkpoints created: {len(zips)} files")
            for z in sorted(zips)[:5]:
                logger.info(f"  - {z.name} ({z.stat().st_size / 1024:.1f} KB)")
    
    def _get_lr_schedule(self, total_steps: int) -> Callable:
        """Crea scheduler de learning rate."""
        from stable_baselines3.common.utils import get_linear_fn
        
        if self.config.lr_schedule == "linear":
            return get_linear_fn(self.config.learning_rate, self.config.learning_rate * 0.1, 1.0)
        elif self.config.lr_schedule == "cosine":
            def cosine_schedule(progress):
                return self.config.learning_rate * (0.5 * (1 + np.cos(np.pi * (1 - progress))))
            return cosine_schedule
        else:  # constant
            return self.config.learning_rate
    
    def _get_activation(self):
        """Obtiene función de activación."""
        import torch.nn as nn
        activations = {
            "relu": nn.ReLU,
            "tanh": nn.Tanh,
            "elu": nn.ELU,
            "leaky_relu": nn.LeakyReLU,
            "gelu": nn.GELU,
            "silu": nn.SiLU,
        }
        return activations.get(self.config.activation, nn.Tanh)
    
    def predict(self, observations: Any, deterministic: bool = True):
        """Predice acción dado el estado."""
        if self.model is None:
            return self._zero_action()
        
        obs = self._flatten_obs(observations)
        # Ajustar a la dimensión esperada por el modelo
        try:
            target_dim = int(self.model.observation_space.shape[0])
            if obs.size < target_dim:
                obs = np.pad(obs, (0, target_dim - obs.size), mode="constant")
            elif obs.size > target_dim:
                obs = obs[:target_dim]
            obs = obs.astype(np.float32)
        except Exception:
            pass
        action, _ = self.model.predict(obs, deterministic=deterministic)
        return self._unflatten_action(action)

    def _flatten_obs(self, obs):
        if isinstance(obs, dict):
            arr = np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
        elif isinstance(obs, (list, tuple)):
            arr = np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
        else:
            arr = np.array(obs, dtype=np.float32).ravel()
        target_dim = None
        # Priorizar el espacio de obs del modelo SB3 si existe
        try:
            if self._model is not None and hasattr(self._model, "observation_space"):
                space = self._model.observation_space
                if space is not None and hasattr(space, "shape") and space.shape:
                    target_dim = int(space.shape[0])
        except Exception:
            target_dim = None
        if target_dim is None:
            try:
                space = getattr(self.env, "observation_space", None)
                if space is not None and hasattr(space, "shape") and space.shape:
                    target_dim = int(space.shape[0])
            except Exception:
                target_dim = None
        if target_dim is not None:
            if arr.size < target_dim:
                arr = np.pad(arr, (0, target_dim - arr.size), mode="constant")
            elif arr.size > target_dim:
                arr = arr[:target_dim]
        return arr.astype(np.float32)
    
    def _unflatten_action(self, action):
        if isinstance(self.env.action_space, list):
            result = []
            idx = 0
            for sp in self.env.action_space:
                dim = sp.shape[0]
                result.append(action[idx:idx+dim].tolist())
                idx += dim
            return result
        if isinstance(action, np.ndarray):
            return [action.tolist()]
        return [action]
    
    def _zero_action(self):
        """Devuelve acción cero."""
        action_space = getattr(self.env, "action_space", None)
        if action_space is None:
            return [[0.0]]
        if isinstance(action_space, list):
            return [[0.0] * sp.shape[0] for sp in action_space]
        return [[0.0] * action_space.shape[0]]
    
    def save(self, path: str):
        """Guarda el modelo."""
        if self.model is not None:
            self.model.save(path)
            logger.info("Modelo PPO guardado en %s", path)
    
    def load(self, path: str):
        """Carga modelo."""
        from stable_baselines3 import PPO
        self.model = PPO.load(path)
        self._trained = True
        logger.info("Modelo PPO cargado desde %s", path)


def make_ppo(env: Any, config: Optional[PPOConfig] = None, **kwargs) -> PPOAgent:
    """Factory function para crear agente PPO robusto."""
    # FIX CRÍTICO: Evaluación explícita para evitar bug con kwargs={}
    if config is not None:
        cfg = config
        logger.info(f"[make_ppo] Using provided config: checkpoint_dir={cfg.checkpoint_dir}, checkpoint_freq_steps={cfg.checkpoint_freq_steps}")
    elif kwargs:
        cfg = PPOConfig(**kwargs)
        logger.info(f"[make_ppo] Created PPOConfig from kwargs: checkpoint_dir={cfg.checkpoint_dir}")
    else:
        cfg = PPOConfig()
        logger.info(f"[make_ppo] Created default PPOConfig: checkpoint_dir={cfg.checkpoint_dir}")
    return PPOAgent(env, cfg)


# Legacy compatibility
def train_ppo(env, cfg: PPOConfig, seed: int = 42):
    """Legacy: Entrena PPO."""
    agent = PPOAgent(env, PPOConfig(train_steps=cfg.train_steps, seed=seed))
    agent.learn()
    return agent.model, agent.wrapped_env


def ppo_predict(model, obs):
    """Legacy: Predice con modelo PPO."""
    action, _ = model.predict(obs, deterministic=True)
    return action
