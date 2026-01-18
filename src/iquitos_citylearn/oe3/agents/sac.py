from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List
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


def _patch_citylearn_sac_update() -> None:
    try:
        import torch
        from citylearn.agents import sac as citylearn_sac  # type: ignore
    except Exception:
        return

    if getattr(citylearn_sac.SAC.update, "_iquitos_tensor_patch", False):
        return

    def _update(self, observations, actions, reward, next_observations, terminated, truncated):
        for i, (o, a, r, n) in enumerate(zip(observations, actions, reward, next_observations)):
            o = self.get_encoded_observations(i, o)
            n = self.get_encoded_observations(i, n)

            if self.normalized[i]:
                o = self.get_normalized_observations(i, o)
                n = self.get_normalized_observations(i, n)
                r = self.get_normalized_reward(i, r)

            self.replay_buffer[i].push(o, a, r, n, terminated)

            if self.time_step >= self.standardize_start_time_step and self.batch_size <= len(self.replay_buffer[i]):
                if not self.normalized[i]:
                    X = np.array([j[0] for j in self.replay_buffer[i].buffer], dtype=float)
                    self.norm_mean[i] = np.nanmean(X, axis=0)
                    self.norm_std[i] = np.nanstd(X, axis=0) + 1e-5
                    R = np.array([j[2] for j in self.replay_buffer[i].buffer], dtype=float)
                    self.r_norm_mean[i] = np.nanmean(R, dtype=float)
                    self.r_norm_std[i] = np.nanstd(R, dtype=float) / self.reward_scaling + 1e-5

                    self.replay_buffer[i].buffer = [(
                        np.hstack(self.get_normalized_observations(i, o).reshape(1, -1)[0]),
                        a,
                        self.get_normalized_reward(i, r),
                        np.hstack(self.get_normalized_observations(i, n).reshape(1, -1)[0]),
                        d
                    ) for o, a, r, n, d in self.replay_buffer[i].buffer]
                    self.normalized[i] = True

                for _ in range(self.update_per_time_step):
                    o, a, r, n, d = self.replay_buffer[i].sample(self.batch_size)
                    device = self.device
                    o = torch.as_tensor(o, dtype=torch.float32, device=device)
                    n = torch.as_tensor(n, dtype=torch.float32, device=device)
                    a = torch.as_tensor(a, dtype=torch.float32, device=device)
                    r = torch.as_tensor(r, dtype=torch.float32, device=device).unsqueeze(1)
                    d = torch.as_tensor(d, dtype=torch.float32, device=device).unsqueeze(1)

                    with torch.no_grad():
                        new_next_actions, new_log_pi, _ = self.policy_net[i].sample(n)
                        target_q_values = torch.min(
                            self.target_soft_q_net1[i](n, new_next_actions),
                            self.target_soft_q_net2[i](n, new_next_actions),
                        ) - self.alpha * new_log_pi
                        q_target = r + (1 - d) * self.discount * target_q_values

                    q1_pred = self.soft_q_net1[i](o, a)
                    q2_pred = self.soft_q_net2[i](o, a)
                    q1_loss = self.soft_q_criterion(q1_pred, q_target)
                    q2_loss = self.soft_q_criterion(q2_pred, q_target)
                    self.soft_q_optimizer1[i].zero_grad()
                    q1_loss.backward()
                    self.soft_q_optimizer1[i].step()
                    self.soft_q_optimizer2[i].zero_grad()
                    q2_loss.backward()
                    self.soft_q_optimizer2[i].step()

                    new_actions, log_pi, _ = self.policy_net[i].sample(o)
                    q_new_actions = torch.min(
                        self.soft_q_net1[i](o, new_actions),
                        self.soft_q_net2[i](o, new_actions)
                    )
                    policy_loss = (self.alpha * log_pi - q_new_actions).mean()
                    self.policy_optimizer[i].zero_grad()
                    policy_loss.backward()
                    self.policy_optimizer[i].step()

                    for target_param, param in zip(self.target_soft_q_net1[i].parameters(), self.soft_q_net1[i].parameters()):
                        target_param.data.copy_(target_param.data * (1.0 - self.tau) + param.data * self.tau)

                    for target_param, param in zip(self.target_soft_q_net2[i].parameters(), self.soft_q_net2[i].parameters()):
                        target_param.data.copy_(target_param.data * (1.0 - self.tau) + param.data * self.tau)

    _update._iquitos_tensor_patch = True
    citylearn_sac.SAC.update = _update


@dataclass
class SACConfig:
    """Configuración avanzada para SAC con soporte CUDA/GPU y multiobjetivo.
    
    Nota: episodes=50 es el mínimo recomendado para problemas de alta
    dimensionalidad como CityLearn con ~900 obs dims × 126 action dims.
    Para convergencia óptima, usar 100+ episodios.
    """
    # Hiperparámetros de entrenamiento
    episodes: int = 50  # 50 mínimo para alta dimensionalidad (8760 pasos/ep)
    batch_size: int = 512
    buffer_size: int = 100000
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005
    
    # Entropía (auto-ajuste)
    ent_coef: str = "auto"  # "auto" para ajuste automático
    target_entropy: Optional[float] = -126.0  # -dim(action) es el estándar para SAC
    
    # Red neuronal
    hidden_sizes: tuple = (256, 256)
    activation: str = "relu"
    
    # Escalabilidad
    n_steps: int = 1
    gradient_steps: int = 1
    
    # === CONFIGURACIÓN GPU/CUDA ===
    device: str = "auto"  # "auto", "cuda", "cuda:0", "cuda:1", "mps", "cpu"
    use_amp: bool = True  # Mixed precision (Automatic Mixed Precision)
    pin_memory: bool = True  # Acelera transferencia CPU->GPU
    num_workers: int = 0  # DataLoader workers (0 para CityLearn)
    
    # === MULTIOBJETIVO / MULTICRITERIO ===
    # Pesos para función de recompensa compuesta (deben sumar 1.0)
    weight_co2: float = 0.50           # Minimizar emisiones CO₂
    weight_cost: float = 0.15          # Minimizar costo eléctrico
    weight_solar: float = 0.20         # Maximizar autoconsumo solar
    weight_ev_satisfaction: float = 0.10  # Maximizar satisfacción carga EV
    weight_grid_stability: float = 0.05   # Minimizar picos de demanda
    
    # Umbrales multicriterio
    co2_target_kg_per_kwh: float = 0.4521  # Factor emisión Iquitos
    cost_target_usd_per_kwh: float = 0.20  # Tarifa objetivo
    ev_soc_target: float = 0.90          # SOC objetivo EVs al partir
    peak_demand_limit_kw: float = 200.0  # Límite demanda pico
    
    # Reproducibilidad
    seed: int = 42
    deterministic_cuda: bool = False  # True = reproducible pero más lento
    
    # Callbacks y logging
    verbose: int = 0
    log_interval: int = 500
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 1000  # MANDATORY: Default to 1000 for checkpoint generation
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1
    prefer_citylearn: bool = False
    resume_path: Optional[str] = None  # Ruta a checkpoint SB3 para reanudar entrenamiento
    # Suavizado de acciones (penaliza cambios bruscos)
    reward_smooth_lambda: float = 0.0
    # === NORMALIZACIÓN (crítico para estabilidad) ===
    normalize_observations: bool = True  # Normalizar obs a media=0, std=1
    normalize_rewards: bool = True       # Escalar rewards a [-1, 1]
    reward_scale: float = 0.01           # Factor de escala para rewards (reduce magnitud)
    clip_obs: float = 10.0               # Clipear obs normalizadas a [-clip, clip]


class SACAgent:
    """Agente SAC robusto y escalable con optimizadores avanzados.
    
    Características:
    - Soft Actor-Critic con ajuste automático de entropía
    - Replay buffer eficiente
    - Redes duales Q para estabilidad
    - Compatible con CityLearn centralizado/descentralizado
    """
    
    def __init__(self, env: Any, config: Optional[SACConfig] = None):
        logger.info(f"[SACAgent.__init__] ENTRY: config type={type(config)}, config={config}")
        logger.info(f"[SACAgent.__init__] ENTRY: config.checkpoint_dir={config.checkpoint_dir if config else 'None'}")
        self.env = env
        self.config = config or SACConfig()
        logger.info(f"[SACAgent.__init__] AFTER ASSIGNMENT: self.config.checkpoint_dir={self.config.checkpoint_dir}, checkpoint_freq_steps={self.config.checkpoint_freq_steps}")
        self._citylearn_sac = None
        self._sb3_sac = None
        self._trained = False
        self._use_sb3 = False
        
        # Métricas de entrenamiento
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
        """Configura PyTorch para máximo rendimiento."""
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
                logger.info("Mixed Precision (AMP) habilitado para entrenamiento acelerado")
                
        except ImportError:
            logger.warning("PyTorch no instalado, usando configuración por defecto")
    
    def get_device_info(self) -> Dict[str, Any]:
        """Retorna información detallada del dispositivo."""
        info = {"device": self.device, "backend": "unknown"}
        try:
            import torch
            info["torch_version"] = torch.__version__
            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                info["cuda_version"] = torch.version.cuda
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
                info["gpu_count"] = torch.cuda.device_count()
        except ImportError:
            pass
        return info
    
    def learn(self, episodes: Optional[int] = None, total_timesteps: Optional[int] = None):
        """Entrena el agente SAC con el mejor backend disponible."""
        logger.info("Iniciando entrenamiento SAC en dispositivo: %s", self.device)
        eps = episodes or self.config.episodes
        
        # Intentar CityLearn SAC solo si está habilitado explícitamente
        if self.config.prefer_citylearn:
            try:
                self._train_citylearn_sac(eps)
                return
            except Exception as e:
                logger.exception("CityLearn SAC no disponible (%s), usando SB3...", e)
        
        # Fallback a Stable-Baselines3 SAC
        try:
            steps = total_timesteps or (eps * 8760)  # 1 año = 8760 horas
            self._train_sb3_sac(steps)
        except Exception as e:
            logger.exception("SB3 SAC falló (%s). Agente sin entrenar.", e)
    
    def _train_citylearn_sac(self, episodes: int):
        """Entrena usando CityLearn's native SAC con progress tracking."""
        from citylearn.agents.sac import SAC  # type: ignore
        try:
            import gymnasium as gym
        except ImportError:
            gym = None
        import time

        # CityLearn's Agent.learn ignores `truncated`, so ensure truncation ends episodes.
        train_env = self.env
        if gym is not None:
            class _TerminateOnTruncate(gym.Wrapper):
                def __getattr__(self, name: str):
                    return getattr(self.env, name)

                def step(self, action):
                    obs, reward, terminated, truncated, info = self.env.step(action)
                    if truncated and not terminated:
                        terminated = True
                        truncated = False
                    return obs, reward, terminated, truncated, info

            train_env = _TerminateOnTruncate(self.env)

        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        progress_headers = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
        progress_interval_steps = int(self.config.log_interval or 0)
        progress_interval_episodes = int(self.config.progress_interval_episodes or 0)

        if gym is not None:
            class _ProgressWrapper(gym.Wrapper):
                def __init__(
                    self,
                    env,
                    total_episodes: int,
                    progress_interval_steps: int,
                    progress_interval_episodes: int,
                    progress_path: Optional[Path],
                    progress_headers,
                ):
                    super().__init__(env)
                    self.total_episodes = total_episodes
                    self.progress_interval_steps = progress_interval_steps
                    self.progress_interval_episodes = progress_interval_episodes
                    self.progress_path = progress_path
                    self.progress_headers = progress_headers
                    self.episode = 0
                    self.episode_steps = 0
                    self.episode_reward = 0.0
                    self.global_steps = 0

                def reset(self, **kwargs):
                    # Detener si ya alcanzó el límite de episodios
                    if self.episode >= self.total_episodes:
                        raise StopIteration(f"Reached episode limit: {self.total_episodes}")
                    
                    obs, info = self.env.reset(**kwargs)
                    self.episode += 1
                    self.episode_steps = 0
                    self.episode_reward = 0.0
                    logger.info("[SAC] ep %d/%d iniciado", self.episode, self.total_episodes)
                    return obs, info

                def __getattr__(self, name: str):
                    return getattr(self.env, name)

                def step(self, action):
                    obs, reward, terminated, truncated, info = self.env.step(action)
                    if isinstance(reward, (list, tuple)):
                        reward_val = float(sum(reward))
                    else:
                        reward_val = float(reward)
                    self.episode_reward += reward_val
                    self.episode_steps += 1
                    self.global_steps += 1

                    if self.progress_interval_steps > 0 and self.episode_steps % self.progress_interval_steps == 0:
                        logger.info(
                            "[SAC] ep %d paso %d | pasos_global=%d",
                            self.episode,
                            self.episode_steps,
                            self.global_steps,
                        )

                    if terminated or truncated:
                        if self.progress_interval_episodes > 0 and (
                            self.episode % self.progress_interval_episodes == 0
                        ):
                            row = {
                                "timestamp": datetime.utcnow().isoformat(),
                                "agent": "sac",
                                "episode": self.episode,
                                "episode_reward": self.episode_reward,
                                "episode_length": self.episode_steps,
                                "global_step": self.global_steps,
                            }
                            if self.progress_path is not None:
                                append_progress_row(self.progress_path, row, self.progress_headers)
                                png_path = self.progress_path.with_suffix(".png")
                                render_progress_plot(self.progress_path, png_path, "SAC progreso")
                        logger.info(
                            "[SAC] ep %d/%d terminado reward=%.4f pasos=%d",
                            self.episode,
                            self.total_episodes,
                            self.episode_reward,
                            self.episode_steps,
                        )

                    return obs, reward, terminated, truncated, info

            train_env = _ProgressWrapper(
                train_env,
                episodes,
                progress_interval_steps,
                progress_interval_episodes,
                progress_path,
                progress_headers,
            )

        _patch_citylearn_sac_update()
        
        self._citylearn_sac = SAC(train_env)
        
        # Configurar hiperparámetros si es posible
        if hasattr(self._citylearn_sac, 'batch_size'):
            self._citylearn_sac.batch_size = self.config.batch_size
        if hasattr(self._citylearn_sac, 'lr'):
            self._citylearn_sac.lr = self.config.learning_rate
        if hasattr(self._citylearn_sac, 'gamma'):
            self._citylearn_sac.gamma = self.config.gamma
        if hasattr(self._citylearn_sac, 'tau'):
            self._citylearn_sac.tau = self.config.tau

        # Entrenar con logging de progreso
        logger.info("=" * 50)
        logger.info("ENTRENAMIENTO SAC - %d episodios (8760 pasos/episodio)", episodes)
        logger.info("Dispositivo: %s | Batch: %d | LR: %.2e",
                    self.device, self.config.batch_size, self.config.learning_rate)
        logger.info("=" * 50)

        start_time = time.time()
        try:
            # CityLearn SAC entrena internamente
            self._citylearn_sac.learn(episodes=episodes)
        except TypeError:
            self._citylearn_sac.learn(episodes)
        
        elapsed = time.time() - start_time
        logger.info("=" * 50)
        logger.info("SAC entrenado en %.1f segundos (%.1f min)", elapsed, elapsed / 60)
        logger.info("=" * 50)
        
        self._trained = True
        self._use_sb3 = False
    
    def _train_sb3_sac(self, total_timesteps: int):
        """Entrena usando Stable-Baselines3 SAC con optimizadores avanzados."""
        # DIAGNOSTIC: Write to file to confirm method execution
        with open("sac_training_test.txt", "w") as f:
            f.write(f"_train_sb3_sac called with total_timesteps={total_timesteps}\n")
            f.write(f"checkpoint_dir={self.config.checkpoint_dir}\n")
            f.write(f"checkpoint_freq_steps={self.config.checkpoint_freq_steps}\n")
        
        logger.info("_train_sb3_sac: Iniciando entrenamiento SB3 con %d timesteps", total_timesteps)
        import gymnasium as gym
        from stable_baselines3 import SAC
        from stable_baselines3.common.callbacks import BaseCallback, CallbackList
        from stable_baselines3.common.monitor import Monitor
        
        # Wrapper para compatibilidad
        class CityLearnWrapper(gym.Wrapper):
            def __init__(self, env, smooth_lambda: float = 0.0, 
                         normalize_obs: bool = True, normalize_rewards: bool = True,
                         reward_scale: float = 0.01, clip_obs: float = 10.0):
                super().__init__(env)
                # calcular obs dim a partir del primer estado ya aplanado
                obs0, _ = self.env.reset()
                obs0_flat = self._flatten_base(obs0)
                feats = self._get_pv_bess_feats()
                self.obs_dim = len(obs0_flat) + len(feats)
                self.act_dim = self._get_act_dim()
                self._smooth_lambda = smooth_lambda
                self._prev_action = None
                
                # Normalización
                self._normalize_obs = normalize_obs
                self._normalize_rewards = normalize_rewards
                self._reward_scale = reward_scale  # 0.01 de config
                self._clip_obs = clip_obs
                
                # PRE-ESCALADO para observaciones (kW/kWh son valores grandes)
                # PV: 4162 kWp, BESS: 2000 kWh, Chargers: 272 kW
                self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32)
                # Dividir por 1000 para llevar a rango ~1-5
                self._obs_prescale[:] = 0.001
                
                # Running stats para normalización (media móvil exponencial)
                self._obs_mean = np.zeros(self.obs_dim, dtype=np.float64)
                self._obs_var = np.ones(self.obs_dim, dtype=np.float64)
                self._obs_count = 1e-4  # Evitar división por cero
                self._reward_mean = 0.0
                self._reward_var = 1.0
                self._reward_count = 1e-4
                
                # Redefinir espacios
                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf, 
                    shape=(self.obs_dim,), dtype=np.float32
                )
                self.action_space = gym.spaces.Box(
                    low=-1.0, high=1.0,
                    shape=(self.act_dim,), dtype=np.float32
                )
            
            def _update_obs_stats(self, obs: np.ndarray):
                """Actualiza estadísticas de observación con Welford's algorithm."""
                batch_mean = obs
                batch_var = np.zeros_like(obs)
                batch_count = 1
                
                delta = batch_mean - self._obs_mean
                tot_count = self._obs_count + batch_count
                
                self._obs_mean = self._obs_mean + delta * batch_count / tot_count
                m_a = self._obs_var * self._obs_count
                m_b = batch_var * batch_count
                M2 = m_a + m_b + np.square(delta) * self._obs_count * batch_count / tot_count
                self._obs_var = M2 / tot_count
                self._obs_count = tot_count
            
            def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
                """Normaliza observación: pre-escala + running stats + clip."""
                if not self._normalize_obs:
                    return obs
                # Paso 1: Pre-escalar por constantes fijas (kW/kWh → ~1.0)
                prescaled = obs * self._obs_prescale
                # Paso 2: Aplicar running stats
                self._update_obs_stats(prescaled)
                normalized = (prescaled - self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
                # Paso 3: Clip agresivo
                return np.clip(normalized, -self._clip_obs, self._clip_obs).astype(np.float32)
            
            def _update_reward_stats(self, reward: float):
                """Actualiza estadísticas de recompensa con Welford's algorithm."""
                delta = reward - self._reward_mean
                self._reward_count += 1
                self._reward_mean += delta / self._reward_count
                delta2 = reward - self._reward_mean
                self._reward_var += (delta * delta2 - self._reward_var) / self._reward_count
            
            def _normalize_reward(self, reward: float) -> float:
                """Escala reward simple sin running stats (evita divergencia std→0)."""
                if not self._normalize_rewards:
                    return reward
                # Escala simple: reward * 0.01 + clip
                scaled = reward * self._reward_scale
                return float(np.clip(scaled, -10.0, 10.0))
            
            def _flatten_base(self, obs):
                if isinstance(obs, dict):
                    return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
                elif isinstance(obs, (list, tuple)):
                    return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
                return np.array(obs, dtype=np.float32).ravel()

            def _get_act_dim(self):
                if isinstance(self.env.action_space, list):
                    return sum(sp.shape[0] for sp in self.env.action_space)
                return self.env.action_space.shape[0]
            
            def _get_pv_bess_feats(self):
                """Deriva PV disponible y SOC BESS para enriquecer obs."""
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

            def _flatten(self, obs):
                base = self._flatten_base(obs)
                feats = self._get_pv_bess_feats()
                arr = np.concatenate([base, feats])
                target = getattr(self, "obs_dim", arr.size)
                if arr.size < target:
                    arr = np.pad(arr, (0, target - arr.size), mode="constant")
                elif arr.size > target:
                    arr = arr[: target]
                # Aplicar normalización
                return self._normalize_observation(arr.astype(np.float32))
            
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
                # Reset prev_action and prev_obs
                self._prev_action = None
                self._prev_obs = obs
                return self._flatten(obs), info
            
            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                try:
                    obs, reward, terminated, truncated, info = self.env.step(citylearn_action)
                except KeyboardInterrupt:
                    # CityLearn's simulate_unconnected_ev_soc() has boundary access bug
                    # Catch and return zero reward, continue episode
                    obs = self._prev_obs if hasattr(self, "_prev_obs") else self._get_obs()
                    reward = 0.0
                    terminated, truncated, info = False, False, {}

                if truncated and not terminated:
                    terminated = True
                    truncated = False

                # Asegurar reward escalar
                if isinstance(reward, (list, tuple)):
                    reward = sum(reward)

                # Penalización por cambios bruscos de acción
                flat_action = np.array(action, dtype=np.float32).ravel()
                if self._prev_action is not None and self._smooth_lambda > 0.0:
                    delta = flat_action - self._prev_action
                    reward -= float(self._smooth_lambda * np.linalg.norm(delta))
                self._prev_action = flat_action
                self._prev_obs = obs  # Store for KeyboardInterrupt fallback
                
                # Aplicar normalización de reward
                normalized_reward = self._normalize_reward(float(reward))
                
                return self._flatten(obs), normalized_reward, terminated, truncated, info
        
        wrapped = Monitor(CityLearnWrapper(
            self.env, 
            smooth_lambda=self.config.reward_smooth_lambda,
            normalize_obs=self.config.normalize_observations,
            normalize_rewards=self.config.normalize_rewards,
            reward_scale=self.config.reward_scale,
            clip_obs=self.config.clip_obs,
        ))
        
        # Configurar SAC con optimizadores avanzados y gradient clipping
        policy_kwargs = {
            "net_arch": list(self.config.hidden_sizes),
            "activation_fn": self._get_activation(),
            # Weight_decay moderado para regularización
            "optimizer_kwargs": {"weight_decay": 1e-5},
        }
        
        target_entropy = self.config.target_entropy if self.config.target_entropy is not None else "auto"
        
        # Learning rate MÁS conservador para estabilidad
        stable_lr = min(self.config.learning_rate, 3e-5)  # Max 3e-5 (muy bajo)
        
        # Gamma estándar (SAC maneja bien gamma alto con entropy)
        stable_gamma = self.config.gamma  # Usar config original (0.99)
        
        # Batch size moderado
        stable_batch = min(self.config.batch_size, 512)
        
        logger.info("[SAC] Hiperparámetros: lr=%.2e, gamma=%.3f, batch=%d", 
                    stable_lr, stable_gamma, stable_batch)

        resume_path = Path(self.config.resume_path) if self.config.resume_path else None
        resuming = resume_path is not None and resume_path.exists()
        if resuming:
            logger.info("Reanudando SAC desde checkpoint: %s", resume_path)
            self._sb3_sac = SAC.load(
                str(resume_path),
                env=wrapped,
                device=self.device,
            )
        else:
            self._sb3_sac = SAC(
                "MlpPolicy",
                wrapped,
                learning_rate=stable_lr,
                buffer_size=self.config.buffer_size,
                batch_size=stable_batch,
                gamma=stable_gamma,
                tau=self.config.tau,
                ent_coef=self.config.ent_coef,
                target_entropy=target_entropy,
                gradient_steps=self.config.gradient_steps,
                policy_kwargs=policy_kwargs,
                verbose=self.config.verbose,
                seed=self.config.seed,
                device=self.device,
            )
        
        # Logging del LR actual
        logger.info("[SAC] Using stable learning_rate=%.2e (config was %.2e)", stable_lr, self.config.learning_rate)
        
        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        progress_headers = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
        expected_episodes = int(total_timesteps // 8760) if total_timesteps > 0 else 0

        class TrainingCallback(BaseCallback):
            def __init__(self, agent, progress_path: Optional[Path], progress_headers, expected_episodes: int, verbose=0):
                super().__init__(verbose)
                self.agent = agent
                self.progress_path = progress_path
                self.progress_headers = progress_headers
                self.expected_episodes = expected_episodes
                self.episode_count = 0
                self.log_interval_steps = int(agent.config.log_interval or 0)
                # Métricas acumuladas para promedios
                self.reward_sum = 0.0
                self.reward_count = 0
                self.grid_energy_sum = 0.0  # kWh consumido de la red
                self.solar_energy_sum = 0.0  # kWh de solar usado
                self.co2_intensity = 0.4521  # kg CO2/kWh para Iquitos
                # Ventana móvil para reward_avg (últimos 200 pasos)
                self.recent_rewards = []
                self.reward_window_size = 200

            def _on_step(self):
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]
                
                # Acumular NORMALIZED rewards (después de escala, no raw)
                # Los raw rewards están en [-0.5, 0.5], muy pequeños
                # Necesitamos acumular los scaled rewards para métricas significativas
                rewards = self.locals.get("rewards", [])
                if rewards is not None:
                    if hasattr(rewards, '__iter__'):
                        for r in rewards:
                            # Aplicar misma escala que en training: reward * 0.01 * 100 = reward
                            # (escala de 100x para logging significativo)
                            scaled_r = float(r) * 100.0  # Amplificar para visibilidad en logs
                            self.reward_sum += scaled_r
                            self.reward_count += 1
                            # Agregar a ventana móvil
                            self.recent_rewards.append(scaled_r)
                            if len(self.recent_rewards) > self.reward_window_size:
                                self.recent_rewards.pop(0)
                    else:
                        scaled_r = float(rewards) * 100.0  # Amplificar para visibilidad en logs
                        self.reward_sum += scaled_r
                        self.reward_count += 1
                        # Agregar a ventana móvil
                        self.recent_rewards.append(scaled_r)
                        if len(self.recent_rewards) > self.reward_window_size:
                            self.recent_rewards.pop(0)
                
                # Extraer métricas de energía del environment
                try:
                    env = self.training_env.envs[0] if hasattr(self.training_env, 'envs') else self.training_env
                    if hasattr(env, 'unwrapped'):
                        env = env.unwrapped
                    # CityLearn buildings tienen net_electricity_consumption
                    if hasattr(env, 'buildings'):
                        for b in env.buildings:
                            # Acumular consumo neto de la red
                            if hasattr(b, 'net_electricity_consumption') and b.net_electricity_consumption:
                                last_consumption = b.net_electricity_consumption[-1] if b.net_electricity_consumption else 0
                                # Acumular valor absoluto para contabilizar importación desde red
                                if last_consumption != 0:  # FIJO: Ahora acumula tanto + como -
                                    self.grid_energy_sum += abs(last_consumption)
                            # Acumular generación solar
                            if hasattr(b, 'solar_generation') and b.solar_generation:
                                last_solar = b.solar_generation[-1] if b.solar_generation else 0
                                if last_solar != 0:  # FIJO: Acumula valores no-cero
                                    self.solar_energy_sum += abs(last_solar)
                except Exception:
                    pass
                
                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    
                    # Calcular reward promedio de ventana móvil (últimos 200 pasos)
                    if self.recent_rewards:
                        avg_reward = sum(self.recent_rewards) / len(self.recent_rewards)
                    else:
                        avg_reward = 0.0
                    
                    # Usar grid_energy_sum acumulado, si es 0 usar valor mínimo
                    grid_kwh_to_log = max(self.grid_energy_sum, 100.0) if self.grid_energy_sum == 0 else self.grid_energy_sum
                    
                    # Calcular CO2 estimado
                    co2_kg = grid_kwh_to_log * self.co2_intensity
                    
                    # Obtener métricas de entrenamiento del logger de SB3
                    parts = []
                    parts.append(f"reward_avg={avg_reward:.4f}")
                    
                    try:
                        if hasattr(self.model, 'logger') and self.model.logger is not None:
                            name_to_value = getattr(self.model.logger, 'name_to_value', {})
                            if name_to_value:
                                actor_loss = name_to_value.get('train/actor_loss', None)
                                critic_loss = name_to_value.get('train/critic_loss', None)
                                ent_coef = name_to_value.get('train/ent_coef', None)
                                learning_rate = name_to_value.get('train/learning_rate', None)
                                
                                if actor_loss is not None:
                                    parts.append(f"actor_loss={actor_loss:.2f}")
                                if critic_loss is not None:
                                    parts.append(f"critic_loss={critic_loss:.2f}")
                                if ent_coef is not None:
                                    parts.append(f"ent_coef={ent_coef:.4f}")
                                if learning_rate is not None:
                                    parts.append(f"lr={learning_rate:.2e}")
                    except Exception:
                        pass
                    
                    # Agregar métricas de energía y CO2
                    if self.grid_energy_sum > 0:
                        parts.append(f"grid_kWh={self.grid_energy_sum:.1f}")
                        parts.append(f"co2_kg={co2_kg:.1f}")
                    if self.solar_energy_sum > 0:
                        parts.append(f"solar_kWh={self.solar_energy_sum:.1f}")
                    
                    metrics_str = " | ".join(parts)
                    
                    logger.info(
                        "[SAC] paso %d | ep~%d | pasos_global=%d | %s",
                        self.n_calls,
                        approx_episode,
                        int(self.model.num_timesteps),
                        metrics_str,
                    )
                    if self.progress_path is not None:
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "sac",
                            "episode": approx_episode,
                            "episode_reward": "",
                            "episode_length": "",
                            "global_step": int(self.model.num_timesteps),
                        }
                        append_progress_row(self.progress_path, row, self.progress_headers)
                for info in infos:
                    episode = info.get("episode")
                    if not episode:
                        continue
                    self.episode_count += 1
                    reward = float(episode.get("r", 0.0))
                    length = int(episode.get("l", 0))
                    
                    # Calcular métricas finales del episodio ANTES de reiniciar
                    episode_co2_kg = self.grid_energy_sum * self.co2_intensity
                    episode_grid_kwh = self.grid_energy_sum
                    episode_solar_kwh = self.solar_energy_sum
                    
                    self.agent.training_history.append({
                        "step": int(self.model.num_timesteps),
                        "mean_reward": reward,
                        "episode_co2_kg": episode_co2_kg,
                        "episode_grid_kwh": episode_grid_kwh,
                        "episode_solar_kwh": episode_solar_kwh,
                    })
                    if self.agent.config.progress_interval_episodes > 0 and (
                        self.episode_count % self.agent.config.progress_interval_episodes == 0
                    ):
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "sac",
                            "episode": self.episode_count,
                            "episode_reward": reward,
                            "episode_length": length,
                            "global_step": int(self.model.num_timesteps),
                        }
                        if self.progress_path is not None:
                            append_progress_row(self.progress_path, row, self.progress_headers)
                        if self.expected_episodes > 0:
                            logger.info(
                                "[SAC] ep %d/%d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
                                self.episode_count,
                                self.expected_episodes,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                                episode_co2_kg,
                                episode_grid_kwh,
                                episode_solar_kwh,
                            )
                        else:
                            logger.info(
                                "[SAC] ep %d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
                                self.episode_count,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                                episode_co2_kg,
                                episode_grid_kwh,
                                episode_solar_kwh,
                            )
                    
                    # REINICIAR métricas para el siguiente episodio
                    self.reward_sum = 0.0
                    self.reward_count = 0
                    self.grid_energy_sum = 0.0
                    self.solar_energy_sum = 0.0
                    
                return True

        checkpoint_dir = self.config.checkpoint_dir
        checkpoint_freq = int(self.config.checkpoint_freq_steps or 0)
        logger.info(f"[SAC Checkpoint Config] dir={checkpoint_dir}, freq={checkpoint_freq}")
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"[SAC] Checkpoint directory created: {checkpoint_dir}")
        else:
            logger.warning("[SAC] NO checkpoint directory configured!")

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq
                self.call_count = 0
                logger.info(f"[SAC CheckpointCallback.__init__] save_dir={self.save_dir}, freq={self.freq}")
                if self.save_dir and self.freq > 0:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[SAC CheckpointCallback] Created directory: {self.save_dir}")

            def _on_step(self) -> bool:
                self.call_count += 1
                
                # Log first call and every 1000 calls
                if self.call_count == 1:
                    logger.info(f"[SAC CheckpointCallback._on_step] FIRST CALL DETECTED! n_calls={self.n_calls}")
                
                if self.call_count % 1000 == 0:
                    logger.info(f"[SAC CheckpointCallback._on_step] call #{self.call_count}, n_calls={self.n_calls}")
                
                if self.save_dir is None or self.freq <= 0:
                    return True
                
                # MANDATORY: Check if we should save (every freq calls)
                should_save = (self.n_calls > 0 and self.n_calls % self.freq == 0)
                if should_save:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = self.save_dir / f"sac_step_{self.n_calls}"
                    try:
                        self.model.save(save_path)
                        logger.info(f"[SAC CHECKPOINT OK] Saved: {save_path}")
                    except Exception as exc:
                        logger.error(f"[SAC CHECKPOINT ERROR] {exc}", exc_info=True)
                
                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])
        logger.info("[SAC] Starting model.learn() with callbacks")
        self._sb3_sac.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            reset_num_timesteps=not resuming,
        )
        logger.info("[SAC] model.learn() completed successfully")
        self._trained = True
        self._use_sb3 = True
        self._wrapped_env = wrapped
        logger.info("SAC (SB3) entrenado con %d timesteps", total_timesteps)

        if self._sb3_sac is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "sac_final"
            try:
                self._sb3_sac.save(final_path)
                logger.info("[SAC FINAL OK] Modelo guardado en %s", final_path)
            except Exception as exc:
                logger.error("[SAC FINAL ERROR] %s", exc, exc_info=True)
        
        # MANDATORY: Verify checkpoints were created
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            zips = list(checkpoint_path.glob("*.zip"))
            logger.info(f"[SAC VERIFICATION] Checkpoints created: {len(zips)} files")
            for z in sorted(zips)[:5]:
                logger.info(f"  - {z.name} ({z.stat().st_size / 1024:.1f} KB)")
    
    def _get_activation(self):
        """Obtiene función de activación."""
        import torch.nn as nn
        activations = {
            "relu": nn.ReLU,
            "tanh": nn.Tanh,
            "elu": nn.ELU,
            "leaky_relu": nn.LeakyReLU,
            "gelu": nn.GELU,
        }
        return activations.get(self.config.activation, nn.ReLU)
    
    def predict(self, observations: Any, deterministic: bool = True):
        """Predice acción dado el estado."""
        if not self._trained:
            return self._zero_action()
        
        if self._use_sb3 and self._sb3_sac is not None:
            obs = self._flatten_obs(observations)
            # Asegurar shape exacta al espacio de obs de SB3
            try:
                target_dim = int(self._sb3_sac.observation_space.shape[0])
                if obs.size < target_dim:
                    obs = np.pad(obs, (0, target_dim - obs.size), mode="constant")
                elif obs.size > target_dim:
                    obs = obs[:target_dim]
                obs = obs.astype(np.float32)
            except Exception:
                pass
            action, _ = self._sb3_sac.predict(obs, deterministic=deterministic)
            return self._unflatten_action(action)
        
        if self._citylearn_sac is not None:
            return self._citylearn_sac.predict(observations, deterministic=deterministic)
        
        return self._zero_action()
    
    def _flatten_obs(self, obs):
        if isinstance(obs, dict):
            arr = np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
        elif isinstance(obs, (list, tuple)):
            arr = np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
        else:
            arr = np.array(obs, dtype=np.float32).ravel()
        target_dim = None
        # Priorizar el espacio de observaciГіn del modelo SB3 (que es el que valida dimensiones)
        try:
            if self._sb3_sac is not None and hasattr(self._sb3_sac, "observation_space"):
                space = self._sb3_sac.observation_space
                if space is not None and hasattr(space, "shape") and space.shape:
                    target_dim = int(space.shape[0])
        except Exception:
            target_dim = None
        # Si no se pudo, usar el espacio del env base
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
        return [action.tolist()]
    
    def _zero_action(self):
        """Devuelve acción cero."""
        if isinstance(self.env.action_space, list):
            return [[0.0] * sp.shape[0] for sp in self.env.action_space]
        return [[0.0] * self.env.action_space.shape[0]]
    
    def save(self, path: str):
        """Guarda el modelo entrenado."""
        if self._sb3_sac is not None:
            self._sb3_sac.save(path)
            logger.info("Modelo SAC guardado en %s", path)
    
    def load(self, path: str):
        """Carga un modelo previamente entrenado."""
        from stable_baselines3 import SAC
        self._sb3_sac = SAC.load(path)
        self._trained = True
        self._use_sb3 = True
        logger.info("Modelo SAC cargado desde %s", path)


def make_sac(env: Any, config: Optional[SACConfig] = None, **kwargs) -> SACAgent:
    """Factory function para crear agente SAC robusto."""
    logger.info(f"[make_sac] ENTRY: config={config is not None}, kwargs_empty={not kwargs}")
    
    # CRITICAL FIX: Properly handle config vs kwargs priority
    if config is not None:
        cfg = config
        logger.info(f"[make_sac] Using provided config: checkpoint_dir={cfg.checkpoint_dir}, checkpoint_freq_steps={cfg.checkpoint_freq_steps}")
    elif kwargs:
        cfg = SACConfig(**kwargs)
        logger.info(f"[make_sac] Created config from kwargs: checkpoint_dir={cfg.checkpoint_dir}, checkpoint_freq_steps={cfg.checkpoint_freq_steps}")
    else:
        cfg = SACConfig()
        logger.info(f"[make_sac] Created default config: checkpoint_dir={cfg.checkpoint_dir}, checkpoint_freq_steps={cfg.checkpoint_freq_steps}")
    
    return SACAgent(env, cfg)
