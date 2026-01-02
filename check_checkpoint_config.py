#!/usr/bin/env python
"""Verificar qué parámetros se pasan a simulate()."""

from iquitos_citylearn.config import load_config, load_paths
from pathlib import Path

cfg = load_config(Path("configs/default.yaml"))
rp = load_paths(cfg)

eval_cfg = cfg["oe3"]["evaluation"]
sac_cfg = eval_cfg.get("sac", {})
ppo_cfg = eval_cfg.get("ppo", {})
a2c_cfg = eval_cfg.get("a2c", {})

sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 0))
ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 0))
a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 0))

training_dir = rp.analyses_dir / "oe3" / "training"

print("=" * 80)
print("PARÁMETROS DE CHECKPOINT")
print("=" * 80)

print(f"\ntraining_dir: {training_dir}")
print(f"training_dir exists: {training_dir.exists()}")

print(f"\nSAC checkpoint_freq_steps: {sac_checkpoint_freq}")
print(f"  Will create checkpoints: {training_dir is not None and sac_checkpoint_freq > 0}")
if training_dir is not None and sac_checkpoint_freq > 0:
    sac_checkpoint_dir = training_dir / "checkpoints" / "sac"
    print(f"  Checkpoint dir: {sac_checkpoint_dir}")

print(f"\nPPO checkpoint_freq_steps: {ppo_checkpoint_freq}")
print(f"  Will create checkpoints: {training_dir is not None and ppo_checkpoint_freq > 0}")
if training_dir is not None and ppo_checkpoint_freq > 0:
    ppo_checkpoint_dir = training_dir / "checkpoints" / "ppo"
    print(f"  Checkpoint dir: {ppo_checkpoint_dir}")

print(f"\nA2C checkpoint_freq_steps: {a2c_checkpoint_freq}")
print(f"  Will create checkpoints: {training_dir is not None and a2c_checkpoint_freq > 0}")
if training_dir is not None and a2c_checkpoint_freq > 0:
    a2c_checkpoint_dir = training_dir / "checkpoints" / "a2c"
    print(f"  Checkpoint dir: {a2c_checkpoint_dir}")

print("\n" + "=" * 80)
if sac_checkpoint_freq > 0 and ppo_checkpoint_freq > 0 and a2c_checkpoint_freq > 0:
    print("✓ Todos los agentes están configurados para guardar checkpoints")
else:
    print("✗ ADVERTENCIA: Algunos agentes no guardarán checkpoints")
print("=" * 80)
