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

# Validar Python 3.11+
if sys.version_info[:2] != (3, 11):
    print("ERROR: Python 3.11 requerido")
    sys.exit(1)

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate


def main(config_path: str) -> int:
    """
    Entrenamiento A2C solamente.

    Args:
        config_path: Ruta a configs/default.yaml

    Returns:
        0 si exitoso, 1 si error
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-5s | %(name)s | %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        logger.info("═" * 80)
        logger.info("ENTRENAMIENTO A2C ÚNICAMENTE")
        logger.info("═" * 80)
        logger.info("[SALTANDO] Baseline (ya calculado)")
        logger.info("[SALTANDO] SAC (ya completado)")
        logger.info("[SALTANDO] PPO (ya completado)")
        logger.info("[INICIANDO] A2C training...")
        logger.info("═" * 80)

        # Cargar config
        logger.info("[CONFIG] Cargando desde {}".format(config_path))
        cfg = load_config(config_path)
        paths = load_paths(cfg)

        # Construir dataset si no existe
        logger.info("[DATASET] Verificando...")
        if not (paths.outputs_dir / "schema_*.json").parent.glob("schema_*.json"):
            logger.info("[DATASET] Construyendo desde OE2...")
            build_citylearn_dataset(cfg, paths)
        else:
            logger.info("[DATASET] Ya existe ✓")

        # Entrenar SOLO A2C
        logger.info("[A2C] Iniciando entrenamiento (3 episodios)...")
        result = simulate(
            cfg=cfg,
            paths=paths,
            skip_baseline=True,      # ← SALTEAR baseline
            skip_sac=True,           # ← SALTEAR SAC
            skip_ppo=True,           # ← SALTEAR PPO
            train_a2c=True,          # ← ENTRENAR A2C
        )

        logger.info("═" * 80)
        logger.info("[A2C] ✓ Entrenamiento completado")
        logger.info("═" * 80)
        logger.info("[RESULTADOS] Guardados en: {}".format(paths.outputs_dir))
        logger.info("[CHECKPOINTS] Guardados en: {}".format(
            paths.workspace_dir / "analyses" / "oe3" / "training" / "checkpoints" / "a2c"
        ))

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
