#!/usr/bin/env python3
"""
Test SAC en UN SOLO EPISODIO para debug rápido sin waiting 26k steps
"""
import logging
import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.agents.sac import SACAgent, SACConfig

def main():
    """Test 1 episode SAC training"""
    logger.info("=" * 80)
    logger.info("[TEST] Iniciando SAC 1-episode debug")
    logger.info("=" * 80)

    # Load config
    cfg = load_config("configs/default.yaml")
    paths = load_paths(cfg)

    # Build dataset (fast)
    logger.info("[TEST] Construyendo dataset...")
    built = build_citylearn_dataset(
        config=cfg,
        interim_dir=paths.interim,
    )
    env, schema, metrics_baseline = built

    logger.info(f"[TEST] Environment creado: {env}")
    logger.info(f"[TEST] Obs shape en reset: {env.reset()[0].shape if hasattr(env.reset()[0], 'shape') else type(env.reset()[0])}")

    # Create SAC with 1 episode only
    logger.info("[TEST] Creando SAC agent...")
    sac_config = SACConfig(
        episodes=1,  # 1 episodio solo
        batch_size=64,
        device='cuda' if True else 'cpu',
        checkpoint_freq_steps=999999,  # No checkpoint
        verbose=1,
    )

    agent = SACAgent(env=env, config=sac_config)

    logger.info("[TEST] Iniciando entrenamiento (1 episodio = 8760 steps)...")
    try:
        agent.learn(
            total_timesteps=8760,
            progress_bar=False,
            log_interval=100,
        )
        logger.info("[TEST] ✅ ENTRENAMIENTO COMPLETADO")
    except Exception as e:
        logger.error(f"[TEST] ❌ ERROR DURANTE ENTRENAMIENTO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
