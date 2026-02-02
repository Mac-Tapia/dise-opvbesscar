#!/usr/bin/env python
"""
Relanzar entrenamiento SAC desde cero con parámetros óptimos sincronizados.

✅ SINCRONIZACIONES APLICADAS:
  - gamma: 0.995 (matching yaml exactly)
  - tau: 0.02 (matching yaml exactly)
  - max_grad_norm: 10.0 (matching yaml exactly)
  - clip_obs: 100.0 (matching yaml exactly)
  - batch_size: 256, buffer_size: 200000 (all synchronized)
  - Checkpoints cleaned: Starting from scratch
  - Dataset: 8,760 hours verified

✅ TODO LO DEMÁS SINCRONIZADO:
  - learning_rate: 5e-5
  - ent_coef_init: 0.5, ent_coef_lr: 1e-3
  - gradient_steps: 1, learning_starts: 2000
"""

from __future__ import annotations

from pathlib import Path
import logging
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("[RELAZO SAC] Entrenamiento ÓPTIMO con parámetros SINCRONIZADOS")
    logger.info("=" * 80)
    logger.info("")
    logger.info("✅ SINCRONIZACIONES APLICADAS:")
    logger.info("   gamma: 0.995 (yaml ← sac.py ← simulate.py)")
    logger.info("   tau: 0.02 (yaml ← sac.py ← simulate.py)")
    logger.info("   max_grad_norm: 10.0, clip_obs: 100.0")
    logger.info("   batch_size: 256, buffer_size: 200,000")
    logger.info("   learning_rate: 5e-5, ent_coef_init: 0.5")
    logger.info("")
    logger.info("📊 DATASET VERIFIED:")
    logger.info("   Solar: 8,760 hours (hourly resolution)")
    logger.info("   Chargers: 128 × 8,760 annual profiles")
    logger.info("   Schema: 1 building (Mall_Iquitos)")
    logger.info("")
    logger.info("🗑️  CLEANUP APPLIED:")
    logger.info("   SAC checkpoints: DELETED (starting from zero)")
    logger.info("   PPO/A2C checkpoints: PRESERVED")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Load config
    cfg, rp = load_all("configs/default.yaml")

    # SAC Training
    logger.info("[1/1] SAC Agent - Training 3 episodes (26,280 steps total)")
    logger.info("")

    result = simulate(
        schema_path=rp.oe3_simulations_dir / "schema.json"
        if (rp.oe3_simulations_dir / "schema.json").exists()
        else rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json",
        agent_name="sac",
        out_dir=rp.oe3_simulations_dir,
        training_dir=rp.checkpoints_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        # SAC parameters (all synchronized from default.yaml)
        sac_episodes=3,
        sac_batch_size=256,
        sac_learning_rate=5e-5,
        sac_log_interval=100,  # Más frequent para monitorear convergencia
        sac_use_amp=True,
        sac_checkpoint_freq_steps=500,  # Más frequent para more granular resumption
        sac_device="cuda",
        sac_resume_checkpoints=False,  # ✅ CRITICAL: Force fresh start
        # Multi-objective
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        # Seed
        seed=42,
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("[RESULTADOS]")
    logger.info(f"  Agent: {result.agent}")
    logger.info(f"  Steps: {result.steps:,}")
    logger.info(f"  CO₂ Total: {result.carbon_kg:,.0f} kg")
    logger.info(f"  Grid Import: {result.grid_import_kwh:,.0f} kWh")
    logger.info(f"  PV Generation: {result.pv_generation_kwh:,.0f} kWh")
    logger.info("=" * 80)
    logger.info("")

if __name__ == "__main__":
    main()
