#!/usr/bin/env python3
"""
Validacion estricta - Tabla 9 (operacionalizacion de variables).
Verifica que los outputs clave existan y contengan los campos requeridos.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, label: str, failures: List[str]) -> bool:
    if not path.exists():
        failures.append(f"Missing file: {label} -> {path}")
        return False
    return True


def _require_keys(data: Dict[str, Any], keys: Iterable[str], label: str, failures: List[str]) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        failures.append(f"Missing keys in {label}: {missing}")


def _require_columns(df: pd.DataFrame, cols: Iterable[str], label: str, failures: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        failures.append(f"Missing columns in {label}: {missing}")


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def main() -> int:
    failures: List[str] = []
    warnings: List[str] = []

    # OE1 - Location summary
    oe1_path = ROOT / "data" / "interim" / "oe1" / "location_summary.json"
    if _require_file(oe1_path, "OE1 location_summary", failures):
        oe1 = _read_json(oe1_path)
        _require_keys(
            oe1,
            [
                "site_name",
                "area_techada_m2",
                "area_estacionamiento_m2",
                "distance_to_substation_m",
                "vehicles_peak_motos",
                "vehicles_peak_mototaxis",
                "dwell_hours_min",
                "parking_capacity_total",
                "required_capacity_kva",
            ],
            "OE1 location_summary.json",
            failures,
        )
        if float(oe1.get("area_techada_m2", 0) or 0) <= 0:
            failures.append("OE1 area_techada_m2 must be > 0")
        if float(oe1.get("area_estacionamiento_m2", 0) or 0) <= 0:
            failures.append("OE1 area_estacionamiento_m2 must be > 0")
        if oe1.get("required_capacity_kva") in (None, 0):
            failures.append("OE1 required_capacity_kva must be > 0")

    # OE2 - Solar
    solar_path = ROOT / "data" / "interim" / "oe2" / "solar" / "solar_results.json"
    if _require_file(solar_path, "OE2 solar_results", failures):
        solar = _read_json(solar_path)
        _require_keys(
            solar,
            [
                "target_dc_kw",
                "target_ac_kw",
                "annual_kwh",
                "area_utilizada_m2",
                "performance_ratio",
            ],
            "OE2 solar_results.json",
            failures,
        )
        if float(solar.get("annual_kwh", 0) or 0) <= 0:
            failures.append("OE2 annual_kwh must be > 0")

    # OE2 - Chargers
    chargers_path = ROOT / "data" / "interim" / "oe2" / "chargers" / "chargers_results.json"
    if _require_file(chargers_path, "OE2 chargers_results", failures):
        chargers = _read_json(chargers_path)
        _require_keys(
            chargers,
            [
                "n_chargers_recommended",
                "peak_power_kw",
                "total_daily_energy_kwh",
                "potencia_total_instalada_kw",
            ],
            "OE2 chargers_results.json",
            failures,
        )
        if int(chargers.get("n_chargers_recommended", 0) or 0) <= 0:
            failures.append("OE2 n_chargers_recommended must be > 0")
        if float(chargers.get("peak_power_kw", 0) or 0) <= 0:
            failures.append("OE2 peak_power_kw must be > 0")

    # OE2 - BESS
    bess_path = ROOT / "data" / "interim" / "oe2" / "bess" / "bess_results.json"
    if _require_file(bess_path, "OE2 bess_results", failures):
        bess = _read_json(bess_path)
        _require_keys(
            bess,
            [
                "capacity_kwh",
                "nominal_power_kw",
                "dod",
                "autonomy_hours",
                "peak_load_kw",
                "sizing_mode",
            ],
            "OE2 bess_results.json",
            failures,
        )
        if float(bess.get("capacity_kwh", 0) or 0) <= 0:
            failures.append("OE2 capacity_kwh must be > 0")
        if float(bess.get("nominal_power_kw", 0) or 0) <= 0:
            failures.append("OE2 nominal_power_kw must be > 0")

    # OE3 - Dataset schema
    schema_path = ROOT / "data" / "processed" / "citylearn" / "iquitos_ev_mall" / "schema.json"
    if _require_file(schema_path, "OE3 schema.json", failures):
        schema = _read_json(schema_path)
        if not schema.get("central_agent", False):
            failures.append("Schema central_agent is not enabled")
        if not schema.get("electric_vehicles_def"):
            failures.append("Schema electric_vehicles_def is missing or empty")
        if not schema.get("buildings"):
            failures.append("Schema buildings section is missing")

    # OE3 - Simulation summary
    summary_path = ROOT / "outputs" / "oe3" / "simulations" / "simulation_summary.json"
    if _require_file(summary_path, "OE3 simulation_summary", failures):
        summary = _read_json(summary_path)
        _require_keys(
            summary,
            ["best_agent", "pv_bess_results", "grid_only_result"],
            "OE3 simulation_summary.json",
            failures,
        )

    # OE3 - CO2 tables
    co2_table_path = ROOT / "analyses" / "oe3" / "co2_comparison_table.csv"
    if _require_file(co2_table_path, "OE3 co2_comparison_table", failures):
        co2_df = _load_csv(co2_table_path)
        _require_columns(
            co2_df,
            ["escenario", "tco2_anual", "reduccion_vs_base_pct"],
            "OE3 co2_comparison_table.csv",
            failures,
        )

    breakdown_path = ROOT / "analyses" / "oe3" / "co2_breakdown.csv"
    if _require_file(breakdown_path, "OE3 co2_breakdown", failures):
        breakdown_df = _load_csv(breakdown_path)
        _require_columns(
            breakdown_df,
            ["metric", "value", "unit"],
            "OE3 co2_breakdown.csv",
            failures,
        )
        if "net_avoided_kgco2_y" in breakdown_df["metric"].values:
            net_val = float(
                breakdown_df.loc[breakdown_df["metric"] == "net_avoided_kgco2_y", "value"].iloc[0]
            )
            if net_val <= 0:
                failures.append("Net CO2 avoided is not positive (check hypothesis HG)")
        else:
            warnings.append("net_avoided_kgco2_y not found in breakdown")

    report = {
        "total_failures": len(failures),
        "failures": failures,
        "warnings": warnings,
        "status": "FAILED" if failures else "OK",
    }

    report_path = ROOT / "REPORTE_CUMPLIMIENTO.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if failures:
        print("Validation FAILED")
        for item in failures:
            print(f"- {item}")
        if warnings:
            print("\nWarnings:")
            for item in warnings:
                print(f"- {item}")
        return 1

    print("Validation OK")
    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
