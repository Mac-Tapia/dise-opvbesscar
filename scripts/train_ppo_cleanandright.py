#!/usr/bin/env python
"""PPO TRAINING - Con action/observation FLATTENED."""
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


class FlatActionWrapper(gym.Wrapper):
    """Flattena action y observation para Gymnasium compatibility."""
    
    def __init__(self, env):
        super().__init__(env)
        
        # Inspeccionar action_space (lista de Box)
        if isinstance(self.env.action_space, list):
            self.agent_action_spaces = self.env.action_space
            # Calcular tamaño total de acciones
            self.total_action_size = sum(space.shape[0] for space in self.agent_action_spaces)
            logger.info(f"Action spaces (list): {len(self.agent_action_spaces)} agents, total size: {self.total_action_size}")
        else:
            logger.error("Unexpected action_space type")
            sys.exit(1)
        
        # Reset para obtener obs
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        logger.info(f"Observation flattened shape: {obs_flat.shape}")
        
        # Crear spaces - SIN lista
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=obs_flat.shape,
            dtype=np.float32,
        )
        # Crear action_space como Box único (concatenado)
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0,
            shape=(self.total_action_size,),
            dtype=np.float32,
        )
        logger.info(f"New action space: {self.action_space}")
    
    def _flatten_obs(self, obs):
        """Convierte obs (lista) a array."""
        if isinstance(obs, list):
            def flatten_recursive(x):
                if isinstance(x, (list, tuple)):
                    result = []
                    for item in x:
                        result.extend(flatten_recursive(item))
                    return result
                else:
                    return [x]
            flat = flatten_recursive(obs)
            return np.array(flat, dtype=np.float32)
        return np.array(obs, dtype=np.float32).flatten()
    
    def _unflatten_action(self, flat_action):
        """Convierte action flat a lista de actions."""
        actions = []
        idx = 0
        for space in self.agent_action_spaces:
            size = space.shape[0]
            actions.append(flat_action[idx:idx+size])
            idx += size
        return actions
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return self._flatten_obs(obs), info
    
    def step(self, action):
        # Convertir action flat a lista
        action_list = self._unflatten_action(action)
        # Pasar al env
        obs, reward, terminated, truncated, info = self.env.step(action_list)
        obs_flat = self._flatten_obs(obs)
        # Convertir reward lista a scalar
        if isinstance(reward, list):
            reward_scalar = float(sum(reward))
        else:
            reward_scalar = float(reward)
        return obs_flat, reward_scalar, terminated, truncated, info


def main():
    logger.info("="*60)
    logger.info("PPO TRAINING - FLATTENED VERSION")
    logger.info("="*60)
    
    # Schema
    schema_path = Path("data/raw/citylearn_templates/schema.json")
    if not schema_path.exists():
        logger.error(f"Schema not found: {schema_path}")
        sys.exit(1)
    
    # Crear entorno
    logger.info("Creating environment...")
    base_env = CityLearnEnv(schema=str(schema_path))
    env = FlatActionWrapper(base_env)
    
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
    logger.info("STARTING TRAINING (17,520 timesteps)")
    logger.info("="*60)
    
    try:
        # Entrenar
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=1000,
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
