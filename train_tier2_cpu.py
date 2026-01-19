#!/usr/bin/env python3
"""
TIER 2 Serial Training - Minimal (No CityLearn Patches)
Uses CPU to avoid GPU/CityLearn interaction issues
A2C (2ep) -> PPO (2ep) -> SAC (2ep)
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Force UTF-8 and minimal output
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Apply CityLearn patches FIRST (before importing simulate)
from citylearn_monkeypatch import apply_citylearn_patches
apply_citylearn_patches()

from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

print("\n" + "=" * 80)
print("TIER 2 SERIAL TRAINING - MINIMAL")
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

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_2ep_minimal"
training_dir.mkdir(parents=True, exist_ok=True)

results = {}

# ============ A2C TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[1/3] A2C TIER 2 - 2 EPISODES (CPU MODE)")
print("=" * 80 + "\n")

try:
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="A2C",
        out_dir=training_dir / "a2c",
        training_dir=training_dir / "a2c" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        a2c_timesteps=2 * 8760,        
        a2c_n_steps=1024,              
        a2c_learning_rate=2.5e-4,      
        a2c_entropy_coef=0.02,         
        a2c_checkpoint_freq_steps=1000,
        a2c_log_interval=1000,
        a2c_device="cpu",  # Use CPU to avoid GPU issues
        a2c_resume_checkpoints=False,
        use_multi_objective=True,
    )
    results["A2C"] = result_a2c
    logger.info(f"[OK] A2C Complete - CO2: {result_a2c.carbon_kg:.2f}kg")
    
except Exception as e:
    logger.error(f"[FAIL] A2C: {type(e).__name__}\n")
    results["A2C"] = None

# ============ PPO TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[2/3] PPO TIER 2 - 2 EPISODES (CPU MODE)")
print("=" * 80 + "\n")

try:
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=training_dir / "ppo",
        training_dir=training_dir / "ppo" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        ppo_timesteps=2 * 8760,        
        ppo_batch_size=256,            
        ppo_n_steps=2048,              
        ppo_checkpoint_freq_steps=1000,
        ppo_log_interval=1000,
        ppo_device="cpu",  # Use CPU
        ppo_resume_checkpoints=False,
        use_multi_objective=True,
    )
    results["PPO"] = result_ppo
    logger.info(f"[OK] PPO Complete - CO2: {result_ppo.carbon_kg:.2f}kg")
    
except Exception as e:
    logger.error(f"[FAIL] PPO: {type(e).__name__}\n")
    results["PPO"] = None

# ============ SAC TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[3/3] SAC TIER 2 - 2 EPISODES (CPU MODE)")
print("=" * 80 + "\n")

try:
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=training_dir / "sac",
        training_dir=training_dir / "sac" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        sac_episodes=2,                
        sac_batch_size=256,            
        sac_checkpoint_freq_steps=1000,
        sac_log_interval=1000,
        sac_device="cpu",  # Use CPU
        sac_resume_checkpoints=False,
        use_multi_objective=True,
    )
    results["SAC"] = result_sac
    logger.info(f"[OK] SAC Complete - CO2: {result_sac.carbon_kg:.2f}kg")
    
except Exception as e:
    logger.error(f"[FAIL] SAC: {type(e).__name__}\n")
    results["SAC"] = None

# ============ SUMMARY ============
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
for agent, result in results.items():
    if result:
        print(f"[OK] {agent}: CO2={result.carbon_kg:.2f}kg")
    else:
        print(f"[FAIL] {agent}")
print("=" * 80 + "\n")

sys.exit(0 if all(results.values()) else 1)
