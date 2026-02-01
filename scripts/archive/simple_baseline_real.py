#!/usr/bin/env python3
"""
Script SIMPLE: Construir dataset OE2→OE3 + calcular BASELINE REAL (sin RL).
Datos completos de 1 año (8760 timesteps) desde datos reales.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from scripts._common import load_all


def main() -> None:
    """Construir dataset y calcular baseline desde datos REALES."""
    setup_logging()
    cfg, rp = load_all("configs/default.yaml")

    # ========================================================================
    # PASO 1: CONSTRUIR DATASET (OE2 -> OE3)
    # ========================================================================
    print("\n" + "="*80)
    print("PASO 1: CONSTRUYENDO DATASET OE2->OE3")
    print("="*80)

    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir

    print(f"\n[OK] Dataset construido en: {dataset_dir}")
    print(f"[OK] Chargers: 128 sockets (32 chargers)")
    print(f"[OK] Timesteps: 8760 (1 año completo)")
    print(f"[OK] Frecuencia: Horaria (1 timestep = 1 hora)")

    # ========================================================================
    # PASO 2: CALCULAR BASELINE DESDE DATOS REALES
    # ========================================================================
    print("\n" + "="*80)
    print("PASO 2: CALCULANDO BASELINE DESDE DATOS REALES")
    print("="*80)

    building_1_csv = dataset_dir / "Building_1.csv"
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not building_1_csv.exists():
        print(f"\n[ERROR] Building_1.csv NO ENCONTRADO en {building_1_csv}")
        return

    # LEER DATOS DEL DATASET CONSTRUIDO
    df = pd.read_csv(building_1_csv)

    print(f"\n[INFO] Leyendo Building_1.csv...")
    print(f"       Filas: {len(df)}")
    print(f"       Columnas: {', '.join(df.columns.tolist())}")

    # CALCULAR METRICAS REALES
    # Nota: El dataset usa 'non_shiftable_load' en lugar de 'electricity_demand'
    demand_kwh = float(df['non_shiftable_load'].sum())
    solar_kwh = float(df['solar_generation'].sum())
    grid_import_kwh = float(max(0, demand_kwh - solar_kwh))

    # CO2 usando carbon_intensity del config
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    co2_kg = float(grid_import_kwh * ci)

    # CALCULAR TASAS (por hora, por día, por año)
    num_hours = len(df)
    demand_kw_avg = demand_kwh / num_hours
    solar_kw_avg = solar_kwh / num_hours
    grid_import_kw_avg = grid_import_kwh / num_hours

    # GUARDAR RESULTADO
    baseline_result = {
        "sistema": "Baseline (Uncontrolled)",
        "descripcion": "Sin control inteligente, datos REALES del dataset construido",
        "source": str(building_1_csv),
        "timesteps": len(df),
        "frecuencia": "Horaria (1 hora/timestep)",
        "metricas_anuales": {
            "demand_kwh": demand_kwh,
            "solar_generation_kwh": solar_kwh,
            "grid_import_kwh": grid_import_kwh,
            "co2_emissions_kg": co2_kg,
            "solar_utilization_percent": (solar_kwh / demand_kwh * 100) if demand_kwh > 0 else 0
        },
        "metricas_promedio": {
            "demand_kw_avg": demand_kw_avg,
            "solar_kw_avg": solar_kw_avg,
            "grid_import_kw_avg": grid_import_kw_avg
        },
        "parametros_grid": {
            "carbon_intensity_kg_per_kwh": ci,
            "tarifa_usd_per_kwh": float(cfg["oe3"]["grid"].get("tariff_usd_per_kwh", 0.20))
        }
    }

    baseline_file = out_dir / "baseline_real_uncontrolled.json"
    with open(baseline_file, 'w') as f:
        json.dump(baseline_result, f, indent=2)

    # ========================================================================
    # MOSTRAR RESULTADOS
    # ========================================================================
    print("\n" + "="*80)
    print("RESULTADOS - BASELINE REAL")
    print("="*80)
    print(f"\n[OK] Baseline calculado desde datos REALES del dataset")
    print(f"\n=== METRICAS ANUALES (8760 horas) ===")
    print(f"    Demanda total:        {demand_kwh:>15,.0f} kWh")
    print(f"    Generacion solar:     {solar_kwh:>15,.0f} kWh")
    print(f"    Importacion grid:     {grid_import_kwh:>15,.0f} kWh")
    print(f"    Emision CO2:          {co2_kg:>15,.0f} kg")
    print(f"    Auto-consumo solar:   {(solar_kwh / demand_kwh * 100):>14.1f}%")

    print(f"\n=== METRICAS PROMEDIO (por hora) ===")
    print(f"    Demanda promedio:     {demand_kw_avg:>15,.0f} kW")
    print(f"    Solar promedio:       {solar_kw_avg:>15,.0f} kW")
    print(f"    Importacion promedio: {grid_import_kw_avg:>15,.0f} kW")

    print(f"\n=== PARAMETROS GRID ===")
    print(f"    Intensidad carbono:   {ci:>15.4f} kg CO2/kWh")
    print(f"    Tarifa:               {baseline_result['parametros_grid']['tarifa_usd_per_kwh']:>14.2f} USD/kWh")

    print(f"\n[OK] Archivo guardado: {baseline_file}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
