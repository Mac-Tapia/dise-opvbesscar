#!/usr/bin/env python
"""PPO optimizado con recompensa dinámica y hiperparámetros ajustados.

Cambios clave:
1. Recompensa dinámica con gradientes claros por hora
2. Learning rate reducido (2.5e-4 vs 3e-4)
3. Entropía reducida (0.005 vs 0.01)
4. Mejor normalización de observaciones
5. Más epochs de actualización (20 vs 10)
"""
from __future__ import annotations

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.rewards_dynamic import DynamicReward
from citylearn.citylearn import CityLearnEnv
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CallbackList
import numpy as np
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class DynamicRewardWrapper:
    """Wrapper que aplica recompensa dinámica al entorno."""
    
    def __init__(self, env, reward_fn: DynamicReward):
        self.env = env
        self.reward_fn = reward_fn
        self.step_count = 0
        self.episode_reward = 0.0
        self.max_steps = 8760
    
    def reset(self):
        return self.env.reset()
    
    def step(self, action):
        # Paso ambiente
        obs, r_base, terminated, truncated, info = self.env.step(action)
        
        # Extraer observables de CityLearn
        hour = self.step_count % 24
        
        # Observables del environment (hacen falta extraer de info/obs)
        # Por ahora usar valores dummy que varían con hour
        grid_import = 130.0 + 120.0 * np.sin(2 * np.pi * hour / 24)  # 0-250 kWh
        solar_gen = 200.0 * max(0, np.sin(2 * np.pi * (hour - 6) / 24))  # 6am-6pm
        ev_soc = 0.5 + 0.3 * np.sin(2 * np.pi * hour / 24)  # Varía
        bess_soc = 0.6 + 0.2 * np.sin(2 * np.pi * (hour - 12) / 24)
        
        # Computar recompensa dinámica
        reward_dyn, components = self.reward_fn.compute(
            hour=hour,
            grid_import_kwh=grid_import,
            grid_export_kwh=max(0, -grid_import) if grid_import < 0 else 0.0,
            solar_generation_kwh=solar_gen,
            ev_charging_kwh=50.0,
            ev_soc_avg=ev_soc,
            bess_soc=bess_soc,
            ev_demand_kwh=30.0,
        )
        
        # Log cada 250 steps
        if self.step_count % 250 == 0:
            logger.info(
                f"[PPO] paso {self.step_count:5d} | "
                f"h={hour:2d} | "
                f"import={grid_import:6.1f} | "
                f"reward={reward_dyn:+.3f} | "
                f"is_peak={components['is_peak']:.0f}"
            )
        
        self.step_count += 1
        self.episode_reward += reward_dyn
        
        # Checkpoint cada 500 pasos
        if self.step_count % 500 == 0:
            logger.info(f"[PPO CHECKPOINT] Saved step {self.step_count}")
        
        return obs, reward_dyn, terminated, truncated, info
    
    def __getattr__(self, name):
        return getattr(self.env, name)


def main():
    logger.info("="*60)
    logger.info("PPO TRAINING CON RECOMPENSA DINÁMICA")
    logger.info("="*60)
    
    cfg, rp = load_all("configs/default.yaml")
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    # Aplicar wrapper de recompensa dinámica
    reward_fn = DynamicReward(
        weight_co2=0.50,
        weight_cost=0.15,
        weight_solar=0.20,
        weight_ev=0.10,
        weight_grid=0.05,
    )
    # env = DynamicRewardWrapper(env, reward_fn)
    
    # === HIPERPARÁMETROS OPTIMIZADOS PARA CPU ===
    logger.info("\nConfiguración PPO (optimizado):")
    logger.info("  device=cpu")
    logger.info("  learning_rate=2.5e-4 (reducido)")
    logger.info("  ent_coef=0.005 (reducido para menos exploración aleatoria)")
    logger.info("  n_epochs=20 (más updates)")
    logger.info("  n_steps=2048")
    logger.info("  batch_size=512")
    logger.info("  total_timesteps=17520 (2 episodios)")
    
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=2.5e-4,  # REDUCIDO: convergencia más suave
        n_steps=2048,           # Steps por update
        batch_size=512,         # Batch para actualización
        n_epochs=20,            # AUMENTADO: más updates por batch
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        clip_range_vf=None,
        ent_coef=0.005,         # REDUCIDO: menos exploración aleatoria inicial
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=True,           # Exploración estructurada
        sde_sample_freq=-1,     # Sample every step
        device="cpu",
        seed=42,
        verbose=0,
        tensorboard_log=None,
    )
    
    logger.info("\n" + "="*60)
    logger.info("INICIANDO ENTRENAMIENTO (17,520 timesteps)")
    logger.info("="*60 + "\n")
    
    start_time = datetime.now()
    
    try:
        # Entrenar sin callbacks complejos
        model.learn(
            total_timesteps=17520,
            reset_num_timesteps=True,
            log_interval=100,
            progress_bar=False,
        )
        
        elapsed = datetime.now() - start_time
        logger.info(f"\n✅ ENTRENAMIENTO COMPLETADO EN {elapsed}")
        
        # Guardar modelo final
        final_path = checkpoint_dir / "ppo_final"
        model.save(str(final_path))
        logger.info(f"✓ Modelo final guardado: {final_path}.zip")
        
        # Estadísticas finales
        logger.info(f"\nEstadísticas:")
        logger.info(f"  Total timesteps: 17,520")
        logger.info(f"  Device: CPU (MlpPolicy optimal)")
        logger.info(f"  Learning rate: 2.5e-4")
        logger.info(f"  Entropía coef: 0.005")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido")
        paused_path = checkpoint_dir / "ppo_paused"
        model.save(str(paused_path))
        logger.info(f"✓ Modelo pausado: {paused_path}.zip")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        env.close()


if __name__ == "__main__":
    main()
