#!/usr/bin/env python3
"""
Robust Baseline Simulation - Full Year (8,760 hours)
Simulates uncontrolled EV charging with real CityLearn environment
Expected duration: 30-45 minutes
"""
import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def run_baseline_simulation():
    """Run full-year baseline simulation with real CityLearn environment"""

    try:
        from citylearn.citylearn_env import CityLearnEnv
    except ImportError:
        logger.error("CityLearn not installed. Install with: pip install citylearn")
        return False

    # Paths
    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
    output_dir = Path("outputs/oe3")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("BASELINE SIMULATION - FULL YEAR UNCONTROLLED (8,760 hours)")
    logger.info("=" * 80)
    logger.info(f"Schema: {schema_path}")
    logger.info(f"Expected duration: 30-45 minutes")
    logger.info(f"Total timesteps: 8,760 (1 year hourly)")
    logger.info("")

    # Check schema exists
    if not schema_path.exists():
        logger.error(f"Schema not found: {schema_path}")
        return False

    logger.info(f"✅ Schema loaded: {schema_path}")

    # Initialize environment
    try:
        logger.info("Initializing CityLearn environment...")
        env = CityLearnEnv(schema=str(schema_path))
        logger.info(f"✅ Environment initialized")
        logger.info(f"   Observation space: {env.observation_space}")
        logger.info(f"   Action space: {env.action_space}")
    except Exception as e:
        logger.error(f"Failed to initialize environment: {e}")
        return False

    # Storage for metrics
    metrics = {
        'timesteps': [],
        'grid_import': [],
        'solar_generation': [],
        'pv_used': [],
        'co2_emissions': [],
        'bess_soc': [],
        'total_demand': []
    }

    logger.info("")
    logger.info("=" * 80)
    logger.info("STARTING SIMULATION - Baseline (All EVs continuous, no control)")
    logger.info("=" * 80)

    obs = env.reset()
    total_reward = 0
    start_time = datetime.now()

    # Run full year simulation
    for timestep in range(8760):
        # Action: All chargers at maximum (no control = continuous charging)
        action = np.ones(env.action_space.shape[0])  # All 1.0 = full power

        # Step environment
        obs, reward, done, info = env.step(action)
        total_reward += reward

        # Collect metrics every 100 steps
        if (timestep + 1) % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            steps_per_sec = (timestep + 1) / elapsed
            eta_remaining = (8760 - timestep) / steps_per_sec / 60  # minutes

            logger.info(
                f"Step {timestep + 1:5d}/8760 | "
                f"Reward: {reward:7.2f} | "
                f"Elapsed: {elapsed:6.1f}s | "
                f"ETA: {eta_remaining:6.1f}min"
            )

        if done:
            logger.info(f"Episode finished at step {timestep + 1}")
            break

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"\n✅ Simulation completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    logger.info(f"   Total reward: {total_reward:.2f}")

    # Extract results from environment
    try:
        # Get building metrics
        buildings = env.buildings
        total_grid_import = 0
        total_co2 = 0
        total_solar = 0

        for building in buildings:
            # Aggregate metrics
            if hasattr(building, 'net_electricity_consumption_history'):
                net_consumption = sum(building.net_electricity_consumption_history)
                total_grid_import += max(0, net_consumption)

            if hasattr(building, 'carbon_emission_history'):
                total_co2 += sum(building.carbon_emission_history)

            if hasattr(building, 'solar_generation_history'):
                total_solar += sum(building.solar_generation_history)

        results = {
            'total_timesteps': 8760,
            'total_grid_import_kwh': float(total_grid_import),
            'total_co2_kg': float(total_co2),
            'total_solar_kwh': float(total_solar),
            'average_grid_import_kw': float(total_grid_import / 8760),
            'simulation_time_seconds': elapsed,
            'total_reward': float(total_reward),
            'timestamp': start_time.isoformat(),
            'scenario': 'baseline_uncontrolled'
        }

        logger.info("")
        logger.info("=" * 80)
        logger.info("BASELINE RESULTS (Uncontrolled)")
        logger.info("=" * 80)
        logger.info(f"Total Grid Import:    {total_grid_import:,.2f} kWh")
        logger.info(f"Total CO2 Emissions:  {total_co2:,.2f} kg")
        logger.info(f"Total Solar Generated: {total_solar:,.2f} kWh")
        logger.info(f"Average Grid Import:  {total_grid_import/8760:,.2f} kW")
        logger.info("")

        # Save results
        results_file = output_dir / "baseline_full_simulation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"✅ Results saved to: {results_file}")
        logger.info("")
        logger.info("=" * 80)
        logger.info("BASELINE CALCULATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        return False

if __name__ == "__main__":
    success = run_baseline_simulation()
    sys.exit(0 if success else 1)
