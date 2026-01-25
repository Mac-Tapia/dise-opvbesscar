#!/usr/bin/env python3
"""
ENTRENAMIENTO DIRECTO: Sin CityLearn wrapper
Entrena agentes RL directamente con datos OE2 (Solar + Chargers + Mall)
"""

import sys
import logging
from pathlib import Path
import numpy as np
import time

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    from stable_baselines3 import SAC, PPO, A2C
    import gymnasium as gym
    from gymnasium import spaces
    logger.info("✓ Dependencias OK")
except ImportError as e:
    logger.error(f"✗ {e}")
    sys.exit(1)

from iquitos_citylearn.config import load_config, load_paths


class SimpleEnergyEnv(gym.Env):
    """Ambiente simple para entrenar agentes con datos OE2."""

    metadata = {'render_modes': ['human']}

    def __init__(self, data_dir: Path):
        """Cargar datos OE2."""
        super().__init__()

        import pandas as pd

        # Cargar datos
        self.solar = pd.read_csv(data_dir / "solar_generation_hourly.csv")['kW'].values
        self.chargers = pd.read_csv(data_dir / "chargers_demand_hourly.csv").values
        self.mall = pd.read_csv(data_dir / "mall_demand_hourly.csv")['kW'].values

        self.n_chargers = self.chargers.shape[1]
        self.n_hours = len(self.solar)

        # Espacios
        obs_size = 1 + 1 + 1 + self.n_chargers + 5  # solar + chargers_demand + mall + charger_states + time_features
        self.observation_space = spaces.Box(low=-1000, high=10000, shape=(obs_size,), dtype=np.float32)
        self.action_space = spaces.Box(low=0, high=1, shape=(self.n_chargers,), dtype=np.float32)

        self.current_step = 0
        self.episode_reward = 0

    def reset(self, seed=None):
        """Reset ambiente."""
        super().reset(seed=seed)
        self.current_step = 0
        self.episode_reward = 0
        return self._get_obs(), {}

    def _get_obs(self):
        """Observación actual."""
        h = self.current_step % self.n_hours

        # Características básicas
        solar = self.solar[h]
        chargers_demand = self.chargers[h].sum()
        mall = self.mall[h]
        hour_of_day = h % 24

        # Construir observación
        obs = np.concatenate([
            [solar],
            [chargers_demand],
            [mall],
            self.chargers[h],
            [hour_of_day, hour_of_day/24, h/self.n_hours, 1.0 if 18<=hour_of_day or hour_of_day<6 else 0, 0.5]
        ]).astype(np.float32)

        return obs

    def step(self, action):
        """Un paso de simulación."""
        h = self.current_step % self.n_hours

        # Demanda
        chargers_demand = self.chargers[h].sum()
        mall_demand = self.mall[h]
        solar = self.solar[h]

        # Control: acción controla disponibilidad de carga a chargers
        action_clipped = np.clip(action, 0, 1)
        chargers_supply = chargers_demand * action_clipped.mean()  # Simplificado

        # Balance
        total_demand = chargers_demand + mall_demand
        available_solar = solar
        grid_import = max(0, total_demand - available_solar - chargers_supply)

        # Recompensa multiobjetivo
        co2_intensity = 0.4521  # kg CO2/kWh
        co2_emissions = grid_import * co2_intensity / 1000  # to tonnes

        cost = grid_import * 0.2  # $0.2/kWh

        solar_utilization = (available_solar - max(0, available_solar - chargers_supply)) / (available_solar + 0.1)

        # Combinar recompensas (multiobjetivo)
        reward = (
            -0.50 * co2_emissions +  # 50% CO2
            0.20 * solar_utilization +  # 20% solar
            -0.10 * cost / 1000 +  # 10% cost
            0.10 * (1 - max(0, chargers_demand - chargers_supply) / (chargers_demand + 0.1)) +  # 10% EV satisfaction
            0.10 * (1 - grid_import / (total_demand + 0.1))  # 10% grid stability
        )

        self.episode_reward += reward
        self.current_step += 1

        terminated = self.current_step >= self.n_hours

        return self._get_obs(), reward, terminated, False, {
            "co2": co2_emissions,
            "cost": cost,
            "grid_import": grid_import,
        }

    def render(self):
        pass

    def close(self):
        pass


def train_agents(episodes: int = 5):
    """Entrenar 3 agentes."""

    logger.info("\n" + "="*70)
    logger.info(f"ENTRENAMIENTO: 3 AGENTES × {episodes} EPISODIOS")
    logger.info("="*70 + "\n")

    # Paths
    cfg = load_config()
    paths = load_paths(cfg)
    data_dir = paths.processed_dir / "dataset"

    if not data_dir.exists():
        logger.error(f"✗ Dataset no encontrado: {data_dir}")
        return False

    # Crear ambiente
    try:
        env = SimpleEnergyEnv(data_dir)
        logger.info(f"✓ Ambiente creado")
        logger.info(f"  Obs: {env.observation_space.shape}")
        logger.info(f"  Act: {env.action_space.shape}")
    except Exception as e:
        logger.error(f"✗ {e}")
        return False

    # Parámetros
    total_steps = episodes * 8760
    checkpoint_dir = ROOT / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # SAC
    logger.info("\n" + "="*70)
    logger.info("FASE 1: SAC (Soft Actor-Critic)")
    logger.info("="*70)
    try:
        t0 = time.time()
        model = SAC("MlpPolicy", env, learning_rate=3e-4, verbose=0)
        logger.info(f"▶ Entrenando: {total_steps:,} steps...")
        model.learn(total_timesteps=total_steps)
        elapsed = time.time() - t0
        model.save(checkpoint_dir / "SAC" / "model.zip")
        logger.info(f"✓ SAC: {elapsed/60:.1f} min")
        results["SAC"] = elapsed
    except Exception as e:
        logger.error(f"✗ SAC: {e}")
        results["SAC"] = None

    env.reset()

    # PPO
    logger.info("\n" + "="*70)
    logger.info("FASE 2: PPO (Proximal Policy Optimization)")
    logger.info("="*70)
    try:
        t0 = time.time()
        model = PPO("MlpPolicy", env, learning_rate=3e-4, verbose=0)
        logger.info(f"▶ Entrenando: {total_steps:,} steps...")
        model.learn(total_timesteps=total_steps)
        elapsed = time.time() - t0
        model.save(checkpoint_dir / "PPO" / "model.zip")
        logger.info(f"✓ PPO: {elapsed/60:.1f} min")
        results["PPO"] = elapsed
    except Exception as e:
        logger.error(f"✗ PPO: {e}")
        results["PPO"] = None

    env.reset()

    # A2C
    logger.info("\n" + "="*70)
    logger.info("FASE 3: A2C (Advantage Actor-Critic)")
    logger.info("="*70)
    try:
        t0 = time.time()
        model = A2C("MlpPolicy", env, learning_rate=7e-4, verbose=0)
        logger.info(f"▶ Entrenando: {total_steps:,} steps...")
        model.learn(total_timesteps=total_steps)
        elapsed = time.time() - t0
        model.save(checkpoint_dir / "A2C" / "model.zip")
        logger.info(f"✓ A2C: {elapsed/60:.1f} min")
        results["A2C"] = elapsed
    except Exception as e:
        logger.error(f"✗ A2C: {e}")
        results["A2C"] = None

    # Resumen
    logger.info("\n" + "="*70)
    logger.info("RESUMEN")
    logger.info("="*70)

    total_time = sum(t for t in results.values() if t)
    for agent, elapsed in results.items():
        if elapsed:
            logger.info(f"{agent}: {elapsed/60:6.1f} min ✓")
        else:
            logger.info(f"{agent}: ERROR ✗")

    logger.info(f"TOTAL: {total_time/60:.1f} min\n")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()

    success = train_agents(args.episodes)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
