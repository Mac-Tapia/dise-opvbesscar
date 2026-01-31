#!/usr/bin/env python
"""
Rebuilds the OE3 CityLearn dataset from OE2 artifacts and runs the full SAC/PPO/A2C
training pipeline end-to-end. Removes any cached dataset so the builders reprocess the
complete 8,760-hour files before rerunning the agents.

Usage:
    python scripts/rebuild_and_train_full_year.py [--config CONFIG]
        [--sac-episodes N] [--ppo-episodes N] [--a2c-episodes N]

After training, the uncontrolled baseline pipeline is executed so you keep the latest
baseline metrics for comparison.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._common import load_all
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Cleanup + rebuild OE3 dataset + train all agents")
    ap.add_argument("--config", default="configs/default.yaml", help="Config YAML path")
    ap.add_argument("--sac-episodes", type=int, default=3, help="SAC episodes (matches run_sac_ppo_a2c_only default)")
    ap.add_argument("--ppo-episodes", type=int, default=3, help="PPO episodes")
    ap.add_argument("--a2c-episodes", type=int, default=3, help="A2C episodes")
    ap.add_argument("--skip-baseline", action="store_true", help="Do not rerun run_uncontrolled_baseline.py")
    return ap.parse_args()


def remove_dataset(cfg: dict, rp: Any) -> None:
    dataset_name = cfg["oe3"]["dataset"]["name"]
    dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    if dataset_dir.exists():
        logger.info("Removing cached dataset directory: %s", dataset_dir)
        shutil.rmtree(dataset_dir)
    else:
        logger.info("No cached dataset found at %s (nothing to delete)", dataset_dir)


def rebuild_dataset(cfg: dict, rp: Any) -> Path:
    logger.info("Rebuilding OE3 CityLearn dataset from OE2 artifacts")
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    logger.info("Dataset rebuilt: %s", built.schema_path)
    return built.dataset_dir


def run_training(cfg: dict, args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_sac_ppo_a2c_only",
        "--config",
        args.config,
        "--sac-episodes",
        str(args.sac_episodes),
        "--ppo-episodes",
        str(args.ppo_episodes),
        "--a2c-episodes",
        str(args.a2c_episodes),
    ]
    logger.info("Launching SAC/PPO/A2C pipeline (%s)", " ".join(cmd))
    subprocess.run(cmd, check=True)


def run_baseline() -> None:
    baseline_script = Path(__file__).with_name("run_uncontrolled_baseline.py")
    cmd = [sys.executable, str(baseline_script)]
    logger.info("Running uncontrolled baseline pipeline (%s)", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = parse_args()
    cfg, rp = load_all(args.config)

    remove_dataset(cfg, rp)
    rebuild_dataset(cfg, rp)
    run_training(cfg, args)

    if not args.skip_baseline:
        run_baseline()


if __name__ == "__main__":
    main()
