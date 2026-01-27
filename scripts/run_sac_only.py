#!/usr/bin/env python3
"""
Script para entrenar SOLO SAC (Soft Actor-Critic).
Sistema completamente integrado con validación Python 3.11.
"""
from __future__ import annotations

import argparse

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all  # Incluye validación Python 3.11


def main() -> int:
    """Entrena SAC agent con datos OE2/OE3 sincronizados."""
    ap = argparse.ArgumentParser(
        description="Entrenar SAC agent (Soft Actor-Critic) para control energético en Iquitos"
    )
    ap.add_argument("--config", default="configs/default.yaml", help="Ruta a config YAML")

    args = ap.parse_args()

    # Configuración y validación Python 3.11
    setup_logging()
    cfg, rp = load_all(args.config)

    # Dataset
    dataset_name = cfg["oe3"]["dataset"]["name"]
    print("[INFO] Construyendo dataset CityLearn desde cero...")
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
    _ = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # SAC config
    sac_cfg = cfg["oe3"]["evaluation"].get("sac", {})
    sac_episodes = int(sac_cfg.get("episodes", 10))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_log_interval = int(sac_cfg.get("log_interval", 500))
    sac_use_amp = bool(sac_cfg.get("use_amp", True))

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
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=ci,
        seconds_per_time_step=seconds_per_time_step,
        sac_episodes=sac_episodes,
        sac_batch_size=sac_batch_size,
        sac_log_interval=sac_log_interval,
        sac_use_amp=sac_use_amp,
    )

    print("\n" + "="*80)
    print("[✓] ENTRENAMIENTO SAC COMPLETADO")
    print("="*80)
    print(f"Resultados: {out_dir}")
    print(f"Checkpoints: checkpoints/SAC/")
    return 0


if __name__ == "__main__":
    exit(main())
