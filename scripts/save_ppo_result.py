from __future__ import annotations

import json
from pathlib import Path
from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

def main() -> None:
    setup_logging()
    cfg, rp = load_all("configs/default.yaml")
    oe3_cfg = cfg["oe3"]

    built = build_citylearn_dataset(cfg=cfg, _raw_dir=rp.raw_dir, interim_dir=rp.interim_dir, processed_dir=rp.processed_dir)
    dataset_dir = built.dataset_dir

    schema_pv = dataset_dir / "schema_pv_bess.json"
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    res = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        ppo_timesteps=0,
        deterministic_eval=True,
        ppo_device="cpu",
        ppo_resume_checkpoints=True,
        seed=int(cfg["project"].get("seed", 42)),
        multi_objective_priority="balanced",
    )

    ppo_result_path = out_dir / "result_PPO.json"
    ppo_result_path.write_text(json.dumps(res.__dict__, indent=2), encoding="utf-8")

    print(f"✓ result_PPO.json guardado: {ppo_result_path}")
    print(f"✓ Tamaño: {ppo_result_path.stat().st_size} bytes")

if __name__ == "__main__":
    main()
