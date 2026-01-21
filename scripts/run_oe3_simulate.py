from __future__ import annotations

import argparse
from pathlib import Path
import json

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

def _tailpipe_kg(cfg: dict, ev_kwh: float, simulated_years: float) -> float:
    """Calcula CO2 tailpipe para motos/mototaxis a combustión equivalentes."""
    if ev_kwh <= 0 or simulated_years <= 0:
        return 0.0
    km_per_kwh = float(cfg["oe3"]["emissions"].get("km_per_kwh", 35.0))
    km_per_gallon = float(cfg["oe3"]["emissions"].get("km_per_gallon", 120.0))
    kgco2_per_gallon = float(cfg["oe3"]["emissions"].get("kgco2_per_gallon", 8.9))
    total_km = ev_kwh * km_per_kwh
    gallons = total_km / max(km_per_gallon, 1e-9)
    return gallons * kgco2_per_gallon / max(simulated_years, 1e-9)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--skip-dataset", action="store_true", help="Reutilizar dataset CityLearn ya construido")
    ap.add_argument("--skip-uncontrolled", action="store_true", help="Reutilizar baseline Uncontrolled si existe en simulation_summary.json")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)
    oe3_cfg = cfg["oe3"]

    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    if args.skip_dataset and processed_dataset_dir.exists():
        dataset_dir = processed_dataset_dir
    else:
        built = build_citylearn_dataset(
            cfg=cfg,
            raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        dataset_dir = built.dataset_dir

    schema_grid = dataset_dir / "schema_grid_only.json"
    schema_pv = dataset_dir / "schema_pv_bess.json"
    chargers_results_path = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    chargers_results = None
    if chargers_results_path.exists():
        chargers_results = json.loads(chargers_results_path.read_text(encoding="utf-8"))

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuración de agentes
    eval_cfg = cfg["oe3"]["evaluation"]
    resume_checkpoints_global = bool(eval_cfg.get("resume_checkpoints", False))
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})
    a2c_cfg = eval_cfg.get("a2c", {})
    
    sac_episodes = int(sac_cfg.get("episodes", 5))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_log_interval = int(sac_cfg.get("log_interval", 500))
    sac_use_amp = bool(sac_cfg.get("use_amp", True))
    sac_device = sac_cfg.get("device")
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))
    
    ppo_episodes = ppo_cfg.get("episodes")
    if ppo_episodes is not None:
        ppo_timesteps = int(ppo_episodes) * 8760
    else:
        ppo_timesteps = int(ppo_cfg.get("timesteps", 100000))
    ppo_device = ppo_cfg.get("device")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    ppo_target_kl = ppo_cfg.get("target_kl")
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))
    ppo_n_steps = int(ppo_cfg.get("n_steps", 1024))
    ppo_batch_size = int(ppo_cfg.get("batch_size", 128))
    ppo_use_amp = bool(ppo_cfg.get("use_amp", True))
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", resume_checkpoints_global))

    a2c_episodes = a2c_cfg.get("episodes")
    if a2c_episodes is not None:
        a2c_timesteps = int(a2c_episodes) * 8760
    else:
        a2c_timesteps = int(a2c_cfg.get("timesteps", 0))
    a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    a2c_n_steps = int(a2c_cfg.get("n_steps", 512))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
    a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
    a2c_device = a2c_cfg.get("device")
    a2c_resume = bool(a2c_cfg.get("resume_checkpoints", resume_checkpoints_global))
    sac_resume = bool(sac_cfg.get("resume_checkpoints", resume_checkpoints_global))
    a2c_log_interval = int(a2c_cfg.get("log_interval", 2000))

    det_eval = bool(sac_cfg.get("deterministic_eval", True))
    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))

    # Opcional: reutilizar baseline de un resumen previo
    summary_path = out_dir / "simulation_summary.json"
    res_uncontrolled = None
    if args.skip_uncontrolled and summary_path.exists():
        prev = json.loads(summary_path.read_text(encoding="utf-8"))
        if "pv_bess_uncontrolled" in prev:
            res_uncontrolled = prev["pv_bess_uncontrolled"]

    # Baseline: Electrified transport + PV+BESS + no control (Uncontrolled)
    # Este es el único baseline necesario - también se usa para calcular tailpipe
    if res_uncontrolled is None:
        res_uncontrolled_obj = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            sac_batch_size=sac_batch_size,
            sac_log_interval=sac_log_interval,
            sac_use_amp=sac_use_amp,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_n_steps=ppo_n_steps,
            ppo_batch_size=ppo_batch_size,
            ppo_use_amp=ppo_use_amp,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            a2c_log_interval=a2c_log_interval,
            sac_resume_checkpoints=sac_resume,
            ppo_resume_checkpoints=ppo_resume,
            a2c_resume_checkpoints=a2c_resume,
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )
        res_uncontrolled = res_uncontrolled_obj.__dict__

    # Scenario B: Electrified transport + PV+BESS + control (evaluate candidate agents)
    agent_names = list(eval_cfg["agents"])
    results = {}
    for agent in agent_names:
        # Skip Uncontrolled in this loop - it will be run in Scenario C as baseline
        if agent.lower() == "uncontrolled":
            continue
        
        # Skip if results already exist
        results_json = out_dir / f"{agent.lower()}_results.json"
        if results_json.exists():
            with open(results_json) as f:
                res = json.load(f)
            
            # Verificar si SAC o PPO ya completaron 2 episodios
            if agent.lower() in ["sac", "ppo"]:
                # Verificar si tiene al menos 2 episodios (simulated_years >= 2.0)
                if res.get("simulated_years", 0) >= 2.0:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"[SKIP] {agent.upper()} - Ya completó 2 episodios ({res.get('simulated_years')} años simulados)")
                    print(f"\n{'='*80}")
                    print(f"✓ {agent.upper()} ya completó {int(res.get('simulated_years', 0))} episodios - SALTANDO")
                    print(f"{'='*80}\n")
                    results[agent] = res
                    continue
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[SKIP] {agent} - resultados ya existen en {results_json}")
            results[agent] = res
            continue
        
        try:
            res = simulate(
                schema_path=schema_pv,
                agent_name=agent,
                out_dir=out_dir,
                training_dir=training_dir,
                carbon_intensity_kg_per_kwh=ci,
                seconds_per_time_step=seconds_per_time_step,
                sac_episodes=sac_episodes,
                sac_batch_size=sac_batch_size,
                sac_log_interval=sac_log_interval,
                sac_use_amp=sac_use_amp,
                ppo_timesteps=ppo_timesteps,
                deterministic_eval=det_eval,
                sac_device=sac_device,
                ppo_device=ppo_device,
                sac_prefer_citylearn=sac_prefer_citylearn,
                sac_checkpoint_freq_steps=sac_checkpoint_freq,
                ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
                ppo_n_steps=ppo_n_steps,
                ppo_batch_size=ppo_batch_size,
                ppo_use_amp=ppo_use_amp,
                ppo_target_kl=ppo_target_kl,
                ppo_kl_adaptive=ppo_kl_adaptive,
                ppo_log_interval=ppo_log_interval,
                a2c_timesteps=a2c_timesteps,
                a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
                a2c_n_steps=a2c_n_steps,
                a2c_learning_rate=a2c_learning_rate,
                a2c_entropy_coef=a2c_entropy_coef,
                a2c_device=a2c_device,
                a2c_log_interval=a2c_log_interval,
                sac_resume_checkpoints=sac_resume,
                ppo_resume_checkpoints=ppo_resume,
                a2c_resume_checkpoints=a2c_resume,
                seed=project_seed,
                multi_objective_priority=mo_priority,
            )
            results[agent] = res.__dict__
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error entrenando agente {agent}: {e}")
            print(f"[ERROR] El agente {agent} falló: {e}")
            print(f"[INFO] Continuando con los siguientes agentes...")
            continue

    # Pick best (lowest annualized carbon, then highest autosuficiencia)
    def annualized_carbon(r: dict) -> float:
        return r["carbon_kg"] / max(r["simulated_years"], 1e-9)

    def autosuficiencia(r: dict) -> float:
        # Manejar claves faltantes con get() para compatibilidad
        ev_kwh_y = r.get("ev_charging_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        build_kwh_y = r.get("building_load_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        import_kwh_y = r.get("grid_import_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        total_load = max(ev_kwh_y + build_kwh_y, 1e-9)
        return 1.0 - import_kwh_y / total_load

    # Manejar caso cuando no hay resultados de agentes
    if not results:
        print("[ADVERTENCIA] No se lograron entrenar agentes. Usando solo baseline Uncontrolled.")
        best_agent = "Uncontrolled"
    else:
        best_agent = min(
            results.keys(),
            key=lambda k: (annualized_carbon(results[k]), -autosuficiencia(results[k])),
        )

    # Calcular tailpipe y reducciones
    # Usamos el baseline (Uncontrolled + PV+BESS) para calcular el tailpipe equivalente
    baseline = res_uncontrolled
    tailpipe_kg_y = _tailpipe_kg(cfg, float(baseline["ev_charging_kwh"]), float(baseline["simulated_years"]))
    grid_only_total = float(baseline["carbon_kg"]) + tailpipe_kg_y  # CO2 si no hubiera PV/BESS
    reductions = {}
    if baseline is not None:
        base_carbon = float(baseline["carbon_kg"])
        reductions["oe2_reduction_kg"] = tailpipe_kg_y  # Reducción por electrificación
        reductions["oe2_reduction_pct"] = tailpipe_kg_y / max(grid_only_total, 1e-9)
        for agent_name, res in results.items():
            agent_carbon = float(res["carbon_kg"])
            reductions[agent_name] = {
                "reduction_kg": base_carbon - agent_carbon,
                "reduction_pct": (base_carbon - agent_carbon) / max(base_carbon, 1e-9),
            }

    summary = {
        "schema_pv_bess": str(schema_pv.resolve()),
        "pv_bess_results": results,
        "pv_bess_uncontrolled": res_uncontrolled,
        "best_agent": best_agent,
        "best_result": results[best_agent] if best_agent in results else res_uncontrolled,
        "best_agent_criteria": "min_annual_co2_then_max_autosuficiencia",
        "tailpipe_kg_per_year": tailpipe_kg_y,
        "grid_only_with_tailpipe_kg": grid_only_total,
        "reductions": reductions,
    }
    if chargers_results is not None:
        summary["chargers_results"] = chargers_results

    summary_path = out_dir / "simulation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Generar tabla comparativa de CO2
    try:
        rows = []
        rows.append({
            "Escenario": "Grid-only + tailpipe",
            "CO2_kg": grid_only_total,
            "Reduccion_vs_grid_kg": 0.0,
            "Reduccion_vs_grid_pct": 0.0,
            "Reduccion_vs_base_kg": 0.0,
            "Reduccion_vs_base_pct": 0.0,
        })
        if baseline is not None:
            base_carbon = float(baseline["carbon_kg"])
            rows.append({
                "Escenario": "Baseline PV+BESS sin control",
                "CO2_kg": base_carbon,
                "Reduccion_vs_grid_kg": grid_only_total - base_carbon,
                "Reduccion_vs_grid_pct": (grid_only_total - base_carbon) / max(grid_only_total, 1e-9),
                "Reduccion_vs_base_kg": 0.0,
                "Reduccion_vs_base_pct": 0.0,
            })
            for agent_name, res in results.items():
                co2 = float(res["carbon_kg"])
                rows.append({
                    "Escenario": agent_name,
                    "CO2_kg": co2,
                    "Reduccion_vs_grid_kg": grid_only_total - co2,
                    "Reduccion_vs_grid_pct": (grid_only_total - co2) / max(grid_only_total, 1e-9),
                    "Reduccion_vs_base_kg": base_carbon - co2,
                    "Reduccion_vs_base_pct": (base_carbon - co2) / max(base_carbon, 1e-9),
                })
            headers = [
                "Escenario", "CO2_kg", "Reduccion_vs_grid_kg",
                "Reduccion_vs_grid_pct", "Reduccion_vs_base_kg", "Reduccion_vs_base_pct"
            ]
            md_lines = ["| " + " | ".join(headers) + " |",
                        "| " + " | ".join(["---"] * len(headers)) + " |"]
            for r in rows:
                md_lines.append(
                    "| " + " | ".join([
                        str(r["Escenario"]),
                        f"{r['CO2_kg']:.2f}",
                        f"{r['Reduccion_vs_grid_kg']:.2f}",
                        f"{r['Reduccion_vs_grid_pct']*100:.4f}%",
                        f"{r['Reduccion_vs_base_kg']:.2f}",
                        f"{r['Reduccion_vs_base_pct']*100:.4f}%",
                    ]) + " |"
                )
            table_path = out_dir / "co2_comparison.md"
            table_path.write_text("\n".join(md_lines), encoding="utf-8")
    except Exception as e:
        print(f"No se pudo generar tabla comparativa: {e}")

if __name__ == "__main__":
    main()
