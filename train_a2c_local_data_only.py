#!/usr/bin/env python3
"""
A2C TRAINING - DATOS LOCALES OE2/OE3 + DEMANDA REAL MALL 2024
==============================================================

Entrena A2C usando:
- Datos generados en OE2 (solar, BESS, chargers reales de Iquitos)
- Datos procesados en OE3 (weather.csv, charger_simulation_*.csv, Building_*.csv)
- DEMANDA REAL DEL MALL 2024 (non_shiftable_load de Building_1.csv)
- NO descarga datos de CityLearn v2 template
- NO usa datos externos

⚠️  REQUERIMIENTO: Python 3.11 EXACTAMENTE
"""

import sys

# ========== VALIDAR PYTHON 3.11 ==========
if sys.version_info[:2] != (3, 11):
    version_str = f"{sys.version_info[0]}.{sys.version_info[1]}"
    print("\n" + "="*80)
    print("ERROR: PYTHON 3.11 REQUERIDO")
    print("="*80)
    print(f"Version actual: Python {version_str}")
    print(f"Version requerida: Python 3.11")
    print("\nPor favor ejecuta:")
    print("   python -m venv .venv")
    print("   .venv\\Scripts\\activate  (Windows)")
    print("   pip install -r requirements-training.txt")
    print("="*80 + "\n")
    sys.exit(1)

import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from pathlib import Path
from typing import Tuple

print("\n" + "="*80)
print("A2C TRAINING - LOCAL DATA ONLY (OE2/OE3)")
print(f"Python: {sys.version_info.major}.{sys.version_info.minor} OK")
print("="*80)

# ============================================================================
# CUSTOM GYMNASIUM ENVIRONMENT - SOLO DATOS LOCALES
# ============================================================================

class IquitosLocalEnv(gym.Env):
    """
    Gym environment que usa SOLO datos locales de OE2/OE3.
    Sin dependencias de CityLearn v2 template.
    """

    def __init__(self, data_dir: Path):
        super().__init__()

        self.data_dir = Path(data_dir)
        self.current_step = 0
        self.max_steps = 8760  # 1 año completo

        # Load local data files
        print(f"  Loading weather data...")
        self.weather = pd.read_csv(self.data_dir / "weather.csv").values

        print(f"  Loading charger data (128 chargers)...")
        self.chargers = []
        for i in range(1, 129):
            charger_file = self.data_dir / f"charger_simulation_{i:03d}.csv"
            if charger_file.exists():
                df = pd.read_csv(charger_file).values
                self.chargers.append(df)

        print(f"  Loading building load data (REAL MALL DEMAND 2024)...")
        self.building_df = pd.read_csv(self.data_dir / "Building_1.csv")
        # Extract non_shiftable_load (demanda real del mall)
        self.mall_demand = np.array(self.building_df['non_shiftable_load'].values, dtype=np.float32)
        self.building = self.building_df.values

        print(f"  Loading carbon intensity...")
        self.carbon_intensity = pd.read_csv(self.data_dir / "carbon_intensity.csv").values

        print(f"  Loading pricing...")
        self.pricing = pd.read_csv(self.data_dir / "pricing.csv").values

        # Validate shapes
        assert len(self.weather) == 8760, f"Weather: expected 8760, got {len(self.weather)}"
        assert len(self.chargers) == 128, f"Chargers: expected 128, got {len(self.chargers)}"
        assert len(self.building) == 8760, f"Building: expected 8760, got {len(self.building)}"
        assert len(self.mall_demand) == 8760, f"Mall demand: expected 8760, got {len(self.mall_demand)}"

        # Store max demand for normalization
        mall_max_val = float(np.max(self.mall_demand))
        self.mall_demand_max = mall_max_val if mall_max_val > 0 else 1.0
        # Observation space: weather (1) + chargers (128) + building (1) + mall_demand (1) + time features (4) = 135
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(135,), dtype=np.float32
        )

        # Action space: 128 chargers [0,1] (power setpoint normalized)
        self.action_space = spaces.Box(
            low=0, high=1, shape=(128,), dtype=np.float32
        )

        self.reward_sum = 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed, options=options)
        self.current_step = 0
        self.reward_sum = 0.0
        obs = self._get_observation()
        return obs, {}

    def _get_observation(self) -> np.ndarray:
        """Build observation vector from current timestep data"""
        t = self.current_step

        obs = []

        # Solar generation (normalized 0-1)
        solar = self.weather[t, 0] if self.weather.shape[1] > 0 else 0.0
        obs.append(np.clip(solar, 0, 1))

        # Charger demands (128 values)
        for charger_data in self.chargers:
            demand = charger_data[t, 0] if charger_data.shape[1] > 0 else 0.0
            obs.append(np.clip(demand / 10.0, 0, 1))  # Normalize to [0,1]

        # Building load (non-shiftable)
        building_load = self.building[t, 0] if self.building.shape[1] > 0 else 0.0
        obs.append(np.clip(building_load / 100.0, 0, 1))  # Normalize

        # Mall demand (REAL 2024) - NEW!
        mall_demand_norm = self.mall_demand[t] / self.mall_demand_max
        obs.append(np.clip(mall_demand_norm, 0, 1))

        # Time features
        hour = (t % 24) / 24.0
        day_of_year = (t // 24) / 365.0
        is_peak = 1.0 if (t % 24) in [17, 18, 19, 20, 21] else 0.0  # Peak hours

        obs.extend([hour, day_of_year, is_peak, 0.0])  # 4 time features

        return np.array(obs, dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one timestep with REAL MALL DEMAND from 2024"""
        t = self.current_step

        # Real data
        solar = self.weather[t, 0] if self.weather.shape[1] > 0 else 0.0
        mall_demand = self.mall_demand[t]  # REAL 2024 MALL DEMAND

        # EV demand (sum of all chargers)
        ev_demand = sum(
            charger_data[t, 0] if charger_data.shape[1] > 0 else 0.0
            for charger_data in self.chargers
        )

        # Total demand = mall + EV chargers
        total_demand = mall_demand + ev_demand

        # Agent action: charge EVs based on action
        charger_power = np.sum(action) * 10.0  # Scale action to kW

        # Energy balance
        available_power = solar + charger_power  # Solar + charging action
        grid_import = max(0, total_demand - solar)  # If demand > solar, import from grid

        # Reward components:

        # 1. SOLAR USAGE (minimize grid dependence)
        solar_used = min(solar, total_demand)
        r_solar_usage = solar_used / max(total_demand, 1.0)

        # 2. DEMAND SATISFACTION (satisfy mall + EV demand)
        demand_satisfied = min(available_power, total_demand)
        r_demand_satisfaction = demand_satisfied / max(total_demand, 1.0)

        # 3. CO2 PENALTY (grid import causes emissions)
        # Iquitos: 0.4521 kg CO2/kWh
        r_co2_penalty = -grid_import * 0.4521 * 0.001  # Scaled penalty

        # 4. PEAK HOUR BONUS (prioritize charging during peak sun)
        is_peak_sun = 1.0 if 8 <= (t % 24) <= 16 else 0.0
        r_peak_bonus = is_peak_sun * 0.05 if charger_power > 0 else 0.0

        # 5. EFFICIENCY (minimize waste)
        if solar > 0:
            solar_efficiency = min(charger_power, solar) / solar
        else:
            solar_efficiency = 0.0
        r_efficiency = solar_efficiency * 0.05

        # Combined reward (weighted)
        reward = (
            0.40 * r_solar_usage +      # Primary: maximize solar usage
            0.35 * r_demand_satisfaction +  # Secondary: satisfy real demand
            0.15 * r_co2_penalty +      # Tertiary: minimize CO2
            0.05 * r_peak_bonus +       # Bonus: use solar when abundant
            0.05 * r_efficiency         # Bonus: efficient solar utilization
        )

        self.reward_sum += reward
        self.current_step += 1

        done = self.current_step >= self.max_steps
        truncated = False

        obs = self._get_observation() if not done else np.zeros(135, dtype=np.float32)

        info = {
            "step": self.current_step,
            "solar": float(solar),
            "mall_demand": float(mall_demand),
            "ev_demand": float(ev_demand),
            "grid_import": float(grid_import),
            "reward": float(reward)
        }

        return obs, float(reward), done, truncated, info

# ============================================================================
# MAIN TRAINING
# ============================================================================

print("\n[1/4] VERIFYING LOCAL DATA...")
print("-" * 80)

data_dir = Path("data/processed/citylearn/iquitos_ev_mall")
if not data_dir.exists():
    print(f"ERROR: Data directory not found: {data_dir}")
    sys.exit(1)

# Check files exist
required_files = [
    "weather.csv",
    "Building_1.csv",
    "carbon_intensity.csv",
    "pricing.csv",
] + [f"charger_simulation_{i:03d}.csv" for i in range(1, 129)]

missing = [f for f in required_files if not (data_dir / f).exists()]
if missing:
    print(f"ERROR: Missing files: {missing[:5]}...")
    sys.exit(1)

print(f"  OK - All required files present")
print(f"  Data directory: {data_dir}")
print(f"  Files: 128 chargers + weather + building + carbon + pricing")

print("\n[2/4] CREATING CUSTOM GYM ENVIRONMENT (REAL MALL DEMAND 2024)...")
print("-" * 80)

try:
    env = IquitosLocalEnv(data_dir)
    obs, info = env.reset()
    print(f"  OK - Environment created")
    print(f"  Observation shape: {obs.shape}")
    print(f"  Action space: {env.action_space}")
except Exception as e:
    print(f"ERROR creating environment: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[3/4] CREATING A2C AGENT (GPU MAX)...")
print("-" * 80)

try:
    from stable_baselines3 import A2C
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device.upper()}")

    agent = A2C(
        policy="MlpPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=512,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.001,
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_rms_prop=True,
        verbose=1,
        device=device
    )

    print(f"  OK - A2C agent created")
    print(f"  Learning rate: 3e-4")
    print(f"  Batch size: 512")

except Exception as e:
    print(f"ERROR creating agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[4/4] TRAINING A2C (8760 TIMESTEPS = 1 YEAR REAL MALL DATA)...")
print("-" * 80)
print()
print("  DATA SOURCE:")
print("    • Generado en OE2 (solar real Iquitos, BESS, chargers)")
print("    • Procesado en OE3 (weather.csv, charger_simulation_*.csv)")
print("    • ★ DEMANDA REAL MALL 2024 (non_shiftable_load de Building_1.csv)")
print("    • NO usa datos de CityLearn v2 template")
print("    • 128 chargers × 8760 horas + mall demand histórico")
print()
print("  REWARD FUNCTION (5 componentes):")
print("    • Solar usage (0.40): maximizar uso directo de solar")
print("    • Demand satisfaction (0.35): satisfacer demanda real mall + EV")
print("    • CO2 penalty (0.15): penalizar importación grid (0.4521 kg CO2/kWh)")
print("    • Peak bonus (0.05): incentivar carga durante pico solar")
print("    • Efficiency (0.05): maximizar eficiencia solar")
print()
print("  TRAINING PARAMETERS:")
print("    • Timesteps: 8,760 (1 año completo)")
print("    • Learning rate: 3e-4")
print("    • Batch size: 512")
print("    • Observation space: 135 dims (incluye mall demand)")
print("    • Action space: 128 dims (charger power setpoints)")
print()
print("-" * 80)
print()

try:
    agent.learn(total_timesteps=8760, log_interval=100)

    print()
    print("="*80)
    print("SUCCESS - A2C TRAINING COMPLETED (REAL MALL 2024 DEMAND)!")
    print("="*80)
    print()

    # Save checkpoint
    checkpoint_dir = Path("checkpoints/A2C")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / "a2c_mall_demand_2024"
    agent.save(str(checkpoint_file))

    print(f"Checkpoint: {checkpoint_file}.zip")
    print(f"Model trained with REAL mall demand from 2024")
    print(f"Observation: 135 dims (includes real mall demand)")
    print(f"Logs: logs/a2c/")
    print()

except KeyboardInterrupt:
    print("\n\nTraining interrupted by user")
    sys.exit(0)

except Exception as e:
    print(f"\nERROR during training: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
