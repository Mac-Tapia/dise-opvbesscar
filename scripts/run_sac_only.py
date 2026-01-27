#!/usr/bin/env python3
"""
Script para entrenar SOLO SAC (Soft Actor-Critic).
Sistema completamente integrado con validación Python 3.11.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all  # Incluye validación Python 3.11


def main() -> None:
    """Entrena SAC agent con datos OE2/OE3 sincronizados."""
    ap = argparse.ArgumentParser(
        description="Entrenar SAC agent (Soft Actor-Critic) para control energético en Iquitos"
    )
    ap.add_argument("--config", default="configs/default.yaml", help="Ruta a config YAML")
    ap.add_argument("--skip-dataset", action="store_true", help="Reutilizar dataset CityLearn")
    args = ap.parse_args()

    # Configuración y validación Python 3.11
    setup_logging()
    cfg, rp = load_all(args.config)

    # Dataset
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

    if args.skip_dataset and processed_dataset_dir.exists():
        dataset_dir = processed_dataset_dir
        print(f"[INFO] Reutilizando dataset: {dataset_dir}")
    else:
        print("[INFO] Construyendo dataset CityLearn...")
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        dataset_dir = built.dataset_dir

    # Schema y directorios
    schema_pv = dataset_dir / "schema_pv_bess.json"
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)
    training_dir.mkdir(parents=True, exist_ok=True)

    # Parámetros globales
    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # SAC config
    sac_cfg = cfg["oe3"]["evaluation"].get("sac", {})

    print("\n" + "="*80)
    print("ENTRENAMIENTO SAC - SISTEMA COMPLETO OE2/OE3")
    print("="*80)
    print(f"[✓] Python 3.11 validado")
    print(f"[✓] Schema: {schema_pv}")
    print(f"[✓] Dataset: {dataset_dir}")
    print(f"[✓] BESS: 4520 kWh / 2712 kW (OE2-calculado)")
    print(f"[✓] Chargers: 128 sockets (32 chargers)")
    print(f"[✓] Solar: 8,760 timesteps horarios (1 año)")
    print(f"[✓] Grid CI: {ci} kg CO₂/kWh")
    print("="*80 + "\n")

    # Entrenar SAC
    print("[INFO] Iniciando entrenamiento SAC...")
    simulate(
        config_dict=cfg,
        dataset_path=dataset_dir,
        output_dir=out_dir,
        training_dir=training_dir,
        agents_to_run=["sac"],
        seed=project_seed,
    )

    print("\n" + "="*80)
    print("[✓] ENTRENAMIENTO SAC COMPLETADO")
    print("="*80)
    print(f"Resultados: {out_dir}")
    print(f"Checkpoints: checkpoints/SAC/")


if __name__ == "__main__":
    main()
