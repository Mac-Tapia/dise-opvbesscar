#!/usr/bin/env python
"""Entrenar PPO desde cero en CPU (optimal para MlpPolicy)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.ppo_sb3 import PPOAgent, PPOConfig
from citylearn.citylearn import CityLearnEnv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    cfg, rp = load_all("configs/default.yaml")
    
    dataset_dir = rp.processed_dir / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_dir / "schema_pv_bess.json"
    checkpoint_dir = rp.analyses_dir / "oe3" / "training" / "checkpoints" / "ppo"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Cargando entorno: {schema_path}")
    env = CityLearnEnv(schema=str(schema_path))
    
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    
    # === CONFIGURACIÓN PARA CPU (MlpPolicy óptimo) ===
    config = PPOConfig(
        train_steps=17520,  # 2 episodios × 8760 pasos
        n_steps=2048,       # n_steps para 17520 pasos: 17520 / 2048 ≈ 8.5 updates
        batch_size=512,
        n_epochs=10,
        learning_rate=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        device="cpu",  # CRITICAL: CPU para MlpPolicy
        seed=42,
        verbose=0,
        log_interval=250,
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_freq_steps=500,
        # Multiobjetivo desde config
        weight_co2=float(ppo_cfg.get("multi_objective_weights", {}).get("co2", 0.50)),
        weight_cost=float(ppo_cfg.get("multi_objective_weights", {}).get("cost", 0.15)),
        weight_solar=float(ppo_cfg.get("multi_objective_weights", {}).get("solar", 0.20)),
        weight_ev_satisfaction=float(ppo_cfg.get("multi_objective_weights", {}).get("ev", 0.10)),
        weight_grid_stability=float(ppo_cfg.get("multi_objective_weights", {}).get("grid", 0.05)),
    )
    
    logger.info(f"Configuración PPO (CPU optimizado):")
    logger.info(f"  device={config.device}")
    logger.info(f"  n_steps={config.n_steps}, batch_size={config.batch_size}")
    logger.info(f"  learning_rate={config.learning_rate}")
    logger.info(f"  total_timesteps=17520 (2 episodios)")
    logger.info(f"  checkpoint_freq_steps={config.checkpoint_freq_steps}")
    
    logger.info("\n" + "="*60)
    logger.info("CREANDO AGENTE PPO")
    logger.info("="*60)
    
    agent = PPOAgent(env, config)
    
    logger.info("\n" + "="*60)
    logger.info("INICIANDO ENTRENAMIENTO PPO EN CPU")
    logger.info("="*60)
    
    try:
        agent.learn(total_timesteps=17520)
        logger.info("\n✅ ENTRENAMIENTO PPO COMPLETADO EXITOSAMENTE")
    except KeyboardInterrupt:
        logger.info("\n⚠️ Entrenamiento interrumpido por usuario")
    except Exception as e:
        logger.error(f"\n❌ Error en entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
