from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List
import numpy as np
import logging

from ..progress import append_progress_row

logger = logging.getLogger(__name__)


def _progress_pct(current: int, total: int) -> Optional[float]:
    """Calcula avance porcentual, devuelve None si no es calculable."""
    if total is None or total <= 0:
        return None
    try:
        return round(100.0 * float(current) / float(total), 1)
    except Exception:
        return None


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
    """Configuración avanzada para SAC con soporte CUDA/GPU y multiobjetivo."""
    # Hiperparámetros de entrenamiento
    episodes: int = 10
    batch_size: int = 256
    buffer_size: int = 100000
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005
    
    # Entropía (auto-ajuste)
    ent_coef: str = "auto"  # "auto" para ajuste automático
    target_entropy: Optional[float] = None
    
    # Red neuronal
    hidden_sizes: tuple = (256, 256)
    activation: str = "relu"
    
    # Escalabilidad
    n_steps: int = 1
    gradient_steps: int = 1
    
    # === CONFIGURACIÓN GPU/CUDA ===
    device: str = "auto"  # "auto", "cuda", "cuda:0", "cuda:1", "mps", "cpu"
    use_amp: bool = False  # Mixed precision (Automatic Mixed Precision)
    pin_memory: bool = True  # Acelera transferencia CPU->GPU
    num_workers: int = 0  # DataLoader workers (0 para CityLearn)
    
    # === MULTIOBJETIVO / MULTICRITERIO ===
    # Pesos para función de recompensa compuesta (deben sumar 1.0)
    weight_co2: float = 0.35           # Minimizar emisiones CO₂
    weight_cost: float = 0.25          # Minimizar costo eléctrico
    weight_solar: float = 0.20         # Maximizar autoconsumo solar
    weight_ev_satisfaction: float = 0.15  # Maximizar satisfacción carga EV
    weight_grid_stability: float = 0.05   # Minimizar picos de demanda
    
    # Umbrales multicriterio
    co2_target_kg_per_kwh: float = 0.45  # Factor emisión Iquitos
    cost_target_usd_per_kwh: float = 0.20  # Tarifa objetivo
    ev_soc_target: float = 0.90          # SOC objetivo EVs al partir
    peak_demand_limit_kw: float = 200.0  # Límite demanda pico
    
    # Reproducibilidad
    seed: int = 42
    deterministic_cuda: bool = False  # True = reproducible pero más lento
    
    # Callbacks y logging
    verbose: int = 0
    log_interval: int = 100
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 0
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1
    prefer_citylearn: bool = False


class SACAgent:
    """Agente SAC robusto y escalable con optimizadores avanzados.
    
    Características:
    - Soft Actor-Critic con ajuste automático de entropía
    - Replay buffer eficiente
    - Redes duales Q para estabilidad
    - Compatible con CityLearn centralizado/descentralizado
    """
    
    def __init__(self, env: Any, config: Optional[SACConfig] = None):
        self.env = env
        self.config = config or SACConfig()
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
        if progress_path is not None and progress_path.exists():
            progress_path.unlink()
        progress_headers = (
            "timestamp",
            "agent",
            "episode",
            "episode_reward",
            "episode_length",
            "global_step",
            "progress_pct",
        )
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
                    obs, info = self.env.reset(**kwargs)
                    self.episode += 1
                    self.episode_steps = 0
                    self.episode_reward = 0.0
                    pct = _progress_pct(self.episode, self.total_episodes)
                    pct_str = f" ({pct:.1f}%)" if pct is not None else ""
                    logger.info("[SAC] ep %d/%d%s iniciado", self.episode, self.total_episodes, pct_str)
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
                            pct = _progress_pct(self.episode, self.total_episodes)
                            row = {
                                "timestamp": datetime.utcnow().isoformat(),
                                "agent": "sac",
                                "episode": self.episode,
                                "episode_reward": self.episode_reward,
                                "episode_length": self.episode_steps,
                                "global_step": self.global_steps,
                                "progress_pct": pct,
                            }
                            if self.progress_path is not None:
                                append_progress_row(self.progress_path, row, self.progress_headers)
                        pct = _progress_pct(self.episode, self.total_episodes)
                        pct_str = f" ({pct:.1f}%)" if pct is not None else ""
                        logger.info(
                            "[SAC] ep %d/%d%s terminado reward=%.4f pasos=%d",
                            self.episode,
                            self.total_episodes,
                            pct_str,
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
        import gymnasium as gym
        from stable_baselines3 import SAC
        from stable_baselines3.common.callbacks import BaseCallback, CallbackList
        from stable_baselines3.common.monitor import Monitor
        
        # Wrapper para compatibilidad
        class CityLearnWrapper(gym.Wrapper):
            def __init__(self, env):
                super().__init__(env)
                self._obs_dim = self._get_obs_dim()
                self._act_dim = self._get_act_dim()
                
                # Redefinir espacios
                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf, 
                    shape=(self._obs_dim,), dtype=np.float32
                )
                self.action_space = gym.spaces.Box(
                    low=-1.0, high=1.0,
                    shape=(self._act_dim,), dtype=np.float32
                )
            
            def _get_obs_dim(self):
                obs, _ = self.env.reset()
                return len(self._flatten(obs))
            
            def _get_act_dim(self):
                if isinstance(self.env.action_space, list):
                    return sum(sp.shape[0] for sp in self.env.action_space)
                return self.env.action_space.shape[0]
            
            def _flatten(self, obs):
                if isinstance(obs, dict):
                    return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
                elif isinstance(obs, (list, tuple)):
                    return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
                return np.array(obs, dtype=np.float32).ravel()
            
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

                # Asegurar reward escalar
                if isinstance(reward, (list, tuple)):
                    reward = sum(reward)
                
                return self._flatten(obs), float(reward), terminated, truncated, info
        
        wrapped = Monitor(CityLearnWrapper(self.env))
        
        # Configurar SAC con optimizadores avanzados
        policy_kwargs = {
            "net_arch": list(self.config.hidden_sizes),
            "activation_fn": self._get_activation(),
        }
        
        target_entropy = self.config.target_entropy if self.config.target_entropy is not None else "auto"
        self._sb3_sac = SAC(
            "MlpPolicy",
            wrapped,
            learning_rate=self.config.learning_rate,
            buffer_size=self.config.buffer_size,
            batch_size=self.config.batch_size,
            gamma=self.config.gamma,
            tau=self.config.tau,
            ent_coef=self.config.ent_coef,
            target_entropy=target_entropy,
            gradient_steps=self.config.gradient_steps,
            policy_kwargs=policy_kwargs,
            verbose=self.config.verbose,
            seed=self.config.seed,
            device=self.device,  # GPU/CUDA support
        )
        
        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        if progress_path is not None and progress_path.exists():
            progress_path.unlink()
        progress_headers = (
            "timestamp",
            "agent",
            "episode",
            "episode_reward",
            "episode_length",
            "global_step",
            "progress_pct",
        )
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

            def _on_step(self):
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]
                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    pct = _progress_pct(approx_episode, self.expected_episodes)
                    pct_str = f" ({pct:.1f}%)" if pct is not None else ""
                    logger.info(
                        "[SAC] paso %d | ep~%d%s | pasos_global=%d",
                        self.n_calls,
                        approx_episode,
                        pct_str,
                        int(self.model.num_timesteps),
                    )
                    if self.progress_path is not None:
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "sac",
                            "episode": approx_episode,
                            "episode_reward": "",
                            "episode_length": "",
                            "global_step": int(self.model.num_timesteps),
                            "progress_pct": pct,
                        }
                        append_progress_row(self.progress_path, row, self.progress_headers)
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
                        pct = _progress_pct(self.episode_count, self.expected_episodes)
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "sac",
                            "episode": self.episode_count,
                            "episode_reward": reward,
                            "episode_length": length,
                            "global_step": int(self.model.num_timesteps),
                            "progress_pct": pct,
                        }
                        if self.progress_path is not None:
                            append_progress_row(self.progress_path, row, self.progress_headers)
                        if self.expected_episodes > 0:
                            logger.info(
                                "[SAC] ep %d/%d (%.1f%%) reward=%.4f len=%d step=%d",
                                self.episode_count,
                                self.expected_episodes,
                                pct if pct is not None else 0.0,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                        else:
                            logger.info(
                                "[SAC] ep %d reward=%.4f len=%d step=%d",
                                self.episode_count,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                            )
                return True

        checkpoint_dir = self.config.checkpoint_dir
        checkpoint_freq = int(self.config.checkpoint_freq_steps or 0)
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq

            def _on_step(self):
                if self.save_dir is None or self.freq <= 0:
                    return True
                if self.n_calls % self.freq == 0:
                    save_path = self.save_dir / f"sac_step_{self.n_calls}"
                    try:
                        self.model.save(save_path)
                        logger.info("Checkpoint SAC guardado en %s", save_path)
                    except Exception as exc:
                        logger.warning("No se pudo guardar checkpoint SAC (%s)", exc)
                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])
        self._sb3_sac.learn(total_timesteps=total_timesteps, callback=callback)
        self._trained = True
        self._use_sb3 = True
        self._wrapped_env = wrapped
        logger.info("SAC (SB3) entrenado con %d timesteps", total_timesteps)

        if self._sb3_sac is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "sac_final"
            try:
                self._sb3_sac.save(final_path)
                logger.info("Modelo SAC guardado en %s", final_path)
            except Exception as exc:
                logger.warning("No se pudo guardar modelo SAC (%s)", exc)
    
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
            action, _ = self._sb3_sac.predict(obs, deterministic=deterministic)
            return self._unflatten_action(action)
        
        if self._citylearn_sac is not None:
            return self._citylearn_sac.predict(observations, deterministic=deterministic)
        
        return self._zero_action()
    
    def _flatten_obs(self, obs):
        if isinstance(obs, dict):
            return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
        elif isinstance(obs, (list, tuple)):
            return np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs])
        return np.array(obs, dtype=np.float32).ravel()
    
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
    cfg = config or SACConfig(**kwargs) if kwargs else SACConfig()
    return SACAgent(env, cfg)
