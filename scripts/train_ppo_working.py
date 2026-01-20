#!/usr/bin/env python
"""PPO Training con wrapper para CityLearnEnv (convierte lista -> array)."""
from __future__ import annotations

import sys
from pathlib import Path
import logging
from datetime import datetime
import numpy as np
import gymnasium as gym

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


class ListToArrayWrapper(gym.Wrapper):
    """Convierte observación de lista a numpy array con Box space."""
    
    def __init__(self, env):
        super().__init__(env)
        
        # Reset para obtener estructura de observación
        obs, _ = env.reset()
        obs_flat = self._flatten_obs(obs)
        
        logger.info(f"Observation shape: {obs_flat.shape}")
        
        # Definir spaces
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=obs_flat.shape,
            dtype=np.float32,
        )
        self.action_space = env.action_space
    
    def _flatten_obs(self, obs):
        """Convierte observación (lista o array) a array plano."""
        if isinstance(obs, list):
            # Si es lista de listas, aplanar
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
        else:
            return np.array(obs, dtype=np.float32).flatten()
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, info
    
    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        obs_flat = self._flatten_obs(obs)
        return obs_flat, reward, terminated, truncated, info


class SimpleProgressCallback(BaseCallback):
    """Callback para loguear progreso cada 500 pasos."""
    
    def __init__(self, checkpoint_dir: Path):
        super().__init__()
        self.checkpoint_dir = checkpoint_dir
        self.start_time = datetime.now()
        self.last_log_step = 0
    
    def _on_step(self) -> bool:
        # Log cada 500 pasos
        if self.num_timesteps - self.last_log_step >= 500:
            elapsed = datetime.now() - self.start_time
            logger.info(
                f"[PPO] paso {self.num_timesteps:6d} | "
                f"tiempo={str(elapsed).split('.')[0]} | "
                f"lr={self.model.lr_schedule(self.num_timesteps):.2e}"
            )
            self.last_log_step = self.num_timesteps
            
            # Guardar checkpoint
            try:
                checkpoint_file = self.checkpoint_dir / f"ppo_step_{self.num_timesteps}.zip"
                self.model.save(str(checkpoint_file))
                logger.info(f"[PPO CHECKPOINT] Guardado: step {self.num_timesteps}")
            except Exception as e:
                logger.warning(f"Error guardando checkpoint: {e}")
        
        return True


def main():
    logger.info("="*70)
    logger.info("PPO TRAINING - VERSIÓN SIMPLIFICADA CON WRAPPER")
    logger.info("="*70)
    
    cfg, rp = load_all("configs/default.yaml")
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Entorno: {schema_path}")
    
    try:
        base_env = CityLearnEnv(schema=str(schema_path))
        env = ListToArrayWrapper(base_env)
        logger.info("✓ Entorno cargado y envuelto")
    except Exception as e:
        logger.error(f"Error cargando entorno: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    
    logger.info("\nConfiguración PPO:")
    logger.info(f"  device: {ppo_cfg.get('device', 'cpu')}")
    logger.info(f"  learning_rate: {ppo_cfg.get('learning_rate', 2.5e-4)}")
    logger.info(f"  n_steps: {ppo_cfg.get('n_steps', 2048)}")
    logger.info(f"  batch_size: {ppo_cfg.get('batch_size', 512)}")
    logger.info(f"  n_epochs: {ppo_cfg.get('n_epochs', 20)}")
    logger.info(f"  ent_coef: {ppo_cfg.get('ent_coef', 0.005)}")
    logger.info(f"  total_timesteps: 17520 (2 episodios)")
    
    logger.info("\n" + "="*70)
    logger.info("Creando modelo PPO...")
    logger.info("="*70)
    
    try:
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=float(ppo_cfg.get("learning_rate", 2.5e-4)),
            n_steps=int(ppo_cfg.get("n_steps", 2048)),
            batch_size=int(ppo_cfg.get("batch_size", 512)),
            n_epochs=int(ppo_cfg.get("n_epochs", 20)),
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=float(ppo_cfg.get("ent_coef", 0.005)),
            vf_coef=0.5,
            max_grad_norm=0.5,
            use_sde=True,
            sde_sample_freq=-1,
            device=ppo_cfg.get("device", "cpu"),
            seed=42,
            verbose=0,
        )
        logger.info("✓ Modelo PPO creado correctamente\n")
    except Exception as e:
        logger.error(f"Error creando modelo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    logger.info("="*70)
    logger.info("INICIANDO ENTRENAMIENTO (17,520 timesteps = 2 episodios)")
    logger.info("="*70 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Entrenar con callback
        callback = SimpleProgressCallback(checkpoint_dir)
        
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=100,
            progress_bar=False,
            callback=callback,
        )
        
        elapsed = datetime.now() - start_time
        logger.info(f"\n✅ ENTRENAMIENTO COMPLETADO en {elapsed}")
        
        # Guardar modelo final
        final_path = checkpoint_dir / "ppo_final"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path}.zip")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            env.close()
        except:
            pass


if __name__ == "__main__":
    main()
