#!/usr/bin/env python3
"""
TIER 2 Serial Training - 2 Episodes Each Agent
A2C (2ep) → PPO (2ep) → SAC (2ep)

Uses: simulate() from iquitos_citylearn.oe3.simulate
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup
sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

setup_logging()

print("\n" + "=" * 70)
print("TIER 2 SERIAL TRAINING - 2 EPISODES EACH AGENT")
print("=" * 70)
print(f"Start: {datetime.now().isoformat()}\n")

# Load config
logger.info("Loading configuration...")
cfg, rp = load_all("configs/default.yaml")
oe3_cfg = cfg["oe3"]

# Build dataset
logger.info("Building dataset...")
dataset_name = oe3_cfg["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

if processed_dataset_dir.exists():
    logger.info(f"Dataset exists: {processed_dataset_dir}")
    dataset_dir = processed_dataset_dir
else:
    logger.info("Building dataset...")
    built = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir
    logger.info(f"Dataset built: {dataset_dir}")

schema_pv = dataset_dir / "schema_pv_bess.json"

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_test"
training_dir.mkdir(parents=True, exist_ok=True)

# ============ A2C TIER 2 ============
print("\n" + "=" * 70)
print("A2C TIER 2 - 2 EPISODES")
print("=" * 70 + "\n")

try:
    a2c_cfg = oe3_cfg["evaluation"].get("a2c", {})
    # Override TIER 2 config
    a2c_cfg.update({
        "episodes": 2,                              # 2 episodes
        "learning_rate": 2.5e-4,                    # ↓ TIER 2
        "n_steps": 1024,                            # ↑ TIER 2
        "ent_coef": 0.02,                           # ↑ TIER 2
        "hidden_sizes": (512, 512),                 # ↑ TIER 2
        "activation": "relu",                       # ↑ TIER 2
        "lr_schedule": "linear",                    # ↑ TIER 2
        "device": "cuda",
        "checkpoint_freq_steps": 1000,
    })
    
    logger.info(f"A2C Config: LR={a2c_cfg['learning_rate']}, ent={a2c_cfg['ent_coef']}, hidden={a2c_cfg['hidden_sizes']}")
    
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="A2C",
        out_dir=training_dir,
        training_dir=training_dir / "a2c",
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        use_multi_objective=True,
        agent_config=a2c_cfg,
    )
    logger.info(f"✅ A2C Complete")
    logger.info(f"   CO2: {result_a2c.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_a2c.reward:.3f}")
    
except Exception as e:
    logger.error(f"❌ A2C Error: {e}", exc_info=True)

# ============ PPO TIER 2 ============
print("\n" + "=" * 70)
print("PPO TIER 2 - 2 EPISODES")
print("=" * 70 + "\n")

try:
    ppo_cfg = oe3_cfg["evaluation"].get("ppo", {})
    # Override TIER 2 config
    ppo_cfg.update({
        "episodes": 2,                              # 2 episodes
        "learning_rate": 2.5e-4,                    # ↓ TIER 2
        "batch_size": 256,                          # ↑ TIER 2
        "n_epochs": 15,                             # ↑ TIER 2
        "ent_coef": 0.02,                           # ↑ TIER 2
        "hidden_sizes": (512, 512),                 # ↑ TIER 2
        "activation": "relu",                       # ↑ TIER 2
        "lr_schedule": "linear",                    # ↑ TIER 2
        "use_sde": True,                            # NEW TIER 2
        "device": "cuda",
        "checkpoint_freq_steps": 1000,
    })
    
    logger.info(f"PPO Config: LR={ppo_cfg['learning_rate']}, batch={ppo_cfg['batch_size']}, ent={ppo_cfg['ent_coef']}, hidden={ppo_cfg['hidden_sizes']}")
    
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=training_dir,
        training_dir=training_dir / "ppo",
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        use_multi_objective=True,
        agent_config=ppo_cfg,
    )
    logger.info(f"✅ PPO Complete")
    logger.info(f"   CO2: {result_ppo.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_ppo.reward:.3f}")
    
except Exception as e:
    logger.error(f"❌ PPO Error: {e}", exc_info=True)

# ============ SAC TIER 2 ============
print("\n" + "=" * 70)
print("SAC TIER 2 - 2 EPISODES")
print("=" * 70 + "\n")

try:
    sac_cfg = oe3_cfg["evaluation"].get("sac", {})
    # Override TIER 2 config
    sac_cfg.update({
        "episodes": 2,                              # 2 episodes
        "learning_rate": 2.5e-4,                    # ↓ TIER 2
        "batch_size": 256,                          # ↓ TIER 2
        "buffer_size": 150000,                      # ↑ TIER 2
        "ent_coef": 0.02,                           # ↑ TIER 2
        "target_entropy": -40,                      # ↓ TIER 2
        "hidden_sizes": (512, 512),                 # ↑ TIER 2
        "activation": "relu",                       # TIER 2
        "update_per_timestep": 2,                   # NEW TIER 2
        "use_dropout": True,                        # NEW TIER 2
        "dropout_rate": 0.1,                        # NEW TIER 2
        "device": "cuda",
        "checkpoint_freq_steps": 1000,
    })
    
    logger.info(f"SAC Config: LR={sac_cfg['learning_rate']}, batch={sac_cfg['batch_size']}, ent={sac_cfg['ent_coef']}, hidden={sac_cfg['hidden_sizes']}")
    
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=training_dir,
        training_dir=training_dir / "sac",
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        use_multi_objective=True,
        agent_config=sac_cfg,
    )
    logger.info(f"✅ SAC Complete")
    logger.info(f"   CO2: {result_sac.carbon_kg:.2f} kg")
    logger.info(f"   Reward: {result_sac.reward:.3f}")
    
except Exception as e:
    logger.error(f"❌ SAC Error: {e}", exc_info=True)

print("\n" + "=" * 70)
print("TRAINING SUMMARY")
print("=" * 70)
print(f"End: {datetime.now().isoformat()}")
print("Training outputs saved to:", training_dir)
print("=" * 70 + "\n")
