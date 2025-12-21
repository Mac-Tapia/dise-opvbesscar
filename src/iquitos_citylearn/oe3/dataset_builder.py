from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import shutil
import logging
import re

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class BuiltDataset:
    dataset_dir: Path
    schema_path: Path
    building_name: str

def _find_first_building(schema: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    buildings = schema.get("buildings")
    if not isinstance(buildings, dict) or len(buildings) == 0:
        raise ValueError("schema.json does not define buildings.")
    name = list(buildings.keys())[0]
    return name, buildings[name]

def _guess_file_key(d: Dict[str, Any], contains: str) -> Optional[str]:
    for k, v in d.items():
        if isinstance(v, str) and contains in k.lower() and v.lower().endswith(".csv"):
            return k
    return None

def _discover_csv_paths(schema: Dict[str, Any], dataset_dir: Path) -> Dict[str, Path]:
    """Return best-effort mapping for common files."""
    out: Dict[str, Path] = {}
    # root-level
    for key in ["weather", "carbon_intensity", "pricing"]:
        v = schema.get(key)
        if isinstance(v, str) and v.lower().endswith(".csv"):
            out[key] = dataset_dir / v

    # building-level (first building)
    bname, b = _find_first_building(schema)
    out["building_name"] = Path(bname)

    for candidate in ["energy_simulation", "energy_simulation_file", "energy_simulation_filename"]:
        if isinstance(b.get(candidate), str) and str(b[candidate]).lower().endswith(".csv"):
            out["energy_simulation"] = dataset_dir / str(b[candidate])
            break

    # Charger simulation paths: search recursively for keys that include 'charger_simulation'
    charger_paths: List[Path] = []
    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.lower().endswith(".csv") and "charger" in k.lower() and "simulation" in k.lower():
                    charger_paths.append(dataset_dir / v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)

    walk(b)
    if charger_paths:
        out["charger_simulations"] = Path(";")  # sentinel
        out["_charger_list"] = charger_paths
    return out

def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}
    # solar
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = pd.read_csv(solar_path)
    # ev profile
    ev_path = interim_dir / "oe2" / "ev" / "perfil_horario_carga.csv"
    if ev_path.exists():
        artifacts["ev_profile_24h"] = pd.read_csv(ev_path)
    # bess
    bess_path = interim_dir / "oe2" / "bess" / "bess_results.json"
    if bess_path.exists():
        # stored as a json string from pd.Series.to_json
        artifacts["bess"] = json.loads(bess_path.read_text(encoding="utf-8"))
    return artifacts

def _repeat_24h_to_length(values_24: np.ndarray, n: int) -> np.ndarray:
    reps = int(np.ceil(n / 24))
    return np.tile(values_24, reps)[:n]

def _write_constant_series_csv(path: Path, df_template: pd.DataFrame, value: float) -> None:
    df = df_template.copy()
    # If single column, overwrite it. Otherwise try common names.
    if df.shape[1] == 1:
        col = df.columns[0]
        df[col] = value
    else:
        written = False
        for col in df.columns:
            if re.search(r"carbon|co2|intensity", col, re.IGNORECASE):
                df[col] = value
                written = True
        if not written:
            df[df.columns[-1]] = value
    df.to_csv(path, index=False)

def build_citylearn_dataset(
    cfg: Dict[str, Any],
    raw_dir: Path,
    interim_dir: Path,
    processed_dir: Path,
) -> BuiltDataset:
    """Create processed CityLearn dataset for OE3 (EV + PV + BESS).

    Strategy:
    1) Download/locate a CityLearn template dataset that already supports EVs.
    2) Copy to processed dataset directory.
    3) Overwrite time series: non_shiftable_load, solar_generation, pricing, carbon_intensity,
       and charger_simulation according to OE2 results.
    4) Update key capacities in schema (PV nominal power, BESS capacity/power, seconds_per_time_step).
    """
    try:
        from citylearn.data import DataSet  # type: ignore
    except Exception as e:
        raise ImportError(
            "CityLearn is required for OE3. Install with: pip install citylearn>=2.5.0"
        ) from e

    template_name = cfg["oe3"]["dataset"]["template_name"]
    dataset_name = cfg["oe3"]["dataset"]["name"]
    central_agent = bool(cfg["oe3"]["dataset"].get("central_agent", True))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])

    cache_dir = raw_dir / "citylearn_templates"
    cache_dir.mkdir(parents=True, exist_ok=True)

    ds = DataSet()
    template_dir = Path(ds.get_dataset(name=template_name, directory=str(cache_dir)))

    out_dir = processed_dir / "citylearn" / dataset_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(template_dir, out_dir)

    schema_path = out_dir / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    # Update schema globals
    schema["central_agent"] = central_agent
    schema["seconds_per_time_step"] = seconds_per_time_step

    # Use only the first building to keep the district minimal
    bname, b = _find_first_building(schema)
    schema["buildings"] = {bname: b}

    # Update PV + BESS sizes
    pv_dc_kw = float(cfg["oe2"]["solar"]["target_dc_kw"])
    bess_cap = None
    bess_pow = None
    artifacts = _load_oe2_artifacts(interim_dir)
    if "bess" in artifacts:
        bess_cap = float(artifacts["bess"].get("capacity_kwh", 0.0))
        bess_pow = float(artifacts["bess"].get("nominal_power_kw", 0.0))

    # Heuristic update for device keys
    if isinstance(b, dict):
        if isinstance(b.get("photovoltaic"), dict):
            b["photovoltaic"]["nominal_power"] = pv_dc_kw
        if isinstance(b.get("electrical_storage"), dict) and bess_cap is not None:
            b["electrical_storage"]["capacity"] = bess_cap
            if bess_pow is not None:
                b["electrical_storage"]["nominal_power"] = bess_pow

    # Discover and overwrite relevant CSVs
    paths = _discover_csv_paths(schema, out_dir)
    energy_path = paths.get("energy_simulation")
    if energy_path is None or not energy_path.exists():
        raise FileNotFoundError("Could not locate energy_simulation CSV in template dataset.")

    df_energy = pd.read_csv(energy_path)
    n = len(df_energy)

    # Build mall load and PV generation series for length n
    mall_energy_day = float(cfg["oe2"]["mall"]["energy_kwh_day"])
    mall_shape = cfg["oe2"]["mall"].get("shape_24h")  # may be None
    if mall_shape is None:
        # Default same as OE2 bess module
        from iquitos_citylearn.oe2.bess import default_mall_shape_24h  # local import
        mall_shape_arr = default_mall_shape_24h()
    else:
        mall_shape_arr = np.array(mall_shape, dtype=float)
        mall_shape_arr = mall_shape_arr / mall_shape_arr.sum()

    mall_24h = mall_energy_day * mall_shape_arr
    mall_series = _repeat_24h_to_length(mall_24h, n)

    # PV series per kWp (kWh/kWp per timestep). If available from OE2, use it.
    pv_per_kwp = None
    if "solar_ts" in artifacts:
        solar_ts = artifacts["solar_ts"]
        if "pv_kwh_per_kwp" in solar_ts.columns:
            pv_per_kwp = solar_ts["pv_kwh_per_kwp"].values
    if pv_per_kwp is None or len(pv_per_kwp) < n:
        # fallback: repeat mean 24h from template solar column if it exists
        pv_per_kwp = np.zeros(n, dtype=float)

    pv_per_kwp = pv_per_kwp[:n]

    # Identify columns to overwrite in energy_simulation (template-dependent names)
    def find_col(regex_list: List[str]) -> Optional[str]:
        for col in df_energy.columns:
            for rgx in regex_list:
                if re.search(rgx, col, re.IGNORECASE):
                    return col
        return None

    load_col = find_col([r"non[_ ]?shiftable", r"electricity[_ ]?load"])
    solar_col = find_col([r"solar[_ ]?generation"])

    if load_col is None:
        raise ValueError("Template energy_simulation file does not include a non_shiftable_load-like column.")
    df_energy[load_col] = mall_series

    if solar_col is not None:
        df_energy[solar_col] = pv_per_kwp
    else:
        # If no solar column exists, leave template as-is (PV device may be absent).
        logger.warning("No solar_generation-like column found; PV may be ignored by this dataset.")

    # Zero-out other end-uses if present to isolate the problem to electricity + EV + PV + BESS
    for col in df_energy.columns:
        if col == load_col or col == solar_col:
            continue
        if re.search(r"cooling|heating|dhw|hot water|gas", col, re.IGNORECASE):
            df_energy[col] = 0.0

    df_energy.to_csv(energy_path, index=False)

    # carbon intensity and pricing
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    tariff = float(cfg["oe3"]["grid"]["tariff_usd_per_kwh"])
    if (out_dir / "carbon_intensity.csv").exists():
        df_ci = pd.read_csv(out_dir / "carbon_intensity.csv")
        _write_constant_series_csv(out_dir / "carbon_intensity.csv", df_ci, ci)
        schema["carbon_intensity"] = "carbon_intensity.csv"
    elif paths.get("carbon_intensity") and paths["carbon_intensity"].exists():
        df_ci = pd.read_csv(paths["carbon_intensity"])
        _write_constant_series_csv(paths["carbon_intensity"], df_ci, ci)

    if (out_dir / "pricing.csv").exists():
        df_pr = pd.read_csv(out_dir / "pricing.csv")
        _write_constant_series_csv(out_dir / "pricing.csv", df_pr, tariff)
        schema["pricing"] = "pricing.csv"
    elif paths.get("pricing") and paths["pricing"].exists():
        df_pr = pd.read_csv(paths["pricing"])
        _write_constant_series_csv(paths["pricing"], df_pr, tariff)

    # Charger simulation (first charger only if possible)
    charger_list: List[Path] = []
    if "_charger_list" in paths:
        charger_list = paths["_charger_list"]
    # Build a generic daily charger simulation for the same length n
    opening = int(cfg["oe2"]["ev_fleet"]["opening_hour"])
    closing = int(cfg["oe2"]["ev_fleet"]["closing_hour"])

    # EV daily energy requirement from OE2 recommended profile, else 0
    ev_energy_day = 0.0
    if "ev_profile_24h" in artifacts and "energy_kwh" in artifacts["ev_profile_24h"].columns:
        ev_energy_day = float(artifacts["ev_profile_24h"]["energy_kwh"].sum())

    dt_hours = seconds_per_time_step / 3600.0
    steps_per_hour = int(round(1.0 / dt_hours))
    steps_per_day = int(round(24.0 / dt_hours))

    # Arrival/departure steps within a day
    arrival_step = opening * steps_per_hour
    departure_step = (closing + 1) * steps_per_hour  # depart after closing hour
    departure_step = min(departure_step, steps_per_day)  # clamp

    # Build schedule arrays
    state = np.full(n, 3, dtype=int)  # 3 = commuting
    ev_id = np.full(n, -1, dtype=int)
    dep_time = np.full(n, -1, dtype=int)
    req_soc = np.full(n, -0.1, dtype=float)
    arr_time = np.full(n, -1, dtype=int)
    arr_soc = np.full(n, -0.1, dtype=float)

    soc_arr = 0.20
    soc_req = 0.90

    for t in range(n):
        day_step = t % steps_per_day
        if arrival_step <= day_step < departure_step:
            state[t] = 1
            ev_id[t] = 0
            dep_time[t] = int(departure_step - day_step)
            req_soc[t] = soc_req
        else:
            state[t] = 3
            # time until next arrival
            if day_step < arrival_step:
                arr_time[t] = int(arrival_step - day_step)
            else:
                arr_time[t] = int(steps_per_day - day_step + arrival_step)
            arr_soc[t] = soc_arr

    charger_df = pd.DataFrame(
        {
            "electric_vehicle_charger_state": state,
            "electric_vehicle_id": ev_id,
            "electric_vehicle_departure_time": dep_time,
            "electric_vehicle_required_soc_departure": req_soc,
            "electric_vehicle_estimated_arrival_time": arr_time,
            "electric_vehicle_estimated_soc_arrival": arr_soc,
        }
    )

    for i, cp in enumerate(charger_list):
        if not cp.exists():
            continue
        # If multiple chargers exist, only the first is active; others always disconnected.
        if i == 0:
            charger_df.to_csv(cp, index=False)
        else:
            charger_df.assign(
                electric_vehicle_charger_state=3,
                electric_vehicle_id=-1,
                electric_vehicle_departure_time=-1,
                electric_vehicle_required_soc_departure=-0.1,
                electric_vehicle_estimated_arrival_time=arr_time,
                electric_vehicle_estimated_soc_arrival=arr_soc,
            ).to_csv(cp, index=False)

    # Save schema
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


    # --- Schema variants for emissions comparison ---
    # 1) PV+BESS (current schema.json)
    (out_dir / "schema_pv_bess.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    # 2) Grid-only variant: disable PV and BESS by setting nominal values to 0.
    schema_grid = json.loads(json.dumps(schema))
    bname2, b2 = _find_first_building(schema_grid)
    if isinstance(b2.get("photovoltaic"), dict):
        b2["photovoltaic"]["nominal_power"] = 0.0
    if isinstance(b2.get("electrical_storage"), dict):
        b2["electrical_storage"]["capacity"] = 0.0
        b2["electrical_storage"]["nominal_power"] = 0.0
    (out_dir / "schema_grid_only.json").write_text(json.dumps(schema_grid, indent=2), encoding="utf-8")

    return BuiltDataset(dataset_dir=out_dir, schema_path=schema_path, building_name=bname)
