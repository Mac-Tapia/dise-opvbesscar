from __future__ import annotations

import argparse
from pathlib import Path
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

    dataset_name = cfg["oe3"]["dataset"]["name"]
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir

    schema_pv = dataset_dir / "schema_pv_bess.json"
    chargers_results_path = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    out_dir.mkdir(parents=True, exist_ok=True)

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuration
    eval_cfg = cfg["oe3"]["evaluation"]
    # Force NO resume - start from scratch
    resume_checkpoints_global = False
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})

    sac_episodes = int(sac_cfg.get("episodes", 5))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_log_interval = int(sac_cfg.get("log_interval", 500))
    sac_learning_rate = float(sac_cfg.get("learning_rate", 1e-4))
    sac_use_amp = bool(sac_cfg.get("use_amp", True))
    sac_device = sac_cfg.get("device")
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 1000))
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))

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
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", resume_checkpoints_global))

    det_eval = bool(sac_cfg.get("deterministic_eval", True))
    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "balanced"))

    logger = logging.getLogger(__name__)
    results = {}

    # Train SAC
    agent_names = ["SAC", "PPO"]

    for agent in agent_names:
        logger.info(f"Starting training for {agent}...")
        print(f"\n{'='*80}")
        print(f">> Training {agent}...")
        print(f"{'='*80}\n")

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
                sac_learning_rate=sac_learning_rate,
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
                a2c_timesteps=0,
                a2c_checkpoint_freq_steps=1000,
                a2c_n_steps=512,
                a2c_learning_rate=3e-4,
                a2c_entropy_coef=0.01,
                a2c_device="cpu",
                a2c_log_interval=2000,
                sac_resume_checkpoints=resume_checkpoints_global,
                ppo_resume_checkpoints=ppo_resume,
                a2c_resume_checkpoints=False,
                seed=project_seed,
                multi_objective_priority=mo_priority,
            )
            results[agent] = res.__dict__
            logger.info(f"✓ {agent} training completed")
            print(f"✓ {agent} training completed\n")
        except Exception as e:
            logger.error(f"✗ {agent} training failed: {e}")
            print(f"✗ {agent} training failed: {e}\n")

    print(f"\n{'='*80}")
    print("✓ SAC and PPO training completed!")
    print(f"{'='*80}\n")

    # Generate training metrics visualization
    print("\n🎯 Generating training metrics visualization...")
    from scripts.monitor_training_metrics import TrainingMonitor

    monitor = TrainingMonitor(rp.outputs_dir / "oe3" / "training_monitoring")

    for agent in ["SAC", "PPO"]:
        print(f"\n📊 Processing metrics for {agent}...")
        monitor.plot_training_metrics(agent)
        monitor.print_summary(agent)

    print("\n📊 Generating SAC vs PPO comparison...")
    monitor.plot_comparison()

    print("\n[OK] Training metrics visualization completed!")

if __name__ == "__main__":
    main()
