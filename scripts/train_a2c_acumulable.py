#!/usr/bin/env python
"""
A2C TRAINING - Con checkpoints acumulables
Guarda checkpoints cada 2048 timesteps y permite continuar desde checkpoint
"""
import sys
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import CheckpointCallback

sys.path.insert(0, str(Path(__file__).parent.parent))
from citylearn.citylearn import CityLearnEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


class FlatActionWrapper(gym.Wrapper):
    """Flatten action y observation para Gymnasium compatibility."""
    
    def __init__(self, env):
        super().__init__(env)
        
        if isinstance(self.env.action_space, list):
            self.agent_action_spaces = self.env.action_space
            self.total_action_size = sum(space.shape[0] for space in self.agent_action_spaces)
            logger.info(f"Action spaces (list): {len(self.agent_action_spaces)} agents, total size: {self.total_action_size}")
        else:
            logger.error("Unexpected action_space type")
            sys.exit(1)
        
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        logger.info(f"Observation flattened shape: {obs_flat.shape}")
        
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=obs_flat.shape,
            dtype=np.float32,
        )
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
        action_list = self._unflatten_action(action)
        obs, reward, terminated, truncated, info = self.env.step(action_list)
        obs_flat = self._flatten_obs(obs)
        if isinstance(reward, list):
            reward_scalar = float(sum(reward))
        else:
            reward_scalar = float(reward)
        return obs_flat, reward_scalar, terminated, truncated, info


def main():
    logger.info("="*80)
    logger.info("A2C TRAINING - ACUMULABLE (CON CHECKPOINTS)")
    logger.info("="*80)
    
    schema_path = Path("data/raw/citylearn_templates/schema.json")
    if not schema_path.exists():
        logger.error(f"Schema not found: {schema_path}")
        sys.exit(1)
    
    logger.info("\n📁 Creating environment...")
    base_env = CityLearnEnv(schema=str(schema_path))
    env = FlatActionWrapper(base_env)
    
    # Checkpoint directory
    ckpt_dir = Path("analyses/oe3/training/checkpoints/a2c")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"✓ Action space: {env.action_space}")
    logger.info(f"✓ Observation space: {env.observation_space}")
    logger.info(f"✓ Checkpoint dir: {ckpt_dir}")
    
    # Buscar último checkpoint
    latest_checkpoint = None
    latest_step = 0
    
    checkpoint_files = list(ckpt_dir.glob("a2c_model_*_steps.zip"))
    if checkpoint_files:
        for f in checkpoint_files:
            try:
                step_num = int(f.name.split("_")[2])
                if step_num > latest_step:
                    latest_step = step_num
                    latest_checkpoint = f
            except:
                pass
    
    # Crear o cargar modelo
    logger.info("\n🤖 Setting up A2C model...")
    
    if latest_checkpoint:
        logger.info(f"✓ Encontrado checkpoint previo: {latest_checkpoint}")
        logger.info(f"✓ Pasos ya entrenados: {latest_step}")
        model = A2C.load(str(latest_checkpoint), env=env)
        logger.info(f"✓ Modelo cargado desde checkpoint")
        reset_num_timesteps = False
    else:
        logger.info("✓ Creando modelo nuevo A2C")
        model = A2C(
            "MlpPolicy",
            env,
            learning_rate=1e-3,
            n_steps=2048,
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.001,
            vf_coef=0.5,
            max_grad_norm=0.5,
            device="cpu",
            seed=42,
            verbose=0,
        )
        reset_num_timesteps = True
    
    # Callback para guardar checkpoints
    checkpoint_callback = CheckpointCallback(
        save_freq=2048,
        save_path=str(ckpt_dir),
        name_prefix="a2c_model",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )
    
    logger.info("\n" + "="*80)
    logger.info("▶️  INICIANDO ENTRENAMIENTO A2C")
    logger.info("="*80)
    logger.info(f"Timesteps totales: 17,520")
    logger.info(f"Checkpoint cada: 2,048 timesteps")
    logger.info(f"Reset num timesteps: {reset_num_timesteps}")
    
    try:
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=reset_num_timesteps,
            callback=checkpoint_callback,
            log_interval=50,
            progress_bar=False,
        )
        
        logger.info("\n" + "="*80)
        logger.info("✅ A2C TRAINING COMPLETADO")
        logger.info("="*80)
        
        # Guardar modelo final
        final_path = ckpt_dir / "a2c_final"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path}.zip")
        
    except Exception as e:
        logger.error(f"❌ Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        env.close()


if __name__ == "__main__":
    main()
