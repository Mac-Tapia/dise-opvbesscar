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

    eval_cfg = cfg["oe3"]["evaluation"]
    ppo_cfg = eval_cfg.get("ppo", {})
    ppo_device = ppo_cfg.get("device")
    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))
    logger = logging.getLogger(__name__)

    print("\n" + "="*80)
    print("SIMULACIÓN FINAL PPO (CARGANDO MODELO ENTRENADO)")
    print("="*80 + "\n")

    try:
        # Cargar el modelo entrenado y simular
        res = simulate(
            schema_path=schema_pv,
            agent_name="PPO",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            ppo_timesteps=0,  # 0 = solo simular sin entrenar más
            deterministic_eval=True,
            ppo_device=ppo_device,
            ppo_resume_checkpoints=True,  # CARGAR modelo entrenado
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )

        # GUARDAR resultado
        ppo_result_path = out_dir / "result_PPO.json"
        ppo_result_path.write_text(json.dumps(res.__dict__, indent=2), encoding="utf-8")

        print("\n" + "="*80)
        print("✓ SIMULACIÓN PPO FINAL COMPLETADA")
        print("="*80)
        print(f"Resultado guardado: {ppo_result_path}")
        print(f"Existe: {ppo_result_path.exists()}")
        print(f"Tamaño: {ppo_result_path.stat().st_size if ppo_result_path.exists() else 'N/A'} bytes")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"[ERROR] {e}")
        raise

if __name__ == "__main__":
    main()
