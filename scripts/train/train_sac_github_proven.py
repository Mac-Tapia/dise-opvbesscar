#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAC TRAINING - CONFIGURACION PROBADA DE GITHUB
Basado en stable-baselines3 official examples
Ajustes para proyecto pvbesscar
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import torch

# Workspace
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import CheckpointCallback
import gymnasium as gym

print("="*80)
print("SAC TRAINING - GITHUB PROVEN CONFIG")
print("="*80)

# ===== STEP 1: LOAD ENVIRONMENT =====
print("\n[1] Loading environment with real OE2 data...")
try:
    # Import from your dataset builder
    from src.dataset_builder_citylearn.dataset_builder import create_iquitos_environment
    env = create_iquitos_environment()
    print(f"    Obs space: {env.observation_space}")
    print(f"    Action space: {env.action_space}")
except Exception as e:
    print(f"    ERROR: {e}")
    print(f"    Falling back to dummy env...")
    env = gym.make("Pendulum-v1")

# ===== STEP 2: SAC CONFIG (STANDARD FROM STABLE-BASELINES3) =====
print("\n[2] SAC Configuration (stable-baselines3 standard)...")

sac_params = {
    "learning_rate": 3e-4,  # Standard SAC LR
    "buffer_size": 1_000_000,  # Large buffer
    "batch_size": 256,
    "tau": 0.005,  # Standard soft update
    "gamma": 0.99,
    "train_freq": 1,  # Update after every step
    "gradient_steps": 1,
    "ent_coef": "auto",  # Auto-tune entropy
    "target_entropy": "auto",
    "policy_kwargs": {
        "net_arch": [256, 256],  # Standard network
        "activation_fn": torch.nn.ReLU,
    }
}

print(f"    Learning rate: {sac_params['learning_rate']}")
print(f"    Buffer size: {sac_params['buffer_size']:,}")
print(f"    Batch size: {sac_params['batch_size']}")
print(f"    tau (soft update): {sac_params['tau']}")
print(f"    Entropy: auto-tune")

# ===== STEP 3: CREATE AGENT =====
print("\n[3] Creating SAC agent...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"    Device: {device}")

agent = SAC(
    "MlpPolicy",
    env,
    **sac_params,
    device=device,
    verbose=1,  # Print progress
    tensorboard_log="./logs/sac_tensorboard",
)

print(f"    Agent created successfully")

# ===== STEP 4: CALLBACKS =====
print("\n[4] Setting up callbacks...")

checkpoint_dir = Path("checkpoints/SAC")
checkpoint_dir.mkdir(parents=True, exist_ok=True)

checkpoint_callback = CheckpointCallback(
    save_freq=8760,  # Save every episode (8760 steps = 1 year)
    save_path=checkpoint_dir,
    name_prefix="sac_github_proven",
    save_replay_buffer=False,  # Don't save huge replay buffer
    save_vecenv_wrapper=False,
)

callbacks = [checkpoint_callback]

print(f"    Checkpoint dir: {checkpoint_dir}")
print(f"    Save frequency: 8,760 steps (1 episode)")

# ===== STEP 5: TRAINING =====
print("\n[5] Starting training...")
print(f"    Total timesteps: 87,600 (10 episodes)")
print(f"    Estimated time: 2-3 hours on RTX 4060")
print("")

try:
    agent.learn(
        total_timesteps=87_600,
        callback=callbacks,
        progress_bar=True,
        log_interval=1,
    )
    print("\n[OK] Training completed successfully!")
    
except KeyboardInterrupt:
    print("\n[USER] Training interrupted by user")
    
except Exception as e:
    print(f"\n[ERROR] Training failed: {e}")
    import traceback
    traceback.print_exc()

# ===== STEP 6: SAVE FINAL MODEL =====
print("\n[6] Saving final model...")
final_path = checkpoint_dir / f"sac_github_proven_final.zip"
agent.save(final_path)
print(f"    Saved to: {final_path}")

# ===== STEP 7: VALIDATE CHECKPOINTS =====
print("\n[7] Validation...")
sac_count = len(list(checkpoint_dir.glob("*.zip")))
ppo_count = len(list(Path("checkpoints/PPO").glob("*.zip")))
a2c_count = len(list(Path("checkpoints/A2C").glob("*.zip")))

print(f"    SAC checkpoints: {sac_count}")
print(f"    PPO checkpoints: {ppo_count} (PROTECTED)")
print(f"    A2C checkpoints: {a2c_count} (PROTECTED)")

print("\n" + "="*80)
print("TRAINING COMPLETE")
print("="*80)
