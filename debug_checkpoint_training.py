#!/usr/bin/env python3
"""Run a single agent training and capture all logs to analyze checkpoint behavior."""
import logging
import sys
import io
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

# Configure logging to capture everything
log_capture = io.StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add to root logger
logging.root.addHandler(handler)
logging.root.setLevel(logging.DEBUG)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

cfg, rp = load_all(Path("configs/default.yaml"))

out_dir = rp.outputs_dir / "oe3" / "simulations"
training_dir = rp.analyses_dir / "oe3" / "training"
out_dir.mkdir(parents=True, exist_ok=True)

schema_pv = Path("data/processed/citylearn/iquitos_pv_bess_ev_scenario/schema_pv_bess.json")
ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])

eval_cfg = cfg["oe3"]["evaluation"]
sac_cfg = eval_cfg.get("sac", {})

print("=== Running SAC Training with Enhanced Logging ===\n")
print(f"Schema: {schema_pv.exists()}")
print(f"Training dir: {training_dir}\n")

try:
    result = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=ci,
        seconds_per_time_step=seconds_per_time_step,
        sac_episodes=1,
        sac_batch_size=int(sac_cfg.get("batch_size", 512)),
        sac_log_interval=int(sac_cfg.get("log_interval", 500)),
        sac_use_amp=bool(sac_cfg.get("use_amp", True)),
        sac_device=sac_cfg.get("device"),
        sac_checkpoint_freq_steps=int(sac_cfg.get("checkpoint_freq_steps", 0)),
        sac_resume_checkpoints=bool(sac_cfg.get("resume_checkpoints", False)),
        multi_objective_priority=str(eval_cfg.get("multi_objective_priority", "balanced")),
    )
    print("✓ Training completed")
except Exception as e:
    print(f"✗ Training failed: {e}")
    import traceback
    traceback.print_exc()

# Print captured logs
logs = log_capture.getvalue()
print("\n=== CAPTURED LOGS (filtered) ===\n")

checkpoint_lines = [line for line in logs.split("\n") if "checkpoint" in line.lower() or "CheckpointCallback" in line]
if checkpoint_lines:
    print("Checkpoint-related log entries:")
    for line in checkpoint_lines[-50:]:  # Last 50 checkpoint lines
        print(line)
else:
    print("✗ NO CHECKPOINT LOGS FOUND!")

# Check saved files
checkpoint_dir = training_dir / "checkpoints" / "sac"
if checkpoint_dir.exists():
    zips = list(checkpoint_dir.glob("*.zip"))
    print(f"\n✓ Checkpoints created: {len(zips)}")
    for z in zips[:10]:
        print(f"  - {z.name}")
else:
    print(f"\n✗ Checkpoint directory not created: {checkpoint_dir}")
