#!/usr/bin/env python3
"""
BASELINE USING REAL CITYLEARN ENVIRONMENT - FULL YEAR
======================================================
Runs actual CityLearn environment simulation for 8,760 timesteps (1 year)
with no intelligent control (zero actions).

This is the TRUE baseline that will take 30+ hours to complete.
Validates that dataset is properly constructed and environment works.

Duration: ~30-45 hours (1 step per environment.step() call)
Output: Real metrics from CityLearn physics simulation
"""

from __future__ import annotations

import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'baseline_citylearn_real.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)


def find_latest_schema() -> Path:
    """Find the most recently generated schema file."""
    # Try multiple locations where schema could be
    possible_locations = [
        project_root / "data" / "processed" / "citylearn" / "iquitos_ev_mall" / "schema.json",
        project_root / "outputs" / "oe3_simulations" / "schema.json",
    ]

    for schema_path in possible_locations:
        if schema_path.exists():
            logger.info(f"[OK] Found schema: {schema_path}")
            return schema_path

    # If not found in fixed locations, search
    schema_dirs = [
        project_root / "outputs" / "oe3_simulations",
        project_root / "data" / "processed" / "citylearn",
    ]

    for schema_dir in schema_dirs:
        if schema_dir.exists():
            schema_files = list(schema_dir.glob("**/schema.json"))
            if schema_files:
                latest = max(schema_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"[OK] Found schema: {latest}")
                return latest

    raise FileNotFoundError(f"No schema.json found in searched locations")
def main():
    """Main: Run baseline with real CityLearn environment."""

    logger.info("")
    logger.info("=" * 90)
    logger.info("BASELINE FULL YEAR SIMULATION USING REAL CITYLEARN ENVIRONMENT".center(90))
    logger.info("=" * 90)
    logger.info(f"Start time: {datetime.now().isoformat()}")
    logger.info("Duration expected: 30-45 hours (real physics simulation)")
    logger.info("=" * 90)

    try:
        # Import CityLearn
        from citylearn.citylearn import CityLearnEnv
        logger.info("[OK] CityLearn imported")

        # Find schema
        schema_path = find_latest_schema()

        # Initialize environment
        logger.info(f"\n[INIT] Initializing CityLearn environment with schema...")
        logger.info(f"       Schema: {schema_path}")

        env = CityLearnEnv(schema=str(schema_path), render_mode=None)
        logger.info(f"[OK] Environment initialized")
        logger.info(f"     Observation space dim: {len(env.observation_space.sample())}")
        logger.info(f"     Action space dim: {len(env.action_space.sample())}")

        # Reset environment
        logger.info(f"\n[RESET] Resetting environment...")
        obs = env.reset()
        logger.info(f"[OK] Initial observation shape: {len(obs) if isinstance(obs, (list, tuple)) else obs.shape}")

        # Prepare results storage
        n_steps = 8760
        step_results = {
            'hour': [],
            'observation_sum': [],
            'reward': [],
            'done': [],
        }

        logger.info(f"\n[SIMULATION] Running baseline for {n_steps} timesteps (1 full year)...")
        logger.info(f"Expected time: 30-45 hours")
        logger.info("")

        start_sim_time = time.time()
        last_progress_time = start_sim_time

        # Main simulation loop
        for step in range(n_steps):
            # Action: all zeros (no intelligent control)
            action = env.action_space.sample()
            action[:] = 0.0  # All chargers off

            # Step environment
            obs, reward, done, info = env.step(action)

            # Store results
            step_results['hour'].append(step)
            step_results['observation_sum'].append(float(np.sum(obs)) if isinstance(obs, np.ndarray) else float(sum(obs)))
            step_results['reward'].append(float(reward) if reward is not None else 0.0)
            step_results['done'].append(bool(done))

            # Progress report every 500 steps
            if (step + 1) % 500 == 0:
                elapsed_seconds = time.time() - start_sim_time
                elapsed_hours = elapsed_seconds / 3600.0
                progress_pct = ((step + 1) / n_steps) * 100.0

                # Estimate remaining time
                if elapsed_hours > 0:
                    rate = (step + 1) / elapsed_hours  # steps per hour
                    remaining_steps = n_steps - (step + 1)
                    eta_hours = remaining_steps / rate if rate > 0 else 0
                    eta_str = f"{eta_hours:.1f}h"
                else:
                    eta_str = "N/A"

                logger.info(
                    f"[STEP] {step+1:5d}/{n_steps} ({progress_pct:5.1f}%) | "
                    f"Elapsed: {elapsed_hours:6.2f}h | "
                    f"ETA: {eta_str:>6s} | "
                    f"Obs_sum: {step_results['observation_sum'][-1]:>12.2f} | "
                    f"Reward: {step_results['reward'][-1]:>8.4f}"
                )

            # Check if episode done
            if done:
                logger.warning(f"[WARNING] Environment reported done at step {step+1}/{n_steps}")
                break

        # Calculate elapsed time
        total_elapsed_seconds = time.time() - start_sim_time
        total_elapsed_hours = total_elapsed_seconds / 3600.0
        total_elapsed_minutes = total_elapsed_seconds / 60.0

        logger.info(f"\n{'='*90}")
        logger.info(f"[OK] SIMULATION COMPLETED")
        logger.info(f"     Total time: {total_elapsed_hours:.2f} hours ({total_elapsed_minutes:.1f} minutes)")
        logger.info(f"     Steps completed: {len(step_results['hour'])} / {n_steps}")
        logger.info(f"{'='*90}")

        # Save results
        df_results = pd.DataFrame(step_results)

        results_csv = project_root / "outputs" / "oe3" / "baseline_citylearn_real_hourly.csv"
        results_csv.parent.mkdir(parents=True, exist_ok=True)
        df_results.to_csv(results_csv, index=False)
        logger.info(f"[OK] Results CSV saved: {results_csv}")

        # Summary statistics
        summary = {
            "timestamp": datetime.now().isoformat(),
            "simulation_type": "baseline_citylearn_real",
            "duration": {
                "total_seconds": float(total_elapsed_seconds),
                "total_minutes": float(total_elapsed_minutes),
                "total_hours": float(total_elapsed_hours),
            },
            "timesteps": {
                "total": int(n_steps),
                "completed": len(step_results['hour']),
                "completed_pct": float(len(step_results['hour']) / n_steps * 100),
            },
            "metrics": {
                "observation_sum_mean": float(np.mean(step_results['observation_sum'])),
                "observation_sum_min": float(np.min(step_results['observation_sum'])),
                "observation_sum_max": float(np.max(step_results['observation_sum'])),
                "reward_mean": float(np.mean(step_results['reward'])),
                "reward_min": float(np.min(step_results['reward'])),
                "reward_max": float(np.max(step_results['reward'])),
            }
        }

        summary_json = project_root / "outputs" / "oe3" / "baseline_citylearn_real_summary.json"
        with open(summary_json, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"[OK] Summary JSON saved: {summary_json}")

        # Print summary
        logger.info(f"\n{'='*90}")
        logger.info(f"BASELINE SUMMARY - REAL CITYLEARN ENVIRONMENT")
        logger.info(f"{'='*90}")
        logger.info(f"Simulation time:        {total_elapsed_hours:.2f} hours ({total_elapsed_minutes:.1f} min)")
        logger.info(f"Steps completed:        {len(step_results['hour'])} / {n_steps}")
        logger.info(f"Observation sum (avg):  {summary['metrics']['observation_sum_mean']:.2f}")
        logger.info(f"Reward (avg):           {summary['metrics']['reward_mean']:.6f}")
        logger.info(f"{'='*90}")
        logger.info(f"End time: {datetime.now().isoformat()}")

        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Baseline simulation failed!")
        logger.error(f"        {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
