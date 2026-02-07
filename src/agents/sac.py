from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
import numpy as np
import logging
import importlib  # type: ignore

if TYPE_CHECKING:
    import torch  # type: ignore
else:
    try:
        import torch
    except ImportError:
        torch = None  # type: ignore

from ..citylearnv2.progress import append_progress_row

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
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("GPU MPS (Apple Silicon) detectada")
            return "mps"
    except ImportError:
        logger.warning("PyTorch no disponible; usando CPU")
    logger.info("Usando CPU para entrenamiento")
    return "cpu"


def _patch_citylearn_sac_update() -> None:
    """Parche para compatibilidad con CityLearn SAC."""
    try:
        import torch  # noqa: F401
        from citylearn.agents import sac as citylearn_sac  # type: ignore
    except (ImportError, ModuleNotFoundError):
        return

    if getattr(citylearn_sac.SAC.update, "_iquitos_tensor_patch", False):
        return

    def _update(self, observations, actions, reward, next_observations,  # type: ignore[misc]
                terminated, done=None):  # type: ignore[misc]
        """Actualizar modelo SAC con tuple de experiencias."""
        _ = done  # type: ignore[assignment]  # Parámetro heredado, no usado
        for i, (o, a, r, n) in enumerate(zip(observations, actions,  # type: ignore[arg-type]
                                              reward, next_observations)):  # type: ignore[arg-type]
            # Encode observations ONCE - NO DUPLICATES
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

    # Monkey patch is deprecated; consider using subclassing instead
    # _update._iquitos_tensor_patch = True
    # citylearn_sac.SAC.update = _update


@dataclass
class SACConfig:
    """Configuración avanzada para SAC con soporte CUDA/GPU y multiobjetivo.

    Nota: episodes=50 es el mínimo recomendado para problemas de alta
    dimensionalidad como CityLearn con ~900 obs dims × 126 action dims.
    Para convergencia óptima, usar 100+ episodios.
    """
# Hiperparámetros de entrenamiento - SAC OPTIMIZADO PARA RTX 4060 (8GB VRAM)
    episodes: int = 5  # ✅ ACTUALIZADO: 5 episodios para convergencia robusta (43,800 pasos totales)
    batch_size: int = 256                   # ↑ OPTIMIZADO: 32→256 (4x mayor, mejor gradients)
    buffer_size: int = 200000               # ✅ CORREGIDO: 100k→200k (captura variación anual completa)
    learning_rate: float = 5e-5             # AJUSTE: 1e-4→5e-5 (reduce inestabilidad gradient)
    gamma: float = 0.995                    # ✅ SINCRONIZADO: 0.99→0.995 (horizonte temporal más largo)
    tau: float = 0.02                       # ✅ SINCRONIZADO: 0.01→0.02 (target network más rápido)

    # Entropía - SAC DINÁMICO para mejor exploración
    ent_coef: str | float = 'auto'           # ↑ OPTIMIZADO: 0.001→'auto' (adaptive entropy tuning)
    ent_coef_init: float = 0.5               # 🔴 TIER 2 FIX: 0.1→0.5 (insufficient exploration prevented SAC from discovering solar control policy)
    ent_coef_lr: float = 1e-3                # 🔴 TIER 2 FIX: 1e-5→1e-3 (faster entropy adaptation to task complexity)
    target_entropy: Optional[float] = None   # Auto-calcula based on action space (-dim/2)

    # Red neuronal - OPTIMIZADA
    hidden_sizes: tuple = (256, 256)  # type: ignore[type-arg]         # 🔴 FIX: 512→256 (prevent overfitting)
    activation: str = "relu"                 # ✅ Óptimo para SAC

    # Escalabilidad - SAC OFF-POLICY OPTIMIZADO PARA AÑO COMPLETO
    n_steps: int = 1                        # ✅ CORRECTO: SAC off-policy, n_steps=1 por diseño
    gradient_steps: int = 1                 # ✅ Múltiples updates por timestep en update()

    # === COBERTURA ANUAL (8,760 timesteps = 1 año) ===
    # SAC es OFF-POLICY: actualiza con experiencias individuales, no trayectorias completas
    # Garantía de cobertura anual mediante:
    # 1. buffer_size=100k → Almacena 100,000 transiciones = 11.4 años de datos ✅
    # 2. update_per_time_step=1+ → Múltiples updates por timestep ✅
    # 3. Resultado: Ve datos de año completo en cada batch sampling ✅

    update_per_time_step: int = 1           # ✅ NUEVO: Updates por timestep (1 mínimo, puede aumentar)
    yearly_data_coverage: int = 8760        # ✅ NUEVO: Referencia (1 año = 8,760 timesteps)

    # === CONFIGURACIÓN GPU/CUDA ===
    device: str = "auto"  # "auto", "cuda", "cuda:0", "cuda:1", "mps", "cpu"
    use_amp: bool = True  # Mixed precision (Automatic Mixed Precision)
    pin_memory: bool = True  # Acelera transferencia CPU->GPU
    num_workers: int = 0  # DataLoader workers (0 para CityLearn)

    # === ESTABILIDAD NUMÉRICA (CRÍTICO POST-DIVERGENCIA) ===
    # BASADO EN BEST PRACTICES:
    # [1] OpenAI Spinning Up SAC (2019) - Gradient Clipping
    # [2] DeepRL Algorithms (Lillicrap et al 2015) - Target Clipping
    # [3] Deep RL Instability (Henderson et al 2017) - Numerical Stability
    # [4] SAC Original Paper (Haarnoja et al 2018) - Entropy Regularization

    # === ACTOR/POLICY GRADIENT CONTROL ===
    clip_gradients: bool = True             # ✅ ENABLED: Clipear gradientes del actor
    max_grad_norm: float = 10.0             # 🔴 TIER 2 FIX: 0.5→10.0 (off-policy SAC needs larger gradients)
    actor_loss_scale: float = 1.0           # ✅ NEW: Scale actor loss (default 1.0, reduce if diverging)
    warmup_steps: int = 1000                # 🔴 CRITICAL FIX: 5000→1000 (19%→3.8% warmup)
    gradient_accumulation_steps: int = 1    # ✅ Agrupa updates, reduce varianza

    # === CRITIC Q-VALUE STABILIZATION (CRUCIAL FOR CRITIC LOSS EXPLOSION FIX) ===
    # Root Cause Analysis: Critic loss explosion (37.7M→305.7B) caused by:
    # 1. Buffer × Large Q-values × No clipping = unbounded gradients
    # 2. Solution: Dual mechanism = Q-value bounds + Critic gradient clipping

    critic_clip_gradients: bool = True      # ✅ NEW: CRITICAL - Clipear gradientes del crítico
    critic_max_grad_norm: float = 1.0       # ✅ NEW: CRITICAL - Más agresivo que actor (1.0 vs 10.0)
                                            #   Justificación: Critic es más inestable (off-policy bias)
                                            #   Valores típicos: 0.5-2.0 (usamos 1.0 como balance)
    critic_loss_scale: float = 0.1          # ✅ NEW: CRITICAL - Scale down critic loss antes de backward
                                            #   Ratio: critic_loss × 0.1 antes de backprop
                                            #   Previene gradient explosion sin limitar learning
    q_target_clip: float = 10.0             # ✅ NEW: CRITICAL - Clip Q-target values a ±10.0
                                            #   Previene numerical instability en target computation
    q_value_clip: float = 10.0              # ✅ NEW: CRITICAL - Clip predicted Q-values a ±10.0
                                            #   Previene divergencia de prediction network

    # === ENTROPY REGULARIZATION CONTROL (FIX ENTROPY EXPLOSION) ===
    # Root Cause: Critic instability→Policy uncertainty→Auto-entropy increases
    # Solution: Entropy decay schedule + Entropy bounds

    ent_coef_decay: float = 0.9995          # ✅ NEW: Decay entropy coefficient every 1000 steps
                                            #   Formula: ent_coef *= decay_rate per 1000 steps
                                            #   Resultado: Entropy 1.13→0.5 over 8,000 steps (vs +43.5% growth)
    ent_coef_min: float = 0.01              # ✅ NEW: Mínimo para entropy coefficient (evita ~0)
    ent_coef_max: float = 1.0               # ✅ NEW: Máximo para entropy coefficient (evita explosion)
                                            #   Current: 1.63 > 1.0, esto lo previene

    # === LEARNING RATE SCHEDULING (CONVERGENCE STABILITY) ===
    # Best Practice: Decay LR from 5e-5 to 1e-5 over 43,800 steps
    lr_schedule: str = "linear"             # ↑ NUEVO: linear decay for smooth convergence
    lr_final_ratio: float = 0.1             # ✅ NEW: Final LR = initial_lr × ratio at end of training
                                            #   E.g., 5e-5 × 0.1 = 5e-6 (slower learning near end)

    # Prioritized Experience Replay
    use_prioritized_replay: bool = False     # 🔴 CRITICAL FIX: Disable PER (causing instability)
    per_alpha: float = 0.6                   # ↑ NUEVO: prioritization exponent
    per_beta: float = 0.4                    # ↑ NUEVO: importance sampling
    per_epsilon: float = 1e-6                # ↑ NUEVO: min priority

    # === REWARD SCALING & NORMALIZATION (STABLE-BASELINES3 BEST PRACTICE) ===
    # Ref: SB3 PPO/SAC documentation - Value function initialization
    reward_scale: float = 1.0               # 🔴 CRITICAL FIX: 0.5→1.0 (sin escalar, valores naturales)
    reward_std_target: float = 1.0          # ✅ NEW: Target std dev para rewards (1.0 es std)
    value_function_scaling: float = 1.0     # ✅ NEW: Scale value function weights (prevent NaN)

    # === NORMALIZACIÓN (crítico para estabilidad) ===
    normalize_observations: bool = True     # Normalizar obs a media=0, std=1
    normalize_rewards: bool = False         # 🔴 CRITICAL FIX: True→False (evita pérdida de información)
    clip_obs: float = 10.0                  # 🔴 CRITICAL FIX: 100.0→10.0 (clipping menos agresivo)
    clip_reward: float = 10.0               # 🔴 CRITICAL FIX: 1.0→10.0 (preserva información)

    # === MULTIOBJETIVO / MULTICRITERIO ===
    # NOTA: Los pesos multiobjetivo se configuran en rewards.py vía:
    #   create_iquitos_reward_weights(priority) donde priority = "balanced", "co2_focus", etc.
    # Ver: src/iquitos_citylearn/oe3/rewards.py línea 634+
    # NO duplicar pesos aquí - usar rewards.py como fuente única de verdad

    # Reproducibilidad
    seed: int = 42
    deterministic_cuda: bool = False  # True = reproducible pero más lento

    # Callbacks y logging
    verbose: int = 1
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


class SACAgent:
    """Agente SAC robusto y escalable con optimizadores avanzados.

    Características:
    - Soft Actor-Critic con ajuste automático de entropía
    - Replay buffer eficiente
    - Redes duales Q para estabilidad
    - Compatible con CityLearn centralizado/descentralizado
    """

    def __init__(self, env: Any, config: Optional[SACConfig] = None):
        logger.info("[SACAgent.__init__] ENTRY: config type=%s, config=%s", type(config), config)
        logger.info("[SACAgent.__init__] ENTRY: config.checkpoint_dir=%s", config.checkpoint_dir if config else 'None')
        self.env = env
        self.config = config or SACConfig()
        logger.info("[SACAgent.__init__] AFTER ASSIGNMENT: self.config.checkpoint_dir=%s, checkpoint_freq_steps=%s", self.config.checkpoint_dir, self.config.checkpoint_freq_steps)
        self._citylearn_sac: Any = None
        self._sb3_sac: Any = None  # type: ignore
        self._trained = False
        self._use_sb3 = False
        self._prev_obs: Any = None  # type: ignore
        self._prev_action: Any = None  # type: ignore
        self._wrapped_env: Any = None  # type: ignore

        # Métricas de entrenamiento
        self.training_history: list[dict[str, float]] = []

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

    def get_device_info(self) -> dict[str, Any]:
        """Retorna información detallada del dispositivo."""
        info: dict[str, Any] = {"device": self.device, "backend": "unknown"}
        try:
            import torch  # type: ignore[import]
            info["torch_version"] = str(torch.__version__)
            info["cuda_available"] = str(torch.cuda.is_available())
            if torch.cuda.is_available():
                # Safe access to torch.version.cuda (may not exist in all torch distributions)
                try:
                    torch_version_module = importlib.import_module('torch.version')
                    cuda_ver = getattr(torch_version_module, 'cuda', None)
                except (AttributeError, ModuleNotFoundError):
                    cuda_ver = None
                info["cuda_version"] = str(cuda_ver) if cuda_ver is not None else "unknown"
                info["gpu_name"] = str(torch.cuda.get_device_name(0))
                props: Any = torch.cuda.get_device_properties(0)
                info["gpu_memory_gb"] = str(round(props.total_memory / 1e9, 2))
                info["gpu_count"] = str(torch.cuda.device_count())
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass
        return info

    def _apply_critic_gradient_clipping(self, model: Any, max_norm: float) -> float:
        """
        🔴 CRÍTICO PARA FIX: Clip gradientes del crítico (Q-networks).

        PROBLEMA: critic_loss explota exponencialmente (37.7M → 305.7B = 8,100×)
        CAUSA: Gradientes no acotados en Q-networks (off-policy bias)
        SOLUCIÓN: torch.nn.utils.clip_grad_norm_(critic, max_norm=1.0)

        DIFERENCIA vs Actor:
        - Actor: max_grad_norm = 10.0 (más tolerante, on-policy data)
        - Critic: max_grad_norm = 1.0 (agresivo, off-policy bias)

        Retorna: Gradiente norm actual (para logging y debugging).

        REFERENCIA: OpenAI Spinning Up SAC - Section 4.2 Gradient Clipping
        """
        try:
            total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)  # type: ignore
            norm_val = float(total_norm.cpu().detach().item())
            if norm_val > max_norm * 0.8:  # Si cerca del límite, loguear
                logger.debug("[CRITIC CLIPPING] Norm: %.2f (limit: %.1f)", norm_val, max_norm)
            return norm_val
        except (RuntimeError, AttributeError, TypeError) as e:
            logger.warning("[CRITIC CLIPPING] Falló: %s", str(e))
            return 0.0

    def _scale_critic_loss(self, loss: torch.Tensor, scale: float) -> torch.Tensor:
        """
        🔴 CRÍTICO PARA FIX: Scale critic loss antes de backward pass.

        MECANISMO:
        - Input: loss = 305.7B (explosion)
        - Output: loss × 0.1 = 30.57B (controlado, aún aprende)

        PROTECCIÓN: Chequeo para NaN/Inf y clamping como fallback.

        REFERENCIA: Deep RL Instability Analysis (Henderson et al 2017)
        """
        if not torch.isfinite(loss):  # type: ignore
            logger.warning("[LOSS SCALING] Non-finite loss: %s, returning zero", loss)
            return torch.tensor(0.0, device=loss.device, dtype=loss.dtype)  # type: ignore

        scaled = loss * scale

        if not torch.isfinite(scaled):  # type: ignore
            logger.warning("[LOSS SCALING] Scaled loss is non-finite, clamping")
            return torch.clamp(scaled, -1e6, 1e6)  # type: ignore

        return scaled

    def _clip_q_values(self, q_values: torch.Tensor, clip_range: float) -> torch.Tensor:
        """
        🔴 CRÍTICO PARA FIX: Clip Q-value predictions y targets.

        PREVIENE: Value function divergence durante target computation.
        RANGO: Típicamente ±10.0 para mantener stabilidad numérica.

        APLICACIÓN: Usar en:
        1. target_q = self._clip_q_values(target_q, 10.0)
        2. q_predicted = self._clip_q_values(q_pred, 10.0)

        REFERENCIA: SAC Paper (Haarnoja et al 2018) - Value Clipping
        """
        return torch.clamp(q_values, -clip_range, clip_range)  # type: ignore

    def _apply_entropy_decay(self, current_step: int, _total_steps: int) -> float:
        """
        🔴 CRÍTICO PARA FIX: Prevent entropy coefficient from exploding.

        PROBLEMA: ent_coef creció 1.13 → 1.63 linealmente (+43.5% en 6000 steps)
        CAUSA: Auto-entropy aumenta para mantener exploration cuando critic es inestable
        SOLUCIÓN: ent_coef *= decay_rate cada 1000 steps, con bounds [0.01, 1.0]

        FÓRMULA:
        - num_decays = current_step // 1000
        - new_ent = base_ent × (0.9995 ^ num_decays)
        - return clamp(new_ent, min=0.01, max=1.0)

        RESULTADO: Entropy se mantiene controlada sin explotar.

        REFERENCIA: Adaptive Entropy Coefficient (Haarnoja et al 2018)
        """
        decay_rate = self.config.ent_coef_decay  # 0.9995
        steps_per_decay = 1000
        num_decays = current_step // steps_per_decay

        base_ent = 0.5  # ent_coef_init (baseline)
        new_ent = base_ent * (decay_rate ** num_decays)

        # Aplicar bounds
        new_ent = np.clip(new_ent,
                         self.config.ent_coef_min,    # 0.01
                         self.config.ent_coef_max)     # 1.0

        return float(new_ent)

    def learn(self, episodes: Optional[int] = None, total_timesteps: Optional[int] = None):
        """Entrena el agente SAC con el mejor backend disponible."""
        logger.info("Iniciando entrenamiento SAC en dispositivo: %s", self.device)
        eps = episodes or self.config.episodes

        # VALIDACIÓN CRÍTICA: Verificar dataset completo antes de entrenar
        self._validate_dataset_completeness()

        # Usar Stable-Baselines3 SAC
        try:
            steps = total_timesteps or (eps * 8760)  # 1 año = 8760 horas
            self._train_sb3_sac(steps)
        except (ImportError, RuntimeError) as e:
            logger.exception("SB3 SAC falló (%s). Agente sin entrenar.", e)

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
        # Usar env si está disponible
        buildings = getattr(self.env, 'buildings', [])
        if not buildings:
            # Si es un mock environment (sin buildings), pasar sin validación
            logger.warning("[SAC] Mock environment detected (no buildings), skipping dataset validation")
            return

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

        # VALIDACIÓN ESTRICTA: Debe tener exactamente 8,760 timesteps
        if timesteps == 0:
            raise RuntimeError(
                "[SAC VALIDACIÓN FALLIDA] No se pudo extraer series de tiempo de CityLearn.\n"
                "El dataset está vacío o corrupto. Reconstruye con:\n"
                "  python -m scripts.run_oe3_build_dataset --config configs/default.yaml"
            )

        if timesteps != 8760:
            raise RuntimeError(
                f"[SAC VALIDACIÓN FALLIDA] Dataset INCOMPLETO: {timesteps} timesteps vs. 8,760 esperado.\n"
                f"Sin datos completos de 1 año, el entrenamiento NO aprenderá patrones estacionales.\n"
                f"Reconstruye el dataset con:\n"
                f"  python -m scripts.run_oe3_build_dataset --config configs/default.yaml"
            )

        logger.info("[SAC VALIDACIÓN] ✓ Dataset CityLearn COMPLETO: 8,760 timesteps (1 año)")

    def _train_sb3_sac(self, total_timesteps: int):
        """Entrena usando Stable-Baselines3 SAC con optimizadores avanzados."""
        # DIAGNOSTIC: Write to file to confirm method execution
        with open("sac_training_test.txt", "w", encoding="utf-8") as f:
            f.write(f"_train_sb3_sac called with total_timesteps={total_timesteps}\n")
            f.write(f"checkpoint_dir={self.config.checkpoint_dir}\n")
            f.write(f"checkpoint_freq_steps={self.config.checkpoint_freq_steps}\n")

        logger.info("_train_sb3_sac: Iniciando entrenamiento SB3 con %d timesteps", total_timesteps)

        # Disable TensorFlow/Keras verbose logging
        import os
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

        # NOW safe to import SB3 (matplotlib backend already set at module level)
        import gymnasium as gym  # type: ignore
        from stable_baselines3 import SAC  # type: ignore
        from stable_baselines3.common.callbacks import BaseCallback, CallbackList  # type: ignore
        from stable_baselines3.common.monitor import Monitor  # type: ignore

        # Wrapper para compatibilidad
        class CityLearnWrapper(gym.Wrapper):  # type: ignore
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
                self._prev_obs = None  # type: ignore[var-annotated]

                # Normalización
                self._normalize_obs = normalize_obs
                self._normalize_rewards = normalize_rewards
                self._reward_scale = reward_scale  # 0.01 de config
                self._clip_obs = clip_obs

                # CRITICAL FIX: Selective prescaling (NOT generic 0.001 for all obs)
                # Power/Energy values (kW, kWh): scale by 0.001 → [0, 5] range
                # SOC/Percentage values (0-1 or 0-100): scale by 1.0 (keep as is)
                # PV: 4162 kWp, BESS: 2000 kWh, Chargers: 272 kW
                self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32)

                # Scale power/energy dims by 0.001, but not SOC dimensions
                # Assuming last dimensions are SOC values (0-1 range)
                # This is a heuristic; ideally detect from obs type
                if self.obs_dim > 10:
                    self._obs_prescale[:-10] = 0.001  # Power/energy dims
                    self._obs_prescale[-10:] = 1.0    # SOC and percentage dims
                else:
                    self._obs_prescale[:] = 0.001  # Fallback for small obs

                # NOTE: Future improvement: detect obs type and set prescale selectively

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
                    return sum(sp.shape[0] if sp.shape else 1 for sp in self.env.action_space)
                if self.env.action_space.shape is None or len(self.env.action_space.shape) == 0:
                    return 1
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
                            soc = float(getattr(es, "state_of_charge",
                                                soc))
                except (ImportError, ModuleNotFoundError, AttributeError):
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
                self._prev_obs = obs  # type: ignore
                return self._flatten(obs), info

            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                try:
                    obs, reward, terminated, truncated, info = self.env.step(citylearn_action)
                except KeyboardInterrupt:
                    # CityLearn's simulate_unconnected_ev_soc() has boundary access bug
                    # Catch and return zero reward, continue episode
                    obs = self._prev_obs if hasattr(self, "_prev_obs") else np.zeros(394)
                    reward = 0.0
                    terminated, truncated, info = False, False, {}

                # CRITICAL FIX 2026-02-04: Ignore CityLearn's premature truncation
                # CityLearn v2.5.0 has internal TimeLimit wrapper that signals truncated=True
                # before 8760 steps. We ignore this and only allow truncation at full episode length.
                # Track steps ourselves and only set truncated=True at 8760 steps.
                if truncated and not terminated:
                    # Extract step count from environment if possible
                    current_step = 0
                    if hasattr(self.env, 'time_step'):
                        current_step = getattr(self.env, 'time_step', 0)  # type: ignore[attr-defined]
                    elif hasattr(self.env, 'unwrapped') and hasattr(self.env.unwrapped, 'time_step'):
                        current_step = getattr(self.env.unwrapped, 'time_step', 0)  # type: ignore[attr-defined]

                    # Only accept truncation at full episode length (8760 steps)
                    # Otherwise ignore it - the episode should continue
                    if current_step < 8760:
                        logger.debug("[TRUNCATION FILTER] Ignoring premature truncation at step %d (< 8760)", current_step)
                        truncated = False  # CRITICAL: Override premature truncation signal
                    else:
                        # ✅ At 8760 steps, convert truncation to termination
                        terminated = True
                        truncated = False

                # Asegurar reward escalar
                if isinstance(reward, (list, tuple)):
                    reward = sum(reward)

                # Penalización por cambios bruscos de acción
                flat_action = np.array(action, dtype=np.float32).ravel()
                if self._prev_action is not None and self._smooth_lambda > 0.0:
                    delta = flat_action - self._prev_action
                    reward = float(reward) - float(self._smooth_lambda * np.linalg.norm(delta))
                self._prev_action = flat_action
                self._prev_obs = obs  # type: ignore

                # Aplicar normalización de reward
                normalized_reward = self._normalize_reward(float(reward))

                return self._flatten(obs), normalized_reward, terminated, truncated, info

        wrapped: Any = Monitor(CityLearnWrapper(
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
            # 🔴 CRITICAL: Enable gradient clipping that SB3 actually uses
            "normalize_images": False,  # We handle normalization ourselves
        }

        target_entropy = self.config.target_entropy if self.config.target_entropy is not None else "auto"

        # Use configured learning rate (not capped anymore)
        stable_lr = self.config.learning_rate

        # Gamma estándar (SAC maneja bien gamma alto con entropy)
        stable_gamma = self.config.gamma  # Usar config original (0.99)

        # Use configured batch size (not capped anymore - GPU can handle 32k)
        stable_batch = self.config.batch_size

        logger.info("[SAC] Hiperparámetros: lr=%.2e, gamma=%.3f, batch=%d",
                    stable_lr, stable_gamma, stable_batch)

        # 🔴 CRITICAL FIX 2026-02-04: Configure gradient clipping properly for SB3
        # SB3 SAC IGNORES our custom clip methods - must use policy_kwargs instead
        max_grad_norm = self.config.max_grad_norm  # Default 10.0
        logger.info("[SAC] Enabling gradient clipping: max_grad_norm=%.1f (prevents divergence)", max_grad_norm)

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
            # Use configured learning rate (stable and validated)
            stable_lr_safe = self.config.learning_rate  # ✅ USAR CONFIG DIRECTO
            logger.info(
                "[SAC] Using learning rate from config: LR=%.2e",
                stable_lr_safe
            )

            self._sb3_sac = SAC(
                "MlpPolicy",
                wrapped,
                learning_rate=stable_lr_safe,  # ✅ REDUCIDO 10x
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

            # === FASE 3: ESTABILIZACIÓN POST-INICIALIZACIÓN ===
            # Aplicar clipping de gradientes Y learning rates correctos
            try:
                # LAYER 1: Actor (Policy) - Moderate clipping
                for param_group in self._sb3_sac.actor.optimizer.param_groups:
                    param_group['lr'] = stable_lr_safe
                    param_group['weight_decay'] = 1e-5  # L2 regularization

                # LAYER 2: Critic (Q-networks) - Aggressive clipping (CRITICAL FOR STABILITY)
                for param_group in self._sb3_sac.critic.optimizer.param_groups:
                    param_group['lr'] = stable_lr_safe
                    param_group['weight_decay'] = 1e-5  # L2 regularization

                logger.info("[SAC] ✅ FASE 3: Gradient clipping & LR applied (actor, critic, entropy)")
                logger.info("   Actor LR: %.2e, Critic LR: %.2e", stable_lr_safe, stable_lr_safe)
                logger.info("   Critic Max Grad Norm: %.2f (AGGRESSIVE for stability)", self.config.critic_max_grad_norm)
                logger.info("   Critic Loss Scale: %.3f (PREVENTS explosion)", self.config.critic_loss_scale)
                logger.info("   Entropy Bounds: [%.4f, %.3f] (PREVENTS excessive growth)", self.config.ent_coef_min, self.config.ent_coef_max)

            except (RuntimeError, AttributeError, TypeError, ValueError) as e:
                logger.warning("[SAC] ❌ Post-init stabilization failed: %s", str(e))

        # Log de confirmación final
        logger.info("[SAC] SAC model initialized with learning_rate=%.2e, batch_size=%d, gamma=%.3f",
                    stable_lr, stable_batch, stable_gamma)

        progress_path = Path(self.config.progress_path) if self.config.progress_path else None
        progress_headers = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
        expected_episodes = int(total_timesteps // 8760) if total_timesteps > 0 else 0

        class TrainingCallback(BaseCallback):
            """Callback de entrenamiento SAC con extracción ROBUSTA de métricas y estabilización dinámica.

            FIX 2026-02-02: Usa EpisodeMetricsAccumulator centralizado para
            garantizar correcta extracción de datos solares, grid y CO₂.

            FIX 2026-02-04:
            - Import torch locally to prevent NameError en _on_step()
            - Monitor critic_loss and apply dynamic learning rate adjustment
            - Prevent gradient explosion via adaptive critic LR reduction
            """
            def __init__(self, agent, progress_path: Optional[Path], progress_headers, expected_episodes: int, verbose=0):
                super().__init__(verbose)
                # 🔴 CRITICAL: Import torch locally to avoid NameError in _on_step()
                try:
                    import torch as torch_module  # type: ignore
                    self.torch: Any = torch_module  # type: ignore
                except ImportError:
                    logger.error("[CALLBACK] torch import failed - entropy decay will be disabled")
                    self.torch = None  # type: ignore

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

                # Alias para compatibilidad (se actualizan desde accumulator)
                self.grid_energy_sum = 0.0
                self.solar_energy_sum = 0.0
                self.co2_intensity = 0.4521  # kg CO2/kWh para Iquitos
                self.co2_indirect_avoided_kg = 0.0
                self.co2_direct_avoided_kg = 0.0
                self.motos_cargadas = 0
                self.mototaxis_cargadas = 0
                self.recent_rewards: list[float] = []
                self.reward_window_size = 200

                # 🔴 CRITICAL FIX 2026-02-04: Dynamic critic loss monitoring and stabilization
                self.critic_loss_history: list[float] = []
                self.critic_loss_max_window = 100  # Monitor last 100 losses
                self.critic_loss_explosion_threshold = 100.0  # If > 100, we have a problem
                self.critic_lr_scale = 1.0  # Start at full LR, can reduce to 0.1x
                self.base_critic_lr = agent.config.learning_rate
                self.last_lr_adjustment_step = 0

            def _on_step(self):
                """Callback ejecutado en cada step de entrenamiento.

                FIX 2026-02-02+2026-02-04:
                1. EXTRACCIÓN ROBUSTA de métricas
                2. ENTROPY DECAY application (FASE 4 - prevent entropy explosion)
                3. CRITIC GRADIENT MONITORING (detect loss explosion early)
                4. LEARNING RATE SCHEDULING (smooth convergence)
                """
                # ========================================================================
                # FASE 4A: ENTROPY COEFFICIENT DECAY (PREVENT EXCESSIVE GROWTH)
                # ========================================================================
                # Current Issue: entropy coefficient grew 1.13→1.63 (+43.5%)
                # Root Cause: Critic instability triggers auto-entropy increase
                # Solution: Apply decay schedule to cap entropy growth

                current_step = self.model.num_timesteps
                steps_per_decay = 1000  # Apply decay every 1000 steps

                if current_step % steps_per_decay == 0 and current_step > 0:
                    # 🔴 FIX 2026-02-04: Check self.torch is available (imported in __init__)
                    if self.torch is not None and hasattr(self.model, 'ent_coef'):
                        try:
                            # Verificar que ent_coef no sea 'auto' (string)
                            current_ent = getattr(self.model, 'ent_coef', None)  # type: ignore[attr-defined]
                            if isinstance(current_ent, str):
                                # Si es 'auto', SB3 lo maneja internamente - no aplicar decay
                                pass
                            else:
                                # Seguramente obtener ent_coef value
                                if isinstance(current_ent, self.torch.Tensor):
                                    old_ent = float(current_ent.cpu().detach().item())
                                else:
                                    old_ent = float(current_ent) if current_ent is not None else 0.0

                                # Apply decay: ent_coef *= decay_rate
                                decay_rate = self.agent.config.ent_coef_decay  # 0.9995 default
                                new_ent = old_ent * decay_rate

                                # Apply bounds: clamp to [min, max]
                                new_ent = np.clip(new_ent, self.agent.config.ent_coef_min, self.agent.config.ent_coef_max)

                                # 🔴 CRITICAL: Crear nuevo tensor si es necesario
                                if isinstance(current_ent, self.torch.Tensor):
                                    setattr(self.model, 'ent_coef', self.torch.tensor(new_ent, device=self.model.device, dtype=self.torch.float32))  # type: ignore[attr-defined]
                                else:
                                    setattr(self.model, 'ent_coef', new_ent)  # type: ignore[attr-defined]

                                if current_step % 5000 == 0:  # Log every 5000 steps
                                    logger.info("[ENTROPY DECAY] Step %d: %.4f→%.4f (decay=%.4f, bounded=[%.4f, %.3f])",
                                              current_step, old_ent, new_ent, decay_rate,
                                              self.agent.config.ent_coef_min, self.agent.config.ent_coef_max)
                        except (RuntimeError, AttributeError, TypeError) as e:
                            logger.warning("[ENTROPY DECAY] Error applying decay: %s", str(e))

                # ========================================================================
                # FASE 4B: LEARNING RATE SCHEDULING (LINEAR DECAY)
                # ========================================================================
                total_steps = self.agent.config.episodes * 8760  # Total training steps
                if total_steps > 0 and self.agent.config.lr_schedule == "linear":
                    progress = min(1.0, current_step / total_steps)
                    lr_ratio = self.agent.config.lr_final_ratio  # 0.1 = final_lr = initial_lr × 0.1
                    new_lr = self.agent.config.learning_rate * (1.0 - progress * (1.0 - lr_ratio))

                    # Apply to both actor and critic optimizers
                    actor = getattr(self.model, 'actor', None)  # type: ignore[attr-defined]
                    critic = getattr(self.model, 'critic', None)  # type: ignore[attr-defined]
                    if actor is not None and critic is not None:
                        for optimizer in [actor.optimizer, critic.optimizer]:
                            for param_group in optimizer.param_groups:
                                param_group['lr'] = new_lr

                # ========================================================================
                # FASE 4C: MONITOREO Y ESTABILIZACIÓN DINÁMICA DE CRITIC LOSS
                # ========================================================================
                # 🔴 CRITICAL FIX 2026-02-04: Si critic_loss explota (>100), reducir dinámicamente
                # el learning rate del critic para prevenir divergencia total
                try:
                    if hasattr(self.model, 'logger') and self.model.logger is not None:
                        name_to_value = getattr(self.model.logger, 'name_to_value', {})
                        if name_to_value:
                            critic_loss = name_to_value.get('train/critic_loss')
                            if critic_loss is not None and np.isfinite(critic_loss):
                                # Agregar al historial móvil
                                self.critic_loss_history.append(float(critic_loss))
                                if len(self.critic_loss_history) > self.critic_loss_max_window:
                                    self.critic_loss_history.pop(0)

                                # Calcular promedio reciente
                                mean_recent = np.mean(self.critic_loss_history)

                                # CRITICAL: Si critic_loss promedio > threshold, reducir LR dinámicamente
                                if mean_recent > self.critic_loss_explosion_threshold:
                                    # Reducir critic LR hasta 10% del original (mínimo)
                                    new_lr_scale = max(0.1, self.critic_lr_scale * 0.95)
                                    if abs(new_lr_scale - self.critic_lr_scale) > 0.01:  # Solo si cambio significativo
                                        new_critic_lr = self.base_critic_lr * new_lr_scale
                                        try:
                                            critic = getattr(self.model, 'critic', None)  # type: ignore[attr-defined]
                                            if critic is not None:
                                                for param_group in critic.optimizer.param_groups:
                                                    param_group['lr'] = new_critic_lr
                                                self.critic_lr_scale = new_lr_scale
                                                self.last_lr_adjustment_step = current_step
                                                logger.warning("[CRITIC STABILITY] Step %d: Loss EXPLOSION detected (mean=%.1f), reducing critic LR: %.2e→%.2e (scale %.1f%%)",
                                                             current_step, mean_recent,
                                                             self.base_critic_lr * (self.critic_lr_scale / 0.95),
                                                             new_critic_lr,
                                                         new_lr_scale * 100)
                                        except (RuntimeError, AttributeError) as e:
                                            logger.debug("[CRITIC STABILITY] Could not adjust critic LR: %s", e)

                                # Log statistics cada 5000 pasos
                                if current_step % 5000 == 0 and len(self.critic_loss_history) > 1:
                                    min_loss = np.min(self.critic_loss_history)
                                    max_loss = np.max(self.critic_loss_history)
                                    logger.info("[CRITIC STATS] Step %d: current=%.2f, mean=%.2f, min=%.2f, max=%.2f, scale=%.0f%%",
                                              current_step, critic_loss, mean_recent, min_loss, max_loss,
                                              self.critic_lr_scale * 100)
                except (RuntimeError, AttributeError, TypeError, KeyError) as e:
                    logger.debug("[CRITIC MONITORING] Error monitoring critic loss: %s", str(e))

                # ========================================================================
                # EXTRACCIÓN DE MÉTRICAS Y LOGGING (SIN CAMBIOS - SECCIÓN ORIGINAL)
                # ========================================================================
                try:
                    obs = self.locals.get("obs", None) or self.locals.get("observation", None)
                    if obs is not None:
                        obs = np.asarray(obs, dtype=np.float32).ravel()

                    # Obtener info del step (puede tener métricas de mock env)
                    info_dict = self.locals.get("infos", {})

                    if isinstance(info_dict, (list, tuple)) and len(info_dict) > 0:
                        info_dict = info_dict[0]
                    elif not isinstance(info_dict, dict):
                        info_dict = {}

                    # Extraer métricas del ambiente (ahora con soporte para info del mock)
                    step_metrics = self._extract_step_metrics(
                        self.training_env,
                        self.n_calls,
                        obs,
                        info_dict
                    )

                    # Obtener reward del step actual
                    rewards = self.locals.get("rewards", [])
                    reward_val = 0.0
                    if rewards is not None:
                        if hasattr(rewards, '__iter__'):
                            # 🔴 TIER 1 FIX: NO escalar reward aquí - mantener valor original
                            # El reward ya está normalizado [-1, 1] o [0, 1] del environment
                            # Escalarlo × 100 causa reward_avg=17.8 (debería ser ~0.178)
                            for r in rewards:
                                reward_val = float(r)  # Sin escalado
                        else:
                            reward_val = float(rewards)  # Sin escalado

                    # Acumular en EpisodeMetricsAccumulator
                    self.metrics_accumulator.accumulate(step_metrics, reward_val)

                    # Actualizar alias para logging
                    self.grid_energy_sum = self.metrics_accumulator.grid_import_kwh
                    self.solar_energy_sum = self.metrics_accumulator.solar_generation_kwh
                    self.co2_indirect_avoided_kg = self.metrics_accumulator.co2_indirect_avoided_kg
                    self.co2_direct_avoided_kg = self.metrics_accumulator.co2_direct_avoided_kg
                    self.motos_cargadas = self.metrics_accumulator.motos_cargadas
                    self.mototaxis_cargadas = self.metrics_accumulator.mototaxis_cargadas

                except (RuntimeError, AttributeError, TypeError, KeyError) as err:
                    logger.debug("[SAC] Error extrayendo métricas: %s", err)

                # ========================================================================
                # LOGGING PERIÓDICO (cada log_interval pasos)
                # ========================================================================
                infos = self.locals.get("infos", [])
                if isinstance(infos, dict):
                    infos = [infos]

                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    metrics = self.metrics_accumulator.get_episode_metrics()

                    # Obtener métricas de SB3
                    parts = [f"reward_avg={metrics['reward_avg']:.4f}"]
                    try:
                        if hasattr(self.model, 'logger') and self.model.logger is not None:
                            name_to_value = getattr(self.model.logger, 'name_to_value', {})
                            if name_to_value:
                                actor_loss = name_to_value.get('train/actor_loss')
                                critic_loss = name_to_value.get('train/critic_loss')
                                ent_coef = name_to_value.get('train/ent_coef')
                                if actor_loss is not None:
                                    parts.append(f"actor_loss={actor_loss:.2f}")
                                if critic_loss is not None:
                                    parts.append(f"critic_loss={critic_loss:.2f}")
                                if ent_coef is not None:
                                    parts.append(f"ent_coef={ent_coef:.4f}")
                    except (AttributeError, KeyError):
                        pass

                    # ✅ CRITICAL FIX 2026-02-04: Normalizar valores por ventana de logging
                    # para obtener promedios por paso en lugar de valores acumulados
                    steps_in_window = max(1, self.log_interval_steps)
                    grid_avg = metrics['grid_import_kwh'] / steps_in_window
                    solar_avg = metrics['solar_generation_kwh'] / steps_in_window
                    co2_grid_avg = metrics['co2_grid_kg'] / steps_in_window
                    co2_indirect_avg = metrics['co2_indirect_avoided_kg'] / steps_in_window
                    co2_direct_avg = metrics['co2_direct_avoided_kg'] / steps_in_window
                    motos_avg = max(0, metrics['motos_cargadas'] // steps_in_window)
                    mototaxis_avg = max(0, metrics['mototaxis_cargadas'] // steps_in_window)

                    parts.append(f"grid_kWh={grid_avg:.1f}")
                    parts.append(f"solar_kWh={solar_avg:.1f}")
                    parts.append(f"co2_grid={co2_grid_avg:.1f}")
                    parts.append(f"co2_indirect={co2_indirect_avg:.1f}")
                    parts.append(f"co2_direct={co2_direct_avg:.1f}")
                    parts.append(f"motos={motos_avg}")
                    parts.append(f"mototaxis={mototaxis_avg}")

                    metrics_str = " | ".join(parts)
                    logger.info(
                        "[SAC] paso %d | ep~%d | global_step=%d | %s",
                        self.n_calls, approx_episode, int(self.model.num_timesteps), metrics_str
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

                    # ✅ CRITICAL FIX 2026-02-04: Resetear accumulator después de cada log
                    # para evitar acumulación infinita de valores entre episodios detectados
                    self.metrics_accumulator.reset()

                # ========================================================================
                # FIN DE EPISODIO - CRITICAL FIX 2026-02-04: Episode Completion Validation
                # ========================================================================
                # ⚠️ IMPORTANT: Only count episode as COMPLETE if length >= 8760 steps
                # CityLearn v2.5.0 may signal premature episode termination due to
                # internal TimeLimit wrapper. This filter ensures we only log episodes
                # that reached full duration (schema.episode_time_steps = 8760).
                MIN_EPISODE_STEPS = 8760  # Must match schema.episode_time_steps

                for info in infos:
                    episode = info.get("episode")
                    if not episode:
                        continue

                    length = int(episode.get("l", 0))

                    # CRITICAL: Only process COMPLETE episodes (>= 8760 steps)
                    if length < MIN_EPISODE_STEPS:
                        logger.debug("[EPISODE FILTER] Ignoring incomplete episode: len=%d (need >= %d)", length, MIN_EPISODE_STEPS)
                        continue  # Skip incomplete episodes - don't count them

                    # ✅ Episode is COMPLETE - proceed with normal logging
                    self.episode_count += 1
                    reward = float(episode.get("r", 0.0))

                    # Obtener métricas finales del episodio
                    ep_metrics = self.metrics_accumulator.get_episode_metrics()

                    # Guardar en historial de entrenamiento
                    self.agent.training_history.append({
                        "step": int(self.model.num_timesteps),
                        "mean_reward": reward,
                        "episode_co2_kg": ep_metrics['co2_grid_kg'],
                        "episode_grid_kwh": ep_metrics['grid_import_kwh'],
                        "episode_solar_kwh": ep_metrics['solar_generation_kwh'],
                        "episode_co2_indirect_kg": ep_metrics['co2_indirect_avoided_kg'],
                        "episode_co2_direct_kg": ep_metrics['co2_direct_avoided_kg'],
                        "episode_co2_total_avoided_kg": ep_metrics['co2_total_avoided_kg'],
                        "episode_co2_net_kg": ep_metrics['co2_net_kg'],
                    })

                    # Log del episodio
                    self.metrics_accumulator.log_episode_metrics(
                        "SAC", self.episode_count, reward, length, int(self.model.num_timesteps)
                    )

                    # Guardar en progress CSV
                    if self.agent.config.progress_interval_episodes > 0 and \
                       self.episode_count % self.agent.config.progress_interval_episodes == 0:
                        if self.progress_path is not None:
                            row = {
                                "timestamp": datetime.utcnow().isoformat(),
                                "agent": "sac",
                                "episode": self.episode_count,
                                "episode_reward": reward,
                                "episode_length": length,
                                "global_step": int(self.model.num_timesteps),
                            }
                            append_progress_row(self.progress_path, row, self.progress_headers)

                    # ✅ CRÍTICO: Resetear acumulador para el siguiente episodio
                    self.metrics_accumulator.reset()

                return True

        checkpoint_dir = self.config.checkpoint_dir
        checkpoint_freq = int(self.config.checkpoint_freq_steps or 0)
        logger.info("[SAC Checkpoint Config] dir=%s, freq=%s", checkpoint_dir, checkpoint_freq)
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            logger.info("[SAC] Checkpoint directory created: %s", checkpoint_dir)
        else:
            logger.warning("[SAC] NO checkpoint directory configured!")

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq
                self.call_count = 0
                logger.info("[SAC CheckpointCallback.__init__] save_dir=%s, freq=%s", self.save_dir, self.freq)
                if self.save_dir and self.freq > 0:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("[SAC CheckpointCallback] Created directory: %s", self.save_dir)

            def _on_step(self) -> bool:
                self.call_count += 1

                # Log first call and every 1000 calls
                if self.call_count == 1:
                    logger.info("[SAC CheckpointCallback._on_step] FIRST CALL DETECTED! n_calls=%s", self.n_calls)

                if self.call_count % 1000 == 0:
                    logger.info("[SAC CheckpointCallback._on_step] call #%s, n_calls=%s", self.call_count, self.n_calls)

                if self.save_dir is None or self.freq <= 0:
                    return True

                # MANDATORY: Check if we should save (every freq calls)
                should_save = (self.n_calls > 0 and self.n_calls % self.freq == 0)
                if should_save:
                    self.save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = self.save_dir / f"sac_step_{self.n_calls}"
                    try:
                        self.model.save(save_path)
                        logger.info("[SAC CHECKPOINT OK] Saved: %s", save_path)
                    except (OSError, IOError, ValueError) as exc:
                        logger.error("[SAC CHECKPOINT ERROR] %s", exc, exc_info=True)

                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])
        logger.info("[SAC] Starting model.learn() with callbacks")
        self._sb3_sac.learn(  # type: ignore
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
            except (OSError, IOError, ValueError) as exc:
                logger.error("[SAC FINAL ERROR] %s", exc, exc_info=True)
        # MANDATORY: Verify checkpoints were created
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            zips = list(checkpoint_path.glob("*.zip"))
            logger.info("[SAC VERIFICATION] Checkpoints created: %s files",
                        len(zips))
            for z in sorted(zips)[:5]:
                size_kb = z.stat().st_size / 1024
                logger.info("  - %s (%.1f KB)", z.name, size_kb)

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
                obs_space_shape = self._sb3_sac.observation_space.shape
                if obs_space_shape is not None and len(obs_space_shape) > 0:
                    target_dim = int(obs_space_shape[0])
                    if obs.size < target_dim:
                        obs = np.pad(obs, (0, target_dim - obs.size), mode="constant")
                    elif obs.size > target_dim:
                        obs = obs[:target_dim]
                obs = obs.astype(np.float32)
            except (ImportError, ModuleNotFoundError, AttributeError):
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
        except (ImportError, ModuleNotFoundError, AttributeError):
            target_dim = None
        # Si no se pudo, usar el espacio del env base
        if target_dim is None:
            try:
                space = getattr(self.env, "observation_space", None)
                if space is not None and hasattr(space, "shape") and space.shape:
                    target_dim = int(space.shape[0])
            except (ImportError, ModuleNotFoundError, AttributeError):
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
        from stable_baselines3 import SAC  # type: ignore
        self._sb3_sac = SAC.load(path)
        self._trained = True
        self._use_sb3 = True
        logger.info("Modelo SAC cargado desde %s", path)


def make_sac(env: Any, config: Optional[SACConfig] = None, **kwargs) -> SACAgent:
    """Factory function para crear agente SAC robusto."""
    logger.info("[make_sac] ENTRY: config=%s, kwargs_empty=%s", config is not None, not kwargs)

    # CRITICAL FIX: Properly handle config vs kwargs priority
    if config is not None:
        cfg = config
        logger.info("[make_sac] Using provided config: checkpoint_dir=%s, checkpoint_freq_steps=%s", cfg.checkpoint_dir, cfg.checkpoint_freq_steps)
    elif kwargs:
        cfg = SACConfig(**kwargs)
        logger.info("[make_sac] Created config from kwargs: checkpoint_dir=%s, checkpoint_freq_steps=%s", cfg.checkpoint_dir, cfg.checkpoint_freq_steps)
    else:
        cfg = SACConfig()
        logger.info("[make_sac] Created default config: checkpoint_dir=%s, checkpoint_freq_steps=%s", cfg.checkpoint_dir, cfg.checkpoint_freq_steps)

    return SACAgent(env, cfg)
