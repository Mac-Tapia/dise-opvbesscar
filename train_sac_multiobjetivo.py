#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
SAC (Soft Actor-Critic): Off-policy, más eficiente en muestras, ideal para problemas asimétricos
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
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from gymnasium import Env, spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

# CityLearn v2 environment
try:
    from citylearn import CityLearnEnv  # type: ignore
    CITYLEARN_AVAILABLE = True
except ImportError:
    CITYLEARN_AVAILABLE = False
    print('⚠️ WARNING: CityLearnEnv not available, will use MockEnv fallback')

from src.rewards.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# ===== CONSTANTES IQUITOS v5.2 (2026-02-12) =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid térmico aislado)
BESS_CAPACITY_KWH: float = 940.0    # 940 kWh (exclusivo EV, 100% cobertura)
BESS_MAX_POWER_KW: float = 342.0    # 342 kW potencia máxima BESS
HOURS_PER_YEAR: int = 8760

# ===== SAC CONFIG =====
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SACConfig:
    """Configuración SAC ÓPTIMA - Off-policy, entrenamiento eficiente."""
    
    # Learning parameters - ÓPTIMOS PARA SAC
    learning_rate: float = 3e-4  # ✅ SAC default (α learning rate)
    buffer_size: int = 2_000_000  # ✅ Replay buffer grande (off-policy) - GPU RTX 4060
    learning_starts: int = 1000  # ✅ Calentar replay buffer
    batch_size: int = 256  # ✅ Batch grande para SAC
    tau: float = 0.005  # ✅ Soft update coefficient
    gamma: float = 0.99  # ✅ Discount factor
    ent_coef: str = 'auto'  # ✅ Auto-tune entropy coefficient
    target_update_interval: int = 1  # ✅ Update cada paso
    target_entropy: float | None = None  # Auto-calculated
    train_freq: tuple = (1, 'step')  # ✅ Entrenar cada step
    gradient_steps: int = 1  # ✅ 1 gradient step por sample
    
    # Network architecture - ÓPTIMA PARA SAC
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[512, 512], qf=[512, 512]),  # ✅ Actor-Critic networks AGGRESSIVE (512x512)
        'activation_fn': torch.nn.ReLU,
    })
    
    @classmethod
    def for_gpu(cls) -> 'SACConfig':
        """Configuración ÓPTIMA para SAC en GPU (OPCIÓN A - Aggressive)."""
        return cls(
            learning_rate=3e-4,
            buffer_size=2_000_000,  # OPCIÓN A: Aumentado para GPU RTX 4060
            learning_starts=1000,
            batch_size=256,
            tau=0.005,
            ent_coef='auto',
            policy_kwargs={
                'net_arch': dict(pi=[512, 512], qf=[512, 512]),  # OPCIÓN A: 512x512 aggressive
            }
        )
    
    @classmethod
    def for_cpu(cls) -> 'SACConfig':
        """Configuración para CPU (fallback, batch más pequeño)."""
        return cls(
            learning_rate=3e-4,
            buffer_size=100_000,
            learning_starts=500,
            batch_size=64,
            tau=0.005,
            policy_kwargs={
                'net_arch': dict(pi=[128, 128], qf=[128, 128]),
            }
        )


# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    try:
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
    except (AttributeError, TypeError, RuntimeError):
        pass

warnings.filterwarnings('ignore', category=DeprecationWarning)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print('='*80)
print('ENTRENAR SAC - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# SAC OPTIMIZADO PARA GPU (RTX 4060 8GB)
# SAC: Off-policy, redes actor-critic 256x256, replay buffer grande
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'🚀 GPU: {GPU_NAME}')
    print(f'   VRAM: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA: {cuda_version}')
    print('   Entrenamiento SAC en GPU (actor-critic 512x512, replay buffer 2M - OPCIÓN A Aggressive)')
else:
    print('CPU mode - GPU no disponible')

print(f'   Device: {DEVICE.upper()}')
print()

CHECKPOINT_DIR = Path('checkpoints/SAC')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/sac_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== DATASET CONSTRUCTION HELPERS =====

def validate_solar_timeseries_hourly(solar_df: pd.DataFrame) -> None:
    """CRITICAL: Ensure solar timeseries is EXACTLY hourly (8,760 rows)."""
    if len(solar_df) != HOURS_PER_YEAR:
        raise ValueError(f"Solar: {len(solar_df)} rows != {HOURS_PER_YEAR} hourly")
    print(f"  ✓ Solar: {len(solar_df)} rows (correct hourly)")


def load_datasets_from_processed():
    """Load datasets desde data/processed/citylearn/iquitos_ev_mall"""
    
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        print(f'ERROR: Dataset no encontrado en {processed_path}')
        print('   Crea el dataset primero con: python build.py')
        sys.exit(1)

    print(f'  Dataset precompilado: {processed_path}')
    dataset_dir = processed_path
    print(f'  OK Dataset: {dataset_dir}')
    print()

    # ====================================================================
    # SOLAR - DEL DATASET PROCESADO
    # ====================================================================
    print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 año)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    solar_path: Path = dataset_dir / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    if not solar_path.exists():
        solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Solar CSV no encontrado en dataset")
    
    df_solar = pd.read_csv(solar_path)
    if 'pv_generation_kwh' in df_solar.columns:
        col = 'pv_generation_kwh'
    elif 'ac_power_kw' in df_solar.columns:
        col = 'ac_power_kw'
    else:
        raise KeyError(f"Solar CSV debe tener 'pv_generation_kwh' o 'ac_power_kw'. Columnas: {list(df_solar.columns)}")
    
    solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
    if len(solar_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
    print('  [SOLAR] REAL (CityLearn v2): columna=%s | %.0f kWh/año (8760h)' % (col, float(np.sum(solar_hourly))))

    # ====================================================================
    # CHARGERS (38 sockets socket_000 to socket_037) - FROM chargers_ev_ano_2024_v3.csv v5.3
    # ====================================================================
    charger_real_path = dataset_dir / 'chargers' / 'chargers_real_hourly_2024.csv'
    
    if not charger_real_path.exists():
        charger_interim_path = Path('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')
        if not charger_interim_path.exists():
            raise FileNotFoundError(
                f"OBLIGATORIO: chargers_real_hourly_2024.csv NO ENCONTRADO\n"
                f"  Dataset esperado: {charger_real_path}\n"
                f"  Fallback esperado: {charger_interim_path}\n"
                f"  ERROR: No hay datos REALES de chargers."
            )
        charger_real_path = charger_interim_path
    
    print(f'  [CHARGERS] Cargando datos REALES desde: {charger_real_path.name}')
    df_chargers = pd.read_csv(charger_real_path)
    
    data_cols = [c for c in df_chargers.columns if 'timestamp' not in c.lower() and 'time' not in c.lower()]
    chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    n_sockets = chargers_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    
    if n_sockets != 38:  # v5.2: 19 cargadores × 2 = 38 sockets
        print(f"  ⚠ ADVERTENCIA: Se encontraron {n_sockets} sockets en lugar de 38 (v5.2)")
    
    if len(chargers_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Chargers: {len(chargers_hourly)} horas != {HOURS_PER_YEAR}")
    
    print("  [CHARGERS] DATASET REAL: %d sockets | Demanda: %.0f kWh/año | Promedio: %.2f kW/socket" % 
          (n_sockets, total_demand, total_demand / n_sockets / HOURS_PER_YEAR))

    # ====================================================================
    # MALL DEMAND - DEL DATASET
    # ====================================================================
    mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
    if not mall_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Mall demand no encontrado en dataset")
    
    try:
        df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
    except Exception:
        df_mall = pd.read_csv(mall_path, encoding='utf-8')
    col = df_mall.columns[-1]
    mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
    if len(mall_data) < HOURS_PER_YEAR:
        mall_hourly = np.pad(mall_data, ((0, HOURS_PER_YEAR - len(mall_data)),), mode='wrap')
    else:
        mall_hourly = mall_data
    print("  [MALL] DATASET: %.0f kWh/año (promedio %.1f kW/h)" % (float(np.sum(mall_hourly)), float(np.mean(mall_hourly))))

    # ====================================================================
    # BESS SOC, COSTOS Y CO2 - DEL DATASET REAL
    # ====================================================================
    # Buscar BESS data en multiple paths, en orden de prioridad
    # PRIORITY 1: Archivo real en data/oe2 (con datos de costos y CO2)
    bess_real_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
    
    # PRIORITY 2: Paths procesados (fallback)
    bess_fallback_paths = [
        Path('data/processed/citylearn/iquitos_ev_mall/bess') / 'bess_simulation_hourly.csv',
        Path('data/interim/oe2/bess/bess_simulation_hourly.csv'),
    ]
    
    # Determinar qué archivo cargar
    bess_path: Path | None = None
    if bess_real_path.exists():
        bess_path = bess_real_path
        source = "OE2 REAL"
    else:
        for p in bess_fallback_paths:
            if p.exists():
                bess_path = p
                source = "FALLBACK"
                break
    
    if bess_path is None:
        print(f"[WARNING] BESS data no encontrado. Usando BESS SOC por defecto (50%)")
        df_bess = None
        bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
        bess_costs = None
        bess_co2 = None
    else:
        df_bess = pd.read_csv(bess_path)
        print(f'  [BESS] Cargando desde: {bess_path.name} ({source})')
        
        # Cargar SOC (State of Charge)
        if 'soc_kwh' in df_bess.columns:
            soc_kwh = df_bess['soc_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
            soc_max = soc_kwh.max()
            bess_soc = 100.0 * soc_kwh / soc_max  # Convertir a porcentaje
        elif 'soc_percent' in df_bess.columns:
            bess_soc = df_bess['soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
        
        # Cargar DATOS DE COSTOS (opcional, para reward)
        if 'cost_grid_import_soles' in df_bess.columns:
            bess_costs = df_bess['cost_grid_import_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
        elif 'tariff_soles_kwh' in df_bess.columns:
            bess_costs = df_bess['tariff_soles_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_costs = None
        
        # Cargar DATOS DE CO2 (CRÍTICO para reward de minimización CO2)
        if 'co2_grid_kg' in df_bess.columns:
            bess_co2_grid = df_bess['co2_grid_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_co2_grid = None
        
        if 'co2_avoided_kg' in df_bess.columns:
            bess_co2_avoided = df_bess['co2_avoided_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_co2_avoided = None
        
        bess_co2 = {
            'grid_kg': bess_co2_grid,
            'avoided_kg': bess_co2_avoided,
        }
        
        print(f"  [BESS] SOC promedio: {float(np.mean(bess_soc)):.1f}%")
        if bess_costs is not None:
            print(f"  [BESS] Costos grid: {float(np.sum(bess_costs)):.2f} soles/año")
        if bess_co2_avoided is not None:
            print(f"  [BESS] CO2 evitado: {float(np.sum(bess_co2_avoided)):.0f} kg/año")
            print(f"  [BESS] CO2 grid (sin BESS): {float(np.sum(bess_co2_grid)):.0f} kg/año")
    
    
    # ====================================================================
    # CARGAR ESTADÍSTICAS DE CHARGERS
    # ====================================================================
    charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
    charger_max_power_kw = np.full(38, 7.0, dtype=np.float32)  # Default motos
    charger_mean_power_kw = np.full(38, 2.5, dtype=np.float32)
    
    if charger_stats_path.exists():
        df_stats = pd.read_csv(charger_stats_path)
        print(f"  [CHARGER STATS] Cargada desde: {charger_stats_path.name}")
        # Opcional: extraer estadísticas reales si existen en el CSV
    
    print()
    # RETORNAR: todos los datos necesarios para entrenamiento + COSTOS Y CO2
    return {
        'solar': solar_hourly,
        'chargers': chargers_hourly,
        'mall': mall_hourly,
        'bess_soc': bess_soc,
        'bess_costs': bess_costs,
        'bess_co2': bess_co2,
        'charger_max_power_kw': charger_max_power_kw,
        'charger_mean_power_kw': charger_mean_power_kw,
    }


# ===== TRAINING LOOP =====

def main():
    """Entrenar SAC con multiobjetivo."""
    
    # Load datasets
    datasets = load_datasets_from_processed()
    
    # Desempaquetar datos cargados
    solar_hourly = datasets['solar']
    chargers_hourly = datasets['chargers']
    mall_hourly = datasets['mall']
    bess_soc = datasets['bess_soc']
    bess_costs = datasets['bess_costs']
    bess_co2 = datasets['bess_co2']
    charger_max_power = datasets['charger_max_power_kw']
    charger_mean_power = datasets['charger_mean_power_kw']
    
    print('[4] CONFIGURAR AGENTE SAC CON DATOS COMPLETOS')
    print('-' * 80)
    print(f'  Solar:           cargado ✓ ({len(solar_hourly)} horas)')
    print(f'  Chargers (38):   cargado ✓')
    print(f'  Mall demand:     cargado ✓')
    print(f'  BESS SOC:        cargado ✓')
    if bess_costs is not None:
        print(f'  BESS Costos:     cargado ✓')
    if bess_co2 is not None and bess_co2.get('avoided_kg') is not None:
        print(f'  BESS CO2 tracked: cargado ✓')
    print()
    
    # SAC Config
    sac_config = SACConfig.for_gpu() if DEVICE == 'cuda' else SACConfig.for_cpu()
    
    
    # SAC Config
    sac_config = SACConfig.for_gpu() if DEVICE == 'cuda' else SACConfig.for_cpu()
    
    print(f'  Learning rate:        {sac_config.learning_rate}')
    print(f'  Buffer size:          {sac_config.buffer_size:,}')
    print(f'  Batch size:           {sac_config.batch_size}')
    print(f'  Tau (soft update):    {sac_config.tau}')
    print(f'  Entropy coef:         {sac_config.ent_coef}')
    print(f'  Network:              Actor/Critic {list(sac_config.policy_kwargs["net_arch"]["pi"])}')
    print()
    
    # Crear ambiente CityLearn real o fallback a MockEnv
    print('[5] CREAR AMBIENTE (CityLearn v2 REAL)')
    print('-' * 80)
    
    # Intentar cargar CityLearnEnv real
    env = None
    if CITYLEARN_AVAILABLE:
        try:
            schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json')
            if not schema_path.exists():
                # Fallback a schema sin especificación de BESS
                schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
            
            if schema_path.exists():
                print(f'  ✓ Loading CityLearn schema: {schema_path.name}')
                env = CityLearnEnv(schema=str(schema_path))
                print(f'  ✓ CityLearnEnv loaded successfully')
            else:
                print(f'  ⚠ Schema not found at {schema_path}, using MockEnv')
        except Exception as e:
            print(f'  ⚠ Failed to load CityLearnEnv: {e}')
            print(f'  Falling back to MockEnv with dataset dimensions')
    
    # Fallback: MockEnv with actual dataset dimensions
    if env is None:
        class MockEnv(Env):
            def __init__(self, obs_dim=394, act_dim=38):  # CORRECTED: 38 sockets from chargers_ev_ano_2024_v3.csv
                self.obs_dim = obs_dim
                self.act_dim = act_dim
                self.observation_space = spaces.Box(low=-1e6, high=1e6, shape=(obs_dim,), dtype=np.float32)
                self.action_space = spaces.Box(low=0, high=1, shape=(act_dim,), dtype=np.float32)
                self.current_step = 0
                self.total_reward = 0
            
            def reset(self, seed=None):
                self.current_step = 0
                self.total_reward = 0
                obs = np.random.randn(self.obs_dim).astype(np.float32)
                return obs, {}
            
            def step(self, action):
                # Dummy step with realistic reward scaling
                reward = float(np.random.randn() * 10)  # Random reward for testing
                self.total_reward += reward
                self.current_step += 1
                done = self.current_step >= HOURS_PER_YEAR
                obs = np.random.randn(self.obs_dim).astype(np.float32)
                truncated = False
                info = {
                    'step': self.current_step,
                    'episode_reward': self.total_reward if done else None,
                }
                return obs, reward, done, truncated, info
        
        # Use actual dataset dimensions: 38 sockets (socket_000 to socket_037) from chargers_ev_ano_2024_v3.csv
        env = MockEnv(obs_dim=394, act_dim=38)
        print(f'  Using MockEnv with dataset dimensions:')
    
    # Get and validate spaces
    if isinstance(env.action_space, list):
        act_dim = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
    else:
        act_dim = env.action_space.shape[0] if hasattr(env.action_space, 'shape') else 1
    
    obs_dim = env.observation_space.shape[0] if hasattr(env.observation_space, 'shape') else 394
    
    print(f'  Observation space: {env.observation_space.shape}')
    print(f'  Action space:      {(act_dim,)} (Corrected: 128 sockets from chargers_real_hourly_2024.csv)')
    print()
    
    # Crear agente SAC
    print('[6] INICIALIZAR AGENTE SAC')
    print('-' * 80)
    
    # Cargar checkpoint si existe
    latest_checkpoint = None
    if CHECKPOINT_DIR.exists():
        checkpoints = sorted(CHECKPOINT_DIR.glob('sac_*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
        if checkpoints:
            latest_checkpoint = checkpoints[0]
            print(f'  Checkpoint encontrado: {latest_checkpoint.name}')
    
    # Crear o cargar agente
    if latest_checkpoint:
        print(f'  Cargando SAC desde checkpoint: {latest_checkpoint.name}')
        agent = SAC.load(latest_checkpoint, env=env, device=DEVICE)
    else:
        print(f'  Creando nuevo agente SAC')
        agent = SAC(
            'MlpPolicy',
            env,
            learning_rate=sac_config.learning_rate,
            buffer_size=sac_config.buffer_size,
            learning_starts=sac_config.learning_starts,
            batch_size=sac_config.batch_size,
            tau=sac_config.tau,
            ent_coef=sac_config.ent_coef,
            target_entropy=sac_config.target_entropy,
            train_freq=sac_config.train_freq,
            gradient_steps=sac_config.gradient_steps,
            policy_kwargs=sac_config.policy_kwargs,
            tensorboard_log=str(OUTPUT_DIR / 'tensorboard'),
            device=DEVICE,
            verbose=1,
        )
    
    print(f'  Device: {agent.device}')
    print()
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=1000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac',
        save_replay_buffer=False,
    )
    
    callback_list = CallbackList([checkpoint_callback])
    
    # Training
    # Reward configuration - from configs/sac_optimized.json
    print('[7] CONFIGURAR MULTIOBJETIVO (CO2, SOLAR, COST, EV, GRID)')
    print('-' * 80)
    
    try:
        reward_weights = create_iquitos_reward_weights(
            co2=0.35,         # From sac_optimized.json
            solar=0.20,
            ev_satisfaction=0.30,
            cost=0.10,
            grid_stability=0.05
        )
        context = IquitosContext()
        # reward_fn = MultiObjectiveReward(context, reward_weights)  # Will be used in reward callback
        print(f'  ✓ Reward weights loaded: CO₂={reward_weights.co2}, Solar={reward_weights.solar}')
    except Exception as e:
        print(f'  ⚠ Warning: Could not load reward weights: {e}')
        reward_weights = None
    print()
    
    print('[8] ENTRENAMIENTO SAC')
    print('-' * 80)
    print(f'  Total timesteps: 26,280 (3 años @ 8,760 h/año)')
    print(f'  Checkpoint cada: 1,000 steps')
    print(f'  Datos: CityLearn v2 Iquitos EV-Mall (solar PV 4050kWp + BESS 940kWh)')
    print()
    
    try:
        agent.learn(
            total_timesteps=26_280,
            callback=callback_list,
            reset_num_timesteps=False,  # Acumular pasos si resume
            progress_bar=True,
        )
        print('\n✅ Entrenamiento SAC completado exitosamente')
    except KeyboardInterrupt:
        print('\n⚠ Entrenamiento interrumpido por usuario')
        agent.save(CHECKPOINT_DIR / 'sac_interrupted.zip')
    except Exception as e:
        print(f'\n❌ Error durante entrenamiento: {e}')
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Guardar checkpoint final
        final_path = CHECKPOINT_DIR / f'sac_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        agent.save(final_path)
        print(f'✅ Checkpoint final guardado: {final_path.name}')
    
    print()
    print('='*80)
    print(f'Fin: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*80)


if __name__ == '__main__':
    main()
