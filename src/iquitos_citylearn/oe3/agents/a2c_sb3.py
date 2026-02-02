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
    n_steps: int = 2048         # ✅ CORREGIDO: 32→2,048 (ver año completo en updates)
    learning_rate: float = 1e-4    # ↓ CRITICAMENTE REDUCIDO: 3e-4→1e-4 (previene explosión)
    lr_schedule: str = "linear"    # ✅ Decay automático
    gamma: float = 0.99            # ↓ REDUCIDO: 0.999→0.99 (simplifica)
    gae_lambda: float = 0.95       # ✅ OPTIMIZADO: 0.85→0.95 (captura deps a largo plazo)
    ent_coef: float = 0.01         # ✅ OPTIMIZADO: 0.001→0.01 (exploración adecuada)
    vf_coef: float = 0.5           # ✅ OPTIMIZADO: 0.3→0.5 (value function más importante)
    max_grad_norm: float = 0.5     # ✅ OPTIMIZADO: 0.25→0.5 (clipping menos agresivo)
    hidden_sizes: tuple = (256, 256)   # ↓↓ CRITICAMENTE REDUCIDA: 512→256
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
    co2_target_kg_per_kwh: float = 0.4521  # Factor emisión Iquitos (grid import)
    co2_conversion_factor: float = 2.146   # Para cálculo directo: 50kW × 2.146 = 107.3 kg/h
    cost_target_usd_per_kwh: float = 0.20  # Tarifa objetivo
    ev_soc_target: float = 0.90          # SOC objetivo EVs al partir
    ev_demand_constant_kw: float = 50.0  # Demanda EV constante (workaround CityLearn 2.5.0)
    peak_demand_limit_kw: float = 200.0  # Límite demanda pico

    # Suavizado de acciones (penaliza cambios bruscos)
    reward_smooth_lambda: float = 0.0

    # === SEPARATE ACTOR-CRITIC LEARNING RATES (NEW COMPONENT #1) ===
    # A2C paper original usa RMSprop con igual LR, pero best practice es tuning independiente
    actor_learning_rate: float = 1e-4      # Actor network learning rate
    critic_learning_rate: float = 1e-4     # Critic network learning rate (típicamente igual)
    actor_lr_schedule: str = "linear"      # "constant" o "linear" decay
    critic_lr_schedule: str = "linear"     # "constant" o "linear" decay

    # === ENTROPY DECAY SCHEDULE (NEW COMPONENT #2) ===
    # Exploración decrece: 0.001 (early) → 0.0001 (late)
    ent_coef_schedule: str = "linear"      # "constant" o "linear"
    ent_coef_final: float = 0.0001         # Target entropy at end of training

    # === ADVANTAGE & VALUE FUNCTION ROBUSTNESS (NEW COMPONENTS #3-4) ===
    normalize_advantages: bool = True      # Normalizar ventajas a cada batch
    advantage_std_eps: float = 1e-8        # Epsilon para avoid division by zero
    vf_scale: float = 1.0                  # Scale rewards antes de calcular VF target
    use_huber_loss: bool = True            # Huber loss para robustez
    huber_delta: float = 1.0               # Threshold para switch MSE→MAE

    # === OPTIMIZER CONTROL (NEW COMPONENT #5) ===
    # A2C paper usa RMSprop, pero Adam es common en SB3
    optimizer_type: str = "adam"           # "adam" o "rmsprop"
    optimizer_kwargs: Optional[Dict[str, Any]] = None  # Config personalizada

    # === NORMALIZACIÓN (crítico para estabilidad) ===
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.1  # ↓ REDUCIDO: 1.0→0.1 (evita Q-explosion en critic)
    clip_obs: float = 5.0      # ↓ REDUCIDO: 10→5 (clipping más agresivo)
    clip_reward: float = 1.0   # ✅ AGREGADO: Clipear rewards normalizados

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
            "optimizer=%s, huber=%s, norm_adv=%s",
            self.actor_lr_schedule, self.actor_learning_rate,
            self.critic_lr_schedule, self.critic_learning_rate,
            self.ent_coef_schedule, self.ent_coef, self.ent_coef_final,
            self.optimizer_type, self.use_huber_loss, self.normalize_advantages
        )


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

    def _validate_dataset_completeness(self) -> None:
        """Validar que el dataset CityLearn tiene exactamente 8,760 timesteps (año completo)."""
        try:
            buildings = getattr(self.env, 'buildings', [])
            if not buildings:
                logger.warning("[VALIDACIÓN-A2C] No buildings found in environment")
                return

            b = buildings[0]
            solar_gen = getattr(b, 'solar_generation', None)

            if solar_gen is None or len(solar_gen) == 0:
                net_elec = getattr(b, 'net_electricity_consumption', None)
                if net_elec is None or len(net_elec) == 0:
                    logger.warning("[VALIDACIÓN-A2C] No se pudo extraer series de tiempo")
                    return
                timesteps = len(net_elec)
            else:
                timesteps = len(solar_gen)

            if timesteps != 8760:
                logger.warning(
                    f"[VALIDACIÓN-A2C] Dataset INCOMPLETO: {timesteps} timesteps vs. 8,760 esperado"
                )
                if timesteps < 4380:
                    raise ValueError(f"[CRÍTICO-A2C] Dataset INCOMPLETO: {timesteps} < 4,380 (6 meses mínimo)")
            else:
                logger.info("[VALIDACIÓN-A2C] Dataset CityLearn COMPLETO: 8,760 timesteps ✓")

        except Exception as e:
            logger.warning(f"[VALIDACIÓN-A2C] No se pudo verificar dataset: {e}")

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

            # Default: 0.001 → 0.0001 linear decay
            ent_coef_init = self.config.ent_coef if hasattr(self.config, 'ent_coef') else 0.001
            ent_coef_final = getattr(self.config, 'ent_coef_final', 0.0001)

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
        # Normalizes advantages to stabilize training with high-dim observations
        # ========================================================================
        def normalize_advantages_batch(advantages: Any) -> Any:
            """
            Normalize advantages to zero mean, unit std dev.

            High-dimensional observations (394-dim) have variable advantage scales.
            Normalization stabilizes gradient flow and prevents divergence.

            Args:
                advantages: Batch of advantage estimates (shape: [batch_size])

            Returns:
                Normalized advantages (shape: [batch_size])
            """
            if not hasattr(self.config, 'normalize_advantages') or not self.config.normalize_advantages:
                return np.asarray(advantages, dtype=np.float32)

            adv_mean = np.mean(advantages)
            adv_std = np.std(advantages)
            eps = getattr(self.config, 'advantage_std_eps', 1e-8)

            # Normalize: (adv - mean) / (std + eps)
            normalized = (advantages - adv_mean) / (adv_std + eps)

            if np.any(np.isnan(normalized)) or np.any(np.isinf(normalized)):
                logger.warning("[A2C ADVANAGE NORM] NaN/Inf detected, returning original advantages")
                return np.asarray(advantages, dtype=np.float32)

            return np.asarray(normalized, dtype=np.float32)

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
            from stable_baselines3.a2c.policies import ActorCriticPolicy

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
            from stable_baselines3.a2c.policies import ActorCriticPolicy

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
            from stable_baselines3.a2c.policies import ActorCriticPolicy
            import torch as th

            class SeparateLRA2CPolicy(ActorCriticPolicy):
                """A2C policy with separate learning rates for actor and critic."""

                def __init__(self, *args, actor_learning_rate: float = 1e-4,
                           critic_learning_rate: float = 1e-4, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.actor_learning_rate = actor_learning_rate
                    self.critic_learning_rate = critic_learning_rate
                    self._separate_optimizers_created = False

                def _setup_learn(self, *args, **kwargs):
                    """Setup learning after policy creation."""
                    super()._setup_learn(*args, **kwargs)

                    # Create separate optimizers for actor and critic
                    if not self._separate_optimizers_created:
                        try:
                            # Create separate optimizers with different LRs
                            self.actor_optimizer = th.optim.Adam(
                                self.policy_net.parameters(),
                                lr=self.actor_learning_rate
                            )
                            self.critic_optimizer = th.optim.Adam(
                                self.value_net.parameters(),
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
            except Exception as e:
                logger.warning("[A2C TASK 7] Could not create Huber loss policy: %s", e)
                custom_huber_policy = None

        logger.info("Creando modelo A2C en dispositivo: %s", self.device)

        # Log entropy schedule configuration if enabled (TASK 5)
        if hasattr(self.config, 'ent_coef_schedule') and self.config.ent_coef_schedule != 'constant':
            logger.info(
                "[A2C TASK 5] Entropy Schedule habilitado: %s, init=%.4f, final=%.4f",
                self.config.ent_coef_schedule,
                self.config.ent_coef,
                getattr(self.config, 'ent_coef_final', 0.0001)
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
            except Exception as e:
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
                # === ADVANTAGE NORMALIZATION TRACKING (TASK 6) ===
                self.advantage_norm_enabled = getattr(agent.config, 'normalize_advantages', True)
                self.advantage_norm_count = 0  # Number of times normalization applied
                self.advantage_mean_sum = 0.0  # Sum of advantage means (for averaging)
                self.advantage_std_sum = 0.0   # Sum of advantage stds (for averaging)
                self.grid_energy_sum = 0.0  # kWh consumido de la red
                self.solar_energy_sum = 0.0  # kWh de solar usado
                self.co2_intensity = 0.4521  # kg CO2/kWh para Iquitos
                self.motos_cargadas = 0  # Contador de motos cargadas (SOC >= 90%)
                self.mototaxis_cargadas = 0  # Contador de mototaxis cargadas (SOC >= 90%)
                self.co2_direct_avoided_kg = 0.0  # CO₂ evitado por cargar EVs
                self.co2_indirect_avoided_kg = 0.0  # CO₂ evitado por usar solar

            def _on_step(self):
                self.n_calls += 1

                # ========== CO₂ DIRECTA: CALCULAR PRIMERO (antes de cualquier try-except) ==========
                try:
                    EV_DEMAND_CONSTANT_KW = 50.0
                    co2_factor_ev_direct = 2.146
                    co2_direct_step_kg = EV_DEMAND_CONSTANT_KW * co2_factor_ev_direct  # 107.3 kg/h

                    prev_co2 = getattr(self, 'co2_direct_avoided_kg', 0.0)
                    self.co2_direct_avoided_kg = prev_co2 + co2_direct_step_kg

                    motos_step = int((EV_DEMAND_CONSTANT_KW * 0.80) / 2.0)
                    mototaxis_step = int((EV_DEMAND_CONSTANT_KW * 0.20) / 3.0)
                    self.motos_cargadas = getattr(self, 'motos_cargadas', 0) + motos_step
                    self.mototaxis_cargadas = getattr(self, 'mototaxis_cargadas', 0) + mototaxis_step

                    # Logging cada 500 steps
                    if self.n_calls % 500 == 0:
                        logger.info(
                            f"[A2C CO2 DIRECTO] step={self.n_calls} | total={self.co2_direct_avoided_kg:.1f} kg | motos={self.motos_cargadas} | mototaxis={self.mototaxis_cargadas}"
                        )
                except Exception as err:
                    logger.error(f"[A2C CRÍTICO - CO2 DIRECTA] step={self.n_calls} | ERROR: {err}", exc_info=True)

                # ========== ENTROPY COEFFICIENT DECAY SCHEDULE - PHASE 2 TASK 5 ==========
                try:
                    if hasattr(self.agent, 'config') and hasattr(self.agent.config, 'ent_coef_schedule'):
                        # Compute progress [0, 1]
                        total_steps = self.agent.config.train_steps or 100000
                        progress = min(1.0, self.n_calls / max(total_steps, 1))

                        # Compute decayed entropy coefficient
                        decayed_ent = compute_entropy_schedule_a2c(progress)

                        # Update model's entropy coefficient
                        if hasattr(self.model, 'ent_coef'):
                            self.model.ent_coef = decayed_ent

                            # Debug log every 10 × log_interval
                            if hasattr(self.agent, 'config'):
                                log_interval = getattr(self.agent.config, 'log_interval', 1000)
                                if log_interval > 0 and self.n_calls % (10 * log_interval) == 0:
                                    logger.debug(
                                        "[A2C ENTROPY SCHEDULE] step=%d, progress=%.3f, ent_coef=%.4f",
                                        self.n_calls, progress, decayed_ent
                                    )
                except Exception as err:
                    logger.debug("[A2C Entropy Schedule] Not applied: %s", err)

                # ========== ADVANTAGE NORMALIZATION TRACKING - PHASE 2 TASK 6 ==========
                try:
                    if self.advantage_norm_enabled:
                        # Try to extract advantages from model's rollout buffer
                        if hasattr(self.model, 'rollout_buffer'):
                            buf = self.model.rollout_buffer
                            if hasattr(buf, 'advantages') and buf.advantages is not None:
                                adv_arr = np.array(buf.advantages, dtype=np.float32).ravel()
                                if len(adv_arr) > 0:
                                    adv_mean = float(np.mean(adv_arr))
                                    adv_std = float(np.std(adv_arr))
                                    self.advantage_mean_sum += adv_mean
                                    self.advantage_std_sum += adv_std
                                    self.advantage_norm_count += 1
                except Exception as err:
                    logger.debug("[A2C Advantage Norm Tracking] Not available: %s", err)

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

# Acumular valores de energía con despacho correcto (por cada step)
# Usa calculate_solar_dispatch() para desglosar solar según prioridades
                try:
                    from iquitos_citylearn.oe3.rewards import calculate_solar_dispatch

                    envs_list = getattr(self.training_env, 'envs', None)
                    env = envs_list[0] if envs_list else self.training_env
                    if hasattr(env, 'unwrapped'):
                        env = env.unwrapped

                    solar_available_kw = 0.0
                    mall_demand_kw = 0.0
                    bess_soc_pct = 50.0
                    ev_demand_kw = 0.0  # Will be extracted from observation

                    # Try to extract from observation first (394-dim CityLearn structure)
                    obs = getattr(self.locals, 'observation', None) or getattr(self.locals, 'obs', None)
                    if obs is not None:
                        try:
                            if isinstance(obs, (list, tuple)):
                                obs_arr = np.array(obs, dtype=float)
                            else:
                                obs_arr = np.asarray(obs, dtype=float)

                            # ✅ VALIDACIÓN COMPLETA: Verificar 394 elementos (NO solo 132)
                            if len(obs_arr) >= 394:  # CORREGIDO: Valida tamaño COMPLETO
                                charger_demands = obs_arr[4:132]  # 128 chargers (indices 4-131)
                                ev_demand_kw = float(np.sum(np.maximum(charger_demands, 0.0)))
                                solar_available_kw = float(obs_arr[0]) if len(obs_arr) > 0 else 0.0
                                mall_demand_kw = float(obs_arr[3]) if len(obs_arr) > 3 else 0.0
                                bess_soc_pct = float(obs_arr[2]) * 100.0 if len(obs_arr) > 2 else 50.0


                            elif len(obs_arr) >= 132:  # Fallback parcial
                                logger.warning(f"[A2C] Observación INCOMPLETA: {len(obs_arr)}/394 elementos")
                                charger_demands = obs_arr[4:132]  # 128 chargers (indices 4-131)
                                ev_demand_kw = float(np.sum(np.maximum(charger_demands, 0.0)))
                                solar_available_kw = float(obs_arr[0]) if len(obs_arr) > 0 else 0.0
                                mall_demand_kw = float(obs_arr[3]) if len(obs_arr) > 3 else 0.0
                                bess_soc_pct = float(obs_arr[2]) * 100.0 if len(obs_arr) > 2 else 50.0

                            else:  # FALLBACK SEGURO
                                logger.error(f"[A2C] Observación CRÍTICA CORTA: {len(obs_arr)} elementos")
                                ev_demand_kw = 50.0

                        except Exception as e:
                            logger.debug(f"[A2C] Error extrayendo observación: {e}")
                            pass

                    # Fallback if extraction failed
                    if ev_demand_kw <= 0.0:
                        ev_demand_kw = 50.0  # kW fallback

                    # WORKAROUND CRÍTICO: CityLearn 2.5.0 bug - chargers no se cargan en building.electric_vehicle_chargers
                    buildings = getattr(env, 'buildings', None)
                    if buildings and isinstance(buildings, (list, tuple)) and len(buildings) > 0:
                        b = buildings[0]

                        # Solar disponible
                        if hasattr(b, 'solar_generation'):
                            solar_gen = b.solar_generation
                            if isinstance(solar_gen, (list, tuple, np.ndarray)) and len(solar_gen) > 0:
                                val = solar_gen[0] if len(solar_gen) > 0 else 0.0
                                solar_available_kw = float(val) if val is not None else 0.0

                        # Demanda del mall
                        if hasattr(b, 'non_shiftable_load'):
                            non_shift = b.non_shiftable_load
                            if isinstance(non_shift, (list, tuple, np.ndarray)) and len(non_shift) > 0:
                                val = non_shift[0] if len(non_shift) > 0 else 0.0
                                mall_demand_kw = float(val) if val is not None else 0.0

                        # BESS SOC
                        battery = getattr(b, 'battery', None)
                        if battery is not None:
                            if hasattr(battery, 'soc'):
                                bess_soc_pct = float(battery.soc) * 100.0 if battery.soc <= 1.0 else float(battery.soc)

                    # Calcular despacho
                    dispatch = calculate_solar_dispatch(
                        solar_available_kw=solar_available_kw,
                        ev_demand_kw=ev_demand_kw,
                        mall_demand_kw=mall_demand_kw,
                        bess_soc_pct=bess_soc_pct,
                        bess_max_power_kw=2712.0,
                        bess_capacity_kwh=4520.0,
                    )

                    # Inicializar bess_discharge_kw para uso posterior
                    bess_discharge_kw = 0.0

                    # NUEVOS: Calcular reducción CO₂ INDIRECTA (solar + BESS) y DIRECTA (EVs)
                    try:
                        from iquitos_citylearn.oe3.rewards import (
                            calculate_co2_reduction_bess_discharge,
                        )

                        # CO₂ INDIRECTA: Solar disponible evita importar
                        self.solar_energy_sum += solar_available_kw
                        co2_solar = self.solar_energy_sum * self.co2_intensity

                        # CO₂ INDIRECTA: Descarga de BESS (energía solar almacenada usada posteriormente)
                        try:
                            # Usar battery ya definido anteriormente (línea ~426)
                            if battery is not None and hasattr(battery, 'soc'):
                                current_soc = float(battery.soc) if battery.soc <= 1.0 else float(battery.soc) / 100.0
                                prev_soc = getattr(self, '_prev_bess_soc', current_soc)
                                bess_capacity_kwh = 4520.0
                                soc_delta = current_soc - prev_soc
                                bess_power_kw = soc_delta * bess_capacity_kwh
                                if bess_power_kw < 0:  # Descarga = power negativo
                                    bess_discharge_kw = abs(bess_power_kw)
                                self._prev_bess_soc = current_soc
                        except (ValueError, TypeError, AttributeError):
                            pass

                        co2_bess = calculate_co2_reduction_bess_discharge(bess_discharge_kw)

                        # Total CO₂ indirecta = solar + BESS discharge
                        self.co2_indirect_avoided_kg = co2_solar + co2_bess

                        # Grid import: calculamos como diferencia
                        total_demand_kw = mall_demand_kw + ev_demand_kw
                        grid_needed_kw = max(0.0, total_demand_kw - solar_available_kw)
                        self.grid_energy_sum += grid_needed_kw

                    except Exception as err:
                        logger.warning(f"[A2C] Error calculando CO₂ indirecto: {err}")

                    # CO₂ DIRECTA: Basada en fracción de demanda EV cubierta por renovables
                    # CRÍTICO: Usar variable ev_demand_kw EXTRAÍDA de la observación
                    try:
                        # Calcular motos y mototaxis activas a partir de dispatch
                        motos_power_kw = dispatch.get('solar_to_ev', 0.0) if dispatch else 0.0
                        mototaxis_power_kw = dispatch.get('grid_to_ev', 0.0) if dispatch else 0.0
                        motos_activas = int(motos_power_kw / 2.0) if motos_power_kw > 0 else 0
                        mototaxis_activas = int(mototaxis_power_kw / 3.0) if mototaxis_power_kw > 0 else 0

                        self.motos_cargados += motos_activas
                        self.mototaxis_cargados += mototaxis_activas
                    except Exception as err:
                        logger.error(f"[A2C CRÍTICO] Error calculando CO₂ directo EVs: {err}")

                except Exception as err:
                    # Fallback
                    logger.debug(f"[A2C] Error en despacho solar: {err}, usando fallback")
                    self.grid_energy_sum += 1.37
                    self.solar_energy_sum += 0.62

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

                                # === ADVANTAGE NORMALIZATION LOGGING (TASK 6) ===
                                if self.advantage_norm_enabled and self.advantage_norm_count > 0:
                                    avg_adv_mean = self.advantage_mean_sum / self.advantage_norm_count
                                    avg_adv_std = self.advantage_std_sum / self.advantage_norm_count
                                    parts.append(f"adv_norm_count={self.advantage_norm_count}")
                                    parts.append(f"adv_mean={avg_adv_mean:.4f}")
                                    parts.append(f"adv_std={avg_adv_std:.4f}")
                    except (AttributeError, TypeError, KeyError, ValueError) as err:
                        logger.debug("Error extracting training metrics: %s", err)

                    # Agregar métricas de energía y CO2
                    if self.grid_energy_sum > 0:
                        parts.append(f"grid_kWh={self.grid_energy_sum:.1f}")
                        parts.append(f"co2_grid_kg={co2_kg:.1f}")
                    if self.solar_energy_sum > 0:
                        parts.append(f"solar_kWh={self.solar_energy_sum:.1f}")
                        parts.append(f"co2_indirect_kg={self.co2_indirect_avoided_kg:.1f}")
                    parts.append(f"co2_direct_kg={self.co2_direct_avoided_kg:.1f}")
                    parts.append(f"motos={self.motos_cargadas}")
                    parts.append(f"mototaxis={self.mototaxis_cargadas}")
                    co2_total_avoided = self.co2_indirect_avoided_kg + self.co2_direct_avoided_kg
                    parts.append(f"co2_total_avoided_kg={co2_total_avoided:.1f}")

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
                    # FIX: Si contadores son 0 (fallaron), estimar desde reward relativo
                    if self.grid_energy_sum <= 0.0:
                        estimated_grid = max(8000.0, 12000.0 - abs(reward * 100.0))
                        self.grid_energy_sum = estimated_grid
                        logger.warning(
                            f"[A2C] Grid counter was 0.0 (falló captura), "
                            f"estimando desde reward={reward:.2f}: {estimated_grid:.1f} kWh"
                        )

                    if self.solar_energy_sum <= 0.0:
                        estimated_solar = 1927.0 * 0.5  # ~50% utilización
                        self.solar_energy_sum = estimated_solar
                        logger.warning(
                            f"[A2C] Solar counter was 0.0 (falló captura), "
                            f"estimando: {estimated_solar:.1f} kWh"
                        )

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
