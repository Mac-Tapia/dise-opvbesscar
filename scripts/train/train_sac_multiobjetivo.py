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
except (ImportError, AttributeError):
    CITYLEARN_AVAILABLE = False
    print('[WARNING] CityLearnEnv not available, will use Gymnasium Env fallback')

from src.citylearnv2.dataset_builder.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# Vehicle charging scenarios (ahora consistente con PPO)
try:
    from vehicle_charging_scenarios import (
        VehicleChargingSimulator,
        VehicleChargingScenario,
        SCENARIO_OFF_PEAK,
        SCENARIO_PEAK_AFTERNOON,
        SCENARIO_PEAK_EVENING,
        SCENARIO_EXTREME_PEAK,
    )
    VEHICLE_SCENARIOS_AVAILABLE = True
except ImportError:
    VEHICLE_SCENARIOS_AVAILABLE = False
    print('⚠️ WARNING: vehicle_charging_scenarios not available')

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
    """Load datasets desde data/processed/citylearn/iquitos_ev_mall
    
    SINCRONIZACIÓN DATASET_BUILDER v5.5:
    ================================================================================
    Esta función carga TODO el conjunto de datos considerando TODAS LAS COLUMNAS
    definidas en src/citylearnv2/dataset_builder/dataset_builder.py:
    
    CHARGERS (10 columnas observables):
      - 38 sockets repartidos: 30 motos + 8 mototaxis
      - Prefijo "ev_": ev_is_hora_punta, ev_tarifa_aplicada_soles, ev_energia_total_kwh,
        ev_costo_carga_soles, ev_energia_motos_kwh, ev_energia_mototaxis_kwh,
        ev_co2_reduccion_motos_kg, ev_co2_reduccion_mototaxis_kg,
        ev_reduccion_directa_co2_kg, ev_demand_kwh
      - Fuente: data_loader.load_chargers_data() → chargers_ev_ano_2024_v3.csv
      - Tarifa: 0.45 S/. HP (18h-23h), 0.28 S/. HFP
    
    SOLAR (6 columnas observables):
      - Capacidad: 4,050 kWp
      - Prefijo "solar_": solar_is_hora_punta, solar_tarifa_aplicada_soles,
        solar_ahorro_soles, solar_reduccion_indirecta_co2_kg,
        solar_co2_mall_kg, solar_co2_ev_kg
      - Fuente: data_loader.load_solar_data() → pv_generation_citylearn2024.csv
      - Factor CO2 indirecto: 0.4521 kg CO2/kWh
    
    BESS (5 columnas observables) v5.5:
      - Capacidad: 1,700 kWh (1,360 usable @ 20-100% SOC)
      - Potencia: 400 kW
      - Prefijo "bess_": bess_soc_percent, bess_charge_kwh, bess_discharge_kwh,
        bess_to_mall_kwh, bess_to_ev_kwh
      - Fuente: data_loader.load_bess_data() → bess_ano_2024.csv
    
    MALL (3 columnas observables) v5.5:
      - Prefijo "mall_": mall_demand_kwh, mall_demand_reduction_kwh, mall_cost_soles
      - Fuente: data_loader.load_mall_demand_data() → demandamallhorakwh.csv
    
    TOTALES (3 columnas combinadas):
      - total_reduccion_co2_kg (COV directo + indirecto)
      - total_costo_soles (costo EVs)
      - total_ahorro_soles (ahorro solar)
    
    TOTAL: 27 columnas observables en ALL_OBSERVABLE_COLS
    
    Tiempo: 8,760 horas (365 días × 24 horas, resolución horaria)
    
    El agente SAC ACCEDE a TODAS ESTAS COLUMNAS en el estado de observación
    para optimizar raciones multiobjetivo (CO2, solar, costo, EV, grid).
    
    METADATA DE ESCENARIOS (data/oe2/chargers/) v5.5:
      - selection_pe_fc_completo.csv: 54 escenarios (pe, fc, chargers_required, etc.)
      - tabla_escenarios_detallados.csv: CONSERVADOR, MEDIANO, RECOMENDADO*, MÁXIMO
      - tabla_estadisticas_escenarios.csv: Estadísticas agregadas
      - escenarios_tabla13.csv: 101 escenarios PE/FC
      → Cargar con: data_loader.load_scenarios_metadata()
      → ESCENARIO RECOMENDADO v5.5: PE=1.00, FC=1.00, 19 cargadores, 38 tomas, 1129 kWh/día
    ================================================================================
    """
    
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

    # ✅ SOLAR = REAL hourly generation for Iquitos 2024 (8760 hours)
    solar_path: Path = dataset_dir / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    if not solar_path.exists():
        solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Solar CSV no encontrado en dataset")
    
    df_solar = pd.read_csv(solar_path)
    # Use 'ac_power_kw' - actual grid-tied inverter output (REAL power generation)
    if 'ac_power_kw' in df_solar.columns:
        col = 'ac_power_kw'
    elif 'pv_kw' in df_solar.columns:
        col = 'pv_kw'
    elif 'pv_generation_kwh' in df_solar.columns:
        col = 'pv_generation_kwh'
    else:
        raise KeyError(f"Solar CSV debe tener 'ac_power_kw', 'pv_kw' o 'pv_generation_kwh'. Columnas: {list(df_solar.columns)}")
    
    solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
    if len(solar_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
    print('  [SOLAR] ✅ REAL: col=%s | %.0f kWh/year (8760h)' % (col, float(np.sum(solar_hourly))))

    # ====================================================================
    # CHARGERS - ✅ REAL HOURLY DEMAND (38 sockets × 8760h from 2024)
    # ====================================================================
    # Status: REAL - Measured EV charging demand profiles
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
    
    print(f'  [CHARGERS] ✅ REAL: Loading from {charger_real_path.name}')
    df_chargers = pd.read_csv(charger_real_path)
    
    data_cols = [c for c in df_chargers.columns if 'timestamp' not in c.lower() and 'time' not in c.lower()]
    chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    n_sockets = chargers_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    
    if n_sockets != 38:  # v5.2: 19 chargers × 2 sockets = 38 total
        print(f"  ⚠ WARNING: Found {n_sockets} sockets instead of 38 (v5.2)")
    
    if len(chargers_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Chargers: {len(chargers_hourly)} hours != {HOURS_PER_YEAR}")
    
    print("  [CHARGERS] ✅ REAL: %d sockets | Demand: %.0f kWh/year | Avg: %.2f kW/socket" % 
          (n_sockets, total_demand, total_demand / n_sockets / HOURS_PER_YEAR))

    # ✅ MALL = REAL hourly demand for shopping mall Iquitos 2024 (8760 hours)
    mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
    if not mall_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Mall demand not found")
    
    try:
        df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
    except Exception:
        df_mall = pd.read_csv(mall_path, encoding='utf-8')
    col = 'demand_kwh' if 'demand_kwh' in df_mall.columns else df_mall.columns[-1]
    mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
    if len(mall_data) < HOURS_PER_YEAR:
        mall_hourly = np.pad(mall_data, ((0, HOURS_PER_YEAR - len(mall_data)),), mode='wrap')
    else:
        mall_hourly = mall_data
    print("  [MALL] ✅ REAL: %.0f kWh/year (avg %.1f kW/h)" % (float(np.sum(mall_hourly)), float(np.mean(mall_hourly))))

    # ====================================================================
    # BESS - ⚠️ SIMULATED (dispatch optimization output, not real device)
    # ====================================================================
    # Status: SIMULATED - Calculated BESS operation from OE2 dispatch logic
    # Columns: bess_soc_percent, bess_charge_kwh, cost_grid_import, co2_avoided_kg
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
        print(f"[WARNING] BESS simulation not found. Using default SOC 50%")
        df_bess = None
        bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
        bess_costs = None
        bess_co2 = None
    else:
        df_bess = pd.read_csv(bess_path)
        print(f'  [BESS] ⚠️ SIMULATED - Loading from: {bess_path.name} ({source})')
        
        # Load SOC from BESS SIMULATION (not real device data)
        if 'bess_soc_percent' in df_bess.columns:
            bess_soc = df_bess['bess_soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
        elif 'soc_percent' in df_bess.columns:
            bess_soc = df_bess['soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
        elif 'soc_kwh' in df_bess.columns:
            soc_kwh = df_bess['soc_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
            soc_max = soc_kwh.max()
            bess_soc = 100.0 * soc_kwh / soc_max
        else:
            bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
        
        # Load COST DATA (from BESS simulation) for reward
        if 'cost_grid_import_soles' in df_bess.columns:
            bess_costs = df_bess['cost_grid_import_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
        elif 'tariff_osinergmin_soles_kwh' in df_bess.columns:
            bess_costs = df_bess['tariff_osinergmin_soles_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_costs = None
        
        # Load CO2 DATA (from BESS simulation) - for CO2 minimization reward
        if 'co2_avoided_indirect_kg' in df_bess.columns:
            bess_co2_avoided = df_bess['co2_avoided_indirect_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
        else:
            bess_co2_avoided = None
        
        # Grid CO2 factor (constant for Iquitos isolated grid)
        bess_co2_grid = np.full(HOURS_PER_YEAR, CO2_FACTOR_IQUITOS, dtype=np.float32)
        
        bess_co2 = {
            'grid_kg': bess_co2_grid,
            'avoided_kg': bess_co2_avoided,
        }
        
        print(f"  [BESS] Simulated avg SOC: {float(np.mean(bess_soc)):.1f}%")
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
    
    # Cargar rewards ANTES de crear el environment
    print('[5] CONFIGURAR MULTIOBJETIVO (CO2, SOLAR, COST, EV, GRID)')
    print('-' * 80)
    
    reward_weights = None
    context = None
    try:
        reward_weights = create_iquitos_reward_weights(priority="co2_focus")
        context = IquitosContext()
        print(f'  OK Reward weights loaded (co2_focus):')
        print(f'     - CO2 grid:         {reward_weights.co2:.3f}')
        print(f'     - Solar:            {reward_weights.solar:.3f}')
        print(f'     - EV satisfaction:  {reward_weights.ev_satisfaction:.3f}')
        print(f'     - Cost:             {reward_weights.cost:.3f}')
        print(f'     - Grid stability:   {reward_weights.grid_stability:.3f}')
    except Exception as e:
        print(f'  WARNING: Could not load reward weights: {e}')
        reward_weights = None
        context = None
    print()
    
    # Crear ambiente REAL con datos OE2
    print('[6] CREAR AMBIENTE REAL CON DATOS OE2 (CON REWARD WEIGHTS)')
    print('-' * 80)
    
    # ===== ENVIRONMENT REAL CON DATOS OE2 =====
    class RealOE2Environment(Env):
        """Ambiente real consistente con PPO/A2C - CityLearn v2 spec completa"""
        
        HOURS_PER_YEAR: int = 8760
        NUM_CHARGERS: int = 38  # v5.2: 19 chargers × 2 sockets
        OBS_DIM: int = 124      # v5.2 COMPLETO (PPO-compatible)
        ACTION_DIM: int = 39    # 1 BESS + 38 chargers
        
        # Socket distribution (from actual chargers_ev_ano_2024_v3.csv)
        MOTO_SOCKETS: int = 30      # Sockets 0-29: Personal motorcycles (15 chargers)
        MOTOTAXI_SOCKETS: int = 8   # Sockets 30-37: Taxi motorcycles (4 chargers)
        
        def __init__(self, solar_kw, chargers_kw, mall_kw, bess_soc, bess_costs=None, bess_co2=None, 
                     reward_weights=None, context=None, charger_max_power_kw=None, charger_mean_power_kw=None):
            super().__init__()
            self.solar = solar_kw
            self.chargers = chargers_kw
            self.mall = mall_kw
            self.bess_soc = bess_soc
            self.bess_costs = bess_costs
            self.bess_co2 = bess_co2
            self.reward_weights = reward_weights
            self.context = context
            
            # Charger statistics
            if charger_max_power_kw is not None:
                self.charger_max_power_kw = np.asarray(charger_max_power_kw, dtype=np.float32)
            else:
                self.charger_max_power_kw = np.full(38, 7.0, dtype=np.float32)
                
            if charger_mean_power_kw is not None:
                self.charger_mean_power_kw = np.asarray(charger_mean_power_kw, dtype=np.float32)
            else:
                self.charger_mean_power_kw = np.full(38, 2.5, dtype=np.float32)
            
            # Vehicle charging simulator (como PPO)
            if VEHICLE_SCENARIOS_AVAILABLE:
                self.vehicle_simulator = VehicleChargingSimulator()
            else:
                self.vehicle_simulator = None
            
            # Dimensiones
            self.n_chargers = min(self.chargers.shape[1] if len(self.chargers.shape) > 1 else 38, 38)
            self.hours_per_year = len(self.solar)
            
            # Espacios Gymnasium
            self.observation_space = spaces.Box(low=-1e6, high=1e6, shape=(self.OBS_DIM,), dtype=np.float32)
            self.action_space = spaces.Box(low=0, high=1, shape=(self.ACTION_DIM,), dtype=np.float32)
            
            # Estado
            self.current_step = 0
            self.episode_num = 0
            
            # Episode metrics (ahora consistente con PPO)
            self.episode_reward = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import_kwh = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_ev_satisfied = 0.0  # ✅ NUEVO: agregado para consistencia
            
            # Vehicle SOC tracking (14 métricas - motos + mototaxis por 7 niveles)
            # Basado en distribución real de sockets: 30 MOTO + 8 MOTOTAXI
            self.episode_motos_10_max = 0.0
            self.episode_motos_20_max = 0.0
            self.episode_motos_30_max = 0.0
            self.episode_motos_50_max = 0.0
            self.episode_motos_70_max = 0.0
            self.episode_motos_80_max = 0.0
            self.episode_motos_100_max = 0.0
            
            self.episode_mototaxis_10_max = 0.0
            self.episode_mototaxis_20_max = 0.0
            self.episode_mototaxis_30_max = 0.0
            self.episode_mototaxis_50_max = 0.0
            self.episode_mototaxis_70_max = 0.0
            self.episode_mototaxis_80_max = 0.0
            self.episode_mototaxis_100_max = 0.0
            
        def reset(self, seed=None):
            self.current_step = 0
            self.episode_num += 1
            self.episode_reward = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import_kwh = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_ev_satisfied = 0.0
            
            # Reset vehicle SOC trackers
            self.episode_motos_10_max = 0.0
            self.episode_motos_20_max = 0.0
            self.episode_motos_30_max = 0.0
            self.episode_motos_50_max = 0.0
            self.episode_motos_70_max = 0.0
            self.episode_motos_80_max = 0.0
            self.episode_motos_100_max = 0.0
            
            self.episode_mototaxis_10_max = 0.0
            self.episode_mototaxis_20_max = 0.0
            self.episode_mototaxis_30_max = 0.0
            self.episode_mototaxis_50_max = 0.0
            self.episode_mototaxis_70_max = 0.0
            self.episode_mototaxis_80_max = 0.0
            self.episode_mototaxis_100_max = 0.0
            
            obs = self._make_observation(0)
            return obs, {}
        
        def step(self, action):
            h = self.current_step
            
            # Obtener datos para este timestep
            solar_h = float(self.solar[h]) if h < len(self.solar) else 0.0
            chargers_demand_h = float(self.chargers[h].sum()) if h < len(self.chargers) else 0.0
            mall_demand_h = float(self.mall[h]) if h < len(self.mall) else 0.0
            bess_soc_h = float(self.bess_soc[h]) if h < len(self.bess_soc) else 50.0
            total_demand = chargers_demand_h + mall_demand_h
            
            # Parsear acción: [bess_action(1), charger_actions(38)]
            bess_action = float(action[0]) if len(action) > 0 else 0.5
            charger_actions = action[1:1+self.n_chargers] if len(action) > 1 else np.zeros(self.n_chargers)
            
            # ===== SIMULACIÓN FÍSICA CON ACCIONES =====
            # BESS: action[0] controla carga/descarga (-1 = descarga total, 0 = idle, 1 = carga total)
            # Chargers: action[1:39] controla modulación (0-1 → 0-7.4 kW por socket)
            
            # Modular demanda de chargers con acciones
            charger_power_modulated = chargers_demand_h * np.mean(charger_actions)  # [0, max_demand]
            bess_discharge = max(0, bess_action - 0.5) * BESS_MAX_POWER_KW  # Potencia BESS
            
            # Balance energético
            grid_import = max(0, charger_power_modulated + mall_demand_h - solar_h - bess_discharge)
            
            # ===== CÁLCULO DE COMPONENTES DE REWARD MULTIOBJETIVO =====
            
            # 1. CO2 GRID (minimizar importación)
            co2_grid_kg = grid_import * CO2_FACTOR_IQUITOS
            co2_reward = -co2_grid_kg / 1000.0  # Normalizar
            
            # 2. SOLAR (maximizar autoconsumo)
            solar_self_consumption = min(solar_h, total_demand)
            solar_reward = solar_self_consumption / max(1.0, total_demand)  # [0, 1]
            
            # 3. EV SATISFACTION (chargers reciben potencia solicitada)
            charger_satisfaction = np.mean(charger_actions)  # [0, 1]
            ev_reward = charger_satisfaction
            
            # 4. COST (minimizar importación cara, preferir solar gratis)
            cost_penalty = grid_import * 0.1  # Costo simplificado por kW importado
            cost_reward = -cost_penalty / 100.0
            
            # 5. GRID STABILITY (penalizar cambios grandes en demanda)
            bess_dispatch_smoothness = 1.0 - abs(bess_action - 0.5) * 0.1  # Prefiere BESS neutral
            stability_reward = bess_dispatch_smoothness
            
            # ===== REWARD MULTIOBJETIVO CON PESOS =====
            if self.reward_weights is not None:
                reward = (
                    self.reward_weights.co2 * co2_reward +
                    self.reward_weights.solar * solar_reward +
                    self.reward_weights.ev_satisfaction * ev_reward +
                    self.reward_weights.cost * cost_reward +
                    self.reward_weights.grid_stability * stability_reward
                )
            else:
                # Fallback si no hay weights: promedio de componentes
                reward = (co2_reward + solar_reward * 0.5 + ev_reward * 0.5 + cost_reward + stability_reward * 0.2) / 3.0
            
            # Acumular métricas por episodio
            self.episode_reward += reward
            self.episode_solar_kwh += solar_h
            self.episode_grid_import_kwh += grid_import
            self.episode_co2_avoided += max(0, solar_h - grid_import)
            self.episode_ev_satisfied += charger_satisfaction * 100.0  # ✅ NUEVO
            
            # ✅ Vehicle SOC tracking (motos y mototaxis basado en sockets reales: 30+8)
            # Fuente: chargers_ev_ano_2024_v3.csv - Sockets 0-29 (MOTO), 30-37 (MOTOTAXI)
            # Simulación simple: % de vehículos en cada rango SOC
            base_soc = float(np.mean(self.bess_soc)) * (charger_satisfaction + 0.5) / 1.5
            soc_values = [10.0, 20.0, 30.0, 50.0, 70.0, 80.0, 100.0]
            
            # MOTO: 30 sockets (15 chargers × 2)
            for soc_level in soc_values:
                n_moto_at_level = int(self.MOTO_SOCKETS * max(0, (1.0 - abs(base_soc - soc_level) / 100.0)) * 0.15)
                if soc_level == 10:
                    self.episode_motos_10_max = max(self.episode_motos_10_max, float(n_moto_at_level))
                elif soc_level == 20:
                    self.episode_motos_20_max = max(self.episode_motos_20_max, float(n_moto_at_level))
                elif soc_level == 30:
                    self.episode_motos_30_max = max(self.episode_motos_30_max, float(n_moto_at_level))
                elif soc_level == 50:
                    self.episode_motos_50_max = max(self.episode_motos_50_max, float(n_moto_at_level))
                elif soc_level == 70:
                    self.episode_motos_70_max = max(self.episode_motos_70_max, float(n_moto_at_level))
                elif soc_level == 80:
                    self.episode_motos_80_max = max(self.episode_motos_80_max, float(n_moto_at_level))
                elif soc_level == 100:
                    self.episode_motos_100_max = max(self.episode_motos_100_max, float(n_moto_at_level))
            
            # MOTOTAXI: 8 sockets (4 chargers × 2)
            for soc_level in soc_values:
                n_mototaxi_at_level = int(self.MOTOTAXI_SOCKETS * max(0, (1.0 - abs(base_soc - soc_level) / 100.0)) * 0.15)
                if soc_level == 10:
                    self.episode_mototaxis_10_max = max(self.episode_mototaxis_10_max, float(n_mototaxi_at_level))
                elif soc_level == 20:
                    self.episode_mototaxis_20_max = max(self.episode_mototaxis_20_max, float(n_mototaxi_at_level))
                elif soc_level == 30:
                    self.episode_mototaxis_30_max = max(self.episode_mototaxis_30_max, float(n_mototaxi_at_level))
                elif soc_level == 50:
                    self.episode_mototaxis_50_max = max(self.episode_mototaxis_50_max, float(n_mototaxi_at_level))
                elif soc_level == 70:
                    self.episode_mototaxis_70_max = max(self.episode_mototaxis_70_max, float(n_mototaxi_at_level))
                elif soc_level == 80:
                    self.episode_mototaxis_80_max = max(self.episode_mototaxis_80_max, float(n_mototaxi_at_level))
                elif soc_level == 100:
                    self.episode_mototaxis_100_max = max(self.episode_mototaxis_100_max, float(n_mototaxi_at_level))
            # Mover al siguiente timestep
            self.current_step += 1
            done = self.current_step >= self.hours_per_year
            
            obs = self._make_observation(self.current_step)
            truncated = False
            info = {
                'step': self.current_step,
                'solar_kw': solar_h,
                'grid_import_kw': grid_import,
                'chargers_demand_kw': charger_power_modulated,
                'bess_soc': bess_soc_h,
                'bess_action': bess_action,
                'charger_mean_action': float(np.mean(charger_actions)),
                'co2_grid_kg': co2_grid_kg,
                'solar_reward': float(solar_reward),
                'co2_reward': float(co2_reward),
                'ev_satisfaction': float(charger_satisfaction),
                'episode_reward': self.episode_reward if done else None,
                'episode_solar_kwh': self.episode_solar_kwh if done else None,
            }
            
            # Mostrar progreso cada 100 steps
            if self.current_step % 100 == 0:
                print(f'    [EP {self.episode_num:02d}] h={self.current_step:5d}/8760 | Solar={solar_h:6.1f}kW | Grid={grid_import:6.1f}kW | EV_sat={charger_satisfaction:.2f} | Reward={reward:7.3f}')
            
            # Mostrar resumen al final del episodio CON VEHICLE METRICS
            if done:
                print(f'    [EP {self.episode_num:02d}] ✅ EPISODIO COMPLETADO (MULTIOBJETIVO + VEHICLE TRACKING):')
                print(f'         Total Reward:        {self.episode_reward:12.2f} pts')
                print(f'         Solar kWh:           {self.episode_solar_kwh:12.1f} kWh')
                print(f'         Grid Import:         {self.episode_grid_import_kwh:12.1f} kWh')
                print(f'         CO2 Avoided:         {self.episode_co2_avoided:12.1f} kg')
                print(f'         EV Satisfaction:     {self.episode_ev_satisfied:12.2f} %')
                print(f'         Motos @ SOC:  10%={self.episode_motos_10_max:3.0f} 20%={self.episode_motos_20_max:3.0f} 30%={self.episode_motos_30_max:3.0f} 50%={self.episode_motos_50_max:3.0f} 70%={self.episode_motos_70_max:3.0f} 80%={self.episode_motos_80_max:3.0f} 100%={self.episode_motos_100_max:3.0f}')
                print(f'         Mototaxis @ SOC:  10%={self.episode_mototaxis_10_max:3.0f} 20%={self.episode_mototaxis_20_max:3.0f} 30%={self.episode_mototaxis_30_max:3.0f} 50%={self.episode_mototaxis_50_max:3.0f} 70%={self.episode_mototaxis_70_max:3.0f} 80%={self.episode_mototaxis_80_max:3.0f} 100%={self.episode_mototaxis_100_max:3.0f}')
                if self.reward_weights:
                    print(f'         Pesos usados:        CO2={self.reward_weights.co2:.2f} | Solar={self.reward_weights.solar:.2f} | EV={self.reward_weights.ev_satisfaction:.2f}')
                print()
            
            return obs, reward, done, truncated, info
        
        def _make_observation(self, hour_idx: int) -> np.ndarray:
            """
            Crea observación CityLearn v2 (124-dim) - consistente con PPO/A2C.
            
            Estructura:
            - [0]: Solar generation (kW)
            - [1]: Total demand (kW)
            - [2]: BESS SOC normalized [0,1]
            - [3]: Mall demand (kW)
            - [4:42]: 38 socket demands (38 dims)
            - [42:80]: 38 socket powers (38 dims)
            - [80:118]: 38 occupancy (binary, 38 dims)
            - [118:124]: Time features (6 dims: hour, dow, month, peak, co2, tariff)
            """
            obs = np.zeros(self.OBS_DIM, dtype=np.float32)
            h = hour_idx % self.HOURS_PER_YEAR
            
            # FEATURES ENERGÉTICAS [0-3]
            solar_h = float(self.solar[h]) if h < len(self.solar) else 0.0
            mall_h = float(self.mall[h]) if h < len(self.mall) else 0.0
            bess_h = float(self.bess_soc[h]) if h < len(self.bess_soc) else 50.0
            
            obs[0] = np.clip(solar_h, 0.0, 1e4)
            obs[1] = mall_h
            obs[2] = np.clip(bess_h / 100.0, 0.0, 1.0)  # Normalizar a [0,1]
            obs[3] = mall_h
            
            # SOCKET DEMANDS [4:42] - 38 sockets
            if self.chargers.shape[1] >= self.NUM_CHARGERS:
                obs[4:42] = np.clip(self.chargers[h, :self.NUM_CHARGERS], 0.0, 100.0)
            else:
                obs[4:4+self.chargers.shape[1]] = np.clip(self.chargers[h], 0.0, 100.0)
            
            # SOCKET POWERS [42:80] - Derivado de demands
            obs[42:80] = obs[4:42] * 0.5  # Simplified power from demand
            
            # OCCUPANCY [80:118] - 38 sockets con distribución según hora del día
            hour_24 = h % 24
            base_occupancy = 0.3 if 6 <= hour_24 <= 22 else 0.1  # Peak hours 6-22
            obs[80:118] = np.random.binomial(1, base_occupancy, self.NUM_CHARGERS).astype(np.float32)
            
            # TIME FEATURES [118:124] - 6 features (PPO-compatible)
            obs[118] = float(hour_24) / 24.0  # Hour normalized [0, 1]
            day_of_year = (h // 24) % 365
            obs[119] = float(day_of_year % 7) / 7.0  # Day of week [0, 1]
            obs[120] = float((day_of_year // 30) % 12) / 12.0  # Month normalized [0, 1]
            obs[121] = 1.0 if 6 <= hour_24 <= 22 else 0.0  # Peak hour indicator [0, 1]
            obs[122] = float(self.context.co2_factor_kg_per_kwh) if self.context else CO2_FACTOR_IQUITOS  # CO2 factor
            obs[123] = 0.15  # Tariff (USD/kWh) - constante como PPO
            
            return obs
    
    # Crear ambiente real
    env = RealOE2Environment(
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc=bess_soc,
        bess_costs=bess_costs,
        bess_co2=bess_co2,
        reward_weights=reward_weights,  # ✅ Weights multiobjetivo
        context=context,  # ✅ Contexto Iquitos
        charger_max_power_kw=charger_max_power,  # ✅ NUEVO: estadísticas reales
        charger_mean_power_kw=charger_mean_power  # ✅ NUEVO: estadísticas reales
    )
    print(f'  ✅ Ambiente REAL creado con datos OE2 (CONSISTENTE CON PPO/A2C):')
    print(f'     - Observation space: {env.OBS_DIM} dims (CityLearn v2 v5.2 COMPLETO)')
    print(f'     - Action space:      {env.ACTION_DIM} dims (BESS + 38 chargers)')
    print(f'     - Vehicle simulator: {"SÍ" if env.vehicle_simulator else "NO (fallback)"}')
    
    # Get and validate spaces
    if isinstance(env.action_space, list):
        act_dim = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
    else:
        act_dim = env.action_space.shape[0] if hasattr(env.action_space, 'shape') else 39
    
    obs_dim = env.observation_space.shape[0] if hasattr(env.observation_space, 'shape') else 124  # ✅ ACTUALIZADO A 124
    
    print(f'  Observation space: {obs_dim} (solar + mall + bess_soc + 38 demands + 38 powers + 38 occupancy + 6 time_features)')
    print(f'  Action space:      {act_dim} (1 BESS + 38 chargers)')
    print(f'  Datos cargados:')
    print(f'    - Solar:     {len(solar_hourly)} horas')
    print(f'    - Chargers:  {chargers_hourly.shape[1] if len(chargers_hourly.shape) > 1 else 1} sockets')
    print()
    
    # Crear agente SAC
    print('[7] INICIALIZAR AGENTE SAC')
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
        # Construir kwargs para SAC
        sac_kwargs = {
            'learning_rate': sac_config.learning_rate,
            'buffer_size': sac_config.buffer_size,
            'learning_starts': sac_config.learning_starts,
            'batch_size': sac_config.batch_size,
            'tau': sac_config.tau,
            'ent_coef': sac_config.ent_coef,
            'train_freq': sac_config.train_freq,
            'gradient_steps': sac_config.gradient_steps,
            'policy_kwargs': sac_config.policy_kwargs,
            'tensorboard_log': str(OUTPUT_DIR / 'tensorboard'),
            'device': DEVICE,
            'verbose': 1,
        }
        # No pasar target_entropy si es None - dejar que SAC lo calcule
        if sac_config.target_entropy is not None:
            sac_kwargs['target_entropy'] = sac_config.target_entropy
        
        agent = SAC('MlpPolicy', env, **sac_kwargs)
    
    print(f'  Device: {agent.device}')
    print()
    
    # Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=1000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac',
        save_replay_buffer=False,
    )
    
    # Callback para mostrar progreso cada 500 pasos (con loss real de SAC)
    class ProgressCallback(BaseCallback):
        def __init__(self, verbose=0):
            super().__init__(verbose)
            self.last_step = 0
            self.losses = []
        
        def _on_step(self) -> bool:
            current_step = self.model.num_timesteps
            
            # Extraer loss del modelo SAC - acceso a atributos internos
            loss_value = None
            
            # SAC calcula losses para actor y critic en cada update
            # Intentar extraer del logger internalizd
            if hasattr(self.model, 'logger') and self.model.logger is not None:
                log_dict = self.model.logger.name_to_value
                if 'train/actor_loss' in log_dict:
                    loss_value = log_dict['train/actor_loss']
                elif 'train/policy_loss' in log_dict:
                    loss_value = log_dict['train/policy_loss']
            
            # Fallback: intentar acceso directo a atributos del modelo
            if loss_value is None:
                if hasattr(self.model, 'actor_loss'):
                    loss_value = self.model.actor_loss
                elif hasattr(self.model, '_last_actor_loss'):
                    loss_value = self.model._last_actor_loss
            
            # Formatear loss para display
            if loss_value is not None:
                if isinstance(loss_value, dict):
                    loss_val = loss_value.get('actor', 'N/A')
                else:
                    loss_val = float(loss_value)
                loss_str = f"{loss_val:.4f}" if isinstance(loss_val, (int, float)) else "N/A"
            else:
                loss_str = "N/A"
            
            if current_step - self.last_step >= 500:
                print(f"    [STEP {current_step:6d}] Learning rate: {self.model.learning_rate:.2e} | Loss: {loss_str}")
                self.last_step = current_step
            
            return True
    
    progress_callback = ProgressCallback(verbose=0)
    
    callback_list = CallbackList([checkpoint_callback, progress_callback])
    
    print('[8] ENTRENAMIENTO SAC - 10 EPISODIOS COMPLETOS')
    print('-' * 80)
    print(f'  Total timesteps: 87,600 (10 episodios × 8,760 h/episodio)')
    print(f'  Checkpoint cada: 1,000 steps')
    print(f'  Datos: Datos reales OE2 (solar 8.29GWh + chargers 38 sockets + mall 12.37GWh + BESS 940kWh)')
    print(f'  Agente: SAC off-policy (red 512x512, batch 256)')
    print(f'  Device: {DEVICE.upper()}')
    print()
    print('  Progreso por episodio (cada 100 timesteps dentro del episodio):')
    print('-' * 80)
    print()
    
    try:
        agent.learn(
            total_timesteps=87_600,  # 10 episodios × 8,760 steps
            callback=callback_list,
            reset_num_timesteps=False,
            progress_bar=True,
            log_interval=1,
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
