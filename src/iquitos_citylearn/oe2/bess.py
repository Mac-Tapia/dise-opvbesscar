from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

@dataclass(frozen=True)
class BessSizingOutput:
    capacity_kwh: float
    nominal_power_kw: float
    dod: float
    c_rate: float
    surplus_kwh_day: float
    round_kwh: float
    profile_path: str

def default_mall_shape_24h() -> np.ndarray:
    # Mildly higher daytime consumption typical for retail.
    shape = np.array(
        [0.03,0.03,0.03,0.03,0.03,0.04,0.05,0.06,0.07,0.07,0.07,0.06,
         0.06,0.06,0.06,0.06,0.07,0.08,0.08,0.07,0.06,0.05,0.04,0.03],
        dtype=float
    )
    return shape / shape.sum()

def round_to_step(x: float, step: float) -> float:
    return float(np.round(x / step) * step)

def run_bess_sizing(
    out_dir: Path,
    mall_energy_kwh_day: float,
    pv_profile_24h_path: Path,
    ev_profile_24h_path: Path,
    dod: float,
    c_rate: float,
    round_kwh: float,
    mall_shape_24h: Optional[np.ndarray] = None,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)

    pv24 = pd.read_csv(pv_profile_24h_path)
    ev24 = pd.read_csv(ev_profile_24h_path)

    if mall_shape_24h is None:
        mall_shape_24h = default_mall_shape_24h()
    mall_energy_h = mall_energy_kwh_day * mall_shape_24h

    df = pd.DataFrame({"hour": np.arange(24)})
    df = df.merge(pv24[["hour", "pv_kwh"]], on="hour", how="left")
    df = df.merge(ev24[["hour", "energy_kwh"]], on="hour", how="left")
    df["pv_kwh"] = df["pv_kwh"].fillna(0.0)
    df["ev_kwh"] = df["energy_kwh"].fillna(0.0)
    df["mall_kwh"] = mall_energy_h
    df["load_kwh"] = df["ev_kwh"] + df["mall_kwh"]
    df["surplus_kwh"] = (df["pv_kwh"] - df["load_kwh"]).clip(lower=0.0)
    df["deficit_kwh"] = (df["load_kwh"] - df["pv_kwh"]).clip(lower=0.0)

    surplus_day = float(df["surplus_kwh"].sum())
    capacity_nominal = surplus_day / max(dod, 1e-9)
    capacity_nominal = round_to_step(capacity_nominal, round_kwh)
    nominal_power = float(c_rate * capacity_nominal)

    profile_path = out_dir / "bess_daily_balance_24h.csv"
    df.to_csv(profile_path, index=False)

    out = BessSizingOutput(
        capacity_kwh=float(capacity_nominal),
        nominal_power_kw=float(nominal_power),
        dod=float(dod),
        c_rate=float(c_rate),
        surplus_kwh_day=float(surplus_day),
        round_kwh=float(round_kwh),
        profile_path=str(profile_path.resolve()),
    )
    (out_dir / "bess_results.json").write_text(pd.Series(out.__dict__).to_json(), encoding="utf-8")
    return out.__dict__
