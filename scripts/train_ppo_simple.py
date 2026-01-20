#!/usr/bin/env python
"""PPO training simple y robusto - sin callbacks complicados."""
import sys
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym

sys.path.insert(0, str(Path(__file__).parent.parent))

from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class CityLearnFixWrapper(gym.Wrapper):
    """Wrapper que arregla action_space y observation de CityLearnEnv."""
    
    def __init__(self, env):
        super().__init__(env)
        # Desempaquetar action_space si es lista
        if isinstance(self.env.action_space, list):
            self.action_space = self.env.action_space[0]
        # Crear observation_space correcto (los 534 elementos)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(534,), dtype=np.float32
        )
    
    def _flatten_obs(self, obs):
        """Convierte observation a array (926,)."""
        if isinstance(obs, list):
            flat = []
            for item in obs:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(item)
            return np.array(flat, dtype=np.float32)
        return np.array(obs, dtype=np.float32)
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, info
    
    def step(self, action):
        # Empaquetar action en lista para env
        obs, reward, done, truncated, info = self.env.step([action])
        obs_flat = self._flatten_obs(obs)
        # Convertir reward a scalar
        if isinstance(reward, list):
            reward_scalar = float(sum(reward))
        else:
            reward_scalar = float(reward)
        return obs_flat, reward_scalar, done, truncated, info


def main():
    logger.info("═" * 60)
    logger.info("PPO TRAINING - SIMPLE VERSION")
    logger.info("═" * 60)
    
    # Cargar schema
    schema_path = Path("data/raw/citylearn_templates/schema.json")
    if not schema_path.exists():
        logger.error(f"Schema not found: {schema_path}")
        sys.exit(1)
    
    # Crear entorno
    logger.info("Creating CityLearn environment...")
    env = CityLearnEnv(schema=str(schema_path))
    env = CityLearnFixWrapper(env)
    
    # Crear directorio
    ckpt_dir = Path("analyses/oe3/training/checkpoints/ppo")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear modelo PPO
    logger.info("Creating PPO model...")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=2.5e-4,
        n_steps=2048,
        batch_size=512,
        n_epochs=20,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.005,
        vf_coef=0.5,
        max_grad_norm=0.5,
        device="cpu",
        seed=42,
        verbose=0,
    )
    logger.info("✓ PPO model created")
    
    logger.info("═" * 60)
    logger.info("STARTING TRAINING (17,520 timesteps)")
    logger.info("═" * 60 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Custom callback inline para logueo
        class SimpleCallback:
            def __init__(self, log_freq=500):
                self.log_freq = log_freq
                self.num_calls = 0
            
            def __call__(self, locals_dict, globals_dict):
                if self.num_calls % self.log_freq == 0:
                    step = locals_dict["self"].num_timesteps
                    logger.info(f"Step {step:6d}/{17520} - Training in progress...")
                    
                    # Guardar checkpoint
                    model_path = ckpt_dir / f"ppo_step_{step}"
                    model.save(str(model_path))
                    logger.info(f"  ✓ Checkpoint saved: {model_path.name}.zip")
                
                self.num_calls += 1
                return True
        
        callback = SimpleCallback(log_freq=500)
        
        # Entrenar
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=None,
            progress_bar=False,
            callback=callback,
        )
        
        elapsed = datetime.now() - start_time
        logger.info(f"\n✅ TRAINING COMPLETED in {elapsed}")
        
        # Guardar modelo final
        final_path = ckpt_dir / "ppo_final"
        model.save(str(final_path))
        logger.info(f"✓ Final model saved: {final_path}.zip")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Training interrupted")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        env.close()


if __name__ == "__main__":
    main()
