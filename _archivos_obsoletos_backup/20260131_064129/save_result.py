#!/usr/bin/env python
from __future__ import annotations
import json
from pathlib import Path
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate, SimulationResult
from scripts._common import load_all

cfg, rp = load_all("configs/default.yaml")
built = build_citylearn_dataset(cfg, rp.raw_dir, rp.interim_dir, rp.processed_dir)

out_dir = rp.outputs_dir / "oe3" / "simulations"
out_dir.mkdir(parents=True, exist_ok=True)

print("[1] Cargando modelo PPO entrenado...")
res = simulate(
    schema_path=built.dataset_dir / "schema_pv_bess.json",
    agent_name="PPO",
    out_dir=out_dir,
    training_dir=rp.analyses_dir / "oe3" / "training",
    carbon_intensity_kg_per_kwh=0.4521,
    seconds_per_time_step=3600,
    ppo_timesteps=0,
    deterministic_eval=True,
    ppo_resume_checkpoints=True,
    seed=42,
    multi_objective_priority="balanced",
)

print("[2] Guardando result_PPO.json...")
result_file = out_dir / "result_PPO.json"
result_file.write_text(json.dumps(res.__dict__, indent=2), encoding="utf-8")

print(f"[OK] {result_file}")
print(f"[OK] Tamaño: {result_file.stat().st_size} bytes")
