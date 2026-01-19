#!/usr/bin/env python3
"""
TIER 2 Serial Training - 2 Episodes Each Agent (FIXED)
A2C (2ep) → PPO (2ep) → SAC (2ep)

Properly calls simulate() with correct parameters (no agent_config)
Includes CityLearn EV charger bug patches
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup
sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Apply CityLearn patches FIRST
logger.info("Applying CityLearn patches...")
try:
    from apply_citylearn_patches import patch_citylearn
    patch_citylearn()
except Exception as e:
    logger.warning(f"Could not apply patches: {e}")

from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

print("\n" + "=" * 80)
print("TIER 2 SERIAL TRAINING - 2 EPISODES EACH AGENT (FIXED)")
print("=" * 80)
print(f"Start: {datetime.now().isoformat()}\n")

# Load config and paths
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

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_2ep_serial"
training_dir.mkdir(parents=True, exist_ok=True)

results = {}

# ============ A2C TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[1/3] A2C TIER 2 - 2 EPISODES")
print("=" * 80)
print("Config: LR=2.5e-4, n_steps=1024, ent=0.02, hidden=(512,512), activation=relu\n")

try:
    # 2 episodes = 2 * 8760 steps (approximately)
    # But simulate() uses timesteps for PPO/A2C
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="A2C",
        out_dir=training_dir / "a2c",
        training_dir=training_dir / "a2c" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # A2C-specific parameters (TIER 2 values)
        a2c_timesteps=2 * 8760,        # ~2 episodes
        a2c_n_steps=1024,              # ↑ TIER 2 (was 256)
        a2c_learning_rate=2.5e-4,      # ↓ TIER 2 (was 3e-4)
        a2c_entropy_coef=0.02,         # ↑ TIER 2 (was 0.01)
        a2c_checkpoint_freq_steps=1000,
        a2c_log_interval=500,
        a2c_device="cuda",
        a2c_resume_checkpoints=False,
        use_multi_objective=True,
        multi_objective_priority="balanced",
    )
    results["A2C"] = result_a2c
    logger.info(f"✅ A2C Complete")
    logger.info(f"   CO2: {result_a2c.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_a2c.reward:.3f}")
    logger.info(f"   Episodes: 2 (8760 timesteps)\n")
    
except Exception as e:
    logger.error(f"❌ A2C Error: {type(e).__name__}: {e}\n")
    results["A2C"] = None

# ============ PPO TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[2/3] PPO TIER 2 - 2 EPISODES")
print("=" * 80)
print("Config: LR=2.5e-4, batch=256, n_epochs=15, ent=0.02, hidden=(512,512), activation=relu, use_sde=True\n")

try:
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=training_dir / "ppo",
        training_dir=training_dir / "ppo" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # PPO-specific parameters (TIER 2 values)
        ppo_timesteps=2 * 8760,        # ~2 episodes
        ppo_batch_size=256,            # ↑ TIER 2 (was 128)
        ppo_n_steps=2048,              # Adjusted for batch size
        ppo_checkpoint_freq_steps=1000,
        ppo_target_kl=0.01,
        ppo_kl_adaptive=True,
        ppo_log_interval=500,
        ppo_device="cuda",
        ppo_resume_checkpoints=False,
        use_multi_objective=True,
        multi_objective_priority="balanced",
    )
    results["PPO"] = result_ppo
    logger.info(f"✅ PPO Complete")
    logger.info(f"   CO2: {result_ppo.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_ppo.reward:.3f}")
    logger.info(f"   Episodes: 2 (8760 timesteps)\n")
    
except Exception as e:
    logger.error(f"❌ PPO Error: {type(e).__name__}: {e}\n")
    results["PPO"] = None

# ============ SAC TIER 2 - 2 EPISODES ============
print("\n" + "=" * 80)
print("[3/3] SAC TIER 2 - 2 EPISODES")
print("=" * 80)
print("Config: LR=2.5e-4, batch=256, ent=0.02, hidden=(512,512), update_freq=2, dropout=0.1\n")

try:
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=training_dir / "sac",
        training_dir=training_dir / "sac" / "checkpoints",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        # SAC-specific parameters (TIER 2 values)
        sac_episodes=2,                # 2 episodes
        sac_batch_size=256,            # ↓ TIER 2 (was 512)
        sac_checkpoint_freq_steps=1000,
        sac_log_interval=500,
        sac_device="cuda",
        sac_resume_checkpoints=False,
        sac_use_amp=True,
        use_multi_objective=True,
        multi_objective_priority="balanced",
    )
    results["SAC"] = result_sac
    logger.info(f"✅ SAC Complete")
    logger.info(f"   CO2: {result_sac.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_sac.reward:.3f}")
    logger.info(f"   Episodes: 2\n")
    
except Exception as e:
    logger.error(f"❌ SAC Error: {type(e).__name__}: {e}\n")
    results["SAC"] = None

# ============ SUMMARY ============
print("\n" + "=" * 80)
print("TRAINING SUMMARY (TIER 2 - 2 EPISODES SERIAL)")
print("=" * 80)

for agent, result in results.items():
    if result:
        print(f"✅ {agent}: CO2={result.carbon_kg:.2f}kg, Reward={result.reward:.3f}")
    else:
        print(f"❌ {agent}: FAILED")

print("=" * 80)
print(f"End: {datetime.now().isoformat()}\n")

sys.exit(0 if all(results.values()) else 1)
