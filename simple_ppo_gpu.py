#!/usr/bin/env python3
"""
Script simple para relanzar PPO sin callbacks - solo entrenamiento puro con GPU.
Uso: python simple_ppo_gpu.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts._common import load_all
from src.iquitos_citylearn.oe3.agents.ppo_sb3 import make_ppo
from src.iquitos_citylearn.oe3.rewards import MultiObjectiveReward
from src.iquitos_citylearn.oe3.envs import CityLearnEnv

def main():
    print("\n" + "="*70)
    print("🚀 PPO SIMPLE TRAINING (GPU MAX)")
    print("="*70)
    
    # Cargar config
    cfg, rp = load_all("configs/default.yaml")
    ppo_cfg = cfg["oe3"]["evaluation"]["ppo"]
    
    print(f"\n✓ Config cargada")
    print(f"  Episodios: {ppo_cfg.get('episodes', 5)}")
    print(f"  Timesteps: {ppo_cfg.get('timesteps', 87600)}")
    print(f"  Device: {ppo_cfg.get('device', 'cuda')}")
    print(f"  Resume: {ppo_cfg.get('resume_checkpoints', True)}")
    
    # Crear entorno
    schema_path = Path(rp.data_processed) / "citylearn" / "iquitos_ev_mall" / "schema_pv_bess.json"
    print(f"\n✓ Entorno: {schema_path}")
    
    env = CityLearnEnv(str(schema_path))
    reward_fn = MultiObjectiveReward(
        weights={
            "co2": ppo_cfg.get("multi_objective_weights", {}).get("co2", 0.5),
            "cost": ppo_cfg.get("multi_objective_weights", {}).get("cost", 0.15),
            "solar": ppo_cfg.get("multi_objective_weights", {}).get("solar", 0.2),
            "ev": ppo_cfg.get("multi_objective_weights", {}).get("ev", 0.1),
            "grid": ppo_cfg.get("multi_objective_weights", {}).get("grid", 0.05),
        }
    )
    env.reward_fn = reward_fn
    
    # Crear agente PPO
    print(f"\n✓ Creando agente PPO...")
    model = make_ppo(env, ppo_cfg)
    
    # Entrenar DIRECTAMENTE sin callbacks complejos
    print(f"\n✓ INICIANDO ENTRENAMIENTO...")
    print(f"  Timesteps: {ppo_cfg.get('timesteps', 87600)}")
    print(f"  GPU: CUDA (8.59 GB disponible)")
    print(f"  AMP: Habilitado")
    print("\n" + "="*70)
    
    try:
        # Entrenar sin progress_callback que causa bloqueos
        model.learn(
            total_timesteps=ppo_cfg.get('timesteps', 87600),
            log_interval=100,  # Log más frecuente
            progress_bar=True,  # Progress bar simple
            callback=None  # SIN callbacks complejos que bloquean
        )
        print("\n✅ ENTRENAMIENTO COMPLETADO")
        
    except KeyboardInterrupt:
        print("\n⚠️ Entrenamiento interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
