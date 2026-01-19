#!/usr/bin/env python
"""
DEPRECATED: Usar train_tier2_v2_gpu.py en su lugar.

Este script es legacy. Para entrenamiento TIER 2 V2:
  python ../train_tier2_v2_gpu.py

La nueva arquitectura proporciona:
- Recompensas normalizadas [-1, 1]
- Entropy coef fijo (0.01)
- LR dinámico por hora
- Observables enriquecidos
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

logger.warning("✗ Este script es DEPRECATED")
logger.warning("✓ Usar: python train_tier2_v2_gpu.py")
sys.exit(1)


def find_latest_checkpoint(checkpoint_dir: Path, prefix: str):
    """Este archivo es DEPRECATED. Los checkpoints se guardan en train_tier2_v2_gpu.py"""
    return None

    
    logger.info("=" * 60)
    logger.info("✓ TODOS LOS ENTRENAMIENTOS COMPLETADOS")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
