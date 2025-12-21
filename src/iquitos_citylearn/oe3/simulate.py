from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import logging

import numpy as np
import pandas as pd

from iquitos_citylearn.oe3.agents import UncontrolledChargingAgent, make_basic_ev_rbc, make_sac

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
    return series if series is not None else np.zeros_like(_extract_net_grid_kwh(env))

def _extract_ev_charging_kwh(env: Any) -> np.ndarray:
    buildings = getattr(env, "buildings", [])
    series = None
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
    return series

def _extract_carbon_intensity(env: Any, default_value: float) -> np.ndarray:
    arr = _get_first_attr(env, ["carbon_intensity", "carbon_intensity_forecast", "carbon_intensity_history"])
    if arr is not None:
        return arr
    return np.full_like(_extract_net_grid_kwh(env), float(default_value), dtype=float)

def _make_env(schema_path: Path) -> Any:
    from citylearn.citylearn import CityLearnEnv  # type: ignore
    try:
        return CityLearnEnv(schema=str(schema_path))
    except TypeError:
        return CityLearnEnv(schema_path=str(schema_path))

def _run_episode(env: Any, agent: Any, deterministic: bool = True) -> None:
    obs, _ = env.reset()
    done = False
    while not done:
        if hasattr(agent, "predict"):
            action = agent.predict(obs, deterministic=deterministic)
        elif hasattr(agent, "act"):
            action = agent.act(obs)
        else:
            action = env.action_space.sample()
        obs, _, terminated, truncated, _ = env.step(action)
        done = bool(terminated or truncated)

def simulate(
    schema_path: Path,
    agent_name: str,
    out_dir: Path,
    carbon_intensity_kg_per_kwh: float,
    seconds_per_time_step: int,
    sac_episodes: int = 5,
    deterministic_eval: bool = True,
) -> SimulationResult:
    out_dir.mkdir(parents=True, exist_ok=True)

    env = _make_env(schema_path)

    # Choose agent
    agent: Any
    if agent_name.lower() == "uncontrolled":
        agent = UncontrolledChargingAgent(env)
        _run_episode(env, agent, deterministic=True)
    elif agent_name.lower() in ["basicevrbc", "rbc", "basic_evrbc"]:
        agent = make_basic_ev_rbc(env)
        _run_episode(env, agent, deterministic=True)
    elif agent_name.lower() == "sac":
        try:
            agent = make_sac(env)
        except Exception as e:
            logger.warning("SAC agent could not be created (%s). Falling back to Uncontrolled.", e)
            agent = UncontrolledChargingAgent(env)
        # Train if learn exists
        if hasattr(agent, "learn"):
            try:
                agent.learn(episodes=sac_episodes)
            except TypeError:
                agent.learn(sac_episodes)
        _run_episode(env, agent, deterministic=deterministic_eval)
    else:
        raise ValueError(f"Unknown agent_name: {agent_name}")

    net = _extract_net_grid_kwh(env)
    grid_import = np.clip(net, 0.0, None)
    grid_export = np.clip(-net, 0.0, None)

    ev = _extract_ev_charging_kwh(env)
    building = _extract_building_load_kwh(env)
    pv = _extract_pv_generation_kwh(env)
    ci = _extract_carbon_intensity(env, default_value=carbon_intensity_kg_per_kwh)

    carbon = float(np.sum(grid_import * ci))

    steps = len(net)
    sim_years = (steps * seconds_per_time_step) / (365.0 * 24.0 * 3600.0)

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
    )

    Path(result.results_path).write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")
    return result
