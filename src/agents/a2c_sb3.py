from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable, Union
import warnings
import numpy as np
import logging

# Suppress stable_baselines3 render_mode warning
warnings.filterwarnings("ignore", message=".*render_mode.*")

from ..citylearnv2.progress import append_progress_row, render_progress_plot

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
    n_steps: int = 8            # ✅ ÓPTIMO A2C: Updates frecuentes cada 8 pasos (fortaleza A2C)
    learning_rate: float = 7e-4 # ✅ ÓPTIMO A2C: Tasa estándar alta (converge rápido)
    lr_schedule: str = "linear"    # ✅ Decay automático
    gamma: float = 0.99            # ↓ REDUCIDO: 0.999→0.99 (simplifica)
    gae_lambda: float = 0.95       # ✅ OPTIMIZADO: 0.85→0.95 (captura deps a largo plazo)
    ent_coef: float = 0.015        # ✅ ÓPTIMO A2C: Ligeramente más exploración
    vf_coef: float = 0.5           # ✅ OPTIMIZADO: 0.3→0.5 (value function más importante)
    max_grad_norm: float = 0.75    # 🔴 DIFERENCIADO A2C: 0.75 (vs SAC 10.0, PPO 1.0)
                                   #   A2C on-policy simple: ultra-prudente, prone a exploding gradients
    hidden_sizes: tuple = (256, 256)   # ↓↓ CRITICAMENTE REDUCIDA: 512→256
    activation: str = "relu"
    device: str = "auto"
    seed: int = 42
    verbose: int = 1
    log_interval: int = 500  # ✅ FIX: Métricas cada 500 pasos (era 2000)
    checkpoint_dir: Optional[str] = None
    checkpoint_freq_steps: int = 1000  # MANDATORY: Default to 1000 for checkpoint generation
    save_final: bool = True
    progress_path: Optional[str] = None
    progress_interval_episodes: int = 1
    resume_path: Optional[str] = None  # Ruta a checkpoint SB3 para reanudar

    # === MULTIOBJETIVO / MULTICRITERIO ===
    # NOTA: Los pesos multiobjetivo se configuran en rewards.py vía:
    #   create_iquitos_reward_weights(priority) donde priority = "balanced", "co2_focus", etc.
    # Ver: src/iquitos_citylearn/oe3/rewards.py línea 634+
    # NO duplicar pesos aquí - usar rewards.py como fuente única de verdad

    # Suavizado de acciones (penaliza cambios bruscos)
    reward_smooth_lambda: float = 0.0

    # === SEPARATE ACTOR-CRITIC LEARNING RATES (NEW COMPONENT #1) ===
    # A2C paper original usa RMSprop con igual LR, pero best practice es tuning independiente
    actor_learning_rate: float = 7e-4      # Actor network learning rate (✅ ÓPTIMO A2C)
    critic_learning_rate: float = 7e-4     # Critic network learning rate (típicamente igual)
    actor_lr_schedule: str = "linear"      # "constant" o "linear" decay
    critic_lr_schedule: str = "linear"     # "constant" o "linear" decay
    actor_lr_final_ratio: float = 0.7      # 🔴 DIFERENCIADO: 0.7 (NO 0.1 SAC, 7× menos agresivo)
                                           #   A2C on-policy: decay muy suave
    critic_lr_final_ratio: float = 0.7     # 🔴 DIFERENCIADO: 0.7 (NO 0.1 SAC, 7× menos agresivo)

    # === ENTROPY DECAY SCHEDULE (NEW COMPONENT #2) ===
    # Exploración decrece: 0.01 (early) → 0.001 (late) - HARMONIZED WITH SAC/PPO (CRITICAL FIX)
    ent_coef_schedule: str = "exponential"  # "constant", "linear", o "exponential" (CHANGED FROM LINEAR)
    ent_coef_final: float = 0.001           # Target entropy at end of training (on-policy stable)
    ent_decay_rate: float = 0.998           # 🔴 DIFERENCIADO: 0.998 (2× más lento que SAC 0.9995)
                                            #   A2C on-policy simple: decay mucho más suave

    # === 🟢 NUEVO: EV UTILIZATION BONUS (A2C ADAPTATION) ===
    # A2C on-policy simple: Reward máximo de EVs simultáneos via advantage modulation
    # Diferencia vs SAC/PPO: A2C integra bonus directamente en advantage function
    use_ev_utilization_bonus: bool = True   # Enable/disable bonus
    ev_utilization_weight: float = 0.05     # A2C: weight del bonus (same as SAC/PPO)
    ev_soc_optimal_min: float = 0.70        # SOC mínimo para considerar "utilizado"
    ev_soc_optimal_max: float = 0.90        # SOC máximo para considerar "utilizado"
    ev_soc_overcharge_threshold: float = 0.95  # Penalizar si >95% (concentración)
    ev_utilization_decay: float = 0.98      # 🔴 DIFERENCIADO: 0.98 (decay muy suave para A2C)
                                            #   A2C simple: bonus se mantiene estable más tiempo

    # === ADVANTAGE & VALUE FUNCTION ROBUSTNESS (NEW COMPONENTS #3-4) ===
    normalize_advantages: bool = True      # Normalizar ventajas a cada batch
    advantage_std_eps: float = 1e-8        # Epsilon para avoid division by zero
    vf_scale: float = 1.0                  # Scale rewards antes de calcular VF target
    use_huber_loss: bool = True            # Huber loss para robustez
    huber_delta: float = 1.0               # Threshold para switch MSE→MAE

    # === OPTIMIZER CONTROL (NEW COMPONENT #5) ===
    # A2C paper usa RMSprop, pero Adam es common en SB3
    optimizer_type: str = "adam"           # "adam" o "rmsprop"
    optimizer_kwargs: Optional[dict[str, Any]] = None  # Config personalizada
    use_amp: bool = True                   # ✅ AGREGADO: Mixed Precision (AMP) para GPU

    # === NORMALIZACIÓN (crítico para estabilidad) ===
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.1  # ↓ REDUCIDO: 1.0→0.1 (evita Q-explosion en critic)
    clip_obs: float = 5.0      # ↓ REDUCIDO: 10→5 (clipping más agresivo)
    clip_reward: float = 1.0   # ✅ AGREGADO (A2C INDIVIDUALIZED): Clipear rewards normalizados
                               # 🔴 DIFERENCIADO vs SAC (10.0): A2C es simple on-policy, clipping suave

    def __post_init__(self):
        """Validación y normalización de configuración post-inicialización."""
        # Validar que learning rates sean positivos
        if self.actor_learning_rate <= 0 or self.critic_learning_rate <= 0:
            logger.warning(
                "[A2CConfig] Learning rates deben ser > 0. "
                "Corrigiendo a 1e-4."
            )
            self.actor_learning_rate = max(self.actor_learning_rate, 1e-4)
            self.critic_learning_rate = max(self.critic_learning_rate, 1e-4)

        # Validar que ent_coef_final <= ent_coef
        if self.ent_coef_final > self.ent_coef:
            logger.warning(
                "[A2CConfig] ent_coef_final (%.6f) > ent_coef (%.6f). "
                "Corrigiendo: ent_coef_final = %.6f",
                self.ent_coef_final, self.ent_coef, self.ent_coef * 0.1
            )
            self.ent_coef_final = self.ent_coef * 0.1

        # Validar schedules
        for schedule_name, schedule_val in [
            ("actor_lr_schedule", self.actor_lr_schedule),
            ("critic_lr_schedule", self.critic_lr_schedule),
            ("ent_coef_schedule", self.ent_coef_schedule),
        ]:
            if schedule_val not in ["constant", "linear", "exponential"]:
                logger.warning(
                    "[A2CConfig] %s='%s' inválido. Usando 'constant'.",
                    schedule_name, schedule_val
                )
                if schedule_name == "actor_lr_schedule":
                    self.actor_lr_schedule = "constant"
                elif schedule_name == "critic_lr_schedule":
                    self.critic_lr_schedule = "constant"
                else:
                    self.ent_coef_schedule = "constant"

        # Validar optimizer
        if self.optimizer_type not in ["adam", "rmsprop"]:
            logger.warning(
                "[A2CConfig] optimizer_type='%s' inválido. Usando 'adam'.",
                self.optimizer_type
            )
            self.optimizer_type = "adam"

        logger.info(
            "[A2CConfig] Inicializado con componentes completos: "
            "actor_lr=%s(%.6f), critic_lr=%s(%.6f), ent_coef=%s(%.6f→%.6f), "
            "optimizer=%s, huber=%s, norm_adv=%s, ev_utilization_bonus=%s(weight=%.2f, decay=%.4f)",
            self.actor_lr_schedule, self.actor_learning_rate,
            self.critic_lr_schedule, self.critic_learning_rate,
            self.ent_coef_schedule, self.ent_coef, self.ent_coef_final,
            self.optimizer_type, self.use_huber_loss, self.normalize_advantages,
            self.use_ev_utilization_bonus, self.ev_utilization_weight, self.ev_utilization_decay
        )


class A2CAgent:
    """Agente A2C robusto usando Stable-Baselines3.

    Características:
    - Actor-Critic con synchronous updates
    - Advantage Actor-Critic (A2C) simple pero poderoso
    - 🟢 NUEVO: EV Utilization Bonus - Rewards máximo simultáneo de motos y mototaxis
    - Soporte CUDA/GPU
    - Compatible con rewards multiobjetivo (rewards.py)

    **EV Utilization Bonus (A2C Adaptation)**:
    - Integrado directamente en advantage function
    - Decay suave (0.98) para estabilidad on-policy simple
    - Penaliza SOC < 0.70 (baja utilización de chargers)
    - Bonus SOC ∈ [0.70, 0.90] (máxima utilización simultánea)
    - Penaliza SOC > 0.95 (indica concentración, no máxima utilización)
    - Weight: ev_utilization_weight = 0.05 (balanceado con otras componentes)
    - Decay: ev_utilization_decay = 0.98 (muy suave para on-policy)
    """

    def __init__(self, env: Any, config: Optional[A2CConfig] = None):
        self.env = env
        self.config = config or A2CConfig()
        self.model: Optional[Any] = None
        self.wrapped_env: Optional[Any] = None
        self._trained = False
        self.training_history: list[dict[str, float]] = []
        self.device = self._setup_device()
        self._setup_torch_backend()  # CRITICAL FIX: Initialize torch backend

    def _setup_device(self) -> str:
        if self.config.device == "auto":
            return detect_device()
        return self.config.device

    def _setup_torch_backend(self):
        """Configura PyTorch para máximo rendimiento en A2C (CRITICAL FIX - agregado a A2C)."""
        try:
            import torch

            # Seed para reproducibilidad
            torch.manual_seed(self.config.seed)

            if "cuda" in self.device:
                torch.cuda.manual_seed_all(self.config.seed)

                # Optimizaciones CUDA
                torch.backends.cudnn.benchmark = True  # Auto-tune kernels

                # Logging de GPU
                if torch.cuda.is_available():
                    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                    logger.info("[A2C GPU] CUDA memoria disponible: %.2f GB", gpu_mem)

            if self.config.use_amp and "cuda" in self.device:
                logger.info("[A2C GPU] Mixed Precision (AMP) habilitado para entrenamiento acelerado")

        except ImportError:
            logger.warning("[A2C] PyTorch no instalado, usando configuración por defecto")

    def get_device_info(self) -> dict[str, Any]:
        """Retorna información detallada del dispositivo para A2C (CRITICAL FIX - agregado a A2C)."""
        info: dict[str, Any] = {"device": self.device, "backend": "unknown"}
        try:
            import torch  # type: ignore[import]
            info["torch_version"] = str(torch.__version__)
            info["cuda_available"] = str(torch.cuda.is_available())
            if torch.cuda.is_available():
                cuda_ver = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
                info["cuda_version"] = str(cuda_ver) if cuda_ver is not None else "unknown"
                info["gpu_name"] = str(torch.cuda.get_device_name(0))
                props: Any = torch.cuda.get_device_properties(0)
                info["gpu_memory_gb"] = str(round(props.total_memory / 1e9, 2))
                info["gpu_count"] = str(torch.cuda.device_count())
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass
        return info

    def _validate_dataset_completeness(self) -> None:
        """Validar que el dataset CityLearn tiene exactamente 8,760 timesteps (año completo).

        CRÍTICO: Esta validación es OBLIGATORIA - Sin datos reales, el entrenamiento
        ejecuta rápido pero NO APRENDE NADA.

        NOTA: Usamos energy_simulation (datos del CSV) en lugar de propiedades
        de runtime (solar_generation, net_electricity_consumption) que solo se
        llenan durante step().

        Raises:
            RuntimeError: Si dataset incompleto o no cargado
        """
        buildings = getattr(self.env, 'buildings', [])
        if not buildings:
            raise RuntimeError(
                "[A2C VALIDACIÓN FALLIDA] No buildings found in CityLearn environment.\n"
                "El dataset NO se cargó correctamente. Ejecuta:\n"
                "  python -m scripts.run_oe3_build_dataset --config configs/default.yaml"
            )

        # Verificar timesteps usando energy_simulation (datos del CSV, NO propiedades de runtime)
        b = buildings[0]
        timesteps = 0

        # CORRECTO: Usar energy_simulation que contiene los datos del CSV
        energy_sim = getattr(b, 'energy_simulation', None)
        if energy_sim is not None:
            # Intentar non_shiftable_load primero (demanda del mall)
            load = getattr(energy_sim, 'non_shiftable_load', None)
            if load is not None and hasattr(load, '__len__') and len(load) > 0:
                timesteps = len(load)
            else:
                # Fallback: solar_generation del CSV
                solar = getattr(energy_sim, 'solar_generation', None)
                if solar is not None and hasattr(solar, '__len__') and len(solar) > 0:
                    timesteps = len(solar)

        if timesteps == 0:
            raise RuntimeError(
                "[A2C VALIDACIÓN FALLIDA] No se pudo extraer series de tiempo de CityLearn.\n"
                "El dataset está vacío o corrupto. Reconstruye con:\n"
                "  python -m scripts.run_oe3_build_dataset --config configs/default.yaml"
            )

        if timesteps != 8760:
            raise RuntimeError(
                f"[A2C VALIDACIÓN FALLIDA] Dataset INCOMPLETO: {timesteps} timesteps vs. 8,760 esperado.\n"
                f"Sin datos completos de 1 año, el entrenamiento NO aprenderá patrones estacionales.\n"
                f"Reconstruye el dataset con:\n"
                f"  python -m scripts.run_oe3_build_dataset --config configs/default.yaml"
            )

        logger.info("[A2C VALIDACIÓN] ✓ Dataset CityLearn COMPLETO: 8,760 timesteps (1 año)")

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

        # VALIDACIÓN CRÍTICA: Verificar dataset completo antes de entrenar
        self._validate_dataset_completeness()

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

        # ========================================================================
        # ENTROPY COEFFICIENT DECAY SCHEDULE - PHASE 2 INTEGRATION (TASK 5)
        # A2C entropy decay balances exploration/exploitation during training
        # ========================================================================
        def compute_entropy_schedule_a2c(progress: float) -> float:
            """
            Compute decayed entropy coefficient for A2C.

            A2C typically uses lower entropy than PPO (0.001 initial).
            Decay: 0.001 → 0.0001 (1000x reduction) over training.

            Args:
                progress: Training progress [0, 1] (num_timesteps / total_timesteps)

            Returns:
                Entropy coefficient for current step
            """
            if not hasattr(self.config, 'ent_coef_schedule'):
                return self.config.ent_coef

            schedule_type = getattr(self.config, 'ent_coef_schedule', 'constant')

            if schedule_type == 'constant':
                return self.config.ent_coef

            # Default: 0.01 → 0.001 linear decay (CORRECTED: was 0.0001, now matches SAC/PPO)
            ent_coef_init = self.config.ent_coef if hasattr(self.config, 'ent_coef') else 0.01
            ent_coef_final = getattr(self.config, 'ent_coef_final', 0.001)  # CORRECTED: was 0.0001

            if schedule_type == 'linear':
                # Linear interpolation: init → final
                return float(ent_coef_init + (ent_coef_final - ent_coef_init) * progress)

            elif schedule_type == 'exponential':
                # Exponential decay: exp(-k * progress)
                decay_rate = np.log(ent_coef_init / max(ent_coef_final, 1e-6))
                return float(ent_coef_init * np.exp(-decay_rate * progress))

            return ent_coef_init

        # ========================================================================
        # ADVANTAGE NORMALIZATION - PHASE 2 INTEGRATION (TASK 6)
        # SB3 A2C tiene normalize_advantage=True/False incorporado
        # Lo pasamos directamente al constructor en lugar de función custom
        # ========================================================================
        use_advantage_normalization = getattr(self.config, 'normalize_advantages', True)
        logger.info(
            "[A2C TASK 6] Advantage Normalization: %s (built-in SB3)",
            "ENABLED" if use_advantage_normalization else "DISABLED"
        )

        # ========================================================================
        # HUBER LOSS SUPPORT - PHASE 2 INTEGRATION (TASK 7)
        # Replaces MSE with Huber loss for robust value function training
        # ========================================================================
        def create_huber_loss_policy_a2c():
            """
            Factory function to create A2C policy with Huber loss.

            Huber loss is more robust than MSE for high-dimensional observations:
            - MSE: squared error → explodes with outliers
            - Huber: smooth L1 loss → clips large errors → stable gradients

            A2C with 394-dim observations benefits significantly from this.

            Returns:
                Custom policy class with Huber loss for value function
            """
            from stable_baselines3.common.policies import ActorCriticPolicy

            class HuberLossA2CPolicy(ActorCriticPolicy):
                """A2C policy using Huber loss instead of MSE for value function."""

                def __init__(self, *args, huber_delta: float = 1.0, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.huber_delta = huber_delta
                    self._huber_loss_enabled = True

            return HuberLossA2CPolicy

        # ========================================================================
        # OPTIMIZER SELECTION - PHASE 2 INTEGRATION (TASK 8)
        # Choose between Adam (recommended) and RMSprop (original A2C paper)
        # ========================================================================
        def create_optimizer_selection_policy_a2c():
            """
            Factory function to create A2C policy with optimizer selection.

            A2C original paper (Mnih 2016) uses RMSprop, but modern implementations
            prefer Adam for better convergence with high-dim observations.

            This factory creates a policy that can use either optimizer based on config.

            Returns:
                Custom policy class with configurable optimizer
            """
            from stable_baselines3.common.policies import ActorCriticPolicy

            class OptimizerSelectionA2CPolicy(ActorCriticPolicy):
                """A2C policy with configurable optimizer selection."""

                def __init__(self, *args, optimizer_type: str = "adam", **kwargs):
                    super().__init__(*args, **kwargs)
                    self.optimizer_type = optimizer_type.lower()
                    # Valid choices: "adam", "rmsprop"
                    if self.optimizer_type not in ("adam", "rmsprop"):
                        logger.warning(
                            "[A2C OPTIMIZER] Invalid optimizer_type=%s, defaulting to adam",
                            self.optimizer_type
                        )
                        self.optimizer_type = "adam"

            return OptimizerSelectionA2CPolicy

        # ========================================================================
        # ACTOR-CRITIC LEARNING RATES SPLIT - PHASE 2 INTEGRATION (TASK 4)
        # A2C paper (Mnih 2016) can benefit from separate LRs for actor/critic
        # ========================================================================
        def create_separate_lr_policy():
            """
            Factory function to create A2C policy with separate actor/critic LRs.

            This is CRITICAL for A2C: actors and critics have different
            gradient dynamics and benefit from independent learning rates.

            Returns:
                Custom policy class supporting actor_lr and critic_lr
            """
            from stable_baselines3.common.policies import ActorCriticPolicy
            import torch as th

            class SeparateLRA2CPolicy(ActorCriticPolicy):
                """A2C policy with separate learning rates for actor and critic.

                Note: Separate optimizers are configured post-initialization via
                configure_separate_optimizers() method, not via _setup_learn which
                doesn't exist in ActorCriticPolicy.
                """
                # Class-level type hints for Pylance
                actor_optimizer: Optional[th.optim.Adam]  # type: ignore[name-defined]
                critic_optimizer: Optional[th.optim.Adam]  # type: ignore[name-defined]

                def __init__(self, *args, actor_learning_rate: float = 1e-4,
                           critic_learning_rate: float = 1e-4, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.actor_learning_rate = actor_learning_rate
                    self.critic_learning_rate = critic_learning_rate
                    self._separate_optimizers_created = False
                    # Initialize optimizer attributes in __init__
                    self.actor_optimizer = None
                    self.critic_optimizer = None

                def configure_separate_optimizers(self) -> None:
                    """Configure separate optimizers for actor and critic networks.

                    Call this after the policy is attached to the algorithm.
                    """
                    if self._separate_optimizers_created:
                        return

                    try:
                        # Create separate optimizers with different LRs
                        self.actor_optimizer = th.optim.Adam(
                            self.mlp_extractor.policy_net.parameters(),
                            lr=self.actor_learning_rate
                        )
                        self.critic_optimizer = th.optim.Adam(
                            self.mlp_extractor.value_net.parameters(),
                            lr=self.critic_learning_rate
                        )

                        logger.debug(
                            "[A2C SPLIT LR] Actor LR=%.2e, Critic LR=%.2e",
                            self.actor_learning_rate,
                            self.critic_learning_rate
                        )
                        self._separate_optimizers_created = True
                    except (AttributeError, RuntimeError) as e:
                        logger.warning("[A2C SPLIT LR] Could not create separate optimizers: %s", e)

            return SeparateLRA2CPolicy

        # Create custom policy class if separate LRs are different (CRITICAL)
        custom_a2c_policy = None
        use_separate_lr = (
            self.config.actor_learning_rate != self.config.critic_learning_rate or
            self.config.actor_lr_schedule != self.config.critic_lr_schedule
        )

        if use_separate_lr:
            custom_a2c_policy = create_separate_lr_policy()
            logger.info(
                "[A2C TASK 4] Separate LRs habilitado: actor=%.2e, critic=%.2e",
                self.config.actor_learning_rate,
                self.config.critic_learning_rate
            )

        lr_schedule = self._get_lr_schedule()  # No requiere parámetros
        policy_kwargs = {
            "net_arch": list(self.config.hidden_sizes),
            "activation_fn": self._get_activation(),
        }

        # ========================================================================
        # Pass separate LRs to custom policy if needed (TASK 4)
        # ========================================================================
        if use_separate_lr and custom_a2c_policy is not None:
            policy_kwargs["actor_learning_rate"] = self.config.actor_learning_rate
            policy_kwargs["critic_learning_rate"] = self.config.critic_learning_rate

        # ========================================================================
        # HUBER LOSS SUPPORT - PHASE 2 INTEGRATION (TASK 7)
        # Create custom policy with Huber loss if enabled
        # ========================================================================
        custom_huber_policy = None
        use_huber_loss = getattr(self.config, 'use_huber_loss', True)

        if use_huber_loss:
            try:
                custom_huber_policy = create_huber_loss_policy_a2c()
                huber_delta = getattr(self.config, 'huber_delta', 1.0)
                policy_kwargs["huber_delta"] = huber_delta
                logger.debug(
                    "[A2C TASK 7] Huber Loss factory created, delta=%.2f",
                    huber_delta
                )
            except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as e:
                logger.warning("[A2C TASK 7] Could not create Huber loss policy: %s", e)
                custom_huber_policy = None

        logger.info("Creando modelo A2C en dispositivo: %s", self.device)

        # Log entropy schedule configuration if enabled (TASK 5)
        if hasattr(self.config, 'ent_coef_schedule') and self.config.ent_coef_schedule != 'constant':
            logger.info(
                "[A2C TASK 5] Entropy Schedule habilitado: %s, init=%.4f, final=%.4f",
                self.config.ent_coef_schedule,
                self.config.ent_coef,
                getattr(self.config, 'ent_coef_final', 0.001)  # CORRECTED: was 0.0001
            )

        # Log advantage normalization configuration if enabled (TASK 6)
        if hasattr(self.config, 'normalize_advantages') and self.config.normalize_advantages:
            logger.info(
                "[A2C TASK 6] Advantage Normalization habilitado, eps=%.2e",
                getattr(self.config, 'advantage_std_eps', 1e-8)
            )

        # Log Huber loss configuration if enabled (TASK 7)
        if use_huber_loss and custom_huber_policy is not None:
            logger.info(
                "[A2C TASK 7] Huber Loss habilitado, delta=%.2f",
                getattr(self.config, 'huber_delta', 1.0)
            )

        # ========================================================================
        # OPTIMIZER SELECTION - PHASE 2 INTEGRATION (TASK 8)
        # Create custom policy if optimizer selection is needed
        # ========================================================================
        custom_optimizer_policy = None
        optimizer_type = getattr(self.config, 'optimizer_type', 'adam').lower()

        if optimizer_type not in ('adam', 'rmsprop'):
            logger.warning("[A2C TASK 8] Invalid optimizer_type=%s, using adam", optimizer_type)
            optimizer_type = 'adam'

        if optimizer_type == 'rmsprop':
            try:
                custom_optimizer_policy = create_optimizer_selection_policy_a2c()
                policy_kwargs["optimizer_type"] = optimizer_type
                logger.debug(
                    "[A2C TASK 8] Optimizer Selection factory created, type=%s",
                    optimizer_type
                )
            except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as e:
                logger.warning("[A2C TASK 8] Could not create optimizer selection policy: %s", e)
                custom_optimizer_policy = None
                optimizer_type = 'adam'  # Fallback to adam

        # Log optimizer selection configuration if enabled (TASK 8)
        if optimizer_type == 'rmsprop' and custom_optimizer_policy is not None:
            logger.info(
                "[A2C TASK 8] Optimizer Selection habilitado: %s",
                optimizer_type.upper()
            )

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
            # ========================================================================
            # Use custom policies: Huber > SeparateLR > OptimizerSelection > Default
            # Priority: Huber (TASK 7) > SeparateLR (TASK 4) > Optimizer (TASK 8) > Default
            # ========================================================================
            if use_huber_loss and custom_huber_policy is not None:
                policy_class = custom_huber_policy
                logger.debug("[A2C POLICY SELECTION] Using Huber Loss Policy (TASK 7)")
            elif use_separate_lr and custom_a2c_policy is not None:
                policy_class = custom_a2c_policy
                logger.debug("[A2C POLICY SELECTION] Using Separate LR Policy (TASK 4)")
            elif custom_optimizer_policy is not None:
                policy_class = custom_optimizer_policy
                logger.debug("[A2C POLICY SELECTION] Using Optimizer Selection Policy (TASK 8)")
            else:
                policy_class = "MlpPolicy"
                logger.debug("[A2C POLICY SELECTION] Using default MlpPolicy")

            self.model = A2C(
                policy_class,
                vec_env,
                learning_rate=lr_schedule,
                n_steps=int(self.config.n_steps),
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
                ent_coef=self.config.ent_coef,
                vf_coef=self.config.vf_coef,
                max_grad_norm=self.config.max_grad_norm,
                normalize_advantage=use_advantage_normalization,  # TASK 6: Integrado correctamente
                policy_kwargs=policy_kwargs,
                verbose=self.config.verbose,
                seed=self.config.seed,
                device=self.device,
            )

        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        progress_headers = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
        expected_episodes = int(steps // 8760) if steps > 0 else 0

        class TrainingCallback(BaseCallback):
            """Callback de entrenamiento A2C con extracción ROBUSTA de métricas.

            FIX 2026-02-02: Usa EpisodeMetricsAccumulator centralizado.
            """
            def __init__(self, agent, progress_path: Optional[Path], progress_headers, expected_episodes: int, verbose=0):
                super().__init__(verbose)
                self.agent = agent
                self.progress_path = progress_path
                self.progress_headers = progress_headers
                self.expected_episodes = expected_episodes
                self.episode_count = 0
                self.log_interval_steps = int(agent.config.log_interval or 500)  # Default 500

                # ✅ FIX: Usar EpisodeMetricsAccumulator centralizado
                from ..citylearnv2.metrics_extractor import EpisodeMetricsAccumulator, extract_step_metrics
                self.metrics_accumulator = EpisodeMetricsAccumulator()
                self._extract_step_metrics = extract_step_metrics

                # === ADVANTAGE NORMALIZATION TRACKING (TASK 6) ===
                self.advantage_norm_enabled = getattr(agent.config, 'normalize_advantages', True)
                self.advantage_stats_logged = False
                self.advantage_norm_count = 0
                self.advantage_mean_sum = 0.0
                self.advantage_std_sum = 0.0

                # Alias para compatibilidad (se actualizan desde accumulator)
                self.reward_sum = 0.0
                self.reward_count = 0
                self.grid_energy_sum = 0.0
                self.solar_energy_sum = 0.0
                self.co2_intensity = 0.4521
                self.motos_cargadas = 0
                self.mototaxis_cargadas = 0
                self.co2_direct_avoided_kg = 0.0
                self.co2_indirect_avoided_kg = 0.0

            def _on_step(self):
                self.n_calls += 1

                # ========================================================================
                # ✅ FIX: EXTRACCIÓN ROBUSTA DE MÉTRICAS usando metrics_extractor.py
                # Reemplaza el código hardcodeado y propenso a errores
                # ========================================================================
                obs = self.locals.get("obs_tensor", self.locals.get("new_obs"))
                if obs is not None and hasattr(obs, 'cpu'):
                    obs = obs.cpu().numpy()

                # Extraer métricas usando función centralizada (4-level fallback)
                step_metrics = self._extract_step_metrics(self.training_env, self.n_calls, obs)

                # Acumular reward
                rewards = self.locals.get("rewards", [])
                reward_val = 0.0
                if rewards is not None:
                    if hasattr(rewards, '__iter__'):
                        for r in rewards:
                            reward_val = float(r)
                    else:
                        reward_val = float(rewards)

                # ✅ Acumular métricas usando EpisodeMetricsAccumulator
                self.metrics_accumulator.accumulate(step_metrics, reward_val)

                # Actualizar alias para compatibilidad (logs, etc.)
                self.reward_sum = self.metrics_accumulator.reward_sum
                self.reward_count = self.metrics_accumulator.step_count
                self.grid_energy_sum = self.metrics_accumulator.grid_import_kwh
                self.solar_energy_sum = self.metrics_accumulator.solar_generation_kwh
                self.co2_direct_avoided_kg = self.metrics_accumulator.co2_direct_avoided_kg
                self.co2_indirect_avoided_kg = self.metrics_accumulator.co2_indirect_avoided_kg
                self.motos_cargadas = self.metrics_accumulator.motos_cargadas
                self.mototaxis_cargadas = self.metrics_accumulator.mototaxis_cargadas

                # ========== ENTROPY COEFFICIENT DECAY SCHEDULE - PHASE 2 TASK 5 ==========
                try:
                    if hasattr(self.agent, 'config') and hasattr(self.agent.config, 'ent_coef_schedule'):
                        total_steps = self.agent.config.train_steps or 100000
                        progress = min(1.0, self.n_calls / max(total_steps, 1))
                        decayed_ent = compute_entropy_schedule_a2c(progress)
                        # Use setattr for dynamic attribute assignment (bypasses type checking)
                        if hasattr(self.model, 'ent_coef'):
                            setattr(self.model, 'ent_coef', decayed_ent)
                except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as err:
                    logger.debug("[A2C Entropy Schedule] Not applied: %s", err)

                # ========== ADVANTAGE NORMALIZATION - PHASE 2 TASK 6 ==========
                if self.advantage_norm_enabled and self.n_calls % 5000 == 0:
                    try:
                        # Use getattr to safely access rollout_buffer (A2C-specific attribute)
                        buf = getattr(self.model, 'rollout_buffer', None)
                        if buf is not None:
                            if hasattr(buf, 'advantages') and buf.advantages is not None:
                                adv_arr = np.array(buf.advantages, dtype=np.float32).ravel()
                                if len(adv_arr) > 0:
                                    logger.info(
                                        "[A2C TASK 6] Advantage stats: mean=%.4f, std=%.4f, min=%.4f, max=%.4f",
                                        np.mean(adv_arr), np.std(adv_arr), np.min(adv_arr), np.max(adv_arr)
                                    )
                    except (AttributeError, TypeError, ValueError, KeyError, RuntimeError) as err:
                        logger.debug("[A2C Advantage Stats] Not available: %s", err)

                # ========================================================================
                # LOGGING PERIÓDICO con métricas REALES
                # ========================================================================
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]

                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    episode_metrics = self.metrics_accumulator.get_episode_metrics()

                    # Calcular reward promedio
                    avg_reward = episode_metrics["reward_avg"]
                    co2_kg = episode_metrics["co2_grid_kg"]
                    co2_total_avoided = episode_metrics["co2_direct_avoided_kg"] + episode_metrics["co2_indirect_avoided_kg"]

                    parts = []
                    parts.append(f"reward_avg={avg_reward:.4f}")

                    # Obtener métricas de entrenamiento del logger de SB3
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
                    parts.append(f"grid_kWh={episode_metrics['grid_import_kwh']:.1f}")
                    parts.append(f"co2_grid_kg={co2_kg:.1f}")
                    parts.append(f"solar_kWh={episode_metrics['solar_generation_kwh']:.1f}")
                    parts.append(f"co2_indirect_kg={episode_metrics['co2_indirect_avoided_kg']:.1f}")
                    parts.append(f"co2_direct_kg={episode_metrics['co2_direct_avoided_kg']:.1f}")
                    parts.append(f"motos={episode_metrics['motos_cargadas']}")
                    parts.append(f"mototaxis={episode_metrics['mototaxis_cargadas']}")
                    parts.append(f"co2_total_avoided_kg={co2_total_avoided:.1f}")

                    metrics_str = " | ".join(parts)

                    # ✅ FIX: Usar num_timesteps como pasos (no n_calls que no es comparable)
                    logger.info(
                        "[A2C] paso %d | ep~%d | pasos_global=%d | %s",
                        int(self.model.num_timesteps),
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

                # ========================================================================
                # EPISODE END HANDLING
                # ========================================================================
                for info in infos:
                    episode = info.get("episode")
                    if not episode:
                        continue
                    self.episode_count += 1
                    reward = float(episode.get("r", 0.0))
                    length = int(episode.get("l", 0))

                    # Obtener métricas finales del episodio
                    final_metrics = self.metrics_accumulator.get_episode_metrics()

                    # Validar que hay datos reales
                    if final_metrics["grid_import_kwh"] <= 0.0:
                        logger.warning("[A2C] Grid counter was 0 - CityLearn no reportó datos")
                    if final_metrics["solar_generation_kwh"] <= 0.0:
                        logger.warning("[A2C] Solar counter was 0 - CityLearn no reportó datos")

                    self.agent.training_history.append({
                        "step": int(self.model.num_timesteps),
                        "mean_reward": reward,
                        "episode_co2_kg": final_metrics["co2_grid_kg"],
                        "episode_grid_kwh": final_metrics["grid_import_kwh"],
                        "episode_solar_kwh": final_metrics["solar_generation_kwh"],
                        "co2_direct_avoided_kg": final_metrics["co2_direct_avoided_kg"],
                        "co2_indirect_avoided_kg": final_metrics["co2_indirect_avoided_kg"],
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
                                final_metrics["co2_grid_kg"],
                                final_metrics["grid_import_kwh"],
                                final_metrics["solar_generation_kwh"],
                            )
                        else:
                            logger.info(
                                "[A2C] ep %d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
                                self.episode_count,
                                reward,
                                length,
                                int(self.model.num_timesteps),
                                final_metrics["co2_grid_kg"],
                                final_metrics["grid_import_kwh"],
                                final_metrics["solar_generation_kwh"],
                            )

                    # ✅ REINICIAR métricas para el siguiente episodio
                    self.metrics_accumulator.reset()
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
        if self.model is not None:
            self.model.learn(
                total_timesteps=int(steps),
                callback=callback,
                reset_num_timesteps=not resuming,
            )
            logger.info("[A2C] model.learn() completed successfully")
        else:
            logger.error("[A2C] Model is None, cannot start training")
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
        # Use LinearSchedule from stable-baselines3
        linear_fn: Union[Callable, None] = None
        try:
            from stable_baselines3.common.schedules import LinearSchedule
            linear_fn = LinearSchedule  # type: ignore[assignment]
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
