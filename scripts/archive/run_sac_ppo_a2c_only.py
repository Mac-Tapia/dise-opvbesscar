#!/usr/bin/env python
"""
Entrenamiento secuencial: SAC → PPO → A2C (sin Uncontrolled ni Baseline)

Relanza el entrenamiento con las correcciones de:
1. Cálculo correcto de consumo solar (no solar disponible)
2. Criterios duales de CO₂ (indirecto + directo)
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

logger = logging.getLogger(__name__)


def main() -> None:
    # Verificar Python 3.11
    if sys.version_info[:2] != (3, 11):
        logger.warning(f"Python 3.11 recomendado, tienes {sys.version_info[0]}.{sys.version_info[1]}")

    ap = argparse.ArgumentParser(description="Entrenamiento SAC+PPO+A2C (sin Uncontrolled/Baseline)")
    ap.add_argument("--config", default="configs/default.yaml", help="Config YAML path")
    ap.add_argument("--sac-episodes", type=int, default=3, help="SAC episodios")
    ap.add_argument("--ppo-episodes", type=int, default=3, help="PPO episodios")
    ap.add_argument("--a2c-episodes", type=int, default=3, help="A2C episodios")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    logger.info("="*80)
    logger.info("ENTRENAMIENTO SAC+PPO+A2C (Correcciones: Solar Correcto + CO₂ Dual)")
    logger.info("="*80)

    # OPTIMIZACIÓN MEJORADA: Verificar dataset completo (schema + CSVs)
    dataset_name = cfg["oe3"]["dataset"]["name"]
    dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    schema_pv = dataset_dir / "schema_pv_bess.json"

    dataset_valid = False
    if schema_pv.exists():
        # Verificar que exista al menos Building_1.csv (debe tener 8760 filas)
        building_csv = dataset_dir / "Building_1.csv"
        if building_csv.exists():
            try:
                df = pd.read_csv(building_csv)
                if len(df) == 8760:
                    dataset_valid = True
                    logger.info(f"✓ Dataset válido encontrado: {schema_pv}")
                    logger.info(f"  Building_1.csv: {len(df)} filas (correcto)")
                    logger.info("  Saltando regeneración de dataset (ahorro ~30 segundos)")
                else:
                    logger.warning(f"⚠ Building_1.csv tiene {len(df)} filas (esperado: 8760)")
            except Exception as e:
                logger.warning(f"⚠ Error validando dataset: {e}")

    if not dataset_valid:
        logger.info("🔧 Regenerando dataset completo...")
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        dataset_dir = built.dataset_dir
        schema_pv = dataset_dir / "schema_pv_bess.json"

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuration
    eval_cfg = cfg["oe3"]["evaluation"]
    resume_checkpoints_global = False
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})
    a2c_cfg = eval_cfg.get("a2c", {})

    sac_episodes = args.sac_episodes or int(sac_cfg.get("episodes", 3))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_learning_rate = float(sac_cfg.get("learning_rate", 5e-5))

    ppo_episodes = args.ppo_episodes or int(ppo_cfg.get("episodes", 3))
    ppo_batch_size = int(ppo_cfg.get("batch_size", 128))
    ppo_learning_rate = float(ppo_cfg.get("learning_rate", 3e-4))

    a2c_episodes = args.a2c_episodes or int(a2c_cfg.get("episodes", 3))
    a2c_batch_size = int(a2c_cfg.get("batch_size", 128))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 7e-4))

    logger.info("\n📊 CONFIGURACIÓN:")
    logger.info(f"  SAC: {sac_episodes} episodios, batch={sac_batch_size}, lr={sac_learning_rate}")
    logger.info(f"  PPO: {ppo_episodes} episodios, batch={ppo_batch_size}, lr={ppo_learning_rate}")
    logger.info(f"  A2C: {a2c_episodes} episodios, batch={a2c_batch_size}, lr={a2c_learning_rate}")
    logger.info(f"  Dataset: {schema_pv}")

    # ============================================================================
    # 1. SAC TRAINING
    # ============================================================================
    logger.info("\n" + "="*80)
    logger.info("▶️  INICIANDO SAC (Soft Actor-Critic)")
    logger.info("="*80)

    try:
        simulate(
            schema_path=schema_pv,
            agent_name="SAC",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            sac_batch_size=sac_batch_size,
            sac_learning_rate=sac_learning_rate,
            sac_use_amp=True,
            sac_device="auto",
            sac_resume_checkpoints=resume_checkpoints_global,
        )
        logger.info("✅ SAC entrenamiento completado")
    except Exception as e:
        logger.error(f"❌ SAC entrenamiento falló: {e}", exc_info=True)
        return

    # ============================================================================
    # 2. PPO TRAINING (Auto-transition)
    # ============================================================================
    logger.info("\n" + "="*80)
    logger.info("▶️  INICIANDO PPO (Proximal Policy Optimization)")
    logger.info("="*80)

    try:
        simulate(
            schema_path=schema_pv,
            agent_name="PPO",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            ppo_batch_size=ppo_batch_size,
            ppo_use_amp=False,
            ppo_device="auto",
            ppo_resume_checkpoints=resume_checkpoints_global,
        )
        logger.info("✅ PPO entrenamiento completado")
    except Exception as e:
        logger.error(f"❌ PPO entrenamiento falló: {e}", exc_info=True)
        return

    # ============================================================================
    # 3. A2C TRAINING (Auto-transition)
    # ============================================================================
    logger.info("\n" + "="*80)
    logger.info("▶️  INICIANDO A2C (Advantage Actor-Critic)")
    logger.info("="*80)

    try:
        simulate(
            schema_path=schema_pv,
            agent_name="A2C",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            a2c_episodes=a2c_episodes,
            a2c_batch_size=a2c_batch_size,
            a2c_learning_rate=a2c_learning_rate,
            a2c_device="cpu",
        )
        logger.info("✅ A2C entrenamiento completado")
    except Exception as e:
        logger.error(f"❌ A2C entrenamiento falló: {e}", exc_info=True)
        return

    # ============================================================================
    # SUMMARY
    # ============================================================================
    logger.info("\n" + "="*80)
    logger.info("✅ ENTRENAMIENTO COMPLETO SAC+PPO+A2C")
    logger.info("="*80)
    logger.info("\n📊 Métricas finales disponibles en:")
    logger.info(f"  Simulaciones: {out_dir}")
    logger.info(f"  Entrenamiento: {training_dir}")
    logger.info(f"  Checkpoints: checkpoints/{{SAC,PPO,A2C}}/")

    logger.info("\n🎯 Para comparar agentes:")
    logger.info("  python -m scripts.run_oe3_co2_table --config configs/default.yaml")


if __name__ == "__main__":
    main()
