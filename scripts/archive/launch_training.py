#!/usr/bin/env python
"""
LAUNCH TRAINING - Integrated pre-flight checks + training launch

Single command to validate everything and start training safely.
"""
from __future__ import annotations

import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(text: str) -> None:
    """Print formatted header"""
    width = 80
    logger.info("=" * width)
    logger.info(f"  {text:^{width-4}}")
    logger.info("=" * width)


def run_validation_script(script_name: str) -> bool:
    """Run a validation script and return success status"""
    script_path = Path(f'scripts/{script_name}')

    logger.info(f"\n▶️  Ejecutando: {script_name}")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"✅ {script_name} PASSED")
            return True
        else:
            logger.error(f"❌ {script_name} FAILED")
            if result.stdout:
                logger.error(f"Output: {result.stdout[-500:]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {script_name} timeout exceeded")
        return False
    except Exception as e:
        logger.error(f"❌ Error running {script_name}: {e}")
        return False


def launch_training() -> int:
    """Launch the training pipeline"""
    print_header("🚀 LANZADOR DE ENTRENAMIENTO OE3")

    logger.info(f"\nFecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Directorio: {Path.cwd()}")

    # Phase 1: Pre-flight checks
    print_header("FASE 1: VALIDACIONES PRE-VUELO")

    validations = [
        'audit_training_pipeline.py',
        'validate_training_readiness.py',
    ]

    all_passed = True
    for validation_script in validations:
        if not run_validation_script(validation_script):
            all_passed = False
            logger.error(f"❌ Validation failed: {validation_script}")
            logger.error("\n🛑 ENTRENAMIENTO CANCELADO - Corrija los errores arriba antes de continuar")
            return 1

    if all_passed:
        logger.info("\n✅ TODAS LAS VALIDACIONES PASADAS - Sistema listo para entrenamiento")

    # Phase 2: Final confirmation
    print_header("FASE 2: CONFIRMACIÓN FINAL")

    logger.info("\nSiguiente paso: Iniciar entrenamiento OE3")
    logger.info("  - SAC: Off-policy agent")
    logger.info("  - PPO: On-policy stable agent")
    logger.info("  - A2C: On-policy baseline agent")
    logger.info("\nEstimado de tiempo: 30-60 minutos (GPU RTX 4060)")

    response = input("\n¿Continuar con el entrenamiento? (s/n): ").strip().lower()

    if response not in ['s', 'si', 'yes', 'y']:
        logger.info("Entrenamiento cancelado por usuario")
        return 0

    # Phase 3: Launch training
    print_header("FASE 3: LANZANDO ENTRENAMIENTO")

    logger.info("\n▶️  Ejecutando: python -m scripts.run_oe3_simulate")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'scripts.run_oe3_simulate', '--config', 'configs/default.yaml'],
            timeout=None  # No timeout for training
        )

        if result.returncode == 0:
            print_header("✅ ENTRENAMIENTO COMPLETADO")
            logger.info("\nResultados guardados en:")
            logger.info("  - checkpoints/SAC/")
            logger.info("  - checkpoints/PPO/")
            logger.info("  - checkpoints/A2C/")
            logger.info("  - outputs/oe3_simulations/")
            return 0
        else:
            logger.error("❌ Entrenamiento falló")
            return result.returncode
    except KeyboardInterrupt:
        logger.info("\n⚠️  Entrenamiento interrumpido por usuario")
        return 0
    except Exception as e:
        logger.error(f"❌ Error durante entrenamiento: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(launch_training())
