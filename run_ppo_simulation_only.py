#!/usr/bin/env python
"""Run solo PPO simulation sin construir dataset (usa el existente)."""
from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent))

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.simulate import simulate

setup_logging()
logger = logging.getLogger(__name__)

def main():
    config_path = "configs/default.yaml"
    cfg = load_config(config_path)
    paths = load_paths(cfg)

    # Assumir que el dataset ya está construido
    dataset_dir = paths.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_pv = dataset_dir / "schema_pv_bess.json"

    if not schema_pv.exists():
        logger.error(f"Schema no encontrado: {schema_pv}")
        sys.exit(1)

    logger.info(f"Usando schema existente: {schema_pv}")
    logger.info("Lanzando simulación PPO + SAC + A2C + Uncontrolled...")

    # Simular todos los agentes
    simulate(
        schema_path=str(schema_pv),
        cfg=cfg,
        paths=paths
    )

    logger.info("✓ Simulación completada")

if __name__ == "__main__":
    main()
