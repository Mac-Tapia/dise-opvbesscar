#!/usr/bin/env python
"""Relanzar PPO sin callbacks complejos para evitar bloqueos."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig
from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def find_latest_checkpoint(checkpoint_dir: Path, prefix: str):
    """Encuentra el checkpoint más reciente."""
    if not checkpoint_dir.exists():
        return None
    
    candidates = list(checkpoint_dir.glob(f"{prefix}_step_*.zip"))
    if not candidates:
        return None
    
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    best = candidates[0]
    
    m = re.search(r"step_(\d+)", best.stem)
    step = int(m.group(1)) if m else 0
    logger.info(f"✓ Checkpoint step {step} encontrado: {best.name}")
    
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    
    cfg, rp = load_all(args.config)
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    total_timesteps = ppo_cfg.get("timesteps", 87600)
    
    logger.info(f"Configuración PPO:")
    logger.info(f"  device={ppo_cfg.get('device', 'cuda')}, n_steps={ppo_cfg.get('n_steps', 8192)}")
    logger.info(f"  total_timesteps={total_timesteps}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("INICIALIZANDO ENTRENAMIENTO PPO SIN CALLBACKS")
    logger.info("=" * 60)
    
    # Encontrar checkpoint anterior
    latest_ckpt = find_latest_checkpoint(checkpoint_dir, "ppo")
    
    if latest_ckpt:
        logger.info(f"\n✓ Cargando modelo desde checkpoint: {latest_ckpt}")
        model = PPO.load(str(latest_ckpt), env=env, device=ppo_cfg.get("device", "cuda"))
        logger.info(f"✓ Modelo cargado exitosamente")
        logger.info(f"  Device: {ppo_cfg.get('device', 'cuda')}")
        logger.info(f"  Continuando entrenamiento sin callbacks...")
    else:
        logger.error("❌ No se encontró checkpoint anterior")
        sys.exit(1)
    
    try:
        logger.info(f"\n▶ Iniciando learn() con {total_timesteps} timesteps...\n")
        
        # Entrenar DIRECTAMENTE sin callbacks complejos
        model.learn(
            total_timesteps=total_timesteps,
            reset_num_timesteps=False,  # Continuar desde donde paró
            log_interval=100,
            progress_bar=True
        )
        
        logger.info("\n✅ ENTRENAMIENTO COMPLETADO")
        
        # Guardar modelo final
        final_path = checkpoint_dir / "ppo_final"
        model.save(final_path)
        logger.info(f"✓ Modelo final guardado en: {final_path}.zip")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido por usuario")
        # Guardar checkpoint de parada
        paused_path = checkpoint_dir / "ppo_paused"
        model.save(paused_path)
        logger.info(f"✓ Modelo pausado guardado en: {paused_path}.zip")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
