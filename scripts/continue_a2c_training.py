#!/usr/bin/env python
"""Entrenar A2C continuando desde checkpoint existente."""
from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.a2c_sb3 import make_a2c, A2CConfig
from citylearn.citylearn import CityLearnEnv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def find_latest_checkpoint(checkpoint_dir: Path, prefix: str):
    """Encuentra el checkpoint más reciente por fecha."""
    if not checkpoint_dir.exists():
        return None
    
    candidates = list(checkpoint_dir.glob(f"{prefix}_step_*.zip"))
    final = checkpoint_dir / f"{prefix}_final.zip"
    if final.exists():
        candidates.append(final)
    
    if not candidates:
        return None
    
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    best = candidates[0]
    
    if "final" in best.name:
        logger.info(f"✓ Checkpoint final encontrado: {best.name}")
    else:
        m = re.search(r"step_(\d+)", best.stem)
        step = int(m.group(1)) if m else 0
        logger.info(f"✓ Checkpoint step {step} encontrado: {best.name}")
    
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--episodes", type=int, default=10)
    args = parser.parse_args()
    
    cfg, rp = load_all(args.config)
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "a2c"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Buscar checkpoint existente
    resume_checkpoint = find_latest_checkpoint(checkpoint_dir, "a2c")
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    a2c_cfg = cfg["oe3"]["evaluation"]["a2c"]
    total_timesteps = args.episodes * 8760
    
    config = A2CConfig(
        train_steps=total_timesteps,
        n_steps=a2c_cfg.get("n_steps", 2048),
        learning_rate=a2c_cfg.get("learning_rate", 7e-4),
        gamma=0.99,
        gae_lambda=1.0,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        device=a2c_cfg.get("device", "cuda"),
        seed=42,
        verbose=0,
        log_interval=a2c_cfg.get("log_interval", 200),
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_freq_steps=a2c_cfg.get("checkpoint_freq_steps", 1000),
        resume_path=str(resume_checkpoint) if resume_checkpoint else None,
    )
    
    logger.info(f"Configuración A2C:")
    logger.info(f"  device={config.device}, n_steps={config.n_steps}")
    logger.info(f"  total_timesteps={total_timesteps} ({args.episodes} episodios)")
    if resume_checkpoint:
        logger.info(f"  Continuando desde: {resume_checkpoint.name}")
    
    logger.info("Creando agente A2C...")
    agent = make_a2c(env, config=config)
    
    logger.info("=" * 60)
    logger.info("INICIANDO ENTRENAMIENTO A2C")
    logger.info("=" * 60)
    
    try:
        agent.learn(total_timesteps=total_timesteps)
        logger.info("✓ Entrenamiento A2C completado!")
    except KeyboardInterrupt:
        logger.info("Entrenamiento interrumpido")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
