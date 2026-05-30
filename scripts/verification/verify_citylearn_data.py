#!/usr/bin/env python
"""Verify current CityLearn v2 dataset completeness.

Canonical processed dataset:
    data/iquitos_ev_mall/
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _fail(message: str) -> None:
    raise SystemExit(f"[ERROR] {message}")


def main() -> None:
    dataset_dir = Path("data/iquitos_ev_mall")
    required_files = {
        "citylearnv2_combined_dataset.csv": "dataset combinado",
        "solar_generation.csv": "generación solar",
        "bess_timeseries.csv": "BESS",
        "chargers_timeseries.csv": "cargadores EV",
        "mall_demand.csv": "demanda mall",
        "co2_emissions.csv": "factores CO2",
        "tariffs_osinergmin.csv": "tarifas",
        "dataset_config_v7.json": "configuración",
    }

    print("=== VERIFICACION CITYLEARN v2 CANONICA ===\n")

    if not dataset_dir.exists():
        _fail(f"No existe {dataset_dir}. Ejecuta: python scripts/generate_oe2_datasets.py --loader-only")

    for filename, description in required_files.items():
        path = dataset_dir / filename
        if not path.exists():
            _fail(f"Falta {filename} ({description})")
        print(f"[OK] {filename}: {path.stat().st_size:,} bytes")

    print("\n=== VALIDACION DE ESTRUCTURA ===\n")

    combined = pd.read_csv(dataset_dir / "citylearnv2_combined_dataset.csv")
    solar = pd.read_csv(dataset_dir / "solar_generation.csv")
    bess = pd.read_csv(dataset_dir / "bess_timeseries.csv")
    chargers = pd.read_csv(dataset_dir / "chargers_timeseries.csv")
    mall = pd.read_csv(dataset_dir / "mall_demand.csv")
    co2 = pd.read_csv(dataset_dir / "co2_emissions.csv")
    tariffs = pd.read_csv(dataset_dir / "tariffs_osinergmin.csv")

    frames = {
        "combined": combined,
        "solar": solar,
        "bess": bess,
        "chargers": chargers,
        "mall": mall,
        "co2": co2,
        "tariffs": tariffs,
    }
    for name, df in frames.items():
        if len(df) != 8760:
            _fail(f"{name}: {len(df)} filas != 8760")
        print(f"[OK] {name}: {len(df)} filas, {len(df.columns)} columnas")

    with open(dataset_dir / "dataset_config_v7.json", encoding="utf-8") as f:
        config = json.load(f)

    ready = config.get("validation_status", {}).get("ready_for_citylearn_v2", False)
    if not ready:
        _fail("dataset_config_v7.json no marca ready_for_citylearn_v2=true")

    print("\n=== RESUMEN ===\n")
    print(f"[OK] Solar anual: {solar['energia_kwh'].sum():,.0f} kWh")
    print(f"[OK] Solar pico: {solar['potencia_kw'].max():,.2f} kW")
    print(f"[OK] BESS SOC min/max: {bess['soc_percent'].min():.1f}% / {bess['soc_percent'].max():.1f}%")
    print(f"[OK] Mall anual: {mall['mall_demand_kwh'].sum():,.0f} kWh")
    print(f"[OK] CO2 factor promedio: {co2['co2_factor_kg_kwh'].mean():.4f} kg/kWh")
    print("\n[PASS] CityLearn v2 está listo para entrenamiento RL.")


if __name__ == "__main__":
    main()
