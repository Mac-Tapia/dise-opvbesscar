#!/usr/bin/env python3
"""
================================================================================
PIPELINE COMPLETO: Ejecuta todos los baselines y agentes
================================================================================
Ejecuta en secuencia:
    1. Baseline 1 (Con Solar)
    2. Baseline 2 (Sin Solar)
    3. Agente SAC (evaluación)
    4. Agente PPO (evaluación)
    5. Agente A2C (evaluación)
    6. Tabla Comparativa

Uso:
    python -m scripts.run_all_pipelines
    python -m scripts.run_all_pipelines --skip-baselines   # Solo agentes
    python -m scripts.run_all_pipelines --skip-agents      # Solo baselines
================================================================================
"""
from __future__ import annotations

import argparse
import logging
import sys
import subprocess
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_script(name: str, module: str) -> bool:
    """Ejecuta un script y retorna True si fue exitoso."""
    logger.info("")
    logger.info("─" * 60)
    logger.info(f"  ▶ Ejecutando: {name}")
    logger.info("─" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            check=True,
            cwd=Path(__file__).parent.parent,
        )
        logger.info(f"  ✓ {name} completado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"  ✗ {name} falló con código {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"  ✗ {name} falló: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pipeline Completo - Baselines y Agentes")
    parser.add_argument(
        "--skip-baselines",
        action="store_true",
        help="Omitir ejecución de baselines",
    )
    parser.add_argument(
        "--skip-agents",
        action="store_true",
        help="Omitir ejecución de agentes",
    )
    parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="Omitir tabla comparativa final",
    )
    args = parser.parse_args()

    logger.info("")
    logger.info("=" * 80)
    logger.info("  🚀 PIPELINE COMPLETO: Baselines + Agentes RL")
    logger.info("=" * 80)
    logger.info("")

    results = {}

    # 1. Baselines
    if not args.skip_baselines:
        logger.info("  📊 FASE 1: BASELINES")
        results["baseline1"] = run_script("Baseline 1 (Con Solar)", "scripts.run_baseline1_solar")
        results["baseline2"] = run_script("Baseline 2 (Sin Solar)", "scripts.run_baseline2_nosolar")
    else:
        logger.info("  ⏭️  Baselines omitidos (--skip-baselines)")

    # 2. Agentes RL
    if not args.skip_agents:
        logger.info("")
        logger.info("  🤖 FASE 2: AGENTES RL (Evaluación)")
        results["sac"] = run_script("Agente SAC", "scripts.run_agent_sac")
        results["ppo"] = run_script("Agente PPO", "scripts.run_agent_ppo")
        results["a2c"] = run_script("Agente A2C", "scripts.run_agent_a2c")
    else:
        logger.info("  ⏭️  Agentes omitidos (--skip-agents)")

    # 3. Tabla comparativa
    if not args.skip_comparison:
        logger.info("")
        logger.info("  📋 FASE 3: TABLA COMPARATIVA")
        results["comparison"] = run_script("Tabla Comparativa", "scripts.compare_all_results")
    else:
        logger.info("  ⏭️  Comparación omitida (--skip-comparison)")

    # Resumen final
    logger.info("")
    logger.info("=" * 80)
    logger.info("  📊 RESUMEN DE EJECUCIÓN")
    logger.info("=" * 80)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for name, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"  {status} {name}")

    logger.info("")
    logger.info(f"  Total: {success_count}/{total_count} exitosos")
    logger.info("=" * 80)

    # Exit code basado en resultados
    if success_count == total_count:
        logger.info("  ✅ PIPELINE COMPLETO EXITOSO")
        sys.exit(0)
    else:
        logger.warning("  ⚠️  Algunos pasos fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main()
