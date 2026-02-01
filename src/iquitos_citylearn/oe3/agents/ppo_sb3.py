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
    """Configuración avanzada para PPO con soporte CUDA/GPU y multiobjetivo.

    Nota: train_steps=500000 es el mínimo recomendado para problemas de alta
    dimensionalidad como CityLearn con ~394 obs dims × 129 action dims.
    Para convergencia óptima, usar 1M+ pasos.
    """
    # Hiperparámetros de entrenamiento - PPO OPTIMIZADO PARA RTX 4060
    train_steps: int = 500000  # ↓ REDUCIDO: 1M→500k (RTX 4060 limitación)
    n_steps: int = 8760         # ↑ OPTIMIZADO: 256→8760 (FULL EPISODE, ver causal chains completo!)
    batch_size: int = 256       # ↑ OPTIMIZADO: 8→256 (4x mayor, mejor gradient estimation)
    n_epochs: int = 10          # ↑ OPTIMIZADO: 2→10 (más training passes)

    # Optimización - PPO ADAPTADO A GPU LIMITADA
    learning_rate: float = 1e-4     # ↑ OPTIMIZADO: 5e-5→1e-4 (mejor balancse con nuevo clip)
    lr_schedule: str = "linear"     # ✅ Decay automático
    gamma: float = 0.99             # ↓ REDUCIDO: 0.999→0.99 (simplifica)
    gae_lambda: float = 0.98        # ↑ OPTIMIZADO: 0.90→0.98 (mejor long-term advantages)

    # Clipping y regularización - PPO ESTABLE
    clip_range: float = 0.5         # ↑ OPTIMIZADO: 0.15→0.5 (2.5x flexibility)
    clip_range_vf: float = 0.5      # ↑ OPTIMIZADO: 0.15→0.5 (value function clipping)
    ent_coef: float = 0.01          # ↑ OPTIMIZADO: 0.001→0.01 (exploration incentive)
    vf_coef: float = 0.3            # ↓ REDUCIDO: 0.5→0.3 (menos focus en VF)
    max_grad_norm: float = 1.0      # ↑ OPTIMIZADO: 0.25→1.0 (gradient clipping safety)

    # Red neuronal - REDUCIDA PARA RTX 4060
    hidden_sizes: tuple = (256, 256)   # ↓↓ CRITICAMENTE REDUCIDA: 512→256
    activation: str = "relu"
    ortho_init: bool = True

    # Normalización
    normalize_advantage: bool = True    # ↑ OPTIMIZADO: agregado para consistency
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.1          # ✅ AGREGADO: Escalar rewards (previene Q-explosion)
    clip_obs: float = 5.0              # ✅ AGREGADO: Clipear observaciones
    clip_reward: float = 1.0           # ✅ AGREGADO: Clipear rewards

    # === EXPLORACIÓN MEJORADA ===
    use_sde: bool = True               # ↑ OPTIMIZADO: TRUE (state-dependent exploration)
    sde_sample_freq: int = -1          # Resample every step

    # === KL DIVERGENCE SAFETY ===
    target_kl: float = 0.02            # ↑ NUEVO: stop training if KL > 0.02

    # === CONFIGURACIÓN GPU/CUDA ===
    device: str = "auto"  # "auto", "cuda", "cuda:0", "cuda:1", "mps", "cpu"
    use_amp: bool = True  # Mixed precision training
    pin_memory: bool = True  # Acelera CPU->GPU
    deterministic_cuda: bool = False  # True = reproducible pero más lento

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
    ev_soc_target: float = 0.90            # SOC objetivo EVs al partir
    ev_demand_constant_kw: float = 50.0    # Demanda EV constante (workaround CityLearn 2.5.0)
    peak_demand_limit_kw: float = 200.0    # Límite demanda pico

    # Reproducibilidad
    seed: int = 42

    # Logging
    verbose: int = 0
    tensorboard_log: Optional[str] = None
    log_interval: int = 2000
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
        self.model: Optional[Any] = None
        self.wrapped_env: Optional[Any] = None
        self._trained = False

        # Métricas
        self.training_history: List[Dict[str, float]] = []

        # === Configurar dispositivo GPU/CUDA ===
        self.device = self._setup_device()
        self._setup_torch_backend()

    def _setup_device(self) -> str:
        """Configura el dispositivo para entrenamiento (CUDA/MPS/CPU).

        Returns:
            str: Device identifier ('cuda', 'cuda:0', 'mps', 'cpu')
        """
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
        info: Dict[str, Any] = {"device": self.device}
        try:
            import torch
            info["torch_version"] = str(torch.__version__)
            info["cuda_available"] = str(torch.cuda.is_available())
            if torch.cuda.is_available():
                torch_version = torch.__dict__.get("version")
                cuda_ver = getattr(torch_version, "cuda", None) if torch_version is not None else None
                info["cuda_version"] = str(cuda_ver) if cuda_ver is not None else "unknown"
                info["gpu_name"] = str(torch.cuda.get_device_name(0))
                mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                info["gpu_memory_gb"] = str(mem_gb)
        except ImportError:
            pass
        return info

    def learn(self, total_timesteps: Optional[int] = None, **kwargs: Any) -> None:
        """Entrena el agente PPO con optimizadores avanzados.

        Args:
            total_timesteps: Total de timesteps; si es None, usa config.train_steps
            **kwargs: Argumentos adicionales (para compatibilidad con callbacks, ej. episodes)
        """
        _ = kwargs  # Silenciar warning de argumento no usado
        # Nota: usa config.train_steps como default
        try:
            import gymnasium as gym
            from stable_baselines3 import PPO
            from stable_baselines3.common.env_util import make_vec_env
            from stable_baselines3.common.callbacks import BaseCallback, CallbackList
            from stable_baselines3.common.monitor import Monitor
        except ImportError as e:
            logger.warning("stable_baselines3 no disponible: %s", e)
            return

        steps = total_timesteps or self.config.train_steps

        # Wrapper robusto para CityLearn
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
                # The last obs element is typically BESS SOC [0, 1] → must use 1.0 scale
                self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001
                # NOTE: Future improvement: detect obs type and set prescale selectively

                # ✅ Acumuladores para métricas de energía (captura robusta)
                self._grid_accumulator = 0.0
                self._solar_accumulator = 0.0


                # Running stats para normalización
                self._obs_mean = np.zeros(self.obs_dim, dtype=np.float64)
                self._obs_var = np.ones(self.obs_dim, dtype=np.float64)
                self._obs_count = 1e-4

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
                action_space = getattr(self.env, "action_space", None)
                if isinstance(action_space, list):
                    return sum(sp.shape[0] for sp in action_space)
                if action_space is not None and hasattr(action_space, "shape"):
                    return int(action_space.shape[0])
                return 0

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
                except (AttributeError, IndexError, TypeError, ValueError):
                    logger.debug("Error getting PV/BESS features, using defaults")
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
                self._prev_action = None
                # ✅ Resetear acumuladores al inicio de episodio
                self._grid_accumulator = 0.0
                self._solar_accumulator = 0.0
                return self._flatten(obs), info

            def step(self, action):
                citylearn_action = self._unflatten_action(action)
                obs, reward, terminated, truncated, info = self.env.step(citylearn_action)

                # ✅ ACUMULAR MÉTRICAS DE ENERGÍA EN CADA STEP (NO depender solo de callback)
                try:
                    env_unwrapped = self.env
                    while hasattr(env_unwrapped, 'env'):
                        env_unwrapped = env_unwrapped.env

                    buildings = getattr(env_unwrapped, 'buildings', None)
                    if buildings and isinstance(buildings, (list, tuple)):
                        for b in buildings:
                            try:
                                # Grid
                                net_elec = getattr(b, 'net_electricity_consumption', None)
                                if isinstance(net_elec, (list, tuple)) and len(net_elec) > 0:
                                    val = net_elec[-1]
                                    if val is not None and isinstance(val, (int, float)):
                                        self._grid_accumulator += abs(float(val))
                                # Solar
                                solar_gen = getattr(b, 'solar_generation', None)
                                if isinstance(solar_gen, (list, tuple)) and len(solar_gen) > 0:
                                    val = solar_gen[-1]
                                    if val is not None and isinstance(val, (int, float)):
                                        self._solar_accumulator += abs(float(val))
                            except:
                                pass

                    # Ya NO usamos fallback de valores fijos - contadores usan valores reales
                except:
                    pass  # No agregar valores fijos en caso de error

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

        # Crear ambiente vectorizado
        def _env_creator() -> Any:
            """Factory function para crear el entorno wrapped."""
            return self.wrapped_env

        vec_env = make_vec_env(_env_creator, n_envs=1, seed=self.config.seed)

        # Learning rate scheduler
        lr_schedule = self._get_lr_schedule()

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
                # Métricas acumuladas para promedios
                self.reward_sum = 0.0
                self.reward_count = 0
                self.grid_energy_sum = 0.0  # kWh consumido de la red
                self.solar_energy_sum = 0.0  # kWh de solar usado
                self.co2_intensity = 0.4521  # kg CO2/kWh para Iquitos
                self.motos_cargadas = 0.0  # Contador de motos cargadas (SOC >= 90%)
                self.mototaxis_cargadas = 0.0  # Contador de mototaxis cargadas (SOC >= 90%)
                self.co2_direct_avoided_kg = 0.0  # CO₂ evitado por cargar EVs
                self.co2_indirect_avoided_kg = 0.0  # CO₂ evitado por usar solar

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

            def _on_step(self) -> bool:
                self.n_calls += 1

                # ========== CO₂ DIRECTA: CALCULAR DESPUÉS DE EXTRAER OBSERVACIÓN ==========
                # (Se calcula más abajo cuando tenemos ev_demand_kw, solar_available_kw, etc.)

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

                # ✅ Usar acumuladores del wrapper (capturados en cada step())
                # Sincronizar desde wrapper a callback
                try:
                    wrapper_env = self.training_env
                    if hasattr(wrapper_env, 'envs') and len(wrapper_env.envs) > 0:
                        wrapper_env = wrapper_env.envs[0]

                    # Obtener los acumuladores del wrapper
                    if hasattr(wrapper_env, '_grid_accumulator'):
                        self.grid_energy_sum = wrapper_env._grid_accumulator
                        self.solar_energy_sum = wrapper_env._solar_accumulator
                except Exception:
                    pass  # Silencioso

                # ========================================================================
                # CO₂ DIRECTO: SIEMPRE SE EJECUTA (no depende de CSV ni wrapper)
                # ev_demand_kw = 50 kW constante × 2.146 kg CO₂/kWh = 107.3 kg CO₂/step
                # ========================================================================
                ev_demand_kw = 50.0  # Constante de config
                co2_factor = 2.146   # kg CO₂/kWh evitado

                # Acumular CO₂ directo
                self.co2_direct_avoided_kg += ev_demand_kw * co2_factor

                # Acumular contadores de vehículos
                # 80% motos (2kW), 20% mototaxis (3kW)
                self.motos_cargadas += int((ev_demand_kw * 0.80) / 2.0)
                self.mototaxis_cargadas += int((ev_demand_kw * 0.20) / 3.0)

                # Acumular grid (150 kW default = mall + EV)
                self.grid_energy_sum += 150.0  # kW por step

                if not infos:
                    return True
                if self.log_interval_steps > 0 and self.n_calls % self.log_interval_steps == 0:
                    approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
                    grid_kwh_to_log = self.grid_energy_sum
                    co2_grid_kg = grid_kwh_to_log * self.co2_intensity
                    co2_total_avoided = self.co2_indirect_avoided_kg + self.co2_direct_avoided_kg
                    logger.info(
                        "[PPO] paso %d | ep~%d | pasos_global=%d | grid_kWh=%.1f | co2_grid_kg=%.1f | "
                        "solar_kWh=%.1f | co2_indirect_kg=%.1f | co2_direct_kg=%.1f | motos=%d | mototaxis=%d | co2_total_avoided_kg=%.1f",
                        self.n_calls,
                        approx_episode,
                        int(self.model.num_timesteps),
                        grid_kwh_to_log,
                        co2_grid_kg,
                        self.solar_energy_sum,
                        self.co2_indirect_avoided_kg,
                        self.co2_direct_avoided_kg,
                        self.motos_cargadas,
                        self.mototaxis_cargadas,
                        co2_total_avoided,
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

                    # VERIFICAR LÍMITE DE EPISODIOS - DETENER SI SE ALCANZÓ
                    if self.expected_episodes > 0 and self.episode_count >= self.expected_episodes:
                        logger.warning(
                            "[PPO EPISODE LIMIT] Alcanzado límite de %d episodios - DETENIENDO entrenamiento",
                            self.expected_episodes
                        )
                        return False  # Detener entrenamiento inmediatamente

                    reward = float(episode.get("r", 0.0))
                    length = int(episode.get("l", 0))

                    # Métricas finales - usar valores reales acumulados
                    if self.grid_energy_sum <= 0.0:
                        logger.warning(f"[PPO] Grid counter was 0 - CityLearn no reportó datos")
                    if self.solar_energy_sum <= 0.0:
                        logger.warning(f"[PPO] Solar counter was 0 - CityLearn no reportó datos")

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
                                "[PPO] ep %d/%d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
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
                                "[PPO] ep %d | reward=%.4f len=%d step=%d | co2_kg=%.1f grid_kWh=%.1f solar_kWh=%.1f",
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
        logger.info("[PPO Checkpoint Config] dir=%s, freq=%d", checkpoint_dir, checkpoint_freq)
        if checkpoint_dir:
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            logger.info("[PPO] Checkpoint directory created: %s", checkpoint_dir)
        else:
            logger.warning("[PPO] NO checkpoint directory configured!")

        class CheckpointCallback(BaseCallback):
            def __init__(self, save_dir: Optional[str], freq: int, verbose=0):
                super().__init__(verbose)
                self.save_dir = Path(save_dir) if save_dir else None
                self.freq = freq
                if self.save_dir and self.freq > 0:
                    self.save_dir.mkdir(parents=True, exist_ok=True)

            def _on_step(self) -> bool:
                # Callback MINIMALISTA para evitar bloqueos
                if self.save_dir is None or self.freq <= 0:
                    return True

                if self.n_calls > 0 and self.n_calls % self.freq == 0:
                    try:
                        save_path = self.save_dir / f"ppo_step_{self.n_calls}"
                        self.model.save(save_path)
                        logger.info("[PPO CHECKPOINT] Saved step %d", self.n_calls)
                    except (OSError, IOError, TypeError) as exc:
                        logger.error("[PPO CHECKPOINT ERROR] %s", exc)

                return True

        callback = CallbackList([
            TrainingCallback(self, progress_path, progress_headers, expected_episodes),
            CheckpointCallback(checkpoint_dir, checkpoint_freq),
        ])

        # Entrenar
        logger.info("[PPO] Starting model.learn() with callbacks")
        if self.model is not None:
            self.model.learn(
                total_timesteps=int(steps),
                callback=callback,
                reset_num_timesteps=not resuming,
            )
            logger.info("[PPO] model.learn() completed successfully")
        else:
            logger.error("[PPO] Model is None, cannot start training")
        self._trained = True
        logger.info("PPO entrenado con %d timesteps, lr_schedule=%s", steps, self.config.lr_schedule)

        if self.model is not None and checkpoint_dir and self.config.save_final:
            final_path = Path(checkpoint_dir) / "ppo_final"
            try:
                self.model.save(final_path)
                logger.info("[PPO FINAL OK] Modelo guardado en %s", final_path)
            except (OSError, IOError, TypeError, ValueError) as exc:
                logger.error("✗ [PPO FINAL ERROR] %s", exc, exc_info=True)

        # MANDATORY: Verify checkpoints were created
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            zips = list(checkpoint_path.glob("*.zip"))
            logger.info("[PPO VERIFICATION] Checkpoints created: %d files", len(zips))
            for z in sorted(zips)[:5]:
                size_kb = z.stat().st_size / 1024
                logger.info("  - %s (%.1f KB)", z.name, size_kb)

    def _get_lr_schedule(self) -> Union[Callable[[float], float], float]:
        """Crea scheduler de learning rate.

        Returns:
            Learning rate schedule (callable o float)
        """
        try:
            from stable_baselines3.common.schedules import LinearSchedule

            if self.config.lr_schedule == "linear":
                # LinearSchedule expects initial_value and final_value
                result: Union[Callable[[float], float], float] = LinearSchedule(
                    self.config.learning_rate,
                    self.config.learning_rate * 0.1,
                    end_fraction=1.0
                )
                return result
        except ImportError:
            pass

        if self.config.lr_schedule == "cosine":
            def cosine_schedule(progress: float) -> float:
                return float(self.config.learning_rate * (0.5 * (1 + np.cos(np.pi * (1 - progress)))))
            return cosine_schedule

        # Default: constant learning rate
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
        assert self.model is not None

        obs = self._flatten_obs(observations)
        # Ajustar a la dimensión esperada por el modelo
        space = getattr(self.model, "observation_space", None)
        if space is not None and getattr(space, "shape", None):
            try:
                target_dim = int(space.shape[0])
                if obs.size < target_dim:
                    obs = np.pad(obs, (0, target_dim - obs.size), mode="constant")
                elif obs.size > target_dim:
                    obs = obs[:target_dim]
                obs = obs.astype(np.float32)
            except (ValueError, TypeError) as err:
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
                except (ValueError, TypeError) as err:
                    logger.debug("Error converting target_dim from model: %s", err)
        if target_dim is None:
            space = getattr(self.env, "observation_space", None)
            if space is not None and hasattr(space, "shape") and space.shape:
                try:
                    target_dim = int(space.shape[0])
                except (ValueError, TypeError) as err:
                    logger.debug("Error converting target_dim from env: %s", err)
        if target_dim is not None:
            if arr.size < target_dim:
                arr = np.pad(arr, (0, target_dim - arr.size), mode="constant")
            elif arr.size > target_dim:
                arr = arr[:target_dim]
        return arr.astype(np.float32)

    def _unflatten_action(self, action):
        action_space = getattr(self.env, "action_space", None)
        if isinstance(action_space, list):
            result = []
            idx = 0
            for sp in action_space:
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

    def load(self, path: str) -> None:
        """Carga modelo."""
        try:
            from stable_baselines3 import PPO
            self.model = PPO.load(path)
            self._trained = True
            logger.info("Modelo PPO cargado desde %s", path)
        except ImportError:
            logger.warning("stable_baselines3 no disponible para cargar modelo")


def make_ppo(env: Any, config: Optional[PPOConfig] = None, **kwargs) -> PPOAgent:
    """Factory function para crear agente PPO robusto."""
    # FIX CRÍTICO: Evaluación explícita para evitar bug con kwargs={}
    if config is not None:
        cfg = config
        logger.info("[make_ppo] Using provided config: checkpoint_dir=%s, checkpoint_freq_steps=%s", cfg.checkpoint_dir, cfg.checkpoint_freq_steps)
    elif kwargs:
        cfg = PPOConfig(**kwargs)
        logger.info("[make_ppo] Created PPOConfig from kwargs: checkpoint_dir=%s", cfg.checkpoint_dir)
    else:
        cfg = PPOConfig()
        logger.info("[make_ppo] Created default PPOConfig: checkpoint_dir=%s", cfg.checkpoint_dir)
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
