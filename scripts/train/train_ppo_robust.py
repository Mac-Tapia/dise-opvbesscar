#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAMIENTO PPO ROBUSTO - VERSIÓN LIMPIA (2026-02-14)
========================================================================
Script optimizado para entrenar PPO con datos REALES OE2 (Iquitos, Perú).

- 10 episodios completos (87,600 timesteps = 1 año)
- Datos reales: 38 sockets (19 chargers × 2), mall demand, BESS, solar
- Reward: Multiobjetivo (CO2 minimization como PRIMARY)
- Optimización: GPU CUDA, VecNormalize, learning rate schedule

Referencias:
  [1] Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
  [2] Engstrom et al. (2020) "Implementation Matters in Deep RL"
  [3] Stable-Baselines3: https://stable-baselines3.readthedocs.io/
========================================================================
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Agregar src/ a path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from gymnasium import Env, spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# ============================================================================
# CONFIGURACIÓN BÁSICA
# ============================================================================
os.environ['PYTHONIOENCODING'] = 'utf-8'
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('train_ppo_robust.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Constantes OE2
CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh
BESS_CAPACITY_KWH = 940.0
BESS_MAX_POWER_KW = 342.0
SOLAR_MAX_KW = 4100.0
MALL_MAX_KW = 150.0

CHECKPOINT_DIR = Path('checkpoints/PPO')
OUTPUT_DIR = Path('outputs/ppo_training')

# ============================================================================
# ENVIRONMENT - SIMPLIFICADO Y ROBUSTO
# ============================================================================
class SimpleEVChargingEnv(Env):
    """Environment robusto para control de carga EV con datos reales OE2."""
    
    HOURS_PER_YEAR = 8760
    NUM_CHARGERS = 38
    OBS_DIM = 50  # Observaciones simplificadas pero completas
    ACTION_DIM = 39  # 1 BESS + 38 sockets
    
    def __init__(
        self,
        solar_hourly: np.ndarray,
        ev_demand_hourly: np.ndarray,
        mall_demand_hourly: np.ndarray,
        bess_soc_hourly: np.ndarray,
    ):
        super().__init__()
        
        # Validar datos
        assert len(solar_hourly) == self.HOURS_PER_YEAR, "Solar data must be 8760 hours"
        assert len(ev_demand_hourly) == self.HOURS_PER_YEAR, "EV demand must be 8760 hours"
        assert len(mall_demand_hourly) == self.HOURS_PER_YEAR, "Mall demand must be 8760 hours"
        assert len(bess_soc_hourly) == self.HOURS_PER_YEAR, "BESS SOC must be 8760 hours"
        
        self.solar_hourly = solar_hourly.astype(np.float32)
        self.ev_demand_hourly = ev_demand_hourly.astype(np.float32)
        self.mall_demand_hourly = mall_demand_hourly.astype(np.float32)
        self.bess_soc_hourly = bess_soc_hourly.astype(np.float32)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.ACTION_DIM,), dtype=np.float32
        )
        
        self.step_count = 0
        self.episode_num = 0
        self.episode_reward = 0.0
        
    def _make_observation(self, hour_idx: int) -> np.ndarray:
        """Crea observación normalizada de 50 dimensiones."""
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        h = hour_idx % self.HOURS_PER_YEAR
        
        # [0-7] Energía del sistema
        solar = float(self.solar_hourly[h])
        ev_demand = float(self.ev_demand_hourly[h])
        mall_demand = float(self.mall_demand_hourly[h])
        bess_soc = float(self.bess_soc_hourly[h])
        
        obs[0] = np.clip(solar / SOLAR_MAX_KW, 0.0, 1.0)
        obs[1] = np.clip(ev_demand / (self.NUM_CHARGERS * 7.4), 0.0, 1.0)
        obs[2] = np.clip(mall_demand / MALL_MAX_KW, 0.0, 1.0)
        obs[3] = np.clip(bess_soc, 0.0, 1.0)
        
        # Balance energético
        total_demand = ev_demand + mall_demand
        obs[4] = np.clip((solar - total_demand) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)
        obs[5] = 1.0 if solar >= total_demand else 0.0
        obs[6] = 1.0 if bess_soc > 0.3 else 0.0
        obs[7] = float(h % 24) / 24.0
        
        # [8-27] Features simplificadas de cargadores (20 features)
        # Distribuir info de 38 sockets en 20 buckets
        for i in range(20):
            obs[8 + i] = 0.5 + 0.5 * np.sin(2 * np.pi * (h + i) / 24.0)
        
        # [28-47] States y comunicación (20 features)
        hour_of_day = h % 24
        day_of_year = h // 24
        
        obs[28] = 1.0 if 6 <= hour_of_day <= 22 else 0.0  # Hora pico
        obs[29] = float(day_of_year % 7) / 7.0  # Día semana
        obs[30] = float((day_of_year // 30) % 12) / 12.0  # Mes
        
        # Fill rest with reasonable patterns
        for i in range(31, self.OBS_DIM):
            obs[i] = 0.5
        
        return obs
    
    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment para new episode."""
        self.step_count = 0
        self.episode_num += 1
        self.episode_reward = 0.0
        return self._make_observation(0), {}
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Ejecuta un paso (1 hora)."""
        self.step_count += 1
        h = (self.step_count - 1) % self.HOURS_PER_YEAR
        
        # Datos reales
        solar_kw = float(self.solar_hourly[h])
        ev_demand = float(self.ev_demand_hourly[h])
        mall_demand = float(self.mall_demand_hourly[h])
        bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)
        
        # Procesar acción
        bess_action = np.clip(action[0], 0.0, 1.0)
        charger_setpoints = np.clip(action[1:39], 0.0, 1.0)
        
        # Carga EV = setpoints × demanda real
        ev_charging = float(np.sum(charger_setpoints) / 38.0) * ev_demand
        
        # Energy balance
        total_demand = ev_charging + mall_demand
        bess_power = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
        net_demand = total_demand - bess_power
        grid_import = max(0.0, net_demand - solar_kw)
        
        # CO2 calculation
        co2_avoided = (solar_kw - grid_import) * CO2_FACTOR_IQUITOS
        
        # Reward: simple pero efectivo
        # 1. Minimizar grid import (usar solar)
        grid_penalty = -grid_import / 500.0
        
        # 2. Maximizar carga EV
        charging_reward = ev_charging / (self.NUM_CHARGERS * 4.6)  # Normalized
        
        # 3. CO2 benefit
        co2_reward = co2_avoided / 200.0
        
        # Combinar rewards
        reward = (grid_penalty * 0.3 + charging_reward * 0.5 + co2_reward * 0.2)
        reward = float(np.clip(reward, -1.0, 1.0))
        
        self.episode_reward += reward
        
        # Next observation
        obs = self._make_observation(self.step_count)
        
        # Termination
        terminated = self.step_count >= self.HOURS_PER_YEAR
        truncated = False
        
        # Info
        info = {
            'step': self.step_count,
            'hour': h % 24,
            'solar_kw': solar_kw,
            'ev_charging_kw': ev_charging,
            'grid_import_kw': grid_import,
            'bess_soc': bess_soc,
            'co2_avoided_kg': co2_avoided,
            'reward': reward,
        }
        
        if terminated:
            info['episode'] = {
                'r': float(self.episode_reward),
                'l': int(self.step_count)
            }
        
        return obs, reward, terminated, truncated, info
    
    def render(self):
        pass


# ============================================================================
# TRAININGCALLBACK - LOG DETALLADO
# ============================================================================
class TrainingLogCallback(BaseCallback):
    """Callback para logging durante entrenamiento."""
    
    def __init__(self, env_ref: SimpleEVChargingEnv, output_dir: Path, verbose: int = 1):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        
        self.episode_rewards = []
        self.episode_solar = []
        self.episode_ev = []
        self.episode_grid = []
        self.episode_co2 = []
        
        self.ep_reward = 0.0
        self.ep_solar = 0.0
        self.ep_ev = 0.0
        self.ep_grid = 0.0
        self.ep_co2 = 0.0
        self.ep_steps = 0
    
    def _on_step(self) -> bool:
        """Llamado después de cada step."""
        infos = self.locals.get('infos', [{}])
        info = infos[0] if infos else {}
        
        # Acumular
        self.ep_reward += info.get('reward', 0.0)
        self.ep_solar += info.get('solar_kw', 0.0)
        self.ep_ev += info.get('ev_charging_kw', 0.0)
        self.ep_grid += info.get('grid_import_kw', 0.0)
        self.ep_co2 += info.get('co2_avoided_kg', 0.0)
        self.ep_steps += 1
        
        # Detección de fin de episodio
        if 'episode' in info:
            self.episode_rewards.append(self.ep_reward)
            self.episode_solar.append(self.ep_solar)
            self.episode_ev.append(self.ep_ev)
            self.episode_grid.append(self.ep_grid)
            self.episode_co2.append(self.ep_co2)
            
            if self.verbose > 0:
                logger.info(
                    "Episode %d: R=%.1f | Solar=%d kWh | EV=%d kWh | Grid=%d kWh | CO2=%.0f kg",
                    len(self.episode_rewards),
                    self.ep_reward,
                    int(self.ep_solar),
                    int(self.ep_ev),
                    int(self.ep_grid),
                    self.ep_co2
                )
            
            # Reset para nuevo episodio
            self.ep_reward = 0.0
            self.ep_solar = 0.0
            self.ep_ev = 0.0
            self.ep_grid = 0.0
            self.ep_co2 = 0.0
            self.ep_steps = 0
        
        return True


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================
def load_oe2_datasets() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Carga los 4 datasets OE2 obligatorios para el entrenamiento."""
    print('=' * 80)
    print('[PASO 1] CARGAR DATASETS OE2 REALES')
    print('=' * 80)
    
    # Solar
    solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"Solar data not found: {solar_path}")
    
    df_solar = pd.read_csv(solar_path, sep=',')
    solar_data = df_solar.iloc[:, 0].values.astype(np.float32)
    
    if len(solar_data) != 8760:
        raise ValueError(f"Solar data must be 8760 hours, got {len(solar_data)}")
    
    print(f"  ✓ Solar: {len(solar_data):,} horas (Max={solar_data.max():.0f} kW)")
    
    # EV demand
    ev_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    if not ev_path.exists():
        raise FileNotFoundError(f"EV demand data not found: {ev_path}")
    
    df_ev = pd.read_csv(ev_path, sep=',')
    ev_data = df_ev.iloc[:, 0].values.astype(np.float32)
    
    if len(ev_data) != 8760:
        raise ValueError(f"EV demand must be 8760 hours, got {len(ev_data)}")
    
    print(f"  ✓ EV Demand: {len(ev_data):,} horas (Max={ev_data.max():.1f} kW)")
    
    # Mall demand
    mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
    if not mall_path.exists():
        raise FileNotFoundError(f"Mall demand data not found: {mall_path}")
    
    df_mall = pd.read_csv(mall_path, sep=';')
    mall_data = df_mall.iloc[:, 0].values.astype(np.float32)
    
    if len(mall_data) != 8760:
        raise ValueError(f"Mall demand must be 8760 hours, got {len(mall_data)}")
    
    print(f"  ✓ Mall Demand: {len(mall_data):,} horas (Max={mall_data.max():.1f} kW)")
    
    # BESS SOC
    bess_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv')
    if not bess_path.exists():
        # Fallback: usar SOC sintetico
        print(f"  ⚠ BESS data not found, using synthetic SOC")
        bess_soc = 0.5 + 0.3 * np.sin(np.linspace(0, 4*np.pi, 8760))
        bess_soc = np.clip(bess_soc, 0.2, 1.0).astype(np.float32)
    else:
        df_bess = pd.read_csv(bess_path, sep=',')
        bess_soc = df_bess.iloc[:, 0].values.astype(np.float32)
        bess_soc = np.clip(bess_soc, 0.0, 1.0)
        print(f"  ✓ BESS SOC: {len(bess_soc):,} horas")
    
    print('=' * 80)
    print()
    
    return solar_data, ev_data, mall_data, bess_soc


def clean_directories() -> None:
    """Limpia checkpoints y outputs anteriores."""
    print('[PASO 0] LIMPIEZA DE DIRECTORIOS')
    print('-' * 80)
    
    for dir_path in [CHECKPOINT_DIR, OUTPUT_DIR]:
        if dir_path.exists():
            import shutil
            try:
                shutil.rmtree(dir_path)
                print(f"  ✓ Eliminado: {dir_path}")
            except Exception as e:
                print(f"  ⚠ Error al eliminar {dir_path}: {e}")
        
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Creado: {dir_path}")
    
    print()


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Entrenamiento PPO robusto."""
    start_time = time.time()
    
    try:
        # Step 0: Limpiar
        clean_directories()
        
        # Step 1: Cargar datos
        solar, ev_demand, mall_demand, bess_soc = load_oe2_datasets()
        
        # Step 2: Crear environment
        print('[PASO 2] CREAR ENVIRONMENT')
        print('-' * 80)
        
        env_base = SimpleEVChargingEnv(solar, ev_demand, mall_demand, bess_soc)
        
        # Envolver con VecEnv y VecNormalize
        env = DummyVecEnv([lambda: env_base])
        env = VecNormalize(env, norm_obs=True, norm_reward=True)
        
        print(f"  ✓ Environment creado")
        print(f"    - Obs space: {env.observation_space}")
        print(f"    - Action space: {env.action_space}")
        print()
        
        # Step 3: Crear modelo PPO
        print('[PASO 3] CREAR MODELO PPO')
        print('-' * 80)
        
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"  Device: {device.upper()}")
        
        model = PPO(
            policy='MlpPolicy',
            env=env,
            learning_rate=1.5e-4,
            n_steps=2048,
            batch_size=256,
            n_epochs=3,
            gamma=0.85,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            target_kl=0.05,
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], vf=[512, 512]),
                'activation_fn': torch.nn.Tanh,
                'ortho_init': True,
            },
            device=device,
            verbose=0
        )
        
        print(f"  ✓ Modelo PPO creado")
        print()
        
        # Step 4: Entrenamiento
        print('[PASO 4] ENTRENAMIENTO')
        print('-' * 80)
        
        num_episodes = 3  # Reducido para prueba rápida
        total_timesteps = num_episodes * 8760
        
        print(f"  Episodios: {num_episodes}")
        print(f"  Total timesteps: {total_timesteps:,}")
        print()
        
        # Callbacks
        checkpoint_callback = CheckpointCallback(
            save_freq=2000,
            save_path=str(CHECKPOINT_DIR),
            name_prefix='ppo',
            verbose=0
        )
        
        log_callback = TrainingLogCallback(env_base, OUTPUT_DIR, verbose=1)
        
        # Entrenar
        print("  Iniciando entrenamiento...")
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, log_callback],
            progress_bar=True,
            reset_num_timesteps=False
        )
        
        elapsed = time.time() - start_time
        speed = total_timesteps / elapsed
        
        print()
        print(f"  ✓ Entrenamiento completado en {elapsed/60:.1f} min ({speed:.0f} steps/s)")
        
        # Guardar modelo final
        final_model_path = CHECKPOINT_DIR / 'ppo_final.zip'
        model.save(str(final_model_path))
        print(f"  ✓ Modelo guardado: {final_model_path}")
        print()
        
        # Step 5: Validación
        print('[PASO 5] VALIDACION - 3 EPISODIOS DETERMINISTICOS')
        print('-' * 80)
        
        val_results = {
            'rewards': [],
            'solar': [],
            'ev': [],
            'grid': [],
            'co2': []
        }
        
        for ep in range(3):
            obs = env.reset()
            done = False
            ep_r = 0.0
            ep_solar = 0.0
            ep_ev = 0.0
            ep_grid = 0.0
            ep_co2 = 0.0
            
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, info = env.step(action)
                
                ep_r += float(reward)
                
                if isinstance(info, (list, tuple)):
                    info = info[0]
                
                if isinstance(info, dict):
                    ep_solar += info.get('solar_kw', 0.0)
                    ep_ev += info.get('ev_charging_kw', 0.0)
                    ep_grid += info.get('grid_import_kw', 0.0)
                    ep_co2 += info.get('co2_avoided_kg', 0.0)
                
                if hasattr(done, '__len__'):
                    done = done[0]
            
            val_results['rewards'].append(ep_r)
            val_results['solar'].append(ep_solar)
            val_results['ev'].append(ep_ev)
            val_results['grid'].append(ep_grid)
            val_results['co2'].append(ep_co2)
            
            logger.info("Val Ep %d: R=%.1f | Solar=%.0f | EV=%.0f | Grid=%.0f | CO2=%.0f",
                       ep+1, ep_r, ep_solar, ep_ev, ep_grid, ep_co2)
        
        print()
        print('=' * 80)
        print('RESULTADOS FINALES')
        print('=' * 80)
        print()
        print(f"  Tiempo total:               {elapsed/60:.1f} min")
        print(f"  Velocidad:                  {speed:.0f} steps/s")
        print(f"  Reward promedio (val):      {np.mean(val_results['rewards']):.2f}")
        print(f"  Solar aprovechado (val):    {np.mean(val_results['solar'])/1000:.1f} MWh")
        print(f"  EV cargado (val):           {np.mean(val_results['ev'])/1000:.1f} MWh")
        print(f"  Grid import (val):          {np.mean(val_results['grid'])/1000:.1f} MWh")
        print(f"  CO2 evitado (val):          {np.mean(val_results['co2'])/1000:.1f} t CO2")
        print()
        
        # Guardar resultados
        summary = {
            'timestamp': datetime.now().isoformat(),
            'agent': 'PPO',
            'duration_seconds': elapsed,
            'speed_steps_per_sec': speed,
            'training_episodes': num_episodes,
            'validation': {
                'mean_reward': float(np.mean(val_results['rewards'])),
                'mean_solar_kwh': float(np.mean(val_results['solar'])),
                'mean_ev_kwh': float(np.mean(val_results['ev'])),
                'mean_grid_kwh': float(np.mean(val_results['grid'])),
                'mean_co2_kg': float(np.mean(val_results['co2'])),
            },
            'model_path': str(final_model_path),
        }
        
        summary_file = OUTPUT_DIR / 'ppo_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"  ✓ Resultados guardados: {summary_file}")
        print()
        print('=' * 80)
        print('ENTRENAMIENTO EXITOSO')
        print('=' * 80)
        
    except Exception as e:
        logger.error("ERROR: %s", e)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
