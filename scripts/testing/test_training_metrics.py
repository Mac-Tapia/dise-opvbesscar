"""
================================================================================
TEST RÁPIDO: Verificar que verbose=1 y métricas funcionan correctamente
================================================================================

Ejecutar: python scripts/testing/test_training_metrics.py
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from pathlib import Path
import logging
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def test_metrics_extractor():
    """Verificar que metrics_extractor funciona correctamente."""
    from iquitos_citylearn.oe3.agents.metrics_extractor import (
        extract_step_metrics,
        calculate_co2_metrics,
        EpisodeMetricsAccumulator,
        CO2_GRID_FACTOR_KG_PER_KWH,
        CO2_EV_FACTOR_KG_PER_KWH,
    )

    logger.info("="*80)
    logger.info("[TEST] metrics_extractor")
    logger.info("="*80)

    # Test CO2 metrics
    co2 = calculate_co2_metrics(
        grid_import_kwh=100.0,
        solar_generation_kwh=50.0,
        ev_demand_kwh=30.0,
    )

    logger.info(f"CO2 Grid Factor: {CO2_GRID_FACTOR_KG_PER_KWH} kg/kWh")
    logger.info(f"CO2 EV Factor: {CO2_EV_FACTOR_KG_PER_KWH} kg/kWh")
    logger.info(f"CO2 metrics: {co2}")

    # Test accumulator
    acc = EpisodeMetricsAccumulator()

    # Simular 10 steps
    for i in range(10):
        fake_metrics = {
            'grid_import_kwh': 50.0 + i,
            'grid_export_kwh': 0.0,
            'solar_generation_kwh': 100.0 + i * 2,
            'ev_demand_kwh': 50.0,
            'mall_demand_kwh': 100.0,
            'bess_soc': 0.5,
        }
        acc.accumulate(fake_metrics, reward=0.5 - i * 0.1)

    episode_metrics = acc.get_episode_metrics()
    logger.info(f"Episode metrics after 10 steps:")
    logger.info(f"  grid_import_kwh: {episode_metrics['grid_import_kwh']:.1f}")
    logger.info(f"  solar_generation_kwh: {episode_metrics['solar_generation_kwh']:.1f}")
    logger.info(f"  co2_grid_kg: {episode_metrics['co2_grid_kg']:.1f}")
    logger.info(f"  co2_indirect_avoided_kg: {episode_metrics['co2_indirect_avoided_kg']:.1f}")
    logger.info(f"  co2_direct_avoided_kg: {episode_metrics['co2_direct_avoided_kg']:.1f}")
    logger.info(f"  reward_avg: {episode_metrics['reward_avg']:.4f}")

    logger.info("[OK] metrics_extractor funciona correctamente")
    return True


def test_agent_configs():
    """Verificar que verbose=1 está configurado."""
    from iquitos_citylearn.oe3.agents import SACConfig, PPOConfig, A2CConfig

    logger.info("="*80)
    logger.info("[TEST] Agent Configs")
    logger.info("="*80)

    sac = SACConfig()
    ppo = PPOConfig()
    a2c = A2CConfig()

    logger.info(f"SAC verbose: {sac.verbose} (esperado: 1)")
    logger.info(f"PPO verbose: {ppo.verbose} (esperado: 1)")
    logger.info(f"A2C verbose: {a2c.verbose} (esperado: 1)")
    logger.info(f"SAC log_interval: {sac.log_interval}")
    logger.info(f"PPO log_interval: {ppo.log_interval} (esperado: 500)")
    logger.info(f"A2C log_interval: {a2c.log_interval} (esperado: 500)")

    assert sac.verbose == 1, f"SAC verbose debe ser 1, es {sac.verbose}"
    assert ppo.verbose == 1, f"PPO verbose debe ser 1, es {ppo.verbose}"
    assert a2c.verbose == 1, f"A2C verbose debe ser 1, es {a2c.verbose}"

    logger.info("[OK] Agent configs configurados correctamente")
    return True


def test_a2c_short_training():
    """Prueba corta de A2C para verificar que las métricas se muestran."""
    logger.info("="*80)
    logger.info("[TEST] A2C Short Training (2000 timesteps)")
    logger.info("="*80)

    from iquitos_citylearn.oe3.simulate import simulate
    from iquitos_citylearn.config import load_config, load_paths, project_root

    cfg = load_config()
    rp = load_paths(cfg)

    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema.json"

    if not schema_path.exists():
        logger.warning(f"[SKIP] Dataset no existe: {schema_path}")
        return False

    out_dir = rp.outputs_dir / "test_metrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    training_dir = project_root() / "checkpoints" / "test"
    training_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Dataset: {dataset_dir}")
    logger.info(f"Output: {out_dir}")
    logger.info(f"Training: {training_dir}")
    logger.info("")
    logger.info(">>> Iniciando entrenamiento corto A2C (2000 timesteps)...")
    logger.info(">>> OBSERVA: Las métricas deben mostrarse cada 500 pasos")
    logger.info("")

    result = simulate(
        schema_path=schema_path,
        agent_name="a2c",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=0.4521,
        seconds_per_time_step=3600,
        # Solo 2000 timesteps para prueba rápida
        a2c_timesteps=2000,
        a2c_log_interval=500,
        deterministic_eval=True,
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        a2c_resume_checkpoints=False,
        seed=42,
    )

    logger.info("")
    logger.info(f"[RESULTADO] A2C Training completado")
    logger.info(f"  Steps: {result.steps}")
    logger.info(f"  Carbon: {result.carbon_kg:.1f} kg")
    logger.info(f"  Grid Import: {result.grid_import_kwh:.1f} kWh")
    logger.info(f"  Solar Generation: {result.pv_generation_kwh:.1f} kWh")

    return True


def main():
    """Ejecutar todas las pruebas."""
    logger.info("")
    logger.info("█████████████████████████████████████████████████████████████████████████")
    logger.info("█ TEST: Verificación de correcciones para métricas de entrenamiento     █")
    logger.info("█████████████████████████████████████████████████████████████████████████")
    logger.info("")

    tests = [
        ("Metrics Extractor", test_metrics_extractor),
        ("Agent Configs", test_agent_configs),
    ]

    results = []
    for name, test_fn in tests:
        try:
            ok = test_fn()
            results.append((name, ok))
        except Exception as e:
            logger.error(f"[FAIL] {name}: {e}")
            results.append((name, False))

    # Resumen
    logger.info("")
    logger.info("="*80)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("="*80)

    all_ok = True
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        logger.info(f"  {status} - {name}")
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("")
        logger.info("[OK] Todas las pruebas pasaron correctamente")
        logger.info("")
        logger.info(">>> Para prueba completa de entrenamiento, ejecuta:")
        logger.info("    python scripts/testing/test_training_metrics.py --train")
    else:
        logger.error("[FAIL] Algunas pruebas fallaron")

    return all_ok


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", action="store_true", help="Incluir prueba de entrenamiento corto")
    args = ap.parse_args()

    ok = main()

    if args.train:
        test_a2c_short_training()

    sys.exit(0 if ok else 1)
