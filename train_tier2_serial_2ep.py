#!/usr/bin/env python3
"""
TIER 2 Training - 2 Episodes Each Agent (Serial)
A2C → PPO → SAC

Updated configs:
- A2C: LR 2.5e-4, n_steps 1024, ent 0.02, hidden (512,512)
- PPO: LR 2.5e-4, batch 256, epochs 15, ent 0.02, hidden (512,512), SDE
- SAC: LR 2.5e-4, batch 256, ent 0.02, hidden (512,512), adaptive norm
"""

import os
import sys
import torch
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_gpu():
    """Verify GPU availability."""
    logger.info("=" * 70)
    logger.info("GPU VERIFICATION")
    logger.info("=" * 70)
    
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"✅ GPU Available: {device_name} ({memory:.1f} GB)")
        return True
    else:
        logger.warning("⚠️  GPU NOT available - using CPU (slow)")
        return False

def train_a2c_tier2(episodes=2):
    """Train A2C with TIER 2 config - 2 episodes."""
    logger.info("\n" + "=" * 70)
    logger.info("A2C TIER 2 TRAINING - 2 EPISODES")
    logger.info("=" * 70)
    
    try:
        from src.iquitos_citylearn.oe3.agents.a2c_sb3 import A2CAgent, A2CConfig
        from src.iquitos_citylearn.agents import make_env
        
        logger.info("Creating environment...")
        env = make_env()
        
        # TIER 2 Config
        config = A2CConfig(
            train_steps=500000,
            n_steps=1024,           # TIER 2: ↑ de 512
            learning_rate=2.5e-4,   # TIER 2: ↓ de 3e-4
            lr_schedule="linear",   # TIER 2: de constant
            ent_coef=0.02,          # TIER 2: ↑ de 0.01
            hidden_sizes=(512, 512),  # TIER 2: ↑ de (256,256)
            activation="relu",      # TIER 2: de tanh
            verbose=1,
        )
        
        logger.info(f"A2C Config: LR={config.learning_rate}, ent={config.ent_coef}, hidden={config.hidden_sizes}")
        
        agent = A2CAgent(env, config)
        
        logger.info(f"Starting training: {episodes} episodes...")
        agent.learn(episodes=episodes)
        
        logger.info(f"✅ A2C Training Complete ({episodes} episodes)")
        return True
        
    except Exception as e:
        logger.error(f"❌ A2C Training Error: {e}", exc_info=True)
        return False

def train_ppo_tier2(episodes=2):
    """Train PPO with TIER 2 config - 2 episodes."""
    logger.info("\n" + "=" * 70)
    logger.info("PPO TIER 2 TRAINING - 2 EPISODES")
    logger.info("=" * 70)
    
    try:
        from src.iquitos_citylearn.oe3.agents.ppo_sb3 import PPOAgent, PPOConfig
        from src.iquitos_citylearn.agents import make_env
        
        logger.info("Creating environment...")
        env = make_env()
        
        # TIER 2 Config
        config = PPOConfig(
            train_steps=500000,
            n_steps=1024,
            batch_size=256,         # TIER 2: ↑ de 128
            n_epochs=15,            # TIER 2: ↑ de 10
            learning_rate=2.5e-4,   # TIER 2: ↓ de 3e-4
            lr_schedule="linear",   # TIER 2: de constant
            ent_coef=0.02,          # TIER 2: ↑ de 0.01
            hidden_sizes=(512, 512),  # TIER 2: ↑ de (256,256)
            activation="relu",      # TIER 2: de tanh
            use_sde=True,           # NEW TIER 2
            verbose=1,
        )
        
        logger.info(f"PPO Config: LR={config.learning_rate}, batch={config.batch_size}, epochs={config.n_epochs}, ent={config.ent_coef}")
        
        agent = PPOAgent(env, config)
        
        logger.info(f"Starting training: {episodes} episodes...")
        agent.learn(episodes=episodes)
        
        logger.info(f"✅ PPO Training Complete ({episodes} episodes)")
        return True
        
    except Exception as e:
        logger.error(f"❌ PPO Training Error: {e}", exc_info=True)
        return False

def train_sac_tier2(episodes=2):
    """Train SAC with TIER 2 config - 2 episodes."""
    logger.info("\n" + "=" * 70)
    logger.info("SAC TIER 2 TRAINING - 2 EPISODES")
    logger.info("=" * 70)
    
    try:
        from src.iquitos_citylearn.oe3.agents.sac import SACAgent, SACConfig
        from src.iquitos_citylearn.agents import make_env
        
        logger.info("Creating environment...")
        env = make_env()
        
        # TIER 2 Config
        config = SACConfig(
            episodes=episodes,
            batch_size=256,         # TIER 2: ↓ de 512
            buffer_size=150000,     # TIER 2: ↑ de 100k
            learning_rate=2.5e-4,   # TIER 2: ↓ de 3e-4
            ent_coef=0.02,          # TIER 2: ↑ de 0.01
            target_entropy=-40,     # TIER 2: ↓ de -50
            hidden_sizes=(512, 512),  # TIER 2: ↑ de (256,256)
            update_per_timestep=2,  # NEW TIER 2
            use_dropout=True,       # NEW TIER 2
            dropout_rate=0.1,       # NEW TIER 2
            verbose=1,
        )
        
        logger.info(f"SAC Config: LR={config.learning_rate}, batch={config.batch_size}, ent={config.ent_coef}")
        
        agent = SACAgent(env, config)
        
        logger.info(f"Starting training: {episodes} episodes...")
        agent.learn(episodes=episodes)
        
        logger.info(f"✅ SAC Training Complete ({episodes} episodes)")
        return True
        
    except Exception as e:
        logger.error(f"❌ SAC Training Error: {e}", exc_info=True)
        return False

def main():
    """Main entry point - serial training."""
    logger.info("\n" + "=" * 70)
    logger.info("TIER 2 SERIAL TRAINING - 2 EPISODES EACH AGENT")
    logger.info("=" * 70)
    logger.info(f"Start time: {datetime.now().isoformat()}")
    
    # Check GPU
    check_gpu()
    
    # Training sequence
    episodes = 2
    results = {}
    
    logger.info(f"\nTraining sequence (2 episodes each):")
    logger.info(f"  1. A2C TIER 2")
    logger.info(f"  2. PPO TIER 2")
    logger.info(f"  3. SAC TIER 2")
    
    # A2C
    results['a2c'] = train_a2c_tier2(episodes=episodes)
    if not results['a2c']:
        logger.warning("⚠️  A2C failed, continuing...")
    
    # PPO
    results['ppo'] = train_ppo_tier2(episodes=episodes)
    if not results['ppo']:
        logger.warning("⚠️  PPO failed, continuing...")
    
    # SAC
    results['sac'] = train_sac_tier2(episodes=episodes)
    if not results['sac']:
        logger.warning("⚠️  SAC failed")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 70)
    for agent, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{agent.upper()}: {status}")
    
    logger.info(f"End time: {datetime.now().isoformat()}")
    logger.info("=" * 70)
    
    # Return success if all trained
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
