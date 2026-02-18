#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR A2C CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
NO se usa ninguna formula de aproximacion - SOLO DATOS REALES
"""
from __future__ import annotations

# ===== CONFIGURACION DE PATH (OBLIGATORIO AL INICIO) =====
# Debe estar ANTES de cualquier import para evitar ModuleNotFoundError
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# =========================================================

import json
import logging
import os
import time
import traceback
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import yaml
from gymnasium import Env, spaces
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)
from src.agents.training_validation import validate_agent_config

# Data loader v5.8 - Centralizado con validación automática y fallbacks
from src.dataset_builder_citylearn.data_loader import (
    rebuild_oe2_datasets_complete,
    load_citylearn_dataset,
    BESS_CAPACITY_KWH,      # Constante centralizada (2,000 kWh verificado)
    BESS_MAX_POWER_KW,      # 400 kW
    N_CHARGERS,             # 19 chargers
    TOTAL_SOCKETS,          # 38 sockets
    SOLAR_PV_KWP,           # 4,050 kWp
    CO2_FACTOR_GRID_KG_PER_KWH,  # 0.4521 kg CO2/kWh
    CO2_FACTOR_EV_KG_PER_KWH,    # 2.146 kg CO2/kWh
    OE2ValidationError,
)

# ===== CONSTANTES IQUITOS v5.8 (2026-02-18) CON COMUNICACION SISTEMA =====
# CRÍTICO: BESS_CAPACITY_KWH actualizado a 2000.0 kWh (verificado contra bess_ano_2024.csv)
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid termico aislado)
# BESS_CAPACITY_KWH importado de data_loader (2,000 kWh verificado)
# BESS_MAX_POWER_KW importado de data_loader (400 kW)
HOURS_PER_YEAR: int = 8760

# v5.3: Constantes para normalizacion de observaciones
# SOLAR_MAX_KW: pico real de generacion solar observado en datos (2,887 kW)
SOLAR_MAX_KW: float = 2887.0        # Max real observado en solar timeseries
MALL_MAX_KW: float = 3000.0         # Real max=2,763 kW from data/oe2/demandamallkwh/demandamallhorakwh.csv [FIXED 2026-02-15]
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (referencia normalizacion)
CHARGER_MAX_KW: float = 10.0        # Max por socket (7.4 kW nominal, 10 kW margen)
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket

# ===== CONSTANTES DE VEHICULOS Y CO2 DIRECTO v7.2 (2026-02-17) =====
# DATOS REALES del dataset EV - NO APROXIMACIONES
# La reduccion DIRECTA de CO2 es proporcional a energia cargada:
#   - Motos: 4.6 kWh bateria, factor 0.87 kg CO2/kWh (vs gasolina)
#   - Mototaxis: 7.4 kWh bateria, factor 0.47 kg CO2/kWh (vs gasolina)
# Energia necesaria para cargar (desde 20% SOC de llegada a 80% SOC objetivo):
#   - Motos: (80-20)% × 4.6 kWh × (1/0.95 eficiencia) = 2.90 kWh
#   - Mototaxis: (80-20)% × 7.4 kWh × (1/0.95 eficiencia) = 4.68 kWh
MOTOS_TARGET_DIARIOS: int = 270     # Motos por día (Iquitos)
MOTOTAXIS_TARGET_DIARIOS: int = 39  # Mototaxis por día (Iquitos)
VEHICLES_TARGET_DIARIOS: int = MOTOS_TARGET_DIARIOS + MOTOTAXIS_TARGET_DIARIOS  # 309 total

MOTO_BATTERY_KWH: float = 4.6       # Capacidad bateria moto (kWh)
MOTOTAXI_BATTERY_KWH: float = 7.4   # Capacidad bateria mototaxi (kWh)
MOTO_SOC_ARRIVAL: float = 0.20      # SOC al llegar (20%)
MOTO_SOC_TARGET: float = 0.80       # SOC objetivo (80%)
MOTO_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTO_BATTERY_KWH / 0.95  # ~2.90 kWh
MOTOTAXI_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTOTAXI_BATTERY_KWH / 0.95  # ~4.68 kWh

CO2_FACTOR_MOTO_KG_KWH: float = 0.87      # kg CO2 por kWh cargado (moto vs gasolina)
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.47  # kg CO2 por kWh cargado (mototaxi vs gasolina)

# ===== COLUMNAS REALES COMPLETAS DE CADA DATASET OE2 v7.0 (2026-02-14) =====
# TODAS las columnas de cada dataset - SIN OMITIR NINGUNA

# 1. CHARGERS - 353 columnas totales (data/oe2/chargers/chargers_ev_ano_2024_v3.csv)
#    4 columnas agregadas + 39 sockets × 9 columnas cada uno
CHARGERS_AGGREGATE_COLS: List[str] = [
    'costo_carga_ev_soles',         # Costo total de carga EV en soles
    'co2_reduccion_motos_kg',       # Reduccion DIRECTA CO2 por motos (factor 0.87)
    'co2_reduccion_mototaxis_kg',   # Reduccion DIRECTA CO2 por mototaxis (factor 0.47)
    'reduccion_directa_co2_kg',     # Reduccion DIRECTA CO2 total EV
]

# Columnas por socket (XXX = 000-038): 9 columnas × 39 sockets = 351 columnas
CHARGERS_SOCKET_COLS_TEMPLATE: List[str] = [
    'socket_{:03d}_charger_power_kw',    # Potencia maxima del socket (7.4 kW)
    'socket_{:03d}_battery_kwh',         # Capacidad bateria del vehiculo
    'socket_{:03d}_vehicle_type',        # Tipo: moto, mototaxi
    'socket_{:03d}_soc_current',         # SOC actual [0-1]
    'socket_{:03d}_soc_arrival',         # SOC al llegar
    'socket_{:03d}_soc_target',          # SOC objetivo (tipico 1.0)
    'socket_{:03d}_active',              # 1 si hay vehiculo, 0 si libre
    'socket_{:03d}_charging_power_kw',   # Potencia actual de carga
    'socket_{:03d}_vehicle_count',       # Conteo acumulado de vehiculos
]

# 2. BESS - 25 columnas (data/oe2/bess/bess_ano_2024.csv)
BESS_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'pv_generation_kwh',                 # Generacion solar total
    'ev_demand_kwh',                     # Demanda EV total
    'mall_demand_kwh',                   # Demanda mall
    'pv_to_ev_kwh',                      # Solar directo a EV (cascada prioridad 1)
    'pv_to_bess_kwh',                    # Solar a BESS (cascada prioridad 2)
    'pv_to_mall_kwh',                    # Solar a mall (cascada prioridad 3)
    'pv_curtailed_kwh',                  # Solar perdido (excedente sin uso)
    'bess_charge_kwh',                   # Energia cargada al BESS
    'bess_discharge_kwh',                # Energia descargada del BESS
    'bess_to_ev_kwh',                    # BESS directo a EV (prioridad 1)
    'bess_to_mall_kwh',                  # BESS a mall (prioridad 2)
    'grid_to_ev_kwh',                    # Grid a EV (ultimo recurso)
    'grid_to_mall_kwh',                  # Grid a mall
    'grid_to_bess_kwh',                  # Grid a BESS (nunca en diseno actual)
    'grid_import_total_kwh',             # Import total del grid
    'bess_soc_percent',                  # SOC del BESS [20-100]%
    'bess_mode',                         # Modo: idle, charging, discharging
    'tariff_osinergmin_soles_kwh',       # Tarifa dinamica OSINERGMIN
    'cost_grid_import_soles',            # Costo de importacion grid
    'peak_reduction_savings_soles',      # Ahorro por reduccion de picos
    'peak_reduction_savings_normalized', # Ahorro normalizado [0-1]
    'co2_avoided_indirect_kg',           # CO2 INDIRECTO evitado por BESS/Solar
    'co2_avoided_indirect_normalized',   # CO2 indirecto normalizado [0-1]
    'mall_grid_import_kwh',              # Import grid solo para mall
]

# 3. SOLAR - 16 columnas (data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv)
SOLAR_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'irradiancia_ghi',                   # Irradiancia GHI (W/m2)
    'temperatura_c',                     # Temperatura ambiente (C)
    'velocidad_viento_ms',               # Velocidad viento (m/s)
    'potencia_kw',                       # Potencia generada (kW)
    'energia_kwh',                       # Energia generada (kWh)
    'is_hora_punta',                     # 1 si hora punta (18-22h)
    'hora_tipo',                         # HP o HFP
    'tarifa_aplicada_soles',             # Tarifa aplicada (soles/kWh)
    'ahorro_solar_soles',                # Ahorro por usar solar (soles)
    'reduccion_indirecta_co2_kg',        # CO2 INDIRECTO evitado por solar
    'energia_suministrada_al_bess_kwh',  # Solar a BESS
    'energia_suministrada_al_ev_kwh',    # Solar a EV
    'energia_suministrada_al_mall_kwh',  # Solar a mall
    'energia_suministrada_a_red_kwh',    # Solar exportado a red (curtailed)
    'reduccion_indirecta_co2_kg_total',  # CO2 indirecto total
]

# 4. MALL - 6 columnas (data/oe2/demandamallkwh/demandamallhorakwh.csv)
MALL_REAL_COLS: List[str] = [
    'datetime',                          # Timestamp
    'mall_demand_kwh',                   # Demanda del mall (kWh)
    'mall_co2_indirect_kg',              # CO2 INDIRECTO por demanda mall
    'is_hora_punta',                     # 1 si hora punta
    'tarifa_soles_kwh',                  # Tarifa mall (soles/kWh)
    'mall_cost_soles',                   # Costo mall (soles)
]

# ===== SELECCION DE COLUMNAS PARA OBSERVACIONES v7.0 =====
# 210 features observables del sistema completo

# CHARGERS observables: 4 agregadas + 39 × 4 (soc_current, active, charging_power, vehicle_count) = 160
CHARGERS_OBS_AGGREGATE: List[str] = CHARGERS_AGGREGATE_COLS  # 4
CHARGERS_OBS_PER_SOCKET: List[str] = ['soc_current', 'active', 'charging_power_kw', 'vehicle_count']  # 4 × 39 = 156

# BESS observables: 12 columnas numericas clave
BESS_OBS_COLS: List[str] = [
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
    'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'bess_soc_percent', 'tariff_osinergmin_soles_kwh', 
    'co2_avoided_indirect_kg', 'peak_reduction_savings_soles'
]  # 12

# SOLAR observables: 10 columnas numericas clave
SOLAR_OBS_COLS: List[str] = [
    'irradiancia_ghi', 'temperatura_c', 'potencia_kw', 'energia_kwh',
    'is_hora_punta', 'tarifa_aplicada_soles', 'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg', 'energia_suministrada_al_ev_kwh', 
    'energia_suministrada_al_bess_kwh'
]  # 10

# MALL observables: 5 columnas numericas
MALL_OBS_COLS: List[str] = [
    'mall_demand_kwh', 'mall_co2_indirect_kg', 'is_hora_punta',
    'tarifa_soles_kwh', 'mall_cost_soles'
]  # 5

# Total observables: 4 + 156 + 12 + 10 + 5 + 6 (time) + 12 (system) = 205 -> redondeado a 210
# El environment usara OBS_DIM = 210 para incluir todas las features

# ===== COLUMNAS PARA REWARD MULTIOBJETIVO v7.0 =====
# Todas las columnas de CO2 (directo e indirecto) y costos
REWARD_CO2_DIRECT_COLS: List[str] = [
    'co2_reduccion_motos_kg',       # Chargers
    'co2_reduccion_mototaxis_kg',   # Chargers  
    'reduccion_directa_co2_kg',     # Chargers total
]

REWARD_CO2_INDIRECT_COLS: List[str] = [
    'co2_avoided_indirect_kg',      # BESS (evita importar de red)
    'reduccion_indirecta_co2_kg',   # SOLAR (evita importar de red)
    # NOTA: mall_co2_indirect_kg NO va aquí porque el mall GENERA emisiones, no las evita
]

REWARD_COST_COLS: List[str] = [
    'costo_carga_ev_soles',         # Chargers
    'cost_grid_import_soles',       # BESS/Grid
    'mall_cost_soles',              # Mall
    'ahorro_solar_soles',           # Solar (positivo = ahorro)
    'peak_reduction_savings_soles', # BESS (positivo = ahorro)
]

# Total de columnas para reward: 3 + 3 + 5 = 11 columnas

# ===== PESOS RECOMPENSA - ALLINEADOS PPO/SAC/A2C (COMPARACION JUSTA) =====
# SINCRONIZADO con SAC.create_iquitos_reward_weights("co2_focus") para comparacion justa
# Identicos en los 3 agentes: PPO, SAC, A2C (solo algoritmo cambia, no objetivos)
# Esto asegura que diferencias en resultados sean por el algoritmo, no por pesos diferentes
REWARD_WEIGHTS_V6: Dict[str, float] = {
    'co2': 0.35,               # Minimizar emision CO2 (grid termico Iquitos = 0.4521 kg/kWh)
    'cost': 0.10,              # Minimizar costo operativo (tarifa + combustible)
    'solar': 0.20,             # Maximizar uso solar directo (cascada - evita baterias)
    'vehicles_charged': 0.35,  # Satisfaccion EV: carga vehiculos 100% a tiempo [v7.2: was 0.30]
    'grid_stable': 0.15,       # Estabilidad grid: suavizar ramping de potencia [v7.2: was 0.05]
    'ev_utilization': 0.00     # No utilizado en co2_focus (priorizar carga sobre uso)
}

# ===== A2C CONFIG (COMPLETO CON BEST PRACTICES) =====
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para generacion de graficos
import matplotlib.pyplot as plt


@dataclass
class A2CConfig:
    """
    Configuracion A2C COMPLETA - On-policy, updates frecuentes (fortaleza de A2C).
    
    A2C (Advantage Actor-Critic) es mas simple y rapido que PPO pero menos estable.
    Caracteristicas:
    - On-policy: aprende de experiencias recientes
    - Updates sincronos (vs A3C asincrono)
    - Menor sample efficiency pero muy rapido
    - Ideal para tareas con feedback denso
    
    HIPERPARAMETROS PRINCIPALES (Best Practices):
    ================================================================================
    n_steps: 5-20 (clasico), 32-128 para tareas complejas
        - Horizonte por update antes de calcular returns
        - A2C funciona mejor con n_steps pequenos (updates frecuentes)
        
    learning_rate: 7e-4 (clasico RMSProp) o 1e-4 - 3e-4 (Adam)
        - Papers originales usaban RMSProp con 7e-4
        - Con Adam, usar rates mas bajos
        
    gamma: 0.99 tipico (discount factor)
        - Que tan lejos mira el agente en el futuro
        
    gae_lambda: 0.9-0.97 (si implementado)
        - GAE reduce varianza de advantage estimates
        
    ent_coef: 0.0-0.02
        - Fomenta exploracion penalizando policies deterministicas
        - Muy importante para evitar colapso prematuro
        
    vf_coef: 0.25-0.5
        - Peso del value loss en la funcion de perdida total
        - Bajar si value loss domina demasiado
    
    max_grad_norm: 0.5-1.0
        - Gradient clipping para estabilidad
        
    SENALES DE PROBLEMA:
    - Alta varianza entre runs -> subir num_envs, ajustar LR, normalizacion
    - Value loss muy alta persistente -> critico mal (LR/arquitectura/normalizacion)
    - Entropy colapsa a 0 -> exploracion muerta, aumentar ent_coef
    ================================================================================
    """
    
    # ========================================================================
    # LEARNING PARAMETERS - OPTIMOS PARA A2C
    # ========================================================================
    
    # Learning rate
    # - 7e-4: Clasico A2C con RMSProp (papers antiguos)
    # - 1e-4 a 3e-4: Recomendado con Adam
    learning_rate: float = 3e-4  # [OK] Optimo con Adam
    
    # Horizonte por update (n_steps)
    # - 5-20: Clasico A2C (updates muy frecuentes = fortaleza)
    # - 32-128: Para tareas mas complejas/largas
    n_steps: int = 16  # [OK] Balance entre frecuencia y estabilidad
    
    # Discount factor (gamma)
    # - 0.99: Tipico para tareas de largo plazo
    # - 0.95-0.97: Para tareas mas cortas
    gamma: float = 0.99
    
    # GAE lambda (Generalized Advantage Estimation)
    # - 0.9-0.97: Reduce varianza de advantage estimates
    # - 1.0: Sin GAE (solo temporal difference)
    gae_lambda: float = 0.95
    
    # Entropy coefficient
    # - 0.0: Sin bonus de exploracion
    # - 0.01-0.02: Tipico para fomentar exploracion
    # - Muy importante para evitar colapso de policy
    ent_coef: float = 0.01  # [OK] Standard A2C exploration
    
    # Value function coefficient
    # - 0.25-0.5: Balance entre policy y value loss
    # - Bajar si value loss domina demasiado
    vf_coef: float = 0.5
    
    # Max gradient norm (clipping)
    # - 0.5: Conservador, mas estable
    # - 1.0: Menos restrictivo
    max_grad_norm: float = 0.5
    
    # RMSProp epsilon (solo si use_rms_prop=True)
    rms_prop_eps: float = 1e-5
    
    # Usar RMSProp en lugar de Adam
    # - True: Clasico A2C (papers originales)
    # - False: Adam (generalmente mejor en practica moderna)
    use_rms_prop: bool = False  # [OK] Adam es mejor en practica moderna
    
    # Normalizacion de advantages
    normalize_advantage: bool = True  # [OK] Reduce varianza
    
    # ========================================================================
    # NETWORK ARCHITECTURE
    # ========================================================================
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[256, 256], vf=[256, 256])  # [OK] 256x256 adecuado
    })
    
    # ========================================================================
    # MONITORING THRESHOLDS (para alertas)
    # ========================================================================
    
    # Entropy minima antes de warning (exploration collapse)
    min_entropy_warning: float = 0.1
    
    # Value loss maxima persistente (indica problemas)
    max_value_loss_warning: float = 100.0
    
    # Explained variance minima esperada tras convergencia
    min_explained_variance: float = 0.0
    
    # ========================================================================
    # FACTORY METHODS
    # ========================================================================
    
    @classmethod
    def for_gpu(cls) -> 'A2CConfig':
        """
        Configuracion OPTIMA para A2C en GPU.
        
        GPU permite n_steps mas altos y redes mas grandes.
        """
        return cls(
            learning_rate=3e-4,  # [OK] Adam rate optimo
            n_steps=16,  # [OK] Balance updates/estabilidad
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.01,  # [OK] Exploracion estandar
            vf_coef=0.5,
            max_grad_norm=0.5,
            use_rms_prop=False,  # Adam
            normalize_advantage=True,
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], vf=[256, 256]),
            }
        )
    
    @classmethod
    def for_cpu(cls) -> 'A2CConfig':
        """
        Configuracion para CPU (fallback).
        
        Mas conservadora para evitar timeouts.
        """
        return cls(
            learning_rate=1e-4,  # [OK] Mas bajo para estabilidad
            n_steps=8,  # [OK] Updates mas frecuentes
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            use_rms_prop=False,
            normalize_advantage=True,
            policy_kwargs={
                'net_arch': dict(pi=[128, 128], vf=[128, 128]),  # Red mas pequena
            }
        )
    
    @classmethod
    def high_exploration(cls) -> 'A2CConfig':
        """
        Configuracion con alta exploracion.
        
        Util al inicio del entrenamiento o en tareas complejas.
        """
        return cls(
            learning_rate=3e-4,
            n_steps=32,  # Horizonte mas largo
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.02,  # [OK] Alta exploracion
            vf_coef=0.25,  # Menos enfasis en value
            max_grad_norm=0.5,
            use_rms_prop=False,
            normalize_advantage=True,
        )
    
    @classmethod
    def stable_convergence(cls) -> 'A2CConfig':
        """
        Configuracion conservadora para convergencia estable.
        
        Menor learning rate, mas gradient clipping.
        """
        return cls(
            learning_rate=1e-4,  # [OK] Mas bajo
            n_steps=16,
            gamma=0.99,
            gae_lambda=0.97,  # GAE mas alto
            ent_coef=0.005,  # Menos exploracion
            vf_coef=0.5,
            max_grad_norm=0.3,  # [OK] Mas restrictivo
            use_rms_prop=False,
            normalize_advantage=True,
        )


# ===== A2C METRICS CALLBACK - METRICAS ESPECIFICAS A2C =====
class A2CMetricsCallback(BaseCallback):
    """
    Callback para registrar metricas ESPECIFICAS de A2C durante entrenamiento.
    
    METRICAS QUE SE LOGUEAN (Best Practices A2C):
    ================================================================================
    1. Entropy: Mide diversidad de la policy (exploracion)
       - Warning si < 0.1 (exploration collapse)
       
    2. Policy Loss: Perdida del actor
       - Deberia estabilizarse tras convergencia
       
    3. Value Loss: Perdida del critico
       - Warning si muy alta persistente (>100)
       
    4. Explained Variance: Que tan bien predice el critico
       - 0 = aleatorio, 1 = perfecto
       - Deberia aumentar durante entrenamiento
       
    5. Grad Norm: Norma de gradientes
       - Monitoreamos para detectar explosion/desvanecimiento
       
    6. Episode Length: Duracion de episodios
       - Util para detectar terminacion prematura
       
    SENALES DE PROBLEMA (A2C):
    - Alta varianza entre runs -> subir num_envs, ajustar LR
    - Value loss muy alta persistente -> arquitectura/normalizacion
    - Entropy colapsa -> aumentar ent_coef
    ================================================================================
    """
    
    def __init__(
        self, 
        output_dir: Path | None = None, 
        config: A2CConfig | None = None,
        verbose: int = 0
    ):
        super().__init__(verbose)
        self.output_dir = output_dir or Path('outputs/a2c_training')
        self.config = config or A2CConfig()
        
        # ========================================================================
        # HISTORIALES PARA GRAFICOS
        # ========================================================================
        
        # Steps tracking (X-axis para todos los graficos)
        self.steps_history: list[int] = []
        
        # Metricas A2C principales
        self.entropy_history: list[float] = []
        self.policy_loss_history: list[float] = []
        self.value_loss_history: list[float] = []
        self.explained_variance_history: list[float] = []
        self.grad_norm_history: list[float] = []
        
        # Metricas de episodios
        self.episode_lengths: list[int] = []
        self.episode_rewards: list[float] = []
        
        # Learning rate tracking (puede cambiar con schedulers)
        self.lr_history: list[float] = []
        
        # ========================================================================
        # KPIs CityLearn (estandar para evaluacion de control en microgrids)
        # ========================================================================
        
        # Steps para KPIs (puede diferir de steps_history si se loguean diferente)
        self.kpi_steps_history: list[int] = []
        
        # 1. Electricity Consumption (net) - kWh neto consumido del grid
        #    Positivo = importacion, Negativo = exportacion
        self.electricity_consumption_history: list[float] = []
        
        # 2. Electricity Cost - USD (o soles) total
        self.electricity_cost_history: list[float] = []
        
        # 3. Carbon Emissions - kg CO2 total
        self.carbon_emissions_history: list[float] = []
        
        # 4. Ramping - kW diferencia absoluta entre timesteps consecutivos
        #    Mide la variabilidad de carga (menor = mas estable)
        self.ramping_history: list[float] = []
        
        # 5. Average Daily Peak - kW promedio de picos diarios
        self.avg_daily_peak_history: list[float] = []
        
        # 6. (1 - Load Factor) - Medida de eficiencia de uso
        #    Load Factor = Average / Peak; menor (1-LF) = mejor
        self.one_minus_load_factor_history: list[float] = []
        
        # Acumuladores para calcular KPIs por ventana de evaluacion
        self._kpi_window_size = 24  # Calcular KPIs cada 24 horas (1 dia)
        self._kpi_grid_imports: list[float] = []  # Para net consumption
        self._kpi_grid_exports: list[float] = []
        self._kpi_costs: list[float] = []
        self._kpi_emissions: list[float] = []
        self._kpi_loads: list[float] = []  # Para ramping y load factor
        self._prev_load: float = 0.0  # Para calcular ramping
        self._kpi_ramping_sum: float = 0.0
        self._kpi_ramping_count: int = 0
        
        # ========================================================================
        # CONTADORES DE ALERTAS
        # ========================================================================
        self.entropy_collapse_alerts: int = 0
        self.high_value_loss_alerts: int = 0
        self.grad_explosion_alerts: int = 0
        self.low_explained_var_alerts: int = 0
        
        # Umbrales de alerta
        self.min_entropy = self.config.min_entropy_warning  # 0.1
        self.max_value_loss = self.config.max_value_loss_warning  # 100.0
        self.max_grad_norm_alert = 10.0  # Alert si grad_norm > 10
        
        # Logging frecuency
        self.log_freq = 1000  # Log cada 1000 steps
        
    def _on_step(self) -> bool:
        """Registrar metricas en cada step."""
        
        # Solo loguear cada log_freq steps
        if self.num_timesteps % self.log_freq != 0:
            return True
            
        # Obtener logger del modelo
        if self.model is None:
            return True
            
        # ========================================================================
        # EXTRAER METRICAS DEL MODELO A2C
        # ========================================================================
        
        # Extraemos metricas del logger interno de SB3
        # A2C registra: entropy_loss, policy_gradient_loss, value_loss, explained_variance
        
        logger = self.model.logger
        if logger is None:
            return True
        
        # Registrar step
        self.steps_history.append(self.num_timesteps)
        
        # Entropy (de logger.name_to_value o del ultimo rollout)
        entropy = 0.0
        policy_loss = 0.0
        value_loss = 0.0
        explained_var = 0.0
        
        # Intentar obtener de logger.name_to_value (SB3 >= 2.0)
        if hasattr(logger, 'name_to_value'):
            name_to_value = logger.name_to_value
            entropy = name_to_value.get('train/entropy_loss', 0.0)
            policy_loss = name_to_value.get('train/policy_gradient_loss', 0.0)
            value_loss = name_to_value.get('train/value_loss', 0.0)
            explained_var = name_to_value.get('train/explained_variance', 0.0)
        
        # Alternativamente, obtener del locals (ultima iteracion)
        if entropy == 0.0 and 'entropy_losses' in self.locals:
            entropy_losses = self.locals.get('entropy_losses', [])
            if entropy_losses:
                entropy = -float(np.mean(entropy_losses))  # Negativo porque SB3 lo almacena negado
        
        if policy_loss == 0.0 and 'pg_losses' in self.locals:
            pg_losses = self.locals.get('pg_losses', [])
            if pg_losses:
                policy_loss = float(np.mean(pg_losses))
        
        if value_loss == 0.0 and 'value_losses' in self.locals:
            value_losses = self.locals.get('value_losses', [])
            if value_losses:
                value_loss = float(np.mean(value_losses))
        
        # Explained variance del rollout buffer
        try:
            rb = getattr(self.model, 'rollout_buffer', None)
            if rb is not None and hasattr(rb, 'returns') and hasattr(rb, 'values') and rb.returns is not None:
                try:
                    returns = rb.returns.flatten()
                    values = rb.values.flatten()
                    if len(returns) > 0 and len(values) > 0:
                        var_returns = np.var(returns)
                        if var_returns > 0:
                            explained_var = 1 - np.var(returns - values) / var_returns
                except Exception:
                    pass
        except Exception:
            pass
        
        # Guardar en historiales
        self.entropy_history.append(abs(entropy))  # Valor absoluto
        self.policy_loss_history.append(policy_loss)
        self.value_loss_history.append(value_loss)
        self.explained_variance_history.append(explained_var)
        
        # ========================================================================
        # GRAD NORM (calcular si posible)
        # ========================================================================
        grad_norm = 0.0
        try:
            if hasattr(self.model, 'policy') and self.model.policy is not None:
                total_norm = 0.0
                for p in self.model.policy.parameters():
                    if p.grad is not None:
                        param_norm = p.grad.data.norm(2)
                        total_norm += param_norm.item() ** 2
                grad_norm = total_norm ** 0.5
        except Exception:
            pass
        
        self.grad_norm_history.append(grad_norm)
        
        # Learning rate actual
        lr = self.model.learning_rate
        if callable(lr):
            lr = lr(1)  # type: ignore
        self.lr_history.append(float(lr))
        
        # ========================================================================
        # KPIs CityLearn - Recolectar datos para evaluacion
        # ========================================================================
        self._collect_kpi_data()
        
        # ========================================================================
        # VERIFICAR ALERTAS
        # ========================================================================
        self._check_alerts(entropy, value_loss, grad_norm, explained_var)
        
        return True
    
    def _check_alerts(
        self, 
        entropy: float, 
        value_loss: float, 
        grad_norm: float,
        explained_var: float
    ) -> None:
        """Verificar condiciones problematicas y emitir alertas."""
        
        # 1. Entropy collapse (exploracion muerta)
        if abs(entropy) < self.min_entropy and abs(entropy) > 0:
            self.entropy_collapse_alerts += 1
            if self.entropy_collapse_alerts <= 3:  # Solo primeras 3 alertas
                print(f'  [!] A2C ALERT [{self.num_timesteps}]: Entropy muy baja '
                      f'({abs(entropy):.4f} < {self.min_entropy}) - Aumentar ent_coef')
        
        # 2. Value loss muy alta
        if value_loss > self.max_value_loss:
            self.high_value_loss_alerts += 1
            if self.high_value_loss_alerts <= 3:
                print(f'  [!] A2C ALERT [{self.num_timesteps}]: Value loss muy alta '
                      f'({value_loss:.2f} > {self.max_value_loss}) - Revisar arquitectura/LR')
        
        # 3. Gradient explosion
        if grad_norm > self.max_grad_norm_alert:
            self.grad_explosion_alerts += 1
            if self.grad_explosion_alerts <= 3:
                print(f'  [!] A2C ALERT [{self.num_timesteps}]: Grad norm muy alta '
                      f'({grad_norm:.2f} > {self.max_grad_norm_alert}) - Reducir LR o max_grad_norm')
        
        # 4. Explained variance muy baja despues de muchos steps
        if self.num_timesteps > 20000 and explained_var < -0.5:
            self.low_explained_var_alerts += 1
            if self.low_explained_var_alerts <= 3:
                print(f'  [!] A2C ALERT [{self.num_timesteps}]: Explained variance negativa '
                      f'({explained_var:.3f}) - Critico no esta aprendiendo')
    
    def _collect_kpi_data(self) -> None:
        """
        Recolectar datos para KPIs CityLearn de evaluacion.
        
        KPIs estandar CityLearn calculados sobre carga neta agregada:
        1. Electricity consumption (net) - kWh
        2. Electricity cost - USD
        3. Carbon emissions - kg CO2
        4. Ramping - kW (variabilidad de carga)
        5. Average daily peak - kW
        6. (1 - Load Factor) - eficiencia de uso
        """
        # Obtener infos del environment
        infos = self.locals.get('infos', [{}])
        if not infos:
            return
        
        info = infos[0] if isinstance(infos, list) else infos
        
        # Extraer metricas del step actual
        grid_import = info.get('grid_import_kwh', 0.0)
        grid_export = info.get('grid_export_kwh', 0.0)
        cost = info.get('cost_usd', info.get('cost_soles', 0.0) * 0.27)  # Convertir soles a USD aprox
        co2 = info.get('co2_grid_kg', grid_import * 0.4521)  # Factor Iquitos
        
        # Carga neta total (para ramping y load factor)
        mall_demand = info.get('mall_demand_kwh', info.get('mall_demand_kw', 0.0))
        ev_demand = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))
        solar_gen = info.get('solar_generation_kwh', info.get('solar_kw', 0.0))
        net_load = mall_demand + ev_demand - solar_gen + grid_import - grid_export
        
        # Acumular datos
        self._kpi_grid_imports.append(grid_import)
        self._kpi_grid_exports.append(grid_export)
        self._kpi_costs.append(cost)
        self._kpi_emissions.append(co2)
        self._kpi_loads.append(max(0, net_load))  # Solo carga positiva
        
        # Calcular ramping (diferencia con step anterior)
        if self._prev_load > 0:
            ramping = abs(net_load - self._prev_load)
            self._kpi_ramping_sum += ramping
            self._kpi_ramping_count += 1
        self._prev_load = net_load
        
        # Calcular KPIs cada _kpi_window_size steps (24 horas = 1 dia)
        if len(self._kpi_loads) >= self._kpi_window_size:
            self._calculate_and_store_kpis()
    
    def _calculate_and_store_kpis(self) -> None:
        """
        Calcular y almacenar KPIs para la ventana actual.
        
        Formulas estandar CityLearn:
        - Net consumption = sum(imports) - sum(exports)
        - Ramping = mean(|load[t] - load[t-1]|)
        - Load Factor = mean(load) / max(load)
        - (1 - Load Factor) = 1 - (mean/max)
        """
        if len(self._kpi_loads) == 0:
            return
        
        # Guardar step actual
        self.kpi_steps_history.append(self.num_timesteps)
        
        # 1. Net electricity consumption (kWh)
        net_consumption = sum(self._kpi_grid_imports) - sum(self._kpi_grid_exports)
        self.electricity_consumption_history.append(net_consumption)
        
        # 2. Electricity cost (USD)
        total_cost = sum(self._kpi_costs)
        self.electricity_cost_history.append(total_cost)
        
        # 3. Carbon emissions (kg CO2)
        total_co2 = sum(self._kpi_emissions)
        self.carbon_emissions_history.append(total_co2)
        
        # 4. Ramping (kW promedio)
        avg_ramping = self._kpi_ramping_sum / max(1, self._kpi_ramping_count)
        self.ramping_history.append(avg_ramping)
        
        # 5. Average daily peak (kW)
        # Para una ventana de 24h, el peak es simplemente el maximo
        daily_peak = max(self._kpi_loads) if self._kpi_loads else 0.0
        self.avg_daily_peak_history.append(daily_peak)
        
        # 6. (1 - Load Factor)
        # Load Factor = average / peak (0 a 1, donde 1 = carga constante)
        avg_load = np.mean(self._kpi_loads) if self._kpi_loads else 0.0
        peak_load = max(self._kpi_loads) if self._kpi_loads else 1.0
        load_factor = avg_load / max(peak_load, 0.001)  # Evitar division por cero
        one_minus_lf = 1.0 - load_factor
        self.one_minus_load_factor_history.append(one_minus_lf)
        
        # Reset acumuladores para siguiente ventana
        self._kpi_grid_imports.clear()
        self._kpi_grid_exports.clear()
        self._kpi_costs.clear()
        self._kpi_emissions.clear()
        self._kpi_loads.clear()
        self._kpi_ramping_sum = 0.0
        self._kpi_ramping_count = 0
    
    def _on_training_end(self) -> None:
        """Generar graficos al finalizar entrenamiento."""
        print('\n  [GRAPH] Generando graficos A2C...')
        self._generate_a2c_graphs()
        
        # [OK] NUEVO: Generar graficos de KPIs CityLearn
        print('\n  [GRAPH] Generando graficos KPIs CityLearn...')
        self._generate_kpi_graphs()
        
        # Resumen de alertas
        total_alerts = (self.entropy_collapse_alerts + self.high_value_loss_alerts + 
                       self.grad_explosion_alerts + self.low_explained_var_alerts)
        
        if total_alerts > 0:
            print(f'\n  📋 RESUMEN ALERTAS A2C:')
            if self.entropy_collapse_alerts > 0:
                print(f'     - Entropy collapse: {self.entropy_collapse_alerts}')
            if self.high_value_loss_alerts > 0:
                print(f'     - High value loss: {self.high_value_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                print(f'     - Gradient explosion: {self.grad_explosion_alerts}')
            if self.low_explained_var_alerts > 0:
                print(f'     - Low explained variance: {self.low_explained_var_alerts}')
    
    def _generate_kpi_graphs(self) -> None:
        """
        Generar graficos de KPIs CityLearn vs Training Steps.
        
        GRAFICOS GENERADOS:
        1. Electricity Consumption (net) vs Steps
        2. Electricity Cost vs Steps
        3. Carbon Emissions vs Steps
        4. Ramping vs Steps
        5. Average Daily Peak vs Steps
        6. (1 - Load Factor) vs Steps
        7. Dashboard KPIs combinado 2×3
        """
        
        if len(self.kpi_steps_history) < 2:
            print('     [!] Insuficientes datos para graficos KPIs (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Funcion helper para suavizado
        def smooth(data: list[float], window: int = 5) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return np.array(pd.Series(data).rolling(window=window, min_periods=1).mean().to_numpy())
        
        steps = np.array(self.kpi_steps_history)
        
        # ====================================================================
        # GRAFICO 1: ELECTRICITY CONSUMPTION vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
            
            # Linea de tendencia
            if len(steps) > 2:
                z = np.polyfit(steps, consumption, 1)
                p = np.poly1d(z)
                ax.plot(steps, p(steps), 'r--', alpha=0.7, label=f'Trend (slope={z[0]:.4f})')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Net Electricity Consumption (kWh/day)')
            ax.set_title('Electricity Consumption vs Training Steps\n(Lower = better grid independence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Anotar mejora si existe
            if len(consumption) > 1:
                improvement = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_consumption.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_electricity_consumption.png')
        except Exception as e:
            print(f'     [X] Error en consumption graph: {e}')
        
        # ====================================================================
        # GRAFICO 2: ELECTRICITY COST vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, cost, 'g-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Electricity Cost (USD/day)')
            ax.set_title('Electricity Cost vs Training Steps\n(Lower = better cost efficiency)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora
            if len(cost) > 1:
                improvement = (cost[0] - cost[-1]) / max(cost[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_cost.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_electricity_cost.png')
        except Exception as e:
            print(f'     [X] Error en cost graph: {e}')
        
        # ====================================================================
        # GRAFICO 3: CARBON EMISSIONS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, emissions, 'brown', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2, label='Smoothed')
            
            # Baseline sin control (aproximado como primer valor)
            if len(emissions) > 0:
                baseline = emissions[0]
                ax.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label=f'Baseline ({baseline:.1f} kg)')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Carbon Emissions (kg CO₂/day)')
            ax.set_title('Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reduccion CO2
            if len(emissions) > 1:
                reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"v" if reduction > 0 else "^"} {abs(reduction):.1f}% CO₂', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_carbon_emissions.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_carbon_emissions.png')
        except Exception as e:
            print(f'     [X] Error en emissions graph: {e}')
        
        # ====================================================================
        # GRAFICO 4: RAMPING vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ramping = np.array(self.ramping_history)
            ax.plot(steps, ramping, 'purple', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Average Ramping (kW)')
            ax.set_title('Load Ramping vs Training Steps\n(Lower = more stable grid operation)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora en estabilidad
            if len(ramping) > 1:
                improvement = (ramping[0] - ramping[-1]) / max(ramping[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}% ramping', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_ramping.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_ramping.png')
        except Exception as e:
            print(f'     [X] Error en ramping graph: {e}')
        
        # ====================================================================
        # GRAFICO 5: AVERAGE DAILY PEAK vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, peak, 'red', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Daily Peak Demand (kW)')
            ax.set_title('Average Daily Peak vs Training Steps\n(Lower = better peak shaving)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reduccion de pico
            if len(peak) > 1:
                reduction = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"v" if reduction > 0 else "^"} {abs(reduction):.1f}% peak', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_daily_peak.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_daily_peak.png')
        except Exception as e:
            print(f'     [X] Error en peak graph: {e}')
        
        # ====================================================================
        # GRAFICO 6: (1 - LOAD FACTOR) vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, one_minus_lf, 'orange', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2, label='Smoothed')
            
            # Zona ideal (< 0.3 = buen load factor > 0.7)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, label='Target (LF > 0.7)')
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('(1 - Load Factor)')
            ax.set_title('(1 - Load Factor) vs Training Steps\n(Lower = better load distribution, 0 = constant load)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Anotar mejora
            if len(one_minus_lf) > 1:
                improvement = (one_minus_lf[0] - one_minus_lf[-1]) / max(one_minus_lf[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"v" if improvement > 0 else "^"} {abs(improvement):.1f}%', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_load_factor.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_load_factor.png')
        except Exception as e:
            print(f'     [X] Error en load factor graph: {e}')
        
        # ====================================================================
        # GRAFICO 7: DASHBOARD KPIs COMBINADO 2×3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Electricity Consumption (top-left)
            ax = axes[0, 0]
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2)
            ax.set_title('Net Consumption (kWh/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            
            # 2. Electricity Cost (top-center)
            ax = axes[0, 1]
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2)
            ax.set_title('Cost (USD/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 3. Carbon Emissions (top-right)
            ax = axes[0, 2]
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2)
            ax.set_title('CO₂ Emissions (kg/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Ramping (bottom-left)
            ax = axes[1, 0]
            ramping = np.array(self.ramping_history)
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2)
            ax.set_title('Ramping (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 5. Daily Peak (bottom-center)
            ax = axes[1, 1]
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2)
            ax.set_title('Daily Peak (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. (1 - Load Factor) (bottom-right)
            ax = axes[1, 2]
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7)
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            ax.set_title('(1 - Load Factor)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Calcular mejoras para titulo
            improvements = []
            if len(consumption) > 1:
                imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                if imp > 0:
                    improvements.append(f'Cons: {imp:.1f}%v')
            if len(emissions) > 1:
                imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'CO₂: {imp:.1f}%v')
            if len(peak) > 1:
                imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'Peak: {imp:.1f}%v')
            
            title = 'CityLearn KPIs Dashboard - A2C Training'
            if improvements:
                title += f'\n[OK] Improvements: {", ".join(improvements)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
            plt.close(fig)
            print('     [OK] kpi_dashboard.png')
            
        except Exception as e:
            print(f'     [X] Error en KPI dashboard: {e}')
        
        print(f'     📁 Graficos KPIs guardados en: {self.output_dir}')
    
    def _generate_a2c_graphs(self) -> None:
        """
        Generar graficos diagnosticos especificos de A2C.
        
        GRAFICOS GENERADOS:
        1. Entropy vs Steps (con zona de colapso)
        2. Policy Loss vs Steps
        3. Value Loss vs Steps (con threshold warning)
        4. Explained Variance vs Steps (target zone)
        5. Grad Norm vs Steps (con clipping threshold)
        6. Dashboard combinado 2×3
        """
        
        if len(self.steps_history) < 2:
            print('     [!] Insuficientes datos para graficos A2C (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Funcion helper para suavizado
        def smooth(data: list[float], window: int = 10) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return np.array(pd.Series(data).rolling(window=window, min_periods=1).mean().to_numpy())
        
        steps = np.array(self.steps_history)
        
        # ====================================================================
        # GRAFICO 1: ENTROPY vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            entropy = np.array(self.entropy_history)
            ax.plot(steps, entropy, 'b-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(entropy)), 'b-', linewidth=2, label='Smoothed')
            
            # Zona de colapso (< 0.1)
            ax.axhline(y=self.min_entropy, color='r', linestyle='--', 
                      label=f'Collapse zone ({self.min_entropy})')
            ax.fill_between(steps, 0, self.min_entropy, alpha=0.1, color='red')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Entropy')
            ax.set_title('A2C Entropy vs Training Steps\n(Higher = more exploration)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotacion si hay colapso
            if self.entropy_collapse_alerts > 0:
                ax.annotate(f'[!] {self.entropy_collapse_alerts} collapse alerts', 
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='red', verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_entropy.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_entropy.png')
        except Exception as e:
            print(f'     [X] Error en entropy graph: {e}')
        
        # ====================================================================
        # GRAFICO 2: POLICY LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            policy_loss = np.array(self.policy_loss_history)
            ax.plot(steps, policy_loss, 'g-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(policy_loss)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Policy Loss')
            ax.set_title('A2C Policy Loss vs Training Steps')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_policy_loss.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_policy_loss.png')
        except Exception as e:
            print(f'     [X] Error en policy loss graph: {e}')
        
        # ====================================================================
        # GRAFICO 3: VALUE LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            value_loss = np.array(self.value_loss_history)
            ax.plot(steps, value_loss, 'r-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(value_loss)), 'r-', linewidth=2, label='Smoothed')
            
            # Warning threshold
            ax.axhline(y=self.max_value_loss, color='orange', linestyle='--',
                      label=f'Warning threshold ({self.max_value_loss})')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Value Loss')
            ax.set_title('A2C Value Loss vs Training Steps\n(Lower is better after convergence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotacion si hay alertas
            if self.high_value_loss_alerts > 0:
                ax.annotate(f'[!] {self.high_value_loss_alerts} high loss alerts', 
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='orange', verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_value_loss.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_value_loss.png')
        except Exception as e:
            print(f'     [X] Error en value loss graph: {e}')
        
        # ====================================================================
        # GRAFICO 4: EXPLAINED VARIANCE vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            explained_var = np.array(self.explained_variance_history)
            ax.plot(steps, explained_var, 'purple', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(explained_var)), 'purple', linewidth=2, label='Smoothed')
            
            # Target zone (> 0.5 es bueno)
            ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.7, label='Good (>0.5)')
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5, label='Random (0)')
            ax.fill_between(steps, 0.5, 1.0, alpha=0.1, color='green')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Explained Variance')
            ax.set_title('A2C Explained Variance vs Training Steps\n(1.0 = perfect value predictions)')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-1, 1.1)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_explained_variance.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_explained_variance.png')
        except Exception as e:
            print(f'     [X] Error en explained variance graph: {e}')
        
        # ====================================================================
        # GRAFICO 5: GRAD NORM vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, grad_norm, 'orange', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2, label='Smoothed')
            
            # Max grad norm configured
            ax.axhline(y=self.config.max_grad_norm, color='blue', linestyle='--',
                      label=f'Clipping threshold ({self.config.max_grad_norm})')
            
            # Alert threshold
            ax.axhline(y=self.max_grad_norm_alert, color='red', linestyle='--',
                      label=f'Alert threshold ({self.max_grad_norm_alert})')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Gradient Norm')
            ax.set_title('A2C Gradient Norm vs Training Steps\n(Monitoring for explosion/vanishing)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_grad_norm.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_grad_norm.png')
        except Exception as e:
            print(f'     [X] Error en grad norm graph: {e}')
        
        # ====================================================================
        # GRAFICO 6: DASHBOARD COMBINADO 2×3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Entropy (top-left)
            ax = axes[0, 0]
            entropy = np.array(self.entropy_history)
            ax.plot(steps, smooth(list(entropy)), 'b-', linewidth=2)
            ax.axhline(y=self.min_entropy, color='r', linestyle='--', alpha=0.7)
            ax.fill_between(steps, 0, self.min_entropy, alpha=0.1, color='red')
            ax.set_title('Entropy')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 2. Policy Loss (top-center)
            ax = axes[0, 1]
            policy_loss = np.array(self.policy_loss_history)
            ax.plot(steps, smooth(list(policy_loss)), 'g-', linewidth=2)
            ax.set_title('Policy Loss')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            
            # 3. Value Loss (top-right)
            ax = axes[0, 2]
            value_loss = np.array(self.value_loss_history)
            ax.plot(steps, smooth(list(value_loss)), 'r-', linewidth=2)
            ax.axhline(y=self.max_value_loss, color='orange', linestyle='--', alpha=0.7)
            ax.set_title('Value Loss')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Explained Variance (bottom-left)
            ax = axes[1, 0]
            explained_var = np.array(self.explained_variance_history)
            ax.plot(steps, smooth(list(explained_var)), 'purple', linewidth=2)
            ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.7)
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5)
            ax.fill_between(steps, 0.5, 1.0, alpha=0.1, color='green')
            ax.set_title('Explained Variance')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-1, 1.1)
            
            # 5. Grad Norm (bottom-center)
            ax = axes[1, 1]
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2)
            ax.axhline(y=self.config.max_grad_norm, color='blue', linestyle='--', alpha=0.7)
            ax.set_title('Gradient Norm')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. Learning Rate (bottom-right)
            ax = axes[1, 2]
            if self.lr_history:
                lr = np.array(self.lr_history)
                ax.plot(steps[:len(lr)], lr, 'brown', linewidth=2)
            ax.set_title('Learning Rate')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))
            
            # Titulo general con info de alertas
            alert_text = []
            if self.entropy_collapse_alerts > 0:
                alert_text.append(f'Entropy: {self.entropy_collapse_alerts}')
            if self.high_value_loss_alerts > 0:
                alert_text.append(f'VLoss: {self.high_value_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                alert_text.append(f'Grad: {self.grad_explosion_alerts}')
            
            title = 'A2C Training Dashboard'
            if alert_text:
                title += f'\n[!] Alerts: {", ".join(alert_text)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'a2c_dashboard.png', dpi=150)
            plt.close(fig)
            print('     [OK] a2c_dashboard.png')
            
        except Exception as e:
            print(f'     [X] Error en dashboard: {e}')
        
        print(f'     📁 Graficos guardados en: {self.output_dir}')


# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    try:
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
    except (AttributeError, TypeError, RuntimeError):
        pass

warnings.filterwarnings('ignore', category=DeprecationWarning)

def main() -> None:
    """
    Funcion principal para entrenar A2C con datos reales OE2.
    
    FLUJO:
    1. Validacion de sincronizacion con SAC/PPO
    2. Cargar configuracion y contexto multiobjetivo
    3. Cargar dataset CityLearn v2 compilado
    4. Crear environment + agent A2C
    5. Entrenar con callbacks (checkpoint + logging + metricas)
    6. Generar resultados: JSON + CSVs + graficos
    """
    
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
    Load real charger dataset from data/oe2/chargers/chargers_ev_ano_2024_v3.csv (38 sockets, 353 columnas)
    
    CRITICAL: This is the NEW REAL DATASET with:
    - 38 individual socket columns (30 motos + 8 mototaxis) [v5.2]
    - 8,760 hourly timesteps (full year 2024)
    - Individual socket control capability for RL agents
    """
    if not charger_data_path.exists():
        return None
    
    try:
        df = pd.read_csv(charger_data_path, index_col=0, parse_dates=True)
        
        if df.shape[0] != 8760:
            raise ValueError(f"Charger dataset MUST have 8,760 rows (hourly), got {df.shape[0]}")
        
        if df.shape[1] != 38:
            raise ValueError(f"Charger dataset MUST have 38 columns (sockets), got {df.shape[1]}")
        
        if len(df.index) > 1:
            dt = (df.index[1] - df.index[0]).total_seconds() / 3600
            if abs(dt - 1.0) > 0.01:
                raise ValueError(f"Charger dataset MUST be hourly frequency, got {dt:.2f} hours")
        
        min_val = df.min().min()
        max_val = df.max().max()
        print(f"[CHARGERS REAL] [OK] Loaded: {df.shape} (8760 hours × 38 sockets)")
        print(f"[CHARGERS REAL]   Value range: [{min_val:.2f}, {max_val:.2f}] kW")
        print(f"[CHARGERS REAL]   Annual energy: {df.sum().sum():,.0f} kWh")
        
        return df
        
    except Exception as e:
        print(f"[CHARGERS REAL] Error loading: {e}")
        raise


def build_oe2_dataset(interim_oe2_dir: Path) -> dict[str, Any]:
    """
    Build complete OE2 dataset using CENTRALIZED data_loader v7.2
    
    Uses rebuild_oe2_datasets_complete() for unified schema and validation.
    CARGA COMPLETA DE DATASETS OE2 - DESDE DATA_LOADER CENTRALIZADO
    ================================================================================
    
    Returns: dict con DataFrames COMPLETOS + arrays numpy para environment (compatible con SAC/PPO)
    """
    print("\n" + "="*80)
    print("[DATASET BUILD v7.2] Cargando desde data_loader CENTRALIZADO (igual SAC/PPO)")
    print("="*80)
    
    # Cargar datos desde data_loader centralizado
    oe2_datasets = rebuild_oe2_datasets_complete()
    
    result: dict[str, Any] = {}
    
    # ===== 1. CHARGERS - desde ChargerData =====
    chargers_obj = oe2_datasets['chargers']
    chargers_df = chargers_obj.df.copy()
    
    if len(chargers_df) != 8760:
        raise ValueError(f"[X] Chargers debe tener 8760 filas, tiene {len(chargers_df)}")
    
    result['chargers_df'] = chargers_df
    
    # Columnas globales
    if 'co2_reduccion_motos_kg' in chargers_df.columns:
        result['chargers_co2_motos_kg'] = chargers_df['co2_reduccion_motos_kg'].values.astype(np.float32)
    if 'co2_reduccion_mototaxis_kg' in chargers_df.columns:
        result['chargers_co2_mototaxis_kg'] = chargers_df['co2_reduccion_mototaxis_kg'].values.astype(np.float32)
    if 'reduccion_directa_co2_kg' in chargers_df.columns:
        result['chargers_co2_total_kg'] = chargers_df['reduccion_directa_co2_kg'].values.astype(np.float32)
    if 'costo_carga_ev_soles' in chargers_df.columns:
        result['chargers_cost_soles'] = chargers_df['costo_carga_ev_soles'].values.astype(np.float32)
    
    # Socket power columns (38 total)
    socket_power_cols = [c for c in chargers_df.columns if c.endswith('_charging_power_kw')]
    socket_power_cols.sort(key=lambda x: int(x.split('_')[1]))
    chargers_hourly = chargers_df[socket_power_cols[:38]].values.astype(np.float32)
    result['chargers'] = chargers_hourly
    
    # Socket SOC
    socket_soc_cols = [c for c in chargers_df.columns if c.endswith('_soc_current')]
    if socket_soc_cols:
        result['chargers_soc'] = chargers_df[socket_soc_cols[:38]].values.astype(np.float32)
    
    # Socket active
    socket_active_cols = [c for c in chargers_df.columns if c.endswith('_active')]
    if socket_active_cols:
        result['chargers_active'] = chargers_df[socket_active_cols[:38]].values.astype(np.float32)
    
    # Socket vehicle count
    socket_count_cols = [c for c in chargers_df.columns if c.endswith('_vehicle_count')]
    if socket_count_cols:
        result['chargers_vehicle_count'] = chargers_df[socket_count_cols[:38]].values.astype(np.float32)
    
    print(f"[CHARGERS] [OK] {len(chargers_df)} horas × {len(chargers_df.columns)} columnas (from data_loader)")
    
    # ===== 2. BESS - desde BESSData =====
    bess_obj = oe2_datasets['bess']
    bess_df = bess_obj.df.copy()
    
    if len(bess_df) != 8760:
        raise ValueError(f"[X] BESS debe tener 8760 filas, tiene {len(bess_df)}")
    
    result['bess_df'] = bess_df
    
    # SOC
    soc_col = [c for c in bess_df.columns if 'soc' in c.lower()][0] if any('soc' in c.lower() for c in bess_df.columns) else None
    if soc_col:
        result['bess_soc_percent'] = bess_df[soc_col].values.astype(np.float32)
    
    # Energy flows
    for col in ['bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
                'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
                'grid_to_ev_kwh', 'grid_to_mall_kwh', 'grid_to_bess_kwh', 'grid_import_total_kwh']:
        if col in bess_df.columns:
            result[f'bess_{col}'] = bess_df[col].values.astype(np.float32)
    
    # CO2 and costs
    if 'co2_avoided_indirect_kg' in bess_df.columns:
        result['bess_co2_avoided_kg'] = bess_df['co2_avoided_indirect_kg'].values.astype(np.float32)
    if 'cost_grid_import_soles' in bess_df.columns:
        result['bess_cost_soles'] = bess_df['cost_grid_import_soles'].values.astype(np.float32)
    if 'tariff_osinergmin_soles_kwh' in bess_df.columns:
        result['bess_tariff'] = bess_df['tariff_osinergmin_soles_kwh'].values.astype(np.float32)
    if 'peak_reduction_savings_soles' in bess_df.columns:
        result['bess_peak_savings'] = bess_df['peak_reduction_savings_soles'].values.astype(np.float32)
    
    result['bess'] = result.get('bess_soc_percent', np.full(8760, 50.0, dtype=np.float32)) / 100.0
    
    print(f"[BESS] [OK] {len(bess_df)} horas × {len(bess_df.columns)} columnas (from data_loader)")
    
    # ===== 3. SOLAR - desde SolarData =====
    solar_obj = oe2_datasets['solar']
    solar_df = solar_obj.df.copy()
    
    if len(solar_df) != 8760:
        raise ValueError(f"[X] Solar debe tener 8760 filas, tiene {len(solar_df)}")
    
    result['solar_df'] = solar_df
    
    # Main power column
    energy_col = 'potencia_kw' if 'potencia_kw' in solar_df.columns else 'energia_kwh' if 'energia_kwh' in solar_df.columns else solar_df.columns[1]
    result['solar'] = solar_df[energy_col].values.astype(np.float32)
    
    # CO2 avoided
    if 'reduccion_indirecta_co2_kg' in solar_df.columns:
        result['solar_co2_avoided_kg'] = solar_df['reduccion_indirecta_co2_kg'].values.astype(np.float32)
    else:
        result['solar_co2_avoided_kg'] = result['solar'] * CO2_FACTOR_IQUITOS
    
    # Additional columns
    for col in ['ahorro_solar_soles', 'irradiancia_ghi', 'temperatura_c',
                'energia_suministrada_al_ev_kwh', 'energia_suministrada_al_bess_kwh',
                'energia_suministrada_al_mall_kwh']:
        if col in solar_df.columns:
            result[f'solar_{col.replace("energia_suministrada_al_", "")}'] = solar_df[col].values.astype(np.float32)
    
    print(f"[SOLAR] [OK] {len(solar_df)} horas × {len(solar_df.columns)} columnas (from data_loader)")
    
    # ===== 4. MALL - desde DemandData =====
    demand_obj = oe2_datasets['demand']
    mall_df = demand_obj.df.copy()
    
    if len(mall_df) != 8760:
        raise ValueError(f"[X] Mall debe tener 8760 filas, tiene {len(mall_df)}")
    
    result['mall_df'] = mall_df
    
    # Main demand column
    demand_col = 'mall_demand_kwh' if 'mall_demand_kwh' in mall_df.columns else 'demand_kwh' if 'demand_kwh' in mall_df.columns else mall_df.columns[1]
    result['mall'] = mall_df[demand_col].values.astype(np.float32)
    
    # CO2 indirect
    if 'mall_co2_indirect_kg' in mall_df.columns:
        result['mall_co2_indirect_kg'] = mall_df['mall_co2_indirect_kg'].values.astype(np.float32)
    else:
        result['mall_co2_indirect_kg'] = result['mall'] * CO2_FACTOR_IQUITOS
    
    # Cost and tariff
    if 'mall_cost_soles' in mall_df.columns:
        result['mall_cost_soles'] = mall_df['mall_cost_soles'].values.astype(np.float32)
    if 'tarifa_soles_kwh' in mall_df.columns:
        result['mall_tariff'] = mall_df['tarifa_soles_kwh'].values.astype(np.float32)
    
    print(f"[MALL] [OK] {len(mall_df)} horas × {len(mall_df.columns)} columnas (from data_loader)")
    
    # ===== 5. CONTEXT (Iquitos parameters) =====
    context = IquitosContext()
    result['context'] = context
    
    # ===== RESUMEN FINAL =====
    print("\n" + "="*80)
    print("[DATASET BUILD v7.2] RESUMEN - DATOS DESDE DATA_LOADER CENTRALIZADO:")
    print("="*80)
    print(f"  CHARGERS: {len(chargers_df.columns)} columnas (38 sockets + CO2 directo)")
    print(f"  BESS:     {len(bess_df.columns)} columnas (flujos + CO2 indirecto)")
    print(f"  SOLAR:    {len(solar_df.columns)} columnas (generacion + CO2)")
    print(f"  MALL:     {len(mall_df.columns)} columnas (demanda + CO2)")
    print(f"  TOTAL:    {len(chargers_df.columns) + len(bess_df.columns) + len(solar_df.columns) + len(mall_df.columns)} columnas")
    print("="*80)
    
    return result


# ===== DETAILED LOGGING CALLBACK (IGUAL QUE PPO) =====
class DetailedLoggingCallback(BaseCallback):
    """Callback para registrar metricas detalladas en cada step - misma estructura que PPO."""

    def __init__(self, env_ref: Any = None, output_dir: Path | None = None, verbose: int = 0, total_timesteps: int = 87600):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.total_timesteps = total_timesteps
        self.start_time = time.time()
        self.last_log_time = time.time()
        self.log_interval = 5000  # Log cada 5000 steps
        
        # ===== CARGAR DATASET REAL DE BESS (bess_ano_2024.csv) =====
        bess_real_path = Path('data/oe2/bess/bess_ano_2024.csv')
        if bess_real_path.exists():
            self.bess_real_df = pd.read_csv(bess_real_path)
            print(f'  [BESS REAL] Cargado: {len(self.bess_real_df)} horas')
        else:
            self.bess_real_df = None
            print(f'  [BESS REAL] No encontrado: {bess_real_path}')
        
        # Trace y timeseries records
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        
        # Episode tracking (IGUAL QUE PPO)
        self.episode_count = 0
        self.step_in_episode = 0
        self.current_episode_reward = 0.0
        
        # Metricas por episodio (IGUAL QUE PPO + NUEVAS METRICAS)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        
        # [OK] NUEVAS: Estabilidad, Costos, Motos/Mototaxis
        self.episode_grid_stability: list[float] = []  # Promedio estabilidad por episodio
        self.episode_cost_usd: list[float] = []        # Costo total por episodio
        self.episode_motos_charged: list[int] = []     # Motos cargadas (>50% setpoint)
        self.episode_mototaxis_charged: list[int] = [] # Mototaxis cargadas (>50% setpoint)
        self.episode_bess_discharge_kwh: list[float] = []  # Descarga BESS por episodio
        self.episode_bess_charge_kwh: list[float] = []     # Carga BESS por episodio
        
        # [OK] NUEVAS: Progreso de control por socket y BESS
        self.episode_avg_socket_setpoint: list[float] = []  # Setpoint promedio 38 sockets
        self.episode_socket_utilization: list[float] = []   # % sockets activos (>0.1)
        self.episode_bess_action_avg: list[float] = []      # Accion BESS promedio [0-1]
        
        # [OK] NUEVAS: Reward components por episodio
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
        
        # [OK] NUEVOS acumuladores
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
        
        # [OK] NUEVOS acumuladores reward components
        self._current_r_solar_sum = 0.0
        self._current_r_cost_sum = 0.0
        self._current_r_ev_sum = 0.0
        self._current_r_grid_sum = 0.0
        self._current_r_co2_sum = 0.0
        
        # [OK] TRACKING DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
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
            # [OK] CORREGIDO: Mostrar R_avg desde episodio 1 (antes requeria 5+)
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
            
            # Acumular metricas del step
            self._current_co2_grid += info.get('co2_grid_kg', 0.0)
            self._current_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0.0)
            self._current_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0.0)
            self._current_solar_kwh += info.get('solar_generation_kwh', 0.0)
            self._current_ev_charging += info.get('ev_charging_kwh', 0.0)
            self._current_grid_import += info.get('grid_import_kwh', 0.0)
            
            # [OK] NUEVAS metricas: Estabilidad, Costos, Motos/Mototaxis, BESS
            # Estabilidad: calcular ratio de variacion de grid import
            grid_import = info.get('grid_import_kwh', 0.0)
            grid_export = info.get('grid_export_kwh', 0.0)
            peak_demand_limit = 450.0  # kW limite tipico
            stability = 1.0 - min(1.0, abs(grid_import - grid_export) / peak_demand_limit)
            self._current_stability_sum += stability
            self._current_stability_count += 1
            
            # Costo: tarifa × (import - export)
            tariff_usd = 0.15  # USD/kWh tarifa Iquitos
            cost_step = (grid_import - grid_export * 0.5) * tariff_usd
            self._current_cost_usd += max(0.0, cost_step)
            
            # Motos y mototaxis (maximo por episodio)
            motos = info.get('motos_charging', 0)
            mototaxis = info.get('mototaxis_charging', 0)
            self._current_motos_charged_max = max(self._current_motos_charged_max, motos)
            self._current_mototaxis_charged_max = max(self._current_mototaxis_charged_max, mototaxis)
            
            # BESS (descarga/carga) - DATOS REALES del dataset OE2
            # Usa flujos reales de bess_ano_2024.csv en lugar de calcular
            hour_of_year = info.get('hour_of_year', self.step_in_episode % 8760)
            
            if self.bess_real_df is not None and hour_of_year < len(self.bess_real_df):
                # USAR DATOS REALES DEL DATASET
                bess_row = self.bess_real_df.iloc[hour_of_year]
                bess_charge_real = float(bess_row.get('bess_charge_kwh', 0.0))
                bess_discharge_real = float(bess_row.get('bess_discharge_kwh', 0.0))
                self._current_bess_charge += bess_charge_real
                self._current_bess_discharge += bess_discharge_real
                # Tambien trackear destino de descarga
                self._current_bess_to_mall = getattr(self, '_current_bess_to_mall', 0.0) + float(bess_row.get('bess_to_mall_kwh', 0.0))
                self._current_bess_to_ev = getattr(self, '_current_bess_to_ev', 0.0) + float(bess_row.get('bess_to_ev_kwh', 0.0))
            else:
                # FALLBACK: usar info del environment si no hay dataset
                bess_power = info.get('bess_power_kw', 0.0)
                if bess_power > 0:
                    self._current_bess_discharge += bess_power
                else:
                    self._current_bess_charge += abs(bess_power)
            
            # Progreso de control de sockets (desde acciones)
            actions = self.locals.get('actions', None)
            if actions is not None and len(actions) > 0:
                action = actions[0] if len(actions[0].shape) > 0 else actions
                if len(action) >= 39:  # v5.2: 1 BESS + 38 sockets
                    bess_action = float(action[0])
                    socket_setpoints = action[1:39]  # v5.2: 38 sockets
                    self._current_bess_action_sum += bess_action
                    self._current_socket_setpoint_sum += float(np.mean(socket_setpoints))
                    self._current_socket_active_count += int(np.sum(socket_setpoints > 0.1))
            
            # [OK] NUEVAS: Acumular reward components desde info
            self._current_r_solar_sum += info.get('r_solar', 0.0)
            self._current_r_cost_sum += info.get('r_cost', 0.0)
            self._current_r_ev_sum += info.get('r_ev', 0.0)
            self._current_r_grid_sum += info.get('r_grid', 0.0)
            self._current_r_co2_sum += info.get('r_co2', 0.0)
            
            # [OK] ACTUALIZAR MAXIMOS DE VEHICULOS POR SOC (desde environment)
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

            # Registrar trace (cada step) - SINCRONIZADO CON PPO
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'hour': info.get('hour', self.step_in_episode % 8760),
                'reward': reward,
                # CO2 metrics
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                # Energy
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                # Vehicle metrics (CRITICO - faltaba)
                'motos_power_kw': info.get('ev_charging_kwh', 0.0) * 0.79,
                'mototaxis_power_kw': info.get('ev_charging_kwh', 0.0) * 0.21,
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
                # Training metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': info.get('approx_kl', 0.0),
                'clip_fraction': 0.0,  # A2C no usa clipping
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': info.get('explained_variance', 0.0),
                # For backward compatibility
                'cumulative_reward': self.current_episode_reward,
                'ev_soc_avg': info.get('ev_soc_avg', 0.0),
            }
            self.trace_records.append(trace_record)

            # Registrar timeseries (cada hora simulada) - SINCRONIZADO CON PPO (33 COLUMNAS)
            timeseries_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'hour': info.get('hour', self.step_in_episode % 8760),
                # Energy metrics
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'bess_soc': info.get('bess_soc', 0.0),
                'mall_demand_kw': info.get('mall_demand_kw', 0.0),
                # CO2 metrics (TODAS COLUMNAS)
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                'co2_avoided_total_kg': info.get('co2_avoided_indirect_kg', 0.0) + info.get('co2_avoided_direct_kg', 0.0),
                # Vehicle metrics
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
                # Reward components
                'reward': info.get('reward', 0.0),
                'r_co2': info.get('r_co2', 0.0),
                'r_solar': info.get('r_solar', 0.0),
                'r_vehicles': info.get('r_vehicles', info.get('ev_satisfaction', 0.0)),
                'r_grid_stable': info.get('r_grid_stable', 0.0),
                'r_bess': info.get('r_bess', 0.0),
                'r_priority': info.get('r_priority', 0.0),
                # Economics (CRITICO - faltaba)
                'ahorro_solar_soles': info.get('solar_generation_kwh', 0.0) * 0.3,
                'ahorro_bess_soles': max(0, info.get('bess_power_kw', 0.0)) * 0.1,
                'costo_grid_soles': info.get('grid_import_kwh', 0.0) * 0.4,
                'ahorro_combustible_usd': info.get('ev_charging_kwh', 0.0) * 0.12,
                'ahorro_total_usd': info.get('ev_charging_kwh', 0.0) * 0.15,
                # A2C-specific metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': info.get('approx_kl', 0.0),
                'clip_fraction': 0.0,  # A2C no usa clipping
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': info.get('explained_variance', 0.0),
            }
            self.timeseries_records.append(timeseries_record)

            if done:
                # Guardar metricas del episodio (IGUAL QUE PPO)
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_co2_avoided_indirect.append(self._current_co2_avoided_indirect)
                self.episode_co2_avoided_direct.append(self._current_co2_avoided_direct)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                
                # [OK] NUEVAS metricas por episodio
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
                self.episode_socket_utilization.append(self._current_socket_active_count / (38.0 * steps_in_ep))
                self.episode_bess_action_avg.append(self._current_bess_action_sum / steps_in_ep)
                
                # [OK] NUEVAS: Promedios de reward components por episodio
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
                
                # [OK] Reset nuevos acumuladores
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
                
                # [OK] Reset acumuladores reward components
                self._current_r_solar_sum = 0.0
                self._current_r_cost_sum = 0.0
                self._current_r_ev_sum = 0.0
                self._current_r_grid_sum = 0.0
                self._current_r_co2_sum = 0.0
                
                # [OK] RESET TRACKING DE VEHICULOS POR SOC
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


def validate_a2c_sync() -> bool:
    """Validacion de sincronizacion A2C v7.0 - todas las columnas OE2."""
    print('\n' + '='*80)
    print('[VALIDACION] Sincronizacion A2C v7.0 - Datasets OE2 Completos')
    print('='*80)
    
    checks = {
        '1. BESS Capacity (1700 kWh)': BESS_CAPACITY_KWH == 1700.0,
        '2. BESS Max normalizacion (1700 kWh)': BESS_MAX_KWH_CONST == 1700.0,
        '3. Solar Max (2887 kW)': SOLAR_MAX_KW == 2887.0,
        '4. Mall Max (3000 kW)': MALL_MAX_KW == 3000.0,
        '5. Chargers CO2 cols (4)': len(CHARGERS_AGGREGATE_COLS) == 4,
        '6. BESS cols (25)': len(BESS_REAL_COLS) == 25,
        '7. Solar cols (16)': len(SOLAR_REAL_COLS) == 16,
        '8. Mall cols (6)': len(MALL_REAL_COLS) == 6,
        '9. BESS obs cols (12)': len(BESS_OBS_COLS) == 12,
        '10. Solar obs cols (10)': len(SOLAR_OBS_COLS) == 10,
    }
    
    all_ok = True
    for check_name, result in checks.items():
        status = '[OK]' if result else '[X]'
        print(f'  {status} {check_name}')
        if not result:
            all_ok = False
    print()
    return all_ok
try:
        print('[0] VALIDACION DE SINCRONIZACION A2C')
        print('-' * 80)
        if not validate_a2c_sync():
            print('[ERROR] A2C no sincronizado. Revisar constantes vs SAC/PPO')
            sys.exit(1)
        print('[OK] A2C sincronizado.\\n')
    
        # PRE-VALIDACION CENTRALIZADA: Garantizar entrenamiento COMPLETO y ROBUSTO
        print('[0.5] VALIDACION CENTRALIZADA - ENTRENAMIENTO COMPLETO')
        print('-' * 80)
        if not validate_agent_config(
            agent_name='A2C',
            num_episodes=10,
            total_timesteps=87_600,
            obs_dim=156,
            action_dim=39
        ):
            print('[FATAL] Agente A2C no cumple especificacion de entrenamiento completo.')
            print('        Revisar datos, constantes, y configuracion.')
            sys.exit(1)
        print('[OK] Entrenamiento COMPLETO garantizado: 10 episodios × 87,600 steps × 27 observables × multiobjetivo.')
        print()
    
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
        print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 ano)'.format(HOURS_PER_YEAR))
        print('-' * 80)

        # ====================================================================
        # SOLAR - RUTA REAL OE2 v5.5
        # ====================================================================
        solar_path: Path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
        if not solar_path.exists():
            raise FileNotFoundError(f"OBLIGATORIO: Solar CSV REAL no encontrado: {solar_path}")
    
        df_solar = pd.read_csv(solar_path)
        # Prioridad: pv_generation_kwh (energia horaria) > ac_power_kw (potencia)
        if 'pv_generation_kwh' in df_solar.columns:
            col = 'pv_generation_kwh'
        elif 'ac_power_kw' in df_solar.columns:
            col = 'ac_power_kw'
        else:
            raise KeyError(f"Solar CSV debe tener 'pv_generation_kwh' o 'ac_power_kw'. Columnas: {list(df_solar.columns)}")
    
        solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
        if len(solar_hourly) != HOURS_PER_YEAR:
            raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
        print('  [SOLAR] REAL (CityLearn v2): columna=%s | %.0f kWh/ano (8760h)' % (col, float(np.sum(solar_hourly))))

        # ===== v7.1: EXTRAER CO2 INDIRECTO DE SOLAR =====
        # CO2 indirecto: evita importar energía de la red térmica
        solar_co2_data: dict[str, np.ndarray] = {}
        if 'reduccion_indirecta_co2_kg' in df_solar.columns:
            solar_co2_data['co2_avoided_kg'] = df_solar['reduccion_indirecta_co2_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         CO2 indirecto solar: {sum(solar_co2_data['co2_avoided_kg']):,.0f} kg/año")
        else:
            # Calcular CO2 indirecto: kWh solar × factor Iquitos (0.4521 kg/kWh)
            solar_co2_data['co2_avoided_kg'] = solar_hourly * 0.4521
            print(f"         CO2 indirecto solar (calculado): {sum(solar_co2_data['co2_avoided_kg']):,.0f} kg/año")
        
        if 'ahorro_solar_soles' in df_solar.columns:
            solar_co2_data['savings_soles'] = df_solar['ahorro_solar_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         Ahorro solar: S/. {sum(solar_co2_data['savings_soles']):,.0f}/año")

        # ====================================================================
        # CHARGERS (38 sockets) - ESPECIFICACION OE2 v5.2
        # ====================================================================
        # [OK] OBLIGATORIO: chargers_ev_ano_2024_v3.csv con demanda REAL
        # Contiene 38 columnas de demanda horaria real (19 chargers × 2 sockets)
        charger_real_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    
        if not charger_real_path.exists():
            raise FileNotFoundError(
                f"OBLIGATORIO: chargers_ev_ano_2024_v3.csv NO ENCONTRADO\n"
                f"  Ruta esperada: {charger_real_path}\n"
                f"  ERROR: No hay datos REALES de chargers. Especificacion OE2 v5.2 requiere 38 sockets."
            )
    
        print(f'  [CHARGERS] [OK] Cargando datos REALES desde: {charger_real_path.name} (353 columnas)')
        df_chargers = pd.read_csv(charger_real_path)
    
        # ===== v7.0: EXTRAER CO2 Y COSTO DE CHARGERS =====
        # Columnas de CO2 directo (reduccion por EV electricos vs combustibles fosiles)
        chargers_co2_data: dict[str, np.ndarray] = {}
        if 'co2_reduccion_motos_kg' in df_chargers.columns:
            chargers_co2_data['co2_motos_kg'] = df_chargers['co2_reduccion_motos_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         CO2 directo motos: {sum(chargers_co2_data['co2_motos_kg']):,.0f} kg/año")
        if 'co2_reduccion_mototaxis_kg' in df_chargers.columns:
            chargers_co2_data['co2_mototaxis_kg'] = df_chargers['co2_reduccion_mototaxis_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         CO2 directo mototaxis: {sum(chargers_co2_data['co2_mototaxis_kg']):,.0f} kg/año")
        if 'reduccion_directa_co2_kg' in df_chargers.columns:
            chargers_co2_data['co2_total_kg'] = df_chargers['reduccion_directa_co2_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         CO2 directo TOTAL: {sum(chargers_co2_data['co2_total_kg']):,.0f} kg/año")
        if 'costo_carga_ev_soles' in df_chargers.columns:
            chargers_co2_data['cost_soles'] = df_chargers['costo_carga_ev_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"         Costo EV: S/. {sum(chargers_co2_data['cost_soles']):,.0f}/año")
        
        # Excluir columna timestamp y columnas no numericas (vehicle_type), tomar solo columnas de potencia (charger_power_kw)
        # Las columnas validas son: socket_XXX_charger_power_kw (38 columnas para 38 sockets)
        data_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
    
        if not data_cols:
            # Fallback: intentar con cualquier columna que no sea datetime o vehicle_type
            data_cols = [c for c in df_chargers.columns if all(x not in c.lower() for x in ['timestamp', 'time', 'vehicle_type', 'datetime'])]
    
        chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
        n_sockets = chargers_hourly.shape[1]
        total_demand = float(np.sum(chargers_hourly))
    
        # Validar que tenemos 38 sockets (v5.2): 19 cargadores × 2 = 38 sockets
        # Si hay mas columnas, tomar solo las primeras 38 (compatible con v5.2)
        if n_sockets > 38:
            print(f"  [!] AJUSTE v5.2: Reduciendo {n_sockets} -> 38 sockets (19 chargers × 2)")
            chargers_hourly = chargers_hourly[:, :38]
            n_sockets = 38
            total_demand = float(np.sum(chargers_hourly))
        elif n_sockets != 38:
            print(f"  [!] ADVERTENCIA: Se encontraron {n_sockets} sockets en lugar de 38 (v5.2)")
    
        if len(chargers_hourly) != HOURS_PER_YEAR:
            raise ValueError(f"Chargers: {len(chargers_hourly)} horas != {HOURS_PER_YEAR}")
    
        print("  [CHARGERS] DATASET REAL: %d sockets | Demanda: %.0f kWh/ano | Promedio: %.2f kW/socket" % 
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
        print("  [MALL] DATASET: %.0f kWh/ano (promedio %.1f kW/h)" % (float(np.sum(mall_hourly)), float(np.mean(mall_hourly))))

        # ====================================================================
        # BESS SIMULATION COMPLETO - DATOS REALES CON CO2, COSTOS, TARIFAS
        # ====================================================================
        # Prioridad 1: bess_ano_2024.csv (COMPLETO con metricas)
        bess_sim_path = Path('data/oe2/bess/bess_ano_2024.csv')
        bess_dataset_path = dataset_dir / 'electrical_storage_simulation.csv'
        bess_interim_paths = [
            dataset_dir / 'bess' / 'bess_hourly_dataset_2024.csv',
            Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
        ]
    
        # Inicializar arrays de BESS con metricas completas
        bess_data: dict[str, np.ndarray] = {}
    
        if bess_sim_path.exists():
            print(f"  [BESS] Cargando DATOS REALES COMPLETOS desde: {bess_sim_path.name}")
            df_bess = pd.read_csv(bess_sim_path, encoding='utf-8')
        
            # Cargar TODAS las metricas disponibles
            bess_cols = {
                'bess_soc_percent': 'soc',           # SOC %
                'bess_charge_kwh': 'charge',         # Carga kWh
                'bess_discharge_kwh': 'discharge',   # Descarga kWh
                'bess_to_ev_kwh': 'to_ev',           # BESS -> EV
                'bess_to_mall_kwh': 'to_mall',       # BESS -> Mall
                'pv_to_bess_kwh': 'pv_charge',       # PV -> BESS
                'grid_to_bess_kwh': 'grid_charge',   # Grid -> BESS
                'co2_avoided_indirect_kg': 'co2_avoided',  # CO2 evitado
                'cost_grid_import_soles': 'cost',    # Costo grid S/.
                'tariff_osinergmin_soles_kwh': 'tariff',  # Tarifa S/./kWh
                'peak_reduction_savings_soles': 'peak_savings',  # Ahorro punta
                'grid_import_total_kwh': 'grid_import',  # Import grid total
                'pv_to_ev_kwh': 'pv_to_ev',          # PV -> EV directo
                'pv_to_mall_kwh': 'pv_to_mall',      # PV -> Mall
                'pv_curtailed_kwh': 'pv_curtailed',  # PV descartado
            }
        
            for col_name, key in bess_cols.items():
                if col_name in df_bess.columns:
                    bess_data[key] = np.asarray(df_bess[col_name].values[:HOURS_PER_YEAR], dtype=np.float32)
        
            # SOC normalizado [0,1]
            if 'soc' in bess_data:
                bess_soc = bess_data['soc'] / 100.0
            else:
                bess_soc = np.full(HOURS_PER_YEAR, 0.5, dtype=np.float32)
        
            print(f"  [BESS] METRICAS CARGADAS: {len(bess_data)} columnas")
            print(f"         SOC: {float(np.mean(bess_soc))*100:.1f}% promedio")
            if 'co2_avoided' in bess_data:
                print(f"         CO2 evitado: {float(np.sum(bess_data['co2_avoided'])):,.0f} kg/ano")
            if 'cost' in bess_data:
                print(f"         Costo grid: S/. {float(np.sum(bess_data['cost'])):,.0f}/ano")
            if 'charge' in bess_data and 'discharge' in bess_data:
                print(f"         Carga: {float(np.sum(bess_data['charge'])):,.0f} kWh | Descarga: {float(np.sum(bess_data['discharge'])):,.0f} kWh")
        else:
            # Fallback a archivos anteriores
            bess_path: Path | None = None
            if bess_dataset_path.exists():
                bess_path = bess_dataset_path
            else:
                for p in bess_interim_paths:
                    if p.exists():
                        bess_path = p
                        break
        
            if bess_path is None:
                raise FileNotFoundError("OBLIGATORIO: BESS data no encontrado")
        
            df_bess = pd.read_csv(str(bess_path), encoding='utf-8')
            if 'soc_stored_kwh' in df_bess.columns:
                bess_soc_kwh = np.asarray(df_bess['soc_stored_kwh'].values[:HOURS_PER_YEAR], dtype=np.float32)
                bess_soc = bess_soc_kwh / BESS_CAPACITY_KWH
            else:
                soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
                if not soc_cols:
                    raise KeyError(f"BESS CSV debe tener columna 'soc'. Columnas: {list(df_bess.columns)}")
                bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
                bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
            print(f"  [BESS] FALLBACK: SOC media {float(np.mean(bess_soc))*100:.1f}%")
    
        # ====================================================================
        # EV CHARGERS COMPLETO - DATOS REALES CON SOC, TIPO VEHICULO, ESTADO
        # v7.2: INCLUDE INDIVIDUAL SOCKET SOC DATA FOR IMPROVED VEHICLE COUNTING
        # ====================================================================
        ev_chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
        ev_data: dict[str, np.ndarray] = {}
        chargers_soc_hourly: np.ndarray | None = None  # v7.2: SOC por socket [8760, 38]
    
        if ev_chargers_path.exists():
            print(f"  [EV] Cargando DATOS REALES COMPLETOS desde: {ev_chargers_path.name}")
            df_ev = pd.read_csv(ev_chargers_path, encoding='utf-8')
        
            # Cargar metricas por socket (primeros 38 sockets para v5.2)
            n_sockets_ev = min(38, len([c for c in df_ev.columns if 'socket_' in c and '_soc_current' in c]))
        
            # v7.2: ARRAY PARA SOC INDIVIDUAL POR SOCKET [8760 horas, 38 sockets]
            chargers_soc_hourly = np.zeros((HOURS_PER_YEAR, 38), dtype=np.float32)
        
            # Arrays agregados por hora
            ev_soc_current = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
            ev_soc_target = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
            ev_active_count = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
            ev_charging_power = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
            ev_vehicle_count = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        
            for i in range(n_sockets_ev):
                prefix = f'socket_{i:03d}_'
                
                # v7.2: Cargar SOC individual por socket
                if f'{prefix}soc_current' in df_ev.columns:
                    chargers_soc_hourly[:, i] = df_ev[f'{prefix}soc_current'].values[:HOURS_PER_YEAR].astype(np.float32) / 100.0
                    ev_soc_current += df_ev[f'{prefix}soc_current'].values[:HOURS_PER_YEAR].astype(np.float32)
                
                if f'{prefix}soc_target' in df_ev.columns:
                    ev_soc_target += df_ev[f'{prefix}soc_target'].values[:HOURS_PER_YEAR].astype(np.float32)
                if f'{prefix}active' in df_ev.columns:
                    ev_active_count += df_ev[f'{prefix}active'].values[:HOURS_PER_YEAR].astype(np.float32)
                if f'{prefix}charging_power_kw' in df_ev.columns:
                    ev_charging_power += df_ev[f'{prefix}charging_power_kw'].values[:HOURS_PER_YEAR].astype(np.float32)
                if f'{prefix}vehicle_count' in df_ev.columns:
                    ev_vehicle_count += df_ev[f'{prefix}vehicle_count'].values[:HOURS_PER_YEAR].astype(np.float32)
        
            # Rellenar sockets restantes (si hay menos de 38) con ceros
            for i in range(n_sockets_ev, 38):
                chargers_soc_hourly[:, i] = 0.0
        
            # Normalizar SOC por sockets activos
            active_mask = ev_active_count > 0
            ev_soc_current[active_mask] /= ev_active_count[active_mask]
            ev_soc_target[active_mask] /= ev_active_count[active_mask]
        
            ev_data['soc_current'] = ev_soc_current
            ev_data['soc_target'] = ev_soc_target
            ev_data['active_count'] = ev_active_count
            ev_data['charging_power'] = ev_charging_power
            ev_data['vehicle_count'] = ev_vehicle_count
        
            print(f"  [EV] METRICAS CARGADAS: {len(ev_data)} arrays agregados + v7.2 SOC por socket")
            print(f"       SOC promedio: {float(np.mean(ev_soc_current[active_mask]))*100:.1f}%")
            print(f"       Sockets SOC individual: {chargers_soc_hourly.shape} (8760 horas × 38 sockets)")
            print(f"       Vehiculos activos: {float(np.sum(ev_active_count)):,.0f}/ano")
            print(f"       Potencia carga: {float(np.sum(ev_charging_power)):,.0f} kWh/ano")
        else:
            print(f"  [EV] ADVERTENCIA: {ev_chargers_path} no encontrado, usando solo demanda horaria")
            # Fallback: crear array vacío de SOC (será completado en step() con cálculos)
            chargers_soc_hourly = np.zeros((HOURS_PER_YEAR, 38), dtype=np.float32)

        # ====================================================================
        # CHARGER STATISTICS (5to dataset OE2) - potencia max/media por socket
        # ====================================================================
        charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
        charger_max_power: np.ndarray | None = None
        charger_mean_power: np.ndarray | None = None
    
        if charger_stats_path.exists():
            df_stats = pd.read_csv(charger_stats_path)
            if len(df_stats) >= 38:
                charger_max_power = np.array(df_stats['max_power_kw'].values[:38], dtype=np.float32)
                charger_mean_power = np.array(df_stats['mean_power_kw'].values[:38], dtype=np.float32)
                min_pwr = float(np.min(charger_max_power))
                max_pwr = float(np.max(charger_max_power))
                mean_pwr = float(np.mean(charger_mean_power))
                print(f'  [CHARGER STATS] (5to OE2): max_power={min_pwr:.2f}-{max_pwr:.2f} kW, mean={mean_pwr:.2f} kW')
            else:
                print(f'  [CHARGER STATS] WARN: {len(df_stats)} filas < 38, usando valores por defecto')
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
        
            COMUNICACION COMPLETA DEL SISTEMA v5.3
            ================================================================================
            El agente puede ver y coordinar TODOS los componentes del sistema:
            - BESS: estado, energia disponible, senales de carga/descarga
            - Solar: generacion, excedente, ratio de uso para EVs
            - 38 Sockets: demanda, potencia, ocupacion individual
            - Motos: cantidad cargando, en cola, SOC, tiempo restante
            - Mototaxis: igual que motos pero para sus 8 sockets
            - Coordinacion: senales para optimizar flujo de energia
        
            Observation Space (156-dim v5.3):
        
            ENERGIA DEL SISTEMA [0-7] (8 features):
            - [0]: Solar generation normalizada [0,1]
            - [1]: Mall demand normalizada [0,1]
            - [2]: BESS SOC [0,1]
            - [3]: BESS energia disponible normalizada
            - [4]: Solar excedente normalizado
            - [5]: Grid import necesario normalizado
            - [6]: Balance energetico (-1 deficit, +1 excedente)
            - [7]: Capacidad EV libre normalizada
        
            ESTADO DE CARGADORES POR SOCKET [8-45] (38 sockets):
            - Demanda actual de cada socket normalizada [0,1]
        
            POTENCIA ACTUAL POR SOCKET [46-83] (38 sockets):
            - Potencia entregada a cada socket normalizada [0,1]
        
            OCUPACION POR SOCKET [84-121] (38 sockets):
            - 1.0 si hay vehiculo conectado, 0.0 si libre
        
            ESTADO DE VEHICULOS [122-137] (16 features):
            - [122]: Motos cargando actualmente (count/30)
            - [123]: Mototaxis cargando actualmente (count/8)  
            - [124]: Motos en cola esperando (count/100)
            - [125]: Mototaxis en cola esperando (count/20)
            - [126]: SOC promedio motos cargando [0,1]
            - [127]: SOC promedio mototaxis cargando [0,1]
            - [128]: Tiempo restante carga motos (horas norm)
            - [129]: Tiempo restante carga mototaxis (horas norm)
            - [130]: Sockets motos disponibles (count/30)
            - [131]: Sockets mototaxis disponibles (count/8)
            - [132]: Motos cargadas 100% hoy (count/270)
            - [133]: Mototaxis cargados 100% hoy (count/39)
            - [134]: Eficiencia carga actual [0,1]
            - [135]: Ratio solar usado para carga [0,1]
            - [136]: CO2 evitado acumulado (norm)
            - [137]: CO2 evitado potencial si carga mas (norm)
        
            TIME FEATURES [138-143] (6 features):
            - [138]: Hora del dia normalizada [0,1]
            - [139]: Dia de semana normalizado [0,1]
            - [140]: Mes normalizado [0,1]
            - [141]: Indicador hora pico [0,1]
            - [142]: Factor CO2 Iquitos
            - [143]: Tarifa electrica (USD/kWh)
        
            COMUNICACION INTER-SISTEMA [144-155] (12 features):
            - [144]: BESS puede suministrar a EVs [0,1]
            - [145]: Solar suficiente para demanda EV [0,1]
            - [146]: Grid necesario para completar carga [0,1]
            - [147]: Prioridad carga motos vs mototaxis [0,1]
            - [148]: Urgencia de carga (vehiculos pendientes/capacidad)
            - [149]: Oportunidad solar (excedente/demanda EV)
            - [150]: BESS deberia cargar (solar alto, demanda baja)
            - [151]: BESS deberia descargar (solar bajo, demanda alta)
            - [152]: Potencial reduccion CO2 con mas carga
            - [153]: Saturacion del sistema [0,1]
            - [154]: Eficiencia sistema completo [0,1]
            - [155]: Meta diaria de vehiculos (progreso [0,1])

            Action Space (39-dim v5.2):
            - [0]: BESS control [0,1] (0=carga max, 0.5=idle, 1=descarga max)
            - [1:39]: 38 socket setpoints [0,1] (potencia asignada a cada socket)
            """
        
            HOURS_PER_YEAR: int = 8760
            NUM_CHARGERS: int = 38      # v5.2: 19 cargadores × 2 tomas = 38 sockets
            OBS_DIM: int = 156          # v5.3: 8 + 38*3 + 16 + 6 + 12 = 156 (comunicacion completa)
            ACTION_DIM: int = 39        # v5.2: 1 BESS + 38 sockets

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
                chargers_soc_hourly: np.ndarray | None = None,  # v7.2: SOC real por socket
                bess_metrics: dict[str, np.ndarray] | None = None,
                ev_metrics: dict[str, np.ndarray] | None = None,
                chargers_co2_data: dict[str, np.ndarray] | None = None,  # v7.0: CO2 directo EV
                solar_co2_data: dict[str, np.ndarray] | None = None,     # v7.1: CO2 indirecto solar
                max_steps: int = 8760
            ) -> None:
                """Inicializa environment con TODOS los datos OE2 reales v7.2 (incluye SOC real por socket)."""
                super().__init__()
            
                self.reward_calculator = reward_calc
                self.context = ctx
                self.max_steps = max_steps
            
                # DATOS REALES (8760 horas = 1 ano)
                self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
                self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
                self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
                self.bess_soc_hourly = np.asarray(bess_soc_arr, dtype=np.float32)
                
                # v7.2: SOC REAL POR SOCKET (para cálculo mejorado de vehículos cargados)
                self.chargers_soc_hourly = chargers_soc_hourly if chargers_soc_hourly is not None else None
            
                # ESTADISTICAS REALES DE CARGADORES (5to dataset OE2)
                if charger_max_power_kw is not None:
                    self.charger_max_power = np.asarray(charger_max_power_kw, dtype=np.float32)
                else:
                    # Fallback v5.2: 7.4 kW por socket (Modo 3 monofasico 32A @ 230V)
                    self.charger_max_power = np.full(self.NUM_CHARGERS, 7.4, dtype=np.float32)
                if charger_mean_power_kw is not None:
                    self.charger_mean_power = np.asarray(charger_mean_power_kw, dtype=np.float32)
                else:
                    # Fallback v5.2: potencia efectiva = 7.4 × 0.62 = 4.6 kW
                    self.charger_mean_power = np.full(self.NUM_CHARGERS, 4.6, dtype=np.float32)
            
                # METRICAS REALES BESS (CO2 indirecto, costos, tarifas, flujos energeticos)
                self.bess_metrics = bess_metrics if bess_metrics is not None else {}
            
                # METRICAS REALES EV (SOC, conteos, potencias por hora)
                self.ev_metrics = ev_metrics if ev_metrics is not None else {}
                
                # v7.0: DATOS REALES CO2 DIRECTO DE CHARGERS (EV reemplaza gasolina)
                self.chargers_co2_data = chargers_co2_data if chargers_co2_data is not None else {}
                
                # v7.1: DATOS REALES CO2 INDIRECTO DE SOLAR (evita importar de red)
                self.solar_co2_data = solar_co2_data if solar_co2_data is not None else {}
            
                # Validacion
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
                self.episode_ev_satisfied = 0.0
            
                # Tracking acumulativo (backwards compatibility)
                self.co2_avoided_total = 0.0
                self.solar_kwh_total = 0.0
                self.cost_total = 0.0
                self.grid_import_total = 0.0
            
                # [v5.3] ESTADO DE VEHICULOS (para comunicacion del sistema)
                self.motos_charging_now: int = 0
                self.mototaxis_charging_now: int = 0
                self.motos_waiting: int = 0
                self.mototaxis_waiting: int = 0
                self.motos_soc_avg: float = 0.0
                self.mototaxis_soc_avg: float = 0.0
                self.motos_time_remaining: float = 0.0
                self.mototaxis_time_remaining: float = 0.0
                self.motos_charged_today: int = 0
                self.mototaxis_charged_today: int = 0
                self.daily_co2_avoided: float = 0.0
            
                # [v5.3] COMUNICACION INTER-SISTEMA
                self.bess_available_kwh: float = 0.0
                self.solar_surplus_kwh: float = 0.0
                self.current_grid_import: float = 0.0
                self.system_efficiency: float = 0.0
            
                # [OK] TRACKING DE VEHICULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
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

            
            def _make_observation(self, hour_idx: int) -> np.ndarray:
                """
                Crea observacion v5.3 (156-dim) con COMUNICACION COMPLETA del sistema.

                NORMALIZACION CRITICA:
                Todas las features estan en rango ~[0,1] para estabilidad del training.
            
                COMUNICACION DEL SISTEMA:
                - El agente ve el estado completo de BESS, Solar, EVs, Cargadores
                - Puede coordinar carga de motos/mototaxis con disponibilidad solar
                - Sabe cuantos vehiculos estan cargando y cuantos faltan
                - Recibe senales de urgencia y oportunidad
                """
                obs = np.zeros(self.OBS_DIM, dtype=np.float32)
                h = hour_idx % self.HOURS_PER_YEAR
                hour_24 = h % 24
                day_of_year = (h // 24) % 365

                # ================================================================
                # [0-7] ENERGIA DEL SISTEMA (8 features)
                # ================================================================
                solar_kw = float(self.solar_hourly[h])
                mall_kw = float(self.mall_hourly[h])
                bess_soc = float(self.bess_soc_hourly[h])
            
                # Calcular balance energetico
                ev_demand_estimate = float(np.sum(self.chargers_hourly[h]))
                total_demand = mall_kw + ev_demand_estimate
                solar_surplus = max(0.0, solar_kw - total_demand)
                grid_import_needed = max(0.0, total_demand - solar_kw)
            
                # BESS energia disponible (SOC × capacidad max × eficiencia)
                bess_energy_available = bess_soc * BESS_MAX_KWH_CONST * 0.90  # 90% eficiencia
            
                obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)                    # Solar norm
                obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)                      # Mall demand
                obs[2] = np.clip(bess_soc, 0.0, 1.0)                                   # BESS SOC
                obs[3] = np.clip(bess_energy_available / BESS_MAX_KWH_CONST, 0.0, 1.0) # BESS disponible
                obs[4] = np.clip(solar_surplus / SOLAR_MAX_KW, 0.0, 1.0)               # Solar excedente
                obs[5] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)                 # Grid import
                obs[6] = np.clip((solar_kw - total_demand) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)  # Balance
                obs[7] = np.clip(1.0 - ev_demand_estimate / (self.NUM_CHARGERS * CHARGER_MAX_KW), 0.0, 1.0)  # Capacidad libre

                # ================================================================
                # [8-45] DEMANDA POR SOCKET (38 features)
                # ================================================================
                if self.chargers_hourly.shape[1] >= self.NUM_CHARGERS:
                    raw_demands = self.chargers_hourly[h, :self.NUM_CHARGERS]
                else:
                    raw_demands = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
                    raw_demands[:self.chargers_hourly.shape[1]] = self.chargers_hourly[h]
            
                obs[8:46] = np.clip(raw_demands / CHARGER_MAX_KW, 0.0, 1.0)

                # ================================================================
                # [46-83] POTENCIA ACTUAL POR SOCKET (38 features)
                # ================================================================
                efficiency_factor = 0.7 if 6 <= hour_24 <= 22 else 0.5
                obs[46:84] = obs[8:46] * efficiency_factor

                # ================================================================
                # [84-121] OCUPACION POR SOCKET (38 features)
                # ================================================================
                occupancy = (raw_demands > 0.1).astype(np.float32)
                obs[84:122] = occupancy

                # ================================================================
                # [122-137] ESTADO DE VEHICULOS (16 features) - CRITICO PARA APRENDIZAJE
                # ================================================================
                motos_sockets = occupancy[:30]  # Primeros 30 sockets = motos
                taxis_sockets = occupancy[30:]  # Ultimos 8 sockets = mototaxis
            
                self.motos_charging_now = int(np.sum(motos_sockets))
                self.mototaxis_charging_now = int(np.sum(taxis_sockets))
            
                # Estimar vehiculos en cola segun hora pico
                if 6 <= hour_24 <= 22:
                    self.motos_waiting = max(0, int(270 / 24 - self.motos_charging_now))
                    self.mototaxis_waiting = max(0, int(39 / 24 - self.mototaxis_charging_now))
                else:
                    self.motos_waiting = 0
                    self.mototaxis_waiting = 0
            
                # SOC promedio (basado en potencia entregada)
                motos_power = obs[46:76]
                taxis_power = obs[76:84]
                self.motos_soc_avg = float(np.mean(motos_power)) if self.motos_charging_now > 0 else 0.0
                self.mototaxis_soc_avg = float(np.mean(taxis_power)) if self.mototaxis_charging_now > 0 else 0.0
            
                # Tiempo restante de carga (horas estimadas)
                self.motos_time_remaining = (1.0 - self.motos_soc_avg) * 0.76
                self.mototaxis_time_remaining = (1.0 - self.mototaxis_soc_avg) * 1.2
            
                # Sockets disponibles
                motos_available = 30 - self.motos_charging_now
                taxis_available = 8 - self.mototaxis_charging_now
            
                # Progreso diario (resetea cada 24 horas)
                hour_in_day = h % 24
                if hour_in_day == 0:
                    self.motos_charged_today = 0
                    self.mototaxis_charged_today = 0
                    self.daily_co2_avoided = 0.0
            
                # CALCULAR VEHICULOS COMPLETADOS DESDE DATASET REAL
                # Usar ev_energia_motos_kwh y ev_energia_mototaxis_kwh del dataset
                if h < len(self.chargers_hourly):
                    # Cargar datos reales del dataset
                    try:
                        # Leer energía cargada por tipo de vehículo
                        ev_energy_motos_kwh = float(self.chargers_hourly[h, 0]) if len(self.chargers_hourly.shape) > 1 else 0.0
                        ev_energy_taxis_kwh = float(self.chargers_hourly[h, 1]) if len(self.chargers_hourly.shape) > 1 else 0.0
                    except (IndexError, TypeError, ValueError):
                        ev_energy_motos_kwh = 0.0
                        ev_energy_taxis_kwh = 0.0
                else:
                    ev_energy_motos_kwh = 0.0
                    ev_energy_taxis_kwh = 0.0
                
                # Calcular vehiculos completados basado en energía necesaria
                # Moto: 2.90 kWh para cargar de 20% a 80% SOC
                # Mototaxi: 4.68 kWh para cargar de 20% a 80% SOC
                motos_completed = int(ev_energy_motos_kwh / max(MOTO_ENERGY_TO_CHARGE, 0.01))
                taxis_completed = int(ev_energy_taxis_kwh / max(MOTOTAXI_ENERGY_TO_CHARGE, 0.01))
                
                self.motos_charged_today += motos_completed
                self.mototaxis_charged_today += taxis_completed
            
                # Eficiencia y ratios
                total_ev_power = float(np.sum(raw_demands))
                solar_for_ev_ratio = min(1.0, solar_kw / max(1.0, total_ev_power)) if total_ev_power > 0 else 0.0
                charge_efficiency = float(np.sum(obs[46:84])) / max(1.0, float(np.sum(obs[8:46])))
            
                # CO2 potencial
                co2_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS
            
                obs[122] = self.motos_charging_now / 30.0                                # Motos cargando
                obs[123] = self.mototaxis_charging_now / 8.0                             # Mototaxis cargando
                obs[124] = np.clip(self.motos_waiting / 100.0, 0.0, 1.0)                 # Motos en cola
                obs[125] = np.clip(self.mototaxis_waiting / 20.0, 0.0, 1.0)              # Mototaxis en cola
                obs[126] = self.motos_soc_avg                                            # SOC promedio motos
                obs[127] = self.mototaxis_soc_avg                                        # SOC promedio mototaxis
                obs[128] = np.clip(self.motos_time_remaining / 2.0, 0.0, 1.0)            # Tiempo restante motos
                obs[129] = np.clip(self.mototaxis_time_remaining / 2.0, 0.0, 1.0)        # Tiempo restante taxis
                obs[130] = motos_available / 30.0                                        # Sockets motos libres
                obs[131] = taxis_available / 8.0                                         # Sockets taxis libres
                obs[132] = np.clip(self.motos_charged_today / 270.0, 0.0, 1.0)           # Motos cargadas hoy
                obs[133] = np.clip(self.mototaxis_charged_today / 39.0, 0.0, 1.0)        # Taxis cargados hoy
                obs[134] = np.clip(charge_efficiency, 0.0, 1.0)                          # Eficiencia carga
                obs[135] = solar_for_ev_ratio                                            # Ratio solar->EV
                obs[136] = np.clip(self.daily_co2_avoided / 500.0, 0.0, 1.0)             # CO2 evitado hoy
                obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)                      # CO2 potencial

                # ================================================================
                # [138-143] TIME FEATURES (6 features)
                # ================================================================
                obs[138] = float(hour_24) / 24.0                                         # Hora
                obs[139] = float(day_of_year % 7) / 7.0                                  # Dia semana
                obs[140] = float((day_of_year // 30) % 12) / 12.0                        # Mes
                obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0                            # Hora pico
                obs[142] = float(self.context.co2_factor_kg_per_kwh)                     # Factor CO2
                obs[143] = 0.15                                                          # Tarifa

                # ================================================================
                # [144-155] COMUNICACION INTER-SISTEMA (12 features)
                # ================================================================
                bess_can_supply = 1.0 if bess_energy_available > total_ev_power else bess_energy_available / max(1.0, total_ev_power)
                solar_sufficient = 1.0 if solar_kw >= total_ev_power else solar_kw / max(1.0, total_ev_power)
                grid_needed_ratio = grid_import_needed / max(1.0, total_ev_power) if total_ev_power > 0 else 0.0
                priority_motos = self.motos_waiting / max(1, self.motos_waiting + self.mototaxis_waiting) if (self.motos_waiting + self.mototaxis_waiting) > 0 else 0.5
                total_waiting = self.motos_waiting + self.mototaxis_waiting
                total_capacity = motos_available + taxis_available
                urgency = total_waiting / max(1, total_capacity) if total_capacity > 0 else 0.0
                solar_opportunity = solar_surplus / max(1.0, total_ev_power) if total_ev_power > 0 else 1.0
                should_charge_bess = 1.0 if (solar_surplus > 100 and bess_soc < 0.8) else 0.0
                should_discharge_bess = 1.0 if (solar_kw < total_demand * 0.5 and bess_soc > 0.3) else 0.0
                co2_reduction_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS / 100.0
                saturation = (self.motos_charging_now + self.mototaxis_charging_now) / self.NUM_CHARGERS
                total_input = solar_kw + bess_energy_available / 10.0
                total_output = total_ev_power
                system_eff = min(1.0, total_output / max(1.0, total_input))
                daily_target = 309  # 270 motos + 39 mototaxis
                daily_progress = (self.motos_charged_today + self.mototaxis_charged_today) / daily_target
            
                obs[144] = np.clip(bess_can_supply, 0.0, 1.0)
                obs[145] = np.clip(solar_sufficient, 0.0, 1.0)
                obs[146] = np.clip(grid_needed_ratio, 0.0, 1.0)
                obs[147] = priority_motos
                obs[148] = np.clip(urgency, 0.0, 1.0)
                obs[149] = np.clip(solar_opportunity, 0.0, 1.0)
                obs[150] = should_charge_bess
                obs[151] = should_discharge_bess
                obs[152] = np.clip(co2_reduction_potential, 0.0, 1.0)
                obs[153] = saturation
                obs[154] = system_eff
                obs[155] = np.clip(daily_progress, 0.0, 1.0)

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
                self.episode_ev_satisfied = 0.0
            
                self.co2_avoided_total = 0.0
                self.solar_kwh_total = 0.0
                self.cost_total = 0.0
                self.grid_import_total = 0.0
            
                # [v5.3] RESET ESTADO DE VEHICULOS
                self.motos_charging_now = 0
                self.mototaxis_charging_now = 0
                self.motos_waiting = 0
                self.mototaxis_waiting = 0
                self.motos_soc_avg = 0.0
                self.mototaxis_soc_avg = 0.0
                self.motos_time_remaining = 0.0
                self.mototaxis_time_remaining = 0.0
                self.motos_charged_today = 0
                self.mototaxis_charged_today = 0
                self.daily_co2_avoided = 0.0
            
                # [v5.3] RESET COMUNICACION INTER-SISTEMA
                self.bess_available_kwh = 0.0
                self.solar_surplus_kwh = 0.0
                self.current_grid_import = 0.0
                self.system_efficiency = 0.0
            
                # [OK] RESET SOC TRACKERS
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
                """Ejecuta un paso de simulacion (1 hora) - MISMA ESTRUCTURA QUE PPO."""
                self.step_count += 1
                h = (self.step_count - 1) % self.HOURS_PER_YEAR

                # DATOS REALES (OE2 timeseries)
                solar_kw = float(self.solar_hourly[h])
                mall_kw = float(self.mall_hourly[h])
                charger_demand = self.chargers_hourly[h].astype(np.float32)
                bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

                # PROCESAR ACCION (39-dim: 1 BESS + 38 sockets)
                bess_action = np.clip(action[0], 0.0, 1.0)
                charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

                # CALCULAR ENERGIA (usando max_power real del 5to dataset OE2)
                charger_power_effective = charger_setpoints * self.charger_max_power[:self.n_chargers]
                ev_charging_kwh = float(np.sum(np.minimum(charger_power_effective, charger_demand)))
                total_demand_kwh = mall_kw + ev_charging_kwh
            
                # BESS power (positivo = descarga, negativo = carga)
                bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
            
                # Separar motos y mototaxis (30 motos + 8 mototaxis = 38 sockets)
                motos_demand = float(np.sum(charger_demand[:30] * charger_setpoints[:30]))
                mototaxis_demand = float(np.sum(charger_demand[30:] * charger_setpoints[30:]))
                motos_charging = int(np.sum(charger_setpoints[:30] > 0.5))
                mototaxis_charging = int(np.sum(charger_setpoints[30:] > 0.5))

                # GRID BALANCE
                net_demand = total_demand_kwh - bess_power_kw
                grid_import_kwh = max(0.0, net_demand - solar_kw)
                grid_export_kwh = max(0.0, solar_kw - net_demand)

                # ===== CO2 CALCULATIONS v7.1 (IDÉNTICO A PPO) =====
                # FUENTE: chargers_ev_ano_2024_v3.csv columnas:
                #   - co2_reduccion_motos_kg
                #   - co2_reduccion_mototaxis_kg  
                #   - reduccion_directa_co2_kg = motos + mototaxis (DATO REAL)
                # NOTA: NO multiplicar por setpoint - es el CO2 evitado por cambio combustible
                
                # CO2 DIRECTO: Usar datos REALES del dataset chargers si disponibles
                # IDÉNTICO A PPO línea 985-989
                try:
                    co2_motos_directo = float(self.chargers_co2_data['co2_motos_kg'][h]) if 'co2_motos_kg' in self.chargers_co2_data else 0.0
                    co2_taxis_directo = float(self.chargers_co2_data['co2_mototaxis_kg'][h]) if 'co2_mototaxis_kg' in self.chargers_co2_data else 0.0
                    co2_avoided_direct_kg = co2_motos_directo + co2_taxis_directo
                except (KeyError, IndexError, TypeError):
                    co2_avoided_direct_kg = 0.0
                
                # ===== CO2 INDIRECTO v7.1: BESS + SOLAR (IDÉNTICO A PPO) =====
                # FUENTE: bess_ano_2024.csv (columna co2_avoided_indirect_kg)
                #         pv_generation_citylearn_enhanced_v2.csv (columna reduccion_indirecta_co2_kg)
                # EV: cambio fósil -> eléctrico (CO2 DIRECTO)
                # SOLAR + BESS: evitan importar de red térmica (CO2 INDIRECTO)
                # IDÉNTICO A PPO línea 994-1013
                
                # CO2 INDIRECTO BESS: Usar datos REALES del dataset BESS si disponibles
                # IDÉNTICO A PPO línea 1003-1010
                try:
                    co2_indirecto_bess_kg = float(self.bess_metrics['co2_avoided'][h]) if 'co2_avoided' in self.bess_metrics else 0.0
                except (KeyError, IndexError, TypeError):
                    # Fallback: calcular con peak_shaving_factor (IGUAL A PPO)
                    if mall_kw > 2000.0:
                        peak_factor = 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
                    else:
                        peak_factor = 0.5 + (mall_kw / 2000.0) * 0.5
                    bess_discharge = max(0.0, bess_power_kw)
                    co2_indirecto_bess_kg = bess_discharge * peak_factor * CO2_FACTOR_IQUITOS if bess_discharge > 0 else 0.0
                
                # CO2 INDIRECTO SOLAR: Usar datos REALES del dataset solar si disponibles
                # IDÉNTICO A PPO línea 994-998
                try:
                    co2_indirecto_solar_kg = float(self.solar_co2_data['co2_avoided_kg'][h]) if 'co2_avoided_kg' in self.solar_co2_data else 0.0
                except (KeyError, IndexError, TypeError):
                    # Fallback: calcular desde flujo solar (IGUAL A PPO)
                    solar_used = min(solar_kw, ev_charging_kwh + mall_kw)
                    co2_indirecto_solar_kg = solar_used * CO2_FACTOR_IQUITOS
                
                # TOTAL CO2 INDIRECTO = BESS + SOLAR
                co2_avoided_indirect_kg = co2_indirecto_solar_kg + co2_indirecto_bess_kg
                
                # TOTAL CO2 EVITADO = DIRECTO (EV) + INDIRECTO (SOLAR + BESS)
                co2_avoided_total_kg = co2_avoided_direct_kg + co2_avoided_indirect_kg
                
                # COSTO: Usar valores REALES del dataset
                if 'cost_soles' in self.chargers_co2_data and len(self.chargers_co2_data['cost_soles']) > h:
                    ev_cost_soles = float(self.chargers_co2_data['cost_soles'][h])
                else:
                    ev_cost_soles = ev_charging_kwh * 0.35  # Tarifa promedio fallback
                
                if 'cost' in self.bess_metrics and len(self.bess_metrics['cost']) > h:
                    grid_cost_soles = float(self.bess_metrics['cost'][h])
                else:
                    grid_cost_soles = grid_import_kwh * 0.30  # Tarifa promedio fallback
                
                total_cost_soles = ev_cost_soles + grid_cost_soles
            
                # CO2 grid para tracking
                co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS

                # EV SATISFACTION - METODO REALISTA (similar a SAC)
                # Basado en cuanta carga se esta entregando vs la demanda
                if float(np.sum(charger_demand)) > 0.1:
                    charge_ratio = ev_charging_kwh / max(1.0, float(np.sum(charger_demand)))
                    ev_soc_avg = np.clip(0.80 + 0.20 * charge_ratio, 0.0, 1.0)
                else:
                    ev_soc_avg = 0.95
            
                # v7.2 MEJORADO: Contar vehiculos cargados diferenciando MOTOS vs MOTOTAXIS
                # CONSIDERAR:
                #   1. SOC REAL del dataset (socket_{i}_soc_current)
                #   2. SOC ENTREGADO en esta hora (potencia actual / maxima)
                #   3. Cantidad MÁXIMA cargable por día (dependencia capacidad batería)
                #
                # REALIDAD OE2 v5.2:
                #   - Motos: 30 sockets, capacidad ~10 kWh, necesitan 1-2 horas al 100%
                #   - Mototaxis: 8 sockets, capacidad ~15 kWh, necesitan 2-3 horas al 100%
                
                # Leer SOC ACTUAL del dataset si está disponible
                chargers_soc_hourly = getattr(self, 'chargers_soc_hourly', None)
                if chargers_soc_hourly is not None and h < len(chargers_soc_hourly):
                    # SOC REAL del dataset [0,1]
                    soc_real = chargers_soc_hourly[h]
                else:
                    # Fallback: calcular SOC desde potencia entregada
                    soc_real = np.clip(ev_charging_kwh / max(1.0, float(np.sum(charger_demand))), 0.0, 1.0)
                
                # MEJORADO: Considerar SOC actual + potencia entregada esta hora
                # Formula: SOC_nuevo = SOC_actual + (potencia_hora / capacidad_bateria)
                # Para motos: capacidad promedio ~12 kWh (rango 10-15 kWh)
                # Para mototaxis: capacidad promedio ~18 kWh (rango 15-20 kWh)
                
                MOTO_CAPACITY_KWH = 12.0
                MOTOTAXI_CAPACITY_KWH = 18.0
                
                # Calcular carga incremental esta hora por socket
                soc_updated = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
                
                for i in range(min(self.NUM_CHARGERS, len(charger_power_effective))):
                    # SOC inicial del socket (dato real si existe)
                    if chargers_soc_hourly is not None and h < len(chargers_soc_hourly) and i < len(chargers_soc_hourly[h]):
                        soc_inicial = float(chargers_soc_hourly[h][i]) if isinstance(chargers_soc_hourly[h], (list, np.ndarray)) else soc_real
                    else:
                        soc_inicial = 0.5  # Asunción: comienzan a media carga
                    
                    # Potencia entregada esta hora
                    power_this_hour = float(charger_power_effective[i]) if i < len(charger_power_effective) else 0.0
                    
                    # Capacidad del vehículo (diferencia por tipo)
                    capacity = MOTO_CAPACITY_KWH if i < 30 else MOTOTAXI_CAPACITY_KWH
                    
                    # SOC nuevo = SOC inicial + (potencia / capacidad * eficiencia)
                    efficiency = 0.92  # Pérdidas de carga ~8%
                    soc_increment = (power_this_hour * efficiency / capacity) if capacity > 0 else 0.0
                    soc_updated[i] = np.clip(soc_inicial + soc_increment, 0.0, 1.0)
                
                # Contar vehiculos por SOC para MOTOS (sockets 0-29)
                motos_soc = soc_updated[:30]
                motos_10 = int(np.sum(motos_soc >= 0.10))
                motos_20 = int(np.sum(motos_soc >= 0.20))
                motos_30 = int(np.sum(motos_soc >= 0.30))
                motos_50 = int(np.sum(motos_soc >= 0.50))
                motos_70 = int(np.sum(motos_soc >= 0.70))
                motos_80 = int(np.sum(motos_soc >= 0.80))
                motos_100 = int(np.sum(motos_soc >= 1.00))
            
                # Contar vehiculos por SOC para MOTOTAXIS (sockets 30-37)
                taxis_soc = soc_updated[30:38]
                taxis_10 = int(np.sum(taxis_soc >= 0.10))
                taxis_20 = int(np.sum(taxis_soc >= 0.20))
                taxis_30 = int(np.sum(taxis_soc >= 0.30))
                taxis_50 = int(np.sum(taxis_soc >= 0.50))
                taxis_70 = int(np.sum(taxis_soc >= 0.70))
                taxis_80 = int(np.sum(taxis_soc >= 0.80))
                taxis_100 = int(np.sum(taxis_soc >= 1.00))
            
                # Actualizar maximos del episodio
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

                # CALCULAR RECOMPENSA MULTIOBJETIVO v5.3 (PRIORIZA CARGAR VEHICULOS)
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
                
                    # ================================================================
                    # [v5.3] REWARD QUE PRIORIZA CARGAR MAS VEHICULOS
                    # ================================================================
                    # Total cargando vs capacidad maxima (38 sockets)
                    total_vehicles = motos_charging + mototaxis_charging
                    vehicles_ratio = total_vehicles / 38.0  # MAX 38
                
                    # Componentes de reward v5.3:
                    r_vehicles_charging = vehicles_ratio * 0.25        # 25% - Mas vehiculos cargando
                    r_vehicles_100 = (motos_100 + taxis_100) / 309.0 * 0.20  # 20% - Completar al 100%
                    r_co2_avoided = np.clip(co2_avoided_total_kg / 50.0, 0.0, 0.10)  # 10% - CO2 evitado
                
                    # Penalizar grid import alto (incentiva solar)
                    r_grid_penalty = -np.clip(grid_import_kwh / 500.0, 0.0, 0.10)  # -10% max
                
                    # Bonus por usar solar para EVs
                    ev_demand_total = float(np.sum(charger_demand))
                    if ev_demand_total > 0.1:
                        solar_for_ev = min(solar_kw, ev_demand_total) / ev_demand_total
                    else:
                        solar_for_ev = 0.0
                    r_solar_to_ev = solar_for_ev * 0.10  # 10% - Solar -> EV
                
                    # Bonus BESS (descargar durante pico, cargar con excedente)
                    hour_24 = h % 24
                    bess_direction = bess_action - 0.5  # -0.5 -> +0.5
                    is_peak = 6 <= hour_24 <= 22
                    if is_peak and solar_kw < ev_demand_total and bess_direction > 0:
                        r_bess = 0.08  # Bonus: descargar BESS cuando hay deficit solar
                    elif not is_peak and solar_kw > ev_demand_total * 1.2 and bess_direction < 0:
                        r_bess = 0.08  # Bonus: cargar BESS con excedente solar
                    else:
                        r_bess = 0.0
                
                    # Socket efficiency: penalizar sockets activos sin carga
                    active_sockets = float(np.sum(charger_setpoints > 0.1))
                    sockets_with_demand = float(np.sum(charger_demand > 0.1))
                    if active_sockets > 0:
                        socket_efficiency = min(sockets_with_demand, active_sockets) / active_sockets
                    else:
                        socket_efficiency = 1.0
                    r_socket_eff = socket_efficiency * 0.05  # 5% - Eficiencia socket
                
                    # Time penalty: urgencia de completar vehiculos antes de fin de dia
                    hour_norm = hour_24 / 24.0
                    daily_target = 309  # 270 motos + 39 mototaxis
                    daily_completed = self.motos_charged_today + self.mototaxis_charged_today
                    if hour_norm > 0.5:  # Segunda mitad del dia
                        progress = daily_completed / daily_target
                        r_time_urgency = 0.02 if progress > hour_norm else -0.02
                    else:
                        r_time_urgency = 0.0
                
                    # COMBINAR REWARD COMPONENTS
                    reward_custom = (
                        r_vehicles_charging +  # 25% - Prioridad #1: Mas vehiculos cargando
                        r_vehicles_100 +       # 20% - Prioridad #2: Completar cargas
                        r_co2_avoided +        # 10% - CO2 evitado
                        r_grid_penalty +       # -10% max - Penalidad grid
                        r_solar_to_ev +        # 10% - Usar solar para EVs
                        r_bess +               # 8% - Coordinacion BESS
                        r_socket_eff +         # 5% - Eficiencia sockets
                        r_time_urgency         # +/-2% - Urgencia temporal
                    )
                
                    # Mezclar con reward original (30% original, 70% custom v5.3)
                    reward_val = reward_val * 0.30 + reward_custom * 0.70
                    reward_val = float(np.clip(reward_val, -1.0, 1.0))
                
                    # Guardar componentes adicionales para logging
                    components['r_vehicles_charging'] = float(r_vehicles_charging)
                    components['r_vehicles_100'] = float(r_vehicles_100)
                    components['r_bess_control'] = float(r_bess)
                    components['r_socket_eff'] = float(r_socket_eff)
                    components['r_solar_to_ev'] = float(r_solar_to_ev)
                
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

                # OBSERVACION
                obs = self._make_observation(self.step_count)

                done = self.step_count >= self.max_steps
                truncated = False

                # INFO DICT (27+ metricas - v7.0 con TODOS los CO2 y costos REALES)
                info: dict[str, Any] = {
                    # CO2 (7 metricas)
                    'co2_grid_kg': co2_grid_kg,
                    'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
                    'co2_avoided_direct_kg': co2_avoided_direct_kg,
                    'co2_avoided_total_kg': co2_avoided_total_kg,
                    # COSTOS v7.0 (3 metricas nuevas)
                    'ev_cost_soles': ev_cost_soles if 'ev_cost_soles' in dir() else 0.0,
                    'grid_cost_soles': grid_cost_soles if 'grid_cost_soles' in dir() else 0.0,
                    'total_cost_soles': total_cost_soles if 'total_cost_soles' in dir() else 0.0,
                    # ENERGIA (6 metricas)
                    'solar_generation_kwh': solar_kw,
                    'ev_charging_kwh': ev_charging_kwh,
                    'mall_demand_kw': mall_kw,
                    'grid_import_kwh': grid_import_kwh,
                    'grid_export_kwh': grid_export_kwh,
                    'bess_power_kw': float(bess_power_kw),
                    'bess_soc': bess_soc,
                    'ev_soc_avg': float(ev_soc_avg),
                    # VEHICULOS (4 metricas)
                    'motos_charging': motos_charging,
                    'mototaxis_charging': mototaxis_charging,
                    'motos_demand_kwh': motos_demand,
                    'mototaxis_demand_kwh': mototaxis_demand,
                    # TIEMPO (3 metricas)
                    'hour': h % 24,
                    'day': h // 24,
                    'step': self.step_count,
                    # TRACKING (3 metricas)
                    'episode_reward': self.episode_reward,
                    'episode_co2_avoided_kg': self.co2_avoided_total,
                    'episode_solar_kwh': self.solar_kwh_total,
                    # REWARD COMPONENTS (5 metricas adicionales)
                    'r_solar': components.get('r_solar', 0.0),
                    'r_cost': components.get('r_cost', 0.0),
                    'r_ev': components.get('r_ev', 0.0),
                    'r_grid': components.get('r_grid', 0.0),
                    'r_co2': components.get('r_co2', 0.0),
                    # [OK] VEHICULOS CARGADOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
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

        # Crear environment con datos cargados - COMPLETO CON TODAS LAS METRICAS OE2 v7.2
        env = CityLearnEnvironment(
            reward_calc=reward_calculator,
            ctx=context,
            solar_kw=solar_hourly,
            chargers_kw=chargers_hourly,
            mall_kw=mall_hourly,
            bess_soc_arr=bess_soc,
            charger_max_power_kw=charger_max_power,
            charger_mean_power_kw=charger_mean_power,
            chargers_soc_hourly=chargers_soc_hourly,     # v7.2: SOC real por socket para conteo mejorado
            bess_metrics=bess_data,              # CO2 indirecto BESS (evita grid)
            ev_metrics=ev_data,                  # SOC, conteos, potencias EV
            chargers_co2_data=chargers_co2_data, # v7.0: CO2 directo EV (reemplaza gasolina)
            solar_co2_data=solar_co2_data,       # v7.1: CO2 indirecto solar (evita grid)
            max_steps=HOURS_PER_YEAR
        )
        print('  OK Environment creado (v7.2 con TODOS los datos OE2 + SOC real por socket)')
        print(f'    - Observation: {env.observation_space.shape} (156-dim)')
        print(f'    - Action: {env.action_space.shape}')
        if chargers_soc_hourly is not None and chargers_soc_hourly.size > 0:
            print(f'    - Socket SOC real: {chargers_soc_hourly.shape} (8760 horas × 38 sockets)')
        if bess_data:
            print(f'    - BESS metricas (CO2 indirecto): {list(bess_data.keys())}')
        if ev_data:
            print(f'    - EV metricas: {list(ev_data.keys())}')
        if chargers_co2_data:
            print(f'    - Chargers CO2 (DIRECTO - EV): {list(chargers_co2_data.keys())}')
        if solar_co2_data:
            print(f'    - Solar CO2 (INDIRECTO): {list(solar_co2_data.keys())}')
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
            rms_prop_eps=a2c_config.rms_prop_eps,
            use_rms_prop=a2c_config.use_rms_prop,
            normalize_advantage=a2c_config.normalize_advantage,
            policy_kwargs=a2c_config.policy_kwargs,
            verbose=0,
            device=DEVICE,
            tensorboard_log=None,
        )

        print(f'  OK A2C agent creado (DEVICE: {DEVICE.upper()})')
        print(f'    - Learning rate: {a2c_config.learning_rate}')
        print(f'    - N steps: {a2c_config.n_steps}')
        print(f'    - Gamma: {a2c_config.gamma}')
        print(f'    - GAE lambda: {a2c_config.gae_lambda}')
        print(f'    - Entropy coef: {a2c_config.ent_coef}')
        print(f'    - Value coef: {a2c_config.vf_coef}')
        print(f'    - Max grad norm: {a2c_config.max_grad_norm}')
        print(f'    - Use RMSProp: {a2c_config.use_rms_prop}')
        print(f'    - Normalize advantage: {a2c_config.normalize_advantage}')
        print()

        # ========================================================================
        # PASO 6: ENTRENAR A2C
        # ========================================================================
        print('[6] ENTRENAR A2C')
        print('-' * 80)

        # ENTRENAMIENTO: 10 episodios completos = 10 × 8,760 timesteps = 87,600 pasos
        # Velocidad GPU RTX 4060 (on-policy A2C): ~650-700 timesteps/segundo
        # [v7.2: Reward weights updated - vehicles_charged 0.35, grid_stable 0.15]
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
        print('  [GRAPH] CONFIGURACION ENTRENAMIENTO A2C (100% DATOS REALES OE2)')
        print(f'     Episodios: {EPISODES} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
        print(f'     Device: {DEVICE.upper()}')
        print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
        print(f'     Duracion: {DURATION_TEXT}')
        print('     Datos: REALES OE2 (chargers_ev_ano_2024_v3.csv 38 sockets, 1,700 kWh BESS max SOC, 4.05 MWp solar)')
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

        # Callbacks: Checkpoint + DetailedLogging + A2CMetrics
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
    
        # [OK] NUEVO: A2CMetricsCallback para metricas especificas A2C
        a2c_metrics_callback = A2CMetricsCallback(
            output_dir=OUTPUT_DIR,
            config=a2c_config,
            verbose=1
        )
    
        callback_list = CallbackList([checkpoint_callback, detailed_callback, a2c_metrics_callback])

        a2c_agent.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callback_list,
            progress_bar=False
        )

        elapsed = time.time() - start_time
        a2c_agent.save(CHECKPOINT_DIR / 'a2c_final_model.zip')

        print()
        print('  [OK] RESULTADO ENTRENAMIENTO:')
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
            print(f'  [OK] trace_a2c.csv: {len(trace_df)} registros -> {trace_path}')
        else:
            print('  [!] trace_a2c.csv: Sin registros (callback vacio)')

        # 2. timeseries_a2c.csv - Series temporales horarias
        if detailed_callback.timeseries_records:
            ts_df = pd.DataFrame(detailed_callback.timeseries_records)
            ts_path = OUTPUT_DIR / 'timeseries_a2c.csv'
            ts_df.to_csv(ts_path, index=False)
            print(f'  [OK] timeseries_a2c.csv: {len(ts_df)} registros -> {ts_path}')
        else:
            print('  [!] timeseries_a2c.csv: Sin registros (callback vacio)')

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
                'chargers_path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
                'chargers_sockets': 38,
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
                # [OK] NUEVAS metricas de evolucion
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
            # [OK] NUEVAS secciones de metricas detalladas
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
                'description': 'Evolucion del aprendizaje de control por episodio',
            },
            'reward_components_avg': {
                'r_solar': float(np.mean(detailed_callback.episode_r_solar)) if detailed_callback.episode_r_solar else 0.0,
                'r_cost': float(np.mean(detailed_callback.episode_r_cost)) if detailed_callback.episode_r_cost else 0.0,
                'r_ev': float(np.mean(detailed_callback.episode_r_ev)) if detailed_callback.episode_r_ev else 0.0,
                'r_grid': float(np.mean(detailed_callback.episode_r_grid)) if detailed_callback.episode_r_grid else 0.0,
                'r_co2': float(np.mean(detailed_callback.episode_r_co2)) if detailed_callback.episode_r_co2 else 0.0,
                'episode_r_solar': [float(x) for x in detailed_callback.episode_r_solar] if detailed_callback.episode_r_solar else [],
                'episode_r_cost': [float(x) for x in detailed_callback.episode_r_cost] if detailed_callback.episode_r_cost else [],
                'episode_r_ev': [float(x) for x in detailed_callback.episode_r_ev] if detailed_callback.episode_r_ev else [],
                'episode_r_grid': [float(x) for x in detailed_callback.episode_r_grid] if detailed_callback.episode_r_grid else [],
                'episode_r_co2': [float(x) for x in detailed_callback.episode_r_co2] if detailed_callback.episode_r_co2 else [],
                'description': 'Componentes de reward promedio por episodio',
            },
            'vehicle_charging': {
                'motos_target': 270,
                'mototaxis_target': 39,
                'vehicles_target_daily': 309,
                'motos_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_motos_charged] if detailed_callback.episode_motos_charged else [],
                'mototaxis_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_mototaxis_charged] if detailed_callback.episode_mototaxis_charged else [],
                'description': 'Conteo real de vehiculos cargados usando energia dataset (270 motos + 39 mototaxis = 309/día)',
            },
            'model_path': str(CHECKPOINT_DIR / 'a2c_final_model.zip'),
        }

        # Custom JSON encoder para numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):  # type: ignore[no-untyped-def]
                if isinstance(obj, (np.floating, np.integer)):
                    return float(obj) if isinstance(obj, np.floating) else int(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        result_path = OUTPUT_DIR / 'result_a2c.json'
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_summary, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        print(f'  [OK] result_a2c.json: Resumen completo -> {result_path}')

        # Extraer metricas para impresion (acceso directo)
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
        print('  ➤ METRICAS DE RECOMPENSA:')
        print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
        print()
        print('  ➤ REDUCCION CO2 (kg):')
        total_indirect = float(sum(detailed_callback.episode_co2_avoided_indirect))
        total_direct = float(sum(detailed_callback.episode_co2_avoided_direct))
        print(f'    Reduccion INDIRECTA (solar)   {total_indirect:>12.1f} kg')
        print(f'    Reduccion DIRECTA (EVs)       {total_direct:>12.1f} kg')
        print(f'    Reduccion TOTAL               {total_indirect + total_direct:>12.1f} kg')
        print(f'    CO2 evitado promedio/ep       {mean_co2:>12.1f} kg')
        print()
        print('  ➤ VEHICULOS CARGADOS (maximo por episodio):')
        max_motos = max(detailed_callback.episode_motos_charged) if detailed_callback.episode_motos_charged else 0
        max_mototaxis = max(detailed_callback.episode_mototaxis_charged) if detailed_callback.episode_mototaxis_charged else 0
        print(f'    Motos (de 112)                {max_motos:>12d} unidades')
        print(f'    Mototaxis (de 16)             {max_mototaxis:>12d} unidades')
        print(f'    Total vehiculos               {max_motos + max_mototaxis:>12d} / 38')
        print()
        print('  ➤ ESTABILIDAD DE RED:')
        avg_stability = np.mean(detailed_callback.episode_grid_stability) if detailed_callback.episode_grid_stability else 0.0
        print(f'    Estabilidad promedio          {avg_stability*100:>12.1f} %')
        print(f'    Grid import promedio/ep       {mean_grid:>12.1f} kWh')
        print()
        print('  ➤ AHORRO ECONOMICO:')
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
        print(f'    Accion BESS promedio          {avg_bess_action:>12.3f} (0=carga, 1=descarga)')
        print()
        print('  ➤ PROGRESO DE CONTROL SOCKETS:')
        avg_setpoint = np.mean(detailed_callback.episode_avg_socket_setpoint) if detailed_callback.episode_avg_socket_setpoint else 0.0
        avg_utilization = np.mean(detailed_callback.episode_socket_utilization) if detailed_callback.episode_socket_utilization else 0.0
        print(f'    Setpoint promedio sockets     {avg_setpoint:>12.3f} [0-1]')
        print(f'    Utilizacion sockets           {avg_utilization*100:>12.1f} %')
        print()
        print('  ➤ SOLAR:')
        print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
        print()
        print('  ARCHIVOS GENERADOS:')
        print(f'    [OK] {OUTPUT_DIR}/result_a2c.json')
        print(f'    [OK] {OUTPUT_DIR}/timeseries_a2c.csv')
        print(f'    [OK] {OUTPUT_DIR}/trace_a2c.csv')
        print(f'    [OK] {CHECKPOINT_DIR}/a2c_final_model.zip')
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


if __name__ == '__main__':
    main()
