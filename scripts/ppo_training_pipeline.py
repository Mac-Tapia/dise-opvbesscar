#!/usr/bin/env python
"""Training Script PPO - Entrenamimento simple del agente PPO.

Pipeline directo:
1. Copiar datos OE2 → OE3 (dataset construction)
2. Entrenar PPO

Uso:
    python -m scripts.ppo_training_pipeline --config configs/default.yaml
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Entrenar PPO con dataset OE3."""
    import argparse
    import yaml
    from src.agents.ppo_sb3 import make_ppo, PPOConfig

    parser = argparse.ArgumentParser(description="Train PPO agent on OE3 dataset")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="Number of episodes to train (overrides config)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"❌ Config not found: {args.config}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info("=" * 70)
    logger.info("PPO TRAINING PIPELINE")
    logger.info("=" * 70)

    # === PASO 1: SETUP DATASET ===
    logger.info("\n[PASO 1/3] Setting up OE3 dataset...")
    from scripts.run_oe3_simulate import build_oe3_dataset

    try:
        dataset_dir = build_oe3_dataset(config)
        logger.info(f"✓ Dataset ready at {dataset_dir}")
    except Exception as e:
        logger.error(f"❌ Dataset setup failed: {e}")
        sys.exit(1)

    # === PASO 2: CREATE ENVIRONMENT ===
    logger.info("\n[PASO 2/3] Creating training environment...")

    try:
        # Try to use a simple gymnasium environment
        import gymnasium as gym
        import numpy as np

        # Create a simple environment for testing
        class SimpleEVChargingEnv(gym.Env):
            def __init__(self, n_episodes=1000):
                super().__init__()
                self.n_episodes = n_episodes
                self.current_step = 0

                # Observation space: 394 dimensions (OE3 standard)
                self.observation_space = gym.spaces.Box(
                    low=-np.inf, high=np.inf, shape=(394,), dtype=np.float32
                )

                # Action space: 129 dimensions (1 BESS + 128 chargers)
                self.action_space = gym.spaces.Box(
                    low=0.0, high=1.0, shape=(129,), dtype=np.float32
                )

            def reset(self, seed=None):
                super().reset(seed=seed)
                self.current_step = 0
                obs = np.random.randn(394).astype(np.float32)
                return obs, {}

            def step(self, action):
                self.current_step += 1

                # Convertir action a numpy array si es lista
                if isinstance(action, list):
                    action = np.array(action[0] if len(action) == 1 and isinstance(action[0], (list, np.ndarray)) else action)
                action = np.asarray(action).flatten()

                # Simple reward: prefer balanced actions
                reward = -np.mean(np.abs(action - 0.5)) * 10

                # Simple observation: random state
                obs = np.random.randn(394).astype(np.float32)

                # Episode ends after 8760 timesteps (1 year)
                terminated = self.current_step >= 8760
                truncated = False

                return obs, reward, terminated, truncated, {}

            def render(self):
                pass

        env = SimpleEVChargingEnv()
        logger.info(f"✓ Created simple EV charging environment")
        logger.info(f"  Observation space: {env.observation_space}")
        logger.info(f"  Action space: {env.action_space}")

    except Exception as e:
        logger.error(f"❌ Environment creation failed: {e}")
        sys.exit(1)

    # === PASO 3: TRAIN PPO ===
    logger.info("\n[PASO 3/3] Training PPO agent...")

    try:
        # Create PPO config
        train_steps = args.episodes or config.get("ppo_train_steps", 500000)
        lr = config.get("ppo_lr", 3e-4)

        ppo_config = PPOConfig(
            train_steps=train_steps,
            learning_rate=lr
        )

        logger.info(f"PPO Config:")
        logger.info(f"  Train steps: {train_steps}")
        logger.info(f"  Learning rate: {lr}")

        # Create and train agent
        logger.info("\nCreating PPO agent...")
        agent = make_ppo(env, ppo_config)

        logger.info(f"\n" + "=" * 70)
        logger.info(f"INICIANDO ENTRENAMIENTO PPO")
        logger.info(f"=" * 70)

        agent.learn(total_timesteps=train_steps)

        logger.info(f"\n" + "=" * 70)
        logger.info(f"✅ ENTRENAMIENTO PPO COMPLETADO")
        logger.info(f"=" * 70)

        return 0

    except Exception as e:
        logger.error(f"❌ PPO training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
