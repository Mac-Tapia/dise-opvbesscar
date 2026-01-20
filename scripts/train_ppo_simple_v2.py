#!/usr/bin/env python
"""PPO simple training - Sin wrappers complejos, solo logueo directo."""
from __future__ import annotations

import sys
from pathlib import Path
import logging
from datetime import datetime
import numpy as np

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


class SimpleProgressCallback(BaseCallback):
    """Callback simple para loguear progreso."""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.now()
        self.last_log_step = 0
    
    def _on_step(self) -> bool:
        if self.num_timesteps - self.last_log_step >= 500:
            elapsed = datetime.now() - self.start_time
            logger.info(
                f"[PPO] paso {self.num_timesteps:6d} | "
                f"tiempo={str(elapsed).split('.')[0]} | "
                f"lr={self.model.lr_schedule(self.num_timesteps):.2e}"
            )
            self.last_log_step = self.num_timesteps
            
            # Guardar checkpoint cada 500 pasos
            if self.num_timesteps % 500 == 0:
                checkpoint_path = Path(self.model.tensorboard_log or ".") / f"ppo_step_{self.num_timesteps}"
                try:
                    self.model.save(str(checkpoint_path))
                    logger.info(f"[PPO CHECKPOINT] Saved step {self.num_timesteps}")
                except Exception as e:
                    logger.warning(f"Failed to save checkpoint: {e}")
        
        return True


def main():
    logger.info("="*70)
    logger.info("PPO TRAINING - SIMPLE VERSION")
    logger.info("="*70)
    
    cfg, rp = load_all("configs/default.yaml")
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Entorno: {schema_path}")
    
    try:
        env = CityLearnEnv(schema=str(schema_path))
        logger.info("✓ Entorno cargado")
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
        logger.info("✓ Modelo PPO creado correctamente")
    except Exception as e:
        logger.error(f"Error creando modelo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    logger.info("\n" + "="*70)
    logger.info("INICIANDO ENTRENAMIENTO (17,520 timesteps)")
    logger.info("="*70 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Entrenar con callback simple
        callback = SimpleProgressCallback()
        
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
        logger.info(f"✓ Modelo final: {final_path}.zip")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido")
    except Exception as e:
        logger.error(f"\n❌ Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            env.close()
            logger.info("✓ Entorno cerrado")
        except:
            pass


if __name__ == "__main__":
    main()
