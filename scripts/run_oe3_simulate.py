from __future__ import annotations

import argparse
from pathlib import Path
import json

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate, SimulationResult
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--skip-uncontrolled", action="store_true", help="Reutiliza baseline existente y omite escenarios 'Uncontrolled'")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)
    summary_existing = None
    if args.skip_uncontrolled:
        summary_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"
        if summary_path.exists():
            try:
                summary_existing = json.loads(summary_path.read_text(encoding="utf-8"))
                print(f"[SKIP] Reutilizando baseline desde {summary_path}")
            except Exception as exc:
                print(f"[SKIP] No se pudo leer summary existente ({exc}), se recalculará baseline.")
                summary_existing = None

    built = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )

    dataset_dir = built.dataset_dir
    schema_grid = dataset_dir / "schema_grid_only.json"
    schema_pv = dataset_dir / "schema_pv_bess.json"

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuración de agentes
    eval_cfg = cfg["oe3"]["evaluation"]
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})
    a2c_cfg = eval_cfg.get("a2c", {})
    
    sac_episodes = int(sac_cfg.get("episodes", 5))
    sac_device = sac_cfg.get("device")
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 0))
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))
    
    ppo_episodes = ppo_cfg.get("episodes")
    if ppo_episodes is not None:
        ppo_timesteps = int(ppo_episodes) * 8760
    else:
        ppo_timesteps = int(ppo_cfg.get("timesteps", 100000))
    ppo_device = ppo_cfg.get("device")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 0))
    ppo_target_kl = ppo_cfg.get("target_kl")
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))

    a2c_episodes = a2c_cfg.get("episodes")
    if a2c_episodes is not None:
        a2c_timesteps = int(a2c_episodes) * 8760
    else:
        a2c_timesteps = int(a2c_cfg.get("timesteps", 0))
    a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 0))
    a2c_n_steps = int(a2c_cfg.get("n_steps", 256))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
    a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
    a2c_device = a2c_cfg.get("device")

    det_eval = bool(sac_cfg.get("deterministic_eval", True))

    # Scenario A: Electrified transport + grid only
    if summary_existing and "grid_only_result" in summary_existing:
        res_grid = SimulationResult(**summary_existing["grid_only_result"])
    else:
        res_grid = simulate(
            schema_path=schema_grid,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            seed=project_seed,
        )

    # Scenario B: Electrified transport + PV+BESS + control (evaluate candidate agents)
    agent_names = list(eval_cfg["agents"])
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
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=det_eval,
            sac_device=sac_device,
            ppo_device=ppo_device,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            seed=project_seed,
        )
        results[agent] = res.__dict__

    # Scenario C: Electrified transport + PV+BESS + no control (baseline)
    if summary_existing and "pv_bess_uncontrolled" in summary_existing:
        res_uncontrolled = SimulationResult(**summary_existing["pv_bess_uncontrolled"])
    else:
        res_uncontrolled = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            seed=project_seed,
        )

    # Pick best (lowest annualized carbon, then highest autosuficiencia)
    def annualized_carbon(r: dict) -> float:
        return r["carbon_kg"] / max(r["simulated_years"], 1e-9)

    def autosuficiencia(r: dict) -> float:
        ev_kwh_y = r["ev_charging_kwh"] / max(r["simulated_years"], 1e-9)
        build_kwh_y = r["building_load_kwh"] / max(r["simulated_years"], 1e-9)
        import_kwh_y = r["grid_import_kwh"] / max(r["simulated_years"], 1e-9)
        return 1.0 - import_kwh_y / max(ev_kwh_y + build_kwh_y, 1e-9)

    best_agent = min(
        results.keys(),
        key=lambda k: (annualized_carbon(results[k]), -autosuficiencia(results[k])),
    )
    summary = {
        "schema_grid_only": str(schema_grid.resolve()),
        "schema_pv_bess": str(schema_pv.resolve()),
        "grid_only_result": res_grid.__dict__,
        "pv_bess_results": results,
        "pv_bess_uncontrolled": res_uncontrolled.__dict__,
        "best_agent": best_agent,
        "best_result": results[best_agent],
        "best_agent_criteria": "min_annual_co2_then_max_autosuficiencia",
    }

    (out_dir / "simulation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
