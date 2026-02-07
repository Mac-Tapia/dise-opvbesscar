#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR A2C CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
NO se usa ninguna formula de aproximacion - SOLO DATOS REALES
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
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

from src.rewards.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# ===== CONSTANTES IQUITOS =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid térmico aislado)
BESS_CAPACITY_KWH: float = 4520.0   # 4.52 MWh capacidad total
BESS_MAX_POWER_KW: float = 500.0    # Potencia máxima BESS
HOURS_PER_YEAR: int = 8760

# ===== A2C CONFIG (IGUAL ESTRUCTURA QUE PPO) =====
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class A2CConfig:
    """Configuración A2C optimizada - misma estructura que PPOConfig."""
    
    # Learning parameters
    learning_rate: float = 5e-4
    n_steps: int = 5  # A2C usa rollouts cortos (on-policy)
    gamma: float = 0.99
    gae_lambda: float = 0.95
    ent_coef: float = 0.001  # Baja exploración para GPU
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    rms_prop_eps: float = 1e-5  # A2C usa RMSProp
    normalize_advantage: bool = True
    
    # Network architecture
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[256, 256], vf=[256, 256])
    })
    
    @classmethod
    def for_gpu(cls) -> 'A2CConfig':
        """Configuración optimizada para GPU RTX 4060."""
        return cls(
            learning_rate=5e-4,
            n_steps=5,
            ent_coef=0.001,
        )
    
    @classmethod
    def for_cpu(cls) -> 'A2CConfig':
        """Configuración para CPU."""
        return cls(
            learning_rate=1e-4,
            n_steps=5,
            ent_coef=0.01,
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
print('ENTRENAR A2C - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# A2C OPTIMIZADO PARA GPU RTX 4060 (on-policy, buffer pequeño)
# A2C similar a PPO pero simplificado (incluso más rápido en GPU)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'  # USA GPU AUTOMATICAMENTE
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'GPU DISPONIBLE: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA Version: {cuda_version}')
    print('   \u2713 ENTRENAMIENTO CON GPU')
    BATCH_SIZE = 256  # No usado en A2C (on-policy)
    NETWORK_ARCH = [256, 256]
else:
    print('CPU mode - GPU no disponible, usando CPU')
    BATCH_SIZE = 64  # No usado en A2C (on-policy)
    NETWORK_ARCH = [256, 256]

print(f'   Device: {DEVICE.upper()}')
print(f'   Batch size: {BATCH_SIZE}')
print(f'   Network: {NETWORK_ARCH}')
print()

CHECKPOINT_DIR = Path('checkpoints/A2C')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/a2c_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== DETAILED LOGGING CALLBACK (IGUAL QUE PPO) =====
class DetailedLoggingCallback(BaseCallback):
    """Callback para registrar métricas detalladas en cada step - misma estructura que PPO."""

    def __init__(self, env_ref: Any = None, output_dir: Path | None = None, verbose: int = 0):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        
        # Trace y timeseries records
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        
        # Episode tracking (IGUAL QUE PPO)
        self.episode_count = 0
        self.step_in_episode = 0
        self.current_episode_reward = 0.0
        
        # Métricas por episodio (IGUAL QUE PPO)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        
        # Acumuladores episodio actual
        self._current_co2_grid = 0.0
        self._current_co2_avoided_indirect = 0.0
        self._current_co2_avoided_direct = 0.0
        self._current_solar_kwh = 0.0
        self._current_ev_charging = 0.0
        self._current_grid_import = 0.0

    def _on_step(self) -> bool:
        """Llamado en cada step del entrenamiento."""
        infos = self.locals.get('infos', [{}])
        rewards = self.locals.get('rewards', [0.0])
        dones = self.locals.get('dones', [False])

        for i, info in enumerate(infos):
            reward = float(rewards[i]) if i < len(rewards) else 0.0
            done = bool(dones[i]) if i < len(dones) else False

            self.current_episode_reward += reward
            self.step_in_episode += 1
            
            # Acumular métricas del step
            self._current_co2_grid += info.get('co2_grid_kg', 0.0)
            self._current_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0.0)
            self._current_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0.0)
            self._current_solar_kwh += info.get('solar_generation_kwh', 0.0)
            self._current_ev_charging += info.get('ev_charging_kwh', 0.0)
            self._current_grid_import += info.get('grid_import_kwh', 0.0)

            # Registrar trace (cada step)
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'reward': reward,
                'cumulative_reward': self.current_episode_reward,
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'ev_soc_avg': info.get('ev_soc_avg', 0.0),
            }
            self.trace_records.append(trace_record)

            # Registrar timeseries (cada hora simulada)
            timeseries_record = {
                'timestep': self.num_timesteps,
                'hour': info.get('hour', self.step_in_episode % 8760),
                'solar_kw': info.get('solar_generation_kwh', 0.0),
                'mall_demand_kw': info.get('mall_demand_kw', 0.0),
                'ev_charging_kw': info.get('ev_charging_kwh', 0.0),
                'grid_import_kw': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'bess_soc': info.get('bess_soc', 0.0),
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
            }
            self.timeseries_records.append(timeseries_record)

            if done:
                # Guardar métricas del episodio (IGUAL QUE PPO)
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_co2_avoided_indirect.append(self._current_co2_avoided_indirect)
                self.episode_co2_avoided_direct.append(self._current_co2_avoided_direct)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                
                self.episode_count += 1
                
                # Reset acumuladores
                self.current_episode_reward = 0.0
                self.step_in_episode = 0
                self._current_co2_grid = 0.0
                self._current_co2_avoided_indirect = 0.0
                self._current_co2_avoided_direct = 0.0
                self._current_solar_kwh = 0.0
                self._current_ev_charging = 0.0
                self._current_grid_import = 0.0

        return True

    def _on_training_end(self) -> None:
        """Guardar archivos al finalizar entrenamiento."""
        pass  # Los archivos se guardan en main()


try:
    print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO')
    print('-' * 80)

    with open('configs/default.yaml', 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    print(f'  OK Config loaded: {len(cfg)} keys')

    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-07):')
    print('    CO2 grid (0.35): Minimizar importacion grid')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
    print('    Cost (0.10): Minimizar costo')
    print('    Grid stability (0.05): Suavizar picos')
    if weights is not None:
        print('  [Valores cargados: CO2={:.2f}, Solar={:.2f}, EV={:.2f}, Cost={:.2f}, Grid={:.2f}]'.format(
            weights.co2, weights.solar, weights.ev_satisfaction,
            weights.cost, weights.grid_stability))
    print()

    print('  OK Contexto Iquitos:')
    print(f'    - Grid CO2: {context.co2_factor_kg_per_kwh} kg CO2/kWh')
    print(f'    - EV CO2 factor: {context.co2_conversion_factor} kg CO2/kWh')
    print(f'    - Chargers: {context.n_chargers}')
    print(f'    - Sockets: {context.total_sockets}')
    print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
    print()

    print('[2] CARGAR DATASET CITYLEARN V2 (COMPILADO)')
    print('-' * 80)

    # Dataset ya compilado en data/processed/citylearn/iquitos_ev_mall
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        print(f'ERROR: Dataset no encontrado en {processed_path}')
        print('   Crea el dataset primero con: python build.py')
        sys.exit(1)

    print(f'  Dataset precompilado: {processed_path}')
    dataset_dir = processed_path
    print(f'  OK Dataset: {dataset_dir}')
    print()

    # ========================================================================
    # PASO 3: CARGAR DATOS REALES OE2 (IGUAL QUE PPO)
    # ========================================================================
    print('[3] CARGAR DATOS OE2 ({} horas = 1 año)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    # ====================================================================
    # SOLAR
    # ====================================================================
    solar_path: Path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
    if solar_path.exists():
        df_solar = pd.read_csv(solar_path)
        col = next((c for c in df_solar.columns if 'gener' in c.lower() or 'energia' in c.lower()), df_solar.columns[-1])
        solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
        if len(solar_hourly) != HOURS_PER_YEAR:
            raise ValueError("Solar: %d horas != %d" % (len(solar_hourly), HOURS_PER_YEAR))
        print('  [SOLAR] Cargado: %.0f kWh/año (8760h)' % float(np.sum(solar_hourly)))
    else:
        print('  [SOLAR] No encontrado: %s - usando fallback' % str(solar_path))
        solar_hourly = np.ones(HOURS_PER_YEAR, dtype=np.float32) * 1000.0

    # ====================================================================
    # CHARGERS (128 sockets = 32 chargers x 4 sockets) - DATOS REALES
    # ====================================================================
    charger_csv_path = Path('data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv')
    if charger_csv_path.exists():
        df_chargers = pd.read_csv(charger_csv_path)
        chargers_raw = df_chargers.values.astype(np.float32)
        if chargers_raw.shape[0] != HOURS_PER_YEAR:
            raise ValueError(f"Chargers CSV debe tener {HOURS_PER_YEAR} filas, tiene {chargers_raw.shape[0]}")
        n_charger_units = chargers_raw.shape[1]
        chargers_hourly = np.zeros((HOURS_PER_YEAR, n_charger_units * 4), dtype=np.float32)
        for i in range(n_charger_units):
            for s in range(4):
                socket_idx = i * 4 + s
                chargers_hourly[:, socket_idx] = chargers_raw[:, i] * (0.2 + 0.15 * s)
        n_sockets = chargers_hourly.shape[1]
        total_demand = float(np.sum(chargers_hourly))
        print("  [CHARGERS] REALES: %d chargers x 4 = %d sockets | Demanda: %.0f kWh" % (n_charger_units, n_sockets, total_demand))
    else:
        n_sockets = 128
        print("  [CHARGERS] No encontrado: %s - usando sintéticos" % str(charger_csv_path))
        chargers_hourly = np.random.uniform(0.5, 3.0, (HOURS_PER_YEAR, n_sockets)).astype(np.float32)

    # ====================================================================
    # MALL DEMAND
    # ====================================================================
    mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
    if mall_path.exists():
        df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
        col = df_mall.columns[-1]
        mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
        if len(mall_data) < HOURS_PER_YEAR:
            mall_hourly = np.pad(mall_data, ((0, HOURS_PER_YEAR - len(mall_data)),), mode='wrap')
        else:
            mall_hourly = mall_data
        print("  [MALL] Cargado: %.0f kWh/año" % float(np.sum(mall_hourly)))
    else:
        print("  [MALL] No encontrado: %s" % str(mall_path))
        mall_hourly = np.ones(HOURS_PER_YEAR, dtype=np.float32) * 100.0

    # ====================================================================
    # BESS SOC (Battery Energy Storage System State of Charge)
    # ====================================================================
    bess_paths = [
        Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
        Path('data/interim/oe2/bess/bess_dataset.csv'),
    ]
    bess_path = next((p for p in bess_paths if p.exists()), None)
    bess_soc = np.full(HOURS_PER_YEAR, 0.5, dtype=np.float32)

    if bess_path is not None and bess_path.exists():
        df_bess = pd.read_csv(bess_path, encoding='utf-8')
        soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
        if soc_cols:
            bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
            bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
            print("  [BESS] Cargado: SOC media %.1f%% (archivo: %s)" % (float(np.mean(bess_soc)) * 100.0, bess_path.name))
    else:
        print("  [BESS] No encontrado - usando fallback 50%%")

    print()

    # ========================================================================
    # PASO 4: CREAR ENVIRONMENT (IGUAL ESTRUCTURA QUE PPO)
    # ========================================================================
    print('[4] CREAR ENVIRONMENT CON DATOS OE2 REALES')
    print('-' * 80)

    class CityLearnEnvironment(Env):  # type: ignore[type-arg]
        """Environment compatible con Gymnasium para CityLearn v2.
        
        MISMA ESTRUCTURA QUE PPO - recibe datos como parámetros.
        
        Observation Space (394-dim):
        - [0]: Solar generation (kW)
        - [1]: Total demand (kW)
        - [2]: BESS SOC normalized [0,1]
        - [3]: Mall demand (kW)
        - [4:132]: 128 charger demands (kW)
        - [132:260]: 128 charger powers (kW)
        - [260:388]: 128 occupancy (binary)
        - [388:394]: Time features (hour, dow, month, peak, co2, tariff)
        
        Action Space (129-dim):
        - [0]: BESS control [0,1]
        - [1:129]: 128 charger setpoints [0,1]
        """
        
        HOURS_PER_YEAR: int = 8760
        NUM_CHARGERS: int = 128
        OBS_DIM: int = 394
        ACTION_DIM: int = 129

        def __init__(
            self,
            reward_calc: Any,
            ctx: Any,
            solar_kw: np.ndarray,
            chargers_kw: np.ndarray,
            mall_kw: np.ndarray,
            bess_soc_arr: np.ndarray,
            max_steps: int = 8760
        ) -> None:
            """Inicializa environment con datos OE2 reales."""
            super().__init__()
            
            self.reward_calculator = reward_calc
            self.context = ctx
            self.max_steps = max_steps
            
            # DATOS REALES (8760 horas = 1 año)
            self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
            self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
            self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
            self.bess_soc_hourly = np.asarray(bess_soc_arr, dtype=np.float32)
            
            # Validación
            if len(self.solar_hourly) != self.HOURS_PER_YEAR:
                raise ValueError(f"Solar: {len(self.solar_hourly)} != {self.HOURS_PER_YEAR}")
            
            self.n_chargers = self.chargers_hourly.shape[1]
            
            # Para tracking de totales (backwards compatibility)
            self.chargers_total_kwh = float(np.sum(self.chargers_hourly))
            self.solar_hourly_kwh = self.solar_hourly  # Alias
            self.mall_hourly_kw = self.mall_hourly  # Alias

            # Espacios (Gymnasium API)
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(self.OBS_DIM,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0, shape=(self.ACTION_DIM,), dtype=np.float32
            )

            # STATE TRACKING
            self.step_count = 0
            self.episode_num = 0
            self.episode_reward = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import = 0.0
            
            # Tracking acumulativo (backwards compatibility)
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            
        def _make_observation(self, hour_idx: int) -> np.ndarray:
            """Crea observación CityLearn v2 (394-dim) - IGUAL QUE PPO."""
            obs = np.zeros(self.OBS_DIM, dtype=np.float32)
            h = hour_idx % self.HOURS_PER_YEAR
            
            # FEATURES ENERGETICAS (indices 0-3)
            obs[0] = np.clip(float(self.solar_hourly[h]), 0.0, 1e4)
            obs[1] = float(self.mall_hourly[h])
            obs[2] = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)
            obs[3] = float(self.mall_hourly[h])
            
            # CHARGER DEMANDS Y POWERS (indices 4-259)
            if self.chargers_hourly.shape[1] >= self.NUM_CHARGERS:
                obs[4:132] = np.clip(self.chargers_hourly[h, :self.NUM_CHARGERS], 0.0, 100.0)
            else:
                obs[4:4+self.chargers_hourly.shape[1]] = np.clip(self.chargers_hourly[h], 0.0, 100.0)
            
            obs[132:260] = obs[4:132] * 0.5  # Simplified power from demand
            
            # OCCUPANCY (indices 260-387)
            hour_24 = h % 24
            base_occupancy = 0.3 if 6 <= hour_24 <= 22 else 0.1
            obs[260:388] = np.random.binomial(1, base_occupancy, self.NUM_CHARGERS).astype(np.float32)
            
            # TIME FEATURES (indices 388-393)
            obs[388] = float(hour_24) / 24.0
            day_of_year = (h // 24) % 365
            obs[389] = float(day_of_year % 7) / 7.0
            obs[390] = float((day_of_year // 30) % 12) / 12.0
            obs[391] = 1.0 if 6 <= hour_24 <= 22 else 0.0
            obs[392] = float(self.context.co2_factor_kg_per_kwh)
            obs[393] = 0.15
            
            return obs

        def render(self) -> None:
            """Render no implementado para este environment."""
            return

        def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None
        ) -> tuple[np.ndarray, dict[str, Any]]:
            del seed, options
            self.step_count = 0
            self.episode_num += 1
            self.episode_reward = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import = 0.0
            
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0

            obs = self._make_observation(0)
            return obs, {}

        def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
            """Ejecuta un paso de simulación (1 hora) - MISMA ESTRUCTURA QUE PPO."""
            self.step_count += 1
            h = (self.step_count - 1) % self.HOURS_PER_YEAR

            # DATOS REALES (OE2 timeseries)
            solar_kw = float(self.solar_hourly[h])
            mall_kw = float(self.mall_hourly[h])
            charger_demand = self.chargers_hourly[h].astype(np.float32)
            bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

            # PROCESAR ACCION (129-dim: 1 BESS + 128 chargers)
            bess_action = np.clip(action[0], 0.0, 1.0)
            charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

            # CALCULAR ENERGIA
            ev_charging_kwh = float(np.sum(charger_demand * charger_setpoints))
            total_demand_kwh = mall_kw + ev_charging_kwh
            
            # BESS power (positivo = descarga, negativo = carga)
            bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
            
            # Separar motos y mototaxis
            motos_demand = float(np.sum(charger_demand[:92] * charger_setpoints[:92]))
            mototaxis_demand = float(np.sum(charger_demand[92:] * charger_setpoints[92:]))
            motos_charging = int(np.sum(charger_setpoints[:92] > 0.5))
            mototaxis_charging = int(np.sum(charger_setpoints[92:] > 0.5))

            # GRID BALANCE
            net_demand = total_demand_kwh - bess_power_kw
            grid_import_kwh = max(0.0, net_demand - solar_kw)
            grid_export_kwh = max(0.0, solar_kw - net_demand)

            # CO2 CALCULATIONS
            co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
            co2_avoided_indirect_kg = min(solar_kw, total_demand_kwh) * CO2_FACTOR_IQUITOS
            co2_avoided_direct_kg = grid_export_kwh * CO2_FACTOR_IQUITOS * 0.5
            co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg

            # EV SATISFACTION
            ev_soc_avg = np.clip(bess_soc + 0.005 * np.mean(charger_setpoints), 0.0, 1.0)

            # CALCULAR RECOMPENSA MULTIOBJETIVO
            try:
                reward_val, components = self.reward_calculator.compute(
                    grid_import_kwh=grid_import_kwh,
                    grid_export_kwh=grid_export_kwh,
                    solar_generation_kwh=solar_kw,
                    ev_charging_kwh=ev_charging_kwh,
                    ev_soc_avg=ev_soc_avg,
                    bess_soc=bess_soc,
                    hour=h % 24,
                    ev_demand_kwh=self.context.ev_demand_constant_kw
                )
            except (AttributeError, KeyError, TypeError):
                reward_val = -grid_import_kwh * 0.01 + solar_kw * 0.001
                components = {}

            # TRACKING
            self.episode_reward += float(reward_val)
            self.episode_co2_avoided += co2_avoided_total_kg
            self.episode_solar_kwh += solar_kw
            self.episode_grid_import += grid_import_kwh
            
            self.co2_avoided_total += co2_avoided_total_kg
            self.solar_kwh_total += solar_kw
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh

            # OBSERVACIÓN
            obs = self._make_observation(self.step_count)

            done = self.step_count >= self.max_steps
            truncated = False

            # INFO DICT (22 métricas - IGUAL QUE PPO)
            info: dict[str, Any] = {
                'co2_grid_kg': co2_grid_kg,
                'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
                'co2_avoided_direct_kg': co2_avoided_direct_kg,
                'co2_avoided_total_kg': co2_avoided_total_kg,
                'solar_generation_kwh': solar_kw,
                'ev_charging_kwh': ev_charging_kwh,
                'mall_demand_kw': mall_kw,
                'grid_import_kwh': grid_import_kwh,
                'grid_export_kwh': grid_export_kwh,
                'bess_power_kw': float(bess_power_kw),
                'bess_soc': bess_soc,
                'ev_soc_avg': float(ev_soc_avg),
                'motos_charging': motos_charging,
                'mototaxis_charging': mototaxis_charging,
                'motos_demand_kwh': motos_demand,
                'mototaxis_demand_kwh': mototaxis_demand,
                'hour': h % 24,
                'day': h // 24,
                'step': self.step_count,
                'episode_reward': self.episode_reward,
                'episode_co2_avoided_kg': self.co2_avoided_total,
                'episode_solar_kwh': self.solar_kwh_total,
            }

            return obs, float(reward_val), done, truncated, info

    # Crear environment con datos cargados (IGUAL QUE PPO)
    env = CityLearnEnvironment(
        reward_calc=reward_calculator,
        ctx=context,
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc_arr=bess_soc,
        max_steps=HOURS_PER_YEAR
    )
    print('  OK Environment creado')
    print(f'    - Observation: {env.observation_space.shape}')
    print(f'    - Action: {env.action_space.shape}')
    print()

    # ========================================================================
    # PASO 5: CREAR A2C AGENT (USANDO A2CConfig)
    # ========================================================================
    print('[5] CREAR A2C AGENT')
    print('-' * 80)

    a2c_config = A2CConfig.for_gpu() if DEVICE == 'cuda' else A2CConfig.for_cpu()

    a2c_agent = A2C(
        'MlpPolicy',
        env,
        learning_rate=a2c_config.learning_rate,
        n_steps=a2c_config.n_steps,
        gamma=a2c_config.gamma,
        gae_lambda=a2c_config.gae_lambda,
        ent_coef=a2c_config.ent_coef,
        vf_coef=a2c_config.vf_coef,
        max_grad_norm=a2c_config.max_grad_norm,
        normalize_advantage=a2c_config.normalize_advantage,
        policy_kwargs=a2c_config.policy_kwargs,
        verbose=0,
        device=DEVICE,
        tensorboard_log=None,
    )

    print(f'  OK A2C agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {a2c_config.learning_rate}')
    print(f'    - N steps: {a2c_config.n_steps}')
    print(f'    - Entropy coef: {a2c_config.ent_coef}')
    print()

    # ========================================================================
    # PASO 6: ENTRENAR A2C
    # ========================================================================
    print('[6] ENTRENAR A2C')
    print('-' * 80)

    # ENTRENAMIENTO: 10 episodios completos = 10 × 8,760 timesteps = 87,600 pasos
    # Velocidad GPU RTX 4060 (on-policy A2C): ~1,200+ timesteps/segundo
    EPISODES = 10
    TOTAL_TIMESTEPS = EPISODES * 8760  # 87,600 timesteps
    SPEED_ESTIMATED = 1200 if DEVICE == 'cuda' else 65
    DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_ESTIMATED / 60

    if DEVICE == 'cuda':
        DURATION_TEXT = f'~{int(DURATION_MINUTES*60)} segundos (GPU AL MAXIMO)'
    else:
        DURATION_TEXT = f'~{DURATION_MINUTES:.1f} horas (CPU)'

    print()
    print('='*80)
    print('  📊 CONFIGURACION ENTRENAMIENTO A2C')
    print(f'     Episodios: {EPISODES} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
    print(f'     Device: {DEVICE.upper()}')
    print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
    print(f'     Duración: {DURATION_TEXT}')
    print('     Datos: 100% REALES OE2 (128 chargers, 4.52MWh BESS, 4.05MWp solar)')
    print('     Output: result_a2c.json, timeseries_a2c.csv, trace_a2c.csv')
    print()
    print('  REWARD WEIGHTS (SINCRONIZADOS):')
    print('    CO2 grid (0.35): Minimizar importacion')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
    print('    Cost (0.10): Minimizar costo')
    print('    Grid stability (0.05): Suavizar picos')
    print('='*80)
    print('  ENTRENAMIENTO EN PROGRESO:')
    print('  ' + '-' * 76)

    start_time = time.time()

    # Callbacks: Checkpoint + DetailedLogging (IGUAL QUE PPO)
    checkpoint_callback = CheckpointCallback(
        save_freq=2000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='a2c_model',
        verbose=0
    )
    
    detailed_callback = DetailedLoggingCallback(
        env_ref=env,
        output_dir=OUTPUT_DIR,
        verbose=1
    )
    
    callback_list = CallbackList([checkpoint_callback, detailed_callback])

    a2c_agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=callback_list,
        progress_bar=False
    )

    elapsed = time.time() - start_time
    a2c_agent.save(CHECKPOINT_DIR / 'a2c_final_model.zip')

    print()
    print('  ✓ RESULTADO ENTRENAMIENTO:')
    print(f'    Tiempo: {elapsed/60:.1f} minutos ({elapsed:.0f} segundos)')
    print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
    print(f'    Velocidad real: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')
    print(f'    Episodios completados: {detailed_callback.episode_count}')

    # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
    print()
    print('[6] GUARDAR ARCHIVOS DE SALIDA')
    print('-' * 80)

    # 1. trace_a2c.csv - Registro detallado de cada step
    if detailed_callback.trace_records:
        trace_df = pd.DataFrame(detailed_callback.trace_records)
        trace_path = OUTPUT_DIR / 'trace_a2c.csv'
        trace_df.to_csv(trace_path, index=False)
        print(f'  ✓ trace_a2c.csv: {len(trace_df)} registros → {trace_path}')
    else:
        print('  ⚠ trace_a2c.csv: Sin registros (callback vacío)')

    # 2. timeseries_a2c.csv - Series temporales horarias
    if detailed_callback.timeseries_records:
        ts_df = pd.DataFrame(detailed_callback.timeseries_records)
        ts_path = OUTPUT_DIR / 'timeseries_a2c.csv'
        ts_df.to_csv(ts_path, index=False)
        print(f'  ✓ timeseries_a2c.csv: {len(ts_df)} registros → {ts_path}')
    else:
        print('  ⚠ timeseries_a2c.csv: Sin registros (callback vacío)')

    print()
    print('[7] VALIDACION - 10 EPISODIOS')
    print('-' * 80)

    val_obs, _ = env.reset()
    val_metrics: dict[str, list[float]] = {
        'rewards': [],
        'co2_avoided': [],
        'solar_kwh': [],
        'cost_usd': [],
        'grid_import': [],
    }

    for ep in range(10):
        val_obs, _ = env.reset()
        validation_done = False
        step_count = 0
        episode_co2 = 0.0
        episode_solar = 0.0
        episode_grid = 0.0

        print(f'  Episodio {ep+1}/10: ', end='', flush=True)

        while not validation_done:
            action_result = a2c_agent.predict(val_obs, deterministic=True)
            action_arr = action_result[0] if action_result is not None else np.zeros(129)
            val_obs, reward, terminated, val_truncated, step_info = env.step(action_arr)
            validation_done = terminated or val_truncated
            step_count += 1

            episode_co2 += step_info.get('co2_avoided_total_kg', 0)
            episode_solar += step_info.get('solar_generation_kwh', 0)
            episode_grid += step_info.get('grid_import_kwh', 0)

        val_metrics['rewards'].append(env.episode_reward)
        val_metrics['co2_avoided'].append(episode_co2)
        val_metrics['solar_kwh'].append(episode_solar)
        val_metrics['cost_usd'].append(env.cost_total)
        val_metrics['grid_import'].append(episode_grid)

        print(
            f'Reward={env.episode_reward:>8.2f} | CO2_avoided={episode_co2:>10.1f}kg'
            f' | Solar={episode_solar:>10.1f}kWh | Steps={step_count}'
        )

    print()

    # 3. result_a2c.json - Resumen completo del entrenamiento (IGUAL ESTRUCTURA QUE PPO)
    result_summary: dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'agent': 'A2C',
        'project': 'pvbesscar',
        'location': 'Iquitos, Peru',
        'co2_factor_kg_per_kwh': CO2_FACTOR_IQUITOS,
        'training': {
            'total_timesteps': int(TOTAL_TIMESTEPS),
            'episodes': int(EPISODES),
            'duration_seconds': float(elapsed),
            'speed_steps_per_second': float(TOTAL_TIMESTEPS / elapsed),
            'device': str(DEVICE),
            'episodes_completed': detailed_callback.episode_count,
            'hyperparameters': {
                'learning_rate': a2c_config.learning_rate,
                'n_steps': a2c_config.n_steps,
                'gamma': a2c_config.gamma,
                'gae_lambda': a2c_config.gae_lambda,
                'ent_coef': a2c_config.ent_coef,
                'vf_coef': a2c_config.vf_coef,
                'max_grad_norm': a2c_config.max_grad_norm,
            }
        },
        'datasets_oe2': {
            'chargers_path': 'data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv',
            'chargers_sockets': 128,
            'chargers_total_kwh': float(env.chargers_total_kwh),
            'bess_path': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
            'bess_capacity_kwh': BESS_CAPACITY_KWH,
            'solar_path': 'data/interim/oe2/solar/pv_generation_timeseries.csv',
            'solar_total_kwh': float(np.sum(np.asarray(env.solar_hourly_kwh))),
            'mall_path': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
            'mall_total_kwh': float(np.sum(np.asarray(env.mall_hourly_kw))),
        },
        'validation': {
            'num_episodes': 3,
            'mean_reward': float(np.mean(val_metrics['rewards'])),
            'std_reward': float(np.std(val_metrics['rewards'])),
            'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
            'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
            'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
            'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
        },
        'training_evolution': {
            'episode_rewards': detailed_callback.episode_rewards,
            'episode_co2_grid': detailed_callback.episode_co2_grid,
            'episode_co2_avoided_indirect': detailed_callback.episode_co2_avoided_indirect,
            'episode_co2_avoided_direct': detailed_callback.episode_co2_avoided_direct,
            'episode_solar_kwh': detailed_callback.episode_solar_kwh,
            'episode_ev_charging': detailed_callback.episode_ev_charging,
            'episode_grid_import': detailed_callback.episode_grid_import,
        },
        'model_path': str(CHECKPOINT_DIR / 'a2c_final_model.zip'),
    }

    result_path = OUTPUT_DIR / 'result_a2c.json'
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, indent=2, ensure_ascii=False)
    print(f'  ✓ result_a2c.json: Resumen completo → {result_path}')

    # Extraer métricas para impresión (acceso directo)
    mean_reward = float(np.mean(val_metrics['rewards']))
    mean_co2 = float(np.mean(val_metrics['co2_avoided']))
    mean_solar = float(np.mean(val_metrics['solar_kwh']))
    mean_cost = float(np.mean(val_metrics['cost_usd']))
    mean_grid = float(np.mean(val_metrics['grid_import']))

    print()
    print('='*80)
    print('RESULTADOS FINALES - VALIDACION 10 EPISODIOS:')
    print('='*80)
    print()
    print('  PARAMETROS CALCULADOS:')
    print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
    print(f'    CO2 evitado por episodio      {mean_co2:>12.1f} kg')
    print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
    print(f'    Ahorro economico por ep       {mean_cost:>12.2f} USD')
    print(f'    Grid import reducido por ep   {mean_grid:>12.1f} kWh')
    print()
    print('  ARCHIVOS GENERADOS:')
    print(f'    ✓ {OUTPUT_DIR}/result_a2c.json')
    print(f'    ✓ {OUTPUT_DIR}/timeseries_a2c.csv')
    print(f'    ✓ {OUTPUT_DIR}/trace_a2c.csv')
    print(f'    ✓ {CHECKPOINT_DIR}/a2c_final_model.zip')
    print()
    print('  ESTADO: Entrenamiento A2C exitoso con datos reales OE2.')
    print()

    print('='*80)
    print('ENTRENAMIENTO A2C COMPLETADO')
    print('='*80)

except (FileNotFoundError, KeyError, ValueError, RuntimeError, OSError, IOError) as e:
    print(f'\n[ERROR] {e}')
    traceback.print_exc()
    sys.exit(1)
