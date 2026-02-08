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

# Importar escenarios de carga de vehículos
from vehicle_charging_scenarios import (
    VehicleChargingSimulator,
    VehicleChargingScenario,
    SCENARIO_OFF_PEAK,
    SCENARIO_PEAK_AFTERNOON,
    SCENARIO_PEAK_EVENING,
    SCENARIO_EXTREME_PEAK,
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
    """Configuración A2C ÓPTIMA - Updates frecuentes (fortaleza de A2C)."""
    
    # Learning parameters - ÓPTIMOS PARA A2C
    learning_rate: float = 7e-4  # ✅ A2C default alto (converge rápido)
    n_steps: int = 8  # ✅ ÓPTIMO A2C: Updates frecuentes cada 8 pasos
    gamma: float = 0.99
    gae_lambda: float = 0.95
    ent_coef: float = 0.015  # ✅ Ligeramente más exploración
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    rms_prop_eps: float = 1e-5  # A2C usa RMSProp
    normalize_advantage: bool = True
    
    # Network architecture - ÓPTIMA PARA A2C
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[256, 256], vf=[256, 256])  # ✅ 256x256 óptimo A2C
    })
    
    @classmethod
    def for_gpu(cls) -> 'A2CConfig':
        """Configuración ÓPTIMA para A2C en GPU."""
        return cls(
            learning_rate=7e-4,  # ✅ A2C estándar alto
            n_steps=8,  # ✅ Updates frecuentes = fortaleza A2C
            ent_coef=0.015,
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], vf=[256, 256]),  # Red apropiada
            }
        )
    
    @classmethod
    def for_cpu(cls) -> 'A2CConfig':
        """Configuración para CPU (fallback)."""
        return cls(
            learning_rate=5e-5,
            n_steps=5,  # ✅ Aún más frecuente en CPU
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

# A2C OPTIMIZADO PARA GPU (RTX 4060 8GB)
# A2C: Red 256x256 on-policy, n_steps=8 (updates frecuentes = fortaleza de A2C)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    # Suprimir warning de SB3 sobre A2C en GPU (funciona, solo es menos eficiente)
    warnings.filterwarnings('ignore', message='.*A2C on the GPU.*')
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'🚀 GPU: {GPU_NAME}')
    print(f'   VRAM: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA: {cuda_version}')
    print('   Entrenamiento A2C en GPU (red 256x256, n_steps=8)')
else:
    print('CPU mode - GPU no disponible')

print(f'   Device: {DEVICE.upper()}')
print()

CHECKPOINT_DIR = Path('checkpoints/A2C')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/a2c_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== DATASET CONSTRUCTION HELPERS - Build CityLearn v2 environment from OE2 data =====

def validate_solar_timeseries_hourly(solar_df: pd.DataFrame) -> None:
    """
    CRITICAL VALIDATION: Ensure solar timeseries is EXACTLY hourly (8,760 rows per year).
    
    NO 15-minute, 30-minute, or sub-hourly data allowed.
    """
    n_rows = len(solar_df)
    
    if n_rows != 8760:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries MUST be exactly 8,760 rows (hourly, 1 year).\n"
            f"   Got {n_rows} rows instead.\n"
            f"   If using PVGIS 15-minute data, downsample: "
            f"df.set_index('time').resample('h').mean()"
        )
    
    if n_rows == 52560:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries has {n_rows} rows = 8,760 × 6 (likely 15-minute data).\n"
            f"   This codebase ONLY supports hourly resolution (8,760 rows per year).\n"
            f"   Downsample using: df.set_index('time').resample('h').mean()"
        )


def load_real_charger_dataset(charger_data_path: Path) -> Optional[pd.DataFrame]:
    """
    Load real charger dataset from data/oe2/chargers/chargers_real_hourly_2024.csv
    
    CRITICAL: This is the NEW REAL DATASET with:
    - 128 individual socket columns (112 motos + 16 mototaxis)
    - 8,760 hourly timesteps (full year 2024)
    - Individual socket control capability for RL agents
    """
    if not charger_data_path.exists():
        return None
    
    try:
        df = pd.read_csv(charger_data_path, index_col=0, parse_dates=True)
        
        if df.shape[0] != 8760:
            raise ValueError(f"Charger dataset MUST have 8,760 rows (hourly), got {df.shape[0]}")
        
        if df.shape[1] != 128:
            raise ValueError(f"Charger dataset MUST have 128 columns (sockets), got {df.shape[1]}")
        
        if len(df.index) > 1:
            dt = (df.index[1] - df.index[0]).total_seconds() / 3600
            if abs(dt - 1.0) > 0.01:
                raise ValueError(f"Charger dataset MUST be hourly frequency, got {dt:.2f} hours")
        
        min_val = df.min().min()
        max_val = df.max().max()
        print(f"[CHARGERS REAL] ✅ Loaded: {df.shape} (8760 hours × 128 sockets)")
        print(f"[CHARGERS REAL]   Value range: [{min_val:.2f}, {max_val:.2f}] kW")
        print(f"[CHARGERS REAL]   Annual energy: {df.sum().sum():,.0f} kWh")
        
        return df
        
    except Exception as e:
        print(f"[CHARGERS REAL] Error loading: {e}")
        raise


def build_oe2_dataset(interim_oe2_dir: Path) -> dict[str, Any]:
    """
    Build complete OE2 dataset from 5 required files.
    
    SECCIÓN CRÍTICA: Carga obligatoriamente 5 archivos REALES desde data/interim/oe2/
    Estas rutas son FIJAS y NO se pueden mover. Son los datos reales.
    """
    print("\n" + "="*80)
    print("[DATASET BUILD] Cargando 5 archivos OE2 REALES OBLIGATORIOS")
    print("="*80)
    
    result: dict[str, Any] = {}
    
    # 1. SOLAR (pv_generation_timeseries.csv)
    solar_path = interim_oe2_dir / 'solar' / 'pv_generation_timeseries.csv'
    if not solar_path.exists():
        raise ValueError(f"❌ Solar REQUERIDO no encontrado: {solar_path}")
    solar_df = pd.read_csv(solar_path)
    validate_solar_timeseries_hourly(solar_df)
    solar_hourly = np.asarray(solar_df.iloc[:, 0], dtype=np.float32)
    result['solar'] = solar_hourly
    print(f"[SOLAR] ✅ Cargado: {len(solar_hourly)} horas, {solar_hourly.sum():.0f} kWh/año")
    
    # 2. CHARGERS (chargers_real_hourly_2024.csv)
    chargers_path = interim_oe2_dir / 'chargers' / 'chargers_real_hourly_2024.csv'
    chargers_df = load_real_charger_dataset(chargers_path)
    if chargers_df is None or chargers_df.empty:
        raise ValueError(f"❌ Chargers REQUERIDO no cargado: {chargers_path}")
    chargers_hourly = np.asarray(chargers_df, dtype=np.float32)
    result['chargers'] = chargers_hourly
    
    # 3. MALL (demandamallhorakwh.csv)
    mall_path = interim_oe2_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        raise ValueError(f"❌ Mall demand REQUERIDO no encontrado: {mall_path}")
    mall_df = pd.read_csv(mall_path)
    if len(mall_df) != 8760:
        raise ValueError(f"❌ Mall demand debe tener 8,760 filas, tiene {len(mall_df)}")
    mall_hourly = np.asarray(mall_df.iloc[:, 0], dtype=np.float32)
    result['mall'] = mall_hourly
    print(f"[MALL] ✅ Cargado: {len(mall_hourly)} horas, {mall_hourly.sum():.0f} kWh/año")
    
    # 4. BESS (bess_hourly_dataset_2024.csv)
    bess_path = interim_oe2_dir / 'bess' / 'bess_hourly_dataset_2024.csv'
    if not bess_path.exists():
        raise ValueError(f"❌ BESS REQUERIDO no encontrado: {bess_path}")
    bess_df = pd.read_csv(bess_path)
    if len(bess_df) != 8760:
        raise ValueError(f"❌ BESS debe tener 8,760 filas, tiene {len(bess_df)}")
    bess_soc = np.asarray(bess_df.iloc[:, 1] if len(bess_df.columns) > 1 else bess_df.iloc[:, 0], dtype=np.float32)
    result['bess'] = bess_soc
    print(f"[BESS] ✅ Cargado: {len(bess_soc)} horas, SOC promedio {bess_soc.mean():.1f}%")
    
    # 5. CONTEXT (Iquitos parameters)
    context = IquitosContext()
    result['context'] = context  # type: ignore[assignment]
    print(f"[CONTEXT] ✅ Cargado: CO2={context.co2_factor_kg_per_kwh} kg/kWh, Chargers={context.n_chargers}")
    
    print("="*80)
    print("[DATASET BUILD] ✅ Todos los 5 archivos OE2 cargados exitosamente")
    print("="*80)
    
    return result


# ===== DETAILED LOGGING CALLBACK (IGUAL QUE PPO) =====
class DetailedLoggingCallback(BaseCallback):
    """Callback para registrar métricas detalladas en cada step - misma estructura que PPO."""

    def __init__(self, env_ref: Any = None, output_dir: Path | None = None, verbose: int = 0, total_timesteps: int = 87600):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.total_timesteps = total_timesteps
        self.start_time = time.time()
        self.last_log_time = time.time()
        self.log_interval = 5000  # Log cada 5000 steps
        
        # Trace y timeseries records
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        
        # Episode tracking (IGUAL QUE PPO)
        self.episode_count = 0
        self.step_in_episode = 0
        self.current_episode_reward = 0.0
        
        # Métricas por episodio (IGUAL QUE PPO + NUEVAS METRICAS)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        
        # ✅ NUEVAS: Estabilidad, Costos, Motos/Mototaxis
        self.episode_grid_stability: list[float] = []  # Promedio estabilidad por episodio
        self.episode_cost_usd: list[float] = []        # Costo total por episodio
        self.episode_motos_charged: list[int] = []     # Motos cargadas (>50% setpoint)
        self.episode_mototaxis_charged: list[int] = [] # Mototaxis cargadas (>50% setpoint)
        self.episode_bess_discharge_kwh: list[float] = []  # Descarga BESS por episodio
        self.episode_bess_charge_kwh: list[float] = []     # Carga BESS por episodio
        
        # ✅ NUEVAS: Progreso de control por socket y BESS
        self.episode_avg_socket_setpoint: list[float] = []  # Setpoint promedio 128 sockets
        self.episode_socket_utilization: list[float] = []   # % sockets activos (>0.1)
        self.episode_bess_action_avg: list[float] = []      # Acción BESS promedio [0-1]
        
        # ✅ NUEVAS: Reward components por episodio
        self.episode_r_solar: list[float] = []
        self.episode_r_cost: list[float] = []
        self.episode_r_ev: list[float] = []
        self.episode_r_grid: list[float] = []
        self.episode_r_co2: list[float] = []
        
        # Acumuladores episodio actual
        self._current_co2_grid = 0.0
        self._current_co2_avoided_indirect = 0.0
        self._current_co2_avoided_direct = 0.0
        self._current_solar_kwh = 0.0
        self._current_ev_charging = 0.0
        self._current_grid_import = 0.0
        
        # ✅ NUEVOS acumuladores
        self._current_stability_sum = 0.0
        self._current_stability_count = 0
        self._current_cost_usd = 0.0
        self._current_motos_charged_max = 0
        self._current_mototaxis_charged_max = 0
        self._current_bess_discharge = 0.0
        self._current_bess_charge = 0.0
        self._current_socket_setpoint_sum = 0.0
        self._current_socket_active_count = 0
        self._current_bess_action_sum = 0.0
        
        # ✅ NUEVOS acumuladores reward components
        self._current_r_solar_sum = 0.0
        self._current_r_cost_sum = 0.0
        self._current_r_ev_sum = 0.0
        self._current_r_grid_sum = 0.0
        self._current_r_co2_sum = 0.0
        
        # ✅ TRACKING DE VEHÍCULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
        self.episode_motos_10_max: float = 0
        self.episode_motos_20_max: float = 0
        self.episode_motos_30_max: float = 0
        self.episode_motos_50_max: float = 0
        self.episode_motos_70_max: float = 0
        self.episode_motos_80_max: float = 0
        self.episode_motos_100_max: float = 0
        
        self.episode_taxis_10_max: float = 0
        self.episode_taxis_20_max: float = 0
        self.episode_taxis_30_max: float = 0
        self.episode_taxis_50_max: float = 0
        self.episode_taxis_70_max: float = 0
        self.episode_taxis_80_max: float = 0
        self.episode_taxis_100_max: float = 0

    def _on_init(self) -> None:
        """Initialize callback after model is set. Called by BaseCallback."""
        pass

    def _on_step(self) -> bool:
        """Llamado en cada step del entrenamiento."""
        infos = self.locals.get('infos', [{}])
        rewards = self.locals.get('rewards', [0.0])
        dones = self.locals.get('dones', [False])
        
        # PROGRESO: Mostrar cada 5000 steps
        if self.num_timesteps % self.log_interval == 0 and self.num_timesteps > 0:
            elapsed = time.time() - self.start_time
            speed = self.num_timesteps / max(elapsed, 0.001)
            pct = 100.0 * self.num_timesteps / self.total_timesteps
            # ✅ CORREGIDO: Mostrar R_avg desde episodio 1 (antes requería 5+)
            mean_reward = np.mean(self.episode_rewards[-5:]) if len(self.episode_rewards) >= 1 else 0.0
            eta_seconds = (self.total_timesteps - self.num_timesteps) / max(speed, 1.0)
            print(f'  Step {self.num_timesteps:>7,}/{self.total_timesteps:,} ({pct:>5.1f}%) | '
                  f'Ep={self.episode_count} | R_avg={mean_reward:>6.2f} | '
                  f'{speed:,.0f} sps | ETA={eta_seconds/60:.1f}min', flush=True)

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
            
            # ✅ NUEVAS métricas: Estabilidad, Costos, Motos/Mototaxis, BESS
            # Estabilidad: calcular ratio de variación de grid import
            grid_import = info.get('grid_import_kwh', 0.0)
            grid_export = info.get('grid_export_kwh', 0.0)
            peak_demand_limit = 450.0  # kW límite típico
            stability = 1.0 - min(1.0, abs(grid_import - grid_export) / peak_demand_limit)
            self._current_stability_sum += stability
            self._current_stability_count += 1
            
            # Costo: tarifa × (import - export)
            tariff_usd = 0.15  # USD/kWh tarifa Iquitos
            cost_step = (grid_import - grid_export * 0.5) * tariff_usd
            self._current_cost_usd += max(0.0, cost_step)
            
            # Motos y mototaxis (máximo por episodio)
            motos = info.get('motos_charging', 0)
            mototaxis = info.get('mototaxis_charging', 0)
            self._current_motos_charged_max = max(self._current_motos_charged_max, motos)
            self._current_mototaxis_charged_max = max(self._current_mototaxis_charged_max, mototaxis)
            
            # BESS (descarga/carga)
            bess_power = info.get('bess_power_kw', 0.0)
            if bess_power > 0:
                self._current_bess_discharge += bess_power
            else:
                self._current_bess_charge += abs(bess_power)
            
            # Progreso de control de sockets (desde acciones)
            actions = self.locals.get('actions', None)
            if actions is not None and len(actions) > 0:
                action = actions[0] if len(actions[0].shape) > 0 else actions
                if len(action) >= 129:
                    bess_action = float(action[0])
                    socket_setpoints = action[1:129]
                    self._current_bess_action_sum += bess_action
                    self._current_socket_setpoint_sum += float(np.mean(socket_setpoints))
                    self._current_socket_active_count += int(np.sum(socket_setpoints > 0.1))
            
            # ✅ NUEVAS: Acumular reward components desde info
            self._current_r_solar_sum += info.get('r_solar', 0.0)
            self._current_r_cost_sum += info.get('r_cost', 0.0)
            self._current_r_ev_sum += info.get('r_ev', 0.0)
            self._current_r_grid_sum += info.get('r_grid', 0.0)
            self._current_r_co2_sum += info.get('r_co2', 0.0)
            
            # ✅ ACTUALIZAR MÁXIMOS DE VEHÍCULOS POR SOC (desde environment)
            self.episode_motos_10_max = max(self.episode_motos_10_max, info.get('motos_10_percent', 0))
            self.episode_motos_20_max = max(self.episode_motos_20_max, info.get('motos_20_percent', 0))
            self.episode_motos_30_max = max(self.episode_motos_30_max, info.get('motos_30_percent', 0))
            self.episode_motos_50_max = max(self.episode_motos_50_max, info.get('motos_50_percent', 0))
            self.episode_motos_70_max = max(self.episode_motos_70_max, info.get('motos_70_percent', 0))
            self.episode_motos_80_max = max(self.episode_motos_80_max, info.get('motos_80_percent', 0))
            self.episode_motos_100_max = max(self.episode_motos_100_max, info.get('motos_100_percent', 0))
            
            self.episode_taxis_10_max = max(self.episode_taxis_10_max, info.get('taxis_10_percent', 0))
            self.episode_taxis_20_max = max(self.episode_taxis_20_max, info.get('taxis_20_percent', 0))
            self.episode_taxis_30_max = max(self.episode_taxis_30_max, info.get('taxis_30_percent', 0))
            self.episode_taxis_50_max = max(self.episode_taxis_50_max, info.get('taxis_50_percent', 0))
            self.episode_taxis_70_max = max(self.episode_taxis_70_max, info.get('taxis_70_percent', 0))
            self.episode_taxis_80_max = max(self.episode_taxis_80_max, info.get('taxis_80_percent', 0))
            self.episode_taxis_100_max = max(self.episode_taxis_100_max, info.get('taxis_100_percent', 0))

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
                
                # ✅ NUEVAS métricas por episodio
                avg_stability = self._current_stability_sum / max(1, self._current_stability_count)
                self.episode_grid_stability.append(avg_stability)
                self.episode_cost_usd.append(self._current_cost_usd)
                self.episode_motos_charged.append(self._current_motos_charged_max)
                self.episode_mototaxis_charged.append(self._current_mototaxis_charged_max)
                self.episode_bess_discharge_kwh.append(self._current_bess_discharge)
                self.episode_bess_charge_kwh.append(self._current_bess_charge)
                
                # Promedios de control por episodio
                steps_in_ep = max(1, self.step_in_episode)
                self.episode_avg_socket_setpoint.append(self._current_socket_setpoint_sum / steps_in_ep)
                self.episode_socket_utilization.append(self._current_socket_active_count / (128.0 * steps_in_ep))
                self.episode_bess_action_avg.append(self._current_bess_action_sum / steps_in_ep)
                
                # ✅ NUEVAS: Promedios de reward components por episodio
                self.episode_r_solar.append(self._current_r_solar_sum / steps_in_ep)
                self.episode_r_cost.append(self._current_r_cost_sum / steps_in_ep)
                self.episode_r_ev.append(self._current_r_ev_sum / steps_in_ep)
                self.episode_r_grid.append(self._current_r_grid_sum / steps_in_ep)
                self.episode_r_co2.append(self._current_r_co2_sum / steps_in_ep)
                
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
                
                # ✅ Reset nuevos acumuladores
                self._current_stability_sum = 0.0
                self._current_stability_count = 0
                self._current_cost_usd = 0.0
                self._current_motos_charged_max = 0
                self._current_mototaxis_charged_max = 0
                self._current_bess_discharge = 0.0
                self._current_bess_charge = 0.0
                self._current_socket_setpoint_sum = 0.0
                self._current_socket_active_count = 0
                self._current_bess_action_sum = 0.0
                
                # ✅ Reset acumuladores reward components
                self._current_r_solar_sum = 0.0
                self._current_r_cost_sum = 0.0
                self._current_r_ev_sum = 0.0
                self._current_r_grid_sum = 0.0
                self._current_r_co2_sum = 0.0
                
                # ✅ RESET TRACKING DE VEHÍCULOS POR SOC
                self.episode_motos_10_max = 0.0
                self.episode_motos_20_max = 0.0
                self.episode_motos_30_max = 0.0
                self.episode_motos_50_max = 0.0
                self.episode_motos_70_max = 0.0
                self.episode_motos_80_max = 0.0
                self.episode_motos_100_max = 0.0
                
                self.episode_taxis_10_max = 0.0
                self.episode_taxis_20_max = 0.0
                self.episode_taxis_30_max = 0.0
                self.episode_taxis_50_max = 0.0
                self.episode_taxis_70_max = 0.0
                self.episode_taxis_80_max = 0.0
                self.episode_taxis_100_max = 0.0

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

    print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-08 - LOG SAC):')
    print('    CO2 grid (0.35): Minimizar importacion grid')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90%')
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
    print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 año)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    # ====================================================================
    # SOLAR - DEL DATASET PROCESADO (Generacionsolar/)
    # ====================================================================
    solar_path: Path = dataset_dir / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    if not solar_path.exists():
        # Fallback a interim si no existe en dataset
        solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Solar CSV no encontrado en dataset")
    
    df_solar = pd.read_csv(solar_path)
    # Prioridad: pv_generation_kwh (energía horaria) > ac_power_kw (potencia)
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
    # CHARGERS (128 sockets) - DEL DATASET CITYLEARN V2 CONSTRUIDO
    # ====================================================================
    # ✅ OBLIGATORIO: chargers_real_hourly_2024.csv con demanda REAL
    # Contiene 128 columnas de demanda horaria real (MOTO_XX_SOCKET_Y)
    charger_real_path = dataset_dir / 'chargers' / 'chargers_real_hourly_2024.csv'
    
    if not charger_real_path.exists():
        # Fallback SOLO a interim con datos reales (NO fallback a datos simplificados)
        charger_interim_path = Path('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')
        if not charger_interim_path.exists():
            raise FileNotFoundError(
                f"OBLIGATORIO: chargers_real_hourly_2024.csv NO ENCONTRADO\n"
                f"  Dataset esperado: {charger_real_path}\n"
                f"  Fallback esperado: {charger_interim_path}\n"
                f"  ERROR: No hay datos REALES de chargers. Dataset incompleto."
            )
        charger_real_path = charger_interim_path
    
    print(f'  [CHARGERS] Cargando datos REALES desde: {charger_real_path.name}')
    df_chargers = pd.read_csv(charger_real_path)
    
    # Excluir columna timestamp, tomar solo las columnas de demanda (128 sockets)
    data_cols = [c for c in df_chargers.columns if 'timestamp' not in c.lower() and 'time' not in c.lower()]
    chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    n_sockets = chargers_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    
    # Validar que tenemos 128 sockets
    if n_sockets != 128:
        print(f"  ⚠ ADVERTENCIA: Se encontraron {n_sockets} sockets en lugar de 128")
    
    if len(chargers_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Chargers: {len(chargers_hourly)} horas != {HOURS_PER_YEAR}")
    
    print("  [CHARGERS] DATASET REAL: %d sockets | Demanda: %.0f kWh/año | Promedio: %.2f kW/socket" % 
          (n_sockets, total_demand, total_demand / n_sockets / HOURS_PER_YEAR))

    # ====================================================================
    # MALL DEMAND - DEL DATASET CITYLEARN V2 (prioridad) o interim
    # ====================================================================
    mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
    if not mall_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Mall demand no encontrado en dataset")
    
    # Intentar cargar con diferentes separadores
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
    # BESS SOC - DEL DATASET CITYLEARN V2 (prioridad) o interim
    # ====================================================================
    # Prioridad 1: electrical_storage_simulation.csv del dataset
    bess_dataset_path = dataset_dir / 'electrical_storage_simulation.csv'
    bess_interim_paths = [
        dataset_dir / 'bess' / 'bess_hourly_dataset_2024.csv',
        Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
        Path('data/interim/oe2/bess/bess_dataset.csv'),
    ]
    
    bess_path: Path | None = None
    if bess_dataset_path.exists():
        bess_path = bess_dataset_path
    else:
        for p in bess_interim_paths:
            if p.exists():
                bess_path = p
                break
    
    if bess_path is None:
        raise FileNotFoundError("OBLIGATORIO: BESS data no encontrado en dataset")
    
    assert bess_path is not None  # Type guard for Pylance
    df_bess = pd.read_csv(str(bess_path), encoding='utf-8')
    # El archivo del dataset tiene soc_stored_kwh (kWh absolutos, no %)
    if 'soc_stored_kwh' in df_bess.columns:
        # Convertir kWh a SOC normalizado [0,1] usando capacidad 4520 kWh
        bess_soc_kwh = np.asarray(df_bess['soc_stored_kwh'].values[:HOURS_PER_YEAR], dtype=np.float32)
        bess_soc = bess_soc_kwh / BESS_CAPACITY_KWH
        print("  [BESS] DATASET: SOC media %.1f%% (%.0f kWh capacidad)" % (float(np.mean(bess_soc)) * 100.0, BESS_CAPACITY_KWH))
    else:
        # Fallback a columna soc tradicional
        soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
        if not soc_cols:
            raise KeyError(f"BESS CSV debe tener columna 'soc'. Columnas: {list(df_bess.columns)}")
        bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
        bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
        print("  [BESS] FALLBACK: SOC media %.1f%%" % (float(np.mean(bess_soc)) * 100.0))

    # ====================================================================
    # CHARGER STATISTICS (5to dataset OE2) - potencia máx/media por socket
    # ====================================================================
    charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
    charger_max_power: np.ndarray | None = None
    charger_mean_power: np.ndarray | None = None
    
    if charger_stats_path.exists():
        df_stats = pd.read_csv(charger_stats_path)
        if len(df_stats) >= 128:
            charger_max_power = np.array(df_stats['max_power_kw'].values[:128], dtype=np.float32)
            charger_mean_power = np.array(df_stats['mean_power_kw'].values[:128], dtype=np.float32)
            min_pwr = float(np.min(charger_max_power))
            max_pwr = float(np.max(charger_max_power))
            mean_pwr = float(np.mean(charger_mean_power))
            print(f'  [CHARGER STATS] (5to OE2): max_power={min_pwr:.2f}-{max_pwr:.2f} kW, mean={mean_pwr:.2f} kW')
        else:
            print(f'  [CHARGER STATS] WARN: {len(df_stats)} filas < 128, usando valores por defecto')
    else:
        print('  [CHARGER STATS] WARN: archivo no encontrado, usando valores por defecto')

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
            charger_max_power_kw: np.ndarray | None = None,
            charger_mean_power_kw: np.ndarray | None = None,
            max_steps: int = 8760
        ) -> None:
            """Inicializa environment con datos OE2 reales (incluye 5to dataset)."""
            super().__init__()
            
            self.reward_calculator = reward_calc
            self.context = ctx
            self.max_steps = max_steps
            
            # DATOS REALES (8760 horas = 1 año)
            self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
            self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
            self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
            self.bess_soc_hourly = np.asarray(bess_soc_arr, dtype=np.float32)
            
            # ESTADISTICAS REALES DE CARGADORES (5to dataset OE2)
            if charger_max_power_kw is not None:
                self.charger_max_power = np.asarray(charger_max_power_kw, dtype=np.float32)
            else:
                self.charger_max_power = np.full(self.NUM_CHARGERS, 2.5, dtype=np.float32)
            if charger_mean_power_kw is not None:
                self.charger_mean_power = np.asarray(charger_mean_power_kw, dtype=np.float32)
            else:
                self.charger_mean_power = np.full(self.NUM_CHARGERS, 0.89, dtype=np.float32)
            
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
            
            # ✅ TRACKING DE VEHÍCULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
            self.episode_motos_10_max: float = 0
            self.episode_motos_20_max: float = 0
            self.episode_motos_30_max: float = 0
            self.episode_motos_50_max: float = 0
            self.episode_motos_70_max: float = 0
            self.episode_motos_80_max: float = 0
            self.episode_motos_100_max: float = 0
            
            self.episode_taxis_10_max: float = 0
            self.episode_taxis_20_max: float = 0
            self.episode_taxis_30_max: float = 0
            self.episode_taxis_50_max: float = 0
            self.episode_taxis_70_max: float = 0
            self.episode_taxis_80_max: float = 0
            self.episode_taxis_100_max: float = 0
            
            # Simulador de escenarios de carga
            self.vehicle_simulator = VehicleChargingSimulator()
            # Seleccionar escenario basado en hora
            self.scenarios_by_hour = self._create_hour_scenarios()
        
        def _create_hour_scenarios(self) -> Dict[int, VehicleChargingScenario]:
            """Mapea cada hora del año a un escenario de carga realista de Iquitos."""
            scenarios = {}
            for h in range(self.HOURS_PER_YEAR):
                hour_of_day = h % 24
                
                # Off-peak: 2-6 AM
                if 2 <= hour_of_day < 6:
                    scenarios[h] = SCENARIO_OFF_PEAK
                # Morning: 6-14 (bajo a moderado)
                elif 6 <= hour_of_day < 14:
                    scenarios[h] = SCENARIO_PEAK_AFTERNOON
                # Afternoon: 14-18 (carga rápida, moderada)
                elif 14 <= hour_of_day < 18:
                    scenarios[h] = SCENARIO_PEAK_AFTERNOON
                # Evening: 18-23 (pico máximo)
                elif 18 <= hour_of_day <= 22:
                    scenarios[h] = SCENARIO_EXTREME_PEAK if (19 <= hour_of_day <= 20) else SCENARIO_PEAK_EVENING
                # Noche: 23-2 (bajo)
                else:
                    scenarios[h] = SCENARIO_OFF_PEAK
            
            return scenarios
            
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
            
            # ✅ RESET SOC TRACKERS
            self.episode_motos_10_max = 0.0
            self.episode_motos_20_max = 0.0
            self.episode_motos_30_max = 0.0
            self.episode_motos_50_max = 0.0
            self.episode_motos_70_max = 0.0
            self.episode_motos_80_max = 0.0
            self.episode_motos_100_max = 0.0
            
            self.episode_taxis_10_max = 0.0
            self.episode_taxis_20_max = 0.0
            self.episode_taxis_30_max = 0.0
            self.episode_taxis_50_max = 0.0
            self.episode_taxis_70_max = 0.0
            self.episode_taxis_80_max = 0.0
            self.episode_taxis_100_max = 0.0

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

            # CALCULAR ENERGIA (usando max_power real del 5to dataset OE2)
            charger_power_effective = charger_setpoints * self.charger_max_power[:self.n_chargers]
            ev_charging_kwh = float(np.sum(np.minimum(charger_power_effective, charger_demand)))
            total_demand_kwh = mall_kw + ev_charging_kwh
            
            # BESS power (positivo = descarga, negativo = carga)
            bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
            
            # Separar motos y mototaxis (112 motos + 16 mototaxis = 128 sockets)
            motos_demand = float(np.sum(charger_demand[:112] * charger_setpoints[:112]))
            mototaxis_demand = float(np.sum(charger_demand[112:] * charger_setpoints[112:]))
            motos_charging = int(np.sum(charger_setpoints[:112] > 0.5))
            mototaxis_charging = int(np.sum(charger_setpoints[112:] > 0.5))

            # GRID BALANCE
            net_demand = total_demand_kwh - bess_power_kw
            grid_import_kwh = max(0.0, net_demand - solar_kw)
            grid_export_kwh = max(0.0, solar_kw - net_demand)

            # CO2 CALCULATIONS
            co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
            co2_avoided_indirect_kg = min(solar_kw, total_demand_kwh) * CO2_FACTOR_IQUITOS
            co2_avoided_direct_kg = grid_export_kwh * CO2_FACTOR_IQUITOS * 0.5
            co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg

            # EV SATISFACTION - MÉTODO REALISTA (similar a SAC)
            # Basado en cuánta carga se está entregando vs la demanda
            if float(np.sum(charger_demand)) > 0.1:
                charge_ratio = ev_charging_kwh / max(1.0, float(np.sum(charger_demand)))
                ev_soc_avg = np.clip(0.80 + 0.20 * charge_ratio, 0.0, 1.0)
            else:
                ev_soc_avg = 0.95
            
            # ✅ SIMULAR CARGA DE VEHÍCULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
            scenario = self.scenarios_by_hour[h]
            min_power_kw = max(150.0, ev_charging_kwh)
            charging_result = self.vehicle_simulator.simulate_hourly_charge(scenario, min_power_kw)
            
            # Extraer conteos por SOC
            motos_10 = charging_result.get('motos_10_percent_charged', 0)  # type: ignore
            motos_20 = charging_result.get('motos_20_percent_charged', 0)  # type: ignore
            motos_30 = charging_result.get('motos_30_percent_charged', 0)  # type: ignore
            motos_50 = charging_result.get('motos_50_percent_charged', 0)  # type: ignore
            motos_70 = charging_result.get('motos_70_percent_charged', 0)  # type: ignore
            motos_80 = charging_result.get('motos_80_percent_charged', 0)  # type: ignore
            motos_100 = charging_result.get('motos_100_percent_charged', 0)  # type: ignore
            
            taxis_10 = charging_result.get('mototaxis_10_percent_charged', 0)  # type: ignore
            taxis_20 = charging_result.get('mototaxis_20_percent_charged', 0)  # type: ignore
            taxis_30 = charging_result.get('mototaxis_30_percent_charged', 0)  # type: ignore
            taxis_50 = charging_result.get('mototaxis_50_percent_charged', 0)  # type: ignore
            taxis_70 = charging_result.get('mototaxis_70_percent_charged', 0)  # type: ignore
            taxis_80 = charging_result.get('mototaxis_80_percent_charged', 0)  # type: ignore
            taxis_100 = charging_result.get('mototaxis_100_percent_charged', 0)  # type: ignore
            
            # Actualizar máximos del episodio
            self.episode_motos_10_max = max(self.episode_motos_10_max, motos_10)
            self.episode_motos_20_max = max(self.episode_motos_20_max, motos_20)
            self.episode_motos_30_max = max(self.episode_motos_30_max, motos_30)
            self.episode_motos_50_max = max(self.episode_motos_50_max, motos_50)
            self.episode_motos_70_max = max(self.episode_motos_70_max, motos_70)
            self.episode_motos_80_max = max(self.episode_motos_80_max, motos_80)
            self.episode_motos_100_max = max(self.episode_motos_100_max, motos_100)
            
            self.episode_taxis_10_max = max(self.episode_taxis_10_max, taxis_10)
            self.episode_taxis_20_max = max(self.episode_taxis_20_max, taxis_20)
            self.episode_taxis_30_max = max(self.episode_taxis_30_max, taxis_30)
            self.episode_taxis_50_max = max(self.episode_taxis_50_max, taxis_50)
            self.episode_taxis_70_max = max(self.episode_taxis_70_max, taxis_70)
            self.episode_taxis_80_max = max(self.episode_taxis_80_max, taxis_80)
            self.episode_taxis_100_max = max(self.episode_taxis_100_max, taxis_100)

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
                
                # AGREGAR BONUS POR EV SATISFACTION (igual que SAC)
                ev_bonus = (2.0 * ev_soc_avg - 1.0)  # Escala [-1, 1]
                reward_val = reward_val * 0.85 + ev_bonus * 0.15  # Ponderación 85%/15%
                reward_val = float(np.clip(reward_val, -1.0, 1.0))
                
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

            # INFO DICT (27 métricas - IGUAL QUE PPO + reward components)
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
                # REWARD COMPONENTS (5 métricas adicionales)
                'r_solar': components.get('r_solar', 0.0),
                'r_cost': components.get('r_cost', 0.0),
                'r_ev': components.get('r_ev', 0.0),
                'r_grid': components.get('r_grid', 0.0),
                'r_co2': components.get('r_co2', 0.0),
                # ✅ VEHÍCULOS CARGADOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
                'motos_10_percent': self.episode_motos_10_max,
                'motos_20_percent': self.episode_motos_20_max,
                'motos_30_percent': self.episode_motos_30_max,
                'motos_50_percent': self.episode_motos_50_max,
                'motos_70_percent': self.episode_motos_70_max,
                'motos_80_percent': self.episode_motos_80_max,
                'motos_100_percent': self.episode_motos_100_max,
                'taxis_10_percent': self.episode_taxis_10_max,
                'taxis_20_percent': self.episode_taxis_20_max,
                'taxis_30_percent': self.episode_taxis_30_max,
                'taxis_50_percent': self.episode_taxis_50_max,
                'taxis_70_percent': self.episode_taxis_70_max,
                'taxis_80_percent': self.episode_taxis_80_max,
                'taxis_100_percent': self.episode_taxis_100_max,
            }

            return obs, float(reward_val), done, truncated, info

    # Crear environment con datos cargados (IGUAL QUE PPO) + 5to dataset
    env = CityLearnEnvironment(
        reward_calc=reward_calculator,
        ctx=context,
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc_arr=bess_soc,
        charger_max_power_kw=charger_max_power,
        charger_mean_power_kw=charger_mean_power,
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
    # Velocidad GPU RTX 4060 (on-policy A2C): ~650-700 timesteps/segundo
    EPISODES = 10
    TOTAL_TIMESTEPS = EPISODES * 8760  # 87,600 timesteps
    SPEED_ESTIMATED = 650 if DEVICE == 'cuda' else 65  # Real RTX 4060 speed on A2C
    DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_ESTIMATED / 60

    if DEVICE == 'cuda':
        DURATION_TEXT = f'~{int(DURATION_MINUTES*60)} segundos (GPU RTX 4060)'
    else:
        DURATION_TEXT = f'~{DURATION_MINUTES:.1f} horas (CPU)'

    print()
    print('='*80)
    print('  📊 CONFIGURACION ENTRENAMIENTO A2C (100% DATOS REALES)')
    print(f'     Episodios: {EPISODES} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
    print(f'     Device: {DEVICE.upper()}')
    print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
    print(f'     Duración: {DURATION_TEXT}')
    print('     Datos: REALES OE2 (chargers_real_hourly_2024.csv, 4.52MWh BESS, 4.05MWp solar)')
    print('     Network: 256x256 (on-policy A2C), n_steps=8 (updates frecuentes)')
    print('     Output: result_a2c.json, timeseries_a2c.csv, trace_a2c.csv')
    print()
    print('  REWARD WEIGHTS (CO2_FOCUS):')
    print('    CO2 grid (0.35): Minimizar importacion')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90%')
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
        verbose=1,
        total_timesteps=TOTAL_TIMESTEPS
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
            'chargers_path': 'data/interim/oe2/chargers/chargers_real_hourly_2024.csv',
            'chargers_sockets': 128,
            'chargers_total_kwh': float(env.chargers_total_kwh),
            'bess_path': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
            'bess_capacity_kwh': BESS_CAPACITY_KWH,
            'solar_path': 'data/interim/oe2/solar/pv_generation_citylearn_v2.csv',
            'solar_total_kwh': float(np.sum(np.asarray(env.solar_hourly_kwh))),
            'mall_path': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
            'mall_total_kwh': float(np.sum(np.asarray(env.mall_hourly_kw))),
        },
        'validation': {
            'num_episodes': 10,
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
            # ✅ NUEVAS métricas de evolución
            'episode_grid_stability': detailed_callback.episode_grid_stability,
            'episode_cost_usd': detailed_callback.episode_cost_usd,
            'episode_motos_charged': detailed_callback.episode_motos_charged,
            'episode_mototaxis_charged': detailed_callback.episode_mototaxis_charged,
            'episode_bess_discharge_kwh': detailed_callback.episode_bess_discharge_kwh,
            'episode_bess_charge_kwh': detailed_callback.episode_bess_charge_kwh,
            'episode_avg_socket_setpoint': detailed_callback.episode_avg_socket_setpoint,
            'episode_socket_utilization': detailed_callback.episode_socket_utilization,
            'episode_bess_action_avg': detailed_callback.episode_bess_action_avg,
        },
        # ✅ NUEVAS secciones de métricas detalladas
        'summary_metrics': {
            'total_co2_avoided_indirect_kg': float(sum(detailed_callback.episode_co2_avoided_indirect)),
            'total_co2_avoided_direct_kg': float(sum(detailed_callback.episode_co2_avoided_direct)),
            'total_co2_avoided_kg': float(sum(detailed_callback.episode_co2_avoided_indirect) + sum(detailed_callback.episode_co2_avoided_direct)),
            'total_cost_usd': float(sum(detailed_callback.episode_cost_usd)),
            'avg_grid_stability': float(np.mean(detailed_callback.episode_grid_stability)) if detailed_callback.episode_grid_stability else 0.0,
            'max_motos_charged': int(max(detailed_callback.episode_motos_charged)) if detailed_callback.episode_motos_charged else 0,
            'max_mototaxis_charged': int(max(detailed_callback.episode_mototaxis_charged)) if detailed_callback.episode_mototaxis_charged else 0,
            'total_bess_discharge_kwh': float(sum(detailed_callback.episode_bess_discharge_kwh)),
            'total_bess_charge_kwh': float(sum(detailed_callback.episode_bess_charge_kwh)),
        },
        'control_progress': {
            'avg_socket_setpoint_evolution': detailed_callback.episode_avg_socket_setpoint,
            'socket_utilization_evolution': detailed_callback.episode_socket_utilization,
            'bess_action_evolution': detailed_callback.episode_bess_action_avg,
            'description': 'Evolución del aprendizaje de control por episodio',
        },
        'reward_components_avg': {
            'r_solar': float(np.mean(detailed_callback.episode_r_solar)) if detailed_callback.episode_r_solar else 0.0,
            'r_cost': float(np.mean(detailed_callback.episode_r_cost)) if detailed_callback.episode_r_cost else 0.0,
            'r_ev': float(np.mean(detailed_callback.episode_r_ev)) if detailed_callback.episode_r_ev else 0.0,
            'r_grid': float(np.mean(detailed_callback.episode_r_grid)) if detailed_callback.episode_r_grid else 0.0,
            'r_co2': float(np.mean(detailed_callback.episode_r_co2)) if detailed_callback.episode_r_co2 else 0.0,
            'episode_r_solar': detailed_callback.episode_r_solar,
            'episode_r_cost': detailed_callback.episode_r_cost,
            'episode_r_ev': detailed_callback.episode_r_ev,
            'episode_r_grid': detailed_callback.episode_r_grid,
            'episode_r_co2': detailed_callback.episode_r_co2,
            'description': 'Componentes de reward promedio por episodio',
        },
        'vehicle_charging': {
            'motos_total': 112,
            'mototaxis_total': 16,
            'motos_charged_per_episode': detailed_callback.episode_motos_charged,
            'mototaxis_charged_per_episode': detailed_callback.episode_mototaxis_charged,
            'description': 'Conteo real de vehículos cargados (setpoint > 50%)',
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
    print('  ➤ MÉTRICAS DE RECOMPENSA:')
    print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
    print()
    print('  ➤ REDUCCIÓN CO2 (kg):')
    total_indirect = float(sum(detailed_callback.episode_co2_avoided_indirect))
    total_direct = float(sum(detailed_callback.episode_co2_avoided_direct))
    print(f'    Reducción INDIRECTA (solar)   {total_indirect:>12.1f} kg')
    print(f'    Reducción DIRECTA (EVs)       {total_direct:>12.1f} kg')
    print(f'    Reducción TOTAL               {total_indirect + total_direct:>12.1f} kg')
    print(f'    CO2 evitado promedio/ep       {mean_co2:>12.1f} kg')
    print()
    print('  ➤ VEHÍCULOS CARGADOS (máximo por episodio):')
    max_motos = max(detailed_callback.episode_motos_charged) if detailed_callback.episode_motos_charged else 0
    max_mototaxis = max(detailed_callback.episode_mototaxis_charged) if detailed_callback.episode_mototaxis_charged else 0
    print(f'    Motos (de 112)                {max_motos:>12d} unidades')
    print(f'    Mototaxis (de 16)             {max_mototaxis:>12d} unidades')
    print(f'    Total vehículos               {max_motos + max_mototaxis:>12d} / 128')
    print()
    print('  ➤ ESTABILIDAD DE RED:')
    avg_stability = np.mean(detailed_callback.episode_grid_stability) if detailed_callback.episode_grid_stability else 0.0
    print(f'    Estabilidad promedio          {avg_stability*100:>12.1f} %')
    print(f'    Grid import promedio/ep       {mean_grid:>12.1f} kWh')
    print()
    print('  ➤ AHORRO ECONÓMICO:')
    total_cost = sum(detailed_callback.episode_cost_usd) if detailed_callback.episode_cost_usd else 0.0
    print(f'    Costo total (10 episodios)    ${total_cost:>11.2f} USD')
    print(f'    Costo promedio por episodio   ${mean_cost:>11.2f} USD')
    print()
    print('  ➤ CONTROL BESS:')
    total_discharge = sum(detailed_callback.episode_bess_discharge_kwh) if detailed_callback.episode_bess_discharge_kwh else 0.0
    total_charge = sum(detailed_callback.episode_bess_charge_kwh) if detailed_callback.episode_bess_charge_kwh else 0.0
    avg_bess_action = np.mean(detailed_callback.episode_bess_action_avg) if detailed_callback.episode_bess_action_avg else 0.5
    print(f'    Descarga total BESS           {total_discharge:>12.1f} kWh')
    print(f'    Carga total BESS              {total_charge:>12.1f} kWh')
    print(f'    Acción BESS promedio          {avg_bess_action:>12.3f} (0=carga, 1=descarga)')
    print()
    print('  ➤ PROGRESO DE CONTROL SOCKETS:')
    avg_setpoint = np.mean(detailed_callback.episode_avg_socket_setpoint) if detailed_callback.episode_avg_socket_setpoint else 0.0
    avg_utilization = np.mean(detailed_callback.episode_socket_utilization) if detailed_callback.episode_socket_utilization else 0.0
    print(f'    Setpoint promedio sockets     {avg_setpoint:>12.3f} [0-1]')
    print(f'    Utilización sockets           {avg_utilization*100:>12.1f} %')
    print()
    print('  ➤ SOLAR:')
    print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
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
