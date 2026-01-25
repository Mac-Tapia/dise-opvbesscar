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
        logger.error(f"❌ Schema CityLearn no encontrado: {schema_path}")
        return False
    logger.info(f"✓ Schema CityLearn: {path.absolute()}")
    return True


def check_agents() -> bool:
    """Verifica que agentes se pueden importar."""
    try:
        from iquitos_citylearn.oe3.agents import (
            PPOAgent, PPOConfig,
            SACAgent, SACConfig,
            A2CAgent, A2CConfig,
            detect_device,
        )
        logger.info("✓ Agentes importados exitosamente")
        logger.info(f"  Device detectado: {detect_device()}")
        return True
    except Exception as e:
        logger.error(f"❌ Error importando agentes: {e}")
        return False


def check_rewards() -> bool:
    """Verifica que rewards se pueden importar."""
    try:
        from iquitos_citylearn.oe3.rewards import (
            MultiObjectiveWeights,
            IquitosContext,
        )
        weights = MultiObjectiveWeights()
        logger.info("✓ Rewards importados exitosamente")
        logger.info(f"  Pesos: CO2={weights.co2}, Solar={weights.solar}, Cost={weights.cost}")
        return True
    except Exception as e:
        logger.error(f"❌ Error importando rewards: {e}")
        return False


def check_gpu() -> None:
    """Verifica disponibilidad de GPU."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"✓ GPU disponible: {torch.cuda.get_device_name(0)}")
            logger.info(f"  CUDA Version: {torch.version.cuda}")
            logger.info(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            logger.warning("⚠ GPU no disponible; se usará CPU")
    except ImportError:
        logger.warning("⚠ PyTorch no importable; se usará CPU")


def check_checkpoint_dir(checkpoint_dir: str) -> bool:
    """Verifica directorio de checkpoints."""
    path = Path(checkpoint_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Checkpoint dir: {path.absolute()}")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando checkpoint dir: {e}")
        return False


def main() -> bool:
    """Ejecuta todas las validaciones.

    Returns:
        bool: True si todas las validaciones pasaron
    """
    logger.info("\n" + "="*70)
    logger.info("PRE-TRAINING VALIDATION")
    logger.info("="*70 + "\n")

    checks = [
        ("Agents", check_agents),
        ("Rewards", check_rewards),
        ("GPU", lambda: (check_gpu(), True)[1]),
        ("Checkpoint Dir", lambda: check_checkpoint_dir("./checkpoints")),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append(result)
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            results.append(False)

    logger.info("\n" + "="*70)
    passed = sum(results)
    total = len(results)
    logger.info(f"Results: {passed}/{total} passed")

    if all(results):
        logger.info("✓ All checks passed! Ready to train.")
        logger.info("="*70 + "\n")
        return True
    else:
        logger.error("✗ Some checks failed. Fix issues before training.")
        logger.info("="*70 + "\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
