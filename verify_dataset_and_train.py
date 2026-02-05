#!/usr/bin/env python3
"""
Verificación rápida del dataset + Lanzar SAC training
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Validar Python 3.11
if sys.version_info[:2] != (3, 11):
    print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} detectado (requiere 3.11)")
    sys.exit(1)

print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")

# Setup paths
project_root = Path(__file__).resolve().parents[0]
os.chdir(project_root)
sys.path.insert(0, str(project_root / "src"))

# ============================================================================
# STEP 1: VERIFICAR DATASET
# ============================================================================
print("\n" + "="*80)
print("STEP 1: VERIFICAR DATASET OE3")
print("="*80)

dataset_dir = project_root / "data/interim/oe3"
solar_csv = dataset_dir / "pv_generation_timeseries.csv"
chargers_dir = dataset_dir / "chargers"

print(f"\n✓ Dataset dir: {dataset_dir}")
print(f"  Existe: {dataset_dir.exists()}")

print(f"\n✓ pv_generation_timeseries.csv: {solar_csv}")
print(f"  Existe: {solar_csv.exists()}")
print(f"  Tamaño: {solar_csv.stat().st_size if solar_csv.exists() else 'N/A'} bytes")

print(f"\n✓ Chargers dir: {chargers_dir}")
print(f"  Existe: {chargers_dir.exists()}")

# Contar charger CSVs
charger_files = list(chargers_dir.glob("charger_*.csv")) if chargers_dir.exists() else []
print(f"\n✓ Archivos charger_*.csv: {len(charger_files)}")
if len(charger_files) > 0:
    print(f"  Primero: {charger_files[0].name}")
    print(f"  Último: {charger_files[-1].name}")

# ============================================================================
# STEP 2: VALIDAR DATOS SOLAR Y CHARGERS
# ============================================================================
print("\n" + "="*80)
print("STEP 2: VALIDAR DATOS OE3")
print("="*80)

try:
    import pandas as pd
    import numpy as np

    # Validar solar data
    if solar_csv.exists():
        solar_df = pd.read_csv(solar_csv)
        print(f"\n✅ Solar timeseries cargado: {len(solar_df)} filas")
        print(f"  Columnas: {list(solar_df.columns)}")
        if 'potencia_kw' in solar_df.columns:
            print(f"  Potencia promedio: {solar_df['potencia_kw'].mean():.2f} kW")
            print(f"  Potencia máxima: {solar_df['potencia_kw'].max():.2f} kW")
        elif 'power_kw' in solar_df.columns:
            print(f"  Potencia promedio: {solar_df['power_kw'].mean():.2f} kW")
            print(f"  Potencia máxima: {solar_df['power_kw'].max():.2f} kW")
    else:
        print(f"❌ Solar data no encontrado")
        sys.exit(1)

    # Validar chargers
    if charger_files:
        sample_charger = pd.read_csv(charger_files[0])
        print(f"\n✅ Chargers validados: {len(charger_files)} archivos")
        print(f"  Columnas: {list(sample_charger.columns)}")
        print(f"  Filas por charger: {len(sample_charger)}")
    else:
        print(f"⚠️ No hay archivos de chargers (se usará configuración por defecto)")

    print("\n✅ DATASET OE3 VALIDADO CORRECTAMENTE")

except Exception as e:
    print(f"\n❌ Error validando dataset: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# STEP 3: LANZAR ENTRENAMIENTO SAC
# ============================================================================
print("\n" + "="*80)
print("STEP 3: LANZAR ENTRENAMIENTO SAC")
print("="*80)

try:
    import yaml
    import gymnasium as gym
    from src.agents.sac import make_sac, SACConfig

    # Cargar configuración
    config_path = project_root / "configs/default.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("✅ Configuración cargada")

    # Crear environment compatible con SAC
    print("\nCreando environment de entrenamiento...")

    class IquitosEVEnv(gym.Env):
        """Environment EV charging para Iquitos con datos OE3."""

        def __init__(self, solar_data: np.ndarray, n_chargers: int = 128):
            super().__init__()
            self.solar_data = solar_data
            self.n_chargers = n_chargers
            self.timesteps = len(solar_data)
            self.current_step = 0

            # Observation: [solar_power, hour, day_type, soc_bess, charger_states...]
            # 394 dim = 1 solar + 2 time + 1 bess_soc + 128*3 charger_states + 3 extra
            self.observation_space = gym.spaces.Box(
                low=-np.inf, high=np.inf, shape=(394,), dtype=np.float32
            )

            # Action: 1 BESS + 128 chargers = 129 actions [0,1]
            self.action_space = gym.spaces.Box(
                low=0.0, high=1.0, shape=(129,), dtype=np.float32
            )

            # CO2 factor Iquitos
            self.co2_factor = 0.4521  # kg CO2/kWh

        def reset(self, seed=None):
            super().reset(seed=seed)
            self.current_step = 0
            return self._get_obs(), {}

        def _get_obs(self):
            obs = np.zeros(394, dtype=np.float32)
            # Solar power normalized
            solar_kw = self.solar_data[self.current_step % self.timesteps]
            obs[0] = solar_kw / 5000.0  # Normalize by max ~5MW
            # Hour sin/cos
            hour = self.current_step % 24
            obs[1] = np.sin(2 * np.pi * hour / 24)
            obs[2] = np.cos(2 * np.pi * hour / 24)
            # BESS SOC
            obs[3] = 0.5 + np.random.randn() * 0.1
            # Charger states (random for now)
            obs[4:] = np.random.randn(390) * 0.1
            return obs

        def step(self, action):
            self.current_step += 1

            # Convertir action a numpy array si es lista
            if isinstance(action, list):
                action = np.array(action[0] if len(action) == 1 and isinstance(action[0], (list, np.ndarray)) else action)
            action = np.asarray(action).flatten()

            # Get solar power
            solar_kw = self.solar_data[(self.current_step - 1) % self.timesteps]

            # EV demand: 50 kW constant
            ev_demand = 50.0

            # BESS action: charge/discharge
            bess_action = (action[0] - 0.5) * 600  # ±300 kW

            # Charger actions: sum of charging power
            charger_power = np.sum(action[1:]) * 10.0  # Max 10 kW per charger

            # Grid import = demand - solar - bess_discharge
            grid_import = max(0, ev_demand + charger_power - solar_kw + bess_action)

            # CO2 reward (negative = good when low)
            co2_kg = grid_import * self.co2_factor / 1000  # Per hour
            reward = -co2_kg * 10  # Scale reward

            # Solar utilization bonus
            solar_used = min(solar_kw, ev_demand + charger_power)
            reward += solar_used / 1000  # Bonus for using solar

            obs = self._get_obs()
            terminated = self.current_step >= self.timesteps
            truncated = False

            return obs, float(reward), terminated, truncated, {
                "grid_import_kwh": grid_import,
                "solar_kw": solar_kw,
                "co2_kg": co2_kg
            }

        def render(self):
            pass

    # Cargar datos solares
    if 'potencia_kw' in solar_df.columns:
        solar_power = solar_df['potencia_kw'].values
    elif 'power_kw' in solar_df.columns:
        solar_power = solar_df['power_kw'].values
    else:
        solar_power = solar_df.iloc[:, 3].values  # Assume 4th column

    env = IquitosEVEnv(solar_power, n_chargers=128)
    print(f"✅ Environment creado:")
    print(f"  Observation space: {env.observation_space.shape}")
    print(f"  Action space: {env.action_space.shape}")
    print(f"  Timesteps: {env.timesteps}")

    # Configurar SAC
    episodes = 3  # Start with 3 episodes for quick test
    sac_config = SACConfig(
        episodes=episodes,
        learning_rate=5e-5,
        checkpoint_dir=str(project_root / "checkpoints/SAC"),
        progress_path=str(project_root / "outputs/sac_progress.csv")
    )

    print(f"\nParámetros SAC:")
    print(f"  Episodes: {episodes}")
    print(f"  Learning rate: {sac_config.learning_rate}")
    print(f"  Checkpoint dir: {sac_config.checkpoint_dir}")

    # Crear directorios
    if sac_config.checkpoint_dir:
        Path(sac_config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    if sac_config.progress_path:
        Path(sac_config.progress_path).parent.mkdir(parents=True, exist_ok=True)

    # Crear y entrenar agente
    print("\n🚀 Creando agente SAC...")
    agent = make_sac(env, sac_config)

    print("\n" + "="*80)
    print("🚀 INICIANDO ENTRENAMIENTO SAC")
    print("="*80)

    agent.learn(episodes=episodes)

    print("\n" + "="*80)
    print("✅ ENTRENAMIENTO SAC COMPLETADO")
    print("="*80)
    print(f"\nCheckpoint guardado en: {sac_config.checkpoint_dir}")
    print(f"Progress CSV: {sac_config.progress_path}")

except Exception as e:
    print(f"\n❌ Error en entrenamiento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ PIPELINE COMPLETADO EXITOSAMENTE\n")
sys.exit(0)
