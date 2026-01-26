#!/usr/bin/env python
"""Reentrenar SAC ahora con datos solares correctos en el dataset."""

from __future__ import annotations

import argparse
import sys

# Validar Python 3.11
if sys.version_info != (3, 11):
    raise RuntimeError(f"Python 3.11 is required, but {sys.version_info.major}.{sys.version_info.minor} found")

from src.iquitos_citylearn._common import load_all
from src.iquitos_citylearn.oe3.agents import make_sac
from citylearn.citylearn import CityLearnEnv
import logging

logger = logging.getLogger(__name__)

def main() -> None:
    ap = argparse.ArgumentParser(description="Reentrenar SAC con datos solares (OE2→OE3 pipeline fijo)")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--episodes", type=int, default=10, help="Episodios de entrenamiento")
    ap.add_argument("--resume", action="store_true", help="Reanudar desde último checkpoint")
    args = ap.parse_args()

    cfg, rp = load_all(args.config)

    logger.info("=" * 80)
    logger.info("REENTRENANDO SAC CON DATOS SOLARES CORREGIDOS")
    logger.info("=" * 80)
    logger.info(f"Dataset: {rp.citylearn_processed}")
    logger.info(f"Episodios: {args.episodes}")
    logger.info(f"Resume: {args.resume}")

    # Construir ambiente CityLearn con solar correctamente asignado
    schema_path = next(rp.outputs_dir.glob("schema_*.json"))
    env = CityLearnEnv(schema_path=str(schema_path))

    # Crear agente SAC
    agent = make_sac(env, cfg["oe3"]["evaluation"]["sac"])

    # Entrenar
    logger.info(f"Entrenando SAC...")
    agent.learn(episodes=args.episodes)

    logger.info("=" * 80)
    logger.info("ENTRENAMIENTO COMPLETADO")
    logger.info("=" * 80)
    logger.info("Próximo paso: Ejecutar run_oe3_simulate para evaluación completa")

if __name__ == "__main__":
    main()
