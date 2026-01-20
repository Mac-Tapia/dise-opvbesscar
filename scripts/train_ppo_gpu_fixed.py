#!/usr/bin/env python
"""
PPO TRAINING - GPU OPTIMIZED VERSION (FIXED)
MALL IQUITOS CON PLAYAS DE CARGA (128 TOMAS)
"""
import sys
import os
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyses/logs/ppo_gpu_fixed.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
from citylearn.citylearn import CityLearnEnv

# SCHEMA CONFIGURATION
SCHEMA_PATH = "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json"


class MetricsCallback(BaseCallback):
    """Callback para registrar metricas durante entrenamiento"""
    def __init__(self):
        super().__init__()
        self.last_log = 0
    
    def _on_step(self) -> bool:
        if self.num_timesteps - self.last_log >= 500 or self.num_timesteps == 0:
            logger.info(f"Step {self.num_timesteps}/17520")
            self.last_log = self.num_timesteps
        return True


class FlatActionWrapper(gym.Wrapper):
    """Flatten action y observation para Gymnasium compatibility."""
    def __init__(self, env):
        super().__init__(env)
        
        if isinstance(self.env.action_space, list):
            self.agent_action_spaces = self.env.action_space
            self.total_action_size = sum(space.shape[0] for space in self.agent_action_spaces)
        else:
            raise ValueError("Unexpected action_space type")
        
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        
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
    
    def _flatten_obs(self, obs):
        if isinstance(obs, list):
            def flatten_recursive(x):
                if isinstance(x, (list, tuple)):
                    result = []
                    for item in x:
                        result.extend(flatten_recursive(item))
                    return result
                else:
                    return [float(x)]
            return np.array(flatten_recursive(obs), dtype=np.float32)
        else:
            return np.array(obs, dtype=np.float32).flatten()
    
    def _unflatten_action(self, flat_action):
        actions = []
        idx = 0
        for space in self.agent_action_spaces:
            dim = space.shape[0]
            actions.append(flat_action[idx:idx+dim])
            idx += dim
        return actions
    
    def step(self, action):
        unflat_action = self._unflatten_action(action)
        obs, reward, terminated, truncated, info = self.env.step(unflat_action)
        obs_flat = self._flatten_obs(obs)
        
        # IMPORTANTE: Asegurar que reward es float, no lista
        if isinstance(reward, (list, np.ndarray)):
            reward = float(np.mean(reward))
        else:
            reward = float(reward)
        
        return obs_flat, reward, terminated, truncated, info
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, info


def main():
    logger.info("="*100)
    logger.info("PPO TRAINING - GPU OPTIMIZED (FIXED)")
    logger.info("MALL IQUITOS: 128 TOMAS (16 MOTOTAXIS + 112 MOTOS)")
    logger.info("="*100)
    
    # Verificar GPU
    logger.info(f"\n[GPU STATUS]")
    logger.info(f"CUDA: {torch.cuda.is_available()}")
    # Usar GPU a pesar del warning - más rápido que CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")
    
    # 1. VALIDAR SCHEMA
    logger.info(f"\n[STEP 1] SCHEMA")
    schema_path = Path(SCHEMA_PATH)
    if not schema_path.exists():
        logger.error(f"Not found: {schema_path}")
        sys.exit(1)
    logger.info(f"OK: {schema_path}")
    
    # 2. CREAR ENVIRONMENT
    logger.info(f"\n[STEP 2] ENVIRONMENT")
    base_env = CityLearnEnv(schema=str(schema_path))
    logger.info(f"Building: {base_env.buildings[0].name}")
    logger.info(f"Central agent: {base_env.central_agent}")
    
    # 3. APLICAR WRAPPER
    logger.info(f"\n[STEP 3] WRAPPER")
    env = FlatActionWrapper(base_env)
    logger.info(f"Actions: {env.action_space.shape}")
    logger.info(f"Observations: {env.observation_space.shape}")
    
    # 4. CHECKPOINTS
    logger.info(f"\n[STEP 4] CHECKPOINTS")
    ckpt_dir = Path("analyses/oe3/training/checkpoints/ppo_gpu")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Dir: {ckpt_dir}")
    
    # 5. CREAR/CARGAR MODELO
    logger.info(f"\n[STEP 5] MODEL")
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=5e-4,
        n_steps=2048,          # Optimizado GPU - rollout más pequeño
        batch_size=256,        # Batch size grande para GPU
        n_epochs=2,            # Muy pocas epochs para GPU
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.0,          # Sin entropy coefficient
        vf_coef=0.5,
        max_grad_norm=0.5,
        device=device,
        verbose=1              # Más verbose para ver progreso
    )
    logger.info(f"PPO created on {device}")
    
    # 6. CALLBACKS
    logger.info(f"\n[STEP 6] CALLBACKS")
    checkpoint_callback = CheckpointCallback(
        save_freq=2048,
        save_path=str(ckpt_dir),
        name_prefix="ppo"
    )
    metrics_callback = MetricsCallback()
    logger.info(f"Callbacks ready")
    
    # 7. TRAINING
    logger.info(f"\n[STEP 7] TRAINING START")
    logger.info(f"Total: 17,520 timesteps (GPU acelerado - 2 EPISODIOS COMPLETOS - ~40-45 min)")
    
    try:
        model.learn(
            total_timesteps=17520,
            callback=[checkpoint_callback, metrics_callback],
            reset_num_timesteps=True,
            log_interval=1
        )
        logger.info(f"\nTRAINING COMPLETED!")
        
        # Save final
        model.save(str(ckpt_dir / "ppo_final.zip"))
        logger.info(f"Final model saved")
        
    except KeyboardInterrupt:
        logger.warning(f"Interrupted")
        model.save(str(ckpt_dir / "ppo_interrupted.zip"))
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        env.close()
        logger.info(f"Done")


if __name__ == "__main__":
    main()
