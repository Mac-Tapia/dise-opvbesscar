#!/usr/bin/env python
"""PPO training - Versión final robusta."""
import sys
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym

sys.path.insert(0, str(Path(__file__).parent.parent))

from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


class CityLearnWrapper(gym.Wrapper):
    """Wrapper simple para CityLearnEnv."""
    
    def __init__(self, env):
        super().__init__(env)
        # Action space: usar el primer Box de la lista
        if isinstance(self.env.action_space, list):
            self.action_space = self.env.action_space[0]
        # Observation space: 534 elementos
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(534,), dtype=np.float32
        )
    
    def _flatten_obs(self, obs):
        """Convierte observation (lista de listas) a array flat."""
        flat = []
        if isinstance(obs, list):
            for item in obs:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(float(item))
        return np.array(flat, dtype=np.float32)
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return self._flatten_obs(obs), info
    
    def step(self, action):
        # action es un numpy array (la salida del modelo PPO)
        # CityLearnEnv.step() espera una lista de acciones (una por agente)
        # Pero como desempaquetamos el action_space, solo tenemos un action
        # Necesitamos adaptarlo para que sea compatible
        # Intentar enviar directo
        try:
            obs, reward, done, truncated, info = self.env.step(action)
        except (IndexError, TypeError):
            # Si falla, intentar como lista
            obs, reward, done, truncated, info = self.env.step([action])
        
        obs_flat = self._flatten_obs(obs)
        # Convertir reward (lista) a scalar
        if isinstance(reward, list):
            reward_scalar = float(sum(reward))
        else:
            reward_scalar = float(reward)
        return obs_flat, reward_scalar, done, truncated, info


def main():
    logger.info("="*60)
    logger.info("PPO TRAINING - FINAL VERSION")
    logger.info("="*60)
    
    # Schema
    schema_path = Path("data/raw/citylearn_templates/schema.json")
    if not schema_path.exists():
        logger.error(f"Schema not found: {schema_path}")
        sys.exit(1)
    
    # Crear entorno
    logger.info("Creating environment...")
    base_env = CityLearnEnv(schema=str(schema_path))
    env = CityLearnWrapper(base_env)
    
    # Checkpoint dir
    ckpt_dir = Path("analyses/oe3/training/checkpoints/ppo")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Action space: {env.action_space}")
    logger.info(f"Observation space: {env.observation_space}")
    
    # Crear modelo
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
    logger.info("✓ Model created")
    
    logger.info("="*60)
    logger.info("STARTING TRAINING")
    logger.info("="*60)
    
    try:
        # Entrenar sin callbacks complicados
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=None,
            progress_bar=False,
        )
        
        logger.info("✅ TRAINING COMPLETED")
        
        # Guardar modelo final
        final_path = ckpt_dir / "ppo_final"
        model.save(str(final_path))
        logger.info(f"✓ Model saved: {final_path}.zip")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        env.close()


if __name__ == "__main__":
    main()
