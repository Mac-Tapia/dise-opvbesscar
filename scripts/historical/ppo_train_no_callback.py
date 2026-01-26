#!/usr/bin/env python
"""Entrenar PPO SIN callbacks que causen deadlock."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig
from stable_baselines3 import PPO
from citylearn.citylearn import CityLearnEnv
from stable_baselines3.common.vec_env import DummyVecEnv
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
    parser.add_argument("--episodes", type=int, default=5)
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
    
    logger.info(f"Configuración PPO:")
    logger.info(f"  device={ppo_cfg.get('device', 'cuda')}, n_steps={ppo_cfg.get('n_steps', 8192)}, batch_size={ppo_cfg.get('batch_size', 4096)}")
    logger.info(f"  total_timesteps={total_timesteps} ({args.episodes} episodios)")
    
    logger.info("Creando agente PPO...")
    
    # Intentar cargar desde checkpoint
    checkpoint = find_latest_checkpoint(checkpoint_dir, "ppo")
    
    if checkpoint:
        logger.info(f"Cargando modelo desde {checkpoint.name}")
        model = PPO.load(str(checkpoint), env=env, device=ppo_cfg.get("device", "cuda"))
        logger.info(f"✓ Modelo cargado exitosamente")
    else:
        logger.info("Creando modelo PPO nuevo")
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=ppo_cfg.get("learning_rate", 3e-4),
            n_steps=ppo_cfg.get("n_steps", 8192),
            batch_size=ppo_cfg.get("batch_size", 4096),
            n_epochs=ppo_cfg.get("n_epochs", 10),
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            device=ppo_cfg.get("device", "cuda"),
            verbose=1,
        )
    
    logger.info("=" * 60)
    logger.info("INICIANDO ENTRENAMIENTO PPO (SIN CALLBACKS)")
    logger.info("=" * 60)
    
    try:
        # Entrenar SIN callbacks (solo model.learn())
        logger.info(f"Ejecutando model.learn({total_timesteps} timesteps)...")
        model.learn(total_timesteps=total_timesteps, log_interval=1)
        
        # Guardar checkpoint final manualmente
        final_path = checkpoint_dir / "ppo_final.zip"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path.name}")
        
    except KeyboardInterrupt:
        logger.info("Entrenamiento interrumpido por usuario")
        # Guardar checkpoint actual
        current_step = model.num_timesteps
        checkpoint_path = checkpoint_dir / f"ppo_step_{current_step}.zip"
        model.save(str(checkpoint_path))
        logger.info(f"✓ Checkpoint de emergencia guardado en step {current_step}")
    except Exception as e:
        logger.error(f"Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        current_step = getattr(model, 'num_timesteps', 0)
        if current_step > 0:
            checkpoint_path = checkpoint_dir / f"ppo_step_{current_step}.zip"
            model.save(str(checkpoint_path))
            logger.info(f"✓ Checkpoint de error guardado en step {current_step}")
        raise


if __name__ == "__main__":
    main()
