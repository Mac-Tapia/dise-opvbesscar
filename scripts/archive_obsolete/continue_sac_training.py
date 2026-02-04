#!/usr/bin/env python
"""
Continuar entrenamiento SAC desde checkpoint (si existe) o desde cero.
Diseñado para evitar interrupciones y permitir entrenamiento prolongado.
"""
from __future__ import annotations

from pathlib import Path
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Ejecutar entrenamiento SAC con opción de resume."""
    from scripts._common import load_all
    from iquitos_citylearn.oe3.simulate import simulate

    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 ENTRENAMIENTO SAC CON RESUME (CONTINUACIÓN DESDE CHECKPOINT)")
    logger.info("=" * 80)
    logger.info("")

    try:
        cfg, rp = load_all('configs/default.yaml')
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    schema_path = rp.processed_dir / 'citylearn' / 'iquitos_ev_mall' / 'schema.json'
    if not schema_path.exists():
        logger.error(f"❌ Dataset no encontrado: {schema_path}")
        logger.info("Ejecuta: python -m scripts.run_oe3_build_dataset")
        sys.exit(1)
    # Configuración OE3
    carbon_intensity = float(cfg['oe3']['grid']['carbon_intensity_kg_per_kwh'])
    seconds_per_ts = int(cfg['project']['seconds_per_time_step'])

    # SAC: 3 episodios para entrenamiento limpio
    sac_episodes = 3  # ✅ CONFIGURADO: 3 episodios para entrenamiento limpio
    sac_batch_size = 256
    sac_learning_rate = 5e-5
    sac_checkpoint_freq = 500  # Guardar cada 500 steps

    out_dir = rp.oe3_simulations_dir / 'sac_continued'
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("")
    logger.info("[1/1] 🎯 Ejecutando entrenamiento SAC (3 episodios, con resume de checkpoint)...")
    logger.info("")

    result = simulate(
        schema_path=schema_path,
        agent_name='SAC',
        out_dir=out_dir,
        training_dir=rp.checkpoints_dir,
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_ts,
        # SAC Config
        sac_episodes=sac_episodes,
        sac_batch_size=sac_batch_size,
        sac_learning_rate=sac_learning_rate,
        sac_checkpoint_freq_steps=sac_checkpoint_freq,
        sac_resume_checkpoints=True,  # ← CLAVE: Resume si existe checkpoint
        sac_device='auto',
        sac_use_amp=True,
        # Multi-objective
        use_multi_objective=True,
        multi_objective_priority='co2_focus',
        # Skip others
        deterministic_eval=True,
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ ENTRENAMIENTO SAC COMPLETADO")
    logger.info("=" * 80)
    logger.info(f"Agent: {result.agent}")
    logger.info(f"Episodios procesados: {result.steps} timesteps (~{result.simulated_years:.2f} años)")
    logger.info(f"Grid import: {result.grid_import_kwh:,.0f} kWh")
    logger.info(f"PV generation: {result.pv_generation_kwh:,.0f} kWh")
    logger.info(f"EV charging: {result.ev_charging_kwh:,.0f} kWh")
    logger.info(f"CO₂ emissions: {result.carbon_kg:,.0f} kg")
    logger.info(f"Results: {result.results_path}")
    logger.info(f"Timeseries: {result.timeseries_path}")
    logger.info("=" * 80)
    logger.info("")

if __name__ == '__main__':
    main()
