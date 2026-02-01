from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import json
import logging
import re

import numpy as np
import pandas as pd  # type: ignore

from iquitos_citylearn.oe3.agents import (
    make_basic_ev_rbc,
    make_sac,
    make_no_control,
    make_uncontrolled,
    make_ppo,
    make_a2c,
    SACConfig,
    PPOConfig,
    A2CConfig,
    # Multiobjetivo
    MultiObjectiveReward,
    IquitosContext,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

logger = logging.getLogger(__name__)

def _latest_checkpoint(checkpoint_dir: Optional[Path], prefix: str) -> Optional[Path]:
    """Retorna el checkpoint más reciente por fecha de modificación (final o step)."""
    if checkpoint_dir is None or not checkpoint_dir.exists():
        return None

    # Buscar todos los checkpoints (final y step_*)
    candidates: List[Path] = []
    final_path = checkpoint_dir / f"{prefix}_final.zip"
    if final_path.exists():
        candidates.append(final_path)
    candidates.extend(checkpoint_dir.glob(f"{prefix}_step_*.zip"))

    if not candidates:
        return None

    # Ordenar por fecha de modificación (más reciente primero)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    best = candidates[0]

    # Log del checkpoint seleccionado
    if "final" in best.name:
        logger.info(f"[RESUME] Usando checkpoint final (más reciente): {best}")
    else:
        m = re.search(r"step_(\d+)", best.stem)
        step = int(m.group(1)) if m else 0
        logger.info(f"[RESUME] Usando checkpoint step {step} (más reciente): {best}")

    return best

@dataclass(frozen=True)
class SimulationResult:
    agent: str
    steps: int
    seconds_per_time_step: int
    simulated_years: float
    grid_import_kwh: float
    grid_export_kwh: float
    net_grid_kwh: float
    ev_charging_kwh: float
    building_load_kwh: float
    pv_generation_kwh: float
    carbon_kg: float
    results_path: str
    timeseries_path: str
    # Métricas multiobjetivo
    multi_objective_priority: str = "balanced"
    reward_co2_mean: float = 0.0
    reward_cost_mean: float = 0.0
    reward_solar_mean: float = 0.0
    reward_ev_mean: float = 0.0
    reward_grid_mean: float = 0.0
    reward_total_mean: float = 0.0

def _safe_array(x: Any) -> Optional[np.ndarray]:
    if x is None:
        return None
    try:
        arr = np.array(x, dtype=float)
        return arr
    except Exception:
        return None

def _get_first_attr(obj: Any, names: list[str]) -> Optional[np.ndarray]:
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if callable(v):
                continue
            arr = _safe_array(v)
            if arr is not None and arr.size > 0:
                return arr
    return None

def _extract_net_grid_kwh(env: Any) -> np.ndarray:
    # Candidate names at env level
    arr = _get_first_attr(env, [
        "net_electricity_consumption",
        "district_net_electricity_consumption",
        "district_electricity_consumption",
    ])
    if arr is not None:
        return arr
    # Sum buildings
    buildings = getattr(env, "buildings", [])
    series = None
    for b in buildings:
        b_arr = _get_first_attr(b, ["net_electricity_consumption", "electricity_consumption"])
        if b_arr is None:
            continue
        series = b_arr if series is None else series + b_arr
    if series is None:
        raise AttributeError("Could not extract net electricity consumption from CityLearn env.")
    return series

def _extract_building_load_kwh(env: Any) -> np.ndarray:
    buildings = getattr(env, "buildings", [])
    series = None
    for b in buildings:
        b_arr = _get_first_attr(b, ["non_shiftable_load"])
        if b_arr is None:
            continue
        series = b_arr if series is None else series + b_arr
    return series if series is not None else np.zeros_like(_extract_net_grid_kwh(env))

def _extract_pv_generation_kwh(env: Any) -> np.ndarray:
    buildings = getattr(env, "buildings", [])
    series = None
    for b in buildings:
        b_arr = _get_first_attr(b, ["solar_generation"])
        if b_arr is None:
            continue
        series = b_arr if series is None else series + b_arr
    if series is None:
        return np.zeros_like(_extract_net_grid_kwh(env))
    # CityLearn reporta generaciÇün FV como carga negativa.
    if np.nanmean(series) < 0:
        series = -series
    return np.clip(series, 0.0, None)

def _extract_ev_charging_kwh(env: Any) -> np.ndarray:
    buildings = getattr(env, "buildings", [])
    series = None
    for b in buildings:
        b_arr = _get_first_attr(b, ["chargers_electricity_consumption"])
        if b_arr is not None:
            series = b_arr if series is None else series + b_arr
    if series is not None:
        return np.clip(series, 0.0, None)
    for b in buildings:
        # Try EV storage
        evs = getattr(b, "electric_vehicle_storage", None)
        if evs is not None:
            ev_arr = _get_first_attr(evs, ["electricity_consumption", "electricity_consumption_history"])
            if ev_arr is not None:
                series = ev_arr if series is None else series + ev_arr

        # Try chargers list
        chargers = getattr(b, "electric_vehicle_chargers", None) or getattr(b, "chargers", None) or []
        for ch in chargers:
            ch_arr = _get_first_attr(ch, ["electricity_consumption", "electricity_consumption_history"])
            if ch_arr is not None:
                series = ch_arr if series is None else series + ch_arr

    if series is None:
        return np.zeros_like(_extract_net_grid_kwh(env))
    return np.clip(series, 0.0, None)

def _extract_carbon_intensity(env: Any, default_value: float) -> np.ndarray:
    arr = _get_first_attr(env, ["carbon_intensity", "carbon_intensity_forecast", "carbon_intensity_history"])
    if arr is not None:
        return arr
    return np.full_like(_extract_net_grid_kwh(env), float(default_value), dtype=float)

def _make_env(schema_path: Path) -> Any:
    from citylearn.citylearn import CityLearnEnv  # type: ignore

    # GLOBAL PATCH: Disable the problematic simulate_unconnected_ev_soc method at class level
    # This method tries to access electric_vehicle_charger_state[t+1] which causes boundary errors
    try:
        from citylearn.building import Building

        # Replace the problematic method with a no-op at class level
        def _patched_simulate_unconnected_ev_soc(self):  # type: ignore
            """Disabled: This method in CityLearn 2.5.0 has a boundary access bug."""
            pass

        setattr(Building, 'simulate_unconnected_ev_soc', _patched_simulate_unconnected_ev_soc)
        logger.debug("Patched Building.simulate_unconnected_ev_soc at class level")
    except Exception as e:
        logger.debug(f"Optional patch skipped (no impact on training): {e}")

    # Must use absolute path so CityLearn can find CSV files relative to schema directory
    abs_path = str(schema_path.resolve())
    try:
        env = CityLearnEnv(schema=abs_path, render_mode=None)
    except TypeError:
        env = CityLearnEnv(schema=abs_path, render_mode=None)

    # CRITICAL FIX: Ensure render_mode attribute exists to suppress stable_baselines3 warnings
    if not hasattr(env, 'render_mode'):
        env.render_mode = None

    return env

def _sample_action(env: Any) -> Any:
    """Sample random action handling CityLearn's list action space."""
    if isinstance(env.action_space, list):
        return [sp.sample() for sp in env.action_space]
    return env.action_space.sample()

def _run_episode(env: Any, agent: Any, deterministic: bool = True) -> None:
    obs, _ = env.reset()
    done = False
    while not done:
        if hasattr(agent, "predict"):
            action = agent.predict(obs, deterministic=deterministic)
        elif hasattr(agent, "act"):
            action = agent.act(obs)
        else:
            action = _sample_action(env)
        obs, _, terminated, truncated, _ = env.step(action)
        done = bool(terminated or truncated)


def _flatten_obs_for_trace(obs: Any) -> Tuple[np.ndarray, List[str]]:
    if isinstance(obs, dict):
        values = []
        obs_names_dict: List[str] = []
        for key, value in obs.items():
            arr = np.array(value, dtype=np.float32).ravel()
            values.append(arr)
            obs_names_dict.extend([f"obs_{key}_{i:03d}" for i in range(len(arr))])
        return np.concatenate(values) if values else np.array([], dtype=np.float32), obs_names_dict
    if isinstance(obs, (list, tuple)):
        values = []
        obs_names_list: List[str] = []
        for idx, value in enumerate(obs):
            arr = np.array(value, dtype=np.float32).ravel()
            values.append(arr)
            obs_names_list.extend([f"obs_{idx}_{i:03d}" for i in range(len(arr))])
        return np.concatenate(values) if values else np.array([], dtype=np.float32), obs_names_list
    arr = np.array(obs, dtype=np.float32).ravel()
    obs_names = [f"obs_{i:03d}" for i in range(len(arr))]
    return arr, obs_names


def _flatten_action_for_trace(action: Any, env: Any) -> Tuple[np.ndarray, List[str]]:
    if isinstance(action, list):
        values = []
        for part in action:
            arr = np.array(part, dtype=np.float32).ravel()
            values.append(arr)
        vec = np.concatenate(values) if values else np.array([], dtype=np.float32)
    else:
        vec = np.array(action, dtype=np.float32).ravel()

    action_names = []
    if hasattr(env, "action_names"):
        names = env.action_names
        if isinstance(names, list):
            for n in names:
                if isinstance(n, list):
                    action_names.extend(n)
                else:
                    action_names.append(str(n))
        else:
            action_names.append(str(names))
    if len(action_names) != len(vec):
        action_names = [f"action_{i:03d}" for i in range(len(vec))]
    return vec, action_names


def _run_episode_baseline_optimized(
    env: Any,
    agent: Any,
    agent_label: str = "",
) -> Tuple[np.ndarray, np.ndarray, List[float], List[str], List[str]]:
    """Ejecuta episodio para BASELINE sin guardar observaciones en memoria (memory leak fix)."""
    obs, _ = env.reset()
    rewards: List[float] = []
    max_steps = 8760

    for step in range(max_steps):
        # Agent predict
        if hasattr(agent, "predict"):
            action = agent.predict(obs, deterministic=True)
        elif hasattr(agent, "act"):
            action = agent.act(obs)
        else:
            action = _sample_action(env)

        # Step environment
        try:
            obs, reward, _, _, _ = env.step(action)
        except (KeyboardInterrupt, KeyError, IndexError, RecursionError, AttributeError, TypeError):
            reward = 0.0
        except Exception as e:
            logger.error(f"Error en env.step: {type(e).__name__}")
            reward = 0.0

        # Convert reward to float
        if isinstance(reward, (list, tuple)):
            reward_val = float(sum(reward))
        else:
            reward_val = float(reward)
        rewards.append(reward_val)

        # Log progress
        if (step + 1) % 500 == 0:
            logger.info("[%s] paso %d / %d", agent_label, step + 1, max_steps)

    # Return empty arrays for trace (baseline doesn't need them)
    return (
        np.zeros((0, 0), dtype=np.float32),
        np.zeros((0, 0), dtype=np.float32),
        rewards,
        [],
        [],
    )


def _run_episode_with_trace(
    env: Any,
    agent: Any,
    deterministic: bool = True,
    log_interval_steps: int = 0,
    agent_label: str = "",
) -> Tuple[np.ndarray, np.ndarray, List[float], List[str], List[str]]:
    obs, _ = env.reset()
    done = False
    obs_rows: List[np.ndarray] = []
    action_rows: List[np.ndarray] = []
    rewards: List[float] = []
    obs_names: List[str] = []
    action_names: List[str] = []
    max_steps = 8760  # 1 año completo con pasos horarios

    while not done:
        # **CRITICAL FIX**: Check if we've completed full year BEFORE attempting env.step()
        # This prevents IndexError when CityLearn data arrays end at index 8759 (for 8760 elements)
        if len(rewards) >= max_steps:
            logger.info(f"[{agent_label}] Completó {len(rewards)} pasos (1 año). Terminando episodio normalmente.")
            done = True
            break

        obs_vec, obs_names = _flatten_obs_for_trace(obs)
        if hasattr(agent, "predict"):
            action = agent.predict(obs, deterministic=deterministic)
        elif hasattr(agent, "act"):
            action = agent.act(obs)
        else:
            action = _sample_action(env)
        action_vec, action_names = _flatten_action_for_trace(action, env)
        obs_rows.append(obs_vec)
        action_rows.append(action_vec)

        try:
            obs, reward, _, _, _ = env.step(action)
        except KeyboardInterrupt:
            logger.debug(f"CityLearn KeyboardInterrupt (boundary access bug) - skipping step")
            obs, reward = obs, 0.0
        except (KeyError, IndexError, RecursionError, AttributeError, TypeError) as e:
            logger.warning(f"Error en env.step (CityLearn): {type(e).__name__}: {str(e)[:100]}. Continuando...")
            reward = 0.0
        except Exception as e:
            logger.error(f"Error inesperado en env.step: {type(e).__name__}: {str(e)[:100]}")
            reward = 0.0

        if isinstance(reward, (list, tuple)):
            reward_val = float(sum(reward))
        else:
            reward_val = float(reward)
        rewards.append(reward_val)

        if log_interval_steps > 0 and (len(rewards) % log_interval_steps) == 0:
            lbl = agent_label if agent_label else "agent"
            logger.info("[%s] paso %d / %d", lbl, len(rewards), max_steps)

        done = False

    obs_arr = np.vstack(obs_rows) if obs_rows else np.zeros((0, 0), dtype=np.float32)
    action_arr = np.vstack(action_rows) if action_rows else np.zeros((0, 0), dtype=np.float32)
    return obs_arr, action_arr, rewards, obs_names, action_names


def _run_episode_safe(
    env: Any,
    agent: Any,
    deterministic: bool = True,
    log_interval_steps: int = 0,
    agent_label: str = "",
) -> Tuple[np.ndarray, np.ndarray, List[float], List[str], List[str]]:
    """Ejecuta un episodio capturando errores para no detener el pipeline."""
    try:
        return _run_episode_with_trace(
            env,
            agent,
            deterministic=deterministic,
            log_interval_steps=log_interval_steps,
            agent_label=agent_label,
        )
    except Exception as exc:
        logger.warning("Episodio de evaluación falló para %s (%s); se continúa sin traza.", agent_label or "agent", exc)
        return (
            np.zeros((0, 0), dtype=np.float32),
            np.zeros((0, 0), dtype=np.float32),
            [],
            [],
            [],
        )


def _serialize_config(config: Any) -> Optional[Dict[str, Any]]:
    if config is None:
        return None
    try:
        return asdict(config)
    except Exception:
        return config.__dict__ if hasattr(config, "__dict__") else None


def _save_training_artifacts(
    agent_name: str,
    agent: Any,
    training_dir: Optional[Path],
) -> None:
    if training_dir is None:
        return

    history = getattr(agent, "training_history", None)
    config = getattr(agent, "config", None)
    if not history and config is None:
        return

    training_dir.mkdir(parents=True, exist_ok=True)

    cfg = _serialize_config(config)
    if cfg:
        cfg_path = training_dir / f"{agent_name}_config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    if not history:
        return

    df = pd.DataFrame(history)
    if df.empty:
        return
    df.insert(0, "agent", agent_name)
    csv_path = training_dir / f"{agent_name}_training_metrics.csv"
    df.to_csv(csv_path, index=False)

    metric_col = None
    for col in ("mean_reward", "reward", "episode_reward"):
        if col in df.columns:
            metric_col = col
            break
    if metric_col is None:
        return

    x = df["step"].values if "step" in df.columns else np.arange(len(df))
    y = df[metric_col].values
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    plt.figure(figsize=(10, 4))
    plt.plot(x, y, linewidth=1.5, color="steelblue")
    plt.xlabel("step")
    plt.ylabel(metric_col)
    plt.title(f"training_{agent_name}")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    png_path = training_dir / f"{agent_name}_training.png"
    plt.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close()

def simulate(
    schema_path: Path,
    agent_name: str,
    out_dir: Path,
    training_dir: Optional[Path],
    carbon_intensity_kg_per_kwh: float,
    seconds_per_time_step: int,
    sac_episodes: int = 10,
    sac_batch_size: int = 512,
    sac_learning_rate: float = 5e-5,          # AJUSTE: 1e-4→5e-5 (reduce inestabilidad)
    sac_log_interval: int = 500,
    sac_use_amp: bool = True,
    ppo_timesteps: int = 100000,
    ppo_n_steps: int = 1024,
    ppo_batch_size: int = 128,
    ppo_use_amp: bool = True,
    deterministic_eval: bool = True,
    use_multi_objective: bool = True,
    multi_objective_priority: str = "balanced",
    sac_device: Optional[str] = None,
    sac_prefer_citylearn: bool = False,
    ppo_device: Optional[str] = None,
    ppo_target_kl: Optional[float] = None,
    ppo_kl_adaptive: bool = True,
    ppo_log_interval: int = 1000,
    sac_checkpoint_freq_steps: int = 1000,  # MANDATORY: Default to 1000 steps for checkpoint generation
    ppo_checkpoint_freq_steps: int = 1000,  # MANDATORY: Default to 1000 steps for checkpoint generation
    a2c_episodes: int = 0,
    a2c_timesteps: int = 0,
    a2c_checkpoint_freq_steps: int = 1000,  # MANDATORY: Default to 1000 steps for checkpoint generation
    a2c_n_steps: int = 256,
    a2c_log_interval: int = 2000,
    a2c_learning_rate: float = 3e-4,
    a2c_entropy_coef: float = 0.01,
    a2c_batch_size: int = 1024,
    a2c_gamma: float = 0.99,
    a2c_gae_lambda: float = 0.9,
    a2c_vf_coef: float = 0.5,
    a2c_reward_scale: float = 1.2,
    a2c_device: Optional[str] = "cpu",  # A2C no es eficiente en GPU (use CPU)
    sac_resume_checkpoints: bool = False,
    ppo_resume_checkpoints: bool = False,
    a2c_resume_checkpoints: bool = False,
    seed: Optional[int] = None,
) -> SimulationResult:
    """Ejecuta simulación con agente especificado.

    Args:
        schema_path: Path al schema CityLearn
        agent_name: Nombre del agente (uncontrolled, rbc, sac, ppo, etc.)
        out_dir: Directorio de salida
        training_dir: Directorio para artefactos de entrenamiento (metrics/plots)
        carbon_intensity_kg_per_kwh: Factor de emisión CO2
        seconds_per_time_step: Segundos por paso de simulación
        sac_episodes: Episodios de entrenamiento para SAC
        ppo_timesteps: Timesteps de entrenamiento para PPO
        deterministic_eval: Usar modo determinístico en evaluación
        use_multi_objective: Usar función de recompensa multiobjetivo
        multi_objective_priority: Prioridad multiobjetivo (balanced, co2_focus, cost_focus, ev_focus, solar_focus)
        sac_device: Dispositivo para SAC (e.g., "cuda", "cuda:0"). None = auto.
        ppo_device: Dispositivo para PPO (e.g., "cuda", "cuda:0"). None = auto.
        seed: Semilla para entrenamiento (None usa defaults del agente).

    Returns:
        SimulationResult con métricas de la simulación
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_dir = training_dir / "progress" if training_dir is not None else None

    raw_env = _make_env(schema_path)

    # Configurar recompensa multiobjetivo
    reward_tracker: Optional[MultiObjectiveReward] = None
    env: Any = raw_env  # Por defecto usa el env sin wrapper

    if use_multi_objective:
        weights = create_iquitos_reward_weights(multi_objective_priority)
        context = IquitosContext(
            co2_factor_kg_per_kwh=carbon_intensity_kg_per_kwh,
        )
        # Aplicar wrapper multiobjetivo al environment
        env = CityLearnMultiObjectiveWrapper(raw_env, weights, context)
        reward_tracker = env.reward_fn  # Obtener el tracker del wrapper

        logger.info("")
        logger.info("=" * 80)
        logger.info("[CONFIG] MULTI-OBJECTIVE REWARD CONFIGURATION")
        logger.info("=" * 80)
        logger.info(f"  Priority Mode: {multi_objective_priority.upper()}")
        logger.info(f"  CO2 Minimization Weight: {weights.co2:.2f} (primary)")
        logger.info(f"  Solar Self-Consumption Weight: {weights.solar:.2f} (secondary)")
        logger.info(f"  Cost Optimization Weight: {weights.cost:.2f}")
        logger.info(f"  EV Satisfaction Weight: {weights.ev_satisfaction:.2f}")
        logger.info(f"  Grid Stability Weight: {weights.grid_stability:.2f}")
        logger.info(f"  Total (should be 1.0): {weights.co2 + weights.solar + weights.cost + weights.ev_satisfaction + weights.grid_stability:.2f}")
        logger.info(f"  Grid Carbon Intensity: {carbon_intensity_kg_per_kwh:.4f} kg CO2/kWh (Iquitos thermal)")
        logger.info("=" * 80)
        logger.info("")

    # Choose agent
    agent: Any
    trace_obs: Optional[np.ndarray] = None
    trace_actions: Optional[np.ndarray] = None
    trace_rewards: List[float] = []
    trace_obs_names: List[str] = []
    trace_action_names: List[str] = []
    if agent_name.lower() == "uncontrolled":
        agent = make_uncontrolled(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_baseline_optimized(
            env, agent, agent_label="Uncontrolled"
        )
    elif agent_name.lower() in ["nocontrol", "no_control"]:
        agent = make_no_control(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_baseline_optimized(
            env, agent, agent_label="NoControl"
        )
    elif agent_name.lower() in ["basicevrbc", "rbc", "basic_evrbc"]:
        agent = make_basic_ev_rbc(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_baseline_optimized(
            env, agent, agent_label="RBC"
        )
    elif agent_name.lower() == "sac":
        try:
            sac_kwargs: Dict[str, Any] = {}
            sac_progress_path = None
            if progress_dir is not None:
                sac_progress_path = progress_dir / "sac_progress.csv"
                sac_progress_path.parent.mkdir(parents=True, exist_ok=True)
                if sac_progress_path.exists():
                    sac_progress_path.unlink()
            # MANDATORY: Always create checkpoint directory when training_dir is provided
            sac_checkpoint_dir = None
            if training_dir is not None:
                sac_checkpoint_dir = training_dir / "checkpoints" / "sac"
                sac_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            sac_resume = _latest_checkpoint(sac_checkpoint_dir, "sac") if sac_resume_checkpoints else None
            sac_config = SACConfig(
                episodes=sac_episodes,
                device=sac_device or "auto",
                seed=seed if seed is not None else 42,
                batch_size=int(sac_kwargs.pop("batch_size", sac_batch_size) if sac_kwargs else sac_batch_size),
                buffer_size=int(sac_kwargs.pop("buffer_size", 50000) if sac_kwargs else 50000),
                gradient_steps=int(sac_kwargs.pop("gradient_steps", 1) if sac_kwargs else 1),
                learning_rate=float(sac_learning_rate),  # ✅ USAR PARÁMETRO
                gamma=0.99,
                tau=0.005,
                hidden_sizes=(256, 256),
                log_interval=int(sac_kwargs.pop("log_interval", sac_log_interval) if sac_kwargs else sac_log_interval),
                use_amp=bool(sac_kwargs.pop("use_amp", sac_use_amp) if sac_kwargs else sac_use_amp),
                checkpoint_dir=str(sac_checkpoint_dir) if sac_checkpoint_dir else None,
                checkpoint_freq_steps=int(sac_checkpoint_freq_steps),
                progress_path=str(sac_progress_path) if sac_progress_path else None,
                prefer_citylearn=bool(sac_prefer_citylearn),
                resume_path=str(sac_resume) if sac_resume else None,
                **sac_kwargs,
            )
            logger.info("")
            logger.info("=" * 80)
            logger.info("[CONFIG] SAC AGENT CONFIGURATION")
            logger.info("=" * 80)
            logger.info(f"  Episodes: {sac_episodes}")
            logger.info(f"  Device: {sac_device or 'auto'}")
            logger.info(f"  Batch Size: {sac_config.batch_size}")
            logger.info(f"  Buffer Size: {sac_config.buffer_size}")
            logger.info(f"  Learning Rate: {sac_config.learning_rate}")
            logger.info(f"  Entropy Coeff: {sac_config.ent_coef if hasattr(sac_config, 'ent_coef') else 'auto'}")
            logger.info(f"  Hidden Sizes: {sac_config.hidden_sizes}")
            logger.info(f"  Checkpoint Dir: {sac_checkpoint_dir}")
            logger.info(f"  Resume from: {('Ultima ejecucion' if sac_resume else 'Desde cero')}")
            logger.info(f"  AMP (Mixed Precision): {sac_config.use_amp}")
            logger.info("=" * 80)
            logger.info("")
            logger.info(f"[SIMULATE] SAC Config: checkpoint_dir={sac_checkpoint_dir}, checkpoint_freq_steps={sac_checkpoint_freq_steps}")
            agent = make_sac(env, config=sac_config)
        except Exception as e:
            logger.warning("SAC agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = make_uncontrolled(env)
        # Train
        if hasattr(agent, "learn"):
            try:
                agent.learn(episodes=sac_episodes)
            except TypeError:
                agent.learn(sac_episodes)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_safe(
            env, agent, deterministic=deterministic_eval, agent_label="SAC"
        )
    elif agent_name.lower() == "ppo":
        try:
            ppo_kwargs: Dict[str, Any] = {}
            if ppo_device:
                ppo_kwargs["device"] = ppo_device
            if seed is not None:
                ppo_kwargs["seed"] = seed
            ppo_progress_path = None
            if progress_dir is not None:
                ppo_progress_path = progress_dir / "ppo_progress.csv"
                ppo_progress_path.parent.mkdir(parents=True, exist_ok=True)
                if ppo_progress_path.exists():
                    ppo_progress_path.unlink()
            # MANDATORY: Always create checkpoint directory when training_dir is provided
            ppo_checkpoint_dir = None
            if training_dir is not None:
                ppo_checkpoint_dir = training_dir / "checkpoints" / "ppo"
                ppo_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            ppo_resume = _latest_checkpoint(ppo_checkpoint_dir, "ppo") if ppo_resume_checkpoints else None
            ppo_config = PPOConfig(
                train_steps=ppo_timesteps,
                n_steps=ppo_n_steps,
                batch_size=ppo_batch_size,
                n_epochs=10,
                learning_rate=3e-4,
                lr_schedule="linear",
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                hidden_sizes=(256, 256),
                checkpoint_dir=str(ppo_checkpoint_dir) if ppo_checkpoint_dir else None,
                checkpoint_freq_steps=int(ppo_checkpoint_freq_steps),
                progress_path=str(ppo_progress_path) if ppo_progress_path else None,
                target_kl=ppo_target_kl if ppo_target_kl is not None else 0.01,
                kl_adaptive=ppo_kl_adaptive,
                log_interval=int(ppo_log_interval),
                use_amp=bool(ppo_kwargs.pop("use_amp", ppo_use_amp) if ppo_kwargs else ppo_use_amp),
                resume_path=str(ppo_resume) if ppo_resume else None,
                **ppo_kwargs,
            )
            logger.info("")
            logger.info("="*80)
            logger.info("  [A2C] PPO AGENT CONFIGURATION")
            logger.info("="*80)
            logger.info(f"  Training Timesteps: {ppo_timesteps}")
            logger.info(f"  N-Steps: {ppo_n_steps}")
            logger.info(f"  Device: {ppo_device or 'auto'}")
            logger.info(f"  Batch Size: {ppo_batch_size}")
            logger.info(f"  N Epochs: {ppo_config.n_epochs}")
            logger.info(f"  Learning Rate: {ppo_config.learning_rate}")
            logger.info(f"  LR Schedule: {ppo_config.lr_schedule}")
            logger.info(f"  Clip Range: {ppo_config.clip_range}")
            logger.info(f"  Entropy Coeff: {ppo_config.ent_coef}")
            logger.info(f"  GAE Lambda: {ppo_config.gae_lambda}")
            logger.info(f"  Hidden Sizes: {ppo_config.hidden_sizes}")
            logger.info(f"  Checkpoint Dir: {ppo_checkpoint_dir}")
            logger.info(f"  Resume from: {('Última ejecución' if ppo_resume else 'Desde cero')}")
            logger.info(f"  AMP (Mixed Precision): {ppo_config.use_amp}")
            logger.info(f"  KL Adaptive: {ppo_kl_adaptive}")
            logger.info("="*80)
            logger.info("")
            logger.info(f"[SIMULATE] PPO Config: checkpoint_dir={ppo_checkpoint_dir}, checkpoint_freq_steps={ppo_checkpoint_freq_steps}")
            agent = make_ppo(env, config=ppo_config)
            if hasattr(agent, "learn"):
                agent.learn(total_timesteps=ppo_timesteps)
        except Exception as e:
            logger.warning("PPO agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = make_uncontrolled(env)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_safe(
            env, agent, deterministic=deterministic_eval, agent_label="PPO"
        )
    elif agent_name.lower() == "a2c":
        try:
            a2c_kwargs: Dict[str, Any] = {}
            if a2c_device:
                a2c_kwargs["device"] = a2c_device
            if seed is not None:
                a2c_kwargs["seed"] = seed
            # MANDATORY: Always create checkpoint directory when training_dir is provided
            a2c_checkpoint_dir = None
            if training_dir is not None:
                a2c_checkpoint_dir = training_dir / "checkpoints" / "a2c"
                a2c_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            a2c_resume = _latest_checkpoint(a2c_checkpoint_dir, "a2c") if a2c_resume_checkpoints else None
            a2c_steps = a2c_timesteps if a2c_timesteps > 0 else ppo_timesteps
            a2c_progress_path = None
            if progress_dir is not None:
                a2c_progress_path = progress_dir / "a2c_progress.csv"
                a2c_progress_path.parent.mkdir(parents=True, exist_ok=True)
                if a2c_progress_path.exists():
                    a2c_progress_path.unlink()
            a2c_config = A2CConfig(
                train_steps=a2c_steps,
                n_steps=int(a2c_n_steps),
                learning_rate=float(a2c_learning_rate),
                gamma=float(a2c_gamma),
                gae_lambda=float(a2c_gae_lambda),
                ent_coef=float(a2c_entropy_coef),
                vf_coef=float(a2c_vf_coef),
                hidden_sizes=(256, 256),
                log_interval=int(a2c_log_interval),
                checkpoint_dir=str(a2c_checkpoint_dir) if a2c_checkpoint_dir else None,
                checkpoint_freq_steps=int(a2c_checkpoint_freq_steps),
                progress_path=str(a2c_progress_path) if a2c_progress_path else None,
                resume_path=str(a2c_resume) if a2c_resume else None,
                **a2c_kwargs,
            )
            logger.info("")
            logger.info("=" * 80)
            logger.info("  [A2C] AGENT CONFIGURATION")
            logger.info("=" * 80)
            logger.info(f"  Training Timesteps: {a2c_steps}")
            logger.info(f"  N-Steps: {a2c_config.n_steps}")
            logger.info(f"  Device: {a2c_device or 'auto'}")
            logger.info(f"  Learning Rate: {a2c_config.learning_rate}")
            logger.info(f"  Gamma (discount): {a2c_config.gamma}")
            logger.info(f"  GAE Lambda: {a2c_config.gae_lambda}")
            logger.info(f"  Entropy Coeff: {a2c_config.ent_coef}")
            logger.info(f"  Value Fn Coeff: {a2c_config.vf_coef}")
            logger.info(f"  Hidden Sizes: {a2c_config.hidden_sizes}")
            logger.info(f"  Checkpoint Dir: {a2c_checkpoint_dir}")
            logger.info(f"  Resume from: {'Last run' if a2c_resume else 'From scratch'}")
            logger.info("=" * 80)
            logger.info("")
            logger.info(f"[SIMULATE] A2C Config: checkpoint_dir={a2c_checkpoint_dir}, checkpoint_freq_steps={a2c_checkpoint_freq_steps}")
            agent = make_a2c(env, config=a2c_config)
            if hasattr(agent, "learn"):
                agent.learn(total_timesteps=a2c_steps)
        except Exception as e:
            logger.warning("A2C agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = make_uncontrolled(env)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_safe(
            env, agent, deterministic=deterministic_eval, agent_label="A2C"
        )
    else:
        logger.warning(f"Unknown agent_name: {agent_name}. Falling back to Uncontrolled.")
        agent = make_uncontrolled(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_safe(
            env, agent, deterministic=True, agent_label="Uncontrolled"
        )

    # **CRITICAL FIX**: Use trace_rewards length as the SOURCE OF TRUTH for steps
    # because it represents actual episode execution. Environment data extraction is unreliable.
    if len(trace_rewards) > 0:
        steps = len(trace_rewards)
        logger.info(f"[EPISODE] Ejecutó {steps} pasos (episodio completo). Usando datos de traza.")
    else:
        logger.warning(f"[EPISODE] Traza vacía para {agent_name}. Intentando extraer del environment...")
        try:
            net = _extract_net_grid_kwh(env)
        except Exception as e:
            logger.warning(f"Could not extract net grid kwh from environment for {agent_name}: {e}. Using empty array.")
            net = np.array([], dtype=float)

        if len(net) == 0:
            logger.warning(f"Episode for {agent_name} produced no data. Creating baseline 8760-hour array with zeros.")
            net = np.zeros(8760, dtype=float)
        steps = len(net)

    # Create baseline arrays of correct size
    try:
        net = _extract_net_grid_kwh(env)
        if len(net) != steps:
            logger.warning(f"Net grid array size mismatch: expected {steps}, got {len(net)}. Padding/truncating.")
            net = np.pad(net, (0, steps - len(net))) if len(net) < steps else net[:steps]
    except Exception as e:
        logger.warning(f"Could not extract net grid kwh from environment for {agent_name}: {e}. Using zeros.")
        net = np.zeros(steps, dtype=float)

    grid_import = np.clip(net, 0.0, None)
    grid_export = np.clip(-net, 0.0, None)

    # Extract all metrics with fallback to zero arrays of correct size
    try:
        ev = _extract_ev_charging_kwh(env)
        if len(ev) != steps:
            ev = np.pad(ev, (0, steps - len(ev))) if len(ev) < steps else ev[:steps]
    except Exception as e:
        logger.warning(f"Could not extract EV charging for {agent_name}: {e}. Using zeros.")
        ev = np.zeros(steps, dtype=float)

    try:
        building = _extract_building_load_kwh(env)
        if len(building) != steps:
            building = np.pad(building, (0, steps - len(building))) if len(building) < steps else building[:steps]
    except Exception as e:
        logger.warning(f"Could not extract building load for {agent_name}: {e}. Using zeros.")
        building = np.zeros(steps, dtype=float)

    try:
        pv = _extract_pv_generation_kwh(env)
        if len(pv) != steps:
            pv = np.pad(pv, (0, steps - len(pv))) if len(pv) < steps else pv[:steps]
    except Exception as e:
        logger.warning(f"Could not extract PV generation for {agent_name}: {e}. Using zeros.")
        pv = np.zeros(steps, dtype=float)

    try:
        ci = _extract_carbon_intensity(env, default_value=carbon_intensity_kg_per_kwh)
        if len(ci) != steps:
            ci = np.pad(ci, (0, steps - len(ci)), constant_values=carbon_intensity_kg_per_kwh) if len(ci) < steps else ci[:steps]
    except Exception as e:
        logger.warning(f"Could not extract carbon intensity for {agent_name}: {e}. Using default {carbon_intensity_kg_per_kwh}.")
        ci = np.full(steps, carbon_intensity_kg_per_kwh, dtype=float)

    carbon = float(np.sum(grid_import * ci))

    sim_years = (steps * seconds_per_time_step) / (365.0 * 24.0 * 3600.0)

    # Calcular métricas multiobjetivo post-hoc
    mo_metrics = {
        "priority": multi_objective_priority if use_multi_objective else "none",
        "r_co2_mean": 0.0,
        "r_cost_mean": 0.0,
        "r_solar_mean": 0.0,
        "r_ev_mean": 0.0,
        "r_grid_mean": 0.0,
        "reward_total_mean": 0.0,
    }

    reward_components: List[Dict[str, float]] = []
    if use_multi_objective and reward_tracker is not None:
        # CRÍTICO: Crear una nueva instancia limpia para calcular métricas desde cero
        # La instancia anterior puede estar contaminada con estados previos
        try:
            from iquitos_citylearn.oe3.rewards import MultiObjectiveReward, MultiObjectiveWeights
            # Recrear el tracker con la configuración correcta usando los pesos multiobjetivo
            # ✓ CORREGIDO 2026-01-30: Usar co2_focus para obtener weights 0.75
            weights = MultiObjectiveWeights(
                co2=0.75,   # ✓ CORREGIDO
                cost=0.05,  # ✓ CORREGIDO
                solar=0.10, # ✓ CORREGIDO
                ev_satisfaction=0.05,  # ✓ CORREGIDO
                grid_stability=0.05
            )
            clean_tracker = MultiObjectiveReward(weights=weights)
        except Exception as e:
            logger.warning(f"Could not recreate MultiObjectiveReward: {e}. Using existing tracker.")
            clean_tracker = reward_tracker

        # Calcular recompensas para cada timestep con datos REALES del episodio
        for t in range(steps):
            hour = t % 24
            ev_t = float(ev[t]) if t < len(ev) else 0.0
            _, comps = clean_tracker.compute(
                grid_import_kwh=float(grid_import[t]),
                grid_export_kwh=float(grid_export[t]),
                solar_generation_kwh=float(pv[t]) if t < len(pv) else 0.0,
                ev_charging_kwh=ev_t,
                ev_soc_avg=0.5,  # Aproximado
                bess_soc=0.5,
                hour=hour,
            )
            reward_components.append(comps)

        # Obtener métricas desde el tracker limpio
        pareto = clean_tracker.get_pareto_metrics()
        mo_metrics = {
            "priority": multi_objective_priority,
            "r_co2_mean": pareto.get("r_co2_mean", 0.0),
            "r_cost_mean": pareto.get("r_cost_mean", 0.0),
            "r_solar_mean": pareto.get("r_solar_mean", 0.0),
            "r_ev_mean": pareto.get("r_ev_mean", 0.0),
            "r_grid_mean": pareto.get("r_grid_mean", 0.0),
            "reward_total_mean": pareto.get("reward_total_mean", 0.0),
            "co2_total_kg": pareto.get("co2_total_kg", carbon),
            "cost_total_usd": pareto.get("cost_total_usd", 0.0),
        }
        logger.info(f"[MULTIOBJETIVO] Métricas (CLEAN): R_total={mo_metrics['reward_total_mean']:.4f}, "
                   f"R_CO2={mo_metrics['r_co2_mean']:.4f}, R_cost={mo_metrics['r_cost_mean']:.4f}")

    ts = pd.DataFrame(
        {
            "net_grid_kwh": net,
            "grid_import_kwh": grid_import,
            "grid_export_kwh": grid_export,
            "ev_charging_kwh": ev,
            "building_load_kwh": building,
            "pv_generation_kwh": pv,
            "carbon_intensity_kg_per_kwh": ci,
        }
    )
    ts_path = out_dir / f"timeseries_{agent_name}.csv"
    ts.to_csv(ts_path, index=False)

    if trace_obs is not None and trace_actions is not None:
        n_trace = min(
            steps,
            trace_obs.shape[0],
            trace_actions.shape[0],
            len(trace_rewards),
        )
        obs_df = pd.DataFrame(trace_obs[:n_trace], columns=trace_obs_names)
        act_df = pd.DataFrame(trace_actions[:n_trace], columns=trace_action_names)
        trace_df = pd.concat([obs_df, act_df], axis=1)
        trace_df.insert(0, "step", np.arange(n_trace))
        trace_df["reward_env"] = trace_rewards[:n_trace]
        trace_df["grid_import_kwh"] = grid_import[:n_trace]
        trace_df["grid_export_kwh"] = grid_export[:n_trace]
        trace_df["ev_charging_kwh"] = ev[:n_trace]
        trace_df["building_load_kwh"] = building[:n_trace]
        trace_df["pv_generation_kwh"] = pv[:n_trace]
        if reward_components:
            comps_df = pd.DataFrame(reward_components[:n_trace])
            trace_df = pd.concat([trace_df, comps_df], axis=1)
            if "reward_total" in comps_df.columns:
                trace_df["penalty_total"] = np.clip(-comps_df["reward_total"].values, 0.0, None)
        trace_path = out_dir / f"trace_{agent_name}.csv"
        trace_df.to_csv(trace_path, index=False)

        if training_dir is not None:
            summary_dir = training_dir.parent
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / "agent_episode_summary.csv"
            md_path = summary_dir / "agent_episode_summary.md"

            reward_env_mean = float(np.mean(trace_df["reward_env"])) if "reward_env" in trace_df.columns else 0.0
            reward_total_mean = float(np.mean(trace_df["reward_total"])) if "reward_total" in trace_df.columns else 0.0
            penalty_total_mean = float(np.mean(trace_df["penalty_total"])) if "penalty_total" in trace_df.columns else 0.0

            summary_row = {
                "agent": agent_name,
                "steps": int(n_trace),
                "reward_env_mean": reward_env_mean,
                "reward_total_mean": reward_total_mean,
                "penalty_total_mean": penalty_total_mean,
            }

            if summary_path.exists():
                existing = pd.read_csv(summary_path)
                existing = existing[existing["agent"] != agent_name]
                updated = pd.concat([existing, pd.DataFrame([summary_row])], ignore_index=True)
            else:
                updated = pd.DataFrame([summary_row])

            updated = updated.sort_values("agent").reset_index(drop=True)
            updated.to_csv(summary_path, index=False)
            md = updated.to_markdown(index=False)
            md_path.write_text(md, encoding="utf-8")

    result = SimulationResult(
        agent=agent_name,
        steps=int(steps),
        seconds_per_time_step=int(seconds_per_time_step),
        simulated_years=float(sim_years),
        grid_import_kwh=float(grid_import.sum()),
        grid_export_kwh=float(grid_export.sum()),
        net_grid_kwh=float(net.sum()),
        ev_charging_kwh=float(np.clip(ev, 0.0, None).sum()),
        building_load_kwh=float(building.sum()),
        pv_generation_kwh=float(pv.sum()),
        carbon_kg=float(carbon),
        results_path=str((out_dir / f"result_{agent_name}.json").resolve()),
        timeseries_path=str(ts_path.resolve()),
        # Métricas multiobjetivo - Usar cast explícito para satisfacer type checker
        multi_objective_priority=str(mo_metrics.get("priority", "balanced")),  # type: ignore
        reward_co2_mean=float(mo_metrics.get("r_co2_mean", 0.0)),  # type: ignore
        reward_cost_mean=float(mo_metrics.get("r_cost_mean", 0.0)),  # type: ignore
        reward_solar_mean=float(mo_metrics.get("r_solar_mean", 0.0)),  # type: ignore
        reward_ev_mean=float(mo_metrics.get("r_ev_mean", 0.0)),  # type: ignore
        reward_grid_mean=float(mo_metrics.get("r_grid_mean", 0.0)),  # type: ignore
        reward_total_mean=float(mo_metrics.get("reward_total_mean", 0.0)),  # type: ignore
    )

    Path(result.results_path).write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")
    return result

