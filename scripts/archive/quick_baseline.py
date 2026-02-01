#!/usr/bin/env python3
"""
Script rápido para calcular baseline sin control (referencia).
Simula situación sin control inteligente.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from iquitos_citylearn.config import load_config, RuntimePaths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from scripts._common import load_all

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    """Calcular baseline sin control."""
    cfg, rp = load_all("configs/default.yaml")
    rp.ensure()

    print("\n" + "="*80)
    print("BASELINE - SIN CONTROL INTELIGENTE")
    print("="*80)

    # Construir dataset si no existe
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

    if not processed_dataset_dir.exists():
        print("[INFO] Construyendo dataset...")
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        dataset_dir = built.dataset_dir
    else:
        dataset_dir = processed_dataset_dir
        print(f"[INFO] Usando dataset existente: {dataset_dir}")

    # Cargar datos de simulación
    building_csv = dataset_dir / "Building_1.csv"
    if not building_csv.exists():
        print(f"ERROR: No encontrado {building_csv}")
        return 1

    df = pd.read_csv(building_csv)
    print(f"[INFO] Cargados datos: {len(df)} timesteps")

    # Calcular métricas baseline
    # Sumar columnas de demanda (sin control = máximo)
    demand_cols = [c for c in df.columns if 'Electricity Demand' in c]
    if demand_cols:
        baseline_grid_import = df[demand_cols[0]].sum() if len(demand_cols) > 0 else 0
    else:
        baseline_grid_import = 0

    # CO2 = importación * factor de grid
    grid_ci = cfg.get("oe2", {}).get("grid_carbon_intensity", 0.4521)
    baseline_co2 = baseline_grid_import * grid_ci

    # Crear resumen
    summary = {
        "agent": "Baseline_Uncontrolled",
        "total_timesteps": len(df),
        "grid_import_kwh": float(baseline_grid_import),
        "co2_kg": float(baseline_co2),
        "grid_ci_kg_per_kwh": grid_ci,
        "description": "Sin control inteligente - referencia de comparación",
    }

    # Guardar
    output_file = rp.outputs_dir / "oe3" / "baseline_summary.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'BASELINE SUMMARY':^80}")
    print("-" * 80)
    print(f"  Grid Import: {summary['grid_import_kwh']:,.1f} kWh/year")
    print(f"  CO₂ Emissions: {summary['co2_kg']:,.1f} kg/year")
    print(f"  Grid CI: {summary['grid_ci_kg_per_kwh']:.4f} kg CO₂/kWh")
    print(f"  Timesteps: {summary['total_timesteps']}")
    print("-" * 80)
    print(f"✓ Baseline guardado en {output_file}")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    exit(main())
