from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import json
import logging

import numpy as np
import pandas as pd

from iquitos_citylearn.oe3.agents import (
    UncontrolledChargingAgent, 
    make_basic_ev_rbc, 
    make_sac,
    make_no_control,
    make_ppo,
    make_a2c,
    SACConfig,
    PPOConfig,
    A2CConfig,
    # Multiobjetivo
    MultiObjectiveReward,
    IquitosContext,
    create_iquitos_reward_weights,
)

logger = logging.getLogger(__name__)

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
    try:
        return CityLearnEnv(schema=str(schema_path))  # type: ignore[call-arg]
    except TypeError:
        return CityLearnEnv(schema_path=str(schema_path))  # type: ignore[call-arg]

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
        names: List[str] = []
        for key, value in obs.items():
            arr = np.array(value, dtype=np.float32).ravel()
            values.append(arr)
            names.extend([f"obs_{key}_{i:03d}" for i in range(len(arr))])
        return np.concatenate(values) if values else np.array([], dtype=np.float32), names
    if isinstance(obs, (list, tuple)):
        values = []
        names: List[str] = []
        for idx, value in enumerate(obs):
            arr = np.array(value, dtype=np.float32).ravel()
            values.append(arr)
            names.extend([f"obs_{idx}_{i:03d}" for i in range(len(arr))])
        return np.concatenate(values) if values else np.array([], dtype=np.float32), names
    arr = np.array(obs, dtype=np.float32).ravel()
    names = [f"obs_{i:03d}" for i in range(len(arr))]
    return arr, names


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


def _run_episode_with_trace(
    env: Any,
    agent: Any,
    deterministic: bool = True,
) -> Tuple[np.ndarray, np.ndarray, List[float], List[str], List[str]]:
    obs, _ = env.reset()
    done = False
    obs_rows: List[np.ndarray] = []
    action_rows: List[np.ndarray] = []
    rewards: List[float] = []
    obs_names: List[str] = []
    action_names: List[str] = []

    while not done:
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

        obs, reward, terminated, truncated, _ = env.step(action)
        if isinstance(reward, (list, tuple)):
            reward_val = float(sum(reward))
        else:
            reward_val = float(reward)
        rewards.append(reward_val)
        done = bool(terminated or truncated)

    obs_arr = np.vstack(obs_rows) if obs_rows else np.zeros((0, 0), dtype=np.float32)
    action_arr = np.vstack(action_rows) if action_rows else np.zeros((0, 0), dtype=np.float32)
    return obs_arr, action_arr, rewards, obs_names, action_names


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
        import matplotlib.pyplot as plt
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
    ppo_timesteps: int = 100000,
    deterministic_eval: bool = True,
    use_multi_objective: bool = True,
    multi_objective_priority: str = "balanced",
    sac_device: Optional[str] = None,
    sac_prefer_citylearn: bool = False,
    ppo_device: Optional[str] = None,
    ppo_target_kl: Optional[float] = None,
    ppo_kl_adaptive: bool = True,
    ppo_log_interval: int = 1000,
    sac_checkpoint_freq_steps: int = 0,
    ppo_checkpoint_freq_steps: int = 0,
    a2c_timesteps: int = 0,
    a2c_checkpoint_freq_steps: int = 0,
    a2c_n_steps: int = 256,
    a2c_learning_rate: float = 3e-4,
    a2c_entropy_coef: float = 0.01,
    a2c_device: Optional[str] = None,
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

    env = _make_env(schema_path)
    
    # Configurar recompensa multiobjetivo
    reward_tracker: Optional[MultiObjectiveReward] = None
    if use_multi_objective:
        weights = create_iquitos_reward_weights(multi_objective_priority)
        context = IquitosContext(
            co2_factor_kg_per_kwh=carbon_intensity_kg_per_kwh,
        )
        reward_tracker = MultiObjectiveReward(weights, context)
        logger.info(f"[MULTIOBJETIVO] Prioridad: {multi_objective_priority}")
        logger.info(f"[MULTIOBJETIVO] Pesos: CO2={weights.co2:.2f}, Costo={weights.cost:.2f}, "
                   f"Solar={weights.solar:.2f}, EV={weights.ev_satisfaction:.2f}, Grid={weights.grid_stability:.2f}")

    # Choose agent
    agent: Any
    trace_obs: Optional[np.ndarray] = None
    trace_actions: Optional[np.ndarray] = None
    trace_rewards: List[float] = []
    trace_obs_names: List[str] = []
    trace_action_names: List[str] = []
    if agent_name.lower() == "uncontrolled":
        agent = UncontrolledChargingAgent(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=True
        )
    elif agent_name.lower() in ["nocontrol", "no_control"]:
        agent = make_no_control(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=True
        )
    elif agent_name.lower() in ["basicevrbc", "rbc", "basic_evrbc"]:
        agent = make_basic_ev_rbc(env)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=True
        )
    elif agent_name.lower() == "sac":
        try:
            sac_kwargs: Dict[str, Any] = {}
            if sac_device:
                sac_kwargs["device"] = sac_device
            if seed is not None:
                sac_kwargs["seed"] = seed
            sac_progress_path = None
            if progress_dir is not None:
                sac_progress_path = progress_dir / "sac_progress.csv"
                sac_progress_path.parent.mkdir(parents=True, exist_ok=True)
                if sac_progress_path.exists():
                    sac_progress_path.unlink()
            sac_checkpoint_dir = None
            if training_dir is not None and sac_checkpoint_freq_steps > 0:
                sac_checkpoint_dir = training_dir / "checkpoints" / "sac"
            sac_config = SACConfig(
                episodes=sac_episodes,
                batch_size=256,
                learning_rate=3e-4,
                gamma=0.99,
                tau=0.005,
                hidden_sizes=(256, 256),
                checkpoint_dir=str(sac_checkpoint_dir) if sac_checkpoint_dir else None,
                checkpoint_freq_steps=int(sac_checkpoint_freq_steps),
                progress_path=str(sac_progress_path) if sac_progress_path else None,
                prefer_citylearn=bool(sac_prefer_citylearn),
                **sac_kwargs,
            )
            agent = make_sac(env, config=sac_config)
        except Exception as e:
            logger.warning("SAC agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = UncontrolledChargingAgent(env)
        # Train
        if hasattr(agent, "learn"):
            try:
                agent.learn(episodes=sac_episodes)
            except TypeError:
                agent.learn(sac_episodes)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=deterministic_eval
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
            ppo_checkpoint_dir = None
            if training_dir is not None and ppo_checkpoint_freq_steps > 0:
                ppo_checkpoint_dir = training_dir / "checkpoints" / "ppo"
            ppo_config = PPOConfig(
                train_steps=ppo_timesteps,
                n_steps=2048,
                batch_size=64,
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
                target_kl=ppo_target_kl,
                kl_adaptive=ppo_kl_adaptive,
                log_interval=int(ppo_log_interval),
                **ppo_kwargs,
            )
            agent = make_ppo(env, config=ppo_config)
            if hasattr(agent, "learn"):
                agent.learn(total_timesteps=ppo_timesteps)
        except Exception as e:
            logger.warning("PPO agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = UncontrolledChargingAgent(env)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=deterministic_eval
        )
    elif agent_name.lower() == "a2c":
        try:
            a2c_kwargs: Dict[str, Any] = {}
            if a2c_device:
                a2c_kwargs["device"] = a2c_device
            if seed is not None:
                a2c_kwargs["seed"] = seed
            a2c_checkpoint_dir = None
            if training_dir is not None and a2c_checkpoint_freq_steps > 0:
                a2c_checkpoint_dir = training_dir / "checkpoints" / "a2c"
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
                gamma=0.99,
                gae_lambda=1.0,
                ent_coef=float(a2c_entropy_coef),
                hidden_sizes=(256, 256),
                checkpoint_dir=str(a2c_checkpoint_dir) if a2c_checkpoint_dir else None,
                checkpoint_freq_steps=int(a2c_checkpoint_freq_steps),
                progress_path=str(a2c_progress_path) if a2c_progress_path else None,
                **a2c_kwargs,
            )
            agent = make_a2c(env, config=a2c_config)
            if hasattr(agent, "learn"):
                agent.learn(total_timesteps=a2c_steps)
        except Exception as e:
            logger.warning("A2C agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = UncontrolledChargingAgent(env)
        _save_training_artifacts(agent_name, agent, training_dir)
        trace_obs, trace_actions, trace_rewards, trace_obs_names, trace_action_names = _run_episode_with_trace(
            env, agent, deterministic=deterministic_eval
        )
    else:
        raise ValueError(f"Unknown agent_name: {agent_name}")

    net = _extract_net_grid_kwh(env)
    grid_import = np.clip(net, 0.0, None)
    grid_export = np.clip(-net, 0.0, None)

    # Asegurar que todos los arrays tengan la misma longitud
    steps = len(net)
    
    ev = _extract_ev_charging_kwh(env)
    building = _extract_building_load_kwh(env)
    pv = _extract_pv_generation_kwh(env)
    ci = _extract_carbon_intensity(env, default_value=carbon_intensity_kg_per_kwh)
    
    # Normalizar longitudes (usar zeros si difiere)
    ev = ev[:steps] if len(ev) >= steps else np.pad(ev, (0, steps - len(ev)))
    building = building[:steps] if len(building) >= steps else np.pad(building, (0, steps - len(building)))
    pv = pv[:steps] if len(pv) >= steps else np.pad(pv, (0, steps - len(pv)))
    ci = ci[:steps] if len(ci) >= steps else np.pad(ci, (0, steps - len(ci)), constant_values=carbon_intensity_kg_per_kwh)

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
        # Calcular recompensas para cada timestep
        for t in range(steps):
            hour = t % 24
            ev_t = float(ev[t]) if t < len(ev) else 0.0
            _, comps = reward_tracker.compute(
                grid_import_kwh=float(grid_import[t]),
                grid_export_kwh=float(grid_export[t]),
                solar_generation_kwh=float(pv[t]) if t < len(pv) else 0.0,
                ev_charging_kwh=ev_t,
                ev_soc_avg=0.5,  # Aproximado
                bess_soc=0.5,
                hour=hour,
            )
            reward_components.append(comps)
        
        pareto = reward_tracker.get_pareto_metrics()
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
        logger.info(f"[MULTIOBJETIVO] Métricas: R_total={mo_metrics['reward_total_mean']:.4f}, "
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

            updated = updated.sort_values(by="agent").reset_index(drop=True)  # pyright: ignore[reportCallIssue]
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
        # Métricas multiobjetivo
        multi_objective_priority=mo_metrics["priority"],
        reward_co2_mean=float(mo_metrics["r_co2_mean"]),
        reward_cost_mean=float(mo_metrics["r_cost_mean"]),
        reward_solar_mean=float(mo_metrics["r_solar_mean"]),
        reward_ev_mean=float(mo_metrics["r_ev_mean"]),
        reward_grid_mean=float(mo_metrics["r_grid_mean"]),
        reward_total_mean=float(mo_metrics["reward_total_mean"]),
    )

    Path(result.results_path).write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")
    return result
