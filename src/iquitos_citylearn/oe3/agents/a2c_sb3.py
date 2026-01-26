from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable, Union
import warnings
import numpy as np
import logging

# Suppress stable_baselines3 render_mode warning
warnings.filterwarnings("ignore", message=".*render_mode.*")

from ..progress import append_progress_row, render_progress_plot

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """Auto-detecta el mejor dispositivo disponible (CUDA/MPS/CPU).

    Prioridad:
        1. CUDA si disponible (NVIDIA GPU)
        2. MPS si disponible (Apple Silicon)
        3. CPU como fallback

    Returns:
        str: Device identifier ('cuda', 'cuda:0', 'mps', 'cpu')
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("GPU CUDA detectada: %s", device_name)
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("GPU MPS (Apple Silicon) detectada")
            return "mps"
    except ImportError:
        logger.warning("PyTorch no disponible; usando CPU")
    logger.info("Usando CPU para entrenamiento")
    return "cpu"


@dataclass
class A2CConfig:
    """Configuración para A2C (SB3) con soporte CUDA/GPU.

    Nota: train_steps=500000 es el mínimo recomendado para problemas de alta
    dimensionalidad como CityLearn con ~900 obs dims × 126 action dims.
    """
    # Hiperparámetros de entrenamiento - A2C OPTIMIZADO PARA RTX 4060
    train_steps: int = 500000  # ↓ REDUCIDO: 1M→500k (GPU limitada)
    n_steps: int = 512         # ↓ REDUCIDO: 2048→512 (menos buffer)
    learning_rate: float = 3e-4    # ↑ AUMENTADO: 1.5e-4→3e-4
    lr_schedule: str = "linear"    # ✅ Decay automático
    gamma: float = 0.99            # ↓ REDUCIDO: 0.999→0.99 (simplifica)
    gae_lambda: float = 0.90       # ↓ REDUCIDO: 0.95→0.90 (menos varianza)
    ent_coef: float = 0.01         # ✅ Mantener
    vf_coef: float = 0.5           # ↓ REDUCIDO: 0.7→0.5
    max_grad_norm: float = 0.5     # ↓ REDUCIDO: 1.0→0.5
    hidden_sizes: tuple = (512, 512)   # ↓ REDUCIDA: 1024→512
    activation: str = "relu"
    device: str = "auto"
    seed: int = 42
    verbose: int = 0
    log_interval: int = 2000
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 1000  # MANDATORY: Default to 1000 for checkpoint generation
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1
    resume_path: Optional[str] = None  # Ruta a checkpoint SB3 para reanudar

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

    # Suavizado de acciones (penaliza cambios bruscos)
    reward_smooth_lambda: float = 0.0
    # === NORMALIZACIÓN (crítico para estabilidad) ===
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.01
    clip_obs: float = 10.0


class A2CAgent:
    """Agente A2C robusto usando Stable-Baselines3."""

    def __init__(self, env: Any, config: Optional[A2CConfig] = None):
        self.env = env
        self.config = config or A2CConfig()
        self.model: Optional[Any] = None
        self.wrapped_env: Optional[Any] = None
        self._trained = False
        self.training_history: List[Dict[str, float]] = []
        self.device = self._setup_device()

    def _setup_device(self) -> str:
        if self.config.device == "auto":
            return detect_device()
        return self.config.device

    def learn(self, total_timesteps: Optional[int] = None, **kwargs: Any) -> None:
        """Entrena el agente A2C."""
        _ = kwargs  # Silenciar warning de argumento no usado
        try:
            import gymnasium as gym
            from stable_baselines3 import A2C  # type: ignore[import]
            from stable_baselines3.common.env_util import make_vec_env
            from stable_baselines3.common.callbacks import BaseCallback, CallbackList
            from stable_baselines3.common.monitor import Monitor
        except ImportError as e:
            logger.warning("stable_baselines3 no disponible: %s", e)
            return

        steps = total_timesteps or self.config.train_steps

        class CityLearnWrapper(gym.Wrapper):
            def __init__(self, env, smooth_lambda: float = 0.0,
                         normalize_obs: bool = True, normalize_rewards: bool = True,
                         reward_scale: float = 0.01, clip_obs: float = 10.0):
                super().__init__(env)
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
                self._reward_scale = reward_scale  # 0.01
                self._clip_obs = clip_obs
                self._reward_count = 1e-4
                self._reward_mean = 0.0
                self._reward_var = 1.0

                # CRITICAL FIX: Selective prescaling (NOT generic 0.001 for all obs)
                # Power/Energy values (kW, kWh): scale by 0.001 → [0, 5] range
                # SOC/Percentage values (0-1 or 0-100): scale by 1.0 (keep as is)
                # The last obs elements are typically BESS SOC [0, 1] → must use 1.0 scale
                self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001
                # NOTE: Future improvement: detect obs type and set prescale selectively

                # Running stats
                self._obs_mean = np.zeros(self.obs_dim, dtype=np.float64)
                self._obs_var = np.ones(self.obs_dim, dtype=np.float64)
                self._obs_count = 1e-4

                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf, shape=(self.obs_dim,), dtype=np.float32
                )
                self.action_space = gym.spaces.Box(
                    low=-1.0, high=1.0, shape=(self.act_dim,), dtype=np.float32
                )

            def _update_obs_stats(self, obs: np.ndarray):
                delta = obs - self._obs_mean
                self._obs_count += 1
                self._obs_mean = self._obs_mean + delta / self._obs_count
                delta2 = obs - self._obs_mean
                self._obs_var = self._obs_var + (delta * delta2 - self._obs_var) / self._obs_count

            def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
                if not self._normalize_obs:
                    return obs.astype(np.float32)
                # Pre-escalar + running stats + clip
                prescaled = obs * self._obs_prescale
                self._update_obs_stats(prescaled)
                normalized = (prescaled - self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
                clipped = np.clip(normalized, -self._clip_obs, self._clip_obs)
                return np.asarray(clipped, dtype=np.float32)

            def _update_reward_stats(self, reward: float):
                delta = reward - self._reward_mean
                self._reward_count += 1
                self._reward_mean += delta / self._reward_count
                delta2 = reward - self._reward_mean
                self._reward_var += (delta * delta2 - self._reward_var) / self._reward_count

            def _normalize_reward(self, reward: float) -> float:
                if not self._normalize_rewards:
                    return reward
                scaled = reward * self._reward_scale
                return float(np.clip(scaled, -10.0, 10.0))

            def _get_act_dim(self):
                if isinstance(self.env.action_space, list):
                    return sum(sp.shape[0] for sp in self.env.action_space)
                action_space = getattr(self.env, 'action_space', None)
                if action_space is not None and hasattr(action_space, 'shape'):
                    return int(action_space.shape[0])
                return 126  # Default to 126 charger actions as fallback

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
                except (AttributeError, TypeError, IndexError, ValueError) as err:
                    logger.debug("Error extracting PV/BESS features: %s", err)
                return np.array([pv_kw, soc], dtype=np.float32)

            def _flatten_base(self, obs):
                if isinstance(obs, dict):
                    return np.concatenate([np.array(v, dtype=np.float32).ravel() for v in obs.values()])
                if isinstance(obs, (list, tuple)):
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
                return self._normalize_observation(arr.astype(np.float32))

            def _unflatten_action(self, action):
                if isinstance(self.env.action_space, list):
                    result = []
                    idx = 0
                    for sp in self.env.action_space:
                        dim = sp.shape[0]
                        result.append(action[idx:idx + dim].tolist())
                        idx += dim
                    return result
                return [action.tolist()]

            def reset(self, **kwargs):
                obs, info = self.env.reset(**kwargs)
                self._prev_action = None
                return self._flatten(obs), info

            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                obs, reward, terminated, truncated, info = self.env.step(citylearn_action)

                if truncated and not terminated:
                    terminated = True
                    truncated = False

                if isinstance(reward, (list, tuple)):
                    reward = float(sum(reward))
                else:
                    reward = float(reward)

                flat_action = np.array(action, dtype=np.float32).ravel()
                if self._prev_action is not None and self._smooth_lambda > 0.0:
                    delta = flat_action - self._prev_action
                    reward -= float(self._smooth_lambda * np.linalg.norm(delta))
                self._prev_action = flat_action

                normalized_reward = self._normalize_reward(reward)
                return self._flatten(obs), normalized_reward, terminated, truncated, info

        wrapped = CityLearnWrapper(
            self.env,
            smooth_lambda=self.config.reward_smooth_lambda,
            normalize_obs=self.config.normalize_observations,
            normalize_rewards=self.config.normalize_rewards,
            reward_scale=self.config.reward_scale,
            clip_obs=self.config.clip_obs,
        )
        self.wrapped_env = Monitor(wrapped)

        def _env_creator() -> Any:
            """Factory function to create wrapped environment."""
            return self.wrapped_env

        vec_env = make_vec_env(_env_creator, n_envs=1, seed=self.config.seed)

        lr_schedule = self._get_lr_schedule()  # No requiere parámetros
        policy_kwargs = {
            "net_arch": list(self.config.hidden_sizes),
            "activation_fn": self._get_activation(),
        }

        logger.info("Creando modelo A2C en dispositivo: %s", self.device)
        resume_path = Path(self.config.resume_path) if self.config.resume_path else None
        resuming = resume_path is not None and resume_path.exists()
        if resuming:
            logger.info("Reanudando A2C desde checkpoint: %s", resume_path)
            self.model = A2C.load(
                str(resume_path),
                env=vec_env,
                device=self.device,
            )
        else:
            self.model = A2C(
                "MlpPolicy",
                vec_env,
                learning_rate=lr_schedule,
                n_steps=int(self.config.n_steps),
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
                ent_coef=self.config.ent_coef,
                vf_coef=self.config.vf_coef,
                max_grad_norm=self.config.max_grad_norm,
                policy_kwargs=policy_kwargs,
                verbose=self.config.verbose,
                seed=self.config.seed,
                device=self.device,
            )

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
                # Métricas acumuladas para promedios
                self.reward_sum = 0.0
                self.reward_count = 0
                self.grid_energy_sum = 0.0  # kWh consumido de la red
                self.solar_energy_sum = 0.0  # kWh de solar usado
                self.co2_intensity = 0.4521  # kg CO2/kWh para Iquitos

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
                    else:
                        scaled_r = float(rewards) * 100.0  # Amplificar para visibilidad en logs
                        self.reward_sum += scaled_r
                        self.reward_count += 1

                # Extraer métricas de energía del environment
                try:
                    envs_list = getattr(self.training_env, 'envs', None)
                    env = envs_list[0] if envs_list else self.training_env
                    if hasattr(env, 'unwrapped'):
                        env = env.unwrapped
                    if hasattr(env, 'buildings'):
                        for b in getattr(env, 'buildings', []):
                            # Acumular consumo neto de la red
                            if hasattr(b, 'net_electricity_consumption') and b.net_electricity_consumption:
                                last_consumption = b.net_electricity_consumption[-1] if b.net_electricity_consumption else 0
                                # Acumular valor absoluto para contabilizar importación desde red
                                if last_consumption != 0:  # FIJO: Ahora acumula tanto + como -
                                    self.grid_energy_sum += abs(last_consumption)
                            # Acumular generación solar (SIEMPRE, incluso si es 0 en la noche)
                            if hasattr(b, 'solar_generation') and b.solar_generation is not None:
                                last_solar = b.solar_generation[-1] if b.solar_generation else 0
                                # Acumular TODOS los valores (incluyendo 0 en noche), pero solo si es positivo
                                self.solar_energy_sum += max(0, float(last_solar))
                except (AttributeError, TypeError, IndexError, ValueError) as err:
                    logger.debug("Error extracting energy metrics: %s", err)

                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)

                    # Calcular reward promedio
                    avg_reward = self.reward_sum / max(1, self.reward_count)

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
                                policy_loss = name_to_value.get('train/policy_loss', None)
                                value_loss = name_to_value.get('train/value_loss', None)
                                entropy_loss = name_to_value.get('train/entropy_loss', None)
                                learning_rate = name_to_value.get('train/learning_rate', None)

                                if policy_loss is not None:
                                    parts.append(f"policy_loss={policy_loss:.2f}")
                                if value_loss is not None:
                                    parts.append(f"value_loss={value_loss:.2f}")
                                if entropy_loss is not None:
                                    parts.append(f"entropy={entropy_loss:.4f}")
                                if learning_rate is not None:
                                    parts.append(f"lr={learning_rate:.2e}")
                    except (AttributeError, TypeError, KeyError, ValueError) as err:
                        logger.debug("Error extracting training metrics: %s", err)

                    # Agregar métricas de energía y CO2
                    if self.grid_energy_sum > 0:
                        parts.append(f"grid_kWh={self.grid_energy_sum:.1f}")
                        parts.append(f"co2_kg={co2_kg:.1f}")
                    if self.solar_energy_sum > 0:
                        parts.append(f"solar_kWh={self.solar_energy_sum:.1f}")

                    metrics_str = " | ".join(parts)

                    logger.info(
                        "[A2C] paso %d | ep~%d | pasos_global=%d | %s",
                        self.n_calls,
                        approx_episode,
                        int(self.model.num_timesteps),
                        metrics_str,
                    )
                    if self.progress_path is not None:
                        row = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": "a2c",
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
                            "agent": "a2c",
                            "episode": self.episode_count,
                            "episode_reward": reward,
                            "episode_length": length,
                            "global_step": int(self.model.num_timesteps),
                        }
                        if self.progress_path is not None:
                            append_progress_row(self.progress_path, row, self.progress_headers)
                            png_path = self.progress_path.with_suffix(".png")
                            render_progress_plot(self.progress_path, png_path, "A2C progreso")
                        if self.expected_episodes > 0:
                            logger.info(
                                "[A2C] ep %d/%d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
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
                                "[A2C] ep %d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
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
        logger.info("[A2C Checkpoint Config] dir=%s, freq=%s", checkpoint_dir, checkpoint_freq)
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            logger.info("[A2C] Checkpoint directory created: %s", checkpoint_dir)
        else:
            logger.warning("[A2C] NO checkpoint directory configured!")

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq
                self.call_count = 0
                logger.info("[A2C CheckpointCallback.__init__] save_dir=%s, freq=%s", self.save_dir, self.freq)
                if self.save_dir and self.freq > 0:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("[A2C CheckpointCallback] Created directory: %s", self.save_dir)

            def _on_step(self) -> bool:
                self.call_count += 1

                if self.call_count == 1:
                    logger.info("[A2C CheckpointCallback._on_step] FIRST CALL DETECTED! num_timesteps=%s", self.num_timesteps)

                if self.call_count % 100 == 0:
                    logger.info("[A2C CheckpointCallback._on_step] call #%s, num_timesteps=%s", self.call_count, self.num_timesteps)

                if self.save_dir is None or self.freq <= 0:
                    return True

                # Use num_timesteps (total steps so far) instead of n_calls (rollout count)
                should_save = (self.num_timesteps > 0 and self.num_timesteps % self.freq == 0)
                if should_save:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = self.save_dir / f"a2c_step_{self.num_timesteps}"
                    try:
                        self.model.save(save_path)
                        logger.info("[A2C CHECKPOINT OK] Saved: %s", save_path)
                    except (OSError, IOError, TypeError, ValueError) as exc:
                        logger.error("[A2C CHECKPOINT ERROR] %s", exc, exc_info=True)

                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])

        logger.info("[A2C] Starting model.learn() with callbacks")
        self.model.learn(
            total_timesteps=int(steps),
            callback=callback,
            reset_num_timesteps=not resuming,
        )
        logger.info("[A2C] model.learn() completed successfully")
        self._trained = True
        logger.info("A2C entrenado con %d timesteps", steps)

        if self.model is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "a2c_final"
            try:
                self.model.save(final_path)
                logger.info("[A2C FINAL OK] Modelo guardado en %s", final_path)
            except (OSError, IOError, TypeError, ValueError) as exc:
                logger.error("[A2C FINAL ERROR] %s", exc, exc_info=True)

        # MANDATORY: Verify checkpoints were created
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            zips = list(checkpoint_path.glob("*.zip"))
            logger.info("[A2C VERIFICATION] Checkpoints created: %d files", len(zips))
            for z in sorted(zips)[:5]:
                size_kb = z.stat().st_size / 1024
                logger.info("  - %s (%.1f KB)", z.name, size_kb)

    def _get_lr_schedule(self) -> Union[Callable[[float], float], float]:
        """Crea scheduler de learning rate."""
        # Try to import from stable-baselines3
        linear_fn: Union[Callable, None] = None
        try:
            from stable_baselines3.common.utils import get_linear_fn as sb3_get_linear_fn  # type: ignore[import]
            linear_fn = sb3_get_linear_fn  # type: ignore[assignment]
        except (ImportError, AttributeError):
            pass

        if linear_fn is None:
            # Fallback implementation
            def linear_fn_fallback(init_val: float, final_val: float, _total: float) -> Callable[[float], float]:
                def fn(progress: float) -> float:
                    return init_val + (final_val - init_val) * progress
                return fn
            linear_fn = linear_fn_fallback

        if self.config.lr_schedule == "linear":
            result: Union[Callable[[float], float], float] = linear_fn(self.config.learning_rate, self.config.learning_rate * 0.1, 1.0)  # type: ignore[misc]
            return result
        if self.config.lr_schedule == "cosine":
            def cosine_schedule(progress: float) -> float:
                return float(self.config.learning_rate * (0.5 * (1 + np.cos(np.pi * (1 - progress)))))
            return cosine_schedule
        return self.config.learning_rate

    def _get_activation(self):
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
        except (AttributeError, TypeError, ValueError) as err:
            logger.debug("Error adjusting observation: %s", err)
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
        if self.model is not None and hasattr(self.model, "observation_space"):
            space = self.model.observation_space
            if space is not None and hasattr(space, "shape") and space.shape:
                try:
                    target_dim = int(space.shape[0])
                except (TypeError, ValueError) as err:
                    logger.debug("Error converting model obs space shape: %s", err)
        if target_dim is None:
            space = getattr(self.env, "observation_space", None)
            if space is not None and hasattr(space, "shape") and space.shape:
                try:
                    target_dim = int(space.shape[0])
                except (TypeError, ValueError) as err:
                    logger.debug("Error converting env obs space shape: %s", err)
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
                result.append(action[idx:idx + dim].tolist())
                idx += dim
            return result
        if isinstance(action, np.ndarray):
            return [action.tolist()]
        return [action]

    def _zero_action(self):
        action_space = getattr(self.env, "action_space", None)
        if action_space is None:
            return [[0.0]]
        if isinstance(action_space, list):
            return [[0.0] * sp.shape[0] for sp in action_space]
        return [[0.0] * action_space.shape[0]]

    def save(self, path: str):
        if self.model is not None:
            self.model.save(path)
            logger.info("Modelo A2C guardado en %s", path)

    def load(self, path: str):
        from stable_baselines3 import A2C  # type: ignore
        self.model = A2C.load(path)
        self._trained = True
        logger.info("Modelo A2C cargado desde %s", path)


def make_a2c(env: Any, config: Optional[A2CConfig] = None, **kwargs) -> A2CAgent:
    """Factory function para crear agente A2C robusto."""
    # FIX CRÍTICO: Evaluación explícita para evitar bug con kwargs={}
    if config is not None:
        cfg = config
        logger.info("[make_a2c] Using provided config: checkpoint_dir=%s, checkpoint_freq_steps=%s", cfg.checkpoint_dir, cfg.checkpoint_freq_steps)
    elif kwargs:
        cfg = A2CConfig(**kwargs)
        logger.info("[make_a2c] Created A2CConfig from kwargs: checkpoint_dir=%s", cfg.checkpoint_dir)
    else:
        cfg = A2CConfig()
        logger.info("[make_a2c] Created default A2CConfig: checkpoint_dir=%s", cfg.checkpoint_dir)
    return A2CAgent(env, cfg)
