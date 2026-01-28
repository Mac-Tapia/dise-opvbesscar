#!/usr/bin/env python
"""
Script de entrenamiento SEGURO para RTX 4060 (8GB VRAM).

PROPÓSITO:
- Lanzar entrenamiento RL (SAC, PPO, A2C) SIN interrupciones OOM
- Auto-ajustar parámetros de memoria según GPU disponible
- Manejo robusto de errores y KeyboardInterrupt
- Checkpoints automáticos para reanudar si es necesario

LIMITACIONES RTX 4060:
- VRAM total: 8GB (6GB usable después de OS/CUDA overhead)
- Batch size máximo recomendado: 128
- Buffer size máximo: 250k para SAC
- Hidden layers: 512 máximo

CAMBIOS APLICADOS ANTES DE ESTE SCRIPT:
1. SAC: episodes 50→5, batch_size 256→128, buffer_size 500k→250k
2. PPO: batch_size 64, n_steps 1024 (ya optimizado)
3. A2C: n_steps 256 (ya optimizado)

USO:
    py -3.11 scripts/train_safe_rtx4060_gpu.py [--config CONFIG] [--skip-baseline]
"""

from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path
from typing import Any, Optional

# Validación de versión Python
if sys.version_info[:2] != (3, 11):
    print(f"ERROR: Python 3.11 requerido. Tienes {sys.version_info[0]}.{sys.version_info[1]}")
    sys.exit(1)

import torch
import psutil

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all


logger = logging.getLogger(__name__)


def check_gpu_memory() -> dict[str, Any]:
    """Verifica memoria GPU y CPU disponibles."""
    gpu_info = {"available": False, "device": "cpu", "total_gb": 0, "free_gb": 0}

    if torch.cuda.is_available():
        try:
            gpu_info["available"] = True
            gpu_info["device"] = "cuda:0"
            gpu_info["total_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
            gpu_info["free_gb"] = torch.cuda.mem_get_info(0)[0] / 1e9
            logger.info(f"✓ GPU DETECTADA: {torch.cuda.get_device_name(0)}")
            logger.info(f"  - Total VRAM: {gpu_info['total_gb']:.1f} GB")
            logger.info(f"  - VRAM libre: {gpu_info['free_gb']:.1f} GB")
        except Exception as e:
            logger.warning(f"Error al detectar GPU: {e}. Usando CPU.")
            gpu_info["available"] = False
            gpu_info["device"] = "cpu"
    else:
        logger.warning("⚠️  CUDA no disponible. Usando CPU (LENTO: ~1 hora/episodio)")

    cpu_info = psutil.virtual_memory()
    logger.info(f"✓ RAM CPU disponible: {cpu_info.available / 1e9:.1f} GB")

    return gpu_info


def adjust_memory_config(cfg: dict[str, Any], gpu_info: dict[str, Any]) -> None:
    """Ajusta parámetros de memoria según GPU disponible."""

    # RTX 4060 = 8GB VRAM
    if gpu_info["available"] and gpu_info["total_gb"] < 16:
        logger.info("🔧 Detectado GPU con <16GB. Aplicando ajustes memoria agresivos...")

        # SAC - Memory conservative
        if "sac" in cfg["oe3"]["agents"]:
            cfg["oe3"]["agents"]["sac"]["batch_size"] = 128  # Critical: was causing OOM at 1024
            cfg["oe3"]["agents"]["sac"]["buffer_size"] = 250000  # Reduced from 500k
            cfg["oe3"]["agents"]["sac"]["episodes"] = 5  # Quick test before full run
            cfg["oe3"]["agents"]["sac"]["train_steps"] = 500000  # Standard
            logger.info("  - SAC: batch_size=128, buffer=250k, episodes=5")

        # PPO - Already optimized
        if "ppo" in cfg["oe3"]["agents"]:
            cfg["oe3"]["agents"]["ppo"]["batch_size"] = 32  # Safety margin
            cfg["oe3"]["agents"]["ppo"]["n_steps"] = 1024  # Standard for PPO
            cfg["oe3"]["agents"]["ppo"]["train_steps"] = 500000
            logger.info("  - PPO: batch_size=32, n_steps=1024")

        # A2C - Lightweight
        if "a2c" in cfg["oe3"]["agents"]:
            cfg["oe3"]["agents"]["a2c"]["n_steps"] = 128  # Reduce from 256
            cfg["oe3"]["agents"]["a2c"]["batch_size"] = 64  # If applicable
            cfg["oe3"]["agents"]["a2c"]["train_steps"] = 500000
            logger.info("  - A2C: n_steps=128")

        # Disable AMP if OOM persists
        for agent in ["sac", "ppo", "a2c"]:
            if agent in cfg["oe3"]["agents"]:
                cfg["oe3"]["agents"][agent]["use_amp"] = False
                cfg["oe3"]["agents"][agent]["pin_memory"] = False
                logger.info(f"  - {agent.upper()}: AMP/pin_memory deshabilitados")
    else:
        logger.info("✓ GPU con >16GB detectada. Usando configuración estándar.")


def safe_train(cfg: dict[str, Any], rp: Any, skip_baseline: bool = False) -> None:
    """Ejecuta entrenamiento con manejo robusto de errores."""

    try:
        # ==== PASO 1: BUILD DATASET ====
        logger.info("\n" + "="*80)
        logger.info("PASO 1/3: Construyendo dataset CityLearn...")
        logger.info("="*80)

        dataset_name = cfg["oe3"]["dataset"]["name"]
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        dataset_dir = built.dataset_dir
        logger.info(f"✓ Dataset construido: {dataset_dir}")

        # ==== PASO 2: ENTRENAMIENTO ====
        logger.info("\n" + "="*80)
        logger.info("PASO 2/3: Iniciando entrenamiento (SAC, PPO, A2C)...")
        logger.info("="*80)

        # Simulate con manejo de KeyboardInterrupt
        simulate(
            cfg=cfg,
            rp=rp,
            schema_grid_path=dataset_dir / "schema_grid_only.json",
            schema_pv_path=dataset_dir / "schema_pv_bess.json",
            chargers_results_path=rp.interim_dir / "oe2" / "chargers" / "chargers_results.json",
            skip_baseline=skip_baseline,
        )

        logger.info("\n" + "="*80)
        logger.info("✓ ENTRENAMIENTO COMPLETADO SIN ERRORES")
        logger.info("="*80)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  KeyboardInterrupt recibido. Guardando checkpoints...")
        # Los checkpoints ya se guardan automáticamente en simulate()
        logger.info("Checkpoints guardados. Puedes reanudar ejecutando este script nuevamente.")
        sys.exit(130)  # Standard exit code for SIGINT

    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            logger.error("\n❌ ERROR: GPU OUT OF MEMORY (OOM)")
            logger.error(f"Detalles: {e}")
            logger.error("\nSOLUCIONES (en orden):")
            logger.error("1. Reducir batch_size aún más (ej: 64→32)")
            logger.error("2. Reducir n_steps o buffer_size")
            logger.error("3. Usar CPU (lento pero funciona): device: 'cpu'")
            logger.error("4. Reducir hidden_sizes de (512,512) a (256,256)")
            sys.exit(1)
        else:
            logger.error(f"ERROR de Runtime: {e}")
            raise

    except Exception as e:
        logger.error(f"ERROR inesperado: {e}")
        logger.error("Stack trace:", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Punto de entrada principal."""

    # Parser argumentos
    parser = argparse.ArgumentParser(
        description="Entrenamiento RL SEGURO para RTX 4060 (8GB VRAM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EJEMPLOS:
  py -3.11 scripts/train_safe_rtx4060_gpu.py
  py -3.11 scripts/train_safe_rtx4060_gpu.py --config configs/default.yaml
  py -3.11 scripts/train_safe_rtx4060_gpu.py --skip-baseline
        """,
    )
    parser.add_argument("--config", default="configs/default.yaml", help="Config YAML")
    parser.add_argument("--skip-baseline", action="store_true", help="Reutilizar baseline Uncontrolled")
    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger.info("="*80)
    logger.info("SCRIPT DE ENTRENAMIENTO SEGURO PARA RTX 4060")
    logger.info("="*80)

    # Chequeos previos
    logger.info(f"\n📋 Información del sistema:")
    logger.info(f"  - Python: {sys.version.split()[0]}")
    gpu_info = check_gpu_memory()

    # Cargar config
    logger.info(f"\n📂 Cargando configuración desde: {args.config}")
    cfg, rp = load_all(args.config)

    # Ajustar parámetros de memoria
    logger.info("\n🔧 Ajustando parámetros de memoria...")
    adjust_memory_config(cfg, gpu_info)

    # Entrenar
    logger.info("\n🚀 Iniciando entrenamiento seguro...")
    safe_train(cfg, rp, skip_baseline=args.skip_baseline)


if __name__ == "__main__":
    main()
