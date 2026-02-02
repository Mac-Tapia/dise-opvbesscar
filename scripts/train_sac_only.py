#!/usr/bin/env python
"""
Script para entrenar SOLO SAC saltando baseline, PPO y A2C.
Entrena desde CERO (sin reanudar desde checkpoints).
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path

# Verificar Python 3.11
if sys.version_info[:2] != (3, 11):
    print(f"❌ ERROR: Python 3.11 EXACTAMENTE requerido. Actual: {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from iquitos_citylearn.config import project_root
from scripts._common import load_all

logger = logging.getLogger(__name__)

def main():
    """Entrenar solo SAC desde cero."""
    setup_logging()

    # Cargar configuración
    logger.info("=" * 80)
    logger.info("🚀 ENTRENAMIENTO SAC SOLO (DESDE CERO)")
    logger.info("=" * 80)

    cfg, rp = load_all('configs/default.yaml')

    # Construir dataset
    logger.info("\n[1/3] Construyendo dataset CityLearn...")
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir
    schema_path = dataset_dir / 'schema.json'
    logger.info("✅ Dataset construido: %s", dataset_dir)

    # Configurar directorios de salida
    out_dir = rp.outputs_dir / 'oe3' / 'simulations'
    training_dir = project_root() / 'checkpoints'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parámetros de entrenamiento
    carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])

    # SAC configuration desde config.yaml
    eval_cfg = cfg["oe3"]["evaluation"]
    sac_cfg = eval_cfg.get("sac", {})
    sac_episodes = int(sac_cfg.get("episodes", 3))

    logger.info("\n[2/3] Configuración SAC:")
    logger.info("  - Episodes: %d", sac_episodes)
    logger.info("  - Batch Size: 256")
    logger.info("  - Learning Rate: 5e-5")
    logger.info("  - Device: auto (GPU si disponible)")
    logger.info("  - Resume: NO (Entrenar desde CERO)")
    logger.info("  - Multi-objective: Sí (CO2 focus)")

    # Entrenar SAC
    logger.info("\n[3/3] 🎯 Ejecutando entrenamiento SAC...")
    logger.info("-" * 80)

    result = simulate(
        schema_path=schema_path,
        agent_name='sac',
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_time_step,
        sac_episodes=sac_episodes,
        sac_batch_size=256,
        sac_learning_rate=5e-5,
        sac_use_amp=True,
        sac_checkpoint_freq_steps=1000,
        sac_resume_checkpoints=False,  # ⭐ NO REANUDAR - Entrenar desde CERO
        use_multi_objective=True,
        multi_objective_priority='co2_focus',
        seed=42,
    )

    # Resultados
    logger.info("-" * 80)
    logger.info("\n" + "=" * 80)
    logger.info("✅ ENTRENAMIENTO SAC COMPLETADO")
    logger.info("=" * 80)
    logger.info("\n📊 RESULTADOS:")
    logger.info("  Agent: %s", result.agent)
    logger.info("  Timesteps: %d", result.steps)
    logger.info("  Simulated Years: %.2f", result.simulated_years)
    logger.info("\n  Grid Import: %s kWh", f"{result.grid_import_kwh:,.0f}")
    logger.info("  Grid Export: %s kWh", f"{result.grid_export_kwh:,.0f}")
    logger.info("  PV Generation: %s kWh", f"{result.pv_generation_kwh:,.0f}")
    logger.info("  EV Charging: %s kWh", f"{result.ev_charging_kwh:,.0f}")
    logger.info("  Building Load: %s kWh", f"{result.building_load_kwh:,.0f}")
    logger.info("  CO₂ Emissions: %s kg", f"{result.carbon_kg:,.0f}")
    logger.info("\n  Multi-objective Metrics:")
    logger.info("    - CO₂ Reward: %.4f", result.reward_co2_mean)
    logger.info("    - Solar Reward: %.4f", result.reward_solar_mean)
    logger.info("    - Grid Reward: %.4f", result.reward_grid_mean)
    logger.info("    - Total Reward: %.4f", result.reward_total_mean)

    logger.info("\n📁 Resultados guardados:")
    logger.info("  - JSON: %s", result.results_path)
    logger.info("  - Timeseries: %s", result.timeseries_path)
    logger.info("  - Checkpoints: %s/sac/", training_dir)

    logger.info("\n" + "=" * 80)

if __name__ == '__main__':
    main()
