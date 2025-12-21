from __future__ import annotations

import argparse
from pathlib import Path
import json

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    built = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )

    dataset_dir = built.dataset_dir
    schema_grid = dataset_dir / "schema_grid_only.json"
    schema_pv = dataset_dir / "schema_pv_bess.json"

    out_dir = rp.interim_dir / "oe3" / "simulations"
    out_dir.mkdir(parents=True, exist_ok=True)

    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    sac_cfg = cfg["oe3"]["evaluation"].get("sac", {})
    sac_episodes = int(sac_cfg.get("episodes", 5))
    det_eval = bool(sac_cfg.get("deterministic_eval", True))

    # Scenario A: Electrified transport + grid only
    res_grid = simulate(
        schema_path=schema_grid,
        agent_name="Uncontrolled",
        out_dir=out_dir,
        carbon_intensity_kg_per_kwh=ci,
        seconds_per_time_step=seconds_per_time_step,
        sac_episodes=sac_episodes,
        deterministic_eval=True,
    )

    # Scenario B: Electrified transport + PV+BESS + control (evaluate candidate agents)
    agent_names = list(cfg["oe3"]["evaluation"]["agents"])
    results = {}
    for agent in agent_names:
        if agent.lower() == "uncontrolled":
            # Uncontrolled with PV+BESS is not the reporting scenario requested,
            # but we keep it for diagnostics.
            pass
        res = simulate(
            schema_path=schema_pv,
            agent_name=agent,
            out_dir=out_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            deterministic_eval=det_eval,
        )
        results[agent] = res.__dict__

    # Pick best (lowest annualized carbon)
    def annualized_carbon(r: dict) -> float:
        return r["carbon_kg"] / max(r["simulated_years"], 1e-9)

    best_agent = min(results.keys(), key=lambda k: annualized_carbon(results[k]))
    summary = {
        "schema_grid_only": str(schema_grid.resolve()),
        "schema_pv_bess": str(schema_pv.resolve()),
        "grid_only_result": res_grid.__dict__,
        "pv_bess_results": results,
        "best_agent": best_agent,
        "best_result": results[best_agent],
    }

    (out_dir / "simulation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
