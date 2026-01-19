#!/usr/bin/env python3
"""
TIER 2 V2 SERIAL TRAINING - GPU OPTIMIZADO CON MEJORAS
A2C (2ep) -> PPO (2ep) -> SAC (2ep)

Cambios V2:
- Recompensas normalizadas [-1, 1] con énfasis pico
- Entropy coef FIJO en 0.01
- LR reducido a 1.5e-4 en pico (estabilidad crítica)
- Observables enriquecidos: flags, SOC dinámico, FV, colas
- Penalizaciones explícitas: potencia pico, SOC, fairness
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Optimización GPU
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'

sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Apply CityLearn patches FIRST
from citylearn_monkeypatch import apply_citylearn_patches
apply_citylearn_patches()

from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all
from src.iquitos_citylearn.oe3.tier2_v2_config import TIER2V2Config

print("\n" + "=" * 80)
print("TIER 2 V2 SERIAL TRAINING - GPU OPTIMIZADO CON MEJORAS")
print("=" * 80)
print(f"Start: {datetime.now().isoformat()}\n")

# Load config
logger.info("Loading configuration...")
cfg, rp = load_all("configs/default.yaml")

# Crear config V2
config_v2 = TIER2V2Config()
logger.info(f"TIER 2 V2 Config loaded:")
logger.info(f"  - Entropy coef (FIJO): {config_v2.entropy_coef_fixed}")
logger.info(f"  - LR base: {config_v2.learning_rate_base:.2e}")
logger.info(f"  - LR pico: {config_v2.learning_rate_peak:.2e}")
logger.info(f"  - CO2 weight: {config_v2.co2_weight}")
logger.info(f"  - Peak power penalty: {config_v2.peak_power_penalty}")
logger.info(f"  - SOC reserve penalty: {config_v2.soc_reserve_penalty}")

dataset_name = cfg["oe3"]["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

if not processed_dataset_dir.exists():
    logger.error(f"Dataset not found: {processed_dataset_dir}")
    sys.exit(1)

schema_pv = processed_dataset_dir / "schema_pv_bess.json"
carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_v2_2ep_gpu"
training_dir.mkdir(parents=True, exist_ok=True)

results = {}

# ============ A2C TIER 2 V2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[1/3] A2C TIER 2 V2 - 2 EPISODES (GPU + MEJORAS)")
print("=" * 80)
print(f"Config: entropy=0.01 (fijo), lr_base={config_v2.learning_rate_base:.2e}, lr_pico={config_v2.learning_rate_peak:.2e}\n")

try:
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="A2C",
        out_dir=training_dir / "a2c",
        training_dir=training_dir / "a2c" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # A2C TIER 2 V2 config
        a2c_timesteps=int(2 * 8760),        # 2 episodes
        a2c_n_steps=1024,                   # TIER 2: batch
        a2c_learning_rate=config_v2.learning_rate_base,  # 2.5e-4
        a2c_entropy_coef=config_v2.entropy_coef_fixed,  # 0.01 FIJO
        a2c_checkpoint_freq_steps=500,
        a2c_log_interval=100,
        a2c_device="cuda",
        a2c_resume_checkpoints=False,
        use_multi_objective=True,
        multi_objective_priority="tier2_v2",  # Nuevo: usa V2
        seed=2022,
    )
    results["A2C"] = result_a2c
    logger.info(f"[OK] A2C Complete - CO2: {result_a2c.carbon_kg:.2f}kg, Reward: {result_a2c.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] A2C: {type(e).__name__}: {str(e)[:120]}")
    results["A2C"] = None
    import traceback
    traceback.print_exc()

# ============ PPO TIER 2 V2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[2/3] PPO TIER 2 V2 - 2 EPISODES (GPU + MEJORAS)")
print("=" * 80)
print(f"Config: entropy=0.01 (fijo), lr_base={config_v2.learning_rate_base:.2e}, lr_pico={config_v2.learning_rate_peak:.2e}\n")

try:
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=training_dir / "ppo",
        training_dir=training_dir / "ppo" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # PPO TIER 2 V2 config
        ppo_timesteps=int(2 * 8760),       # 2 episodes
        ppo_batch_size=256,                # TIER 2
        ppo_n_steps=2048,                  # TIER 2
        ppo_n_epochs=15,                   # TIER 2
        ppo_learning_rate=config_v2.learning_rate_base,  # 2.5e-4
        ppo_ent_coef=config_v2.entropy_coef_fixed,  # 0.01 FIJO
        ppo_checkpoint_freq_steps=500,
        ppo_log_interval=100,
        ppo_target_kl=0.01,
        ppo_kl_adaptive=True,
        ppo_device="cuda",
        ppo_resume_checkpoints=False,
        ppo_use_sde=True,  # TIER 2: Stochastic Delta Exploration
        use_multi_objective=True,
        multi_objective_priority="tier2_v2",  # Nuevo: usa V2
        seed=2022,
    )
    results["PPO"] = result_ppo
    logger.info(f"[OK] PPO Complete - CO2: {result_ppo.carbon_kg:.2f}kg, Reward: {result_ppo.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] PPO: {type(e).__name__}: {str(e)[:120]}")
    results["PPO"] = None
    import traceback
    traceback.print_exc()

# ============ SAC TIER 2 V2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[3/3] SAC TIER 2 V2 - 2 EPISODES (GPU + MEJORAS)")
print("=" * 80)
print(f"Config: entropy=0.01 (fijo), lr_base={config_v2.learning_rate_base:.2e}, lr_pico={config_v2.learning_rate_peak:.2e}\n")

try:
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=training_dir / "sac",
        training_dir=training_dir / "sac" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # SAC TIER 2 V2 config
        sac_episodes=2,                    # 2 episodes
        sac_batch_size=256,                # TIER 2
        sac_learning_rate=config_v2.learning_rate_base,  # 2.5e-4
        sac_checkpoint_freq_steps=500,
        sac_log_interval=100,
        sac_device="cuda",
        sac_resume_checkpoints=False,
        sac_use_amp=True,
        use_multi_objective=True,
        multi_objective_priority="tier2_v2",  # Nuevo: usa V2
        seed=2022,
    )
    results["SAC"] = result_sac
    logger.info(f"[OK] SAC Complete - CO2: {result_sac.carbon_kg:.2f}kg, Reward: {result_sac.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] SAC: {type(e).__name__}: {str(e)[:120]}")
    results["SAC"] = None
    import traceback
    traceback.print_exc()

# ============ SUMMARY ============
print("\n" + "=" * 80)
print("TRAINING SUMMARY (TIER 2 V2 - GPU + MEJORAS)")
print("=" * 80)

for agent in ["A2C", "PPO", "SAC"]:
    result = results.get(agent)
    if result:
        print(f"[OK] {agent:4} | CO2: {result.carbon_kg:8.2f} kg | Reward: {result.reward:7.3f}")
    else:
        print(f"[FAIL] {agent}")

print("=" * 80)
print(f"End: {datetime.now().isoformat()}\n")

# Summary statistics
success_count = sum(1 for r in results.values() if r is not None)

# Save summary
summary_path = training_dir / "TIER2_V2_SUMMARY.txt"
with open(summary_path, "w") as f:
    f.write("TIER 2 V2 TRAINING SUMMARY\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Start: {datetime.now().isoformat()}\n")
    f.write(f"Training Dir: {training_dir}\n\n")
    f.write("Configuration:\n")
    f.write(f"  - Entropy coef (FIJO): {config_v2.entropy_coef_fixed}\n")
    f.write(f"  - LR base: {config_v2.learning_rate_base:.2e}\n")
    f.write(f"  - LR pico: {config_v2.learning_rate_peak:.2e}\n")
    f.write(f"  - CO2 weight: {config_v2.co2_weight}\n")
    f.write(f"  - Peak power penalty: {config_v2.peak_power_penalty}\n\n")
    f.write("Results:\n")
    for agent in ["A2C", "PPO", "SAC"]:
        result = results.get(agent)
        if result:
            f.write(f"  {agent}: CO2={result.carbon_kg:.2f}kg, Reward={result.reward:.3f}\n")
        else:
            f.write(f"  {agent}: FAILED\n")
    f.write(f"\nSuccess: {success_count}/3 agents\n")

logger.info(f"Summary saved to {summary_path}")

# Exit status
sys.exit(0 if success_count == 3 else 1)
