#!/usr/bin/env python3
"""Test checkpoint callback execution with minimal setup."""
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test 1: Verify callback can write files
test_dir = Path("test_checkpoint_dir")
test_dir.mkdir(exist_ok=True)

# Create a dummy test with Stable-Baselines3
try:
    import gymnasium as gym
    import numpy as np
    from stable_baselines3 import SAC
    from stable_baselines3.common.callbacks import BaseCallback
    
    logger.info("✓ Stable-Baselines3 imports successful")
    
    # Create a simple test environment
    env = gym.make("Pendulum-v1")
    
    # Create a test callback
    class TestCallback(BaseCallback):
        def __init__(self, save_dir, freq=100):
            super().__init__()
            self.save_dir = Path(save_dir)
            self.freq = freq
            self.save_count = 0
            logger.info(f"[TestCallback] Initialized with save_dir={self.save_dir}, freq={self.freq}")
            self.save_dir.mkdir(parents=True, exist_ok=True)
        
        def _on_step(self):
            # Log every 100 steps
            if self.n_calls % 100 == 0:
                logger.debug(f"[TestCallback] _on_step called: n_calls={self.n_calls}")
            
            # Save at checkpoint frequency
            if self.n_calls > 0 and self.n_calls % self.freq == 0:
                save_path = self.save_dir / f"test_step_{self.n_calls}.zip"
                try:
                    self.model.save(str(save_path))
                    self.save_count += 1
                    logger.info(f"✓ [TestCallback] Saved checkpoint #{self.save_count}: {save_path}")
                except Exception as e:
                    logger.error(f"✗ [TestCallback] Failed to save: {e}")
            return True
    
    # Train with callback
    logger.info("\nStarting test training...")
    model = SAC("MlpPolicy", env, verbose=0, device="cpu")  # Use CPU for faster test
    callback = TestCallback(test_dir, freq=100)
    
    logger.info("Calling model.learn() with callback...")
    model.learn(total_timesteps=500, callback=callback, log_interval=None)
    
    logger.info("✓ Training completed")
    
    # Check saved files
    saved_files = list(test_dir.glob("*.zip"))
    logger.info(f"\n✓ Checkpoints saved: {len(saved_files)}")
    for f in saved_files:
        logger.info(f"  - {f.name}: {f.stat().st_size / 1024:.1f} KB")
    
    if len(saved_files) == 0:
        logger.warning("✗ NO CHECKPOINTS WERE SAVED!")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    
except Exception as e:
    logger.exception("Test failed: %s", e)
    sys.exit(1)
