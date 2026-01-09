#!/usr/bin/env python
"""Entrenar PPO y A2C en serie (uno después del otro)."""
from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.ppo_sb3 import make_ppo, PPOConfig
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


def train_ppo(cfg, rp, episodes: int):
    """Entrenar PPO."""
    logger.info("=" * 60)
    logger.info("ENTRENAMIENTO PPO")
    logger.info("=" * 60)
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    resume_checkpoint = find_latest_checkpoint(checkpoint_dir, "ppo")
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    total_timesteps = episodes * 8760
    
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
        resume_path=str(resume_checkpoint) if resume_checkpoint else None,
    )
    
    logger.info(f"  device={config.device}, total_timesteps={total_timesteps}")
    if resume_checkpoint:
        logger.info(f"  Continuando desde: {resume_checkpoint.name}")
    
    agent = make_ppo(env, config=config)
    agent.learn(total_timesteps=total_timesteps)
    logger.info("✓ PPO completado!")


def train_a2c(cfg, rp, episodes: int):
    """Entrenar A2C."""
    logger.info("=" * 60)
    logger.info("ENTRENAMIENTO A2C")
    logger.info("=" * 60)
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "a2c"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    resume_checkpoint = find_latest_checkpoint(checkpoint_dir, "a2c")
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    a2c_cfg = cfg["oe3"]["evaluation"]["a2c"]
    total_timesteps = episodes * 8760
    
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
    
    logger.info(f"  device={config.device}, total_timesteps={total_timesteps}")
    if resume_checkpoint:
        logger.info(f"  Continuando desde: {resume_checkpoint.name}")
    
    agent = make_a2c(env, config=config)
    agent.learn(total_timesteps=total_timesteps)
    logger.info("✓ A2C completado!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--episodes", type=int, default=10)
    args = parser.parse_args()
    
    cfg, rp = load_all(args.config)
    
    logger.info("=" * 60)
    logger.info("ENTRENAMIENTO EN SERIE: PPO → A2C")
    logger.info(f"Episodios por agente: {args.episodes}")
    logger.info("=" * 60)
    
    # 1. PPO primero
    train_ppo(cfg, rp, args.episodes)
    
    # 2. A2C después
    train_a2c(cfg, rp, args.episodes)
    
    logger.info("=" * 60)
    logger.info("✓ TODOS LOS ENTRENAMIENTOS COMPLETADOS")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
