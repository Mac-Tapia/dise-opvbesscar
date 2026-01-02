#!/usr/bin/env python3
"""Diagnose why checkpoints aren't being saved."""
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scripts._common import load_all

def main():
    cfg, rp = load_all(Path("configs/default.yaml"))
    
    logger.info("=" * 80)
    logger.info("CHECKPOINT CONFIGURATION ANALYSIS")
    logger.info("=" * 80)
    
    # Check OE3 config
    oe3_cfg = cfg.get("oe3", {})
    logger.info(f"\nOE3 evaluation config: {oe3_cfg.get('evaluation', {})}")
    
    eval_cfg = oe3_cfg.get('evaluation', {})
    agents = eval_cfg.get('agents', [])
    
    logger.info(f"\nAgents configured: {agents}")
    
    for agent_name in agents:
        logger.info(f"\n{'─' * 60}")
        logger.info(f"Agent: {agent_name}")
        logger.info(f"{'─' * 60}")
        
        # Convert agent name to lowercase for config lookup
        agent_key = agent_name.lower()
        agent_cfg = eval_cfg.get(agent_key, {})
        logger.info(f"Config: {agent_cfg}")
        
        checkpoint_freq = agent_cfg.get('checkpoint_freq_steps', 0)
        save_final = agent_cfg.get('save_final', False)
        episodes = agent_cfg.get('episodes', 1)
        
        logger.info(f"  checkpoint_freq_steps: {checkpoint_freq}")
        logger.info(f"  save_final: {save_final}")
        logger.info(f"  episodes: {episodes}")
        
        # Calculate expected checkpoints
        steps_per_episode = 8760  # Iquitos year
        total_steps = steps_per_episode * episodes
        expected_checkpoints = total_steps // checkpoint_freq if checkpoint_freq > 0 else 0
        
        logger.info(f"\n  Expected checkpoints:")
        logger.info(f"    Steps per episode: {steps_per_episode}")
        logger.info(f"    Total episodes: {episodes}")
        logger.info(f"    Total steps: {total_steps}")
        logger.info(f"    Checkpoint frequency: {checkpoint_freq}")
        logger.info(f"    Expected checkpoint count: {expected_checkpoints}")
        if save_final:
            logger.info(f"    Plus 1 final checkpoint")
    
    # Check checkpoint directories
    logger.info(f"\n{'=' * 80}")
    logger.info("CHECKPOINT DIRECTORY STATUS")
    logger.info(f"{'=' * 80}")
    
    checkpoint_base = Path("analyses/oe3/training/checkpoints")
    if checkpoint_base.exists():
        logger.info(f"✓ Checkpoint base directory exists: {checkpoint_base}")
        
        for agent_dir in checkpoint_base.iterdir():
            if agent_dir.is_dir():
                zips = list(agent_dir.glob("*.zip"))
                logger.info(f"  {agent_dir.name}: {len(zips)} checkpoint files")
    else:
        logger.warning(f"✗ Checkpoint base directory NOT found: {checkpoint_base}")
    
    logger.info("\n" + "=" * 80)
    logger.info("STABLE-BASELINES3 CHECKPOINT CALLBACK INFO")
    logger.info("=" * 80)
    
    # Check if CheckpointCallback is being used correctly
    logger.info("\nCheckpointCallback requirements:")
    logger.info("  1. Must be passed to agent.learn() via 'callbacks' parameter")
    logger.info("  2. Must have freq > 0 to save periodically")
    logger.info("  3. Must have save_dir set to a valid directory")
    logger.info("  4. _on_step() is called after each environment.step()")
    logger.info("  5. Save condition: n_calls % freq == 0")
    
    logger.info("\nChecking if CheckpointCallback is correctly instantiated...")
    logger.info("  Look for log messages like:")
    logger.info("    '[CheckpointCallback] Inicializado: save_dir=..., freq=...'")
    logger.info("    '✓ Checkpoint [AGENT] guardado: ...'")

if __name__ == "__main__":
    main()
