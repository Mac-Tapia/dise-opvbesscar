"""Pre-training validation script.

Verifica que todo esté configurado correctamente antes de iniciar entrenamiento:
- Dataset CityLearn disponible
- Agentes importables
- GPU detectada (si está disponible)
- Checkpoints accesibles
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


def check_dataset(schema_path: str) -> bool:
    """Verifica que schema CityLearn existe."""
    path = Path(schema_path)
    if not path.exists():
        logger.error("❌ Schema CityLearn no encontrado: %s", schema_path)
        return False
    logger.info("✓ Schema CityLearn: %s", path.absolute())
    return True


def check_agents() -> bool:
    """Verifica que agentes se pueden importar."""
    try:
        from iquitos_citylearn.oe3.agents import (
            detect_device,
        )
        _ = detect_device()  # Usar la función
        logger.info("✓ Agentes importados exitosamente")
        logger.info("  Device detectado: %s", detect_device())
        return True
    except (ImportError, AttributeError) as e:
        logger.error("❌ Error importando agentes: %s", e)
        return False


def check_rewards() -> bool:
    """Verifica que rewards se pueden importar."""
    try:
        from iquitos_citylearn.oe3.rewards import (
            MultiObjectiveWeights,
        )
        weights = MultiObjectiveWeights()
        logger.info("✓ Rewards importados exitosamente")
        logger.info("  Pesos: CO2=%s, Solar=%s, Cost=%s", weights.co2, weights.solar, weights.cost)
        return True
    except (ImportError, AttributeError) as e:
        logger.error("❌ Error importando rewards: %s", e)
        return False


def check_gpu() -> bool:
    """Verifica disponibilidad de GPU."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("✓ GPU disponible: %s", torch.cuda.get_device_name(0))
            logger.info("  CUDA Version: %s", torch.version.cuda)
            logger.info("  Memory: %.1f GB", torch.cuda.get_device_properties(0).total_memory / 1e9)
        else:
            logger.warning("⚠ GPU no disponible; se usará CPU")
        return True
    except ImportError:
        logger.warning("⚠ PyTorch no importable; se usará CPU")
        return True


def check_checkpoint_dir(checkpoint_dir: str) -> bool:
    """Verifica directorio de checkpoints."""
    path = Path(checkpoint_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Checkpoint dir: %s", path.absolute())
        return True
    except (OSError, IOError, ValueError) as e:
        logger.error("❌ Error creando checkpoint dir: %s", e)
        return False


def main() -> bool:
    """Ejecuta todas las validaciones.

    Returns:
        bool: True si todas las validaciones pasaron
    """
    logger.info("")
    logger.info("="*70)
    logger.info("PRE-TRAINING VALIDATION")
    logger.info("="*70)

    checks = [
        ("Agents", check_agents),
        ("Rewards", check_rewards),
        ("GPU", check_gpu),
        ("Checkpoint Dir", lambda: check_checkpoint_dir("./checkpoints")),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
        except (OSError, IOError, ValueError, ImportError) as e:
            logger.error("❌ %s: %s", name, e)
            results.append(False)

    logger.info("")
    logger.info("="*70)
    passed = sum(results)
    total = len(results)
    logger.info("Results: %d/%d passed", passed, total)

    if all(results):
        logger.info("✓ All checks passed! Ready to train.")
        logger.info("="*70)
        return True
    else:
        logger.error("✗ Some checks failed. Fix issues before training.")
        logger.info("="*70)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
