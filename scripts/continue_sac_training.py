#!/usr/bin/env python
"""Continuar entrenamiento SAC desde el último checkpoint con métricas visibles."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.sac import make_sac, SACConfig
from citylearn.citylearn import CityLearnEnv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def find_latest_checkpoint(checkpoint_dir: Path, prefix: str) -> tuple[Path | None, int]:
    """Encuentra el checkpoint más reciente por fecha y retorna (path, step)."""
    if not checkpoint_dir.exists():
        return None, 0
    
    import re
    candidates = list(checkpoint_dir.glob(f"{prefix}_step_*.zip"))
    final = checkpoint_dir / f"{prefix}_final.zip"
    if final.exists():
        candidates.append(final)
    
    if not candidates:
        return None, 0
    
    # Ordenar por fecha de modificación
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    best = candidates[0]
    
    # Extraer step number
    if "final" in best.name:
        step = 999999
    else:
        m = re.search(r"step_(\d+)", best.stem)
        step = int(m.group(1)) if m else 0
    
    return best, step


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--episodes", type=int, default=10, help="Total episodes to train")
    args = parser.parse_args()
    
    cfg, rp = load_all(args.config)
    
    # Paths
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "sac"
    
    # Find checkpoint
    checkpoint_path, checkpoint_step = find_latest_checkpoint(checkpoint_dir, "sac")
    
    if checkpoint_path:
        episodes_done = checkpoint_step // 8760
        logger.info(f"✓ Checkpoint encontrado: {checkpoint_path.name}")
        logger.info(f"  → Step: {checkpoint_step} (~{episodes_done} episodios completados)")
        logger.info(f"  → Continuará hasta {args.episodes} episodios totales")
    else:
        logger.info("✗ No hay checkpoint, iniciando desde cero")
        checkpoint_step = 0
    
    # Create environment
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    # SAC Config from yaml
    sac_cfg = cfg["oe3"]["evaluation"]["sac"]
    
    config = SACConfig(
        episodes=args.episodes,
        device=sac_cfg.get("device", "cuda"),
        seed=42,
        batch_size=sac_cfg.get("batch_size", 4096),
        buffer_size=sac_cfg.get("buffer_size", 500000),
        gradient_steps=sac_cfg.get("gradient_steps", 4),
        learning_rate=3e-4,
        gamma=0.99,
        tau=0.005,
        hidden_sizes=(256, 256),
        log_interval=sac_cfg.get("log_interval", 200),
        use_amp=sac_cfg.get("use_amp", True),
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_freq_steps=sac_cfg.get("checkpoint_freq_steps", 1000),
        progress_path=None,
        prefer_citylearn=sac_cfg.get("prefer_citylearn", True),
        resume_path=str(checkpoint_path) if checkpoint_path else None,
    )
    
    logger.info(f"Configuración SAC:")
    logger.info(f"  device={config.device}, batch_size={config.batch_size}")
    logger.info(f"  buffer_size={config.buffer_size}, gradient_steps={config.gradient_steps}")
    logger.info(f"  log_interval={config.log_interval}, checkpoint_freq={config.checkpoint_freq_steps}")
    
    # Create agent
    logger.info("Creando agente SAC...")
    agent = make_sac(env, config=config)
    
    # Train
    logger.info("=" * 60)
    logger.info("INICIANDO ENTRENAMIENTO SAC")
    logger.info("=" * 60)
    
    try:
        agent.learn(episodes=args.episodes)
        logger.info("✓ Entrenamiento completado!")
    except KeyboardInterrupt:
        logger.info("Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"Error durante entrenamiento: {e}")
        raise


if __name__ == "__main__":
    main()
