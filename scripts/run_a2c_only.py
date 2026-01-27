#!/usr/bin/env python
"""
Script: Entrenamiento A2C ÚNICAMENTE (Saltea SAC y PPO)
========================================================

Ejecuta SOLO el entrenamiento de A2C, omitiendo:
  ✗ Baseline (ya calculado)
  ✗ SAC (ya completado)
  ✗ PPO (ya completado)

Uso:
  python -m scripts.run_a2c_only --config configs/default.yaml
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Validar Python 3.11 EXACTAMENTE (NO 3.12, NO 3.13)
if sys.version_info[:2] != (3, 11):
    print(f"ERROR: Python 3.11 EXACTAMENTE requerido")
    print(f"Tienes: Python {sys.version_info[0]}.{sys.version_info[1]}")
    print(f"NO se soportan: 3.12, 3.13, etc")
    sys.exit(1)

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all


def main(config_path: str) -> int:
    """
    Entrenamiento A2C solamente.

    Args:
        config_path: Ruta a configs/default.yaml

    Returns:
        0 si exitoso, 1 si error
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("=" * 80)
        logger.info("ENTRENAMIENTO A2C UNICAMENTE")
        logger.info("=" * 80)
        logger.info("[SALTANDO] Baseline (ya calculado)")
        logger.info("[SALTANDO] SAC (ya completado)")
        logger.info("[SALTANDO] PPO (ya completado)")
        logger.info("[INICIANDO] A2C training...")
        logger.info("=" * 80)

        # Cargar config + RuntimePaths
        logger.info("[CONFIG] Cargando desde {}".format(config_path))
        cfg, rp = load_all(config_path)
        oe3_cfg = cfg["oe3"]

        # Construir dataset si no existe
        dataset_name = cfg["oe3"]["dataset"]["name"]
        processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

        logger.info("[DATASET] Verificando...")
        if processed_dataset_dir.exists():
            logger.info("[DATASET] Ya existe ✓")
            dataset_dir = processed_dataset_dir
        else:
            logger.info("[DATASET] Construyendo desde OE2...")
            built = build_citylearn_dataset(
                cfg=cfg,
                _raw_dir=rp.raw_dir,
                interim_dir=rp.interim_dir,
                processed_dir=rp.processed_dir,
            )
            dataset_dir = built.dataset_dir

        # Rutas necesarias
        schema_pv = dataset_dir / "schema_pv_bess.json"
        out_dir = rp.outputs_dir / "oe3" / "simulations"
        training_dir = rp.analyses_dir / "oe3" / "training"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Parámetros globales
        project_seed = int(cfg["project"].get("seed", 42))
        seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
        ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

        # Configuración A2C
        eval_cfg = cfg["oe3"]["evaluation"]
        a2c_cfg = eval_cfg.get("a2c", {})

        a2c_episodes = a2c_cfg.get("episodes")
        if a2c_episodes is not None:
            a2c_timesteps = int(a2c_episodes) * 8760
        else:
            a2c_timesteps = int(a2c_cfg.get("timesteps", 8760))

        a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 1000))
        a2c_n_steps = int(a2c_cfg.get("n_steps", 512))
        a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
        a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
        a2c_device = a2c_cfg.get("device")
        a2c_resume = bool(a2c_cfg.get("resume_checkpoints", False))
        a2c_log_interval = int(a2c_cfg.get("log_interval", 2000))
        mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))

        # Entrenar SOLO A2C
        logger.info("[A2C] Iniciando entrenamiento...")
        logger.info(f"[A2C] Timesteps: {a2c_timesteps}, Episodes: {a2c_episodes or a2c_timesteps // 8760}")

        result = simulate(
            schema_path=schema_pv,
            agent_name="A2C",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            a2c_log_interval=a2c_log_interval,
            a2c_resume_checkpoints=a2c_resume,
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )

        logger.info("═" * 80)
        logger.info("[A2C] ✓ Entrenamiento completado")
        logger.info("═" * 80)
        logger.info("[RESULTADOS] Guardados en: {}".format(out_dir))
        logger.info("[CHECKPOINTS] Guardados en: {}".format(training_dir))

        return 0

    except Exception as e:
        logger.error(f"[ERROR] {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Entrenar SOLO A2C (saltear SAC, PPO, baseline)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta a archivo de configuración",
    )
    args = parser.parse_args()

    sys.exit(main(args.config))
