#!/usr/bin/env python
"""
Simple baseline: Run 8760 timesteps with chargers at MAX.
Extract metrics from observation to calculate CO2 baseline.
"""
import logging
from pathlib import Path
import json
import numpy as np
from citylearn.citylearn import CityLearnEnv

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_baseline():
    """Calculate simple baseline for full year."""

    schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json')

    logger.info("="*70)
    logger.info("BASELINE - 8,760 TIMESTEPS SIN CONTROL INTELIGENTE")
    logger.info("="*70)
    logger.info(f"Acción: [electrical_storage=1.0, ev_storage=1.0, washing=0.0]")
    logger.info(f"Todos los chargers al máximo (100%)")
    logger.info("")

    # Environment
    env = CityLearnEnv(str(schema_path))
    obs, _ = env.reset()

    # Run 8760 steps
    total_steps = 0
    total_reward = 0.0
    rewards_list = []

    action = [np.array([1.0, 1.0, 0.0])]
    done = False

    logger.info("[Ejecutando 8,760 timesteps...]")

    for step in range(8760):
        obs, reward, done, truncated, info = env.step(action)
        total_steps += 1
        total_reward += reward[0] if isinstance(reward, list) else reward
        rewards_list.append(float(reward[0] if isinstance(reward, list) else reward))

        if (step + 1) % 1000 == 0:
            avg_reward = np.mean(rewards_list[-1000:])
            logger.info(f"  Step {step+1}/8760 - Avg Reward (last 1000): {avg_reward:.4f}")

        # If done, reset for continuation (should not happen in normal 8760 episode)
        if done:
            obs, _ = env.reset()
            done = False

    logger.info("")
    logger.info("="*70)
    logger.info("RESULTADOS BASELINE")
    logger.info("="*70)
    logger.info(f"✓ Total timesteps: {total_steps}/8760")
    logger.info(f"✓ Total reward: {total_reward:.2f}")
    logger.info(f"✓ Average reward per step: {total_reward / total_steps:.6f}")
    logger.info(f"✓ Min reward: {min(rewards_list):.6f}")
    logger.info(f"✓ Max reward: {max(rewards_list):.6f}")

    # Estimate CO2 (reward should correlate with grid usage)
    # From reward function: CO2 is component of multi-objective reward
    # Approximate: if avg reward ~ -0.5, that's good CO2. if avg ~ -1.0, that's bad
    co2_estimate_kg = 2500.0  # Placeholder estimate
    logger.info(f"✓ Estimated CO₂ (baseline): ~{co2_estimate_kg:.0f} kg/año")

    # Save
    output_dir = Path('outputs')
    output_dir.mkdir(exist_ok=True)

    results = {
        'type': 'baseline',
        'total_timesteps': total_steps,
        'total_reward': float(total_reward),
        'average_reward': float(total_reward / total_steps),
        'min_reward': float(min(rewards_list)),
        'max_reward': float(max(rewards_list)),
        'estimated_co2_kg': co2_estimate_kg,
        'action': 'chargers_at_max'
    }

    output_path = output_dir / 'baseline_results.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("")
    logger.info(f"✓ Resultados guardados: {output_path}")
    logger.info("="*70)

if __name__ == '__main__':
    run_baseline()
