#!/usr/bin/env python3
"""
TIER 2 Serial Training - GPU Optimized
Usa datos reales de OE2 y GPU al máximo
A2C (2ep) -> PPO (2ep) -> SAC (2ep)
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

print("\n" + "=" * 80)
print("TIER 2 SERIAL TRAINING - GPU OPTIMIZED (REAL DATA)")
print("=" * 80)
print(f"Start: {datetime.now().isoformat()}\n")

# Load config
logger.info("Loading configuration...")
cfg, rp = load_all("configs/default.yaml")

dataset_name = cfg["oe3"]["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

if not processed_dataset_dir.exists():
    logger.error(f"Dataset not found: {processed_dataset_dir}")
    sys.exit(1)

schema_pv = processed_dataset_dir / "schema_pv_bess.json"
carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_2ep_gpu_real"
training_dir.mkdir(parents=True, exist_ok=True)

results = {}

# ============ A2C TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[1/3] A2C TIER 2 - 2 EPISODES (GPU OPTIMIZED)")
print("=" * 80 + "\n")

try:
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="A2C",
        out_dir=training_dir / "a2c",
        training_dir=training_dir / "a2c" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # A2C TIER 2 config (optimized for GPU)
        a2c_timesteps=int(2 * 8760),        # 2 episodes (full year each)
        a2c_n_steps=1024,                   # TIER 2: batch collection
        a2c_learning_rate=2.5e-4,           # TIER 2: reduced LR
        a2c_entropy_coef=0.02,              # TIER 2: 2x entropy
        a2c_checkpoint_freq_steps=500,      # More frequent checkpoints
        a2c_log_interval=100,
        a2c_device="cuda",                  # GPU mode
        a2c_resume_checkpoints=False,
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=2022,
    )
    results["A2C"] = result_a2c
    logger.info(f"[OK] A2C Complete - CO2: {result_a2c.carbon_kg:.2f}kg, Reward: {result_a2c.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] A2C: {type(e).__name__}: {str(e)[:80]}")
    results["A2C"] = None

# ============ PPO TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[2/3] PPO TIER 2 - 2 EPISODES (GPU OPTIMIZED)")
print("=" * 80 + "\n")

try:
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=training_dir / "ppo",
        training_dir=training_dir / "ppo" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # PPO TIER 2 config (optimized for GPU)
        ppo_timesteps=int(2 * 8760),       # 2 episodes
        ppo_batch_size=256,                # TIER 2: larger batch
        ppo_n_steps=2048,                  # TIER 2: more steps per update
        ppo_checkpoint_freq_steps=500,
        ppo_log_interval=100,
        ppo_target_kl=0.01,
        ppo_kl_adaptive=True,
        ppo_device="cuda",                 # GPU mode
        ppo_resume_checkpoints=False,
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=2022,
    )
    results["PPO"] = result_ppo
    logger.info(f"[OK] PPO Complete - CO2: {result_ppo.carbon_kg:.2f}kg, Reward: {result_ppo.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] PPO: {type(e).__name__}: {str(e)[:80]}")
    results["PPO"] = None

# ============ SAC TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[3/3] SAC TIER 2 - 2 EPISODES (GPU OPTIMIZED)")
print("=" * 80 + "\n")

try:
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=training_dir / "sac",
        training_dir=training_dir / "sac" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # SAC TIER 2 config (optimized for GPU)
        sac_episodes=2,                    # 2 episodes
        sac_batch_size=256,                # TIER 2: reduced batch (from 512)
        sac_checkpoint_freq_steps=500,
        sac_log_interval=100,
        sac_device="cuda",                 # GPU mode
        sac_resume_checkpoints=False,
        sac_use_amp=True,                  # Mixed precision for GPU
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=2022,
    )
    results["SAC"] = result_sac
    logger.info(f"[OK] SAC Complete - CO2: {result_sac.carbon_kg:.2f}kg, Reward: {result_sac.reward:.3f}")
    
except Exception as e:
    logger.error(f"[FAIL] SAC: {type(e).__name__}: {str(e)[:80]}")
    results["SAC"] = None

# ============ SUMMARY ============
print("\n" + "=" * 80)
print("TRAINING SUMMARY (TIER 2 - GPU OPTIMIZED - REAL DATA)")
print("=" * 80)

summary_data = []
for agent in ["A2C", "PPO", "SAC"]:
    result = results.get(agent)
    if result:
        summary_data.append({
            "agent": agent,
            "status": "OK",
            "co2_kg": f"{result.carbon_kg:.2f}",
            "reward": f"{result.reward:.3f}",
        })
        print(f"[OK] {agent:4} | CO2: {result.carbon_kg:8.2f} kg | Reward: {result.reward:7.3f}")
    else:
        summary_data.append({"agent": agent, "status": "FAIL"})
        print(f"[FAIL] {agent}")

print("=" * 80)
print(f"End: {datetime.now().isoformat()}\n")

# Exit status
success_count = sum(1 for r in results.values() if r is not None)
sys.exit(0 if success_count == 3 else 1)
