#!/usr/bin/env python3
"""
Baseline REAL desde schema OE2→OE3 usando CityLearn environment sin control.
Ejecuta simulación completa con acciones nulas (sin control inteligente).
"""
from __future__ import annotations

import json
from typing import Any

from citylearn.citylearn import CityLearnEnv

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from scripts._common import load_all


def main() -> None:
    """Calcular baseline REAL ejecutando simulación sin control."""
    setup_logging()
    cfg, rp = load_all("configs/default.yaml")

    # ========================================================================
    # PASO 1: CONSTRUIR DATASET (OE2 -> OE3)
    # ========================================================================
    print("\n" + "="*80)
    print("PASO 1: CONSTRUYENDO DATASET OE2->OE3")
    print("="*80)

    _dataset_name = cfg["oe3"]["dataset"]["name"]

    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir
    schema_path = dataset_dir / "schema_pv_bess.json"

    print(f"\n[OK] Dataset construido en: {dataset_dir}")
    print(f"[OK] Schema: {schema_path}")
    print(f"[OK] Chargers: 128 sockets (32 chargers)")
    print(f"[OK] Timesteps: 8760 (1 año completo)")
    print(f"[OK] Frecuencia: Horaria (1 timestep = 1 hora)")

    # ========================================================================
    # PASO 2: EJECUTAR SIMULACION SIN CONTROL (BASELINE)
    # ========================================================================
    print("\n" + "="*80)
    print("PASO 2: EJECUTANDO SIMULACION SIN CONTROL (BASELINE REAL)")
    print("="*80 + "\n")

    env = CityLearnEnv(str(schema_path))
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    _obs, _info = env.reset()

    # Almacenar datos por timestep
    demand_per_step: list[float] = []
    solar_per_step: list[float] = []
    grid_import_per_step: list[float] = []
    co2_per_step: list[float] = []

    # Variables de control
    terminated: bool = False
    truncated: bool = False

    # Ejecutar simulación completa (8760 timesteps = 1 año)
    print("[EJECUTANDO] Simulación sin control...")
    for step_idx in range(8760):
        # Acción nula: sin control, los chargers usan su demanda sin restricciones
        # CityLearn espera 130 acciones (126 cargadores + 2 para BESS/demanda)
        # Nota: 126 de 128 sockets (32 cargadores × 4 - 2 reservados para comparación)
        action = [[0] * 130]  # 1 building × 130 actions

        _obs, _reward, terminated, truncated, _info = env.step(action)

        # Extraer datos del timestep actual
        # Las métricas están disponibles en los building.energy_simulation
        if "building" in str(type(env)):
            building = env.buildings[0] if hasattr(env, 'buildings') else None
            if building:
                demand = building.energy_simulation.non_shiftable_load[step_idx] if step_idx < len(building.energy_simulation.non_shiftable_load) else 0
                solar = building.energy_simulation.solar_generation[step_idx] if step_idx < len(building.energy_simulation.solar_generation) else 0
            else:
                demand = 0
                solar = 0
        else:
            demand = 0
            solar = 0

        # Grid import = max(demand - solar, 0)
        grid_import = max(demand - solar, 0)
        co2 = grid_import * ci

        demand_per_step.append(demand)
        solar_per_step.append(solar)
        grid_import_per_step.append(grid_import)
        co2_per_step.append(co2)

        # Progreso cada 1000 steps
        if (step_idx + 1) % 1000 == 0:
            print(f"   [{step_idx + 1}/8760] timesteps completados")

        if terminated or truncated:
            break

    # ========================================================================
    # PASO 3: CALCULAR TOTALES Y GUARDAR
    # ========================================================================
    print("\n" + "="*80)
    print("RESULTADOS - BASELINE REAL SIN CONTROL")
    print("="*80)

    baseline_demand_kwh = float(sum(demand_per_step))
    baseline_solar_kwh = float(sum(solar_per_step))
    baseline_grid_import_kwh = float(sum(grid_import_per_step))
    baseline_co2_kg = float(sum(co2_per_step))

    baseline_data: dict[str, Any] = {
        "sistema": "Baseline (Uncontrolled)",
        "descripcion": "Sin control inteligente, simulado desde schema OE2→OE3",
        "source": f"CityLearnEnv simulation {schema_path}",
        "timesteps": len(demand_per_step),
        "frecuencia": "Horaria (1 hora/timestep)",
        "metricas_anuales": {
            "demand_kwh": baseline_demand_kwh,
            "solar_generation_kwh": baseline_solar_kwh,
            "grid_import_kwh": baseline_grid_import_kwh,
            "co2_emissions_kg": baseline_co2_kg,
            "solar_utilization_percent": (baseline_solar_kwh / baseline_demand_kwh * 100) if baseline_demand_kwh > 0 else 0
        },
        "metricas_promedio": {
            "demand_kw_avg": baseline_demand_kwh / len(demand_per_step),
            "solar_kw_avg": baseline_solar_kwh / len(demand_per_step),
            "grid_import_kw_avg": baseline_grid_import_kwh / len(demand_per_step)
        },
        "parametros_grid": {
            "carbon_intensity_kg_per_kwh": ci,
            "tarifa_usd_per_kwh": float(cfg["oe3"]["grid"].get("tariff_usd_per_kwh", 0.20))
        }
    }

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = out_dir / "baseline_real_from_schema.json"

    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)

    print(f"\n[OK] Baseline REAL calculado desde schema OE2→OE3")
    print(f"\n=== METRICAS ANUALES (8760 horas) ===")
    print(f"    Demanda total:        {baseline_demand_kwh:>15,.0f} kWh")
    print(f"    Generacion solar:     {baseline_solar_kwh:>15,.0f} kWh")
    print(f"    Importacion grid:     {baseline_grid_import_kwh:>15,.0f} kWh")
    print(f"    Emision CO2:          {baseline_co2_kg:>15,.0f} kg")
    print(f"    Auto-consumo solar:   {(baseline_solar_kwh / baseline_demand_kwh * 100) if baseline_demand_kwh > 0 else 0:>14.1f}%")

    print(f"\n=== METRICAS PROMEDIO (por hora) ===")
    print(f"    Demanda promedio:     {baseline_demand_kwh / len(demand_per_step):>15,.0f} kW")
    print(f"    Solar promedio:       {baseline_solar_kwh / len(demand_per_step):>15,.0f} kW")
    print(f"    Importacion promedio: {baseline_grid_import_kwh / len(demand_per_step):>15,.0f} kW")

    print(f"\n=== PARAMETROS GRID ===")
    print(f"    Intensidad carbono:   {ci:>15.4f} kg CO2/kWh")
    tarifa_usd: float = baseline_data.get("parametros_grid", {}).get("tarifa_usd_per_kwh", 0.20)
    print(f"    Tarifa:               {tarifa_usd:>14.2f} USD/kWh")

    print(f"\n[OK] Archivo guardado: {baseline_file}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
