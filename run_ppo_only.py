#!/usr/bin/env python
"""Run SOLO PPO - saltando SAC y A2C."""
from __future__ import annotations

import argparse
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

    # SOLO PPO - modificar config
    cfg["oe3"]["evaluation"]["agents"] = ["PPO", "Uncontrolled"]

    # Not used in this script
    # cfg["oe3"]["dataset"]["name"]
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir

    schema_pv = dataset_dir / "schema_pv_bess.json"

    out_dir = rp.outputs_dir / "oe3_simulations"
    out_dir.mkdir(parents=True, exist_ok=True)

    training_dir = rp.analyses_dir / "oe3" / "training"
    training_dir.mkdir(parents=True, exist_ok=True)

    # Configuración
    sac_cfg = oe3_cfg["agents"]["sac"]
    ppo_cfg = oe3_cfg["agents"]["ppo"]
    # Not used in this script
    # oe3_cfg["evaluation"]

    ci = float(oe3_cfg.get("carbon_intensity_kg_per_kwh", 0.4521))
    seconds_per_time_step = int(oe3_cfg["env"].get("seconds_per_time_step", 3600))

    ppo_timesteps = int(ppo_cfg.get("total_timesteps", 26280))
    ppo_n_steps = int(ppo_cfg.get("n_steps", 1024))
    ppo_batch_size = int(ppo_cfg.get("batch_size", 128))
    ppo_use_amp = bool(ppo_cfg.get("use_amp", True))
    ppo_target_kl = ppo_cfg.get("target_kl")
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))
    ppo_device = ppo_cfg.get("device", "auto")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 1000))
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", True))

    sac_episodes = int(sac_cfg.get("episodes", 1))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_use_amp = bool(sac_cfg.get("use_amp", True))
    sac_log_interval = int(sac_cfg.get("log_interval", 500))
    # Not used in this script
    # sac_cfg.get("device", "auto")
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 1000))
    sac_resume = bool(sac_cfg.get("resume_checkpoints", True))

    project_seed = int(cfg.get("seed", 42))
    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "CO2_FOCUS"))

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("LANZANDO SOLO PPO (saltando SAC y A2C)")
    logger.info("=" * 80)

    # Baseline Uncontrolled
    logger.info("\n[1/2] Ejecutando baseline (Uncontrolled)...")
    _ = simulate(
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
        sac_resume_checkpoints=sac_resume,
        ppo_resume_checkpoints=ppo_resume,
        a2c_resume_checkpoints=False,
        seed=project_seed,
        multi_objective_priority=mo_priority,
    )
    logger.info("✓ Uncontrolled completado")

    # PPO
    logger.info("\n[2/2] Ejecutando PPO...")
    _ = simulate(
        schema_path=schema_pv,
        agent_name="PPO",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=ci,
        seconds_per_time_step=seconds_per_time_step,
        sac_episodes=0,  # NO SAC
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
        a2c_timesteps=0,  # NO A2C
        ppo_resume_checkpoints=ppo_resume,
        a2c_resume_checkpoints=False,
        seed=project_seed,
        multi_objective_priority=mo_priority,
    )
    logger.info("✓ PPO completado")

    logger.info("\n" + "=" * 80)
    logger.info("✓✓✓ SIMULACIÓN SOLO PPO COMPLETADA ✓✓✓")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
