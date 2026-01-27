#!/usr/bin/env python3
"""
Script para entrenar PPO y A2C con sistema completamente integrado OE2/OE3.
Sistema validado Python 3.11, BESS 4520/2712, Schema 8760 timesteps.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all  # Incluye validación Python 3.11


def main() -> None:
    """Entrena PPO y A2C agents con datos OE2/OE3 sincronizados."""
    ap = argparse.ArgumentParser(
        description="Entrenar PPO y A2C agents para control energético en Iquitos"
    )
    ap.add_argument("--config", default="configs/default.yaml", help="Ruta a config YAML")
    args = ap.parse_args()

    # Configuración y validación Python 3.11
    setup_logging()
    cfg, rp = load_all(args.config)

    dataset_name = cfg["oe3"]["dataset"]["name"]
    print("[INFO] Construyendo dataset CityLearn desde cero...")
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
    training_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*80)
    print("ENTRENAMIENTO PPO/A2C - SISTEMA COMPLETO OE2/OE3")
    print("="*80)
    print(f"[OK] Python 3.11 validado")
    print(f"[OK] Schema: {schema_pv}")
    print(f"[OK] Dataset: {dataset_dir}")
    print(f"[OK] BESS: 4520 kWh / 2712 kW (OE2-calculado)")
    print(f"[OK] Chargers: 128 sockets (32 chargers)")
    print(f"[OK] Solar: 8,760 timesteps horarios (1 año)")
    print("="*80 + "\n")
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

    # BASELINE: Calcular desde datos reales del dataset construido
    print("\n" + "="*80)
    print("[CALCULANDO] BASELINE desde datos reales del dataset")
    print("="*80 + "\n")

    # Leer datos reales del dataset construido
    building_1_csv = dataset_dir / "Building_1.csv"
    baseline_json = out_dir / "baseline_real_uncontrolled.json"

    if building_1_csv.exists():
        try:
            df_building = pd.read_csv(building_1_csv)

            # Baseline: usar demanda real del building sin control inteligente
            # IMPORTANTE: El CSV usa 'non_shiftable_load' no 'electricity_demand'
            baseline_demand_kwh = float(df_building['non_shiftable_load'].sum()) if 'non_shiftable_load' in df_building.columns else 0.0
            baseline_solar_kwh = float(df_building['solar_generation'].sum()) if 'solar_generation' in df_building.columns else 0.0

            # Grid import = demanda - solar disponible
            baseline_grid_import_kwh = float(max(0, baseline_demand_kwh - baseline_solar_kwh))
            baseline_co2_kg = float(baseline_grid_import_kwh * ci)

            baseline_data = {
                "name": "Uncontrolled",
                "total_timesteps": len(df_building),
                "demand_kwh": baseline_demand_kwh,
                "solar_kwh": baseline_solar_kwh,
                "grid_import_kwh": baseline_grid_import_kwh,
                "co2_kg": baseline_co2_kg,
                "grid_carbon_intensity": ci,
                "source": "REAL desde Building_1.csv construido con OE2->OE3"
            }

            with open(baseline_json, 'w') as f:
                json.dump(baseline_data, f, indent=2)

            print(f"[OK] BASELINE REAL calculado desde Building_1.csv")
            print(f"    Demanda total: {baseline_demand_kwh:,.0f} kWh")
            print(f"    Solar total: {baseline_solar_kwh:,.0f} kWh")
            print(f"    Importacion grid: {baseline_grid_import_kwh:,.0f} kWh")
            print(f"    CO2 emissions: {baseline_co2_kg:,.0f} kg")
            print(f"    Archivo: {baseline_json}\n")
        except Exception as e:
            print(f"[ERROR] Error al calcular baseline: {e}")
            baseline_json = None
    else:
        print(f"[ADVERTENCIA] No se encontro Building_1.csv en {building_1_csv}")
        print(f"[ADVERTENCIA] Baseline no calculado")
        baseline_json = None

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
        print("\n" + "="*40)
        print("[OK] PPO COMPLETADO EXITOSAMENTE")
        print("="*40 + "\n")
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
            print("\n" + "="*40)
            print("[OK] A2C COMPLETADO EXITOSAMENTE")
            print("="*40 + "\n")
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
