#!/usr/bin/env python
"""Entrenar PPO con 10 episodios."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.ppo_sb3 import make_ppo, PPOConfig
from citylearn.citylearn import CityLearnEnv
import logging
import re

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
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    total_timesteps = args.episodes * 8760
    
    config = PPOConfig(
        train_steps=total_timesteps,
        n_steps=ppo_cfg.get("n_steps", 4096),
        batch_size=ppo_cfg.get("batch_size", 512),
        n_epochs=ppo_cfg.get("n_epochs", 10),
        learning_rate=ppo_cfg.get("learning_rate", 3e-4),
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        device=ppo_cfg.get("device", "cuda"),
        seed=42,
        verbose=0,
        log_interval=ppo_cfg.get("log_interval", 200),
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_freq_steps=ppo_cfg.get("checkpoint_freq_steps", 1000),
        resume_path=str(find_latest_checkpoint(checkpoint_dir, "ppo")) if find_latest_checkpoint(checkpoint_dir, "ppo") else None,
    )
    
    logger.info(f"Configuración PPO:")
    logger.info(f"  device={config.device}, n_steps={config.n_steps}, batch_size={config.batch_size}")
    logger.info(f"  total_timesteps={total_timesteps} ({args.episodes} episodios)")
    
    logger.info("Creando agente PPO...")
    agent = make_ppo(env, config=config)
    
    logger.info("=" * 60)
    logger.info("INICIANDO ENTRENAMIENTO PPO")
    logger.info("=" * 60)
    
    try:
        agent.learn(total_timesteps=total_timesteps)
        logger.info("✓ Entrenamiento PPO completado!")
    except KeyboardInterrupt:
        logger.info("Entrenamiento interrumpido")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
