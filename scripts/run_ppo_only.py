from __future__ import annotations

import argparse
import json
import logging

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
    oe3_cfg = cfg["oe3"]

    # cfg["oe3"]["dataset"]["name"]  # Not used in this script
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir

    schema_pv = dataset_dir / "schema_pv_bess.json"
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuración PPO solo
    eval_cfg = cfg["oe3"]["evaluation"]
    ppo_cfg = eval_cfg.get("ppo", {})

    ppo_episodes = ppo_cfg.get("episodes")
    if ppo_episodes is not None:
        ppo_timesteps = int(ppo_episodes) * 8760
    else:
        ppo_timesteps = int(ppo_cfg.get("timesteps", 100000))
    ppo_device = ppo_cfg.get("device")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 1000))
    ppo_target_kl = ppo_cfg.get("target_kl")
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))
    ppo_n_steps = int(ppo_cfg.get("n_steps", 1024))
    ppo_batch_size = int(ppo_cfg.get("batch_size", 128))
    ppo_use_amp = bool(ppo_cfg.get("use_amp", True))
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", True))

    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))
    logger = logging.getLogger(__name__)

    print("\n" + "="*80)
    print("BASELINE + PPO TRAINING")
    print("="*80)
    print(f"Timesteps (PPO): {ppo_timesteps}")
    print(f"Device: {ppo_device}")
    print(f"Resume: {ppo_resume}")
    print(f"Multi-objective: {mo_priority}")
    print("="*80 + "\n")

    # Asegurar que out_dir existe
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. BASELINE (Uncontrolled)
    print("\n>>> FASE 1: CALCULANDO BASELINE (Uncontrolled) <<<\n")
    try:
        res_baseline = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            deterministic_eval=True,
            multi_objective_priority=mo_priority,
        )

        # GUARDAR MANUALMENTE para asegurar que se guarde
        baseline_result_path = out_dir / "result_Uncontrolled.json"
        baseline_result_path.write_text(json.dumps(res_baseline.__dict__, indent=2), encoding="utf-8")

        print("\n" + "="*80)
        print("BASELINE COMPLETE")
        print("="*80)
        print(f"CO2: {res_baseline.carbon_kg:.2f} kg/year")
        print(f"Grid Import: {res_baseline.grid_import_kwh:.2f} kWh/year")
        print(f"Guardado en: {baseline_result_path}")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Error en baseline: {e}")
        print(f"[ERROR] Baseline failed: {e}")
        raise

    # 2. PPO TRAINING
    print("\n>>> FASE 2: ENTRENAMIENTO PPO <<<\n")

    # 2. PPO TRAINING
    print("\n>>> FASE 2: ENTRENAMIENTO PPO <<<\n")

    try:
        res = simulate(
            schema_path=schema_pv,
            agent_name="PPO",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=True,
            ppo_device=ppo_device,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_n_steps=ppo_n_steps,
            ppo_batch_size=ppo_batch_size,
            ppo_use_amp=ppo_use_amp,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            ppo_resume_checkpoints=ppo_resume,
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )

        # GUARDAR MANUALMENTE para asegurar que se guarde
        ppo_result_path = out_dir / "result_PPO.json"
        ppo_result_path.write_text(json.dumps(res.__dict__, indent=2), encoding="utf-8")

        print("\n" + "="*80)
        print("PPO TRAINING COMPLETE")
        print("="*80)
        print(f"CO2: {res.carbon_kg:.2f} kg/year")
        print(f"Baseline CO2: {res_baseline.carbon_kg:.2f} kg/year")
        print(f"Reduction: {res_baseline.carbon_kg - res.carbon_kg:.2f} kg/year ({(1 - res.carbon_kg/max(res_baseline.carbon_kg, 1e-9))*100:.1f}%)")
        print(f"Grid Import: {res.grid_import_kwh:.2f} kWh/year")
        print(f"Guardado en: {ppo_result_path}")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Error entrenando PPO: {e}")
        print(f"[ERROR] PPO training failed: {e}")
        raise

    finally:
        print(f"\n[DEBUG] Expected output directory: {out_dir}")
        print(f"[DEBUG] Directory exists: {out_dir.exists()}")
        if out_dir.exists():
            files = list(out_dir.glob("result_*.json"))
            print(f"[DEBUG] Result files found: {len(files)}")
            for f in files:
                print(f"  - {f.name} ({f.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
