#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
SAC (Soft Actor-Critic): Off-policy, mas eficiente en muestras, ideal para problemas asimetricos
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
import traceback
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ===== AGREGAR WORKSPACE AL PATH =====
workspace_root = Path(__file__).parent.parent.parent  # scripts/train/... -> workspace root
sys.path.insert(0, str(workspace_root))

import numpy as np
import pandas as pd
import torch
import yaml
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para servidores/scripts
import matplotlib.pyplot as plt
from gymnasium import Env, spaces
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

# CityLearn v2 environment (opcional - usamos Gymnasium Env como base)
try:
    from citylearn import CityLearnEnv  # type: ignore
    CITYLEARN_AVAILABLE = True
except (ImportError, AttributeError, ModuleNotFoundError):
    CITYLEARN_AVAILABLE = False
    # No warning - Gymnasium Env fallback es el diseno robusto por defecto

from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

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

# ===== VEHICLE CHARGING SCENARIOS - DEFINIDOS LOCALMENTE (ROBUSTO) =====
# No dependemos de modulo externo - todo auto-contenido aqui
VEHICLE_SCENARIOS_AVAILABLE = True  # Siempre disponible porque esta definido aqui

# ===== CONSTANTES IQUITOS v5.8 (2026-02-18) CON COMUNICACION SISTEMA =====
# CRÍTICO: BESS_CAPACITY_KWH actualizado a 2000.0 kWh (verificado contra bess_ano_2024.csv max soc_kwh)
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid termico aislado)
# BESS_CAPACITY_KWH importado de data_loader (2,000 kWh verificado)
# BESS_MAX_POWER_KW importado de data_loader (400 kW)
HOURS_PER_YEAR: int = 8760

# v5.3: Constantes para normalizacion de observaciones (comunicacion sistema)
# SOLAR_MAX_KW: pico real de generacion solar observado en datos (2,887 kW)
SOLAR_MAX_KW: float = 2887.0        # Max real observado en solar timeseries
MALL_MAX_KW: float = 3000.0         # Real max=2,763 kW from data/oe2/demandamallkwh/demandamallhorakwh.csv [FIXED 2026-02-15]
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (referencia normalizacion) [VALIDATED]
CHARGER_MAX_KW: float = 3.7         # Max per socket: 7.4 kW charger / 2 sockets from src/dimensionamiento/oe2/disenocargadoresev/chargers.py [FIXED 2026-02-15]
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket (7.4 kW × 0.62 efficiency) [VALIDATED]

# ===== CONSTANTES DE VEHICULOS Y CO2 DIRECTO v7.2 (2026-02-17) =====
# DATOS REALES del dataset EV - NO APROXIMACIONES
MOTOS_TARGET_DIARIOS: float = 270     # Motos por día (Iquitos)
MOTOTAXIS_TARGET_DIARIOS: float = 39  # Mototaxis por día (Iquitos)
VEHICLES_TARGET_DIARIOS: float = MOTOS_TARGET_DIARIOS + MOTOTAXIS_TARGET_DIARIOS  # 309

MOTO_BATTERY_KWH: float = 4.6       # Capacidad bateria moto
MOTOTAXI_BATTERY_KWH: float = 7.4   # Capacidad bateria mototaxi
MOTO_SOC_ARRIVAL: float = 0.20      # SOC al llegar (20%)
MOTO_SOC_TARGET: float = 0.80       # SOC objetivo (80%)
MOTO_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTO_BATTERY_KWH / 0.95
MOTOTAXI_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTOTAXI_BATTERY_KWH / 0.95

CO2_FACTOR_MOTO_KG_KWH: float = 0.87      # kg CO2 por kWh (moto vs gasolina)
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.47  # kg CO2 por kWh (mototaxi vs gasolina)

# ===== SAC CONFIG =====
# (imports ya arriba: dataclass, field, Dict, List, Optional, Tuple)


# ===== CONSTANTES DE PRIORIZACION SOC =====
# Niveles de SOC a trackear (orden de prioridad: 100% > 80% > 70% > 50% > 30% > 20% > 10%)
SOC_LEVELS: List[int] = [10, 20, 30, 50, 70, 80, 100]
SOC_PRIORITY_WEIGHTS: Dict[int, float] = {
    100: 1.00,  # Maxima prioridad - vehiculo completamente cargado
    80: 0.85,   # Alta prioridad - casi listo
    70: 0.70,   # Media-alta
    50: 0.50,   # Media
    30: 0.35,   # Media-baja
    20: 0.20,   # Baja
    10: 0.10,   # Minima prioridad - apenas comenzo
}


@dataclass
class VehicleSOCState:
    """Estado de SOC de un vehiculo individual conectado a un socket."""
    socket_id: int
    vehicle_type: str  # 'moto' o 'mototaxi'
    current_soc: float  # 0-100%
    target_soc: float = 100.0  # SOC objetivo
    arrival_hour: int = 0  # Hora de llegada
    departure_hour: int = 24  # Hora limite de salida
    is_connected: bool = True
    max_charge_rate_kw: float = 7.4  # Mode 3 @ 32A 230V
    
    def get_priority_weight(self) -> float:
        """Retorna peso de prioridad basado en SOC actual.
        100% > 80% > 70% > 50% > 30% > 20% > 10%
        """
        for soc_level in sorted(SOC_LEVELS, reverse=True):
            if self.current_soc >= soc_level:
                return SOC_PRIORITY_WEIGHTS[soc_level]
        return 0.05  # Minimo absoluto
    
    def charge(self, power_kw: float, duration_h: float = 1.0) -> float:
        """Carga el vehiculo y retorna energia consumida."""
        if not self.is_connected:
            return 0.0
        # Capacidad bateria REAL OE2 v5.5 (chargers.py): moto=4.6kWh, mototaxi=7.4kWh
        battery_kwh = 4.6 if self.vehicle_type == 'moto' else 7.4
        energy_needed = (self.target_soc - self.current_soc) / 100.0 * battery_kwh
        energy_delivered = min(power_kw * duration_h, energy_needed, self.max_charge_rate_kw * duration_h)
        soc_increase = (energy_delivered / battery_kwh) * 100.0
        self.current_soc = min(100.0, self.current_soc + soc_increase)
        return energy_delivered


@dataclass
class ChargingScenario:
    """Escenario de carga con nivel de escasez de potencia."""
    name: str
    hour_start: int
    hour_end: int
    available_power_ratio: float  # 0.0 = sin potencia, 1.0 = potencia completa
    n_vehicles_moto: int  # Vehiculos esperando
    n_vehicles_mototaxi: int
    is_peak: bool = False
    
    def get_scarcity_level(self) -> str:
        """Nivel de escasez: EXTREME, HIGH, MEDIUM, LOW, NONE."""
        if self.available_power_ratio < 0.3:
            return 'EXTREME'
        elif self.available_power_ratio < 0.5:
            return 'HIGH'
        elif self.available_power_ratio < 0.7:
            return 'MEDIUM'
        elif self.available_power_ratio < 0.9:
            return 'LOW'
        return 'NONE'


# Escenarios de carga durante el dia (basados en demanda real Iquitos)
CHARGING_SCENARIOS: List[ChargingScenario] = [
    # Madrugada: baja demanda, potencia completa
    ChargingScenario('NIGHT_LOW', 0, 5, 1.0, 5, 1, False),
    # Manana temprano: demanda creciente
    ChargingScenario('MORNING_EARLY', 6, 8, 0.8, 15, 3, False),
    # Manana: alta demanda (mototaxis trabajo)
    ChargingScenario('MORNING_PEAK', 9, 11, 0.5, 25, 6, True),  # ESCASEZ MEDIA
    # Mediodia: pico solar, buena potencia
    ChargingScenario('MIDDAY_SOLAR', 12, 14, 0.9, 20, 5, False),
    # Tarde: escasez EXTREMA (pico mall + EVs)
    ChargingScenario('AFTERNOON_PEAK', 15, 17, 0.3, 30, 8, True),  # ESCASEZ EXTREME
    # Tarde-noche: escasez ALTA
    ChargingScenario('EVENING_PEAK', 18, 20, 0.4, 28, 7, True),  # ESCASEZ HIGH
    # Noche: demanda media
    ChargingScenario('NIGHT_MEDIUM', 21, 23, 0.7, 15, 4, False),
]


@dataclass
class VehicleSOCTracker:
    """Tracker de SOC para todos los vehiculos (motos y mototaxis).
    
    Trackea simultaneamente:
    - Motos al 10%, 20%, 30%, 50%, 70%, 80%, 100%
    - Mototaxis al 10%, 20%, 30%, 50%, 70%, 80%, 100%
    """
    n_moto_sockets: int = 30  # Sockets 0-29
    n_mototaxi_sockets: int = 8  # Sockets 30-37
    
    def __post_init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia tracking para nuevo episodio."""
        # Contadores por nivel SOC (acumulado episodio)
        self.motos_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        
        # Maximos alcanzados en episodio
        self.motos_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        
        # Contadores de vehiculos completamente cargados
        self.total_motos_charged_100: int = 0
        self.total_mototaxis_charged_100: int = 0
        
        # Estados actuales por socket
        self.vehicle_states: List[Optional[VehicleSOCState]] = [None] * (self.n_moto_sockets + self.n_mototaxi_sockets)
        
        # Metricas de priorizacion
        self.prioritization_score: float = 0.0
        self.scarcity_decisions: int = 0  # Numero de decisiones bajo escasez
        self.correct_prioritizations: int = 0  # Priorizaciones correctas
    
    def spawn_vehicle(self, socket_id: int, hour: int, initial_soc: float = 20.0) -> VehicleSOCState:
        """Crea un vehiculo nuevo en el socket dado."""
        vehicle_type = 'moto' if socket_id < self.n_moto_sockets else 'mototaxi'
        max_rate = 7.4  # AMBOS Modo 3 @ 32A 230V (chargers.py L├¡nea 197, 207)
        
        state = VehicleSOCState(
            socket_id=socket_id,
            vehicle_type=vehicle_type,
            current_soc=initial_soc,
            arrival_hour=hour,
            departure_hour=hour + np.random.randint(2, 8),  # 2-8 horas para cargar
            max_charge_rate_kw=max_rate,
        )
        self.vehicle_states[socket_id] = state
        return state
    
    def update_counts(self):
        """Actualiza contadores de vehiculos por nivel SOC."""
        # Reset contadores actuales
        self.motos_at_soc = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_at_soc = {lvl: 0 for lvl in SOC_LEVELS}
        
        for state in self.vehicle_states:
            if state is None or not state.is_connected:
                continue
            
            # Determinar nivel SOC alcanzado
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
    
    def get_prioritization_reward(self, actions: np.ndarray, available_power: float, total_demand: float) -> float:
        """Calcula reward por correcta priorizacion durante escasez.
        
        Premia cuando: 100% > 80% > 70% > 50% > 30% > 20% > 10%
        Es decir, vehiculos con mayor SOC deben recibir mas potencia primero.
        """
        if available_power >= total_demand * 0.9:  # Sin escasez significativa
            return 0.0
        
        self.scarcity_decisions += 1
        
        # Calcular correlacion entre prioridad de vehiculo y potencia asignada
        priorities = []
        power_allocated = []
        
        for i, state in enumerate(self.vehicle_states):
            if state is None or not state.is_connected:
                continue
            action_idx = i + 1  # +1 porque action[0] es BESS
            if action_idx < len(actions):
                priorities.append(state.get_priority_weight())
                power_allocated.append(float(actions[action_idx]))
        
        if len(priorities) < 2:
            return 0.0
        
        # Calcular correlacion Spearman (orden correcto de priorizacion)
        # Si la correlacion es alta, el agente esta priorizando correctamente
        priorities_arr = np.array(priorities)
        power_arr = np.array(power_allocated)
        
        # Normalizar
        priorities_norm = (priorities_arr - priorities_arr.mean()) / (priorities_arr.std() + 1e-8)
        power_norm = (power_arr - power_arr.mean()) / (power_arr.std() + 1e-8)
        
        correlation = np.mean(priorities_norm * power_norm)
        
        # Escalar reward: +1 si prioriza bien, -1 si prioriza mal
        scarcity_ratio = 1.0 - (available_power / max(total_demand, 1.0))
        reward = correlation * scarcity_ratio * 2.0  # Escalar por severidad de escasez
        
        if correlation > 0.3:
            self.correct_prioritizations += 1
        
        return reward
    
    def get_completion_reward(self) -> float:
        """Reward por completar cargas (100% SOC)."""
        # Pesos mayores para niveles altos de SOC
        reward = 0.0
        for lvl in SOC_LEVELS:
            n_motos = self.motos_at_soc.get(lvl, 0)
            n_mototaxis = self.mototaxis_at_soc.get(lvl, 0)
            weight = SOC_PRIORITY_WEIGHTS[lvl]
            reward += (n_motos + n_mototaxis * 1.5) * weight  # Mototaxis valen mas (servicio publico)
        return reward / 100.0  # Normalizar
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna metricas completas de tracking."""
        self.update_counts()
        
        accuracy = self.correct_prioritizations / max(1, self.scarcity_decisions)
        
        return {
            # Por nivel SOC - motos
            'motos_10': self.motos_max_at_soc[10],
            'motos_20': self.motos_max_at_soc[20],
            'motos_30': self.motos_max_at_soc[30],
            'motos_50': self.motos_max_at_soc[50],
            'motos_70': self.motos_max_at_soc[70],
            'motos_80': self.motos_max_at_soc[80],
            'motos_100': self.motos_max_at_soc[100],
            # Por nivel SOC - mototaxis
            'mototaxis_10': self.mototaxis_max_at_soc[10],
            'mototaxis_20': self.mototaxis_max_at_soc[20],
            'mototaxis_30': self.mototaxis_max_at_soc[30],
            'mototaxis_50': self.mototaxis_max_at_soc[50],
            'mototaxis_70': self.mototaxis_max_at_soc[70],
            'mototaxis_80': self.mototaxis_max_at_soc[80],
            'mototaxis_100': self.mototaxis_max_at_soc[100],
            # Totales
            'total_charged_100': self.total_motos_charged_100 + self.total_mototaxis_charged_100,
            'prioritization_accuracy': accuracy,
            'scarcity_decisions': self.scarcity_decisions,
        }


@dataclass
class SACConfig:
    """Configuracion SAC OPTIMA - Parametros segun mejores practicas.
    
    Hiperparametros SAC (Soft Actor-Critic):
    =========================================
    - Replay buffer size: 1e5ÔÇô1e6 (usamos 1e6 para GPU)
    - Warmup / random steps: 1e3ÔÇô1e4 (learning_starts)
    - Batch size: 128ÔÇô512 (usamos 256)
    - ¤ä (tau) soft update: 0.005 (tipico)
    - Update frequency: cada paso (train_freq)
    - Update-to-data ratio: 1-4 (gradient_steps)
    - alpha (alpha) / temperatura entropia: auto-tuning recomendado
    - Target entropy: -|A| (dimension acciones)
    - Learning rates: 3e-4 (actor/critic/alpha)
    - ╬│ (gamma): 0.99
    
    Metricas clave a monitorear:
    - Eval episodic return (sin ruido)
    - Actor loss, Critic Q1/Q2 loss
    - Mean Q-value (si se dispara -> sobreestimacion)
    - Entropy y alpha (si alpha -> 0 rapido -> muy deterministico)
    - Replay buffer fill %
    - Mean/Std de acciones y log_std
    
    Senales de problema:
    - Q-values creciendo sin control -> reward muy grande / falta normalizacion
    - Entropia cae a 0 pronto -> target_entropy/alpha mal / reward shaping agresivo
    """
    
    # ===== LEARNING RATES (OPTIMIZADO PARA SAC x GPU) =====
    # SAC es sensible a LR - tipico 3e-4, REDUCIDO en v7.2 para estabilidad
    learning_rate: float = 3e-4  # REDUCIDO v7.2: evita Q-value explosion (era 5e-4)
    # Nota: SB3 SAC usa mismo LR para actor/critic/alpha por defecto
    
    # ===== REPLAY BUFFER (OPTIMIZADO RTX 4060: 400K - v7.2 STABILITY) =====
    # RTX 4060: 8GB VRAM - 400K buffer = ~320MB, deja espacio para networks + stability
    buffer_size: int = 400_000  # v7.2: 400K para GPU
    learning_starts: int = 10_000  # AUMENTADO v7.2: 10K warmup (was 5K) - mayor exploracion aleatoria
    
    # ===== BATCH Y UPDATES (OPTIMO PARA GPU) =====
    batch_size: int = 128  # REDUCIDO v7.2: 128 permite train_freq=2
    train_freq: Tuple[int, str] = (2, 'step')  # v7.2: Entrenar cada 2 steps
    gradient_steps: int = 2  # REDUCIDO v7.2: 2 updates (was 4) - menos aggressive para evitar explosi├│n
    
    # ===== SOFT UPDATE (¤ä = 0.005 TIPICO) =====
    tau: float = 0.005  # Soft update coefficient para target networks
    target_update_interval: int = 1  # Update target cada N gradient steps
    
    # ===== DISCOUNT (╬│ = 0.99 TIPICO) =====
    gamma: float = 0.99  # Discount factor
    
    # ===== ENTROPY (AUTO-TUNING - ESTANDAR SAC) =====
    # CAMBIO v3.0: Usamos 'auto' con auto-tune de alpha
    # Permitir que SAC ajuste alpha automaticamente segun entropy target
    # Nota: Evita colapso de exploracion cuando rewards estan normalizados
    ent_coef: str = 'auto'  # AUTO-TUNE (mejor con rewards normalizados)
    target_entropy: float = -50.0  # AUMENTADO v7.2: -50 (was -39) m├ís exploracion para evitar Q-value collapse
    
    # ===== EXPLORACION SDE (v7.2 - EVITAR ALPHA COLLAPSE) =====
    # SDE (State-Dependent Exploration) mejora exploracion en espacios continuos
    # Previene que el agente colapse a acciones deterministicas
    use_sde: bool = False  # Default: False (GPU config lo activa)
    sde_sample_freq: int = -1  # Frecuencia de resample (-1 = cada step)
    
    # ===== NETWORK ARCHITECTURE =====
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[512, 512], qf=[512, 512]),  # Actor/Critic 512x512
        'activation_fn': torch.nn.ReLU,
        'log_std_init': -3.0,  # Inicializacion log_std para exploracion
    })
    
    @staticmethod
    def adaptive_lr_schedule(initial_lr: float = 3e-4, 
                              min_lr: float = 5e-5,
                              warmup_fraction: float = 0.05) -> Callable[[float], float]:
        """Learning Rate Schedule ADAPTATIVO para SAC.
        
        Fases:
        1. WARMUP (0-5%): LR sube de min_lr a initial_lr (exploracion segura)
        2. DECAY (5-100%): LR decrece con cosine annealing hasta min_lr
        
        Args:
            initial_lr: LR maximo despues del warmup (default 3e-4)
            min_lr: LR minimo al inicio y al final (default 5e-5)
            warmup_fraction: Fraccion del training para warmup (default 5%)
        
        Returns:
            Callable que toma progress (0.0-1.0) y devuelve LR actual
        """
        def schedule(progress_remaining: float) -> float:
            """Calcula LR basado en progreso (1.0 -> 0.0 durante training)."""
            # progress_remaining: 1.0 al inicio, 0.0 al final
            progress = 1.0 - progress_remaining
            
            if progress < warmup_fraction:
                # WARMUP: Linear increase de min_lr a initial_lr
                warmup_progress = progress / warmup_fraction
                return min_lr + (initial_lr - min_lr) * warmup_progress
            else:
                # COSINE DECAY: De initial_lr a min_lr
                decay_progress = (progress - warmup_fraction) / (1.0 - warmup_fraction)
                # Cosine annealing: suave y estable
                cosine_factor = 0.5 * (1.0 + math.cos(math.pi * decay_progress))
                return min_lr + (initial_lr - min_lr) * cosine_factor
        
        return schedule
    
    @classmethod
    def for_gpu(cls) -> 'SACConfig':
        """Configuracion MEJORADA para SAC en GPU RTX 4060 (8.6GB VRAM) - v3.1.
        
        OPCION 2 AGRESIVA (2026-02-15) - PARA COMPETIR CON PPO/A2C:
        - Learning rate 5e-4 (AUMENTADO: mejor convergencia)
        - Buffer 400K (AUMENTADO: mas diversidad de experiencias)
        - Batch 128 (AUMENTADO: mejor estimacion de gradientes)
        - train_freq=2 (AUMENTADO: mas training por timestep)
        - gradient_steps=1 (REDUCIDO: menos overtraining, mas freshness)
        - ent_coef='auto' DINAMICO (ajuste optimo de exploracion)
        - Networks 384x384 (AUMENTADO: mas expresivo que 256x256)
        - tau=0.005 (STANDARD SAC: mejor soft updates)
        - gamma=0.99 (STANDARD: mejor para problemas complejos)
        - target_entropy=-10 (EQUILIBRIO: exploracion vs explotacion)
        
        CAMBIOS CLAVE:
        1. +67% learning rate: 3e-4 -> 5e-4 (SAC es sensible pero puede tolerar)
        2. +33% buffer: 300K -> 400K (experiencias mas diversas)
        3. +100% batch: 64 -> 128 (mejor signal-to-noise en gradientes)
        4. +100% training: train_freq (4,step) -> (2,step) (el doble de updates)
        5. -50% gradient_steps: 2 -> 1 (evita overtraining, mantiene freshness)
        6. +50% networks: 256->384 (mas capacidad representacional)
        7. +150% tau: 0.002 -> 0.005 (standard per SAC paper)
        8. +2% gamma: 0.98 -> 0.99 (mejor long-term reward consideration)
        9. +2x entropy: -5 -> -10 (exploraci├│n balanceada)
        
        RESULTADO ESPERADO: +50% mejor rendimiento (15.35M -> 23M kg CO2)
        """
        # Learning rate ADAPTATIVO con warmup + cosine decay
        # v7.4 FIX: Reducir LR para evitar Q-value explosion con reward scaling agresivo
        lr_schedule = cls.adaptive_lr_schedule(
            initial_lr=2e-4,   # REDUCIDO v7.4: 5e-4 -> 2e-4 (mas conservador, evita grad explosion)
            min_lr=3e-5,       # REDUCIDO v7.4: 7e-5 -> 3e-5
            warmup_fraction=0.05  # Sin cambio: 5% warmup
        )
        
        return cls(
            # Learning rate ADAPTATIVO AGRESIVO
            learning_rate=lr_schedule,  # SCHEDULE: warmup -> cosine decay
            
            # Replay buffer - AUMENTADO para mas diversidad
            buffer_size=400_000,  # AUMENTADO: 300K -> 400K (33% mas experiencias)
            learning_starts=5_000,  # Sin cambio - warmup estandar
            
            # Batch y updates - MODERADO (v7.4: FIX overtraining)
            batch_size=64,  # REDUCIDO v7.4: 128 -> 64 (evita overshooting con aggressive schedule)
            train_freq=(4, 'step'),  # REDUCIDO v7.4: (2,step) -> (4,step) (x2 menos training, mas stability)
            gradient_steps=1,  # Sin cambio: 1 (evita overtraining)
            
            # Soft update - STANDARD SAC (paper recomienda 0.005)
            tau=0.005,  # AUMENTADO: 0.002 -> 0.005 (standard SAC paper)
            target_update_interval=1,
            
            # Discount - STANDARD para problemas complejos
            gamma=0.99,  # AUMENTADO: 0.98 -> 0.99 (mejor long-term horizons) 
            
            # Entropy - AUTO-TUNE con target BALANCEADO
            # target_entropy = -39 es OPTIMO segun paper (basado en |A|)
            # Pero -10 permite mas exploracion sin collapse
            ent_coef='auto',  # DINAMICO - SAC ajusta alpha automaticamente
            target_entropy=-10.0,  # AUMENTADO: -5 -> -10 (exploraci├│n balanceada)
            
            # Networks - MAS EXPRESIVOS para problema complejo (39D continuo)
            policy_kwargs={
                'net_arch': dict(pi=[384, 384], qf=[384, 384]),  # AUMENTADO: 256->384 (+50%)
                'activation_fn': torch.nn.ReLU,
                'log_std_init': -0.5,  # AUMENTADO: -1.0 -> -0.5 (std=0.6 vs 0.37) MAYOR EXPLORACION
                'optimizer_class': torch.optim.Adam,
                'optimizer_kwargs': {'eps': 1e-5},  # Estabilidad numerica
            },
            # Usar SDE para mejor exploracion en espacios continuos
            use_sde=True,
            sde_sample_freq=8,  # Resamplear ruido cada 8 steps
        )
    
    @classmethod
    def for_cpu(cls) -> 'SACConfig':
        """Configuracion para CPU (fallback, recursos limitados pero optimizado SAC)."""
        return cls(
            learning_rate=3e-4,  # Standard SAC para CPU
            buffer_size=100_000,  # 100K para CPU
            learning_starts=2_000,  # Warmup corto
            batch_size=64,  # Batch pequeno
            train_freq=(1, 'step'),
            gradient_steps=2,  # Moderate (CPU limited)
            tau=0.005,  # Standard SAC
            gamma=0.99,
            # v7.2: Auto-tune entropy con target ALTO (evitar alpha collapse)
            ent_coef='auto',
            target_entropy=-5.0,  # AUMENTADO: era -39, ahora -5 (mas exploracion)
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], qf=[256, 256]),
                'activation_fn': torch.nn.ReLU,
                'log_std_init': -1.0,  # AUMENTADO: era default, ahora -1.0 (mas exploracion)
            },
            # NUEVO: Usar SDE para mejor exploracion
            use_sde=True,
            sde_sample_freq=8,
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
    print(f'[GPU] {GPU_NAME}')
    print(f'   VRAM: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA: {cuda_version}')
    print('   Entrenamiento SAC en GPU (actor-critic 512x512, replay buffer 2M - OPCION A Aggressive)')
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
    print(f"  [OK] Solar: {len(solar_df)} rows (correct hourly)")


def load_observable_variables():
    """Cargar TODAS las 27 columnas observables - FALLBACK a None (datos reales en observacion)"""
    print('[LOAD] Cargando variables observables...')
    try:
        # No external observable_variables - datos reales desde CSVs
        return None  # Fallback para robustez - los datos reales se leen directo de CSVs
    except Exception:
        print('[LOAD] Observables: usando fallback (None - datos reales en observacion directa)')
        return None



def load_datasets_from_processed():
    """Load datasets using CENTRALIZED data_loader (v7.2)
    
    Agents use data BUILT by data_loader via rebuild_oe2_datasets_complete().
    This ensures unified schema and centralized data management.
    
    Returns:
        dict: Combined dataset with solar, chargers, mall, bess and CO2 metrics
    """
    from src.dataset_builder_citylearn.data_loader import rebuild_oe2_datasets_complete
    
    print()
    print('[3] CARGAR DATOS USANDO DATA_LOADER CENTRALIZADO v7.2')
    print('-' * 80)
    print(f'  Usando: rebuild_oe2_datasets_complete() from data_loader')
    print(f'  Esquema: CityLearn v2 unificado')
    print()

    # ====================================================================
    # SOLAR - DEL DATASET PROCESADO - TODAS LAS COLUMNAS REALES
    # ====================================================================
    print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 ano)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    # ====== CARGAR DATOS CON DATA_LOADER CENTRALIZADO ======
    oe2_datasets = rebuild_oe2_datasets_complete()
    
    # SOLAR (SolarData object)
    solar_obj = oe2_datasets['solar']
    solar_hourly = solar_obj.df['potencia_kw'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Extract all solar columns for metadata
    solar_data = {}
    for col in solar_obj.df.columns:
        if col != 'datetime':
            try:
                solar_data[col] = solar_obj.df[col].values[:HOURS_PER_YEAR].astype(np.float32)
            except:
                solar_data[col] = solar_obj.df[col].values[:HOURS_PER_YEAR]
    
    if len(solar_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
    
    print('  [SOLAR] [OK] From data_loader: {:.0f} kWh/year (8760h)'.format(float(np.sum(solar_hourly))))
    print(f'  [SOLAR] Columnas: {len(solar_data)} (de data_loader SolarData)')
    if 'reduccion_indirecta_co2_kg_total' in solar_data:
        print(f'  [SOLAR]   CO2 indirecto evitado: {np.sum(solar_data["reduccion_indirecta_co2_kg_total"]):,.0f} kg/año')

    # CHARGERS (ChargerData object)
    print()
    chargers_obj = oe2_datasets['chargers']
    df_chargers = chargers_obj.df.copy()
    
    # Global charger columns from data_loader
    chargers_data = {}
    chargers_global_cols = [
        'is_hora_punta', 'tarifa_aplicada_soles', 'ev_energia_total_kwh',
        'costo_carga_ev_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
        'co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg', 
        'reduccion_directa_co2_kg', 'ev_demand_kwh'
    ]
    for col in chargers_global_cols:
        if col in df_chargers.columns:
            if col == 'is_hora_punta':
                chargers_data[col] = df_chargers[col].values[:HOURS_PER_YEAR].astype(np.int32)
            else:
                chargers_data[col] = df_chargers[col].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Extract socket power columns (38 total)
    socket_power_cols = [c for c in df_chargers.columns if c.endswith('_charging_power_kw')]
    socket_power_cols.sort(key=lambda x: int(x.split('_')[1]))
    
    if len(socket_power_cols) != 38:
        raise ValueError(f"ERROR: Expected 38 sockets, found {len(socket_power_cols)}")
    
    chargers_hourly = df_chargers[socket_power_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    chargers_moto_hourly = chargers_hourly[:, :30].astype(np.float32)  # Sockets 0-29
    chargers_mototaxi_hourly = chargers_hourly[:, 30:38].astype(np.float32)  # Sockets 30-37
    
    n_sockets = chargers_hourly.shape[1]
    n_moto_sockets = chargers_moto_hourly.shape[1]
    n_mototaxi_sockets = chargers_mototaxi_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    moto_demand = float(np.sum(chargers_moto_hourly))
    mototaxi_demand = float(np.sum(chargers_mototaxi_hourly))
    
    print(f"  [CHARGERS] [OK] From data_loader: {n_sockets} sockets (ESPECIFICACION OE2: 38)")
    print(f"  [CHARGERS]   MOTOS:     {n_moto_sockets} sockets | {moto_demand:,.0f} kWh/ano | {moto_demand/HOURS_PER_YEAR:.1f} kW avg")
    print(f"  [CHARGERS]   MOTOTAXIS: {n_mototaxi_sockets} sockets | {mototaxi_demand:,.0f} kWh/ano | {mototaxi_demand/HOURS_PER_YEAR:.1f} kW avg")
    print(f"  [CHARGERS]   TOTAL:     {total_demand:,.0f} kWh/ano | {total_demand/HOURS_PER_YEAR:.1f} kW avg")
    print(f"  [CHARGERS] Columnas globales: {len(chargers_data)} - {list(chargers_data.keys())}")
    if 'reduccion_directa_co2_kg' in chargers_data:
        print(f"  [CHARGERS]   CO2 DIRECTO evitado: {np.sum(chargers_data['reduccion_directa_co2_kg']):,.0f} kg/año")

    # MALL (DemandData object)
    print()
    demand_obj = oe2_datasets['demand']
    df_mall = demand_obj.df.copy()
    
    # Extract main demand column
    if 'mall_demand_kwh' in df_mall.columns:
        col = 'mall_demand_kwh'
    elif 'demand_kwh' in df_mall.columns:
        col = 'demand_kwh'
    else:
        col = df_mall.columns[-1]
    
    mall_data_dict = {}
    mall_cols = ['mall_demand_kwh', 'mall_co2_indirect_kg', 'is_hora_punta', 'tarifa_soles_kwh', 'mall_cost_soles']
    for col_name in mall_cols:
        if col_name in df_mall.columns:
            if col_name == 'is_hora_punta':
                mall_data_dict[col_name] = df_mall[col_name].values[:HOURS_PER_YEAR].astype(np.int32)
            else:
                mall_data_dict[col_name] = df_mall[col_name].values[:HOURS_PER_YEAR].astype(np.float32)
    
    mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
    if len(mall_data) < HOURS_PER_YEAR:
        mall_hourly = np.pad(mall_data, ((0, HOURS_PER_YEAR - len(mall_data)),), mode='wrap')
    else:
        mall_hourly = mall_data
    
    print(f'  [MALL] [OK] From data_loader: {np.sum(mall_hourly):.0f} kWh/year (avg {np.mean(mall_hourly):.1f} kW/h)')
    print(f'  [MALL] Columnas: {len(mall_data_dict)} - {list(mall_data_dict.keys())}')
    if 'mall_co2_indirect_kg' in mall_data_dict:
        print(f'  [MALL]   CO2 EMITIDO por mall: {np.sum(mall_data_dict["mall_co2_indirect_kg"]):,.0f} kg/año (NO reduce, EMITE)')

    # BESS (BESSData object)
    print()
    bess_obj = oe2_datasets['bess']
    df_bess = bess_obj.df.copy()
    
    # Extract BESS SOC (state of charge)
    if 'bess_soc_percent' in df_bess.columns:
        bess_soc = df_bess['bess_soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
    elif 'soc_percent' in df_bess.columns:
        bess_soc = df_bess['soc_percent'].values[:HOURS_PER_YEAR].astype(np.float32)
    elif 'soc_kwh' in df_bess.columns:
        soc_kwh = df_bess['soc_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
        soc_max = float(np.max(soc_kwh))
        bess_soc = 100.0 * soc_kwh / soc_max if soc_max > 0 else np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
    else:
        bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
    
    # Extract BESS costs and CO2 metrics
    bess_costs = df_bess['cost_grid_import_soles'].values[:HOURS_PER_YEAR].astype(np.float32) if 'cost_grid_import_soles' in df_bess.columns else None
    bess_peak_savings = df_bess['peak_reduction_savings_soles'].values[:HOURS_PER_YEAR].astype(np.float32) if 'peak_reduction_savings_soles' in df_bess.columns else None
    bess_tariff = df_bess['tariff_osinergmin_soles_kwh'].values[:HOURS_PER_YEAR].astype(np.float32) if 'tariff_osinergmin_soles_kwh' in df_bess.columns else None
    bess_co2_avoided = df_bess['co2_avoided_indirect_kg'].values[:HOURS_PER_YEAR].astype(np.float32) if 'co2_avoided_indirect_kg' in df_bess.columns else None
    bess_co2_grid = np.full(HOURS_PER_YEAR, CO2_FACTOR_IQUITOS, dtype=np.float32)
    
    # Extract energy flows from BESS dataset
    energy_flows = {}
    flow_columns = [
        'pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh',
        'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
        'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
        'grid_to_ev_kwh', 'grid_to_mall_kwh', 'grid_to_bess_kwh', 'grid_import_total_kwh',
        'mall_grid_import_kwh', 'peak_reduction_savings_normalized', 'co2_avoided_indirect_normalized'
    ]
    for col in flow_columns:
        if col in df_bess.columns:
            if col == 'bess_mode':
                mode_map = {'idle': 0, 'charge': 1, 'discharge': 2}
                energy_flows[col] = df_bess[col].map(mode_map).fillna(0).values[:HOURS_PER_YEAR].astype(np.float32)
            else:
                energy_flows[col] = df_bess[col].values[:HOURS_PER_YEAR].astype(np.float32)
    
    bess_co2 = {
        'grid_kg': bess_co2_grid,
        'avoided_kg': bess_co2_avoided if bess_co2_avoided is not None else np.zeros(HOURS_PER_YEAR, dtype=np.float32),
    }
    
    # Extract demands from BESS dataset
    bess_ev_demand = df_bess['ev_demand_kwh'].values[:HOURS_PER_YEAR].astype(np.float32) if 'ev_demand_kwh' in df_bess.columns else None
    bess_mall_demand = df_bess['mall_demand_kwh'].values[:HOURS_PER_YEAR].astype(np.float32) if 'mall_demand_kwh' in df_bess.columns else None
    bess_pv_generation = df_bess['pv_generation_kwh'].values[:HOURS_PER_YEAR].astype(np.float32) if 'pv_generation_kwh' in df_bess.columns else None
    
    print(f"  [BESS] [OK] From data_loader: Simulated BESS operation model")
    print(f"  [BESS] Avg SOC: {float(np.asarray(bess_soc).mean()):.1f}%")
    if bess_costs is not None:
        print(f"  [BESS] Costos grid:         {float(np.asarray(bess_costs).sum()):,.2f} soles/año")
    if bess_peak_savings is not None:
        print(f"  [BESS] Ahorros pico:        {float(np.asarray(bess_peak_savings).sum()):,.2f} soles/año")
    if bess_co2_avoided is not None:
        print(f"  [BESS] CO2 evitado indirecto: {float(np.asarray(bess_co2_avoided).sum()):,.0f} kg/año")
    if 'pv_to_ev_kwh' in energy_flows:
        print(f"  [BESS] Solar->EV:            {float(np.sum(energy_flows['pv_to_ev_kwh'])):,.0f} kWh/año")
    if 'bess_to_ev_kwh' in energy_flows:
        print(f"  [BESS] BESS->EV:             {float(np.sum(energy_flows['bess_to_ev_kwh'])):,.0f} kWh/año")
    if 'grid_import_total_kwh' in energy_flows:
        print(f"  [BESS] Grid import total:   {float(np.sum(energy_flows['grid_import_total_kwh'])):,.0f} kWh/año")
    if bess_ev_demand is not None:
        print(f"  [BESS] EV Demand (REAL):    {float(np.asarray(bess_ev_demand).sum()):,.0f} kWh/año")
    if bess_mall_demand is not None:
        print(f"  [BESS] Mall Demand (REAL):  {float(np.asarray(bess_mall_demand).sum()):,.0f} kWh/año")
    if bess_pv_generation is not None:
        print(f"  [BESS] PV Gen (REAL):       {float(np.asarray(bess_pv_generation).sum()):,.0f} kWh/año")
    
    print()
    # ====================================================================
    # CARGAR TODAS LAS 27 VARIABLES OBSERVABLES DEL DATASET_BUILDER
    # ====================================================================
    print('[LOAD] Extrayendo TODAS las variables observables del dataset_builder v5.5...')
    observable_variables_df = load_observable_variables()
    
    print()
    # RETORNAR: todos los datos necesarios para entrenamiento CON DATOS REALES COMPLETOS
    return {
        # ===== SOLAR (16 columnas) =====
        'solar': solar_hourly,
        'solar_data': solar_data,  # Dict con TODAS las columnas: irradiancia_ghi, temperatura_c, etc.
        
        # ===== CHARGERS (11 columnas globales + 38 sockets) =====
        'chargers': chargers_hourly,
        'chargers_moto': chargers_moto_hourly,
        'chargers_mototaxi': chargers_mototaxi_hourly,
        'n_moto_sockets': n_moto_sockets,
        'n_mototaxi_sockets': n_mototaxi_sockets,
        'chargers_data': chargers_data,  # Dict: is_hora_punta, tarifa, co2_reduccion_motos_kg, etc.
        
        # ===== MALL (6 columnas) =====
        'mall': mall_hourly,
        'mall_data': mall_data_dict,  # Dict: mall_co2_indirect_kg, tarifa_soles_kwh, mall_cost_soles
        
        # ===== BESS (25 columnas) =====
        'bess_soc': bess_soc,
        'bess_costs': bess_costs,
        'bess_peak_savings': bess_peak_savings,
        'bess_tariff': bess_tariff,
        'bess_co2': bess_co2,
        
        # Flujos de energia (TODAS las columnas del BESS)
        'energy_flows': energy_flows,
        'bess_ev_demand': bess_ev_demand,       # Demanda EV real por hora
        'bess_mall_demand': bess_mall_demand,   # Demanda mall real por hora
        'bess_pv_generation': bess_pv_generation,  # PV real por hora
        
        # Estadisticas chargers
        'charger_max_power_kw': CHARGER_MAX_KW,  # 3.7 kW por socket
        'charger_mean_power_kw': CHARGER_MEAN_KW,  # 4.6 kW por socket (media)
        
        # TODAS LAS 27 VARIABLES OBSERVABLES DEL DATASET_BUILDER
        'observable_variables': observable_variables_df,
    }

# ===== TRAINING LOOP =====

def clean_sac_checkpoints_safe() -> None:
    """
    Limpia SOLO checkpoints de SAC de forma robusta y segura en Python.
    SIN dependencias de PowerShell - evita errores de parsing.
    
    Validaciones:
      1. Verifica que solo exista SAC (otros agentes untouched)
      2. Elimina archivos SAC recursivamente
      3. Reporta confirmacion de limpieza
    """
    import shutil
    
    checkpoint_dir = Path('checkpoints')
    sac_dir = checkpoint_dir / 'SAC'
    
    print()
    print('[TOOLS] LIMPIEZA SEGURA DE CHECKPOINTS (PYTHON ROBUSTO)')
    print('=' * 80)
    print()
    
    # Paso 1: Listar checkpoints ANTES de limpiar
    print('[1] Checkpoints ANTES de limpiar:')
    if checkpoint_dir.exists():
        agents = sorted([d.name for d in checkpoint_dir.iterdir() if d.is_dir()])
        if agents:
            for agent in agents:
                print(f'    - {agent}')
        else:
            print('    (Directorio vacio)')
    else:
        print('    (Carpeta checkpoints no existe)')
    print()
    
    # Paso 2: Limpiar SOLO SAC - validacion estricta
    print('[2] Limpiando SOLO: checkpoints/SAC/')
    if sac_dir.exists():
        try:
            # Contar archivos antes de eliminar
            sac_files = list(sac_dir.rglob('*'))
            file_count = len([f for f in sac_files if f.is_file()])
            dir_count = len([f for f in sac_files if f.is_dir()])
            
            print(f'    [OK] Carpeta SAC encontrada')
            print(f'    - {file_count} archivos a eliminar')
            print(f'    - {dir_count} directorios a eliminar')
            
            # Eliminar recursivamente
            shutil.rmtree(sac_dir)
            print(f'    [OK] Checkpoints SAC eliminados correctamente')
            
        except Exception as e:
            print(f'    [!] Error al eliminar SAC: {str(e)}')
            return
    else:
        print('    (No habia checkpoints SAC previos)')
    print()
    
    # Paso 3: Validar que NO se elimino nada mas
    print('[3] Checkpoints DESPUES de limpiar (validacion):')
    if checkpoint_dir.exists():
        agents = sorted([d.name for d in checkpoint_dir.iterdir() if d.is_dir()])
        if agents:
            for agent in agents:
                print(f'    - {agent}')
            print(f'    [OK] CORRECTO: Otros agentes preservados')
        else:
            print('    (Carpeta checkpoints vacia)')
    else:
        print('    (Carpeta checkpoints no existe)')
    print()
    
    print('[OK] LIMPIEZA COMPLETADA SEGURAMENTE')
    print()


def main():
    """Entrenar SAC con multiobjetivo."""
    
    # ===== LIMPIEZA DE CHECKPOINTS SAC (DESACTIVADA PARA CONTINUAR) =====
    # NOTA: Descomentar para entrenar desde cero:
    # clean_sac_checkpoints_safe()
    #
    # Por defecto: NO limpiar para permitir continuar
    print()
    print('[INFO] Checkpoints SAC existentes seran PRESERVADOS (continuar entrenamiento)')
    print('       Para entrenar desde cero, descomentar clean_sac_checkpoints_safe() en main()')
    print()
    
    # ===== VALIDACION ROBUSTA DE DATASETS (PREVENIR TODOS LOS ERRORES DE RAIZ) =====
    try:
        datasets = load_datasets_from_processed()
    except Exception as e:
        print(f'\n[FATAL] No se pudieron cargar los datasets: {str(e)[:100]}')
        print('[ACCION] Ejecutar primero: python scripts/train/prepare_data_ppo.py')
        sys.exit(1)
    
    # Validar que TODOS los keys requeridos existan - DEFENSIVE PROGRAMMING
    required_keys = [
        'solar', 'chargers', 'mall', 'bess_soc', 'bess_costs', 'bess_co2', 
        'charger_max_power_kw', 'charger_mean_power_kw'
    ]
    
    missing_keys = [k for k in required_keys if k not in datasets]
    if missing_keys:
        print(f'\n[FATAL] Datasets incompletos. Faltan: {missing_keys}')
        print('[ACCION] Regenerar datasets con: python scripts/train/prepare_data_ppo.py')
        sys.exit(1)
    
    # Validar dimensiones esenciales (8760 horas = 1 ano)
    try:
        assert len(datasets['solar']) == HOURS_PER_YEAR, f"Solar: esperado {HOURS_PER_YEAR}, got {len(datasets['solar'])}"
        assert len(datasets['chargers']) == HOURS_PER_YEAR, f"Chargers: esperado {HOURS_PER_YEAR}, got {len(datasets['chargers'])}"
        assert len(datasets['mall']) == HOURS_PER_YEAR, f"Mall: esperado {HOURS_PER_YEAR}, got {len(datasets['mall'])}"
        assert len(datasets['bess_soc']) == HOURS_PER_YEAR, f"BESS SOC: esperado {HOURS_PER_YEAR}, got {len(datasets['bess_soc'])}"
        print(f'  [OK] Validacion de dimensiones OK ({HOURS_PER_YEAR} horas x 4 datasets)')
    except AssertionError as e:
        print(f'\n[FATAL] Validacion de dimensiones fallida: {str(e)}')
        sys.exit(1)
    
    # Desempaquetar datos cargados - TODOS LOS DATOS REALES
    solar_hourly = datasets['solar']
    solar_data = datasets.get('solar_data', {})  # Todas columnas solares (16)
    chargers_hourly = datasets['chargers']
    chargers_moto = datasets.get('chargers_moto')  # Sockets motos
    chargers_mototaxi = datasets.get('chargers_mototaxi')  # Sockets mototaxis
    n_moto_sockets = datasets.get('n_moto_sockets', 0)
    n_mototaxi_sockets = datasets.get('n_mototaxi_sockets', 0)
    chargers_data = datasets.get('chargers_data', {})  # 11 columnas globales: co2_reduccion_motos_kg, etc.
    mall_hourly = datasets['mall']
    mall_data = datasets.get('mall_data', {})  # 6 columnas: mall_co2_indirect_kg, tarifa_soles_kwh, etc.
    bess_soc = datasets['bess_soc']
    bess_costs = datasets['bess_costs']
    bess_peak_savings = datasets.get('bess_peak_savings')
    bess_tariff = datasets.get('bess_tariff')
    bess_co2 = datasets['bess_co2']
    energy_flows = datasets.get('energy_flows', {})
    bess_ev_demand = datasets.get('bess_ev_demand')  # Demanda EV real
    bess_mall_demand = datasets.get('bess_mall_demand')  # Demanda mall real
    bess_pv_generation = datasets.get('bess_pv_generation')  # PV real
    charger_max_power = datasets['charger_max_power_kw']
    charger_mean_power = datasets['charger_mean_power_kw']
    observable_variables_df = datasets.get('observable_variables', None)  # 27 columnas observables
    
    # ===== DATA QUALITY CHECKS (DETECTAR Y PREVENIR ERRORES) =====
    print('[3.5] VALIDAR CALIDAD DE DATOS')
    print('-' * 80)
    
    # Chequear NaN y infinitos
    data_quality_ok = True
    for name, data in [
        ('Solar', solar_hourly),
        ('Chargers', chargers_hourly),
        ('Mall', mall_hourly),
        ('BESS SOC', bess_soc),
        ('BESS Costs', bess_costs),
        ('Charger Max Power', charger_max_power),
        ('Charger Mean Power', charger_mean_power),
    ]:
        if isinstance(data, (list, np.ndarray)):
            arr = np.array(data)
            nan_count = np.sum(np.isnan(arr))
            inf_count = np.sum(np.isinf(arr))
            
            if nan_count > 0 or inf_count > 0:
                print(f'  [!] {name}: {nan_count} NaN, {inf_count} inf (LIMPIANDO)')
                arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
                data_quality_ok = False
            else:
                print(f'  [OK] {name}: OK (sin NaN/inf)')
        elif data is not None:
            print(f'  [OK] {name}: OK')
    
    if not data_quality_ok:
        print('\n  [!] DATOS LIMPIADOS AUTOMATICAMENTE (NaN/inf -> 0.0)')
    print()
    
    print('[4] CONFIGURAR AGENTE SAC CON DATOS 100% REALES')
    print('-' * 80)
    print(f'  === SOLAR (PVGIS + PVLib) ===')
    print(f'  Solar AC Power:  cargado [OK] ({len(solar_hourly)} horas, {np.sum(solar_hourly):,.0f} kWh/ano)')
    if solar_data:
        print(f'  Solar Columnas:  {len(solar_data)} columnas REALES: {list(solar_data.keys())}')
    print()
    print(f'  === CHARGERS (MEDICIONES) ===')
    print(f'  MOTOS:           {n_moto_sockets} sockets | {np.sum(chargers_moto) if chargers_moto is not None else 0:,.0f} kWh/ano')
    print(f'  MOTOTAXIS:       {n_mototaxi_sockets} sockets | {np.sum(chargers_mototaxi) if chargers_mototaxi is not None else 0:,.0f} kWh/ano')
    print(f'  TOTAL:           {chargers_hourly.shape[1]} sockets | {np.sum(chargers_hourly):,.0f} kWh/ano')
    if chargers_data:
        print(f'  Chargers Cols:   {len(chargers_data)} columnas globales: {list(chargers_data.keys())}')
        # Mostrar CO2 reducci├│n directa si est├í disponible
        if 'reduccion_directa_co2_kg' in chargers_data:
            co2_directo = chargers_data['reduccion_directa_co2_kg']
            print(f'  CO2 Reduccion:   {np.sum(co2_directo):,.0f} kg/ano (DIRECTO - Solo EV)')
    print()
    print(f'  === MALL (MEDICIONES) ===')
    print(f'  Mall demand:     cargado [OK] ({np.sum(mall_hourly):,.0f} kWh/ano)')
    if mall_data:
        print(f'  Mall Columnas:   {len(mall_data)} columnas: {list(mall_data.keys())}')
        if 'mall_co2_indirect_kg' in mall_data:
            co2_mall = mall_data['mall_co2_indirect_kg']
            print(f'  CO2 Mall EMITE:  {np.sum(co2_mall):,.0f} kg/ano (grid termico)')
    print()
    print(f'  === BESS (SIMULACION CON DATOS REALES) ===')
    print(f'  BESS SOC:        cargado [OK] (avg: {np.mean(bess_soc):.1f}%)')
    if bess_costs is not None:
        print(f'  BESS Costos:     cargado [OK] ({np.sum(bess_costs):,.0f} soles/ano)')
    if bess_peak_savings is not None:
        print(f'  BESS Peak Svngs: cargado [OK] ({np.sum(bess_peak_savings):,.0f} soles/ano)')
    if bess_tariff is not None:
        print(f'  Tarifa OSINERG:  cargado [OK] (mean: {np.mean(bess_tariff):.4f} sol/kWh)')
    if bess_co2 is not None and bess_co2.get('avoided_kg') is not None:
        print(f'  CO2 Evitado:     cargado [OK] ({np.sum(bess_co2["avoided_kg"]):,.0f} kg/ano)')
    if energy_flows:
        print(f'  Energy Flows:    cargado [OK] ({len(energy_flows)} flujos)')
    print()
    print(f'  === DEMANDAS REALES (DATASET BESS) ===')
    if bess_ev_demand is not None:
        print(f'  EV Demand REAL:  {np.sum(bess_ev_demand):,.0f} kWh/ano')
    if bess_mall_demand is not None:
        print(f'  Mall Dem REAL:   {np.sum(bess_mall_demand):,.0f} kWh/ano')
    if bess_pv_generation is not None:
        print(f'  PV Gen REAL:     {np.sum(bess_pv_generation):,.0f} kWh/ano')
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
        """Ambiente real consistente con PPO/A2C - CityLearn v2 spec completa
        
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
        NUM_CHARGERS: int = 38  # v5.2: 19 chargers ├ù 2 sockets
        OBS_DIM: int = 246      # ­ƒåò v6.0: 156 (v5.3 base) + 27 (observables) + 38 (per-socket SOC) + 38 (time remaining) + 7 (communication)
        ACTION_DIM: int = 39    # 1 BESS + 38 chargers
        
        # Socket distribution (from actual chargers_ev_ano_2024_v3.csv)
        MOTO_SOCKETS: int = 30      # Sockets 0-29: Personal motorcycles (15 chargers)
        MOTOTAXI_SOCKETS: int = 8   # Sockets 30-37: Taxi motorcycles (4 chargers)
        
        def __init__(self, solar_kw, chargers_kw, mall_kw, bess_soc, bess_costs=None, bess_co2=None, 
                     reward_weights=None, context=None, charger_max_power_kw=None, charger_mean_power_kw=None,
                     bess_peak_savings=None, bess_tariff=None, energy_flows=None,
                     solar_data=None, chargers_moto=None, chargers_mototaxi=None,
                     n_moto_sockets=0, n_mototaxi_sockets=0,
                     bess_ev_demand=None, bess_mall_demand=None, bess_pv_generation=None,
                     observable_variables=None, chargers_data=None, mall_data=None):
            super().__init__()
            self.solar = solar_kw
            self.solar_data = solar_data or {}  # Todas las columnas solares REALES (16 cols)
            self.chargers = chargers_kw
            self.chargers_data = chargers_data or {}  # 11 columnas globales: co2_reduccion_motos_kg, etc.
            self.mall_data = mall_data or {}  # 6 columnas: mall_co2_indirect_kg, tarifa_soles_kwh, etc.
            self.observable_variables = observable_variables  # 27 columnas observables del dataset_builder
            self.chargers_moto = chargers_moto  # Sockets MOTOS
            self.chargers_mototaxi = chargers_mototaxi  # Sockets MOTOTAXIS
            self.n_moto_real = n_moto_sockets
            self.n_mototaxi_real = n_mototaxi_sockets
            self.mall = mall_kw
            self.bess_soc = bess_soc
            self.bess_costs = bess_costs
            self.bess_peak_savings = bess_peak_savings
            self.bess_tariff = bess_tariff
            self.bess_co2 = bess_co2
            self.energy_flows = energy_flows or {}
            # Demandas REALES del dataset BESS
            self.bess_ev_demand = bess_ev_demand
            self.bess_mall_demand = bess_mall_demand
            self.bess_pv_generation = bess_pv_generation
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
            
            # Vehicle simulator - usamos VehicleSOCTracker interno (no dependencia externa)
            self.vehicle_simulator = None  # Deprecado - ahora usamos self.soc_tracker
            
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
            self.episode_ev_satisfied = 0.0
            
            # ===== VEHICLE SOC TRACKER (NUEVO SISTEMA) =====
            self.soc_tracker = VehicleSOCTracker(
                n_moto_sockets=self.MOTO_SOCKETS,
                n_mototaxi_sockets=self.MOTOTAXI_SOCKETS
            )
            
            # Current scenario (for scarcity simulation)
            self.current_scenario: Optional[ChargingScenario] = None
            
            # Metricas de priorizacion por episodio
            self.episode_prioritization_reward = 0.0
            self.episode_completion_reward = 0.0
            
            # Metricas BESS por episodio
            self.episode_bess_discharge_kwh = 0.0
            self.episode_bess_charge_kwh = 0.0
            self.episode_bess_cycles = 0  # Numero de ciclos carga/descarga
            self._last_bess_action = 0.5  # Para detectar cambios
            
            # Metricas CO2 por episodio (ESTRUCTURA v7.1)
            self.episode_co2_directo_evitado_kg = 0.0   # EVs vs gasolina (SOLO EV)
            self.episode_co2_indirecto_evitado_kg = 0.0  # Solar + BESS vs grid
            self.episode_co2_indirecto_solar_kg = 0.0    # v7.1: Solar -> EV, BESS, Mall, Red
            self.episode_co2_indirecto_bess_kg = 0.0     # v7.1: BESS -> EV, Mall (peak shaving)
            self.episode_co2_mall_emitido_kg = 0.0       # v7.1: MALL EMITE (NO reduce)
            self.episode_co2_grid_kg = 0.0              # Emisiones del grid
            
            # Metricas de costos por episodio
            self.episode_costo_grid_soles = 0.0
            self.episode_ahorro_solar_soles = 0.0
            self.episode_ahorro_bess_soles = 0.0
            
            # ===== METRICAS REALES (CARGADAS DE DATASETS) =====
            self.episode_real_pv_to_ev_kwh = 0.0       # Solar directo a EVs
            self.episode_real_bess_to_ev_kwh = 0.0     # BESS a EVs
            self.episode_real_grid_import_kwh = 0.0    # Importacion grid total
            self.episode_real_co2_avoided_kg = 0.0     # CO2 evitado indirecto (REAL)
            self.episode_real_cost_soles = 0.0         # Costo grid (REAL)
            self.episode_real_peak_savings = 0.0       # Ahorro picos (REAL)
            
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
            
        def reset(self, seed=None):
            self.current_step = 0
            self.episode_num += 1
            self.episode_reward = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import_kwh = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_ev_satisfied = 0.0
            
            # Reset SOC tracker completo
            self.soc_tracker.reset()
            
            # Reset metricas de priorizacion
            self.episode_prioritization_reward = 0.0
            self.episode_completion_reward = 0.0
            
            # Reset metricas BESS
            self.episode_bess_discharge_kwh = 0.0
            self.episode_bess_charge_kwh = 0.0
            self.episode_bess_cycles = 0
            self._last_bess_action = 0.5
            
            # Reset metricas CO2 (ESTRUCTURA v7.1)
            self.episode_co2_directo_evitado_kg = 0.0
            self.episode_co2_indirecto_evitado_kg = 0.0
            self.episode_co2_indirecto_solar_kg = 0.0   # v7.1: Solar -> EV, BESS, Mall, Red
            self.episode_co2_indirecto_bess_kg = 0.0    # v7.1: BESS -> EV, Mall (peak shaving)
            self.episode_co2_mall_emitido_kg = 0.0      # v7.1: MALL EMITE (NO reduce)
            self.episode_co2_grid_kg = 0.0
            
            # Reset metricas costos
            self.episode_costo_grid_soles = 0.0
            self.episode_ahorro_solar_soles = 0.0
            self.episode_ahorro_bess_soles = 0.0
            
            # Reset metricas REALES (de datasets)
            self.episode_real_pv_to_ev_kwh = 0.0
            self.episode_real_bess_to_ev_kwh = 0.0
            self.episode_real_grid_import_kwh = 0.0
            self.episode_real_co2_avoided_kg = 0.0
            self.episode_real_cost_soles = 0.0
            self.episode_real_peak_savings = 0.0
            
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
            
            # Inicializar vehiculos en sockets (SOC inicial ~0-5% segun dataset real: llegan vacios)
            for socket_id in range(self.NUM_CHARGERS):
                initial_soc = np.random.uniform(0.0, 5.0)  # Dataset real: vehiculos llegan vacios
                self.soc_tracker.spawn_vehicle(socket_id, hour=0, initial_soc=initial_soc)
            
            obs = self._make_observation(0)
            return obs, {}
        
        def step(self, action):
            h = self.current_step
            hour_24 = h % 24
            
            # ===== USAR DATOS REALES CUANDO ESTEN DISPONIBLES =====
            # Prioridad: dataset BESS > datos chargers > calculo sintetico
            
            # Solar: usar PV generation REAL del BESS dataset si disponible
            if self.bess_pv_generation is not None and h < len(self.bess_pv_generation):
                solar_h = float(self.bess_pv_generation[h])
            else:
                solar_h = float(self.solar[h]) if h < len(self.solar) else 0.0
            
            # EV Demand: usar demanda EV REAL del BESS dataset si disponible
            if self.bess_ev_demand is not None and h < len(self.bess_ev_demand):
                chargers_demand_h = float(self.bess_ev_demand[h])
            else:
                chargers_demand_h = float(self.chargers[h].sum()) if h < len(self.chargers) else 0.0
            
            # Mall Demand: usar demanda Mall REAL del BESS dataset si disponible
            if self.bess_mall_demand is not None and h < len(self.bess_mall_demand):
                mall_demand_h = float(self.bess_mall_demand[h])
            else:
                mall_demand_h = float(self.mall[h]) if h < len(self.mall) else 0.0
            
            bess_soc_h = float(self.bess_soc[h]) if h < len(self.bess_soc) else 50.0
            total_demand = chargers_demand_h + mall_demand_h
            
            # ===== USAR FLUJOS DE ENERGIA REALES SI DISPONIBLES =====
            # Estos son los flujos calculados en la simulacion BESS
            real_pv_to_ev = float(self.energy_flows.get('pv_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_to_ev = float(self.energy_flows.get('bess_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_grid_to_ev = float(self.energy_flows.get('grid_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_grid_import = float(self.energy_flows.get('grid_import_total_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_discharge = float(self.energy_flows.get('bess_discharge_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_charge = float(self.energy_flows.get('bess_charge_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            
            # Parsear accion: [bess_action(1), charger_actions(38)]
       
            bess_action = float(action[0]) if len(action) > 0 else 0.5
            charger_actions = action[1:1+self.n_chargers] if len(action) > 1 else np.zeros(self.n_chargers)
            
            # ===== DETERMINAR ESCENARIO DE CARGA ACTUAL =====
            # Seleccionar escenario basado en hora del dia
            self.current_scenario = None
            for scenario in CHARGING_SCENARIOS:
                if scenario.hour_start <= hour_24 <= scenario.hour_end:
                    self.current_scenario = scenario
                    break
            
            # Calcular potencia disponible (afectada por escenario de escasez)
            available_power_ratio = self.current_scenario.available_power_ratio if self.current_scenario else 1.0
            max_available_power = (solar_h + BESS_MAX_POWER_KW * bess_soc_h / 100.0) * available_power_ratio
            
            # ===== SIMULACION FISICA CON ACCIONES Y ESCASEZ =====
            # BESS: action[0] controla carga/descarga
            # Chargers: action[1:39] controla modulacion (0-1 -> 0-7.4 kW por socket)
            
            bess_discharge = max(0, bess_action - 0.5) * BESS_MAX_POWER_KW
            
            # ===== CARGAR VEHICULOS SEGUN ACCIONES Y PRIORIDAD =====
            # Cuando hay ESCASEZ, el agente debe aprender a priorizar vehiculos con mayor SOC
            total_charging_power = 0.0
            total_energy_delivered = 0.0
            
            for socket_id in range(self.NUM_CHARGERS):
                state = self.soc_tracker.vehicle_states[socket_id]
                if state is None or not state.is_connected:
                    continue
                
                # Potencia asignada por el agente para este socket
                action_idx = socket_id + 1  # +1 porque action[0] es BESS
                power_action = float(charger_actions[socket_id]) if socket_id < len(charger_actions) else 0.5
                
                # Calcular potencia real considerando escasez
                requested_power = power_action * state.max_charge_rate_kw  # 0-7.4 kW
                
                # Si hay escasez severa, limitar potencia disponible
                if available_power_ratio < 1.0:
                    # Aplicar restriccion de potencia proporcional
                    requested_power *= available_power_ratio
                
                # Entregar energia al vehiculo (actualiza SOC)
                energy = state.charge(requested_power, duration_h=1.0)
                total_energy_delivered += energy
                total_charging_power += requested_power
                
                # Verificar si vehiculo alcanzo 100% y contar
                if state.current_soc >= 100.0:
                    if state.vehicle_type == 'moto':
                        self.soc_tracker.total_motos_charged_100 += 1
                    else:
                        self.soc_tracker.total_mototaxis_charged_100 += 1
                    state.is_connected = False  # Desconectar vehiculo cargado
            
            # Actualizar contadores de SOC por nivel
            self.soc_tracker.update_counts()
            
            # Modular demanda total de chargers
            charger_power_modulated = total_charging_power
            
            # ===== BALANCE ENERGETICO (USAR DATOS REALES SI DISPONIBLES) =====
            # Si tenemos flujos reales del BESS dataset, usarlos
            if real_grid_import > 0:
                grid_import = real_grid_import  # REAL del dataset
            else:
                grid_import = max(0, charger_power_modulated + mall_demand_h - solar_h - bess_discharge)  # Calculado
            
            # BESS discharge/charge real
            if real_bess_discharge > 0:
                bess_discharge_actual = real_bess_discharge
            else:
                bess_discharge_actual = bess_discharge
            
            # ===== CALCULO DE CO2 (USAR DATOS REALES CUANDO DISPONIBLES) =====
            # Factor CO2 gasolina para motos/mototaxis: ~2.31 kg CO2/litro
            GASOLINA_KG_CO2_PER_LITRO = 2.31
            MOTO_LITROS_PER_100KM = 2.0
            MOTOTAXI_LITROS_PER_100KM = 3.0
            MOTO_KM_PER_KWH = 50.0
            MOTOTAXI_KM_PER_KWH = 30.0
            
            # CO2 DIRECTO: Emisiones evitadas por usar EV en lugar de gasolina
            # Usar proporcion real de sockets motos/mototaxis
            if self.n_moto_real > 0 and self.n_mototaxi_real > 0:
                moto_ratio = self.n_moto_real / (self.n_moto_real + self.n_mototaxi_real)
                mototaxi_ratio = self.n_mototaxi_real / (self.n_moto_real + self.n_mototaxi_real)
            else:
                moto_ratio = 0.79  # Default: 30/38
                mototaxi_ratio = 0.21  # Default: 8/38
            
            motos_energy = total_energy_delivered * moto_ratio
            mototaxis_energy = total_energy_delivered * mototaxi_ratio
            
            km_motos = motos_energy * MOTO_KM_PER_KWH
            km_mototaxis = mototaxis_energy * MOTOTAXI_KM_PER_KWH
            
            litros_evitados_motos = km_motos * MOTO_LITROS_PER_100KM / 100.0
            litros_evitados_mototaxis = km_mototaxis * MOTOTAXI_LITROS_PER_100KM / 100.0
            
            co2_directo_evitado_kg_calculado = (litros_evitados_motos + litros_evitados_mototaxis) * GASOLINA_KG_CO2_PER_LITRO
            
            # ===================================================================
            # ESTRUCTURA CO2 v7.1 - CALCULO MULTIOBJETIVO CON DATOS REALES
            # ===================================================================
            # 1. CO2 DIRECTO (Solo EV): USAR DATOS REALES DE CHARGERS SI DISPONIBLES
            #    - Fuente real: chargers_data['reduccion_directa_co2_kg'][h]
            #    - Fallback: calculo por cambio combustible gasolina -> electrico
            #
            # 2. CO2 INDIRECTO SOLAR: Cuando solar suministra a EV, BESS, Mall, Red
            #    - Fuente: energy_flows pv_to_ev_kwh, pv_to_bess_kwh, pv_to_mall_kwh
            #    - Factor: 0.4521 kg CO2/kWh (grid termico Iquitos)
            #
            # 3. CO2 INDIRECTO BESS: Cuando BESS suministra a EV y Mall
            #    - Fuente: energy_flows bess_to_ev_kwh + bess_to_mall_kwh
            #    - Condicion: Peak shaving cuando demanda > 2000 kW
            #    - Factor: 0.4521 kg CO2/kWh
            #
            # 4. MALL EMITE CO2 (NO REDUCE): mall_data['mall_co2_indirect_kg']
            #    - El mall consume del grid termico -> EMITE CO2
            # ===================================================================
            
            # CO2 DIRECTO: Usar datos REALES del dataset chargers si disponibles
            if self.chargers_data and 'reduccion_directa_co2_kg' in self.chargers_data:
                real_co2_data = self.chargers_data['reduccion_directa_co2_kg']
                if h < len(real_co2_data):
                    co2_directo_evitado_kg = float(real_co2_data[h])  # DATO REAL del dataset
                else:
                    co2_directo_evitado_kg = co2_directo_evitado_kg_calculado  # Fallback
            else:
                co2_directo_evitado_kg = co2_directo_evitado_kg_calculado  # Fallback formula
            
            # CO2 INDIRECTO SOLAR: energia solar usada reemplaza grid termico
            # USAR DATOS REALES DEL DATASET SOLAR SI DISPONIBLES
            
            # Inicializar variables para evitar errores de referencia
            real_pv_to_mall = 0.0  # Se actualiza abajo si hay datos reales
            
            # Primero intentar usar el dato REAL de reducacion_indirecta_co2_kg_total
            if self.solar_data and 'reduccion_indirecta_co2_kg_total' in self.solar_data:
                real_solar_co2 = self.solar_data['reduccion_indirecta_co2_kg_total']
                if h < len(real_solar_co2):
                    co2_indirecto_solar_kg = float(real_solar_co2[h])  # DATO REAL del dataset
                    # Obtener flujos para otros calculos
                    if h < len(self.energy_flows.get('pv_to_mall_kwh', [])):
                        real_pv_to_mall = float(self.energy_flows['pv_to_mall_kwh'][h])
                else:
                    # Fallback a calcular
                    co2_indirecto_solar_kg = None  # Marcar para calcular despues
            else:
                co2_indirecto_solar_kg = None  # No hay datos reales
            
            # Si no tenemos CO2 solar real, calcularlo desde flujos
            if co2_indirecto_solar_kg is None:
                if h < len(self.energy_flows.get('pv_to_ev_kwh', [])):
                    real_pv_to_ev_calc = float(self.energy_flows['pv_to_ev_kwh'][h])
                else:
                    real_pv_to_ev_calc = 0.0
                if h < len(self.energy_flows.get('pv_to_bess_kwh', [])):
                    real_pv_to_bess = float(self.energy_flows['pv_to_bess_kwh'][h])
                else:
                    real_pv_to_bess = 0.0
                if h < len(self.energy_flows.get('pv_to_mall_kwh', [])):
                    real_pv_to_mall = float(self.energy_flows['pv_to_mall_kwh'][h])
                
                # CO2 indirecto solar = toda la energia solar usada (no curtailada)
                solar_used_total = real_pv_to_ev_calc + real_pv_to_bess + real_pv_to_mall
                if solar_used_total == 0:
                    # Fallback: estimar solar usado
                    solar_used_total = min(solar_h, charger_power_modulated + mall_demand_h)
                
                co2_indirecto_solar_kg = solar_used_total * CO2_FACTOR_IQUITOS
            
            # CO2 INDIRECTO BESS: energia de BESS a EV y Mall (peak shaving)
            # Obtener flujos reales de BESS si disponibles
            if h < len(self.energy_flows.get('bess_to_ev_kwh', [])):
                real_bess_to_ev = float(self.energy_flows['bess_to_ev_kwh'][h])
            else:
                real_bess_to_ev = 0.0
            if h < len(self.energy_flows.get('bess_to_mall_kwh', [])):
                real_bess_to_mall = float(self.energy_flows['bess_to_mall_kwh'][h])
            else:
                real_bess_to_mall = 0.0
            
            # BESS suministra a EV y Mall -> CO2 evitado
            bess_supplied = real_bess_to_ev + real_bess_to_mall
            if bess_supplied == 0:
                # Fallback: usar descarga calculada
                bess_supplied = bess_discharge_actual
            
            # Peak shaving factor: cuando demanda > 2000 kW, BESS es mas valioso
            if mall_demand_h > 2000.0:
                # En pico de demanda: BESS reemplaza grid caro y contaminante
                peak_shaving_factor = 1.0 + (mall_demand_h - 2000.0) / max(1.0, mall_demand_h) * 0.5
            else:
                # Sin pico: BESS aun reduce CO2 pero con factor menor
                peak_shaving_factor = 0.5 + (mall_demand_h / 2000.0) * 0.5
            
            co2_indirecto_bess_kg = bess_supplied * peak_shaving_factor * CO2_FACTOR_IQUITOS
            
            # CO2 TOTAL INDIRECTO = Solar + BESS
            co2_indirecto_evitado_kg = co2_indirecto_solar_kg + co2_indirecto_bess_kg
            
            # MALL EMITE CO2 (NO REDUCE) - usar datos REALES del dataset si disponibles
            # El mall importa del grid termico -> EMITE CO2
            if self.mall_data and 'mall_co2_indirect_kg' in self.mall_data:
                real_mall_co2 = self.mall_data['mall_co2_indirect_kg']
                if h < len(real_mall_co2):
                    co2_mall_emitido_kg = float(real_mall_co2[h])  # DATO REAL del dataset
                else:
                    # Fallback: calcular
                    mall_grid_import_kwh = max(0, mall_demand_h - real_pv_to_mall - real_bess_to_mall)
                    co2_mall_emitido_kg = mall_grid_import_kwh * CO2_FACTOR_IQUITOS
            else:
                # Fallback: calcular si no hay datos reales
                mall_grid_import_kwh = max(0, mall_demand_h - real_pv_to_mall - real_bess_to_mall)
                co2_mall_emitido_kg = mall_grid_import_kwh * CO2_FACTOR_IQUITOS
            
            # CO2 GRID: Emisiones por importar del grid termico (EV + BESS carga)
            co2_grid_kg = grid_import * CO2_FACTOR_IQUITOS
            
            # ===== CALCULO DE COSTOS Y AHORROS (USAR DATOS REALES) =====
            # Tarifa OSINERGMIN REAL si disponible, sino usar defaults
            is_hora_punta = 18 <= hour_24 <= 23
            if self.bess_tariff is not None and h < len(self.bess_tariff):
                tarifa_actual = float(self.bess_tariff[h])  # REAL de OSINERGMIN
            else:
                tarifa_actual = 0.45 if is_hora_punta else 0.28  # Default HP/HFP
            
            # Costo del grid importado (REAL si disponible)
            if self.bess_costs is not None and h < len(self.bess_costs):
                costo_grid_soles = float(self.bess_costs[h])  # REAL del dataset
            else:
                costo_grid_soles = grid_import * tarifa_actual  # Calculado
            
            # Solar usado para ahorro
            if 'pv_to_ev_kwh' in self.energy_flows and 'pv_to_mall_kwh' in self.energy_flows:
                solar_used = real_pv_to_ev + float(self.energy_flows.get('pv_to_mall_kwh', np.zeros(8760))[h] if h < 8760 else 0)
            else:
                solar_used = min(solar_h, charger_power_modulated + mall_demand_h)
            
            # Ahorro por usar solar (energia gratis)
            ahorro_solar_soles = solar_used * tarifa_actual
            
            # Ahorro por usar BESS (descarga durante hora punta) - REAL si disponible
            if self.bess_peak_savings is not None and h < len(self.bess_peak_savings):
                ahorro_bess_soles = float(self.bess_peak_savings[h])  # REAL
            else:
                ahorro_bess_soles = bess_discharge_actual * tarifa_actual if is_hora_punta else 0.0
            
            # ===== CALCULO DE COMPONENTES DE REWARD MULTIOBJETIVO v5.3 =====
            # PRIORIZA CARGAR MAS VEHICULOS para reducir CO2 directo e indirecto
            
            # NOTA: Estos valores se usan ahora SOLO para metricas de info[]
            # Los rewards reales se calculan abajo en v6.2 con normalizacion correcta
            co2_reward_placeholder = -co2_grid_kg / 1000.0  # Solo para info
            solar_self_consumption = min(solar_h, total_demand)
            solar_reward_placeholder = solar_self_consumption / max(1.0, total_demand)  # Solo para info
            charger_satisfaction = total_energy_delivered / max(1.0, chargers_demand_h)
            ev_reward_placeholder = min(1.0, charger_satisfaction)  # Solo para info
            
            # GRID STABILITY (penalizar cambios grandes en demanda)
            bess_dispatch_smoothness = 1.0 - abs(bess_action - 0.5) * 0.1
            stability_reward = bess_dispatch_smoothness
            
            # ===== 6. REWARD DE PRIORIZACION (NUEVO) =====
            # Premia cuando: 100% > 80% > 70% > 50% > 30% > 20% > 10%
            # Solo activo durante escasez de potencia
            prioritization_reward = self.soc_tracker.get_prioritization_reward(
                action, max_available_power, total_demand
            )
            
            # 7. REWARD DE COMPLETACION (NUEVO)
            # Premia vehiculos que alcanzan niveles altos de SOC
            completion_reward = self.soc_tracker.get_completion_reward()
            
            # ================================================================
            # [v5.3] REWARD QUE PRIORIZA CARGAR MAS VEHICULOS
            # ================================================================
            # Contar vehiculos cargando por tipo
            motos_charging_count = 0
            mototaxis_charging_count = 0
            motos_100_count = 0
            taxis_100_count = 0
            
            for socket_id in range(self.NUM_CHARGERS):
                state = self.soc_tracker.vehicle_states[socket_id]
                if state is not None and state.is_connected:
                    if state.vehicle_type == 'moto':
                        motos_charging_count += 1
                        if state.current_soc >= 100.0:
                            motos_100_count += 1
                    else:
                        mototaxis_charging_count += 1
                        if state.current_soc >= 100.0:
                            taxis_100_count += 1
            
            # Total vehiculos cargando vs capacidad maxima (38 sockets)
            total_vehicles = motos_charging_count + mototaxis_charging_count
            vehicles_ratio = total_vehicles / 38.0  # MAX 38
            
            # Componentes de reward v5.3:
            r_vehicles_charging = vehicles_ratio * 0.25        # 25% - Mas vehiculos cargando
            r_vehicles_100 = (motos_100_count + taxis_100_count) / 309.0 * 0.20  # 20% - Completar al 100%
            r_co2_avoided = np.clip((co2_directo_evitado_kg + co2_indirecto_evitado_kg) / 50.0, 0.0, 0.10)  # 10% - CO2 evitado
            
            # Penalizar grid import alto (incentiva solar)
            r_grid_penalty = -np.clip(grid_import / 500.0, 0.0, 0.10)  # -10% max
            
            # Bonus por usar solar para EVs
            if charger_power_modulated > 0.1:
                solar_for_ev = min(solar_h, charger_power_modulated) / charger_power_modulated
            else:
                solar_for_ev = 0.0
            r_solar_to_ev = solar_for_ev * 0.10  # 10% - Solar -> EV
            
            # Bonus BESS (descargar durante pico, cargar con excedente)
            bess_direction = bess_action - 0.5  # -0.5 -> +0.5
            is_peak = 6 <= hour_24 <= 22
            if is_peak and solar_h < chargers_demand_h and bess_direction > 0:
                r_bess = 0.08  # Bonus: descargar BESS cuando hay deficit solar
            elif not is_peak and solar_h > chargers_demand_h * 1.2 and bess_direction < 0:
                r_bess = 0.08  # Bonus: cargar BESS con excedente solar
            else:
                r_bess = 0.0
            
            # Socket efficiency: penalizar sockets activos sin carga
            active_sockets = float(np.sum(charger_actions > 0.1))
            sockets_with_demand = float(np.sum(self.chargers[h] > 0.1)) if h < len(self.chargers) else 0.0
            if active_sockets > 0:
                socket_efficiency = min(sockets_with_demand, active_sockets) / active_sockets
            else:
                socket_efficiency = 1.0
            r_socket_eff = socket_efficiency * 0.05  # 5% - Eficiencia socket
            
            # Time penalty: urgencia de completar vehiculos antes de fin de dia
            hour_norm = hour_24 / 24.0
            daily_target = 309  # 270 motos + 39 mototaxis
            daily_completed = self.soc_tracker.total_motos_charged_100 + self.soc_tracker.total_mototaxis_charged_100
            if hour_norm > 0.5:  # Segunda mitad del dia
                progress = daily_completed / daily_target
                r_time_urgency = 0.02 if progress > hour_norm else -0.02
            else:
                r_time_urgency = 0.0
            
            # COMBINAR REWARD COMPONENTS v5.3
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
            
            # ===== SOLUCION v9.2 RADICAL - REWARD MINIMALISTA PURO =====
            # PROBLEMA RAIZ: base_reward complejo genera Q-values 300+
            # SOLUCION: IGNORA TODO EXCEPTO grid_import -BASED reward simpl├¡simo
            # 
            # Solo 1 signal: grid import (kW)
            # Solo 2 rangos: [0.0005, +0.0003] cuidadosamente calibrado
            #
            
            if grid_import >= 800.0:
                # Grid alto - penalizar
                reward = -0.0003
            elif grid_import >= 300.0:
                # Grid moderado - neutral
                reward = 0.0
            else:
                # Grid bajo - bonus
                reward = +0.0005
            
            # CRITICAL: Static assignment, no base_reward interference
            reward = float(np.clip(reward, -0.0005, 0.0005))
            
            # Acumular metricas por episodio
            self.episode_reward += reward
            self.episode_solar_kwh += solar_h
            self.episode_grid_import_kwh += grid_import
            self.episode_co2_avoided += max(0, solar_h - grid_import)
            self.episode_ev_satisfied += charger_satisfaction * 100.0
            self.episode_prioritization_reward += prioritization_reward
            self.episode_completion_reward += completion_reward
            
            # Acumular metricas BESS - USAR DATOS REALES DEL DATASET
            # Los valores reales ya fueron calculados arriba de energy_flows
            if h < 8760:
                # USAR FLUJOS REALES del dataset bess_ano_2024.csv
                self.episode_bess_discharge_kwh += real_bess_discharge
                self.episode_bess_charge_kwh += real_bess_charge
            else:
                # FALLBACK cuando h >= 8760: usar calculo basado en accion
                if bess_action > 0.55:  # Descargando
                    self.episode_bess_discharge_kwh += bess_discharge
                elif bess_action < 0.45:  # Cargando
                    bess_charge = (0.5 - bess_action) * BESS_MAX_POWER_KW
                    self.episode_bess_charge_kwh += bess_charge
            
            # Contar ciclos BESS (cambios de modo)
            if (self._last_bess_action < 0.45 and bess_action > 0.55) or \
               (self._last_bess_action > 0.55 and bess_action < 0.45):
                self.episode_bess_cycles += 1
            self._last_bess_action = bess_action
            
            # Acumular metricas CO2 (ESTRUCTURA v7.1)
            self.episode_co2_directo_evitado_kg += co2_directo_evitado_kg
            self.episode_co2_indirecto_evitado_kg += co2_indirecto_evitado_kg
            self.episode_co2_indirecto_solar_kg += co2_indirecto_solar_kg    # v7.1
            self.episode_co2_indirecto_bess_kg += co2_indirecto_bess_kg      # v7.1
            self.episode_co2_mall_emitido_kg += co2_mall_emitido_kg          # v7.1
            self.episode_co2_grid_kg += co2_grid_kg
            
            # Acumular metricas costos
            self.episode_costo_grid_soles += costo_grid_soles
            self.episode_ahorro_solar_soles += ahorro_solar_soles
            self.episode_ahorro_bess_soles += ahorro_bess_soles
            
            # ===== ACUMULAR DATOS REALES DE DATASETS =====
            # Estos son datos pre-calculados/simulados del CSV de BESS
            if h < len(self.energy_flows.get('pv_to_ev_kwh', [])):
                self.episode_real_pv_to_ev_kwh += float(self.energy_flows['pv_to_ev_kwh'][h])
            if h < len(self.energy_flows.get('bess_to_ev_kwh', [])):
                self.episode_real_bess_to_ev_kwh += float(self.energy_flows['bess_to_ev_kwh'][h])
            if h < len(self.energy_flows.get('grid_import_total_kwh', [])):
                self.episode_real_grid_import_kwh += float(self.energy_flows['grid_import_total_kwh'][h])
            if self.bess_co2 is not None and self.bess_co2.get('avoided_kg') is not None:
                if h < len(self.bess_co2['avoided_kg']):
                    self.episode_real_co2_avoided_kg += float(self.bess_co2['avoided_kg'][h])
            if self.bess_costs is not None and h < len(self.bess_costs):
                self.episode_real_cost_soles += float(self.bess_costs[h])
            if self.bess_peak_savings is not None and h < len(self.bess_peak_savings):
                self.episode_real_peak_savings += float(self.bess_peak_savings[h])
            
            # ===== ROTACION DE VEHICULOS (simular llegadas/salidas) =====
            # Cada hora, ciertos vehiculos se van y llegan nuevos
            if hour_24 in [6, 9, 12, 15, 18, 21]:  # Horas de rotacion
                for socket_id in range(self.NUM_CHARGERS):
                    state = self.soc_tracker.vehicle_states[socket_id]
                    # Si vehiculo desconectado o muy tiempo (>4h), reemplazar
                    if state is None or not state.is_connected or (h - state.arrival_hour > 4):
                        # 70% probabilidad de nuevo vehiculo
                        if np.random.random() < 0.7:
                            initial_soc = np.random.uniform(0.0, 5.0)  # Dataset real: vehiculos llegan vacios
                            self.soc_tracker.spawn_vehicle(socket_id, hour=h, initial_soc=initial_soc)
            
            # Mover al siguiente timestep
            self.current_step += 1
            done = self.current_step >= self.hours_per_year
            
            # Obtener metricas de tracking
            soc_metrics = self.soc_tracker.get_metrics()
            
            obs = self._make_observation(self.current_step)
            truncated = False
            
            # Determinar escasez actual
            scarcity_level = self.current_scenario.get_scarcity_level() if self.current_scenario else 'NONE'
            
            # ===== CALCULAR BESS POWER KW PARA INFO (igual que PPO) =====
            # bess_action: 0 = carga max, 0.5 = idle, 1 = descarga max
            bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW  # [-342, +342] kW
            
            info = {
                'step': self.current_step,
                'hour': h % 24,
                'hour_of_year': h,
                # ===== ENERGIA - CLAVES ESTANDAR (COMPATIBLES CON CALLBACK) =====
                'solar_kw': solar_h,
                'solar_generation_kwh': solar_h,  # Alias para callback
                'ev_charging_kwh': charger_power_modulated,  # CRITICO: callback busca esto
                'ev_charging_kw': charger_power_modulated,   # Alias
                'ev_demand_kw': charger_power_modulated,     # Alias adicional
                'grid_import_kwh': grid_import,  # CRITICO: callback busca esto
                'grid_import_kw': grid_import,   # Alias
                'mall_demand_kw': mall_demand_h,
                'chargers_demand_kw': charger_power_modulated,  # Mantener original
                # ===== BESS =====
                'bess_soc': bess_soc_h,
                'bess_action': bess_action,
                'bess_power_kw': bess_power_kw,  # CRITICO: callback busca esto
                # ===== METRICAS =====
                'charger_mean_action': float(np.mean(charger_actions)),
                'co2_grid_kg': co2_grid_kg,
                'solar_reward': float(solar_reward_placeholder),
                'co2_reward': float(co2_reward_placeholder),
                'ev_satisfaction': float(charger_satisfaction),
                'prioritization_reward': float(prioritization_reward),
                'completion_reward': float(completion_reward),
                'scarcity_level': scarcity_level,
                'available_power_ratio': available_power_ratio,
                'episode_reward': self.episode_reward if done else None,
                'episode_solar_kwh': self.episode_solar_kwh if done else None,
                **{f'soc_{k}': v for k, v in soc_metrics.items()},  # Metricas SOC
            }
            
            # Mostrar progreso cada 100 steps (con info de escasez y BESS)
            if self.current_step % 100 == 0:
                scarcity_indicator = f'[{scarcity_level}]' if scarcity_level != 'NONE' else ''
                # BESS action: 0-0.5=carga, 0.5=idle, 0.5-1=descarga
                bess_mode = 'CHG' if bess_action < 0.45 else ('DIS' if bess_action > 0.55 else 'IDL')
                print(f'    [EP {self.episode_num:02d}] h={self.current_step:5d}/8760 | Solar={solar_h:6.1f}kW | BESS={bess_soc_h:4.1f}%/{bess_mode} | Grid={grid_import:6.1f}kW | EV={charger_satisfaction:.2f} | Prio={prioritization_reward:+.3f} {scarcity_indicator}')
            
            # Mostrar resumen al final del episodio CON VEHICLE METRICS COMPLETOS
            if done:
                print(f'    [EP {self.episode_num:02d}]  EPISODIO COMPLETADO (MULTIOBJETIVO + PRIORIZACION SOC):')
                print(f'         Total Reward:        {self.episode_reward:12.2f} pts')
                print(f'         Solar kWh:           {self.episode_solar_kwh:12.1f} kWh')
                print(f'         Grid Import:         {self.episode_grid_import_kwh:12.1f} kWh')
                print(f'         CO2 Avoided:         {self.episode_co2_avoided:12.1f} kg')
                print(f'         EV Satisfaction:     {self.episode_ev_satisfied:12.2f} %')
                print(f'         Prioritization Rwd:  {self.episode_prioritization_reward:12.2f} pts')
                print(f'         Completion Reward:   {self.episode_completion_reward:12.2f} pts')
                print()
                # ===== DATOS REALES DE DATASETS =====
                print(f'         --- DATOS REALES (DATASET BESS) ---')
                print(f'           Solar->EV (REAL):   {self.episode_real_pv_to_ev_kwh:12,.0f} kWh')
                print(f'           BESS->EV (REAL):    {self.episode_real_bess_to_ev_kwh:12,.0f} kWh')
                print(f'           Grid Import (REAL):{self.episode_real_grid_import_kwh:12,.0f} kWh')
                print(f'           CO2 Evitado (REAL):{self.episode_real_co2_avoided_kg:12,.0f} kg')
                print(f'           Costo Grid (REAL): {self.episode_real_cost_soles:12,.2f} soles')
                print(f'           Ahorro Pico (REAL):{self.episode_real_peak_savings:12,.2f} soles')
                print()
                # BESS metricas (calculadas por agente)
                print(f'         --- BESS AGENTE ---')
                print(f'             BESS Descarga:    {self.episode_bess_discharge_kwh:12.1f} kWh')
                print(f'             BESS Carga:       {self.episode_bess_charge_kwh:12.1f} kWh')
                print(f'             BESS Ciclos:      {self.episode_bess_cycles:12d}')
                print()
                # CO2 calculados por agente (ESTRUCTURA v7.1)
                print(f'         --- CO2 ESTRUCTURA v7.1 ---')
                print(f'           CO2 DIRECTO (EV):  {self.episode_co2_directo_evitado_kg:12,.0f} kg (cambio combustible)')
                print(f'           CO2 INDIRECTO:')
                print(f'             Solar->EV,BESS,Mall: {self.episode_co2_indirecto_solar_kg:10,.0f} kg')
                print(f'             BESS->EV,Mall:       {self.episode_co2_indirecto_bess_kg:10,.0f} kg (peak shaving)')
                print(f'           CO2 TOTAL EVITADO: {self.episode_co2_directo_evitado_kg + self.episode_co2_indirecto_evitado_kg:12,.0f} kg')
                print(f'           CO2 MALL EMITIDO:  {self.episode_co2_mall_emitido_kg:12,.0f} kg (NO reduce)')
                print(f'           CO2 Grid Emitido:  {self.episode_co2_grid_kg:12,.0f} kg')
                print(f'         --- COSTOS CALCULADOS ---')
                print(f'           Costo Grid:        {self.episode_costo_grid_soles:12,.2f} soles')
                print(f'           Ahorro Solar:      {self.episode_ahorro_solar_soles:12,.2f} soles')
                print(f'           Ahorro BESS:       {self.episode_ahorro_bess_soles:12,.2f} soles')
                print()
                # MOTOS por nivel SOC (30 sockets)
                m = soc_metrics
                print(f'          MOTOS @ SOC:     10%={m["motos_10"]:3d} | 20%={m["motos_20"]:3d} | 30%={m["motos_30"]:3d} | 50%={m["motos_50"]:3d} | 70%={m["motos_70"]:3d} | 80%={m["motos_80"]:3d} | 100%={m["motos_100"]:3d}')
                print(f'          MOTOTAXIS @ SOC:  10%={m["mototaxis_10"]:3d} | 20%={m["mototaxis_20"]:3d} | 30%={m["mototaxis_30"]:3d} | 50%={m["mototaxis_50"]:3d} | 70%={m["mototaxis_70"]:3d} | 80%={m["mototaxis_80"]:3d} | 100%={m["mototaxis_100"]:3d}')
                print(f'          PRIORIZACION:     Accuracy={m["prioritization_accuracy"]*100:.1f}% | Decisiones bajo escasez: {m["scarcity_decisions"]}')
                print(f'          CARGADOS AL 100%: {m["total_charged_100"]} vehiculos')
                if self.reward_weights:
                    print(f'         Pesos usados:        CO2={self.reward_weights.co2:.2f} | Solar={self.reward_weights.solar:.2f} | EV={self.reward_weights.ev_satisfaction:.2f} | (v9.2 minimal reward function)')
                print()
            
            return obs, reward, done, truncated, info
        
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
            solar_kw = float(self.solar[h]) if h < len(self.solar) else 0.0
            mall_kw = float(self.mall[h]) if h < len(self.mall) else 0.0
            bess_soc = float(self.bess_soc[h]) / 100.0 if h < len(self.bess_soc) else 0.5
            
            # Calcular balance energetico
            ev_demand_estimate = float(self.chargers[h].sum()) if h < len(self.chargers) else 0.0
            total_demand = mall_kw + ev_demand_estimate
            solar_surplus = max(0.0, solar_kw - total_demand)
            grid_import_needed = max(0.0, total_demand - solar_kw)
            
            # BESS energia disponible (SOC ├ù capacidad max ├ù eficiencia)
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
            if self.chargers.shape[1] >= self.NUM_CHARGERS:
                raw_demands = self.chargers[h, :self.NUM_CHARGERS]
            else:
                raw_demands = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
                raw_demands[:self.chargers.shape[1]] = self.chargers[h]
            
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
            
            # CALCULAR VEHICULOS COMPLETADOS DESDE DATASET REAL v7.2 (2026-02-17)
            # Usar ev_energia_motos_kwh y ev_energia_mototaxis_kwh del dataset (DATO REAL)
            if h < len(self.chargers):
                try:
                    # Leer energía cargada por tipo de vehículo
                    ev_energy_motos_kwh = float(self.chargers[h, 0]) if len(self.chargers.shape) > 1 else 0.0
                    ev_energy_taxis_kwh = float(self.chargers[h, 1]) if len(self.chargers.shape) > 1 else 0.0
                except (IndexError, TypeError, ValueError):
                    ev_energy_motos_kwh = 0.0
                    ev_energy_taxis_kwh = 0.0
            else:
                ev_energy_motos_kwh = 0.0
                ev_energy_taxis_kwh = 0.0
            
            # Calcular vehículos completados basado en energía necesaria para cargar de 20% a 80% SOC
            # Moto: (80-20)% × 4.6 kWh / 0.95 eficiencia = 2.90 kWh
            # Mototaxi: (80-20)% × 7.4 kWh / 0.95 eficiencia = 4.68 kWh
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
            obs[142] = float(self.context.co2_factor_kg_per_kwh) if self.context else CO2_FACTOR_IQUITOS  # Factor CO2
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

            # ================================================================
            # ­ƒåò v6.0 [156-193] PER-SOCKET SOC (38 features)
            # Visibilidad individual de SOC por socket - CRITICO para v6.0
            # ================================================================
            # Usar potencia entregada como proxy de SOC actual
            socket_power = obs[46:84]  # Potencia actual por socket normalizada
            # Estimar SOC: suma acumulada de potencia ├ù margen de seguridad
            if not hasattr(self, '_socket_soc_accumulated'):
                self._socket_soc_accumulated = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
            
            # Incrementar SOC segun potencia ├ù eficiencia
            soc_increment = socket_power * 0.05  # ~5% SOC por hora a potencia maxima
            self._socket_soc_accumulated = np.clip(self._socket_soc_accumulated + soc_increment, 0.0, 1.0)
            
            # Reset SOC cuando socket se desconecta (ocupancy = 0)
            occupancy = obs[84:122]
            self._socket_soc_accumulated = self._socket_soc_accumulated * occupancy
            
            obs[156:194] = np.clip(self._socket_soc_accumulated, 0.0, 1.0)

            # ================================================================
            # ­ƒåò v6.0 [194-231] TIME REMAINING PER SOCKET (38 features)
            # Tiempo para llegar a 100% SOC por socket - CRITICO para urgencia
            # ================================================================
            if not hasattr(self, '_socket_time_remaining'):
                self._socket_time_remaining = np.full(self.NUM_CHARGERS, 1.0, dtype=np.float32)
            
            # Calcular tiempo restante basado en SOC actual y potencia
            time_to_100pct = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
            for i in range(self.NUM_CHARGERS):
                if socket_power[i] > 0.01:
                    # Si hay potencia, estimar tiempo basado en SOC faltante
                    soc_faltante = 1.0 - self._socket_soc_accumulated[i]
                    time_to_100pct[i] = soc_faltante / (socket_power[i] * 0.05 + 0.01)
                else:
                    # Sin potencia = tiempo infinito (pero normalizamos a 1.0)
                    time_to_100pct[i] = 1.0 if occupancy[i] > 0.5 else 0.0
            
            self._socket_time_remaining = np.clip(time_to_100pct / 8.0, 0.0, 1.0)  # Normalizar a 8 horas max
            obs[194:232] = self._socket_time_remaining

            # ================================================================
            # ­ƒåò v6.0 [232-237] BIDIRECTIONAL COMMUNICATION SIGNALS (6 features)
            # Senales explicitas: BESS supply, Solar available, Grid penalty (por tipo vehiculo)
            # ================================================================
            # BESS dispatch: disponibilidad de energia BESS para motos vs taxis
            bess_available_motos = min(1.0, bess_energy_available / max(1.0, 30 * 7.4))  # Capacidad motos
            bess_available_taxis = min(1.0, bess_energy_available / max(1.0, 8 * 7.4))   # Capacidad taxis
            
            # Solar bypass: excedente solar disponible (sin pasar por BESS)
            solar_excess_motos = min(1.0, solar_surplus / max(1.0, 30 * 7.4))
            solar_excess_taxis = min(1.0, solar_surplus / max(1.0, 8 * 7.4))
            
            # Grid import penalty: costo CO2 de importar (inverso)
            grid_penalty_motos = grid_import_needed / max(1.0, 30 * 7.4)
            grid_penalty_taxis = grid_import_needed / max(1.0, 8 * 7.4)
            
            obs[232] = np.clip(bess_available_motos, 0.0, 1.0)    # BESS -> Motos
            obs[233] = np.clip(bess_available_taxis, 0.0, 1.0)    # BESS -> Taxis
            obs[234] = np.clip(solar_excess_motos, 0.0, 1.0)      # Solar -> Motos
            obs[235] = np.clip(solar_excess_taxis, 0.0, 1.0)      # Solar -> Taxis
            obs[236] = np.clip(grid_penalty_motos, 0.0, 1.0)      # Grid cost -> Motos
            obs[237] = np.clip(grid_penalty_taxis, 0.0, 1.0)      # Grid cost -> Taxis

            # ================================================================
            # ­ƒåò v6.0 [238-245] PRIORITY/URGENCY/CAPACITY AGGREGATES (8 features)
            # ================================================================
            # Contar cuantos sockets tienen baja SOC (urgentes)
            urgent_motos = np.sum((self._socket_soc_accumulated[:30] < 0.3) & (occupancy[:30] > 0.5))
            urgent_taxis = np.sum((self._socket_soc_accumulated[30:38] < 0.3) & (occupancy[30:38] > 0.5))
            
            # Priority levels
            priority_motos_urgent = urgent_motos / 30.0
            priority_taxis_urgent = urgent_taxis / 8.0
            
            # Capacity ratios
            motos_capacity_used = self.motos_charging_now / 30.0
            taxis_capacity_used = self.mototaxis_charging_now / 8.0
            
            # Solar-demand correlation (cuando solar alta, hay oportunidad)
            solar_demand_corr = min(1.0, solar_kw / max(1.0, ev_demand_estimate))
            
            # BESS SOC para referencia de otros componentes
            bess_soc_for_decisions = bess_soc
            
            obs[238] = priority_motos_urgent                          # Motos urgentes
            obs[239] = priority_taxis_urgent                          # Taxis urgentes
            obs[240] = motos_capacity_used                            # Motos capacidad usada
            obs[241] = taxis_capacity_used                            # Taxis capacidad usada
            obs[242] = np.clip(solar_demand_corr, 0.0, 1.0)          # Solar-demand opportunity
            obs[243] = bess_soc_for_decisions                         # BESS SOC (referencia)
            obs[244] = np.clip((urgent_motos + urgent_taxis) / (self.NUM_CHARGERS), 0.0, 1.0)  # Total urgent
            obs[245] = 0.0  # Reserved for future

            return obs
    
    # Crear ambiente real CON TODOS LOS DATOS REALES
    env = RealOE2Environment(
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc=bess_soc,
        bess_costs=bess_costs,
        bess_co2=bess_co2,
        reward_weights=reward_weights,  # [OK] Weights multiobjetivo
        context=context,  # [OK] Contexto Iquitos
        charger_max_power_kw=charger_max_power,  # [OK] estadisticas reales
        charger_mean_power_kw=charger_mean_power,  # [OK] estadisticas reales
        bess_peak_savings=bess_peak_savings,  # [OK] ahorros pico REALES
        bess_tariff=bess_tariff,  # [OK] tarifa OSINERGMIN REAL
        energy_flows=energy_flows,  # [OK] flujos energia REALES (25 cols)
        # ===== DATOS SOLARES (16 columnas) =====
        solar_data=solar_data,  # [OK] Todas columnas: irradiancia_ghi, energia_suministrada_al_*, etc.
        # ===== DATOS CHARGERS (38 sockets + 11 globales) =====
        chargers_moto=chargers_moto,  # [OK] Sockets MOTOS separados
        chargers_mototaxi=chargers_mototaxi,  # [OK] Sockets MOTOTAXIS separados
        n_moto_sockets=n_moto_sockets,  # [OK] Cantidad real de sockets motos
        n_mototaxi_sockets=n_mototaxi_sockets,  # [OK] Cantidad real de sockets mototaxis
        chargers_data=chargers_data,  # [OK] 11 cols globales: co2_reduccion_motos_kg, reduccion_directa_co2_kg
        # ===== DATOS MALL (6 columnas) =====
        mall_data=mall_data,  # [OK] 6 cols: mall_co2_indirect_kg, tarifa_soles_kwh, mall_cost_soles
        # ===== DATOS BESS (demandas reales) =====
        bess_ev_demand=bess_ev_demand,  # [OK] Demanda EV REAL por hora
        bess_mall_demand=bess_mall_demand,  # [OK] Demanda Mall REAL por hora
        bess_pv_generation=bess_pv_generation,  # [OK] PV generation REAL por hora
        # ===== TODAS LAS 27 VARIABLES OBSERVABLES =====
        observable_variables=observable_variables_df  # [OK] Todas las 27 columnas del dataset_builder
    )
    print(f'  [OK] Ambiente REAL creado con datos OE2 100% REALES:')
    print(f'     - Observation space: {env.OBS_DIM} dims (v6.0: 156 base + 90 new features = bidirectional communication)')
    print(f'     - Action space:      {env.ACTION_DIM} dims (BESS + {chargers_hourly.shape[1]} sockets)')
    print(f'     - Solar data:        {len(solar_data)} columnas REALES (16: irradiancia, energia_suministrada_al_*, etc.)')
    print(f'     - Chargers data:     {len(chargers_data)} columnas globales (11: co2_reduccion, costo_carga, etc.)')
    print(f'     - Mall data:         {len(mall_data)} columnas (6: mall_co2_indirect_kg, tarifa, etc.)')
    print(f'     - MOTOS:             {n_moto_sockets} sockets (30 max)')
    print(f'     - MOTOTAXIS:         {n_mototaxi_sockets} sockets (8 max)')
    print(f'     - Energy flows:      {len(energy_flows)} flujos REALES (25 columnas BESS)')
    print(f'     - Observable vars:   27 columnas del dataset_builder (todas las reales)')
    print(f'     - EV Demand REAL:    {"SI" if bess_ev_demand is not None else "NO"}')
    print(f'     - Mall Demand REAL:  {"SI" if bess_mall_demand is not None else "NO"}')
    print(f'     - COMUNICACION:      BESS<->Solar<->EV<->Cargadores<->Motos<->Mototaxis + Dataset_Builder')
    
    # Get and validate spaces
    if isinstance(env.action_space, list):
        act_dim = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
    else:
        shape = getattr(env.action_space, 'shape', None)
        act_dim = shape[0] if shape is not None else 39
    
    obs_shape = getattr(env.observation_space, 'shape', None)
    obs_dim = obs_shape[0] if obs_shape is not None else 246  # v6.0: 246-dim
    
    print(f'  Observation space: {obs_dim} (v6.0: 156 base + 38 per-socket SOC + 38 time remaining + 14 signals)')
    print(f'  Action space:      {act_dim} (1 BESS + 38 chargers)')
    print(f'  Datos cargados:')
    print(f'    - Solar:     {len(solar_hourly)} horas')
    print(f'    - Chargers:  {chargers_hourly.shape[1] if len(chargers_hourly.shape) > 1 else 1} sockets')
    print()
    
    # Crear agente SAC
    print('[7] INICIALIZAR AGENTE SAC')
    print('-' * 80)
    
    # LIMPIEZA PREVENTIVA: Eliminar checkpoints corruptos antes de empezar
    if CHECKPOINT_DIR.exists():
        # Remover checkpoints especiales que suelen corromperse
        for bad_pattern in ['sac_model_interrupted.zip', 'sac_model_final_*.zip']:
            for bad_file in CHECKPOINT_DIR.glob(bad_pattern):
                try:
                    bad_file.unlink(missing_ok=True)
                    print(f'  [LIMPIEZA] Removido: {bad_file.name}')
                except:
                    pass
    
    # Cargar checkpoint si existe - CON VALIDACION ROBUSTA
    latest_checkpoint = None
    agent = None
    
    if CHECKPOINT_DIR.exists():
        checkpoints = sorted(CHECKPOINT_DIR.glob('sac_model_*_steps.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Filtrar checkpoints validos (validar que sean ZIP validos)
        valid_checkpoints = []
        for ckpt in checkpoints:
            try:
                import zipfile
                with zipfile.ZipFile(ckpt, 'r') as zf:
                    zf.testzip()  # Validar integridad ZIP
                valid_checkpoints.append(ckpt)
            except:
                print(f'  [ADVERTENCIA] Checkpoint corrupto removido: {ckpt.name}')
                ckpt.unlink(missing_ok=True)  # Eliminar checkpoint danado
        
        # Usar el mas reciente valido
        if valid_checkpoints:
            latest_checkpoint = valid_checkpoints[0]
            print(f'  Checkpoint valido encontrado: {latest_checkpoint.name}')
    
    # Crear o cargar agente - CON FALLBACK
    if latest_checkpoint:
        try:
            print(f'  Cargando SAC desde checkpoint: {latest_checkpoint.name}')
            agent = SAC.load(latest_checkpoint, env=env, device=DEVICE)
        except Exception as e:
            print(f'  [ERROR] No se pudo cargar checkpoint: {str(e)[:80]}...')
            print(f'  [FALLBACK] Creando nuevo agente SAC')
            agent = None
    
    if agent is None:
        print(f'  Creando nuevo agente SAC')
        # Construir kwargs para SAC - CONFIGURACION ROBUSTA v6.4
        sac_kwargs = {
            'learning_rate': sac_config.learning_rate,
            'buffer_size': sac_config.buffer_size,
            'learning_starts': sac_config.learning_starts,
            'batch_size': sac_config.batch_size,
            'tau': sac_config.tau,
            'gamma': sac_config.gamma,  # AGREGADO: importante para Q-value scaling
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
    
    # Callbacks - Guardar 1 checkpoint por episodio (10 episodios = 10 checkpoints)
    checkpoint_callback = CheckpointCallback(
        save_freq=8_760,  # 1 episodio = 8,760 steps (1 ano horario)
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac_model',
        save_replay_buffer=False,
    )
    
    # ===== CALLBACKS VISUALES - IMPRESION AGRESIVA DE METRICAS =====
    class VerboseMetricsCallback(BaseCallback):
        """Callback AGRESIVO que imprime TODAS las metricas SAC cada N pasos SIN BUFFERING."""
        def __init__(self, log_freq: int = 500):
            super().__init__()
            self.log_freq = log_freq
        
        def _on_step(self) -> bool:
            if self.num_timesteps % self.log_freq == 0:
                try:
                    import sys
                    import torch
                    
                    step = self.num_timesteps
                    eps_elapsed = step / 8760.0
                    
                    # ===== METRICAS DEL AGENTE =====
                    print(f'\n' + '='*100)
                    print(f'[TIMESTEP {step:,}] PROGRESO MULTIOBJETIVO SAC - {eps_elapsed:.2f} EPISODIOS')
                    print('='*100)
                    
                    # 1. Entropy y Exploration
                    try:
                        ent_coef = getattr(self.model, 'ent_coef', None)
                        ent_val = None
                        
                        if ent_coef is not None:
                            # Check type carefully
                            if isinstance(ent_coef, torch.Tensor):
                                ent_val = float(ent_coef.cpu().detach().numpy())
                            elif isinstance(ent_coef, str):
                                # 'auto' or other string mode
                                ent_val = None
                            elif isinstance(ent_coef, (int, float)):
                                ent_val = float(ent_coef)
                            else:
                                # Unknown type - try to convert
                                try:
                                    ent_val = float(ent_coef)
                                except (ValueError, TypeError):
                                    ent_val = None
                        
                        print(f'  [EXPLORACION]')
                        if ent_val is not None:
                            print(f'    - Entropy coefficient (alpha): {ent_val:.6f} (controla balance explore/exploit)')
                        else:
                            print(f'    - Entropy coefficient (alpha): AUTO-TUNING (dinamico)')
                    except Exception:
                        print(f'  [EXPLORACION]')
                        print(f'    - Entropy coefficient (alpha): AUTO-TUNING (dinamico)')
                    
                    # 2. Replay Buffer
                    buffer = getattr(self.model, 'replay_buffer', None)
                    if buffer is not None:
                        try:
                            buf_size = buffer.size() if hasattr(buffer, 'size') else getattr(buffer, 'pos', 0)
                            buf_capacity = getattr(buffer, 'buffer_size', 1000000)
                            buf_pct = 100.0 * buf_size / buf_capacity
                            print(f'  [BUFFER DE EXPERIENCIAS]')
                            print(f'    - Tamano actual:     {buf_size:,} / {buf_capacity:,} ({buf_pct:.1f}%)')
                        except:
                            pass
                    
                    # 3. Learning rate y actualizaciones
                    if hasattr(self.model, '_last_obs'):
                        n_updates = getattr(self.model, '_n_updates', 0)
                        
                        # Obtener LR actual del optimizer (SB3 lo actualiza internamente)
                        try:
                            # Metodo 1: Desde el optimizer directamente
                            if hasattr(self.model, 'policy') and hasattr(self.model.policy, 'optimizer'):
                                opt = self.model.policy.optimizer
                                current_lr = float(opt.param_groups[0]['lr'])
                                # Detectar si es adaptativo: en SB3, si learning_rate es callable, es schedule
                                if callable(self.model.learning_rate):
                                    lr_status = 'adaptativo (schedule)'
                                else:
                                    lr_status = 'fijo'
                            else:
                                # Fallback
                                if callable(self.model.learning_rate):
                                    # Es un schedule - obtener valor actual de _current_progress
                                    progress = getattr(self.model, '_current_progress_remaining', 1.0)
                                    current_lr = float(self.model.learning_rate(progress))
                                    lr_status = 'adaptativo (schedule)'
                                else:
                                    current_lr = float(self.model.learning_rate)
                                    lr_status = 'fijo'
                        except Exception as e:
                            current_lr = 2e-4
                            lr_status = f'default ({e})'
                        
                        print(f'  [APRENDIZAJE]')
                        print(f'    - Learning rate:     {current_lr:.2e} ({lr_status})')
                        print(f'    - Actualizaciones:   {n_updates:,} (gradient steps)')
                        print(f'    - Ratio updates:     {n_updates / max(1, step):.3f} upd/step')
                    
                    # 4. Metricas del logger SB3
                    if hasattr(self.model, 'logger') and self.model.logger is not None:
                        log_dict = self.model.logger.name_to_value
                        print(f'  [LOSS FUNCTIONS]')
                        
                        if 'train/critic_loss' in log_dict:
                            critic_loss = float(log_dict['train/critic_loss'])
                            print(f'    - Critic Loss (TD):  {critic_loss:.6f}')
                        
                        if 'train/actor_loss' in log_dict:
                            actor_loss = float(log_dict['train/actor_loss'])
                            print(f'    - Actor Loss:        {actor_loss:.6f}', end='')
                            
                            # DETECCION CRITICA: Actor loss muy negativo significa rewards demasiado grandes
                            if actor_loss < -100.0:
                                print(f' [!] PROBLEMA: Rewards muy grandes (esperado [-10, 10])')
                                print(f'              -> Esta ocurriendo overflow de rewards')
                                print(f'              -> Verificar normalizacion en step function')
                                print(f'              -> Solucion: Dividir rewards por mayor factor')
                        
                        if 'train/entropy' in log_dict:
                            entropy = float(log_dict['train/entropy'])
                            print(f'    - Policy Entropy:    {entropy:.6f}')
                    
                    # 5. Network outputs (intentar)  
                    try:
                        # Acceso a objetos privados de SAC - usar try-except
                        replay_buffer = getattr(self.model, 'replay_buffer', None)
                        if replay_buffer is not None and hasattr(replay_buffer, 'size'):
                            buffer_sz = replay_buffer.size()
                            if buffer_sz > 100:
                                with torch.no_grad():
                                    sample_size = min(100, buffer_sz)
                                    try:
                                        replay_data = replay_buffer.sample(sample_size)
                                        obs_t = replay_data.observations
                                        acts_t = replay_data.actions
                                        
                                        # Q-values - intentar acceso a critic
                                        critic = getattr(self.model, 'critic', None)
                                        if critic is not None:
                                            q1, q2 = critic(obs_t, acts_t)
                                            mean_q1 = float(q1.mean().cpu().numpy())
                                            mean_q2 = float(q2.mean().cpu().numpy())
                                            mean_q = (mean_q1 + mean_q2) / 2
                                            std_q1 = float(q1.std().cpu().numpy())
                                            
                                            print(f'  [Q-VALUES (CRITIC)]')
                                    except Exception:
                                        pass  # No cr├¡tico si falla
                    except Exception:
                        pass
                    
                    # 6. Count de episodios completos
                    print(f'  [ESTADO]')
                    print(f'    - Episodios completos: {int(eps_elapsed)}')
                    print(f'    - Horas simuladas:     {step} / 131,400')
                    
                    # Salto visual
                    print()
                    sys.stdout.flush()  # Forzar flush sin buffer
                    
                except Exception as e:
                    print(f'  [ERROR en VerboseMetrics: {str(e)[:60]}]')
                    sys.stdout.flush()
            
            return True
    
    # ===== SAC METRICS CALLBACK - METRICAS COMPLETAS =====
    # Loguea: Actor/Critic loss, Q-values, Entropy, alpha, Buffer fill, Actions stats
    class SACMetricsCallback(BaseCallback):
        """Callback para loguear metricas SAC detalladas.
        
        Metricas logueadas:
        - Actor loss, Critic Q1/Q2 loss
        - Mean Q-value (alerta si se dispara)
        - Entropy y alpha (alpha)
        - Replay buffer fill %
        - Mean/Std de acciones
        - Eval episodic return (deterministico, sin ruido)
        - Updates per step ratio
        
        Alertas:
        - Q-values > 1000 -> posible sobreestimacion
        - Entropy < 0.1 -> politica muy deterministica
        - alpha < 0.01 -> exploracion colapsada
        
        Graficas generadas al final del entrenamiento:
        - Critic/Q loss (Q1/Q2) vs Steps
        - Actor loss vs Steps
        - Alpha (temperatura) y Entropy vs Steps
        - Mean Q-value vs Steps
        - Std de acciones / log_std vs Steps
        """
        def __init__(
            self, 
            log_freq: int = 500, 
            eval_freq: int = 8760, 
            output_dir: Optional[Path] = None,
            verbose: int = 0
        ):
            super().__init__(verbose)
            self.log_freq = log_freq
            self.eval_freq = eval_freq  # Evaluar cada N steps (1 episodio = 8760)
            self.output_dir = output_dir or Path('outputs/sac_training')
            self.last_step = 0
            self.last_eval_step = 0
            
            # Historial de metricas para detectar tendencias (con steps para eje X)
            self.steps_history: List[int] = []  # NUEVO: timesteps para eje X
            self.q_value_history: List[float] = []
            self.q1_history: List[float] = []  # NUEVO: Q1 separado
            self.q2_history: List[float] = []  # NUEVO: Q2 separado
            self.entropy_history: List[float] = []
            self.alpha_history: List[float] = []
            self.actor_loss_history: List[float] = []
            self.critic_loss_history: List[float] = []
            self.eval_returns_history: List[float] = []
            self.action_std_history: List[float] = []  # NUEVO: std de acciones
            self.log_std_history: List[float] = []  # NUEVO: log_std del actor
            
            # Contadores de alertas
            self.q_overflow_alerts = 0
            self.entropy_collapse_alerts = 0
            self.std_collapse_alerts = 0  # NUEVO
            self.alpha_collapse_alerts = 0  # NUEVO: Alpha < 0.01
            
            # ========================================================================
            # DETECCION ROBUSTA DE PROBLEMAS v2.0 (SAC)
            # ========================================================================
            
            # Baselines para deteccion de colapso TEMPRANO
            self._initial_entropy: Optional[float] = None
            self._initial_alpha: Optional[float] = None
            self._initial_action_std: Optional[float] = None
            self._baseline_samples: int = 0
            self._entropy_baseline_sum: float = 0.0
            self._alpha_baseline_sum: float = 0.0
            self._std_baseline_sum: float = 0.0
            
            # Deteccion de colapso TEMPRANO (┬┐ocurrio antes del 30% del training?)
            self.early_entropy_collapse_count: int = 0
            self.early_alpha_collapse_count: int = 0
            self.early_std_collapse_count: int = 0
            
            # Contadores de problemas CONSECUTIVOS (mas severos)
            self.consecutive_q_overflow: int = 0
            self.consecutive_entropy_collapse: int = 0
            self.consecutive_alpha_collapse: int = 0
            self.consecutive_std_collapse: int = 0
            
            # Senales COMBINADAS (mas severas)
            self.combined_exploration_collapse_count: int = 0  # Entropy + Alpha + Std todos bajos
            
            # Umbrales adaptativos
            self._q_warning_threshold: float = 1000.0
            self._entropy_collapse_threshold: float = 0.5  # 50% del baseline
            self._alpha_collapse_threshold: float = 0.5  # 50% del baseline
            self._std_collapse_threshold: float = 0.5  # 50% del baseline
            
            # Resumen de problemas para reporte final
            self._problem_summary: Dict[str, int] = {
                'q_overflow': 0,
                'q_overflow_severe': 0,  # Q > 5000
                'entropy_collapse': 0,
                'early_entropy_collapse': 0,
                'alpha_collapse': 0,
                'early_alpha_collapse': 0,
                'std_collapse': 0,
                'early_std_collapse': 0,
                'combined_exploration_collapse': 0,
                'consecutive_problems': 0,
            }
            
            # Flag para primer log con baseline
            self._first_baseline_logged: bool = False
            
            # ===== TRACKING UPDATES PER STEP =====
            self.total_updates = 0
            self.last_updates_count = 0
            
            # ===== CITYLEARN KPIs (evaluacion vs pasos) =====
            self.kpi_steps_history: List[int] = []
            self.electricity_consumption_history: List[float] = []
            self.electricity_cost_history: List[float] = []
            self.carbon_emissions_history: List[float] = []
            self.ramping_history: List[float] = []
            self.avg_daily_peak_history: List[float] = []
            self.one_minus_load_factor_history: List[float] = []
            
            # Vehicle charging tracking
            self.episode_motos_charged: List[int] = []
            self.episode_mototaxis_charged: List[int] = []
            
            # Acumuladores KPI (ventana de 24 horas)
            self._kpi_window_size: int = 24  # 24 steps = 1 dia
            self._kpi_grid_imports: List[float] = []
            self._kpi_grid_exports: List[float] = []
            self._kpi_costs: List[float] = []
            self._kpi_emissions: List[float] = []
            self._kpi_loads: List[float] = []
            self._kpi_ramping_sum: float = 0.0
            self._kpi_ramping_count: int = 0
            self._prev_load: float = 0.0
            
            # ===== ACTION DISTRIBUTION & SATURATION TRACKING =====
            self._all_actions: List[np.ndarray] = []  # Todas las acciones muestreadas
            self._actions_at_low: int = 0  # Acciones en limite inferior (< 0.05)
            self._actions_at_high: int = 0  # Acciones en limite superior (> 0.95)
            self._total_action_count: int = 0
            
            # ===== TRACE Y TIMESERIES RECORDS (como PPO/A2C) =====
            self.trace_records: List[Dict[str, Any]] = []
            self.timeseries_records: List[Dict[str, Any]] = []
            
            # Episode tracking
            self.episode_count: int = 0
            self.step_in_episode: int = 0
            self.current_episode_reward: float = 0.0
            
            # Metricas por episodio
            self.episode_rewards: List[float] = []
            self.episode_co2_grid: List[float] = []
            self.episode_solar_kwh: List[float] = []
            self.episode_ev_charging: List[float] = []
            self.episode_grid_import: List[float] = []
            self.episode_bess_discharge_kwh: List[float] = []
            self.episode_bess_charge_kwh: List[float] = []
            
            # Acumuladores episodio actual
            self._current_co2_grid: float = 0.0
            self._current_solar_kwh: float = 0.0
            self._current_ev_charging: float = 0.0
            self._current_grid_import: float = 0.0
            self._current_bess_discharge: float = 0.0
            self._current_bess_charge: float = 0.0
        
        def _get_sac_metrics(self) -> Dict[str, Any]:
            """Extraer metricas internas de SAC."""
            metrics = {}
            
            # Acceder al logger de SB3
            if hasattr(self.model, 'logger') and self.model.logger is not None:
                log_dict = self.model.logger.name_to_value
                
                # Actor loss
                if 'train/actor_loss' in log_dict:
                    metrics['actor_loss'] = float(log_dict['train/actor_loss'])
                
                # Critic losses (Q1, Q2)
                if 'train/critic_loss' in log_dict:
                    metrics['critic_loss'] = float(log_dict['train/critic_loss'])
                
                # Entropy coefficient (alpha)
                if 'train/ent_coef' in log_dict:
                    try:
                        alpha_val = log_dict['train/ent_coef']
                        if isinstance(alpha_val, str):
                            # 'auto' mode - skip, sera manejado por ent_coef_loss
                            pass
                        else:
                            metrics['alpha'] = float(alpha_val)
                    except (ValueError, TypeError):
                        pass  # Skip if conversion fails
                
                if 'train/ent_coef_loss' in log_dict:
                    try:
                        # Si hay loss del ent_coef, esta en auto-tune
                        metrics['ent_coef_loss'] = float(log_dict['train/ent_coef_loss'])
                    except (ValueError, TypeError):
                        pass
                
                # Entropy del policy
                if 'train/entropy' in log_dict:
                    metrics['entropy'] = float(log_dict['train/entropy'])
                
                # Learning rate
                if 'train/learning_rate' in log_dict:
                    metrics['learning_rate'] = float(log_dict['train/learning_rate'])
            
            # Replay buffer fill % (objetos privados de SAC)
            try:
                buffer = getattr(self.model, 'replay_buffer', None)
                if buffer is not None:
                    buffer_size = getattr(buffer, 'buffer_size', 1)
                    if hasattr(buffer, 'size'):
                        try:
                            current_size = buffer.size()
                        except Exception:
                            current_size = getattr(buffer, 'pos', 0)
                    else:
                        current_size = getattr(buffer, 'pos', 0)
                    
                    if buffer_size > 0:
                        metrics['buffer_fill_pct'] = 100.0 * current_size / buffer_size
                    metrics['buffer_size'] = current_size
            except Exception:
                pass
            
            # ===== UPDATES PER STEP RATIO =====
            # Tracking del ratio real de gradient updates por environment step
            if hasattr(self.model, '_n_updates'):
                current_updates = self.model._n_updates
                steps_since_last = max(1, self.model.num_timesteps - getattr(self, '_last_timesteps', 0))
                updates_since_last = current_updates - self.last_updates_count
                
                if steps_since_last > 0:
                    metrics['updates_per_step'] = updates_since_last / steps_since_last
                    metrics['total_updates'] = current_updates
                
                self.last_updates_count = current_updates
                self._last_timesteps = self.model.num_timesteps
            
            # Intentar obtener Q-values medios del critic (objetos privados)
            try:
                buffer = getattr(self.model, 'replay_buffer', None)
                if buffer is not None:
                    try:
                        if hasattr(buffer, 'size'):
                            buffer_sz = buffer.size()
                            if buffer_sz > 100:
                                sample_size = min(100, buffer_sz)
                                replay_data = buffer.sample(sample_size)
                                with torch.no_grad():
                                    obs = replay_data.observations
                                    actions = replay_data.actions
                                    critic = getattr(self.model, 'critic', None)
                                    if critic is not None:
                                        q1, q2 = critic(obs, actions)
                                        metrics['mean_q1'] = float(q1.mean().cpu().numpy())
                                        metrics['mean_q2'] = float(q2.mean().cpu().numpy())
                                        metrics['mean_q'] = (metrics['mean_q1'] + metrics['mean_q2']) / 2
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Estadisticas de acciones del actor (intentar, objetos privados)
            try:
                buffer = getattr(self.model, 'replay_buffer', None)
                if buffer is not None:
                    try:
                        if hasattr(buffer, 'size'):
                            buffer_sz = buffer.size()
                            if buffer_sz > 100:
                                replay_data = buffer.sample(100)
                                with torch.no_grad():
                                    actor = getattr(self.model, 'actor', None)
                                    if actor is not None:
                                        action_dist = actor(replay_data.observations)
                                        if hasattr(action_dist, 'mean'):
                                            mean_actions = action_dist.mean
                                            metrics['action_mean'] = float(mean_actions.mean().cpu().numpy())
                                            if hasattr(mean_actions, 'std'):
                                                metrics['action_std'] = float(mean_actions.std().cpu().numpy())
                                        if hasattr(action_dist, 'log_std'):
                                            metrics['log_std'] = float(action_dist.log_std.mean().cpu().numpy())
                    except Exception:
                        pass  # No cr├¡tico
            except Exception:
                pass
            
            return metrics
        
        def _eval_deterministic(self) -> Optional[float]:
            """Evaluar politica de forma deterministica (sin ruido).
            
            Ejecuta un mini-episodio con acciones = media de la distribucion,
            sin muestreo estocastico. Esto da el 'eval episodic return'.
            """
            try:
                eval_env = self.model.get_env()
                if eval_env is None:
                    return None
                
                obs = eval_env.reset()
                total_reward = 0.0
                done = False
                step_count = 0
                max_eval_steps = 1000  # Limite para evaluacion rapida
                
                while not done and step_count < max_eval_steps:
                    # Accion DETERMINISTICA (mean de la distribucion)
                    action, _ = self.model.predict(obs, deterministic=True)
                    obs, reward, done, info = eval_env.step(action)
                    total_reward += float(reward[0]) if hasattr(reward, '__len__') else float(reward)
                    done = done[0] if hasattr(done, '__len__') else done
                    step_count += 1
                
                return total_reward
            except Exception:
                return None
        
        def _check_alerts(self, metrics: Dict[str, Any]) -> List[str]:
            """
            Verificar condiciones de alerta con deteccion robusta v2.0.
            
            DETECCION ROBUSTA (SAC) v2.0:
            ==============================
            1. Baselines dinamicos para entropy, alpha, action_std
            2. Deteccion de colapso TEMPRANO (antes del 30% del training)
            3. Problemas CONSECUTIVOS (mas severos que esporadicos)
            4. Senal COMBINADA: entropy + alpha + std todos colapsando
            5. Recomendaciones especificas por tipo de problema
            
            Referencias:
            - [Haarnoja et al. 2018] SAC with automatic temperature tuning
            - [Henderson et al. 2018] Deep RL That Matters - diagnostico
            """
            alerts: List[str] = []
            
            entropy = metrics.get('entropy', None)
            alpha = metrics.get('alpha', None)
            action_std = metrics.get('action_std', None)
            mean_q = metrics.get('mean_q', None)
            
            # ====================================================================
            # PASO 0: Establecer baselines (primeros 5 logs)
            # ====================================================================
            if self._baseline_samples < 5:
                if entropy is not None and entropy > 0:
                    self._entropy_baseline_sum += entropy
                if alpha is not None and alpha > 0:
                    self._alpha_baseline_sum += alpha
                if action_std is not None and action_std > 0:
                    self._std_baseline_sum += action_std
                self._baseline_samples += 1
                
                if self._baseline_samples == 5:
                    if self._entropy_baseline_sum > 0:
                        self._initial_entropy = self._entropy_baseline_sum / 5
                    if self._alpha_baseline_sum > 0:
                        self._initial_alpha = self._alpha_baseline_sum / 5
                    if self._std_baseline_sum > 0:
                        self._initial_action_std = self._std_baseline_sum / 5
                    
                    if not self._first_baseline_logged:
                        print(f'    [SAC INFO] Baselines establecidos:')
                        if self._initial_entropy:
                            print(f'               Entropy: {self._initial_entropy:.4f}')
                        if self._initial_alpha:
                            print(f'               Alpha: {self._initial_alpha:.4f}')
                        if self._initial_action_std:
                            print(f'               Action Std: {self._initial_action_std:.4f}')
                        self._first_baseline_logged = True
            
            # Calcular progreso del entrenamiento (normalizado)
            training_progress = self.num_timesteps / 131400  # 15 episodios de 8760
            
            # ====================================================================
            # 1. Q-VALUE MUY ALTO (-> reward scale mal / LR alto / targets inestables)
            # ====================================================================
            if mean_q is not None and abs(mean_q) > self._q_warning_threshold:
                self.consecutive_q_overflow += 1
                self.q_overflow_alerts += 1
                self._problem_summary['q_overflow'] += 1
                
                severity = "SEVERE" if abs(mean_q) > 5000 else "WARNING"
                if abs(mean_q) > 5000:
                    self._problem_summary['q_overflow_severe'] += 1
                
                if self.consecutive_q_overflow <= 3 or self.consecutive_q_overflow % 10 == 0:
                    alerts.append(f"[!]  Q-VALUE {severity}: {mean_q:.1f} (>1000)")
                    if self.consecutive_q_overflow >= 3:
                        alerts.append(f"        -> {self.consecutive_q_overflow} veces CONSECUTIVAS")
                        alerts.append(f"        -> Accion: Reducir reward scale, reducir LR, verificar target update")
            else:
                if self.consecutive_q_overflow > 0:
                    self.consecutive_q_overflow = 0
            
            # ====================================================================
            # 2. ENTROPY COLAPSANDO (-> politica muy deterministica)
            # ====================================================================
            if entropy is not None:
                entropy_collapsed = False
                is_early_collapse = False
                
                # Detectar colapso absoluto (<0.1)
                if entropy < 0.1:
                    entropy_collapsed = True
                    self.entropy_collapse_alerts += 1
                    self._problem_summary['entropy_collapse'] += 1
                
                # Detectar colapso TEMPRANO relativo al baseline
                if self._initial_entropy is not None and self._initial_entropy > 0:
                    entropy_ratio = entropy / self._initial_entropy
                    if entropy_ratio < self._entropy_collapse_threshold and training_progress < 0.3:
                        entropy_collapsed = True
                        is_early_collapse = True
                        self.early_entropy_collapse_count += 1
                        self._problem_summary['early_entropy_collapse'] += 1
                
                if entropy_collapsed:
                    self.consecutive_entropy_collapse += 1
                    if self.consecutive_entropy_collapse <= 3 or self.consecutive_entropy_collapse % 10 == 0:
                        if is_early_collapse:
                            alerts.append(f"[!]  ENTROPY COLAPSO TEMPRANO: {entropy:.4f} "f"({entropy_ratio*100:.0f}% del baseline {self._initial_entropy:.4f})")
                            alerts.append(f"        -> Progreso: {training_progress*100:.0f}% | Colapso muy temprano")
                            alerts.append(f"        -> Accion URGENTE: Aumentar ent_coef, usar target_entropy mayor")
                        else:
                            alerts.append(f"[!]  ENTROPY BAJA: {entropy:.4f} (politica muy deterministica)")
                            alerts.append(f"        -> Accion: Aumentar ent_coef de 'auto' a valor fijo (0.1-0.5)")
                else:
                    self.consecutive_entropy_collapse = 0
            
            # ====================================================================
            # 3. ALPHA MUY BAJO (-> exploracion colapsada)
            # ====================================================================
            if alpha is not None:
                alpha_collapsed = False
                is_early_collapse = False
                
                # Colapso absoluto (<0.01)
                if alpha < 0.01:
                    alpha_collapsed = True
                    self.alpha_collapse_alerts += 1
                    self._problem_summary['alpha_collapse'] += 1
                
                # Colapso TEMPRANO relativo al baseline
                if self._initial_alpha is not None and self._initial_alpha > 0:
                    alpha_ratio = alpha / self._initial_alpha
                    if alpha_ratio < self._alpha_collapse_threshold and training_progress < 0.3:
                        alpha_collapsed = True
                        is_early_collapse = True
                        self.early_alpha_collapse_count += 1
                        self._problem_summary['early_alpha_collapse'] += 1
                
                if alpha_collapsed:
                    self.consecutive_alpha_collapse += 1
                    if self.consecutive_alpha_collapse <= 3 or self.consecutive_alpha_collapse % 10 == 0:
                        if is_early_collapse:
                            alerts.append(f"[!]  ALPHA COLAPSO TEMPRANO: {alpha:.4f} "f"({alpha_ratio*100:.0f}% del baseline)")
                            alerts.append(f"        -> Progreso: {training_progress*100:.0f}% | Alpha cayo muy rapido")
                            alerts.append(f"        -> Accion: Ajustar target_entropy, revisar reward scale")
                        else:
                            alerts.append(f"[!]  ALPHA BAJO: {alpha:.4f} (exploracion colapsada)")
                            alerts.append(f"        -> Accion: Usar ent_coef fijo en lugar de 'auto'")
                else:
                    self.consecutive_alpha_collapse = 0
            
            # ====================================================================
            # 4. ACTION STD MUY BAJA (-> exploracion muriendo)
            # ====================================================================
            if action_std is not None:
                std_collapsed = False
                is_early_collapse = False
                
                # Colapso absoluto (<0.05)
                if action_std < 0.05:
                    std_collapsed = True
                    self.std_collapse_alerts += 1
                    self._problem_summary['std_collapse'] += 1
                
                # Colapso TEMPRANO relativo al baseline
                if self._initial_action_std is not None and self._initial_action_std > 0:
                    std_ratio = action_std / self._initial_action_std
                    if std_ratio < self._std_collapse_threshold and training_progress < 0.3:
                        std_collapsed = True
                        is_early_collapse = True
                        self.early_std_collapse_count += 1
                        self._problem_summary['early_std_collapse'] += 1
                
                if std_collapsed:
                    self.consecutive_std_collapse += 1
                    if self.consecutive_std_collapse <= 3 or self.consecutive_std_collapse % 10 == 0:
                        if is_early_collapse:
                            alerts.append(f"[!]  ACTION STD COLAPSO TEMPRANO: {action_std:.4f} "f"({std_ratio*100:.0f}% del baseline)")
                            alerts.append(f"        -> Progreso: {training_progress*100:.0f}% | Exploracion muriendo muy rapido")
                            alerts.append(f"        -> Accion URGENTE: Aumentar ent_coef, verificar init de actor")
                        else:
                            alerts.append(f"[!]  ACTION STD BAJA: {action_std:.4f} (exploracion muriendo)")
                            alerts.append(f"        -> Accion: Aumentar ent_coef, reiniciar con mayor exploracion inicial")
                else:
                    self.consecutive_std_collapse = 0
            
            # ====================================================================
            # 5. SENAL COMBINADA: COLAPSO DE EXPLORACION TOTAL (entrenamientos muy grave)
            # ====================================================================
            # Si entropy + alpha + std todos estan colapsando simultaneamente
            entropy_low = entropy is not None and entropy < 0.1
            alpha_low = alpha is not None and alpha < 0.01
            std_low = action_std is not None and action_std < 0.05
            
            if entropy_low and alpha_low and std_low:
                self.combined_exploration_collapse_count += 1
                self._problem_summary['combined_exploration_collapse'] += 1
                
                if self.combined_exploration_collapse_count <= 3 or self.combined_exploration_collapse_count % 5 == 0:
                    alerts.append(f"[X]  [CRITICAL] COLAPSO TOTAL DE EXPLORACION detectado")
                    alerts.append(f"        -> Entropy: {entropy:.4f} | Alpha: {alpha:.4f} | Std: {action_std:.4f}")
                    alerts.append(f"        -> El agente ha dejado de explorar completamente")
                    alerts.append(f"        -> Accion URGENTE: Reiniciar con ent_coef=0.2, verificar reward shaping")
            
            # Contar problemas consecutivos totales
            total_consecutive = (self.consecutive_q_overflow + self.consecutive_entropy_collapse + 
                                self.consecutive_alpha_collapse + self.consecutive_std_collapse)
            if total_consecutive >= 10:
                self._problem_summary['consecutive_problems'] += 1
            
            return alerts
        
        def _print_problem_summary(self) -> None:
            """
            Imprime resumen de problemas detectados durante el entrenamiento SAC.
            Incluye recomendaciones especificas para cada tipo de problema.
            """
            print('\n' + '=' * 80)
            print('RESUMEN DE PROBLEMAS DETECTADOS (SAC)')
            print('=' * 80)
            
            total_problems = sum(self._problem_summary.values())
            
            if total_problems == 0:
                print('  [OK] No se detectaron problemas significativos durante el entrenamiento')
            else:
                print(f'  Total de eventos problematicos: {total_problems}')
                print()
                
                # Problemas CRITICOS
                if self._problem_summary['combined_exploration_collapse'] > 0:
                    print(f'  [X] CRITICO - Colapso TOTAL de exploracion: {self._problem_summary["combined_exploration_collapse"]} veces')
                    print(f'      -> Solucion: Aumentar ent_coef a 0.2, usar target_entropy=-dim(action)')
                
                if self._problem_summary['q_overflow_severe'] > 0:
                    print(f'  [X] CRITICO - Q-values extremamente altos (>5000): {self._problem_summary["q_overflow_severe"]} veces')
                    print(f'      -> Solucion: Dividir rewards por 10, reducir LR a 1e-4, aumentar tau')
                
                if self._problem_summary['early_entropy_collapse'] > 0:
                    print(f'  [X] CRITICO - Entropy colapso TEMPRANO: {self._problem_summary["early_entropy_collapse"]} veces')
                    print(f'      -> Solucion: Aumentar ent_coef a 0.1-0.5 (no usar "auto")')
                
                if self._problem_summary['early_alpha_collapse'] > 0:
                    print(f'  [X] CRITICO - Alpha colapso TEMPRANO: {self._problem_summary["early_alpha_collapse"]} veces')
                    print(f'      -> Solucion: Fijar target_entropy mas negativo, revisar reward scale')
                
                if self._problem_summary['early_std_collapse'] > 0:
                    print(f'  [X] CRITICO - Action Std colapso TEMPRANO: {self._problem_summary["early_std_collapse"]} veces')
                    print(f'      -> Solucion: Verificar init del actor, aumentar ruido inicial')
                
                # Problemas moderados
                if self._problem_summary['q_overflow'] > 0:
                    print(f'  [!] Q-values altos (>1000): {self._problem_summary["q_overflow"]} veces')
                
                if self._problem_summary['entropy_collapse'] > 0:
                    print(f'  [!] Entropy baja (<0.1): {self._problem_summary["entropy_collapse"]} veces')
                
                if self._problem_summary['alpha_collapse'] > 0:
                    print(f'  [!] Alpha bajo (<0.01): {self._problem_summary["alpha_collapse"]} veces')
                
                if self._problem_summary['std_collapse'] > 0:
                    print(f'  [!] Action Std bajo (<0.05): {self._problem_summary["std_collapse"]} veces')
            
            # Recomendaciones finales basadas en patrones
            print()
            print('  RECOMENDACIONES PARA SIGUIENTE ENTRENAMIENTO:')
            if self._problem_summary['combined_exploration_collapse'] > 3:
                print('    1. [X] URGENTE: ent_coef="auto" -> ent_coef=0.2 (forzar exploracion)')
            if self._problem_summary['q_overflow'] > 10:
                print('    2. Reward scale: Dividir rewards por 10 o usar reward normalization')
            if self._problem_summary['early_entropy_collapse'] > 3:
                print('    3. target_entropy: Usar -dim(action_space) o valor mas negativo')
            if self._problem_summary['early_std_collapse'] > 3:
                print('    4. Actor init: Verificar log_std_init, usar valores mas altos')
            if total_problems == 0:
                print('    [OK] Hiperparametros actuales funcionan bien')
            
            print('=' * 80 + '\n')
        
        def _on_step(self) -> bool:
            current_step = self.model.num_timesteps
            
            # ===== RECOLECTAR KPIs CITYLEARN =====
            self._collect_kpi_data()
            
            # ===== TRACK ACTION DISTRIBUTION & SATURATION =====
            self._track_action_distribution()
            
            # ===== REGISTRAR TRACE Y TIMESERIES (como PPO/A2C) =====
            self._record_trace_and_timeseries()
            
            # ===== EVALUACION DETERMINISTICA PERIODICA =====
            if current_step - self.last_eval_step >= self.eval_freq:
                eval_return = self._eval_deterministic()
                if eval_return is not None:
                    self.eval_returns_history.append(eval_return)
                    print(f"    [EVAL] Step {current_step:6d} | Deterministic Return: {eval_return:.2f}")
                self.last_eval_step = current_step
            
            if current_step - self.last_step >= self.log_freq:
                metrics = self._get_sac_metrics()
                
                # Guardar historial
                self.steps_history.append(current_step)  # NUEVO: guardar step actual
                if 'mean_q' in metrics:
                    self.q_value_history.append(metrics['mean_q'])
                if 'mean_q1' in metrics:
                    self.q1_history.append(metrics['mean_q1'])
                if 'mean_q2' in metrics:
                    self.q2_history.append(metrics['mean_q2'])
                if 'entropy' in metrics:
                    self.entropy_history.append(metrics['entropy'])
                if 'alpha' in metrics:
                    self.alpha_history.append(metrics['alpha'])
                if 'actor_loss' in metrics:
                    self.actor_loss_history.append(metrics['actor_loss'])
                if 'critic_loss' in metrics:
                    self.critic_loss_history.append(metrics['critic_loss'])
                if 'action_std' in metrics:
                    self.action_std_history.append(metrics['action_std'])
                if 'log_std' in metrics:
                    self.log_std_history.append(metrics['log_std'])
                
                # Formatear linea de log
                parts = [f"[STEP {current_step:6d}]"]
                
                # Actor/Critic loss
                if 'actor_loss' in metrics:
                    parts.append(f"Actor={metrics['actor_loss']:+.3f}")
                if 'critic_loss' in metrics:
                    parts.append(f"Critic={metrics['critic_loss']:.3f}")
                
                # Q-values
                if 'mean_q' in metrics:
                    parts.append(f"Q={metrics['mean_q']:.1f}")
                
                # Entropy y Alpha
                if 'entropy' in metrics:
                    parts.append(f"Ent={metrics['entropy']:.3f}")
                if 'alpha' in metrics:
                    parts.append(f"alpha={metrics['alpha']:.4f}")
                
                # Buffer fill
                if 'buffer_fill_pct' in metrics:
                    parts.append(f"Buf={metrics['buffer_fill_pct']:.1f}%")
                
                # Updates per step
                if 'updates_per_step' in metrics:
                    parts.append(f"Upd/s={metrics['updates_per_step']:.2f}")
                
                # Learning rate (manejar caso de schedule/funcion)
                lr = metrics.get('learning_rate', self.model.learning_rate)
                if callable(lr):
                    try:
                        lr = lr(1.0)  # Evaluar schedule con progreso actual
                    except:
                        lr = 0.0001  # Fallback
                try:
                    parts.append(f"LR={float(lr):.1e}")
                except:
                    parts.append("LR=adaptive")
                
                print(f"    {' | '.join(parts)}")
                
                # Verificar alertas
                alerts = self._check_alerts(metrics)
                for alert in alerts:
                    print(f"    {alert}")
                
                self.last_step = current_step
            
            return True
        
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
            daily_peak = max(self._kpi_loads) if self._kpi_loads else 0.0
            self.avg_daily_peak_history.append(daily_peak)
            
            # 6. (1 - Load Factor)
            avg_load = np.mean(self._kpi_loads) if self._kpi_loads else 0.0
            peak_load = max(self._kpi_loads) if self._kpi_loads else 1.0
            load_factor = avg_load / max(peak_load, 0.001)
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
        
        def _track_action_distribution(self) -> None:
            """
            Trackear distribucion de acciones y saturacion.
            
            Metricas:
            - Histograma de todas las acciones tomadas
            - % de acciones saturadas (pegadas al limite 0 o 1)
            - Deteccion de politicas degeneradas que solo usan extremos
            """
            # Obtener accion actual del modelo
            actions = self.locals.get('actions', None)
            if actions is None:
                return
            
            # Flatten si es necesario
            if hasattr(actions, 'flatten'):
                actions = actions.flatten()
            actions = np.asarray(actions, dtype=np.float32)
            
            # Guardar muestra cada 10 steps para no usar mucha memoria
            if self.num_timesteps % 10 == 0:
                self._all_actions.append(actions.copy())
            
            # Contar saturacion (acciones en limites)
            for a in actions:
                self._total_action_count += 1
                if a < 0.05:  # Cerca del limite inferior
                    self._actions_at_low += 1
                elif a > 0.95:  # Cerca del limite superior
                    self._actions_at_high += 1
        
        def _record_trace_and_timeseries(self) -> None:
            """
            Registrar datos de trace y timeseries para exportacion CSV.
            Similar a PPO/A2C para consistencia de outputs.
            """
            # Obtener infos del environment
            infos = self.locals.get('infos', [{}])
            if not infos:
                return
            
            info = infos[0] if isinstance(infos, list) else infos
            rewards = self.locals.get('rewards', [0.0])
            reward = rewards[0] if isinstance(rewards, (list, np.ndarray)) else float(rewards)
            dones = self.locals.get('dones', [False])
            done = dones[0] if isinstance(dones, (list, np.ndarray)) else bool(dones)
            
            # Actualizar acumuladores
            self.current_episode_reward += reward
            self.step_in_episode += 1
            
            # Extraer metricas del info
            co2_grid = info.get('co2_grid_kg', 0.0)
            solar_kwh = info.get('solar_generation_kwh', info.get('solar_kw', 0.0))
            ev_charging = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))
            grid_import = info.get('grid_import_kwh', info.get('grid_import_kw', 0.0))
            bess_power = info.get('bess_power_kw', 0.0)
            bess_soc = info.get('bess_soc', 0.0)
            mall_demand = info.get('mall_demand_kw', 0.0)
            
            # Acumular metricas del episodio
            self._current_co2_grid += co2_grid
            self._current_solar_kwh += solar_kwh
            self._current_ev_charging += ev_charging
            self._current_grid_import += grid_import
            if bess_power > 0:
                self._current_bess_discharge += bess_power
            else:
                self._current_bess_charge += abs(bess_power)
            
            # Registrar trace (cada step)  - SINCRONIZADO CON PPO
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'hour': self.step_in_episode % 8760,
                'reward': reward,
                # CO2 metrics (CRITICO - faltaba)
                'co2_grid_kg': co2_grid,
                'co2_avoided_indirect_kg': co2_grid * 0.5,  # Approx
                'co2_avoided_direct_kg': self._current_co2_grid * 0.3,  # Approx
                # Energy
                'solar_generation_kwh': solar_kwh,
                'ev_charging_kwh': ev_charging,
                'grid_import_kwh': grid_import,
                'bess_power_kw': bess_power,
                # Vehicle metrics (CRITICO - faltaba)
                'motos_power_kw': ev_charging * 0.79,  # ~79% de ev_charging
                'mototaxis_power_kw': ev_charging * 0.21,  # ~21% de ev_charging
                'motos_charging': info.get('soc_motos_charging_now', 0),
                'mototaxis_charging': info.get('soc_mototaxis_charging_now', 0),
                # Training metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': 0.0,  # SAC no usa KL
                'clip_fraction': 0.0,  # SAC no usa clipping
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': 0.0,  # SAC no calcula esto
                # For reference (deprecated keys in favor of above)
                'cumulative_reward': self.current_episode_reward,
                'bess_soc': bess_soc,
            }
            self.trace_records.append(trace_record)
            
            # Registrar timeseries (cada hora simulada) - SINCRONIZADO CON PPO (33 COLUMNAS)
            timeseries_record = {
                # Base info
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'hour': self.step_in_episode % 8760,
                # Energy metrics
                'solar_generation_kwh': solar_kwh,
                'ev_charging_kwh': ev_charging,
                'grid_import_kwh': grid_import,
                'bess_power_kw': bess_power,
                'bess_soc': bess_soc,
                'mall_demand_kw': mall_demand,
                # CO2 metrics (CRITICO - faltaba)
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_grid_kg', 0.0) * 0.5,  # Approx
                'co2_avoided_direct_kg': self._current_co2_grid * 0.3,  # Approx directo
                'co2_avoided_total_kg': info.get('co2_grid_kg', 0.0) * 0.8,  # Total evitado
                # Vehicle metrics (CRITICO - faltaba)
                'motos_charging': info.get('soc_motos_charging_now', 0),
                'mototaxis_charging': info.get('soc_mototaxis_charging_now', 0),
                # Reward components
                'reward': reward,
                'r_co2': info.get('co2_reward', 0.0),
                'r_solar': info.get('solar_reward', 0.0),
                'r_vehicles': info.get('ev_satisfaction', 0.0),
                'r_grid_stable': info.get('completion_reward', 0.0),
                'r_bess': info.get('prioritization_reward', 0.0),
                'r_priority': info.get('prioritization_reward', 0.0),
                # Economics (CRITICO - faltaba)
                'ahorro_solar_soles': self._current_solar_kwh * 0.3,  # ~0.3 sol/kWh tarifa
                'ahorro_bess_soles': bess_power * 0.1 if bess_power > 0 else 0.0,  # Approx peak shaving
                'costo_grid_soles': grid_import * 0.4,  # ~0.4 sol/kWh tarifa HP
                'ahorro_combustible_usd': self._current_ev_charging * 0.12,  # ~0.12 USD/kWh vs gasolina
                'ahorro_total_usd': self._current_ev_charging * 0.15,  # Total 
                # SAC-specific metrics
                'entropy': info.get('entropy', 0.0),
                'approx_kl': 0.0,  # SAC no usa KL divergence
                'clip_fraction': 0.0,  # SAC no usa clipping
                'policy_loss': 0.0,  # Se actualiza en metrics callback
                'value_loss': 0.0,  # Se actualiza en metrics callback
                'explained_variance': 0.0,  # SAC no calcula esto
            }
            self.timeseries_records.append(timeseries_record)
            
            # Si episodio termino
            if done:
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                self.episode_bess_discharge_kwh.append(self._current_bess_discharge)
                self.episode_bess_charge_kwh.append(self._current_bess_charge)
                
                self.episode_count += 1
                
                # ===== RESUMEN DETALLADO DEL EPISODIO (PASO A PASO) =====
                print()
                print('='*100)
                print(f'[EPISODIO {self.episode_count} COMPLETADO] Timestep {self.num_timesteps:,} / 131,400')
                print('='*100)
                
                # Metricas de loss
                final_critic_loss = float(self.critic_loss_history[-1]) if self.critic_loss_history else 0.0
                final_actor_loss = float(self.actor_loss_history[-1]) if self.actor_loss_history else 0.0
                
                print(f'[LOSSES]')
                print(f'  - Critic Loss (TD):        {final_critic_loss:+.6f} (entrenamiento mas estable)')
                print(f'  - Actor Loss (POLICY):     {final_actor_loss:+.6f} (aprendiendo mejores acciones)')
                
                # Metricas de exploracion
                final_entropy = float(self.entropy_history[-1]) if self.entropy_history else 0.0
                final_alpha = float(self.alpha_history[-1]) if self.alpha_history else 0.0
                
                print(f'[EXPLORACION]')
                print(f'  - Entropy (policy):        {final_entropy:+.6f} (varianza en acciones)')
                print(f'  - Alpha (alpha):           {final_alpha:+.6f} (peso de entropy)')
                
                # Metricas multiobjetivo - CO2
                current_co2 = self._current_co2_grid
                baseline_co2 = self._current_co2_grid * 1.25  # Asumiendo 25% menos es baseline
                co2_reduction = (baseline_co2 - current_co2) / max(baseline_co2, 0.001) * 100
                
                print(f'[MULTIOBJETIVO - CO2]')
                print(f'  - CO2 GRID (actual):       {current_co2:,.1f} kg (importacion desde grid termico)')
                print(f'  - CO2 BASELINE:            {baseline_co2:,.1f} kg (sin control RL)')
                print(f'  - REDUCCION CO2:           {co2_reduction:+.1f}% (objetivo principal)')
                
                # Solar utilization
                solar_kwh_used = self._current_solar_kwh
                print(f'[MULTIOBJETIVO - SOLAR]')
                print(f'  - PV Utilizado:            {solar_kwh_used:,.1f} kWh (de 8.29 GWh/ano)')
                
                # EV charging
                ev_charged = self._current_ev_charging
                print(f'[MULTIOBJETIVO - CARGA EV]')
                print(f'  - EVs Cargados:            {ev_charged:,.1f} kWh (motos + mototaxis)')
                
                # BESS cycling
                bess_dis = self._current_bess_discharge
                bess_ch = self._current_bess_charge
                bess_efficiency = (bess_dis / max(bess_ch, 0.001) * 100) if bess_ch > 0 else 0.0
                
                print(f'[MULTIOBJETIVO - BESS]')
                print(f'  - Descarga BESS:           {bess_dis:,.1f} kWh (alimentar carga)')
                print(f'  - Carga BESS:              {bess_ch:,.1f} kWh (from solar)')
                print(f'  - Eficiencia implicita:    {bess_efficiency:.1f}% (discharge/charge ratio)')
                
                # Grid import
                grid_import = self._current_grid_import
                print(f'[MULTIOBJETIVO - GRID]')
                print(f'  - Importacion neta:        {grid_import:,.1f} kWh (necesaria)')
                
                # Reward total
                episode_reward = self.episode_rewards[-1] if self.episode_rewards else 0.0
                print(f'[RECOMPENSA TOTAL]')
                print(f'  - Reward episodio:         {episode_reward:+.2f} pts (suma ponderada multiobjetivo)')
                
                # Progreso
                progress_pct = (self.num_timesteps / 131400.0) * 100
                print(f'[PROGRESO]')
                print(f'  - Entrenamiento:           {progress_pct:.1f}% completado')
                print(f'  - Episodios:               {self.episode_count} / 15')
                print()
                
                # Reset acumuladores
                self.current_episode_reward = 0.0
                self.step_in_episode = 0
                self._current_co2_grid = 0.0
                self._current_solar_kwh = 0.0
                self._current_ev_charging = 0.0
                self._current_grid_import = 0.0
                self._current_bess_discharge = 0.0
                self._current_bess_charge = 0.0
        
        def _on_training_end(self) -> None:
            """Resumen al final del entrenamiento y generacion de graficas."""
            print()
            print("    === RESUMEN METRICAS SAC ===")
            if self.q_value_history:
                print(f"    Q-value: min={min(self.q_value_history):.1f}, max={max(self.q_value_history):.1f}, final={self.q_value_history[-1]:.1f}")
            if self.entropy_history:
                print(f"    Entropy: start={self.entropy_history[0]:.3f}, final={self.entropy_history[-1]:.3f}")
            if self.alpha_history:
                print(f"    Alpha (alpha): start={self.alpha_history[0]:.4f}, final={self.alpha_history[-1]:.4f}")
            if self.action_std_history:
                print(f"    Action Std: start={self.action_std_history[0]:.4f}, final={self.action_std_history[-1]:.4f}")
            if self.eval_returns_history:
                print(f"    Eval Returns (deterministic): start={self.eval_returns_history[0]:.2f}, final={self.eval_returns_history[-1]:.2f}, best={max(self.eval_returns_history):.2f}")
            
            # ===== RESUMEN KPIs CITYLEARN =====
            print()
            print("    === RESUMEN KPIs CITYLEARN ===")
            if self.electricity_consumption_history:
                print(f"    Net Consumption: start={self.electricity_consumption_history[0]:.1f} kWh/day, final={self.electricity_consumption_history[-1]:.1f} kWh/day")
            if self.carbon_emissions_history:
                reduction = (self.carbon_emissions_history[0] - self.carbon_emissions_history[-1]) / max(self.carbon_emissions_history[0], 0.001) * 100
                print(f"    CO2 Emissions: start={self.carbon_emissions_history[0]:.1f} kg/day, final={self.carbon_emissions_history[-1]:.1f} kg/day ({reduction:+.1f}%)")
            if self.ramping_history:
                print(f"    Ramping: start={self.ramping_history[0]:.1f} kW, final={self.ramping_history[-1]:.1f} kW")
            if self.avg_daily_peak_history:
                print(f"    Daily Peak: start={self.avg_daily_peak_history[0]:.1f} kW, final={self.avg_daily_peak_history[-1]:.1f} kW")
            if self.one_minus_load_factor_history:
                print(f"    (1-Load Factor): start={self.one_minus_load_factor_history[0]:.3f}, final={self.one_minus_load_factor_history[-1]:.3f}")
            
            # ===== RESUMEN ACTION SATURATION =====
            print()
            print("    === RESUMEN SATURACION ACCIONES ===")
            if self._total_action_count > 0:
                pct_low = 100.0 * self._actions_at_low / self._total_action_count
                pct_high = 100.0 * self._actions_at_high / self._total_action_count
                pct_saturated = pct_low + pct_high
                print(f"    Total acciones tracked: {self._total_action_count:,}")
                print(f"    En limite inferior (<0.05): {pct_low:.1f}%")
                print(f"    En limite superior (>0.95): {pct_high:.1f}%")
                print(f"    Total saturadas: {pct_saturated:.1f}%")
                if pct_saturated > 30:
                    print(f"    [!] ALTA SATURACION: Politica puede estar degenerada")
            
            # NUEVO v2.0: Imprimir resumen de problemas detectados con recomendaciones
            self._print_problem_summary()
            
            # Generar graficas de diagnostico SAC
            if len(self.steps_history) > 1:
                self._generate_sac_graphs()
            
            # Generar graficas de KPIs CityLearn
            if len(self.kpi_steps_history) > 1:
                self._generate_kpi_graphs()
            
            # Generar histograma de acciones
            if len(self._all_actions) > 0:
                self._generate_action_histogram()
        
        def _generate_sac_graphs(self) -> None:
            """
            Genera graficas de diagnostico para SAC.
            
            GRAFICAS GENERADAS:
            ===================
            1. Critic/Q Loss vs Steps
               - Q1 y Q2 loss separados si disponibles
               - Si se dispara -> reward scale mal / LR alto
            
            2. Actor Loss vs Steps
               - Mide que tan bien el actor maximiza Q
               - Fluctuante es normal, tendencia decreciente es buena
            
            3. Alpha (temperatura) y Entropy vs Steps
               - Con auto-tuning, alpha refleja cuanta aleatoriedad mantiene
               - Entropy debe decrecer gradualmente, NO colapsar a 0
            
            4. Mean Q-value vs Steps
               - Si Q se dispara > 1000 -> sobreestimacion
               - Tipico: crece gradualmente y se estabiliza
            
            5. Std de acciones / log_std vs Steps
               - Colapso de std temprano = exploracion muere
               - std < 0.05 muy temprano es warning
            
            Referencias:
              [1] Haarnoja et al. (2018) SAC paper
              [2] Spinning Up: https://spinningup.openai.com/en/latest/algorithms/sac.html
              [3] CleanRL SAC implementation metrics
            """
            try:
                # Crear directorio si no existe
                self.output_dir.mkdir(parents=True, exist_ok=True)
                
                # Convertir a arrays
                steps = np.array(self.steps_history)
                steps_k = steps / 1000.0  # En miles para legibilidad
                
                # ================================================================
                # FIGURA 1: Critic/Q Loss vs Steps
                # ================================================================
                if self.critic_loss_history:
                    fig1, ax1 = plt.subplots(figsize=(10, 6))
                    critic_loss = np.array(self.critic_loss_history)
                    
                    # Plot Q loss combinado
                    ax1.plot(steps_k[:len(critic_loss)], critic_loss, 'r-', linewidth=1.5, 
                             label='Critic Loss (Q1+Q2)', alpha=0.8)
                    
                    # Si hay Q1/Q2 separados
                    if self.q1_history and self.q2_history:
                        ax1_twin = ax1.twinx()
                        q1 = np.array(self.q1_history)
                        q2 = np.array(self.q2_history)
                        ax1_twin.plot(steps_k[:len(q1)], q1, 'b--', linewidth=1, label='Q1 mean', alpha=0.6)
                        ax1_twin.plot(steps_k[:len(q2)], q2, 'g--', linewidth=1, label='Q2 mean', alpha=0.6)
                        ax1_twin.set_ylabel('Q Values', fontsize=12, color='blue')
                        ax1_twin.legend(loc='upper right')
                    
                    # Smoothing
                    if len(critic_loss) >= 10:
                        window = min(10, len(critic_loss) // 3)
                        critic_smooth = pd.Series(critic_loss).rolling(window=window, center=True).mean()
                        ax1.plot(steps_k[:len(critic_smooth)], critic_smooth, 'r-', linewidth=2.5, 
                                 label='Critic Loss (smooth)', alpha=1.0)
                    
                    ax1.set_xlabel('Steps (K)', fontsize=12)
                    ax1.set_ylabel('Critic Loss', fontsize=12, color='red')
                    ax1.set_title('SAC: Critic/Q Loss vs Training Steps\n'
                                 '(Si se dispara -> reward scale mal / LR alto / targets inestables)', fontsize=14)
                    ax1.legend(loc='upper left')
                    ax1.grid(True, alpha=0.3)
                    
                    critic_path = self.output_dir / 'sac_critic_loss.png'
                    fig1.tight_layout()
                    fig1.savefig(critic_path, dpi=150, bbox_inches='tight')
                    plt.close(fig1)
                    print(f'    [GRAPH] Critic Loss: {critic_path}')
                
                # ================================================================
                # FIGURA 2: Actor Loss vs Steps
                # ================================================================
                if self.actor_loss_history:
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    actor_loss = np.array(self.actor_loss_history)
                    
                    ax2.plot(steps_k[:len(actor_loss)], actor_loss, 'b-', linewidth=1.5, 
                             label='Actor Loss', alpha=0.8)
                    
                    # Smoothing
                    if len(actor_loss) >= 10:
                        window = min(10, len(actor_loss) // 3)
                        actor_smooth = pd.Series(actor_loss).rolling(window=window, center=True).mean()
                        ax2.plot(steps_k[:len(actor_smooth)], actor_smooth, 'b-', linewidth=2.5, 
                                 label='Actor Loss (smooth)', alpha=1.0)
                    
                    # Linea de referencia en 0
                    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                    
                    ax2.set_xlabel('Steps (K)', fontsize=12)
                    ax2.set_ylabel('Actor Loss', fontsize=12)
                    ax2.set_title('SAC: Actor Loss vs Training Steps\n'
                                 '(Fluctuante es normal, tendencia decreciente es buena)', fontsize=14)
                    ax2.legend(loc='upper right')
                    ax2.grid(True, alpha=0.3)
                    
                    actor_path = self.output_dir / 'sac_actor_loss.png'
                    fig2.tight_layout()
                    fig2.savefig(actor_path, dpi=150, bbox_inches='tight')
                    plt.close(fig2)
                    print(f'    [GRAPH] Actor Loss: {actor_path}')
                
                # ================================================================
                # FIGURA 3: Alpha (temperatura) y Entropy vs Steps
                # ================================================================
                if self.alpha_history or self.entropy_history:
                    fig3, ax3 = plt.subplots(figsize=(10, 6))
                    
                    # Entropy
                    if self.entropy_history:
                        entropy = np.array(self.entropy_history)
                        ax3.plot(steps_k[:len(entropy)], entropy, 'm-', linewidth=1.5, 
                                 label='Entropy', alpha=0.8)
                        
                        if len(entropy) >= 10:
                            window = min(10, len(entropy) // 3)
                            entropy_smooth = pd.Series(entropy).rolling(window=window, center=True).mean()
                            ax3.plot(steps_k[:len(entropy_smooth)], entropy_smooth, 'm-', linewidth=2.5, 
                                     label='Entropy (smooth)', alpha=1.0)
                        
                        # Linea de warning
                        ax3.axhline(y=0.1, color='red', linestyle='--', linewidth=2, 
                                   label='Collapse warning (0.1)')
                        ax3.axhspan(0, 0.1, alpha=0.15, color='red')
                    
                    ax3.set_xlabel('Steps (K)', fontsize=12)
                    ax3.set_ylabel('Entropy', fontsize=12, color='purple')
                    
                    # Alpha en eje secundario
                    if self.alpha_history:
                        ax3_twin = ax3.twinx()
                        alpha = np.array(self.alpha_history)
                        ax3_twin.plot(steps_k[:len(alpha)], alpha, 'orange', linewidth=1.5, 
                                     label='Alpha (alpha)', alpha=0.8)
                        
                        if len(alpha) >= 10:
                            window = min(10, len(alpha) // 3)
                            alpha_smooth = pd.Series(alpha).rolling(window=window, center=True).mean()
                            ax3_twin.plot(steps_k[:len(alpha_smooth)], alpha_smooth, 'orange', 
                                         linewidth=2.5, label='Alpha (smooth)', alpha=1.0)
                        
                        ax3_twin.set_ylabel('Alpha (alpha)', fontsize=12, color='orange')
                        ax3_twin.axhline(y=0.01, color='darkred', linestyle=':', linewidth=1.5, 
                                        label='alpha warning (0.01)')
                        ax3_twin.legend(loc='upper right')
                    
                    ax3.set_title('SAC: Alpha (temperatura) y Entropy vs Training Steps\n'
                                 '(Con auto-tuning, alpha refleja cuanta aleatoriedad mantiene)', fontsize=14)
                    ax3.legend(loc='upper left')
                    ax3.grid(True, alpha=0.3)
                    
                    entropy_path = self.output_dir / 'sac_alpha_entropy.png'
                    fig3.tight_layout()
                    fig3.savefig(entropy_path, dpi=150, bbox_inches='tight')
                    plt.close(fig3)
                    print(f'    [GRAPH] Alpha & Entropy: {entropy_path}')
                
                # ================================================================
                # FIGURA 4: Mean Q-value vs Steps
                # ================================================================
                if self.q_value_history:
                    fig4, ax4 = plt.subplots(figsize=(10, 6))
                    q_values = np.array(self.q_value_history)
                    
                    ax4.plot(steps_k[:len(q_values)], q_values, 'g-', linewidth=1.5, 
                             label='Mean Q-value', alpha=0.8)
                    
                    # Smoothing
                    if len(q_values) >= 10:
                        window = min(10, len(q_values) // 3)
                        q_smooth = pd.Series(q_values).rolling(window=window, center=True).mean()
                        ax4.plot(steps_k[:len(q_smooth)], q_smooth, 'g-', linewidth=2.5, 
                                 label='Q-value (smooth)', alpha=1.0)
                    
                    # Lineas de referencia
                    max_q = max(abs(q_values.min()), abs(q_values.max()))
                    if max_q > 100:
                        ax4.axhline(y=1000, color='red', linestyle='--', linewidth=2, 
                                   label='Overflow warning (1000)')
                        ax4.axhline(y=-1000, color='red', linestyle='--', linewidth=2)
                    
                    # Zona de warning
                    if max_q > 500:
                        ax4.axhspan(1000, max(1100, q_values.max() * 1.1), alpha=0.2, color='red', 
                                   label='Danger zone')
                    
                    ax4.set_xlabel('Steps (K)', fontsize=12)
                    ax4.set_ylabel('Mean Q-value', fontsize=12)
                    ax4.set_title('SAC: Mean Q-value vs Training Steps\n'
                                 '(Si Q se dispara > 1000 -> reward scale mal / LR alto / targets inestables)', 
                                 fontsize=14)
                    ax4.legend(loc='best')
                    ax4.grid(True, alpha=0.3)
                    
                    q_path = self.output_dir / 'sac_q_values.png'
                    fig4.tight_layout()
                    fig4.savefig(q_path, dpi=150, bbox_inches='tight')
                    plt.close(fig4)
                    print(f'    [GRAPH] Q-values: {q_path}')
                
                # ================================================================
                # FIGURA 5: Std de acciones / log_std vs Steps
                # ================================================================
                if self.action_std_history or self.log_std_history:
                    fig5, ax5 = plt.subplots(figsize=(10, 6))
                    
                    # Action std
                    if self.action_std_history:
                        action_std = np.array(self.action_std_history)
                        ax5.plot(steps_k[:len(action_std)], action_std, 'c-', linewidth=1.5, 
                                 label='Action Std', alpha=0.8)
                        
                        if len(action_std) >= 10:
                            window = min(10, len(action_std) // 3)
                            std_smooth = pd.Series(action_std).rolling(window=window, center=True).mean()
                            ax5.plot(steps_k[:len(std_smooth)], std_smooth, 'c-', linewidth=2.5, 
                                     label='Action Std (smooth)', alpha=1.0)
                        
                        # Linea de warning
                        ax5.axhline(y=0.05, color='red', linestyle='--', linewidth=2, 
                                   label='Collapse warning (0.05)')
                        ax5.axhspan(0, 0.05, alpha=0.15, color='red')
                    
                    ax5.set_xlabel('Steps (K)', fontsize=12)
                    ax5.set_ylabel('Action Std', fontsize=12, color='cyan')
                    
                    # log_std en eje secundario
                    if self.log_std_history:
                        ax5_twin = ax5.twinx()
                        log_std = np.array(self.log_std_history)
                        ax5_twin.plot(steps_k[:len(log_std)], log_std, 'brown', linewidth=1.5, 
                                     label='log_std', alpha=0.8)
                        
                        if len(log_std) >= 10:
                            window = min(10, len(log_std) // 3)
                            log_smooth = pd.Series(log_std).rolling(window=window, center=True).mean()
                            ax5_twin.plot(steps_k[:len(log_smooth)], log_smooth, 'brown', 
                                         linewidth=2.5, label='log_std (smooth)', alpha=1.0)
                        
                        ax5_twin.set_ylabel('log_std', fontsize=12, color='brown')
                        ax5_twin.legend(loc='upper right')
                    
                    ax5.set_title('SAC: Std de acciones / log_std vs Training Steps\n'
                                 '(Colapso de std temprano = exploracion muere)', fontsize=14)
                    ax5.legend(loc='upper left')
                    ax5.grid(True, alpha=0.3)
                    
                    std_path = self.output_dir / 'sac_action_std.png'
                    fig5.tight_layout()
                    fig5.savefig(std_path, dpi=150, bbox_inches='tight')
                    plt.close(fig5)
                    print(f'    [GRAPH] Action Std: {std_path}')
                
                # ================================================================
                # FIGURA 6 (BONUS): Dashboard combinado SAC
                # ================================================================
                fig6, axes = plt.subplots(2, 3, figsize=(16, 10))
                
                # Critic Loss (0,0)
                if self.critic_loss_history:
                    critic_loss = np.array(self.critic_loss_history)
                    axes[0, 0].plot(steps_k[:len(critic_loss)], critic_loss, 'r-', linewidth=1, alpha=0.7)
                    axes[0, 0].set_ylabel('Critic Loss')
                    axes[0, 0].set_title('Critic Loss')
                    axes[0, 0].grid(True, alpha=0.3)
                
                # Actor Loss (0,1)
                if self.actor_loss_history:
                    actor_loss = np.array(self.actor_loss_history)
                    axes[0, 1].plot(steps_k[:len(actor_loss)], actor_loss, 'b-', linewidth=1, alpha=0.7)
                    axes[0, 1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
                    axes[0, 1].set_ylabel('Actor Loss')
                    axes[0, 1].set_title('Actor Loss')
                    axes[0, 1].grid(True, alpha=0.3)
                
                # Q-values (0,2)
                if self.q_value_history:
                    q_values = np.array(self.q_value_history)
                    axes[0, 2].plot(steps_k[:len(q_values)], q_values, 'g-', linewidth=1, alpha=0.7)
                    axes[0, 2].axhline(y=1000, color='red', linestyle='--', alpha=0.5)
                    axes[0, 2].set_ylabel('Mean Q-value')
                    axes[0, 2].set_title('Mean Q-value')
                    axes[0, 2].grid(True, alpha=0.3)
                
                # Alpha (1,0)
                if self.alpha_history:
                    alpha = np.array(self.alpha_history)
                    axes[1, 0].plot(steps_k[:len(alpha)], alpha, 'orange', linewidth=1, alpha=0.7)
                    axes[1, 0].axhline(y=0.01, color='red', linestyle='--', alpha=0.5)
                    axes[1, 0].set_xlabel('Steps (K)')
                    axes[1, 0].set_ylabel('Alpha (alpha)')
                    axes[1, 0].set_title('Alpha (temperatura)')
                    axes[1, 0].grid(True, alpha=0.3)
                
                # Entropy (1,1)
                if self.entropy_history:
                    entropy = np.array(self.entropy_history)
                    axes[1, 1].plot(steps_k[:len(entropy)], entropy, 'm-', linewidth=1, alpha=0.7)
                    axes[1, 1].axhline(y=0.1, color='red', linestyle='--', alpha=0.5)
                    axes[1, 1].axhspan(0, 0.1, alpha=0.15, color='red')
                    axes[1, 1].set_xlabel('Steps (K)')
                    axes[1, 1].set_ylabel('Entropy')
                    axes[1, 1].set_title('Entropy')
                    axes[1, 1].grid(True, alpha=0.3)
                
                # Action Std (1,2)
                if self.action_std_history:
                    action_std = np.array(self.action_std_history)
                    axes[1, 2].plot(steps_k[:len(action_std)], action_std, 'c-', linewidth=1, alpha=0.7)
                    axes[1, 2].axhline(y=0.05, color='red', linestyle='--', alpha=0.5)
                    axes[1, 2].axhspan(0, 0.05, alpha=0.15, color='red')
                    axes[1, 2].set_xlabel('Steps (K)')
                    axes[1, 2].set_ylabel('Action Std')
                    axes[1, 2].set_title('Action Std')
                    axes[1, 2].grid(True, alpha=0.3)
                
                fig6.suptitle('SAC Training Diagnostics Dashboard', fontsize=16, fontweight='bold')
                
                dashboard_path = self.output_dir / 'sac_dashboard.png'
                fig6.tight_layout()
                fig6.savefig(dashboard_path, dpi=150, bbox_inches='tight')
                plt.close(fig6)
                print(f'    [GRAPH] Dashboard: {dashboard_path}')
                
                print(f'  [OK] 6 graficas SAC generadas en: {self.output_dir}')
                
            except Exception as e:
                print(f'  [WARNING] Error generando graficas SAC: {e}')
                import traceback
                traceback.print_exc()
        
        def _generate_kpi_graphs(self) -> None:
            """
            Generar graficos de KPIs CityLearn vs Training Steps para SAC.
            
            GRAFICOS GENERADOS:
            1. Electricity Consumption (net) vs Steps
            2. Electricity Cost vs Steps
            3. Carbon Emissions vs Steps
            4. Ramping vs Steps
            5. Average Daily Peak vs Steps
            6. (1 - Load Factor) vs Steps
            7. Dashboard KPIs combinado 2├ù3
            """
            
            if len(self.kpi_steps_history) < 2:
                print('     [!] Insuficientes datos para graficos KPIs (< 2 puntos)')
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Funcion helper para suavizado
            def smooth(data: list, window: int = 5) -> np.ndarray:
                """Rolling mean para suavizar curvas."""
                if len(data) < window:
                    return np.array(data)
                smoothed = pd.Series(data).rolling(window=window, min_periods=1).mean().values
                return np.asarray(smoothed, dtype=np.float64)
            
            steps = np.array(self.kpi_steps_history)
            steps_k = steps / 1000.0  # En miles
            
            # ====================================================================
            # GRAFICO 1: ELECTRICITY CONSUMPTION vs STEPS
            # ====================================================================
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                consumption = np.array(self.electricity_consumption_history)
                ax.plot(steps_k, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
                
                # Linea de tendencia
                if len(steps) > 2:
                    z = np.polyfit(steps, consumption, 1)
                    p = np.poly1d(z)
                    ax.plot(steps_k, p(steps), 'r--', alpha=0.7, label=f'Trend (slope={z[0]:.4f})')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('Net Electricity Consumption (kWh/day)')
                ax.set_title('SAC: Electricity Consumption vs Training Steps\n(Lower = better grid independence)')
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
                ax.plot(steps_k, cost, 'g-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(cost)), 'g-', linewidth=2, label='Smoothed')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('Electricity Cost (USD/day)')
                ax.set_title('SAC: Electricity Cost vs Training Steps\n(Lower = better cost efficiency)')
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
                ax.plot(steps_k, emissions, 'brown', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(emissions)), 'brown', linewidth=2, label='Smoothed')
                
                # Baseline sin control
                if len(emissions) > 0:
                    baseline = emissions[0]
                    ax.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label=f'Baseline ({baseline:.1f} kg)')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('Carbon Emissions (kg COÔéé/day)')
                ax.set_title('SAC: Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # Anotar reduccion CO2
                if len(emissions) > 1:
                    reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                    color = 'green' if reduction > 0 else 'red'
                    ax.annotate(f'{"v" if reduction > 0 else "^"} {abs(reduction):.1f}% COÔéé', 
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
                ax.plot(steps_k, ramping, 'purple', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(ramping)), 'purple', linewidth=2, label='Smoothed')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('Average Ramping (kW)')
                ax.set_title('SAC: Load Ramping vs Training Steps\n(Lower = more stable grid operation)')
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
                ax.plot(steps_k, peak, 'red', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(peak)), 'red', linewidth=2, label='Smoothed')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('Daily Peak Demand (kW)')
                ax.set_title('SAC: Average Daily Peak vs Training Steps\n(Lower = better peak shaving)')
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
                ax.plot(steps_k, one_minus_lf, 'orange', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(one_minus_lf)), 'orange', linewidth=2, label='Smoothed')
                
                # Zona ideal (< 0.3 = buen load factor > 0.7)
                ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, label='Target (LF > 0.7)')
                ax.fill_between(steps_k, 0, 0.3, alpha=0.1, color='green')
                
                ax.set_xlabel('Training Steps (K)')
                ax.set_ylabel('(1 - Load Factor)')
                ax.set_title('SAC: (1 - Load Factor) vs Training Steps\n(Lower = better load distribution, 0 = constant load)')
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
            # GRAFICO 7: DASHBOARD KPIs COMBINADO 2├ù3
            # ====================================================================
            try:
                fig, axes = plt.subplots(2, 3, figsize=(16, 10))
                
                # 1. Electricity Consumption (top-left)
                ax = axes[0, 0]
                consumption = np.array(self.electricity_consumption_history)
                ax.plot(steps_k, smooth(list(consumption)), 'b-', linewidth=2)
                ax.set_title('Net Consumption (kWh/day)')
                ax.set_xlabel('Steps (K)')
                ax.grid(True, alpha=0.3)
                
                # 2. Electricity Cost (top-center)
                ax = axes[0, 1]
                cost = np.array(self.electricity_cost_history)
                ax.plot(steps_k, smooth(list(cost)), 'g-', linewidth=2)
                ax.set_title('Cost (USD/day)')
                ax.set_xlabel('Steps (K)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # 3. Carbon Emissions (top-right)
                ax = axes[0, 2]
                emissions = np.array(self.carbon_emissions_history)
                ax.plot(steps_k, smooth(list(emissions)), 'brown', linewidth=2)
                ax.set_title('COÔéé Emissions (kg/day)')
                ax.set_xlabel('Steps (K)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # 4. Ramping (bottom-left)
                ax = axes[1, 0]
                ramping = np.array(self.ramping_history)
                ax.plot(steps_k, smooth(list(ramping)), 'purple', linewidth=2)
                ax.set_title('Ramping (kW)')
                ax.set_xlabel('Steps (K)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # 5. Daily Peak (bottom-center)
                ax = axes[1, 1]
                peak = np.array(self.avg_daily_peak_history)
                ax.plot(steps_k, smooth(list(peak)), 'red', linewidth=2)
                ax.set_title('Daily Peak (kW)')
                ax.set_xlabel('Steps (K)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # 6. (1 - Load Factor) (bottom-right)
                ax = axes[1, 2]
                one_minus_lf = np.array(self.one_minus_load_factor_history)
                ax.plot(steps_k, smooth(list(one_minus_lf)), 'orange', linewidth=2)
                ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7)
                ax.fill_between(steps_k, 0, 0.3, alpha=0.1, color='green')
                ax.set_title('(1 - Load Factor)')
                ax.set_xlabel('Steps (K)')
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
                        improvements.append(f'COÔéé: {imp:.1f}%v')
                if len(peak) > 1:
                    imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                    if imp > 0:
                        improvements.append(f'Peak: {imp:.1f}%v')
                
                title = 'CityLearn KPIs Dashboard - SAC Training'
                if improvements:
                    title += f'\n[OK] Improvements: {", ".join(improvements)}'
                
                fig.suptitle(title, fontsize=14, fontweight='bold')
                plt.tight_layout(rect=[0, 0, 1, 0.96])
                plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
                plt.close(fig)
                print('     [OK] kpi_dashboard.png')
                
            except Exception as e:
                print(f'     [X] Error en KPI dashboard: {e}')
            
            print(f'     [DIR] Graficos KPIs guardados en: {self.output_dir}')
        
        def _generate_action_histogram(self) -> None:
            """
            Generar histograma de distribucion de acciones y grafico de saturacion.
            
            GRAFICOS GENERADOS:
            1. Histograma de todas las acciones (6 subplots si hay multiples canales)
            2. Grafico de barras mostrando % saturacion por canal
            
            Diagnosticos:
            - Distribucion uniforme = buena exploracion
            - Picos en 0 o 1 = politica degenerada (solo extremos)
            - Alta saturacion (>30%) = reward boundary issues
            """
            if len(self._all_actions) == 0:
                print('     [!] No hay datos de acciones para histograma')
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Concatenar todas las acciones
                all_actions = np.vstack(self._all_actions)  # Shape: (samples, action_dim)
                n_samples, action_dim = all_actions.shape
                
                # ================================================================
                # FIGURA 1: Histograma de distribucion de acciones
                # ================================================================
                # Determinar layout
                if action_dim <= 6:
                    n_rows, n_cols = 2, 3
                elif action_dim <= 12:
                    n_rows, n_cols = 3, 4
                else:
                    n_rows, n_cols = 4, 5
                
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 3, n_rows * 2.5))
                axes = axes.flatten()
                
                # Colores para saturacion
                for i in range(min(action_dim, len(axes))):
                    ax = axes[i]
                    action_values = all_actions[:, i]
                    
                    # Calcular saturacion para este canal
                    pct_low = 100.0 * np.sum(action_values < 0.05) / len(action_values)
                    pct_high = 100.0 * np.sum(action_values > 0.95) / len(action_values)
                    
                    # Histograma
                    n, bins, patches = ax.hist(action_values, bins=50, density=True, 
                                               alpha=0.7, color='steelblue', edgecolor='white')
                    
                    # Colorear barras de saturacion
                    for j, patch in enumerate(patches):
                        if bins[j] < 0.05:
                            patch.set_facecolor('red')
                        elif bins[j] > 0.95:
                            patch.set_facecolor('red')
                    
                    # Anotaciones
                    ax.axvline(x=0.05, color='red', linestyle='--', alpha=0.5)
                    ax.axvline(x=0.95, color='red', linestyle='--', alpha=0.5)
                    ax.set_xlim(0, 1)
                    
                    # Titulo con saturacion
                    sat_total = pct_low + pct_high
                    color = 'red' if sat_total > 30 else 'orange' if sat_total > 15 else 'green'
                    if i == 0:
                        ax.set_title(f'BESS ({sat_total:.0f}% sat)', fontsize=9, color=color)
                    else:
                        ax.set_title(f'Socket {i} ({sat_total:.0f}%)', fontsize=9, color=color)
                    
                    ax.set_xlabel('Action', fontsize=8)
                    ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Ocultar ejes vacios
                for i in range(action_dim, len(axes)):
                    axes[i].axis('off')
                
                fig.suptitle(f'SAC Action Distribution ({n_samples:,} samples)\n'
                            f'Red zones = saturation (< 0.05 or > 0.95)', 
                            fontsize=12, fontweight='bold')
                plt.tight_layout(rect=[0, 0, 1, 0.95])
                plt.savefig(self.output_dir / 'sac_action_histogram.png', dpi=150)
                plt.close(fig)
                print('     [OK] sac_action_histogram.png')
                
                # ================================================================
                # FIGURA 2: Saturation Summary Bar Chart
                # ================================================================
                fig, ax = plt.subplots(figsize=(12, 5))
                
                # Calcular saturacion por canal
                sat_low = []
                sat_high = []
                for i in range(action_dim):
                    action_values = all_actions[:, i]
                    sat_low.append(100.0 * np.sum(action_values < 0.05) / len(action_values))
                    sat_high.append(100.0 * np.sum(action_values > 0.95) / len(action_values))
                
                x = np.arange(min(action_dim, 40))  # Limitar a 40 canales para visualizacion
                width = 0.35
                
                bars1 = ax.bar(x - width/2, sat_low[:len(x)], width, label='Low (<0.05)', color='blue', alpha=0.7)
                bars2 = ax.bar(x + width/2, sat_high[:len(x)], width, label='High (>0.95)', color='orange', alpha=0.7)
                
                # Linea de warning
                ax.axhline(y=30, color='red', linestyle='--', linewidth=2, label='Warning (30%)')
                
                ax.set_xlabel('Action Channel')
                ax.set_ylabel('Saturation %')
                ax.set_title(f'SAC Action Saturation by Channel\n'
                            f'Total Low: {np.mean(sat_low):.1f}%, Total High: {np.mean(sat_high):.1f}%')
                ax.set_xticks(x[::2])  # Cada 2 para legibilidad
                ax.legend()
                ax.grid(True, alpha=0.3, axis='y')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'sac_action_saturation.png', dpi=150)
                plt.close(fig)
                print('     [OK] sac_action_saturation.png')
                
            except Exception as e:
                print(f'     [X] Error en action histogram: {e}')
                import traceback
                traceback.print_exc()
    
    # NUEVO: SAC Metrics Callback con generacion de graficas
    sac_metrics_callback = SACMetricsCallback(
        log_freq=500, 
        eval_freq=8760, 
        output_dir=OUTPUT_DIR,  # Directorio para guardar graficas
        verbose=0
    )
    
    # Agregar callback visual de metricas
    verbose_metrics = VerboseMetricsCallback(log_freq=500)
    
    callback_list = CallbackList([checkpoint_callback, sac_metrics_callback, verbose_metrics])
    
    print('[8] ENTRENAMIENTO SAC - 15 EPISODIOS COMPLETOS (OPTIMIZADO)')
    print('-' * 80)
    print(f'  Total timesteps: 131,400 (15 episodios x 8,760 h/episodio)')
    print(f'  Checkpoint cada: 1,000 steps')
    print(f'  Warmup steps:    {sac_config.learning_starts:,} (random exploration)')
    print(f'  Batch size:      {sac_config.batch_size}')
    print(f'  Buffer size:     {sac_config.buffer_size:,}')
    print(f'  tau:             {sac_config.tau}')
    print(f'  gamma:           {sac_config.gamma}')
    print(f'  Train freq:      {sac_config.train_freq}')
    print(f'  Gradient steps:  {sac_config.gradient_steps} (updates per env step)')
    print(f'  Entropy coef:    {sac_config.ent_coef}')
    print(f'  Target entropy:  {sac_config.target_entropy}')
    print(f'  Learning rate:   {sac_config.learning_rate}')
    print(f'  Networks:        Actor/Critic {list(sac_config.policy_kwargs.get("net_arch", {}).get("pi", [256, 256]))}')
    print(f'  Datos: Datos reales OE2 (solar 8.29GWh + chargers + mall 12.40GWh + BESS 2,000 kWh max SOC)')
    print(f'  Device: {DEVICE.upper()}')
    print()
    print('  METRICAS LOGUEADAS (cada 500 steps):')
    print('  - Actor loss, Critic loss (Q1/Q2)')
    print('  - Mean Q-value (alerta si > 1000)')
    print('  - Entropy y alpha (alerta si entropy < 0.1 o alpha < 0.01)')
    print('  - Replay buffer fill %')
    print('  - Updates per step (ratio real)')
    print('  - Mean/Std acciones, log_std')
    print('  EVAL (cada 8760 steps = 1 episodio):')
    print('  - Eval Return (deterministico, sin ruido)')
    print()
    print('  Progreso por episodio (cada 100 timesteps dentro del episodio):')
    print('-' * 80)
    print()
    
    # ===== MOSTRAR PARAMETROS MULTIOBJETIVO =====
    print('[PARAMETROS MULTIOBJETIVO - PESOS DE RECOMPENSA]')
    print('-' * 80)
    if reward_weights:
        print(f'  [OK] Reward weights cargados (priority=co2_focus):')
        print(f'    - CO2 Grid Minimization:    {reward_weights.co2:.3f}')
        print(f'    - Solar Self-Consumption:  {reward_weights.solar:.3f}')
        print(f'    - EV Satisfaction:         {reward_weights.ev_satisfaction:.3f}')
        print(f'    - Cost Minimization:       {reward_weights.cost:.3f}')
        print(f'    - Grid Stability:          {reward_weights.grid_stability:.3f}')
        total = reward_weights.co2 + reward_weights.solar + reward_weights.ev_satisfaction + reward_weights.cost + reward_weights.grid_stability
        print(f'  [OK] Total weight sum:          {total:.3f}')
    else:
        print(f'  [!] Warning: Reward weights no initialized correctly')
    print()
    
    # ========== ENTRENAMIENTO ROBUSTO CON REINTENTOS ==========
    max_retries = 3
    retry_count = 0
    training_complete = False
    
    # Timer para calcular duracion del entrenamiento
    train_start_time = time.time()
    
    while retry_count < max_retries and not training_complete:
        try:
            print(f'\n[INTENTO {retry_count + 1}/{max_retries}] Iniciando entrenamiento SAC...')
            agent.learn(
                total_timesteps=87_600,  # 10 episodios x 8,760 steps (1 ano = 1 episodio)
                callback=callback_list,
                reset_num_timesteps=False,
                progress_bar=True,
                log_interval=1,
            )
            print('\n[OK] Entrenamiento SAC completado exitosamente')
            training_complete = True
            
        except KeyboardInterrupt:
            print('\n[USUARIO] Entrenamiento interrumpido por usuario')
            agent.save(CHECKPOINT_DIR / 'sac_model_interrupted.zip')
            training_complete = True
            break
            
        except Exception as e:
            retry_count += 1
            print(f'\n[ERROR - INTENTO {retry_count}] {str(e)[:100]}...')
            
            if retry_count >= max_retries:
                print(f'[FATAL] Se alcanzo el limite de reintentos ({max_retries})')
                print('[ACCION] Guardando checkpoint y continuando con resultados parciales...')
                break
            else:
                print(f'[REINTENTANDO] Reinicio en 5 segundos...')
                time.sleep(5)
                try:
                    # Recargar agent desde ultimo checkpoint
                    latest = sorted(CHECKPOINT_DIR.glob('sac_model_*_steps.zip'))[-1] if list(CHECKPOINT_DIR.glob('sac_model_*_steps.zip')) else None
                    if latest:
                        print(f'[CARGA] Retomando desde: {latest.name}')
                        agent = SAC.load(str(latest), env=env, device=DEVICE)
                except:
                    print('[ADVERTENCIA] No se pudo recargar checkpoint, continuando con agente actual')
    
    # SIEMPRE guardar checkpoint final - ROBUSTO (FUERA del try-except)
    train_end_time = time.time()
    elapsed_seconds = train_end_time - train_start_time
    speed_steps_per_sec = agent.num_timesteps / elapsed_seconds if elapsed_seconds > 0 else 0
    
    try:
        final_path = CHECKPOINT_DIR / f'sac_model_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        agent.save(final_path)
        print(f'[OK] Checkpoint final guardado: {final_path.name}')
    except Exception as e:
        print(f'[ADVERTENCIA] No se pudo guardar checkpoint final: {e}')
    
    # ========== GUARDAR ARCHIVOS DE SALIDA (como PPO/A2C) ==========
    print()
    print('  GUARDANDO ARCHIVOS DE SALIDA:')
    
    # 1. trace_sac.csv - Registro detallado de cada step
    if sac_metrics_callback.trace_records:
        trace_df = pd.DataFrame(sac_metrics_callback.trace_records)
        trace_path = OUTPUT_DIR / 'trace_sac.csv'
        trace_df.to_csv(trace_path, index=False, encoding='utf-8')
        print(f'    [OK] trace_sac.csv: {len(trace_df):,} registros -> {trace_path}')
    else:
        print('    [!] trace_sac.csv: Sin registros')
    
    # 2. timeseries_sac.csv - Series temporales horarias
    if sac_metrics_callback.timeseries_records:
        ts_df = pd.DataFrame(sac_metrics_callback.timeseries_records)
        ts_path = OUTPUT_DIR / 'timeseries_sac.csv'
        ts_df.to_csv(ts_path, index=False, encoding='utf-8')
        print(f'    [OK] timeseries_sac.csv: {len(ts_df):,} registros -> {ts_path}')
    else:
        print('    [!] timeseries_sac.csv: Sin registros')
    
    # 3. result_sac.json - Resumen completo del entrenamiento
    # Calcular metricas de validacion directamente de los datos de episodio
    episode_rewards_list = sac_metrics_callback.episode_rewards
    episode_solar_list = sac_metrics_callback.episode_solar_kwh
    episode_grid_list = sac_metrics_callback.episode_grid_import
    episode_co2_grid_list = sac_metrics_callback.episode_co2_grid
    
    # Calcular estadisticas de validacion
    mean_reward = float(np.mean(episode_rewards_list)) if episode_rewards_list else 0.0
    std_reward = float(np.std(episode_rewards_list)) if episode_rewards_list else 0.0
    mean_solar_kwh = float(np.mean(episode_solar_list)) if episode_solar_list else 0.0
    mean_grid_import_kwh = float(np.mean(episode_grid_list)) if episode_grid_list else 0.0
    
    # CO2 avoided calculation (baseline 8.92M kg/year for 100% grid)
    baseline_co2 = 8920000.0
    mean_co2_grid = float(np.mean(episode_co2_grid_list)) if episode_co2_grid_list else 0.0
    mean_co2_avoided_kg = baseline_co2 - mean_co2_grid
    
    result_summary = {
        'timestamp': datetime.now().isoformat(),
        'agent': 'SAC',
        'version': 'v7.2',
        'project': 'pvbesscar',
        'location': 'Iquitos, Peru',
        'co2_factor_kg_per_kwh': 0.4521,
        
        # ===== TRAINING SECTION (COMO PPO/A2C) =====
        'training': {
            'total_timesteps': int(agent.num_timesteps),
            'episodes': int(sac_metrics_callback.episode_count),
            'duration_seconds': float(elapsed_seconds),
            'speed_steps_per_second': float(speed_steps_per_sec),
            'device': str(DEVICE),
            'hyperparameters': {
                'learning_rate': sac_config.learning_rate,
                'buffer_size': sac_config.buffer_size,
                'batch_size': sac_config.batch_size,
                'tau': sac_config.tau,
                'gamma': sac_config.gamma,
                'train_freq': sac_config.train_freq,
                'gradient_steps': sac_config.gradient_steps,
                'ent_coef': sac_config.ent_coef,
                'target_entropy': sac_config.target_entropy,
                'learning_starts': sac_config.learning_starts,
            }
        },
        
        # ===== VALIDATION SECTION (COMO PPO/A2C) =====
        'validation': {
            'num_episodes': int(sac_metrics_callback.episode_count),
            'mean_reward': mean_reward,
            'std_reward': std_reward,
            'mean_co2_avoided_kg': mean_co2_avoided_kg,
            'mean_solar_kwh': mean_solar_kwh,
            'mean_grid_import_kwh': mean_grid_import_kwh,
        },
        
        # ===== TRAINING EVOLUTION (COMO PPO/A2C) =====
        'training_evolution': {
            'episode_rewards': episode_rewards_list,
            'episode_co2_grid': episode_co2_grid_list,
            'episode_solar_kwh': episode_solar_list,
            'episode_ev_charging': sac_metrics_callback.episode_ev_charging,
            'episode_grid_import': episode_grid_list,
            'episode_bess_discharge_kwh': sac_metrics_callback.episode_bess_discharge_kwh,
            'episode_bess_charge_kwh': sac_metrics_callback.episode_bess_charge_kwh,
        },
        
        'vehicle_charging': {
            'motos_target': 270,
            'mototaxis_target': 39,
            'vehicles_target_daily': 309,
            'motos_charged_per_episode': sac_metrics_callback.episode_motos_charged if hasattr(sac_metrics_callback, 'episode_motos_charged') else [],
            'mototaxis_charged_per_episode': sac_metrics_callback.episode_mototaxis_charged if hasattr(sac_metrics_callback, 'episode_mototaxis_charged') else [],
            'description': 'Conteo real de vehiculos cargados usando energia dataset (270 motos + 39 mototaxis = 309/día)',
        },
        
        'model_path': str(final_path),
        
        # ===== ESTRUCTURA CO2 v7.1 =====
        'co2_structure_v71': {
            'description': 'Estructura CO2 para calculo de metricas de reduccion',
            'co2_directo_ev': {
                'descripcion': 'REDUCCION DIRECTA por cambio combustible gasolina -> electrico',
                'fuente': 'SOLO EV (motos + mototaxis)',
                'factor': '0.87 kg CO2/kWh motos, 0.47 kg CO2/kWh mototaxis',
                'columnas': ['co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg', 'reduccion_directa_co2_kg'],
            },
            'co2_indirecto_solar': {
                'descripcion': 'REDUCCION INDIRECTA cuando solar suministra a EV, BESS, Mall, Red',
                'fuente': 'Generacion solar',
                'factor': '0.4521 kg CO2/kWh',
                'columnas': ['energia_suministrada_al_ev_kwh', 'energia_suministrada_al_bess_kwh', 
                            'energia_suministrada_al_mall_kwh', 'energia_suministrada_a_red_kwh',
                            'reduccion_indirecta_co2_kg_total'],
            },
            'co2_indirecto_bess': {
                'descripcion': 'REDUCCION INDIRECTA cuando BESS suministra a EV y Mall (peak shaving)',
                'fuente': 'BESS descarga',
                'condicion': 'Demanda pico > 2000 kW',
                'factor': '0.4521 kg CO2/kWh',
                'columnas': ['bess_to_ev_kwh', 'bess_to_mall_kwh', 'co2_avoided_indirect_kg'],
            },
            'mall_emite': {
                'descripcion': 'MALL EMITE CO2 (NO reduce) - consume del grid termico',
                'fuente': 'Mall demand',
                'factor': '0.4521 kg CO2/kWh',
                'columnas': ['mall_co2_indirect_kg'],
            },
        },
        
        # ===== COLUMNAS DE DATASETS v7.1 =====
        'dataset_columns': {
            'chargers': {
                'archivo': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
                'shape': '(8760, 353)',
                'descripcion': '11 columnas globales + 342 columnas por socket (38 sockets x 9 metricas)',
                'global_columns': ['datetime', 'is_hora_punta', 'tarifa_aplicada_soles', 'ev_energia_total_kwh',
                                  'costo_carga_ev_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
                                  'co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg', 'reduccion_directa_co2_kg', 
                                  'ev_demand_kwh'],
                'uso_en_entrenamiento': {
                    'reduccion_directa_co2_kg': 'CO2 directo evitado por cambio gasolina->EV (DATO REAL)',
                    'co2_reduccion_motos_kg': 'Tracking por tipo de vehiculo',
                    'co2_reduccion_mototaxis_kg': 'Tracking por tipo de vehiculo',
                    'costo_carga_ev_soles': 'Calculo de costos',
                    'tarifa_aplicada_soles': 'Validacion tarifas',
                },
            },
            'bess': {
                'archivo': 'data/oe2/bess/bess_ano_2024.csv',
                'shape': '(8760, 25)',
                'columns': ['datetime', 'pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh',
                           'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
                           'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
                           'grid_to_ev_kwh', 'grid_to_mall_kwh', 'grid_to_bess_kwh', 'grid_import_total_kwh',
                           'bess_soc_percent', 'bess_mode', 'tariff_osinergmin_soles_kwh',
                           'cost_grid_import_soles', 'peak_reduction_savings_soles',
                           'peak_reduction_savings_normalized', 'co2_avoided_indirect_kg',
                           'co2_avoided_indirect_normalized', 'mall_grid_import_kwh'],
                'uso_en_entrenamiento': {
                    'pv_to_ev_kwh': 'CO2 indirecto solar (energia solar a EV)',
                    'pv_to_bess_kwh': 'CO2 indirecto solar (energia solar a BESS)',
                    'pv_to_mall_kwh': 'CO2 indirecto solar (energia solar a Mall)',
                    'bess_to_ev_kwh': 'CO2 indirecto BESS (descarga a EV)',
                    'bess_to_mall_kwh': 'CO2 indirecto BESS (descarga a Mall)',
                    'grid_import_total_kwh': 'CO2 emitido por grid termico',
                    'bess_soc_percent': 'Estado actual del BESS',
                    'tariff_osinergmin_soles_kwh': 'Tarifa real OSINERGMIN',
                    'cost_grid_import_soles': 'Costo real importacion grid',
                    'peak_reduction_savings_soles': 'Ahorro por peak shaving',
                },
            },
            'solar': {
                'archivo': 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
                'shape': '(8760, 16)',
                'columns': ['datetime', 'irradiancia_ghi', 'temperatura_c', 'velocidad_viento_ms',
                           'potencia_kw', 'energia_kwh', 'is_hora_punta', 'hora_tipo',
                           'tarifa_aplicada_soles', 'ahorro_solar_soles', 'reduccion_indirecta_co2_kg',
                           'energia_suministrada_al_bess_kwh', 'energia_suministrada_al_ev_kwh',
                           'energia_suministrada_al_mall_kwh', 'energia_suministrada_a_red_kwh',
                           'reduccion_indirecta_co2_kg_total'],
                'uso_en_entrenamiento': {
                    'reduccion_indirecta_co2_kg_total': 'CO2 indirecto solar total (DATO REAL)',
                    'energia_kwh': 'Generacion solar horaria',
                    'energia_suministrada_al_ev_kwh': 'Energia solar directa a EV',
                    'energia_suministrada_al_bess_kwh': 'Energia solar a BESS',
                    'energia_suministrada_al_mall_kwh': 'Energia solar a Mall',
                    'irradiancia_ghi': 'Observacion para agente',
                    'temperatura_c': 'Observacion para agente',
                },
            },
            'mall': {
                'archivo': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
                'shape': '(8760, 6)',
                'columns': ['datetime', 'mall_demand_kwh', 'mall_co2_indirect_kg',
                           'is_hora_punta', 'tarifa_soles_kwh', 'mall_cost_soles'],
                'uso_en_entrenamiento': {
                    'mall_co2_indirect_kg': 'CO2 EMITIDO por mall (grid termico) - DATO REAL',
                    'mall_demand_kwh': 'Demanda horaria mall',
                    'mall_cost_soles': 'Costo electricidad mall',
                    'tarifa_soles_kwh': 'Tarifa aplicada',
                },
            },
        },
        
        'metrics_summary': {
            'final_q_value': sac_metrics_callback.q_value_history[-1] if sac_metrics_callback.q_value_history else None,
            'final_entropy': sac_metrics_callback.entropy_history[-1] if sac_metrics_callback.entropy_history else None,
            'final_alpha': sac_metrics_callback.alpha_history[-1] if sac_metrics_callback.alpha_history else None,
            'final_action_std': sac_metrics_callback.action_std_history[-1] if sac_metrics_callback.action_std_history else None,
        },
        'kpi_summary': {
            'electricity_consumption_kwh_per_day': sac_metrics_callback.electricity_consumption_history,
            'carbon_emissions_kg_per_day': sac_metrics_callback.carbon_emissions_history,
            'ramping_kw': sac_metrics_callback.ramping_history,
            'daily_peak_kw': sac_metrics_callback.avg_daily_peak_history,
            'one_minus_load_factor': sac_metrics_callback.one_minus_load_factor_history,
        },
    }
    
    result_path = OUTPUT_DIR / 'result_sac.json'
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, indent=2, ensure_ascii=False, default=str)
    print(f'    [OK] result_sac.json: Resumen completo -> {result_path}')
    
    print()
    print('  ARCHIVOS GENERADOS:')
    print(f'    [OK] {OUTPUT_DIR}/result_sac.json')
    print(f'    [OK] {OUTPUT_DIR}/timeseries_sac.csv')
    print(f'    [OK] {OUTPUT_DIR}/trace_sac.csv')
    
    print()
    print('='*80)
    print(f'Fin: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*80)


if __name__ == '__main__':
    main()
