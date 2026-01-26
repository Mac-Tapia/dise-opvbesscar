#!/usr/bin/env python3
"""
Script para entrenar SOLO PPO y A2C (saltando SAC que ya está completado).
Reutiliza los checkpoints de SAC y continúa con los siguientes agentes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
import logging

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--skip-dataset", action="store_true")
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
    a2c_cfg = eval_cfg.get("a2c", {})

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

    a2c_episodes = a2c_cfg.get("episodes")
    if a2c_episodes is not None:
        a2c_timesteps = int(a2c_episodes) * 8760
    else:
        a2c_timesteps = int(a2c_cfg.get("timesteps", 0))
    a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 1000))
    a2c_n_steps = int(a2c_cfg.get("n_steps", 512))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
    a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
    a2c_device = a2c_cfg.get("device")
    a2c_log_interval = int(a2c_cfg.get("log_interval", 2000))
    a2c_resume = bool(a2c_cfg.get("resume_checkpoints", True))

    mo_priority = cfg["oe3"]["evaluation"].get("multi_objective_priority", "balanced")

    results = {}

    # VERIFICAR SI BASELINE EXISTE - SI EXISTE, SALTEAR
    baseline_json = out_dir / "result_Uncontrolled.json"
    res_uncontrolled = None
    if baseline_json.exists():
        print("\n" + "="*80)
        print("✓ BASELINE (Uncontrolled) ya existe - SALTANDO")
        print("="*80 + "\n")
        with open(baseline_json) as f:
            res_uncontrolled = json.load(f)
    else:
        print("\n" + "="*80)
        print("⚠️  BASELINE (Uncontrolled) NO ENCONTRADO - Necesario para comparación")
        print("Por favor ejecutar: python -m scripts.run_uncontrolled_baseline --config configs/default.yaml")
        print("="*80 + "\n")
        print("[ADVERTENCIA] Continuando sin baseline... Los resultados serán incompletos")

    # SOLO PPO
    print("\n" + "="*80)
    print("INICIANDO ENTRENAMIENTO DE PPO (SAC ya completado, saltando...)")
    print("="*80 + "\n")

    try:
        res_ppo = simulate(
            schema_path=schema_pv,
            agent_name="PPO",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            ppo_timesteps=ppo_timesteps,
            ppo_device=ppo_device,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            ppo_n_steps=ppo_n_steps,
            ppo_batch_size=ppo_batch_size,
            ppo_use_amp=ppo_use_amp,
            ppo_resume_checkpoints=ppo_resume,
            a2c_timesteps=0,  # No entrenar A2C aún
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )
        results["PPO"] = res_ppo.__dict__
        print("\n" + "✓"*40)
        print("PPO COMPLETADO EXITOSAMENTE")
        print("✓"*40 + "\n")
    except Exception as e:
        print(f"\n[ERROR] PPO falló: {e}\n")
        import traceback
        traceback.print_exc()

    # SOLO A2C
    if a2c_timesteps > 0:
        print("\n" + "="*80)
        print("INICIANDO ENTRENAMIENTO DE A2C")
        print("="*80 + "\n")

        try:
            res_a2c = simulate(
                schema_path=schema_pv,
                agent_name="A2C",
                out_dir=out_dir,
                training_dir=training_dir,
                carbon_intensity_kg_per_kwh=ci,
                seconds_per_time_step=seconds_per_time_step,
                a2c_timesteps=a2c_timesteps,
                a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
                a2c_n_steps=a2c_n_steps,
                a2c_learning_rate=a2c_learning_rate,
                a2c_entropy_coef=a2c_entropy_coef,
                a2c_device=a2c_device,
                a2c_log_interval=a2c_log_interval,
                a2c_resume_checkpoints=a2c_resume,
                ppo_timesteps=0,  # No entrenar PPO nuevamente
                seed=project_seed,
                multi_objective_priority=mo_priority,
            )
            results["A2C"] = res_a2c.__dict__
            print("\n" + "✓"*40)
            print("A2C COMPLETADO EXITOSAMENTE")
            print("✓"*40 + "\n")
        except Exception as e:
            print(f"\n[ERROR] A2C falló: {e}\n")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    for agent, res in results.items():
        print(f"{agent}: {res.get('simulated_years', 0)} años, CO2: {res.get('carbon_kg', 0):.2f} kg")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
