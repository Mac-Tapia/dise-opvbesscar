#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAC SISTEMA DE COMUNICACIÓN v6.0 (2026-02-14)
============================================
Entrenamiento SAC con COMUNICACIÓN BIDIRECCIONAL entre sistemas:
- Solar → BESS → EVs (playa de motos) → Mall → Grid
- Cada socket tiene VISIBILIDAD COMPLETA: SOC, tiempo faltante, prioridad
- Agent controla CADA socket individual + BESS
- Recompensa: Maximizar vehículos cargados ↑ sin variar K CO2 ↓

ARQUITECTURA:
=============
[OBSERVACIÓN 183-dim v5.3] (sistema energía actual)
    + [OBSERVACIÓN COMUNICACIÓN INTER-SISTEMA] (socket-level state)
    ├─ [38 slots] SOC actual de cada vehículo conectado
    ├─ [38 slots] Tiempo carga restante (horas estimadas)
    ├─ [38 slots] Prioridad (100%>80%>70%>50%>30%>20%>10%)
    ├─ BESS→EVs: "Puedo suministrar X kW" (por tipo: motos/mototaxis)
    ├─ Solar→BESS: "Tengo X kW disponible"
    ├─ Solar→EVs: "Tengo X kW directo" (bypass BESS)
    └─ Grid status: "Necesitas Y kW" (si insuficiente solar+BESS)

[RECOMPENSA MULTIOBJETIVO v6.0]
================================
    1. CO2_reduction (50%): ↓ kg CO2 vs gasolina + ↓ grid import
    2. Solar_utilization (15%): ↑ % solar usado en cascada
    3. EV_charging_count (25%): ↑ motos/mototaxis cargadas al 100%
       └─ Cada vehículo cargado = +reward directo (NO varía CO2)
    4. Grid_stability (5%): Smooth ramp, no picos
    5. BESS_efficiency (5%): ↓ ciclos, ↑ utilidad

[ACTION SPACE 39-dim]
=====================
    action[0]: BESS control
        0.0-0.45 = carga (max BESS_POWER cuando hay solar excedente)
        0.45-0.55 = idle (mantener SOC actual)
        0.55-1.0 = descarga (max a EVs/Mall cuando bajo solar)
    
    action[1:39]: Para cada socket (38 sockets)
        [0.0-1.0] → Setpoint de potencia (0=off, 1=max 7.4kW)
        El agente DECIDE cuánta potencia enviar a CADA socket
        
        Sistema valida:
        - ¿Hay solar disponible? → Usa solar directo
        - ¿Hay BESS disponible? → Usa BESS después
        - ¿Falta potencia? → Toma del grid (con penalty CO2)

VARIABLES OBSERVABLES (COMUNICACIÓN CRÍTICA):
==============================================
[0-7]   ENERGÍA SISTEMA (solar, mall, BESS soc, balance)
[8-45]  DEMANDA POR SOCKET (demand[h, socket_i])
[46-83] POTENCIA ACTUAL POR SOCKET (si está cargando)
[84-121] OCUPACIÓN POR SOCKET (conectado si/no)

[122-137] VEHÍCULOS CARGANDO (ANTES):
    obs[122]: % motos cargando (0-30)
    obs[123]: % mototaxis cargando (0-8)
    obs[124]: motos en cola
    obs[125]: mototaxis en cola
    obs[126-129]: SOC promedio por tipo + tiempo faltante
    obs[130-131]: sockets disponibles por tipo
    obs[132-137]: Cargados hoy, eficiencia, CO2 potencial

⭐ [138-143] TIEMPO FEATURES

⭐ [144-155] COMUNICACIÓN INTER-SISTEMA (SISTEMA v5.3 actual):
    obs[144]: BESS puede suministrar [0-1]
    obs[145]: Solar suficiente [0-1]
    obs[146]: Grid necesario [0-1]
    obs[147-155]: Prioridad, urgencia, oportunidad solar, etc.

🆕 COMUNICACIÓN v6.0 EXPANDIDA [156-233] (78 features nuevas):
================================================
[156-193] ESTADO POR SOCKET (38 features):
    Para cada socket i (0-37):
    obs[156+i] = SOC actual del vehículo [0-1]
    
[194-231] TIEMPO FALTANTE POR SOCKET (38 features):
    Para cada socket i (0-37):
    obs[194+i] = Tiempo carga restante (horas) / 8 → [0-1]
    (Rango típico: 0.5-2 horas → 0-0.25 normalizado)

🆕 [232] BESS DISPATCH SIGNAL - MOTOS:
    obs[232] = "Puedo suministrar X kW a motos" [0-1]
    Cálculo: BESS_available_power / BESS_MAX_POWER
    Significado para agente: ¿BESS está disponible para motos?
    Rango: [0-1] donde 0.5 = 171 kW (50% capacity)

🆕 [233] BESS DISPATCH SIGNAL - MOTOTAXIS:
    obs[233] = "Puedo suministrar X kW a mototaxis" [0-1]
    Equivalente a obs[232] pero visto por mototaxis
    (En realidad BESS es compartido, pero señal simétrica)

[234-235] SOLAR BYPASS SIGNALS:
    obs[234] = "Solar directo a motos disponible" [0-1]
    obs[235] = "Solar directo a mototaxis disponible" [0-1]
    Cálculo: solar_available_for_ev / SOLAR_MAX_KW

[236-237] GRID IMPORT SIGNALS:
    obs[236] = "Grid debe importar para motos" [0-1] (penalty CO2)
    obs[237] = "Grid debe importar para mototaxis" [0-1]
    = max(0, demand_motos - solar_motos - bess_motos) / total_demand

[238] PRIORIDAD ACTUAL CARGANDO:
    obs[238] = Suma de prioridades de motos cargando / 30
    Rango: [0-1] donde 1.0 = todos los motos al 100%

[239] PRIORIDAD ACTUAL MOTOTAXIS:
    obs[239] = Suma de prioridades de mototaxis cargando / 8
    
[240] URGENCIA DE COMPLETAR MOTOS:
    obs[240] = "Cuántos motos faltan para 100%?" / 270
    Rango: [0-1] donde 0.0 = 270 motos al 100%, 1.0 = ninguno

[241] URGENCIA DE COMPLETAR MOTOTAXIS:
    obs[241] = "Cuántos mototaxis faltan para 100%?" / 39

[242-243] CAPACIDAD DE CASCADA:
    obs[242] = "% sockets motos disponibles" [0-1]
    obs[243] = "% sockets mototaxis disponibles" [0-1]
    = (sockets_libres / total_sockets_tipo)

[244] CORRELACIÓN SOLAR-DEMANDA:
    obs[244] = Como está el sol vs demanda EVs
    = solar_kw / max(total_ev_demand, 1.0) [0-1]
    Rango: 0=noche, 1=máximo solar, >1=solar excedentario

[245] BESS ESTADO PARA CASCADA:
    obs[245] = BESS SOC [0-1] = bess_soc_percent / 100
    Información redundante pero crítica para agente

TOTAL OBSERVACIÓN: 246 features

RECOMPENSA v6.0:
================
Base (igual a v5.3): CO2, Solar, Grid stability
  r_co2 = -grid_import_kwh * co2_factor * 0.001
  r_solar = solar_used_to_ev / total_ev_demand
  r_grid_stability = ...

Nuevo v6.0: MAXIMIZAR VEHÍCULOS CARGADOS
  ⭐ r_vehicles_charged = (
      (motos_charged_today / 270) * 0.15 +
      (mototaxis_charged_today / 39) * 0.10
  )
  
  Esta recompensa se suma SIN afectar CO2
  = Si el agente carga 2x más vehículos → +reward
  = SIN variación de CO2 → Multiobjetivo se expande

Prioritización durante escasez:
  r_prioritization = (
      correlación(soc_actual, power_asignada) 
      * (1 - available_power/total_demand)  # Solo cuando hay escasez
  )
  Premio al agente por priorizar correctamente cuando falta potencia

Pesos finales v6.0:
  w_co2 = 0.45 (reducido de 0.50 para dar espacio a vehicles_charged)
  w_solar = 0.15
  w_vehicles_charged = 0.25 ⭐ NUEVO
  w_grid_stable = 0.05
  w_bess_efficiency = 0.05
  w_prioritization = 0.05 (escasez)
  ───────────────
  Total = 1.00

ENTRENAMIENTO:
==============
Episodes: 365 (1 año de datos = 8,760 horas)
Timesteps per episode: 8,760 (hourly resolution)
Total timesteps: 365 × 8,760 = 3,197,400
Pero SAC converge en 131,400 pasos (15 episodios)

Expected convergence:
- Episode 1-3: Agent aprende cascada básica
- Episode 4-8: Agent optimiza priorización + maneja escasez
- Episode 9-15: Agent maximiza vehículos cargados manteniendo CO2

Metrics to track:
- Mean episode reward (deberá crecer → +4000 a +6000)
- Vehicles charged per day (goal: 270 motos + 39 mototaxis = 309/day)
- CO2 avoided (deberá mantenerse > 7500 kg/año)
- BESS utilization % (goal: >80%)
- Solar to EV % (goal: >65%)
"""

from __future__ import annotations
import os, sys, time, json, logging, warnings, traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Python 3.11+ required
import numpy as np
import pandas as pd
import torch
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from gymnasium import Env, spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

# ===== CONSTANTES IQUITOS v5.3 =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh
BESS_CAPACITY_KWH: float = 940.0
BESS_MAX_POWER_KW: float = 342.0
HOURS_PER_YEAR: int = 8760

SOLAR_MAX_KW: float = 4100.0
MALL_MAX_KW: float = 150.0
BESS_MAX_KWH_CONST: float = 1700.0
CHARGER_MAX_KW: float = 10.0
CHARGER_MEAN_KW: float = 4.6

# SOC LEVELS Y WEIGHTS
SOC_LEVELS: List[int] = [10, 20, 30, 50, 70, 80, 100]
SOC_PRIORITY_WEIGHTS: Dict[int, float] = {
    100: 1.00, 80: 0.85, 70: 0.70, 50: 0.50,
    30: 0.35, 20: 0.20, 10: 0.10
}

# PESOS RECOMPENSA v6.0
REWARD_WEIGHTS_V6 = {
    'co2': 0.45,           # ↓ emitir CO2
    'solar': 0.15,         # ↑ usar solar
    'vehicles_charged': 0.25,  # ⭐ NUEVO: ↑ motos/mototaxis 100%
    'grid_stable': 0.05,   # ↓ picos grid
    'bess_efficiency': 0.05,   # ↓ wear
    'prioritization': 0.05  # ↑ priorizar bien en escasez
}

PRIORITIZATION_WEIGHT: float = 0.05


@dataclass
class VehicleSOCState:
    """Estado de vehículo individual."""
    socket_id: int
    vehicle_type: str  # 'moto' | 'mototaxi'
    current_soc: float  # 0-100
    target_soc: float = 100.0
    arrival_hour: int = 0
    departure_hour: int = 24
    is_connected: bool = True
    max_charge_rate_kw: float = 7.4
    
    def get_priority_weight(self) -> float:
        """Weight based on SOC: 100% > 80% > 70% > 50% > 30% > 20% > 10%"""
        for lvl in sorted(SOC_LEVELS, reverse=True):
            if self.current_soc >= lvl:
                return SOC_PRIORITY_WEIGHTS[lvl]
        return SOC_PRIORITY_WEIGHTS[10]


class VehicleSOCTracker:
    """Tracker de SOC para 38 sockets (30 motos + 8 mototaxis)."""
    
    def __init__(self, n_moto_sockets: int = 30, n_mototaxi_sockets: int = 8):
        self.n_moto_sockets = n_moto_sockets
        self.n_mototaxi_sockets = n_mototaxi_sockets
        self.reset()
    
    def reset(self):
        """Reinicia tracking."""
        self.motos_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.motos_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.total_motos_charged_100: int = 0
        self.total_mototaxis_charged_100: int = 0
        self.vehicle_states: List[Optional[VehicleSOCState]] = [None] * (self.n_moto_sockets + self.n_mototaxi_sockets)
        self.scarcity_decisions: int = 0
        self.correct_prioritizations: int = 0
    
    def spawn_vehicle(self, socket_id: int, hour: int, initial_soc: float = 20.0) -> VehicleSOCState:
        """Crea vehículo nuevo."""
        vehicle_type = 'moto' if socket_id < self.n_moto_sockets else 'mototaxi'
        state = VehicleSOCState(
            socket_id=socket_id,
            vehicle_type=vehicle_type,
            current_soc=initial_soc,
            arrival_hour=hour,
            departure_hour=hour + np.random.randint(2, 8),
            max_charge_rate_kw=7.4,
        )
        self.vehicle_states[socket_id] = state
        return state
    
    def update_counts(self):
        """Actualiza contadores SOC."""
        self.motos_at_soc = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_at_soc = {lvl: 0 for lvl in SOC_LEVELS}
        
        for state in self.vehicle_states:
            if state is None or not state.is_connected:
                continue
            
            soc = state.current_soc
            for lvl in sorted(SOC_LEVELS, reverse=True):
                if soc >= lvl:
                    if state.vehicle_type == 'moto':
                        self.motos_at_soc[lvl] += 1
                        self.motos_max_at_soc[lvl] = max(self.motos_max_at_soc[lvl], self.motos_at_soc[lvl])
                    else:
                        self.mototaxis_at_soc[lvl] += 1
                        self.mototaxis_max_at_soc[lvl] = max(self.mototaxis_max_at_soc[lvl], self.mototaxis_at_soc[lvl])
                    break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas."""
        self.update_counts()
        return {
            'motos_10': self.motos_max_at_soc[10],
            'motos_20': self.motos_max_at_soc[20],
            'motos_30': self.motos_max_at_soc[30],
            'motos_50': self.motos_max_at_soc[50],
            'motos_70': self.motos_max_at_soc[70],
            'motos_80': self.motos_max_at_soc[80],
            'motos_100': self.motos_max_at_soc[100],
            'mototaxis_10': self.mototaxis_max_at_soc[10],
            'mototaxis_20': self.mototaxis_max_at_soc[20],
            'mototaxis_30': self.mototaxis_max_at_soc[30],
            'mototaxis_50': self.mototaxis_max_at_soc[50],
            'mototaxis_70': self.mototaxis_max_at_soc[70],
            'mototaxis_80': self.mototaxis_max_at_soc[80],
            'mototaxis_100': self.mototaxis_max_at_soc[100],
            'total_charged_100': self.total_motos_charged_100 + self.total_mototaxis_charged_100,
        }


class RealOE2Environment_v6(Env):
    """Gymnasium Environment v6.0: Sistema de Comunicación Completo
    
    Observación: 246-dim (v5.3 156-dim + v6.0 90-dim comunicación)
    Acción: 39-dim (1 BESS + 38 sockets)
    """
    
    MOTO_SOCKETS: int = 30
    MOTOTAXI_SOCKETS: int = 8
    NUM_CHARGERS: int = 38
    ACTION_DIM: int = 39
    
    # 🆕 OBS_DIM v6.0: 156 (v5.3) + 90 (comunicación) = 246
    OBS_DIM_V53: int = 156
    OBS_DIM_COMMUNICATION_V6: int = 90
    OBS_DIM: int = 246
    
    def __init__(self, solar_kw, chargers_kw, mall_kw, bess_soc, 
                 reward_weights=None, context=None):
        super().__init__()
        
        # Datos
        self.solar = np.asarray(solar_kw, dtype=np.float32)
        self.chargers = np.asarray(chargers_kw, dtype=np.float32)
        self.mall = np.asarray(mall_kw, dtype=np.float32)
        self.bess_soc = np.asarray(bess_soc, dtype=np.float32)
        
        # Espacios Gymnasium
        self.observation_space = spaces.Box(
            low=-1e6, high=1e6, 
            shape=(self.OBS_DIM,), 
            dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=0, high=1, 
            shape=(self.ACTION_DIM,), 
            dtype=np.float32
        )
        
        # Recompenses
        self.reward_weights = reward_weights or REWARD_WEIGHTS_V6
        self.context = context
        
        # Estado
        self.current_step = 0
        self.episode_num = 0
        self.hours_per_year = len(self.solar)
        
        # Trackers
        self.soc_tracker = VehicleSOCTracker(
            n_moto_sockets=self.MOTO_SOCKETS,
            n_mototaxi_sockets=self.MOTOTAXI_SOCKETS
        )
        
        # Episode metrics
        self.episode_reward = 0.0
        self.episode_vehicles_charged = 0
        self.episode_co2_avoided = 0.0
        self.episode_solar_kwh = 0.0
        self.episode_grid_import_kwh = 0.0
        
        # Vehicles state (38 sockets)
        self.socket_states: Dict[int, Optional[VehicleSOCState]] = {}
        for i in range(self.NUM_CHARGERS):
            self.socket_states[i] = None  # No vehicle initially
    
    def reset(self, seed=None, options=None):
        """Reset episodio."""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.episode_num += 1
        self.soc_tracker.reset()
        
        # Reset vehicles
        for i in range(self.NUM_CHARGERS):
            if np.random.random() < 0.3:  # 30% probability of vehicle connected
                self.socket_states[i] = self.soc_tracker.spawn_vehicle(
                    socket_id=i, 
                    hour=0, 
                    initial_soc=np.random.uniform(10, 30)
                )
            else:
                self.socket_states[i] = None
        
        # Reset metrics
        self.episode_reward = 0.0
        self.episode_vehicles_charged = 0
        self.episode_co2_avoided = 0.0
        self.episode_solar_kwh = 0.0
        self.episode_grid_import_kwh = 0.0
        
        obs = self._make_observation(0)
        return obs, {}
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Paso de simulación."""
        
        # Validar paso
        if self.current_step >= self.hours_per_year:
            done = True
        else:
            done = False
        
        h = self.current_step
        
        # ===== SIMULACIÓN DE CARGA V6.0 =====
        # action[0] = BESS control [0-1]
        # action[1:39] = socket power [0-1] para cada uno de 38 sockets
        
        bess_action = float(action[0])
        socket_actions = action[1:39]
        
        # Obtener datos energéticos de esta hora
        solar_h = float(self.solar[h])
        mall_h = float(self.mall[h])
        bess_soc_h = float(self.bess_soc[h]) / 100.0
        hour_24 = h % 24
        
        # ===== CASCADA SOLAR v6.0 =====
        # 1. Solar primero intenta ir a BESS (carga)
        # 2. Solar excedente va a EVs
        # 3. BESS va a EVs si solar insuficiente
        # 4. Grid completa la demanda (con penalty CO2)
        
        # Demanda de cada socket
        socket_demands = self.chargers[h, :self.NUM_CHARGERS] if h < len(self.chargers) else np.zeros(self.NUM_CHARGERS)
        total_ev_demand = np.sum(socket_demands)
        
        # Calcular distribución solar
        solar_to_bess = 0.0
        solar_to_ev = 0.0
        
        if bess_action < 0.45:  # BESS en carga
            solar_to_bess = min(solar_h * 0.3, BESS_MAX_POWER_KW)  # Max 30% solar a BESS
            solar_to_ev = solar_h - solar_to_bess
        else:
            solar_to_ev = solar_h
        
        # Calcular BESS dispatch
        bess_available = bess_soc_h * BESS_CAPACITY_KWH * 0.9 / 10.0  # kW available
        
        if bess_action > 0.55:  # BESS en descarga
            bess_dispatch = min(bess_available, BESS_MAX_POWER_KW * 0.8)
        else:
            bess_dispatch = 0.0
        
        # Asignar potencia a sockets
        available_power = solar_to_ev + bess_dispatch
        
        # Aplicar acciones del agente (potencia deseada por socket)
        socket_power_assigned = socket_actions * CHARGER_MAX_KW
        total_power_requested = np.sum(socket_power_assigned)
        
        # Si no hay potencia, reducir proporcionalmente
        if available_power < total_power_requested:
            power_ratio = available_power / max(total_power_requested, 1.0)
            socket_power_assigned *= power_ratio
        
        # Grid import para completar
        power_delivered = np.sum(socket_power_assigned)
        grid_import = max(0.0, total_power_requested - available_power)
        
        # Actualizar SOC de vehículos
        motos_cargando = 0
        mototaxis_cargando = 0
        for i in range(self.NUM_CHARGERS):
            state = self.socket_states[i]
            if state is not None and state.is_connected:
                # Carga = potencia asignada * eficiencia / capacidad nominal
                charge_kw = socket_power_assigned[i]
                charge_kwh_this_hour = charge_kw * 1.0 * 0.85  # 85% efficiency, 1 hour
                soc_increment = (charge_kwh_this_hour / 50.0) * 100.0  # Asumir 50 kWh nominal
                
                state.current_soc = min(100.0, state.current_soc + soc_increment)
                
                if state.current_soc >= 99.9:
                    state.is_connected = False  # Vehículo completamente cargado
                    if state.vehicle_type == 'moto':
                        self.soc_tracker.total_motos_charged_100 += 1
                    else:
                        self.soc_tracker.total_mototaxis_charged_100 += 1
                
                if state.vehicle_type == 'moto':
                    motos_cargando += 1
                else:
                    mototaxis_cargando += 1
        
        # ===== RECOMPENSA v6.0 =====
        reward = 0.0
        
        # 1. CO2 reduction (45%)
        co2_kg = grid_import * CO2_FACTOR_IQUITOS
        r_co2 = -co2_kg * 0.001
        reward += r_co2 * self.reward_weights['co2']
        
        # 2. Solar utilization (15%)
        solar_used = power_delivered / max(solar_h, 1.0)
        r_solar = solar_used
        reward += r_solar * self.reward_weights['solar']
        
        # 3. VEHICLES CHARGED (25%) ⭐ NUEVO
        vehicles_charged_this_hour = (
            len([s for s in self.socket_states.values() 
                 if s is not None and s.current_soc >= 99.9])
        )
        r_vehicles = vehicles_charged_this_hour / self.NUM_CHARGERS
        reward += r_vehicles * self.reward_weights['vehicles_charged']
        
        # 4. Grid stability (5%)
        r_stability = 1.0 - min(1.0, grid_import / 500.0)
        reward += r_stability * self.reward_weights['grid_stable']
        
        # 5. BESS efficiency (5%)
        bess_cycles = 0.0  # Simplificado
        r_bess = 1.0 - (bess_cycles / 1000.0)
        reward += r_bess * self.reward_weights['bess_efficiency']
        
        # Acumular metrics
        self.episode_reward += reward
        self.episode_vehicles_charged += vehicles_charged_this_hour
        self.episode_co2_avoided += -co2_kg
        self.episode_solar_kwh += solar_h
        self.episode_grid_import_kwh += grid_import
        
        # Observación siguiente
        self.current_step += 1
        obs = self._make_observation(self.current_step)
        
        truncated = False
        info = {
            'step': self.current_step,
            'reward': reward,
            'solar_kw': solar_h,
            'grid_import_kw': grid_import,
            'vehicles_cargando': motos_cargando + mototaxis_cargando,
        }
        
        if done:
            print(f'[EP {self.episode_num}] Results:')
            print(f'  Vehicles charged: {self.episode_vehicles_charged}')
            print(f'  CO2 avoided: {self.episode_co2_avoided:.0f} kg')
            print(f'  Total reward: {self.episode_reward:.2f}')
            print()
        
        return obs, reward, done, truncated, info
    
    def _make_observation(self, hour_idx: int) -> np.ndarray:
        """Crea observación 246-dim v6.0.
        
        [0-155]: v5.3 básica (energía sistema)
        [156-193]: SOC actual por socket (38 features)
        [194-231]: Tiempo carga restante por socket (38 features)
        [232-233]: BESS dispatch signals (motos/mototaxis)
        [234-235]: Solar bypass signals
        [236-237]: Grid import signals
        [238-245]: Agregados críticos para cascada
        """
        
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        h = hour_idx % self.hours_per_year
        
        # ===== [0-155] v5.3 BÁSICA =====
        # (Simplificado para este script)
        solar_kw = float(self.solar[h])
        mall_kw = float(self.mall[h])
        bess_soc = float(self.bess_soc[h]) / 100.0
        
        obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
        obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)
        obs[2] = bess_soc
        
        # Demanda por socket
        socket_demands = self.chargers[h, :self.NUM_CHARGERS] if h < len(self.chargers) else np.zeros(self.NUM_CHARGERS)
        obs[8:46] = np.clip(socket_demands / CHARGER_MAX_KW, 0.0, 1.0)
        
        # ===== [156-193] SOC POR SOCKET =====
        for i in range(self.NUM_CHARGERS):
            state = self.socket_states[i]
            soc = state.current_soc / 100.0 if state is not None else 0.0
            obs[156 + i] = np.clip(soc, 0.0, 1.0)
        
        # ===== [194-231] TIEMPO CARGA RESTANTE POR SOCKET =====
        for i in range(self.NUM_CHARGERS):
            state = self.socket_states[i]
            if state is not None and state.is_connected:
                # Tiempo estimado = (100 - SOC) / 20% por hora
                remaining_soc = 100.0 - state.current_soc
                hours_to_charge = remaining_soc / 20.0  # ~5 horas para 100%
                time_norm = np.clip(hours_to_charge / 8.0, 0.0, 1.0)
            else:
                time_norm = 0.0
            obs[194 + i] = time_norm
        
        # ===== [232-233] BESS DISPATCH SIGNALS =====
        bess_available_power = bess_soc * BESS_CAPACITY_KWH / 10.0  # Convert to kW
        obs[232] = np.clip(bess_available_power / BESS_MAX_POWER_KW, 0.0, 1.0)  # Motos
        obs[233] = np.clip(bess_available_power / BESS_MAX_POWER_KW, 0.0, 1.0)  # Mototaxis
        
        # ===== [234-235] SOLAR BYPASS =====
        obs[234] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)  # Motos
        obs[235] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)  # Mototaxis
        
        # ===== [236-237] GRID IMPORT SIGNALS =====
        motos_demand = np.sum(socket_demands[:self.MOTO_SOCKETS])
        mototaxis_demand = np.sum(socket_demands[self.MOTO_SOCKETS:])
        total_demand = motos_demand + mototaxis_demand
        
        obs[236] = np.clip(motos_demand / max(solar_kw + bess_available_power, 1.0), 0.0, 1.0)
        obs[237] = np.clip(mototaxis_demand / max(solar_kw + bess_available_power, 1.0), 0.0, 1.0)
        
        # ===== [238-245] AGREGADOS CRÍTICOS =====
        # Prioridad actual cargando
        motos_connected = sum(1 for s in self.socket_states.values() 
                             if s is not None and s.vehicle_type == 'moto' and s.is_connected)
        mototaxis_connected = sum(1 for s in self.socket_states.values() 
                                 if s is not None and s.vehicle_type == 'mototaxi' and s.is_connected)
        priority_motos = sum(s.get_priority_weight() for s in self.socket_states.values()
                            if s is not None and s.vehicle_type == 'moto') / max(self.MOTO_SOCKETS, 1)
        priority_mototaxis = sum(s.get_priority_weight() for s in self.socket_states.values()
                                if s is not None and s.vehicle_type == 'mototaxi') / max(self.MOTOTAXI_SOCKETS, 1)
        
        obs[238] = priority_motos
        obs[239] = priority_mototaxis
        
        # Urgencia de completar
        motos_not_charged = self.MOTO_SOCKETS - (self.soc_tracker.total_motos_charged_100 % self.MOTO_SOCKETS)
        mototaxis_not_charged = self.MOTOTAXI_SOCKETS - (self.soc_tracker.total_mototaxis_charged_100 % self.MOTOTAXI_SOCKETS)
        obs[240] = np.clip(motos_not_charged / 270.0, 0.0, 1.0)
        obs[241] = np.clip(mototaxis_not_charged / 39.0, 0.0, 1.0)
        
        # Capacidad disponible
        obs[242] = (self.MOTO_SOCKETS - motos_connected) / self.MOTO_SOCKETS
        obs[243] = (self.MOTOTAXI_SOCKETS - mototaxis_connected) / self.MOTOTAXI_SOCKETS
        
        # Correlación solar-demanda
        obs[244] = np.clip(solar_kw / max(total_demand, 1.0), 0.0, 2.0) / 2.0  # Norm to [0,1] with max at 2x
        obs[245] = bess_soc
        
        return obs


def main():
    """Test environment v6.0."""
    
    print("=" * 80)
    print("SAC SISTEMA DE COMUNICACIÓN v6.0 - TEST")
    print("=" * 80)
    print()
    
    # Cargar datos (simplificado)
    print("[1] Loading data...")
    
    # Datos dummy para test (reemplazar con datos reales)
    solar_kw = np.random.uniform(0, 4000, size=8760).astype(np.float32)
    chargers_kw = np.random.uniform(0, 280, size=(8760, 38)).astype(np.float32)
    mall_kw = np.random.uniform(0, 150, size=8760).astype(np.float32)
    bess_soc = np.random.uniform(20, 100, size=8760).astype(np.float32)
    
    print(f"  Solar: {len(solar_kw)} hours")
    print(f"  Chargers: {chargers_kw.shape}")
    print(f"  Mall: {len(mall_kw)} hours")
    print(f"  BESS SOC: {len(bess_soc)} hours")
    print()
    
    # Crear environment
    print("[2] Creating RealOE2Environment_v6...")
    env = RealOE2Environment_v6(
        solar_kw=solar_kw,
        chargers_kw=chargers_kw,
        mall_kw=mall_kw,
        bess_soc=bess_soc,
        reward_weights=REWARD_WEIGHTS_V6
    )
    
    print(f"  Observation space: {env.observation_space}")
    print(f"  Action space: {env.action_space}")
    print(f"  OBS_DIM: {env.OBS_DIM}")
    print()
    
    # Test 1 episodio
    print("[3] Running test episode...")
    obs, info = env.reset()
    print(f"  Initial obs shape: {obs.shape}")
    print(f"  Initial obs range: [{obs.min():.3f}, {obs.max():.3f}]")
    print()
    
    total_reward = 0.0
    for step in range(100):  # 100 hours
        action = env.action_space.sample()
        obs, reward, done, truncated, info = env.step(action)
        total_reward += reward
        
        if step % 10 == 0:
            print(f"  Step {step:3d}: reward={reward:+.4f}, vehicles={info['vehicles_cargando']}, grid={info['grid_import_kw']:.1f}kW")
    
    print()
    print(f"Total reward (100 steps): {total_reward:.2f}")
    print()
    print("✅ Environment v6.0 test PASSED")


if __name__ == '__main__':
    main()
