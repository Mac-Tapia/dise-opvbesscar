#!/usr/bin/env python3
"""Verify checkpoint_freq is being passed correctly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scripts._common import load_all
from iquitos_citylearn.oe3.agents.sac import SACConfig

cfg, rp = load_all(Path("configs/default.yaml"))

eval_cfg = cfg["oe3"]["evaluation"]
sac_cfg = eval_cfg.get("sac", {})

print("=== SAC Configuration ===")
print(f"checkpoint_freq_steps from YAML: {sac_cfg.get('checkpoint_freq_steps', 0)}")

# Create SACConfig to verify it's passed correctly
sac_config = SACConfig(
    episodes=sac_cfg.get("episodes", 5),
    device=sac_cfg.get("device", "auto"),
    batch_size=int(sac_cfg.get("batch_size", 512)),
    checkpoint_freq_steps=int(sac_cfg.get("checkpoint_freq_steps", 0)),
    checkpoint_dir="test_checkpoint",
)

print(f"SACConfig.checkpoint_freq_steps: {sac_config.checkpoint_freq_steps}")
print(f"SACConfig.checkpoint_dir: {sac_config.checkpoint_dir}")

if sac_config.checkpoint_freq_steps == 0:
    print("\n⚠️  WARNING: checkpoint_freq_steps is 0! No checkpoints will be saved.")
else:
    print(f"\n✓ Checkpoint frequency is set to {sac_config.checkpoint_freq_steps} steps")
