#!/usr/bin/env python
"""
Cálculo SIMPLE de baseline - Sin control inteligente.
Simula 1 año completo sin agentes RL.
"""
import sys
from pathlib import Path
import logging
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from citylearn.citylearn import CityLearnEnv
from scripts._common import load_config, load_paths

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def baseline_no_control(schema_path, episodes=1):
    """
    Simula SIN control inteligente (cargar al 100% siempre disponible).
    Retorna métricas CO2 y energía.
    """
    logger.info(f"[BASELINE] Cargando schema: {schema_path}")
    env = CityLearnEnv(schema_path)

    # Parámetros de CO2
    CO2_GRID_KG_PER_KWH = 0.4521  # Iquitos thermal
    CO2_CONVERSION_FACTOR = 2.146  # conversión factor

    baseline_results = {
        "episodes": episodes,
        "metrics": []
    }

    for ep in range(episodes):
        logger.info(f"\n[BASELINE] Episodio {ep+1}/{episodes}")

        obs = env.reset()
        done = False
        step = 0

        # Acumuladores
        total_grid_kwh = 0.0
        total_co2_kg = 0.0
        total_solar_kwh = 0.0
        total_ev_demand_kwh = 0.0

        while not done:
            # BASELINE: Cargar todos los chargers al máximo siempre
            # 129 acciones (1 BESS + 128 chargers individuales), todas a 1.0 = máximo poder
            action = [1.0] * 129

            obs, reward, done, info = env.step(action)
            step += 1

            # Extraer métricas del info
            if "grid_import" in info:
                grid_kw = info["grid_import"]
                total_grid_kwh += grid_kw / 1000 if grid_kw > 0 else 0

            if "solar_generation" in info:
                solar_kw = info["solar_generation"]
                total_solar_kwh += solar_kw / 1000 if solar_kw > 0 else 0

            if step % 1000 == 0:
                logger.info(f"  Paso {step}/8760 - Grid: {total_grid_kwh:.1f} kWh, CO2: {total_grid_kwh*CO2_GRID_KG_PER_KWH:.1f} kg")

        # Cálculos finales
        total_co2_kg = total_grid_kwh * CO2_GRID_KG_PER_KWH

        ep_metrics = {
            "episode": ep + 1,
            "steps": step,
            "grid_import_kwh": total_grid_kwh,
            "co2_grid_kg": total_co2_kg,
            "solar_generation_kwh": total_solar_kwh,
            "solar_utilization_percent": (total_solar_kwh / (total_solar_kwh + total_grid_kwh) * 100) if (total_solar_kwh + total_grid_kwh) > 0 else 0
        }

        baseline_results["metrics"].append(ep_metrics)

        logger.info(f"\n[BASELINE] Episodio {ep+1} COMPLETADO:")
        logger.info(f"  ✓ Grid import: {total_grid_kwh:.1f} kWh")
        logger.info(f"  ✓ CO₂ emissions: {total_co2_kg:.1f} kg")
        logger.info(f"  ✓ Solar generation: {total_solar_kwh:.1f} kWh")
        logger.info(f"  ✓ Solar utilization: {ep_metrics['solar_utilization_percent']:.2f}%")

    return baseline_results

def main():
    logger.info("="*70)
    logger.info("BASELINE CALCULATION - NO INTELLIGENT CONTROL")
    logger.info("="*70)

    # Cargar config
    cfg = load_config("configs/default.yaml")
    paths = load_paths(cfg)

    # Schema path
    schema_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    schema_file = schema_dir / "schema.json"

    if not schema_file.exists():
        logger.error(f"Schema no encontrado: {schema_file}")
        return

    # Ejecutar baseline
    results = baseline_no_control(str(schema_file), episodes=1)

    # Guardar resultados
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    baseline_file = output_dir / "baseline_results_simple.json"
    with open(baseline_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✅ Baseline guardado: {baseline_file}")

    # Mostrar resumen
    if results["metrics"]:
        m = results["metrics"][0]
        logger.info(f"\n📊 RESUMEN BASELINE:")
        logger.info(f"  Grid Import: {m['grid_import_kwh']:.0f} kWh/año")
        logger.info(f"  CO₂ Emissions: {m['co2_grid_kg']:.0f} kg/año")
        logger.info(f"  Solar: {m['solar_generation_kwh']:.0f} kWh/año")
        logger.info(f"  Solar Utilization: {m['solar_utilization_percent']:.1f}%")

if __name__ == "__main__":
    main()
