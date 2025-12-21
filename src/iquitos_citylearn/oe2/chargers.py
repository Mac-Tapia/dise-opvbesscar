from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import math
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class ChargerSizingResult:
    scenario_id: int
    pe: float
    fc: float
    chargers_required: int
    sockets_total: int
    energy_day_kwh: float
    peak_sessions_per_hour: float
    session_minutes: float
    utilization: float
    charger_power_kw: float
    sockets_per_charger: int

def chargers_needed(
    sessions_peak_per_hour: float,
    session_minutes: float,
    utilization: float,
    sockets_per_charger: int,
) -> int:
    """Compute number of chargers required at peak.

    Each socket can serve 60 / (session_minutes / utilization) sessions per hour.
    Each charger has `sockets_per_charger` sockets.
    """
    ts_eff = session_minutes / utilization
    sessions_per_socket_per_hour = 60.0 / ts_eff
    capacity_per_charger_per_hour = sockets_per_charger * sessions_per_socket_per_hour
    return int(math.ceil(sessions_peak_per_hour / max(capacity_per_charger_per_hour, 1e-9)))

def evaluate_scenario(
    scenario_id: int,
    pe: float,
    fc: float,
    n_motos: int,
    n_mototaxis: int,
    peak_share_day: float,
    session_minutes: float,
    utilization: float,
    charger_power_kw: float,
    sockets_per_charger: int,
) -> ChargerSizingResult:
    # Peak arrivals in peak hour:
    sessions_peak = (n_motos * pe * fc) + (n_mototaxis * pe * fc)

    # Daily arrivals inferred from peak share (as in original notebook):
    arrivals_motos_day = n_motos / peak_share_day
    arrivals_mototaxis_day = n_mototaxis / peak_share_day
    ts_h = session_minutes / 60.0
    energy_session_kwh = charger_power_kw * ts_h
    energy_day = (arrivals_motos_day * pe * fc + arrivals_mototaxis_day * pe * fc) * energy_session_kwh

    chargers = chargers_needed(
        sessions_peak_per_hour=sessions_peak,
        session_minutes=session_minutes,
        utilization=utilization,
        sockets_per_charger=sockets_per_charger,
    )

    return ChargerSizingResult(
        scenario_id=scenario_id,
        pe=float(pe),
        fc=float(fc),
        chargers_required=int(chargers),
        sockets_total=int(chargers * sockets_per_charger),
        energy_day_kwh=float(energy_day),
        peak_sessions_per_hour=float(sessions_peak),
        session_minutes=float(session_minutes),
        utilization=float(utilization),
        charger_power_kw=float(charger_power_kw),
        sockets_per_charger=int(sockets_per_charger),
    )

def generate_random_scenarios(seed: int, n_scenarios: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    pe_values = np.array([0.10, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 1.0])
    fc_values = np.array([0.40, 0.50, 0.60, 0.70, 0.80, 1.0])
    pe_list = rng.choice(pe_values, size=n_scenarios, replace=True)
    fc_list = rng.choice(fc_values, size=n_scenarios, replace=True)
    return pe_list, fc_list

def select_recommended(df: pd.DataFrame) -> pd.Series:
    """Replicate notebook selection: choose p75 of chargers then max daily energy."""
    p75 = df["chargers_required"].quantile(0.75)
    df_p75 = df[df["chargers_required"] >= p75]
    return df_p75.sort_values("energy_day_kwh", ascending=False).iloc[0]

def build_hourly_profile(
    energy_day_kwh: float,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
    peak_share_day: float,
) -> pd.DataFrame:
    """Build 24h energy and power profile for EV charging.

    The original notebook allocates a fraction (peak_share_day) of daily energy to peak_hours,
    and the remainder uniformly to the remaining operating hours.
    """
    hours = list(range(24))
    operating_hours = [h for h in hours if opening_hour <= h <= closing_hour]
    hours_peak = [h for h in peak_hours if h in operating_hours]
    hours_day = len(operating_hours)
    hours_peak_n = len(hours_peak)
    hours_off = max(hours_day - hours_peak_n, 1)

    share_peak = peak_share_day
    share_off = 1.0 - share_peak

    factors = []
    for h in hours:
        if h in hours_peak:
            factors.append(share_peak / hours_peak_n)
        elif h in operating_hours:
            factors.append(share_off / hours_off)
        else:
            factors.append(0.0)

    factors = np.array(factors, dtype=float)
    # Normalize in case of rounding errors
    if factors.sum() > 0:
        factors = factors / factors.sum()

    energy_h = energy_day_kwh * factors
    power_kw = energy_h  # 1-hour timestep: kWh == kW average

    return pd.DataFrame(
        {
            "hour": hours,
            "factor": factors,
            "energy_kwh": energy_h,
            "power_kw": power_kw,
        }
    )

def run_charger_sizing(
    out_dir: Path,
    seed: int,
    n_motos: int,
    n_mototaxis: int,
    peak_share_day: float,
    session_minutes: float,
    utilization: float,
    charger_power_kw: float,
    sockets_per_charger: int,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
    n_scenarios: int = 100,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)

    pe_list, fc_list = generate_random_scenarios(seed=seed, n_scenarios=n_scenarios)

    rows = []
    for i, (pe, fc) in enumerate(zip(pe_list, fc_list), start=1):
        res = evaluate_scenario(
            scenario_id=i,
            pe=float(pe),
            fc=float(fc),
            n_motos=n_motos,
            n_mototaxis=n_mototaxis,
            peak_share_day=peak_share_day,
            session_minutes=session_minutes,
            utilization=utilization,
            charger_power_kw=charger_power_kw,
            sockets_per_charger=sockets_per_charger,
        )
        rows.append(res.__dict__)

    df = pd.DataFrame(rows).drop_duplicates(subset=["pe", "fc"]).reset_index(drop=True)
    df.to_csv(out_dir / "selection_pe_fc_completo.csv", index=False)

    # Select scenarios
    esc_min = df.sort_values("chargers_required", ascending=True).iloc[0]
    esc_max = df.sort_values("chargers_required", ascending=False).iloc[0]
    esc_rec = select_recommended(df)

    # Build hourly profile from recommended scenario
    profile = build_hourly_profile(
        energy_day_kwh=float(esc_rec["energy_day_kwh"]),
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
        peak_share_day=peak_share_day,
    )
    profile.to_csv(out_dir / "perfil_horario_carga.csv", index=False)

    summary = {
        "esc_min": esc_min.to_dict(),
        "esc_max": esc_max.to_dict(),
        "esc_rec": esc_rec.to_dict(),
        "profile_path": str((out_dir / "perfil_horario_carga.csv").resolve()),
        "scenarios_path": str((out_dir / "selection_pe_fc_completo.csv").resolve()),
    }
    (out_dir / "chargers_results.json").write_text(
        pd.Series(summary).to_json(), encoding="utf-8"
    )
    return summary
