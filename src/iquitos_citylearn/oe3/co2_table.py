from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import json
import pandas as pd

@dataclass(frozen=True)
class EmissionsFactors:
    km_per_kwh: float
    km_per_gallon: float
    kgco2_per_gallon: float
    grid_kgco2_per_kwh: float
    project_life_years: int

def load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def annualize(value: float, simulated_years: float) -> float:
    return value / max(simulated_years, 1e-9)

def allocate_grid_to_ev(grid_import_kwh: float, ev_kwh: float, building_kwh: float) -> float:
    denom = max(ev_kwh + building_kwh, 1e-9)
    return grid_import_kwh * (ev_kwh / denom)

def compute_table(summary: Dict[str, Any], factors: EmissionsFactors) -> pd.DataFrame:
    grid = summary["grid_only_result"]
    best = summary["best_result"]

    # Annual energy terms (kWh/year)
    grid_ev_kwh_y = annualize(grid["ev_charging_kwh"], grid["simulated_years"])
    grid_build_kwh_y = annualize(grid["building_load_kwh"], grid["simulated_years"])
    grid_import_kwh_y = annualize(grid["grid_import_kwh"], grid["simulated_years"])

    best_ev_kwh_y = annualize(best["ev_charging_kwh"], best["simulated_years"])
    best_build_kwh_y = annualize(best["building_load_kwh"], best["simulated_years"])
    best_import_kwh_y = annualize(best["grid_import_kwh"], best["simulated_years"])

    # Allocate grid imports to EV charging (proportional split with building load).
    grid_ev_import_kwh_y = allocate_grid_to_ev(grid_import_kwh_y, grid_ev_kwh_y, grid_build_kwh_y)
    best_ev_import_kwh_y = allocate_grid_to_ev(best_import_kwh_y, best_ev_kwh_y, best_build_kwh_y)

    # Transport service (annual km) implied by EV electricity
    km_y = grid_ev_kwh_y * factors.km_per_kwh

    # Baseline combustion
    gallons_y = km_y / factors.km_per_gallon
    base_kg_y = gallons_y * factors.kgco2_per_gallon

    # Electrified + grid
    grid_kg_y = grid_ev_import_kwh_y * factors.grid_kgco2_per_kwh

    # Electrified + PV+BESS + control
    ctrl_kg_y = best_ev_import_kwh_y * factors.grid_kgco2_per_kwh

    data = [
        ("Emisiones transporte base (combustión)", base_kg_y),
        ("Emisiones transporte electrificado + red", grid_kg_y),
        ("Emisiones transporte electrificado + FV+BESS + control", ctrl_kg_y),
    ]

    df = pd.DataFrame(data, columns=["escenario", "kgco2_anual"])
    df["tco2_anual"] = df["kgco2_anual"] / 1000.0
    df["tco2_20_anios"] = df["tco2_anual"] * factors.project_life_years

    base = df.loc[df["escenario"].str.contains("combustión"), "tco2_anual"].iloc[0]
    df["reduccion_vs_base_tco2_anual"] = base - df["tco2_anual"]
    df["reduccion_vs_base_pct"] = 100.0 * df["reduccion_vs_base_tco2_anual"] / max(base, 1e-9)

    meta = {
        "annual_km_equivalent": km_y,
        "grid_ev_import_kwh_y": grid_ev_import_kwh_y,
        "control_ev_import_kwh_y": best_ev_import_kwh_y,
        "best_agent": summary.get("best_agent"),
    }
    df.attrs.update(meta)
    return df

def write_outputs(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "co2_comparison_table.csv", index=False)

    # Minimal markdown report
    md = []
    md.append(f"# Tabla de emisiones y reducción de CO₂\n")
    md.append(f"Best agent (FV+BESS+control): **{df.attrs.get('best_agent')}**\n")
    md.append(f"Km equivalentes anuales (a partir de energía EV): {df.attrs.get('annual_km_equivalent'):.0f} km/año\n")
    md.append(df[["escenario", "tco2_anual", "tco2_20_anios", "reduccion_vs_base_pct"]].to_markdown(index=False))
    (out_dir / "co2_comparison_table.md").write_text("\n".join(md), encoding="utf-8")
