#!/usr/bin/env python
"""PPO training con wrapper correcto para CityLearnEnv.

Wrapper convierte:
- observation: list → np.array(926,)
- action_space: [Box] → Box (desempaqueta lista)
- action: Box → [action] (empaqueta para env)
"""
from __future__ import annotations

import sys
from pathlib import Path
import logging
import numpy as np
import gymnasium as gym

sys.path.insert(0, str(Path(__file__).parent.parent))

from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class CityLearnFixWrapper(gym.Wrapper):
    """Wrapper que arregla action_space y observation de CityLearnEnv.
    
    CityLearnEnv:
    - observation: list de listas (list[list]) → convierte a np.array(926,)
    - action_space: [Box] (lista) → convierte a Box directo
    - action: Box → convierte a [action] para env
    """
    
    def __init__(self, env: CityLearnEnv):
        super().__init__(env)
        
        # Fix action_space: desempaquetar [Box] → Box
        if isinstance(self.env.action_space, list) and len(self.env.action_space) > 0:
            self.action_space = self.env.action_space[0]
            logger.info(f"✓ action_space fixed: {self.action_space}")
        
        # Fix observation_space: crear Box para array (926,)
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(926,), dtype=np.float32
        )
        logger.info(f"✓ observation_space set: Box(926,)")
    
    def _flatten_obs(self, obs) -> np.ndarray:
        """Convierte observation (list o nested) a array (926,)."""
        if isinstance(obs, list):
            # obs es lista de listas/valores
            flat = []
            for item in obs:
                if isinstance(item, (list, tuple)):
                    flat.extend(item)
                else:
                    flat.append(item)
            return np.array(flat, dtype=np.float32)
        else:
            return np.array(obs, dtype=np.float32)
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        logger.info(f"Reset: obs shape {obs_flat.shape}")
        return obs_flat, info
    
    def step(self, action: np.ndarray):
        """action es np.array(130,) → convierte a [action] para env."""
        # Empaquetar action como [action]
        action_wrapped = [action]
        
        obs, reward, terminated, truncated, info = self.env.step(action_wrapped)
        obs_flat = self._flatten_obs(obs)
        
        # Convertir reward a scalar (si es lista, tomar primero o suma)
        if isinstance(reward, (list, tuple)):
            reward = float(sum(reward)) if len(reward) > 0 else 0.0
        else:
            reward = float(reward)
        
        return obs_flat, reward, terminated, truncated, info


class LoggingCallback(BaseCallback):
    """Log progreso cada N pasos."""
    
    def __init__(self, log_freq: int = 500):
        super().__init__()
        self.log_freq = log_freq
    
    def _on_step(self) -> bool:
        if self.n_calls % self.log_freq == 0 and self.model is not None:
            ep_infos = list(self.model.ep_info_buffer)
            rewards = [float(info.get("r", 0.0)) for info in ep_infos if isinstance(info, dict)]
            reward_mean = float(np.mean(rewards)) if rewards else 0.0
            logger.info(f"[PPO] paso {self.n_calls:6d} | reward_mean={reward_mean:.3f}")
        return True


def main():
    logger.info("="*60)
    logger.info("PPO TRAINING (FIXED ACTION SPACE)")
    logger.info("="*60)
    
    # Cargar entorno
    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")
    logger.info(f"Cargando: {schema_path}")
    
    env = CityLearnEnv(schema=str(schema_path))
    logger.info(f"Original action_space: {env.action_space}")
    logger.info(f"Original observation_space: {env.observation_space}")
    
    # Aplicar wrapper
    env = CityLearnFixWrapper(env)
    logger.info(f"Fixed action_space: {env.action_space}")
    logger.info(f"Fixed observation_space: {env.observation_space}")
    
    # Crear directorio checkpoints
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/ppo")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("\n" + "="*60)
    logger.info("CONFIGURACIÓN PPO")
    logger.info("="*60)
    logger.info("  device: cpu")
    logger.info("  learning_rate: 2.5e-4")
    logger.info("  ent_coef: 0.005")
    logger.info("  n_epochs: 20")
    logger.info("  batch_size: 512")
    logger.info("  n_steps: 2048")
    logger.info("  total_timesteps: 17520")
    
    # Crear modelo PPO
    logger.info("\nCreando modelo PPO...")
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
        use_sde=True,
        sde_sample_freq=-1,
        device="cpu",
        seed=42,
        verbose=0,
        tensorboard_log=None,
    )
    logger.info("✓ Modelo PPO creado")
    
    logger.info("\n" + "="*60)
    logger.info("INICIANDO ENTRENAMIENTO (17,520 timesteps)")
    logger.info("="*60 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Callback para logueo
        callback = LoggingCallback(log_freq=500)
        
        # Entrenar
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=100,
            progress_bar=False,
            callback=callback,
        )
        
        elapsed = datetime.now() - start_time
        logger.info(f"\n✅ ENTRENAMIENTO COMPLETADO EN {elapsed}")
        
        # Guardar modelo final
        final_path = checkpoint_dir / "ppo_final"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path}.zip")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        env.close()


if __name__ == "__main__":
    main()
