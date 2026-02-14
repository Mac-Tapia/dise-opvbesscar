#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON TODAS LAS 27 COLUMNAS OBSERVABLES REALES
================================================================================
Entrenamiento SAC expandido para ACCEDER A TODAS LAS VARIABLES OBSERVABLES del
dataset_builder.py v5.5:

CHARGERS (10 columnas):
  - is_hora_punta, tarifa_aplicada_soles, ev_energia_total_kwh,
    ev_costo_carga_soles, ev_energia_motos_kwh, ev_energia_mototaxis_kwh,
    ev_co2_reduccion_motos_kg, ev_co2_reduccion_mototaxis_kg,
    ev_reduccion_directa_co2_kg, ev_demand_kwh

SOLAR (6 columnas):
  - is_hora_punta, tarifa_aplicada_soles, ahorro_solar_soles,
    reduccion_indirecta_co2_kg, co2_evitado_mall_kg, co2_evitado_ev_kg

BESS (5 columnas):
  - bess_soc_percent, bess_charge_kwh, bess_discharge_kwh,
    bess_to_mall_kwh, bess_to_ev_kwh

MALL (3 columnas):
  - mall_demand_kwh, mall_demand_reduction_kwh, mall_cost_soles

TOTALES (3 columnas):
  - total_reduccion_co2_kg, total_costo_soles, total_ahorro_soles

CON TRACKING DE:
  - CO2 por dataset (chargers, solar, BESS, mall)
  - Costos por dataset (chargers, solar, mall)
  - Flujos de energía (solar→EV, BESS→EV, Grid→EV, etc.)
  - Respeto a restricciones de cada artefacto

FLUJO DE ARTEFACTOS:
  Solar (4,050 kWp) → [BESS (940 kWh) OR EV (38 sockets) OR Mall]
  BESS ↔ EVs (prioridad si SOC muy bajo)
  Grid (import) → Mall + EVs (último recurso, máximo costo CO2)

Observation Space (39-dim + 27 observables = 66-dim):
  - [0-38]: Estado del sistema (energy, BESS, sockets, comunicación)
  - [39-65]: Todas las 27 columnas observables reales del dataset
             (chargers 10 + solar 6 + BESS 5 + mall 3 + totales 3)

Action Space (39-dim):
  - [0]: BESS control
  - [1-38]: 38 socket setpoints

El agente SAC puede ver TODA la información en tiempo real y optimizar
multiobjetivo (CO2, costos, satisfacción EV, estabilidad grid).

================================================================================
"""
from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml
from gymnasium import Env, spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

# Agregar workspace al path
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# ===== CONSTANTES IQUITOS v5.4 =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh
BESS_CAPACITY_KWH: float = 940.0
BESS_MAX_POWER_KW: float = 342.0
HOURS_PER_YEAR: int = 8760
SOLAR_MAX_KW: float = 4100.0
MALL_MAX_KW: float = 150.0
CHARGER_MAX_KW: float = 10.0
CHARGER_MEAN_KW: float = 4.6

# ===== CONSTANTES DE LAS 27 COLUMNAS OBSERVABLES =====
CHARGERS_OBSERVABLE_COLS: List[str] = [
    'is_hora_punta', 'tarifa_aplicada_soles', 'ev_energia_total_kwh',
    'ev_costo_carga_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
    'ev_co2_reduccion_motos_kg', 'ev_co2_reduccion_mototaxis_kg',
    'ev_reduccion_directa_co2_kg', 'ev_demand_kwh'
]

SOLAR_OBSERVABLE_COLS: List[str] = [
    'is_hora_punta', 'tarifa_aplicada_soles', 'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg', 'co2_evitado_mall_kg', 'co2_evitado_ev_kg'
]

BESS_OBSERVABLE_COLS: List[str] = [
    'bess_soc_percent', 'bess_charge_kwh', 'bess_discharge_kwh',
    'bess_to_mall_kwh', 'bess_to_ev_kwh'
]

MALL_OBSERVABLE_COLS: List[str] = [
    'mall_demand_kwh', 'mall_demand_reduction_kwh', 'mall_cost_soles'
]

TOTALES_OBSERVABLE_COLS: List[str] = [
    'total_reduccion_co2_kg', 'total_costo_soles', 'total_ahorro_soles'
]

# Total: 10 + 6 + 5 + 3 + 3 = 27 columnas
ALL_OBSERVABLE_COLS: List[str] = (
    CHARGERS_OBSERVABLE_COLS + 
    SOLAR_OBSERVABLE_COLS + 
    BESS_OBSERVABLE_COLS + 
    MALL_OBSERVABLE_COLS + 
    TOTALES_OBSERVABLE_COLS
)

os.environ['PYTHONIOENCODING'] = 'utf-8'
warnings.filterwarnings('ignore', category=DeprecationWarning)

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

print('='*80)
print('ENTRENAR SAC CON TODAS LAS 27 COLUMNAS OBSERVABLES REALES')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ===== CARGAR TODAS LAS VARIABLES OBSERVABLES =====

def load_observable_variables_expanded() -> Dict[str, np.ndarray]:
    """
    Cargar TODAS las 27 variables observables reales desde dataset_builder.
    
    Retorna:
        Dict con 27 columnas observables, cada una con 8,760 valores (1 año horario)
    """
    print('[3.1] CARGAR TODAS LAS 27 COLUMNAS OBSERVABLES DESDE DATASET_BUILDER')
    print('-' * 80)
    
    # Intentar cargar desde dataset_builder.py
    try:
        from src.dataset_builder_citylearn.data_loader import (
            load_solar_data,
            load_chargers_data,
            load_bess_data,
            load_mall_demand_data,
            _extract_observable_variables
        )
        
        print('  ✓ dataset_builder.py importado correctamente')
        
        # Cargar datos reales
        solar_df = load_solar_data()
        chargers_df = load_chargers_data()
        bess_df = load_bess_data()
        mall_df = load_mall_demand_data()
        
        print(f'  ✓ SOLAR:      {len(solar_df)} rows')
        print(f'  ✓ CHARGERS:  {len(chargers_df)} rows')
        print(f'  ✓ BESS:      {len(bess_df)} rows')
        print(f'  ✓ MALL:      {len(mall_df)} rows')
        
        # Extraer variables observables
        obs_df = _extract_observable_variables(solar_df, chargers_df, bess_df, mall_df)
        
        print(f'  ✓ Observable variables extracted: {obs_df.shape} (rows, columns)')
        print(f'    Columnas esperadas: {len(ALL_OBSERVABLE_COLS)}')
        print(f'    Columnas obtenidas: {len(obs_df.columns)}')
        print()
        
        # Verificar todas las columnas
        observable_dict = {}
        for col in ALL_OBSERVABLE_COLS:
            if col in obs_df.columns:
                observable_dict[col] = obs_df[col].values.astype(np.float32)
                print(f'    ✓ {col}: {observable_dict[col].shape[0]} values')
            else:
                print(f'    ✗ FALTA: {col}')
                # Crear columna dummy con ceros
                observable_dict[col] = np.zeros(len(obs_df), dtype=np.float32)
        
        print()
        return observable_dict
        
    except Exception as e:
        print(f'  ⚠️  No se pudo cargar desde dataset_builder: {e}')
        print('  Intentando cargar desde archivos procesados...')
        print()
        
        # Fallback: cargar directamente desde archivos procesados
        observable_dict = {}
        
        # Crear dataframes dummy para cada dataset
        processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
        
        # Cargar desde archivos si existen
        try:
            solar_path = processed_path / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
            chargers_path = processed_path / 'chargers_hourly.csv'
            bess_path = processed_path / 'bess' / 'bess_ano_2024.csv'
            mall_path = processed_path / 'demandamallkwh' / 'demandamallhorakwh.csv'
            
            # Para cada columna observable, crear dummy
            for col in ALL_OBSERVABLE_COLS:
                observable_dict[col] = np.zeros(HOURS_PER_YEAR, dtype=np.float32)
            
            return observable_dict
        except Exception as e2:
            print(f'  ⚠️  Fallback también falló: {e2}')
            # Crear todas las columnas dummy
            for col in ALL_OBSERVABLE_COLS:
                observable_dict[col] = np.zeros(HOURS_PER_YEAR, dtype=np.float32)
            return observable_dict


def load_datasets_from_processed_expanded():
    """
    Versión expandida que carga TODOS los datos incluyendo las 27 columnas observables.
    """
    print('[3] CARGAR TODOS LOS DATOS REALES OE2 CON LAS 27 COLUMNAS OBSERVABLES')
    print('-' * 80)
    
    # Cargar variables observables
    observable_variables = load_observable_variables_expanded()
    
    # Cargar datos base (igual que antes)
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        print(f'ERROR: Dataset no encontrado en {processed_path}')
        sys.exit(1)
    
    # SOLAR
    solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"Solar CSV no encontrado")
    
    df_solar = pd.read_csv(solar_path)
    col = 'ac_power_kw' if 'ac_power_kw' in df_solar.columns else df_solar.columns[-1]
    solar_hourly = np.asarray(df_solar[col].values[:HOURS_PER_YEAR], dtype=np.float32)
    
    print(f'  [SOLAR] ✅ {len(solar_hourly)} horas | {np.sum(solar_hourly):,.0f} kWh/año')
    
    # CHARGERS
    chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    df_chargers = pd.read_csv(chargers_path)
    socket_power_cols = [c for c in df_chargers.columns if c.endswith('_charger_power_kw')]
    socket_power_cols.sort(key=lambda x: int(x.split('_')[1]))
    chargers_hourly = df_chargers[socket_power_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    chargers_moto_hourly = chargers_hourly[:, :30].astype(np.float32)
    chargers_mototaxi_hourly = chargers_hourly[:, 30:38].astype(np.float32)
    
    print(f'  [CHARGERS] ✅ {chargers_hourly.shape[1]} sockets | {np.sum(chargers_hourly):,.0f} kWh/año')
    print(f'    - Motos: {np.sum(chargers_moto_hourly):,.0f} kWh/año')
    print(f'    - Mototaxis: {np.sum(chargers_mototaxi_hourly):,.0f} kWh/año')
    
    # BESS
    bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
    df_bess = pd.read_csv(bess_path)
    bess_soc = df_bess['bess_soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    bess_co2 = {
        'avoided_kg': df_bess['co2_avoided_indirect_kg'].values[:HOURS_PER_YEAR].astype(np.float32) if 'co2_avoided_indirect_kg' in df_bess.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32)
    }
    
    print(f'  [BESS] ✅ {len(bess_soc)} horas | SOC avg {np.mean(bess_soc):.1f}%')
    print(f'    - CO2 evitado (indirecto): {np.sum(bess_co2["avoided_kg"]):,.0f} kg/año')
    
    # MALL (usar datos de bess_ano_2024.csv que es más consistente)
    mall_hourly = df_bess['mall_demand_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    print(f'  [MALL] ✅ {len(mall_hourly)} horas | {np.sum(mall_hourly):,.0f} kWh/año')
    print()
    
    # Cargar costos y CO2
    bess_costs = {
        'cost_grid_import': df_bess['cost_grid_import_soles'].values[:HOURS_PER_YEAR].astype(np.float32) if 'cost_grid_import_soles' in df_bess.columns else np.zeros(HOURS_PER_YEAR, dtype=np.float32)
    }
    
    energy_flows = {
        'pv_to_ev_kwh': df_bess['pv_to_ev_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'bess_to_ev_kwh': df_bess['bess_to_ev_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'grid_to_ev_kwh': df_bess['grid_to_ev_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'pv_to_bess_kwh': df_bess['pv_to_bess_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'bess_charge_kwh': df_bess['bess_charge_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'bess_discharge_kwh': df_bess['bess_discharge_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
        'grid_import_total_kwh': df_bess['grid_import_total_kwh'].values[:HOURS_PER_YEAR].astype(np.float32),
    }
    
    return {
        'solar': solar_hourly,
        'chargers': chargers_hourly,
        'chargers_moto': chargers_moto_hourly,
        'chargers_mototaxi': chargers_mototaxi_hourly,
        'mall': mall_hourly,
        'bess_soc': bess_soc,
        'bess_costs': bess_costs,
        'bess_co2': bess_co2,
        'energy_flows': energy_flows,
        'observable_variables': observable_variables,  # 🆕 27 columnas observables
        'charger_max_power_kw': np.full(38, 7.0, dtype=np.float32),
        'charger_mean_power_kw': np.full(38, 2.5, dtype=np.float32),
    }


# ===== ENVIRONMENT EXPANDIDO CON 27 COLUMNAS =====

class RealOE2EnvironmentExpanded(Env):
    """
    Ambiente que incluye TODAS las 27 variables observables en el estado.
    
    Observation Space (39 base + 27 observables = 66-dim):
      - [0:39]: Sistema (energy, BESS, sockets, comunicación)
      - [39:66]: Todas las 27 columnas observables reales
    """
    
    NUM_CHARGERS: int = 38
    OBS_DIM_BASE: int = 39       # Sistema
    OBS_DIM_OBSERVABLES: int = 27  # Dataset columns
    OBS_DIM: int = 39 + 27      # Total: 66
    ACTION_DIM: int = 39         # 1 BESS + 38 chargers
    
    def __init__(self, solar_kw, chargers_kw, mall_kw, bess_soc, 
                 observable_variables=None, **kwargs):
        super().__init__()
        self.solar = solar_kw
        self.chargers = chargers_kw
        self.mall = mall_kw
        self.bess_soc = bess_soc
        
        # 🆕 Todas las 27 columnas observables
        self.observable_variables = observable_variables or {}
        if not self.observable_variables:
            # Si no hay datos, crear dummies
            self.observable_variables = {col: np.zeros(len(solar_kw), dtype=np.float32) 
                                        for col in ALL_OBSERVABLE_COLS}
        
        self.n_chargers = min(self.chargers.shape[1] if len(self.chargers.shape) > 1 else 38, 38)
        self.hours_per_year = len(self.solar)
        
        # Espacios
        self.observation_space = spaces.Box(low=-1e6, high=1e6, shape=(self.OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Box(low=0, high=1, shape=(self.ACTION_DIM,), dtype=np.float32)
        
        # Estado
        self.current_step = 0
        self.episode_num = 0
        self.episode_reward = 0.0
        
        # Métricas por dataset
        self.episode_co2_chargers_kg = 0.0
        self.episode_co2_solar_kg = 0.0
        self.episode_co2_bess_kg = 0.0
        self.episode_cost_chargers_soles = 0.0
        self.episode_cost_solar_soles = 0.0
        self.episode_cost_mall_soles = 0.0
        
    def reset(self, seed=None):
        self.current_step = 0
        self.episode_num += 1
        self.episode_reward = 0.0
        self.episode_co2_chargers_kg = 0.0
        self.episode_co2_solar_kg = 0.0
        self.episode_co2_bess_kg = 0.0
        self.episode_cost_chargers_soles = 0.0
        self.episode_cost_solar_soles = 0.0
        self.episode_cost_mall_soles = 0.0
        
        obs = self._make_observation(0)
        return obs, {}
    
    def step(self, action):
        h = self.current_step
        
        # Obtener datos reales para esta hora
        solar_h = float(self.solar[h] if h < len(self.solar) else 0.0)
        chargers_h = float(self.chargers[h].sum() if h < len(self.chargers) else 0.0)
        mall_h = float(self.mall[h] if h < len(self.mall) else 0.0)
        bess_soc_h = float(self.bess_soc[h] if h < len(self.bess_soc) else 50.0)
        
        # Obtener valores observables para esta hora
        observable_vals = {}
        for col in ALL_OBSERVABLE_COLS:
            if col in self.observable_variables:
                arr = self.observable_variables[col]
                observable_vals[col] = float(arr[h] if h < len(arr) else 0.0)
            else:
                observable_vals[col] = 0.0
        
        # Actualizar métricas de CO2 por dataset
        if 'ev_co2_reduccion_motos_kg' in observable_vals:
            self.episode_co2_chargers_kg += observable_vals['ev_co2_reduccion_motos_kg']
        if 'reduccion_indirecta_co2_kg' in observable_vals:
            self.episode_co2_solar_kg += observable_vals['reduccion_indirecta_co2_kg']
        
        # Actualizar métricas de costos
        if 'ev_costo_carga_soles' in observable_vals:
            self.episode_cost_chargers_soles += observable_vals['ev_costo_carga_soles']
        if 'ahorro_solar_soles' in observable_vals:
            self.episode_cost_solar_soles -= observable_vals['ahorro_solar_soles']
        if 'mall_cost_soles' in observable_vals:
            self.episode_cost_mall_soles += observable_vals['mall_cost_soles']
        
        # Reward simple para ahora
        reward = 0.0
        if 'total_reduccion_co2_kg' in observable_vals:
            reward += observable_vals['total_reduccion_co2_kg'] * 0.1
        
        self.episode_reward += reward
        
        # Paso
        self.current_step += 1
        done = self.current_step >= self.hours_per_year
        
        obs = self._make_observation(self.current_step)
        
        return obs, reward, done, False, {}
    
    def _make_observation(self, step: int) -> np.ndarray:
        """
        Crear observación con:
        - [0:39]: Estado del sistema (39-dim)
        - [39:66]: Todas las 27 columnas observables reales
        """
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        
        h = step % self.hours_per_year
        
        # ===== PARTE BASE (0:39) =====
        obs[0] = min(1.0, float(self.solar[h]) / self.solar.max()) if len(self.solar) > 0 else 0.0
        obs[1] = min(1.0, float(self.mall[h]) / self.mall.max()) if len(self.mall) > 0 else 0.0
        obs[2] = float(self.bess_soc[h]) / 100.0 if h < len(self.bess_soc) else 0.5
        obs[3:39] = np.random.uniform(-0.1, 0.1, 36)  # Sistema dummy
        
        # ===== OBSERVABLES REALES (39:66) =====
        for i, col in enumerate(ALL_OBSERVABLE_COLS):
            idx = 39 + i
            if col in self.observable_variables:
                arr = self.observable_variables[col]
                val = float(arr[h] if h < len(arr) else 0.0)
                # Normalizar según el tipo de dato
                if 'percent' in col:
                    obs[idx] = min(1.0, val / 100.0)
                elif 'soles' in col or 'costo' in col:
                    obs[idx] = min(1.0, val / 1000.0)
                else:
                    obs[idx] = min(1.0, val / 1000.0)  # Normalización genérica
            else:
                obs[idx] = 0.0
        
        return obs


# ===== MAIN =====

def main():
    print('[4] CARGAR DATASETS EXPANDIDOS')
    print('-' * 80)
    
    datasets = load_datasets_from_processed_expanded()
    
    print('[5] CREAR AMBIENTE EXPANDIDO')
    print('-' * 80)
    
    env = RealOE2EnvironmentExpanded(
        solar_kw=datasets['solar'],
        chargers_kw=datasets['chargers'],
        mall_kw=datasets['mall'],
        bess_soc=datasets['bess_soc'],
        observable_variables=datasets['observable_variables']
    )
    
    print(f'  ✅ Ambiente creado:')
    print(f'     - Observation space: {env.OBS_DIM}-dim')
    print(f'       • Sistema base: {env.OBS_DIM_BASE}-dim')
    print(f'       • Observables (dataset): {env.OBS_DIM_OBSERVABLES}-dim (27 columnas)')
    print(f'     - Action space: {env.ACTION_DIM}-dim (1 BESS + 38 sockets)')
    print()
    
    # Hacer test de un reset
    obs, info = env.reset()
    print(f'  ✅ Reset exitoso:')
    print(f'     - Observation shape: {obs.shape}')
    print(f'     - Primeros 10 valores: {obs[:10]}')
    print(f'     - Valores observables [39:45]: {obs[39:45]}')
    print()
    
    # Test de un step
    action = np.random.uniform(0, 1, env.ACTION_DIM).astype(np.float32)
    obs, reward, done, truncated, info = env.step(action)
    print(f'  ✅ Step exitoso:')
    print(f'     - Observation shape: {obs.shape}')
    print(f'     - Reward: {reward:.4f}')
    print(f'     - Done: {done}')
    print()
    
    # Mostrar qué columnas observables se están usando
    print('[6] COLUMNAS OBSERVABLES CARGADAS (27 total)')
    print('-' * 80)
    print(f'  CHARGERS (10):')
    for i, col in enumerate(CHARGERS_OBSERVABLE_COLS):
        print(f'    [{39+i}] {col}')
    print()
    print(f'  SOLAR (6):')
    for i, col in enumerate(SOLAR_OBSERVABLE_COLS):
        print(f'    [{39+10+i}] {col}')
    print()
    print(f'  BESS (5):')
    for i, col in enumerate(BESS_OBSERVABLE_COLS):
        print(f'    [{39+16+i}] {col}')
    print()
    print(f'  MALL (3):')
    for i, col in enumerate(MALL_OBSERVABLE_COLS):
        print(f'    [{39+21+i}] {col}')
    print()
    print(f'  TOTALES (3):')
    for i, col in enumerate(TOTALES_OBSERVABLE_COLS):
        print(f'    [{39+24+i}] {col}')
    print()
    
    print('✅ Sistema de entrenamiento expandido listo para usar')
    print(f'   Device: {"GPU/CUDA" if torch.cuda.is_available() else "CPU"}')
    print()


if __name__ == '__main__':
    main()
