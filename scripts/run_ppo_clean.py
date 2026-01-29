from __future__ import annotations

import argparse
import json
import logging
import time

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

    print("\n" + "="*80)
    print("PPO TRAINING (LIMPIO - SIN CHECKPOINTS PREVIOS)")
    print("="*80 + "\n")

    # dataset_name = cfg["oe3"]["dataset"]["name"]  # Not used
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

    # CREAR directorio explícitamente
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INIT] Output directory: {out_dir}")
    print(f"[INIT] Output directory exists: {out_dir.exists()}\n")

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuración PPO
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
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", False))  # SIEMPRE False para entrenamiento limpio

    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))
    logger = logging.getLogger(__name__)

    print(f"[CONFIG] Timesteps: {ppo_timesteps}")
    print(f"[CONFIG] Device: {ppo_device}")
    print(f"[CONFIG] Resume checkpoints: {ppo_resume} (False = entrenar desde cero)")
    print(f"[CONFIG] Multi-objective: {mo_priority}")
    print(f"[CONFIG] Output path: {out_dir}\n")

    print(">>> INICIANDO ENTRENAMIENTO <<<\n")
    start_time = time.time()

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
            ppo_resume_checkpoints=ppo_resume,  # False para entrenamiento limpio
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )

        elapsed = time.time() - start_time

        # GUARDAR RESULTADO - ULTRA ROBUSTO
        ppo_result_path = out_dir / "result_PPO.json"
        print(f"\n[SAVE] Guardando resultado en: {ppo_result_path}")
        ppo_result_path.write_text(json.dumps(res.__dict__, indent=2), encoding="utf-8")

        # VALIDAR que se guardó
        if ppo_result_path.exists():
            file_size = ppo_result_path.stat().st_size
            print(f"[SAVE] ✓ Archivo guardado correctamente ({file_size} bytes)")
        else:
            raise RuntimeError(f"CRÍTICO: El archivo NO se guardó en {ppo_result_path}")

        print("\n" + "="*80)
        print("PPO TRAINING COMPLETADO EXITOSAMENTE")
        print("="*80)
        print(f"Tiempo total: {elapsed/60:.1f} minutos")
        print(f"CO2 (kg/año): {res.carbon_kg:.2f}")
        print(f"Grid Import (kWh/año): {res.grid_import_kwh:.2f}")
        print(f"Grid Export (kWh/año): {res.grid_export_kwh:.2f}")
        print(f"EV Charging (kWh/año): {res.ev_charging_kwh:.2f}")
        print(f"PV Generation (kWh/año): {res.pv_generation_kwh:.2f}")
        print(f"Años simulados: {res.simulated_years:.2f}")
        print(f"")
        print(f"Resultado guardado en: {ppo_result_path}")
        print(f"Timeseries guardado en: {res.timeseries_path}")
        print("="*80 + "\n")

        logger.info(f"✓ PPO training completed successfully")
        logger.info(f"✓ Results saved to {ppo_result_path}")

    except Exception as e:
        logger.error(f"ERROR durante PPO training: {e}", exc_info=True)
        print(f"\n[ERROR] Falló el entrenamiento PPO: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
