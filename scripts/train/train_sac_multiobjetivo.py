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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    # No warning - Gymnasium Env fallback es el diseño robusto por defecto

from src.dataset_builder_citylearn.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# ===== VEHICLE CHARGING SCENARIOS - DEFINIDOS LOCALMENTE (ROBUSTO) =====
# No dependemos de módulo externo - todo auto-contenido aquí
VEHICLE_SCENARIOS_AVAILABLE = True  # Siempre disponible porque está definido aquí

# ===== CONSTANTES IQUITOS v5.3 (2026-02-14) CON COMUNICACIÓN SISTEMA =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid térmico aislado)
BESS_CAPACITY_KWH: float = 940.0    # 940 kWh (exclusivo EV, 100% cobertura)
BESS_MAX_POWER_KW: float = 342.0    # 342 kW potencia máxima BESS
HOURS_PER_YEAR: int = 8760

# v5.3: Constantes para normalización de observaciones (comunicación sistema)
SOLAR_MAX_KW: float = 4100.0        # 4,050 kWp nominal + margen
MALL_MAX_KW: float = 150.0          # Demanda máxima mall
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad máxima BESS (referencia normalización)
CHARGER_MAX_KW: float = 10.0        # Max por socket (7.4 kW nominal, 10 kW margen)
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket

# ===== SAC CONFIG =====
# (imports ya arriba: dataclass, field, Dict, List, Optional, Tuple)


# ===== CONSTANTES DE PRIORIZACIÓN SOC =====
# Niveles de SOC a trackear (orden de prioridad: 100% > 80% > 70% > 50% > 30% > 20% > 10%)
SOC_LEVELS: List[int] = [10, 20, 30, 50, 70, 80, 100]
SOC_PRIORITY_WEIGHTS: Dict[int, float] = {
    100: 1.00,  # Máxima prioridad - vehículo completamente cargado
    80: 0.85,   # Alta prioridad - casi listo
    70: 0.70,   # Media-alta
    50: 0.50,   # Media
    30: 0.35,   # Media-baja
    20: 0.20,   # Baja
    10: 0.10,   # Mínima prioridad - apenas comenzó
}


@dataclass
class VehicleSOCState:
    """Estado de SOC de un vehículo individual conectado a un socket."""
    socket_id: int
    vehicle_type: str  # 'moto' o 'mototaxi'
    current_soc: float  # 0-100%
    target_soc: float = 100.0  # SOC objetivo
    arrival_hour: int = 0  # Hora de llegada
    departure_hour: int = 24  # Hora límite de salida
    is_connected: bool = True
    max_charge_rate_kw: float = 7.4  # Mode 3 @ 32A 230V
    
    def get_priority_weight(self) -> float:
        """Retorna peso de prioridad basado en SOC actual.
        100% > 80% > 70% > 50% > 30% > 20% > 10%
        """
        for soc_level in sorted(SOC_LEVELS, reverse=True):
            if self.current_soc >= soc_level:
                return SOC_PRIORITY_WEIGHTS[soc_level]
        return 0.05  # Mínimo absoluto
    
    def charge(self, power_kw: float, duration_h: float = 1.0) -> float:
        """Carga el vehículo y retorna energía consumida."""
        if not self.is_connected:
            return 0.0
        # Capacidad batería típica: moto=3kWh, mototaxi=5kWh
        battery_kwh = 3.0 if self.vehicle_type == 'moto' else 5.0
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
    n_vehicles_moto: int  # Vehículos esperando
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


# Escenarios de carga durante el día (basados en demanda real Iquitos)
CHARGING_SCENARIOS: List[ChargingScenario] = [
    # Madrugada: baja demanda, potencia completa
    ChargingScenario('NIGHT_LOW', 0, 5, 1.0, 5, 1, False),
    # Mañana temprano: demanda creciente
    ChargingScenario('MORNING_EARLY', 6, 8, 0.8, 15, 3, False),
    # Mañana: alta demanda (mototaxis trabajo)
    ChargingScenario('MORNING_PEAK', 9, 11, 0.5, 25, 6, True),  # ESCASEZ MEDIA
    # Mediodía: pico solar, buena potencia
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
    """Tracker de SOC para todos los vehículos (motos y mototaxis).
    
    Trackea simultáneamente:
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
        
        # Máximos alcanzados en episodio
        self.motos_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        self.mototaxis_max_at_soc: Dict[int, int] = {lvl: 0 for lvl in SOC_LEVELS}
        
        # Contadores de vehículos completamente cargados
        self.total_motos_charged_100: int = 0
        self.total_mototaxis_charged_100: int = 0
        
        # Estados actuales por socket
        self.vehicle_states: List[Optional[VehicleSOCState]] = [None] * (self.n_moto_sockets + self.n_mototaxi_sockets)
        
        # Métricas de priorización
        self.prioritization_score: float = 0.0
        self.scarcity_decisions: int = 0  # Número de decisiones bajo escasez
        self.correct_prioritizations: int = 0  # Priorizaciones correctas
    
    def spawn_vehicle(self, socket_id: int, hour: int, initial_soc: float = 20.0) -> VehicleSOCState:
        """Crea un vehículo nuevo en el socket dado."""
        vehicle_type = 'moto' if socket_id < self.n_moto_sockets else 'mototaxi'
        max_rate = 7.0 if vehicle_type == 'moto' else 7.4
        
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
        """Actualiza contadores de vehículos por nivel SOC."""
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
        """Calcula reward por correcta priorización durante escasez.
        
        Premia cuando: 100% > 80% > 70% > 50% > 30% > 20% > 10%
        Es decir, vehículos con mayor SOC deben recibir más potencia primero.
        """
        if available_power >= total_demand * 0.9:  # Sin escasez significativa
            return 0.0
        
        self.scarcity_decisions += 1
        
        # Calcular correlación entre prioridad de vehículo y potencia asignada
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
        
        # Calcular correlación Spearman (orden correcto de priorización)
        # Si la correlación es alta, el agente está priorizando correctamente
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
            reward += (n_motos + n_mototaxis * 1.5) * weight  # Mototaxis valen más (servicio público)
        return reward / 100.0  # Normalizar
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas completas de tracking."""
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
    """Configuración SAC ÓPTIMA - Parámetros según mejores prácticas.
    
    Hiperparámetros SAC (Soft Actor-Critic):
    =========================================
    - Replay buffer size: 1e5–1e6 (usamos 1e6 para GPU)
    - Warmup / random steps: 1e3–1e4 (learning_starts)
    - Batch size: 128–512 (usamos 256)
    - τ (tau) soft update: 0.005 (típico)
    - Update frequency: cada paso (train_freq)
    - Update-to-data ratio: 1-4 (gradient_steps)
    - α (alpha) / temperatura entropía: auto-tuning recomendado
    - Target entropy: -|A| (dimensión acciones)
    - Learning rates: 3e-4 (actor/critic/alpha)
    - γ (gamma): 0.99
    
    Métricas clave a monitorear:
    - Eval episodic return (sin ruido)
    - Actor loss, Critic Q1/Q2 loss
    - Mean Q-value (si se dispara → sobreestimación)
    - Entropy y α (si α → 0 rápido → muy determinístico)
    - Replay buffer fill %
    - Mean/Std de acciones y log_std
    
    Señales de problema:
    - Q-values creciendo sin control → reward muy grande / falta normalización
    - Entropía cae a 0 pronto → target_entropy/α mal / reward shaping agresivo
    """
    
    # ===== LEARNING RATES (TÍPICO 3e-4, OPTIMIZADO A 1e-4) =====
    learning_rate: float = 1e-4  # LR para actor, critic y alpha (reducido para convergencia más estable)
    # Nota: SB3 SAC usa mismo LR para actor/critic/alpha por defecto
    
    # ===== REPLAY BUFFER (1e5-1e6) =====
    buffer_size: int = 1_000_000  # 1M - recomendado para GPU
    learning_starts: int = 10_000  # Warmup: 1e4 random steps antes de entrenar
    
    # ===== BATCH Y UPDATES =====
    batch_size: int = 256  # 128-512, usamos 256
    train_freq: Tuple[int, str] = (1, 'step')  # Entrenar cada step
    gradient_steps: int = 2  # Updates por step (update-to-data ratio: aumentado para mejor estabilidad)
    
    # ===== SOFT UPDATE (τ = 0.005 TÍPICO) =====
    tau: float = 0.005  # Soft update coefficient para target networks
    target_update_interval: int = 1  # Update target cada N gradient steps
    
    # ===== DISCOUNT (γ = 0.99 TÍPICO) =====
    gamma: float = 0.99  # Discount factor
    
    # ===== ENTROPY (FORZAR EXPLORACIÓN v2.0) =====
    # NOTA v2.0: Cambiado de 'auto' a 0.2 para FORZAR exploración
    # Problema detectado: Con 'auto', α colapsa muy rápido (→ policy determinista)
    # Referencia: Haarnoja et al. recomienda ajustar si hay colapso temprano
    ent_coef: float = 0.2  # Fijo en lugar de 'auto' para mantener exploración
    target_entropy: str = 'auto'  # Target entropy = -|A| (dimensión acciones)
    # Si se especifica: target_entropy: float = -39.0  # -|A| = -39 para 39 acciones
    
    # ===== NETWORK ARCHITECTURE =====
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[512, 512], qf=[512, 512]),  # Actor/Critic 512x512
        'activation_fn': torch.nn.ReLU,
        'log_std_init': -3.0,  # Inicialización log_std para exploración
    })
    
    @classmethod
    def for_gpu(cls) -> 'SACConfig':
        """Configuración ÓPTIMA para SAC en GPU (RTX 4060, 8GB VRAM).
        
        Aggressive settings para hardware potente:
        - Buffer 1M (puede llegar a 2M si hay VRAM)
        - Batch 256
        - Networks 512x512
        - Warmup 10K steps
        """
        return cls(
            # Learning rates
            learning_rate=1e-4,  # Reducido de 3e-4 para convergencia más estable
            
            # Replay buffer
            buffer_size=1_000_000,  # 1M standard, 2M si hay VRAM
            learning_starts=10_000,  # 10K warmup (random exploration)
            
            # Batch y updates
            batch_size=256,
            train_freq=(1, 'step'),
            gradient_steps=2,  # Aumentado de 1 a 2 para mejor estabilidad
            
            # Soft update
            tau=0.005,
            target_update_interval=1,
            
            # Discount
            gamma=0.99,
            
            # Entropy (FORZAR EXPLORACIÓN v2.0)
            # NOTA: Cambiado de 'auto' a 0.2 para evitar colapso temprano de α
            ent_coef=0.2,  # Fijo para mantener exploración durante todo el training
            target_entropy='auto',  # = -|A| automáticamente
            
            # Networks
            policy_kwargs={
                'net_arch': dict(pi=[512, 512], qf=[512, 512]),
                'activation_fn': torch.nn.ReLU,
                'log_std_init': -3.0,
            }
        )
    
    @classmethod
    def for_cpu(cls) -> 'SACConfig':
        """Configuración para CPU (fallback, recursos limitados)."""
        return cls(
            learning_rate=1e-4,  # Reducido de 3e-4 para convergencia más estable
            buffer_size=100_000,  # 100K para CPU
            learning_starts=1_000,  # Warmup más corto
            batch_size=64,  # Batch pequeño
            train_freq=(1, 'step'),
            gradient_steps=2,  # Aumentado de 1 a 2
            tau=0.005,
            gamma=0.99,
            # NOTA v2.0: ent_coef=0.2 para forzar exploración (evita colapso de α)
            ent_coef=0.2,
            target_entropy='auto',
            policy_kwargs={
                'net_arch': dict(pi=[128, 128], qf=[128, 128]),
                'activation_fn': torch.nn.ReLU,
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


def load_observable_variables():
    """Cargar TODAS las 27 columnas observables del dataset_builder v5.5.
    
    RETORNA: DataFrame con (8760, 27) columnas indexadas por hora
    
    ESTRUCTURA:
    - CHARGERS (10): ev_* prefix
    - SOLAR (6): solar_* prefix
    - BESS (5): bess_* prefix
    - MALL (3): mall_* prefix
    - TOTALES (3): total_* prefix
    """
    from src.dataset_builder_citylearn.data_loader import (
        load_solar_data, load_chargers_data, load_bess_data, load_mall_demand_data,
        _extract_observable_variables
    )
    
    print('[LOAD] Cargando TODAS las variables observables (27 columnas) del dataset_builder...')
    
    try:
        # Cargar datos crudos
        solar_df = load_solar_data()
        chargers_df = load_chargers_data()
        bess_df = load_bess_data()
        mall_df = load_mall_demand_data()
        
        print(f'  ✅ Solar: {len(solar_df)} filas')
        print(f'  ✅ Chargers: {len(chargers_df)} filas, {chargers_df.shape[1]} columnas')
        print(f'  ✅ BESS: {len(bess_df)} filas')
        print(f'  ✅ Mall: {len(mall_df)} filas')
        
        # Extraer TODAS las variables observables (27 columnas)
        obs_df = _extract_observable_variables(solar_df, chargers_df, bess_df, mall_df)
        
        print(f'  ✅ Variables observables extraídas: {obs_df.shape[0]} horas × {obs_df.shape[1]} columnas')
        print(f'     Columnas: {list(obs_df.columns)}')
        
        return obs_df
    except Exception as e:
        print(f'  ❌ Error cargando observables: {e}')
        print(f'     Retornando None - se usará fallback normalizando datos manuales')
        return None


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
    # SOLAR - DEL DATASET PROCESADO - TODAS LAS COLUMNAS REALES
    # ====================================================================
    print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 año)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    # ✅ SOLAR = REAL hourly generation for Iquitos 2024 (8760 hours)
    solar_path: Path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Solar CSV no encontrado: {solar_path}")
    
    df_solar = pd.read_csv(solar_path)
    
    # ===== CARGAR TODAS LAS COLUMNAS SOLARES REALES =====
    solar_data = {}
    
    # Irradiancia (REAL - PVGIS)
    if 'ghi_wm2' in df_solar.columns:
        solar_data['ghi_wm2'] = df_solar['ghi_wm2'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'dni_wm2' in df_solar.columns:
        solar_data['dni_wm2'] = df_solar['dni_wm2'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'dhi_wm2' in df_solar.columns:
        solar_data['dhi_wm2'] = df_solar['dhi_wm2'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Clima (REAL - PVGIS)
    if 'temp_air_c' in df_solar.columns:
        solar_data['temp_air_c'] = df_solar['temp_air_c'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'wind_speed_ms' in df_solar.columns:
        solar_data['wind_speed_ms'] = df_solar['wind_speed_ms'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Potencia generada (REAL - PVLib simulation)
    if 'dc_power_kw' in df_solar.columns:
        solar_data['dc_power_kw'] = df_solar['dc_power_kw'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'ac_power_kw' in df_solar.columns:
        solar_data['ac_power_kw'] = df_solar['ac_power_kw'].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Energía (REAL)
    if 'dc_energy_kwh' in df_solar.columns:
        solar_data['dc_energy_kwh'] = df_solar['dc_energy_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'ac_energy_kwh' in df_solar.columns:
        solar_data['ac_energy_kwh'] = df_solar['ac_energy_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
    if 'pv_generation_kwh' in df_solar.columns:
        solar_data['pv_generation_kwh'] = df_solar['pv_generation_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
    
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
    print(f'  [SOLAR] Columnas cargadas: {list(solar_data.keys())}')
    if 'ghi_wm2' in solar_data:
        print(f'  [SOLAR]   GHI: max={solar_data["ghi_wm2"].max():.0f} W/m², sum={solar_data["ghi_wm2"].sum():,.0f}')
    if 'temp_air_c' in solar_data:
        print(f'  [SOLAR]   Temp: min={solar_data["temp_air_c"].min():.1f}°C, max={solar_data["temp_air_c"].max():.1f}°C')

    # ====================================================================
    # CHARGERS - ✅ REAL HOURLY DEMAND (MOTOS + MOTOTAXIS SEPARADOS)
    # ====================================================================
    # Status: REAL - Measured EV charging demand profiles
    # CORRECCIÓN: Usar chargers_ev_ano_2024_v3.csv con 38 sockets (ESPECIFICACIÓN OE2)
    # NO usar chargers_real_hourly_2024.csv (128 sockets, formato incorrecto)
    v3_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    
    if not v3_path.exists():
        raise FileNotFoundError(
            f"OBLIGATORIO: chargers_ev_ano_2024_v3.csv NO ENCONTRADO\n"
            f"  Ruta esperada: {v3_path}\n"
            f"  ERROR: No hay datos REALES de 38 sockets."
        )
    
    print(f'  [CHARGERS] ✅ REAL: Loading from {v3_path.name}')
    df_chargers = pd.read_csv(v3_path)
    
    # ===== PROCESAR ARCHIVO v3: EXTRAER POTENCIA DE CARGA =====
    # Estructura: socket_XXX_charger_power_kw para cada socket 0-37 (38 total)
    # 38 sockets × 9 columnas/socket + 1 datetime = 343 columnas
    socket_power_cols = [c for c in df_chargers.columns if c.endswith('_charger_power_kw')]
    
    if len(socket_power_cols) != 38:
        raise ValueError(
            f"ERROR: Se esperan 38 sockets, pero se encontraron {len(socket_power_cols)}\n"
            f"  Columnas de potencia encontradas: {len(socket_power_cols)}\n"
            f"  Archivo: {v3_path}"
        )
    
    # Ordenar columnas de socket por índice numérico
    socket_power_cols.sort(key=lambda x: int(x.split('_')[1]))
    
    # Extraer datos de poder de carga (kW) para cada socket
    chargers_hourly = df_chargers[socket_power_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    # Separar motos (sockets 0-29) y mototaxis (sockets 30-37)
    chargers_moto_hourly = chargers_hourly[:, :30].astype(np.float32)  # Sockets 0-29 (30 motos)
    chargers_mototaxi_hourly = chargers_hourly[:, 30:38].astype(np.float32)  # Sockets 30-37 (8 mototaxis)
    
    n_sockets = chargers_hourly.shape[1]
    n_moto_sockets = chargers_moto_hourly.shape[1]
    n_mototaxi_sockets = chargers_mototaxi_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    moto_demand = float(np.sum(chargers_moto_hourly))
    mototaxi_demand = float(np.sum(chargers_mototaxi_hourly))
    
    print(f"  [CHARGERS] ✅ REAL: {n_sockets} sockets total (ESPECIFICACIÓN OE2: 38)")
    print(f"  [CHARGERS]   MOTOS:     {n_moto_sockets} sockets | {moto_demand:,.0f} kWh/año | {moto_demand/HOURS_PER_YEAR:.1f} kW avg")
    print(f"  [CHARGERS]   MOTOTAXIS: {n_mototaxi_sockets} sockets | {mototaxi_demand:,.0f} kWh/año | {mototaxi_demand/HOURS_PER_YEAR:.1f} kW avg")
    print(f"  [CHARGERS]   TOTAL:     {total_demand:,.0f} kWh/año | {total_demand/HOURS_PER_YEAR:.1f} kW avg")
    
    if len(chargers_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Chargers: {len(chargers_hourly)} hours != {HOURS_PER_YEAR}")

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
    bess_real_path = Path('data/oe2/bess/bess_ano_2024.csv')
    
    # PRIORITY 2: Paths procesados (fallback)
    bess_fallback_paths = [
        Path('data/processed/citylearn/iquitos_ev_mall/bess') / 'bess_ano_2024.csv',
        Path('data/interim/oe2/bess/bess_ano_2024.csv'),
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
        
        # ===== CARGAR DATOS REALES DE COSTOS =====
        bess_costs = None
        if 'cost_grid_import_soles' in df_bess.columns:
            bess_costs = df_bess['cost_grid_import_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
        
        # Ahorros por reducción de picos (REAL)
        bess_peak_savings = None
        if 'peak_reduction_savings_soles' in df_bess.columns:
            bess_peak_savings = df_bess['peak_reduction_savings_soles'].values[:HOURS_PER_YEAR].astype(np.float32)
        
        # Tarifa OSINERGMIN (REAL)
        bess_tariff = None
        if 'tariff_osinergmin_soles_kwh' in df_bess.columns:
            bess_tariff = df_bess['tariff_osinergmin_soles_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
        
        # ===== CARGAR DATOS REALES DE CO2 =====
        bess_co2_avoided = None
        if 'co2_avoided_indirect_kg' in df_bess.columns:
            bess_co2_avoided = df_bess['co2_avoided_indirect_kg'].values[:HOURS_PER_YEAR].astype(np.float32)
        
        # Grid CO2 factor (constant for Iquitos isolated grid)
        bess_co2_grid = np.full(HOURS_PER_YEAR, CO2_FACTOR_IQUITOS, dtype=np.float32)
        
        # ===== CARGAR FLUJOS DE ENERGÍA REALES =====
        energy_flows = {}
        flow_columns = [
            'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
            'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
            'grid_to_ev_kwh', 'grid_to_mall_kwh', 'grid_to_bess_kwh', 'grid_import_total_kwh'
        ]
        for col in flow_columns:
            if col in df_bess.columns:
                energy_flows[col] = df_bess[col].values[:HOURS_PER_YEAR].astype(np.float32)
        
        bess_co2 = {
            'grid_kg': bess_co2_grid,
            'avoided_kg': bess_co2_avoided,
        }
        
        print(f"  [BESS] Simulated avg SOC: {float(np.mean(bess_soc)):.1f}%")
        if bess_costs is not None:
            print(f"  [BESS] Costos grid:         {float(np.sum(bess_costs)):,.2f} soles/año")
        if bess_peak_savings is not None:
            print(f"  [BESS] Ahorros pico:        {float(np.sum(bess_peak_savings)):,.2f} soles/año")
        if bess_co2_avoided is not None:
            print(f"  [BESS] CO2 evitado indirecto: {float(np.sum(bess_co2_avoided)):,.0f} kg/año")
        if 'pv_to_ev_kwh' in energy_flows:
            print(f"  [BESS] Solar→EV:            {float(np.sum(energy_flows['pv_to_ev_kwh'])):,.0f} kWh/año")
        if 'bess_to_ev_kwh' in energy_flows:
            print(f"  [BESS] BESS→EV:             {float(np.sum(energy_flows['bess_to_ev_kwh'])):,.0f} kWh/año")
        if 'grid_import_total_kwh' in energy_flows:
            print(f"  [BESS] Grid import total:   {float(np.sum(energy_flows['grid_import_total_kwh'])):,.0f} kWh/año")
    
    
    # ====================================================================
    # CARGAR ESTADÍSTICAS DE CHARGERS
    # ====================================================================
    charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
    charger_max_power_kw = np.full(n_sockets, 7.0, dtype=np.float32)  # Default motos
    charger_mean_power_kw = np.full(n_sockets, 2.5, dtype=np.float32)
    
    if charger_stats_path.exists():
        df_stats = pd.read_csv(charger_stats_path)
        print(f"  [CHARGER STATS] Cargada desde: {charger_stats_path.name}")
        # Opcional: extraer estadísticas reales si existen en el CSV
    
    # ====================================================================
    # CARGAR DEMANDAS REALES DEL DATASET BESS (ev_demand, mall_demand)
    # ====================================================================
    bess_ev_demand = None
    bess_mall_demand = None
    bess_pv_generation = None
    if df_bess is not None:
        if 'ev_demand_kwh' in df_bess.columns:
            bess_ev_demand = df_bess['ev_demand_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"  [BESS] EV Demand (REAL):    {float(np.sum(bess_ev_demand)):,.0f} kWh/año")
        if 'mall_demand_kwh' in df_bess.columns:
            bess_mall_demand = df_bess['mall_demand_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"  [BESS] Mall Demand (REAL):  {float(np.sum(bess_mall_demand)):,.0f} kWh/año")
        if 'pv_generation_kwh' in df_bess.columns:
            bess_pv_generation = df_bess['pv_generation_kwh'].values[:HOURS_PER_YEAR].astype(np.float32)
            print(f"  [BESS] PV Gen (REAL):       {float(np.sum(bess_pv_generation)):,.0f} kWh/año")
    
    print()
    # ====================================================================
    # CARGAR TODAS LAS 27 VARIABLES OBSERVABLES DEL DATASET_BUILDER
    # ====================================================================
    print('[LOAD] Extrayendo TODAS las variables observables del dataset_builder v5.5...')
    observable_variables_df = load_observable_variables()
    
    print()
    # RETORNAR: todos los datos necesarios para entrenamiento CON DATOS REALES COMPLETOS
    return {
        # Solar (REAL - PVGIS + PVLib)
        'solar': solar_hourly,
        'solar_data': solar_data,  # Todas las columnas: ghi, dni, dhi, temp, wind, dc/ac power
        
        # Chargers (REAL - mediciones)
        'chargers': chargers_hourly,
        'chargers_moto': chargers_moto_hourly,
        'chargers_mototaxi': chargers_mototaxi_hourly,
        'n_moto_sockets': n_moto_sockets,
        'n_mototaxi_sockets': n_mototaxi_sockets,
        
        # Mall (REAL)
        'mall': mall_hourly,
        
        # BESS - SOC y operación (SIMULADO pero basado en datos reales)
        'bess_soc': bess_soc,
        'bess_costs': bess_costs,
        'bess_peak_savings': bess_peak_savings,
        'bess_tariff': bess_tariff,
        'bess_co2': bess_co2,
        
        # Flujos de energía (REAL del dataset BESS)
        'energy_flows': energy_flows,
        'bess_ev_demand': bess_ev_demand,       # Demanda EV real por hora
        'bess_mall_demand': bess_mall_demand,   # Demanda mall real por hora
        'bess_pv_generation': bess_pv_generation,  # PV real por hora
        
        # Estadísticas chargers
        'charger_max_power_kw': charger_max_power_kw,
        'charger_mean_power_kw': charger_mean_power_kw,
        
        # 🆕 TODAS LAS 27 VARIABLES OBSERVABLES DEL DATASET_BUILDER
        'observable_variables': observable_variables_df,  # DataFrame (8760, 27) con todas las columnas reales
    }

# ===== TRAINING LOOP =====

def main():
    """Entrenar SAC con multiobjetivo."""
    
    # Load datasets
    datasets = load_datasets_from_processed()
    
    # Desempaquetar datos cargados - TODOS LOS DATOS REALES
    solar_hourly = datasets['solar']
    solar_data = datasets.get('solar_data', {})  # Todas columnas solares
    chargers_hourly = datasets['chargers']
    chargers_moto = datasets.get('chargers_moto')  # Sockets motos
    chargers_mototaxi = datasets.get('chargers_mototaxi')  # Sockets mototaxis
    n_moto_sockets = datasets.get('n_moto_sockets', 0)
    n_mototaxi_sockets = datasets.get('n_mototaxi_sockets', 0)
    mall_hourly = datasets['mall']
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
    
    print('[4] CONFIGURAR AGENTE SAC CON DATOS 100% REALES')
    print('-' * 80)
    print(f'  === SOLAR (PVGIS + PVLib) ===')
    print(f'  Solar AC Power:  cargado ✓ ({len(solar_hourly)} horas, {np.sum(solar_hourly):,.0f} kWh/año)')
    if solar_data:
        print(f'  Solar Columnas:  {len(solar_data)} columnas REALES: {list(solar_data.keys())}')
    print()
    print(f'  === CHARGERS (MEDICIONES) ===')
    print(f'  MOTOS:           {n_moto_sockets} sockets | {np.sum(chargers_moto) if chargers_moto is not None else 0:,.0f} kWh/año')
    print(f'  MOTOTAXIS:       {n_mototaxi_sockets} sockets | {np.sum(chargers_mototaxi) if chargers_mototaxi is not None else 0:,.0f} kWh/año')
    print(f'  TOTAL:           {chargers_hourly.shape[1]} sockets | {np.sum(chargers_hourly):,.0f} kWh/año')
    print()
    print(f'  === MALL (MEDICIONES) ===')
    print(f'  Mall demand:     cargado ✓ ({np.sum(mall_hourly):,.0f} kWh/año)')
    print()
    print(f'  === BESS (SIMULACIÓN CON DATOS REALES) ===')
    print(f'  BESS SOC:        cargado ✓ (avg: {np.mean(bess_soc):.1f}%)')
    if bess_costs is not None:
        print(f'  BESS Costos:     cargado ✓ ({np.sum(bess_costs):,.0f} soles/año)')
    if bess_peak_savings is not None:
        print(f'  BESS Peak Svngs: cargado ✓ ({np.sum(bess_peak_savings):,.0f} soles/año)')
    if bess_tariff is not None:
        print(f'  Tarifa OSINERG:  cargado ✓ (mean: {np.mean(bess_tariff):.4f} sol/kWh)')
    if bess_co2 is not None and bess_co2.get('avoided_kg') is not None:
        print(f'  CO2 Evitado:     cargado ✓ ({np.sum(bess_co2["avoided_kg"]):,.0f} kg/año)')
    if energy_flows:
        print(f'  Energy Flows:    cargado ✓ ({len(energy_flows)} flujos)')
    print()
    print(f'  === DEMANDAS REALES (DATASET BESS) ===')
    if bess_ev_demand is not None:
        print(f'  EV Demand REAL:  {np.sum(bess_ev_demand):,.0f} kWh/año')
    if bess_mall_demand is not None:
        print(f'  Mall Dem REAL:   {np.sum(bess_mall_demand):,.0f} kWh/año')
    if bess_pv_generation is not None:
        print(f'  PV Gen REAL:     {np.sum(bess_pv_generation):,.0f} kWh/año')
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
        
        COMUNICACIÓN COMPLETA DEL SISTEMA v5.3
        ================================================================================
        El agente puede ver y coordinar TODOS los componentes del sistema:
        - BESS: estado, energía disponible, señales de carga/descarga
        - Solar: generación, excedente, ratio de uso para EVs
        - 38 Sockets: demanda, potencia, ocupación individual
        - Motos: cantidad cargando, en cola, SOC, tiempo restante
        - Mototaxis: igual que motos pero para sus 8 sockets
        - Coordinación: señales para optimizar flujo de energía
        
        Observation Space (156-dim v5.3):
        
        ENERGÍA DEL SISTEMA [0-7] (8 features):
        - [0]: Solar generation normalizada [0,1]
        - [1]: Mall demand normalizada [0,1]
        - [2]: BESS SOC [0,1]
        - [3]: BESS energía disponible normalizada
        - [4]: Solar excedente normalizado
        - [5]: Grid import necesario normalizado
        - [6]: Balance energético (-1 déficit, +1 excedente)
        - [7]: Capacidad EV libre normalizada
        
        ESTADO DE CARGADORES POR SOCKET [8-45] (38 sockets):
        - Demanda actual de cada socket normalizada [0,1]
        
        POTENCIA ACTUAL POR SOCKET [46-83] (38 sockets):
        - Potencia entregada a cada socket normalizada [0,1]
        
        OCUPACIÓN POR SOCKET [84-121] (38 sockets):
        - 1.0 si hay vehículo conectado, 0.0 si libre
        
        ESTADO DE VEHÍCULOS [122-137] (16 features):
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
        - [137]: CO2 evitado potencial si carga más (norm)
        
        TIME FEATURES [138-143] (6 features):
        - [138]: Hora del día normalizada [0,1]
        - [139]: Día de semana normalizado [0,1]
        - [140]: Mes normalizado [0,1]
        - [141]: Indicador hora pico [0,1]
        - [142]: Factor CO2 Iquitos
        - [143]: Tarifa eléctrica (USD/kWh)
        
        COMUNICACIÓN INTER-SISTEMA [144-155] (12 features):
        - [144]: BESS puede suministrar a EVs [0,1]
        - [145]: Solar suficiente para demanda EV [0,1]
        - [146]: Grid necesario para completar carga [0,1]
        - [147]: Prioridad carga motos vs mototaxis [0,1]
        - [148]: Urgencia de carga (vehículos pendientes/capacidad)
        - [149]: Oportunidad solar (excedente/demanda EV)
        - [150]: BESS debería cargar (solar alto, demanda baja)
        - [151]: BESS debería descargar (solar bajo, demanda alta)
        - [152]: Potencial reducción CO2 con más carga
        - [153]: Saturación del sistema [0,1]
        - [154]: Eficiencia sistema completo [0,1]
        - [155]: Meta diaria de vehículos (progreso [0,1])

        Action Space (39-dim v5.2):
        - [0]: BESS control [0,1] (0=carga máx, 0.5=idle, 1=descarga máx)
        - [1:39]: 38 socket setpoints [0,1] (potencia asignada a cada socket)
        """
        
        HOURS_PER_YEAR: int = 8760
        NUM_CHARGERS: int = 38  # v5.2: 19 chargers × 2 sockets
        OBS_DIM: int = 246      # 🆕 v6.0: 156 (v5.3 base) + 27 (observables) + 38 (per-socket SOC) + 38 (time remaining) + 7 (communication)
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
                     observable_variables=None):
            super().__init__()
            self.solar = solar_kw
            self.solar_data = solar_data or {}  # Todas las columnas solares REALES
            self.chargers = chargers_kw
            self.observable_variables = observable_variables  # 🆕 27 columnas observables del dataset_builder
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
            
            # Métricas de priorización por episodio
            self.episode_prioritization_reward = 0.0
            self.episode_completion_reward = 0.0
            
            # Métricas BESS por episodio
            self.episode_bess_discharge_kwh = 0.0
            self.episode_bess_charge_kwh = 0.0
            self.episode_bess_cycles = 0  # Número de ciclos carga/descarga
            self._last_bess_action = 0.5  # Para detectar cambios
            
            # Métricas CO2 por episodio
            self.episode_co2_directo_evitado_kg = 0.0   # EVs vs gasolina
            self.episode_co2_indirecto_evitado_kg = 0.0  # Solar vs grid
            self.episode_co2_grid_kg = 0.0              # Emisiones del grid
            
            # Métricas de costos por episodio
            self.episode_costo_grid_soles = 0.0
            self.episode_ahorro_solar_soles = 0.0
            self.episode_ahorro_bess_soles = 0.0
            
            # ===== MÉTRICAS REALES (CARGADAS DE DATASETS) =====
            self.episode_real_pv_to_ev_kwh = 0.0       # Solar directo a EVs
            self.episode_real_bess_to_ev_kwh = 0.0     # BESS a EVs
            self.episode_real_grid_import_kwh = 0.0    # Importación grid total
            self.episode_real_co2_avoided_kg = 0.0     # CO2 evitado indirecto (REAL)
            self.episode_real_cost_soles = 0.0         # Costo grid (REAL)
            self.episode_real_peak_savings = 0.0       # Ahorro picos (REAL)
            
            # [v5.3] ESTADO DE VEHÍCULOS (para comunicación del sistema)
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
            
            # [v5.3] COMUNICACIÓN INTER-SISTEMA
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
            
            # Reset métricas de priorización
            self.episode_prioritization_reward = 0.0
            self.episode_completion_reward = 0.0
            
            # Reset métricas BESS
            self.episode_bess_discharge_kwh = 0.0
            self.episode_bess_charge_kwh = 0.0
            self.episode_bess_cycles = 0
            self._last_bess_action = 0.5
            
            # Reset métricas CO2
            self.episode_co2_directo_evitado_kg = 0.0
            self.episode_co2_indirecto_evitado_kg = 0.0
            self.episode_co2_grid_kg = 0.0
            
            # Reset métricas costos
            self.episode_costo_grid_soles = 0.0
            self.episode_ahorro_solar_soles = 0.0
            self.episode_ahorro_bess_soles = 0.0
            
            # Reset métricas REALES (de datasets)
            self.episode_real_pv_to_ev_kwh = 0.0
            self.episode_real_bess_to_ev_kwh = 0.0
            self.episode_real_grid_import_kwh = 0.0
            self.episode_real_co2_avoided_kg = 0.0
            self.episode_real_cost_soles = 0.0
            self.episode_real_peak_savings = 0.0
            
            # [v5.3] RESET ESTADO DE VEHÍCULOS
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
            
            # [v5.3] RESET COMUNICACIÓN INTER-SISTEMA
            self.bess_available_kwh = 0.0
            self.solar_surplus_kwh = 0.0
            self.current_grid_import = 0.0
            self.system_efficiency = 0.0
            
            # Inicializar vehículos en sockets (SOC inicial ~0-5% según dataset real: llegan vacíos)
            for socket_id in range(self.NUM_CHARGERS):
                initial_soc = np.random.uniform(0.0, 5.0)  # Dataset real: vehículos llegan vacíos
                self.soc_tracker.spawn_vehicle(socket_id, hour=0, initial_soc=initial_soc)
            
            obs = self._make_observation(0)
            return obs, {}
        
        def step(self, action):
            h = self.current_step
            hour_24 = h % 24
            
            # ===== USAR DATOS REALES CUANDO ESTÉN DISPONIBLES =====
            # Prioridad: dataset BESS > datos chargers > cálculo sintético
            
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
            
            # ===== USAR FLUJOS DE ENERGÍA REALES SI DISPONIBLES =====
            # Estos son los flujos calculados en la simulación BESS
            real_pv_to_ev = float(self.energy_flows.get('pv_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_to_ev = float(self.energy_flows.get('bess_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_grid_to_ev = float(self.energy_flows.get('grid_to_ev_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_grid_import = float(self.energy_flows.get('grid_import_total_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_discharge = float(self.energy_flows.get('bess_discharge_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            real_bess_charge = float(self.energy_flows.get('bess_charge_kwh', np.zeros(8760))[h]) if h < 8760 else 0.0
            
            # Parsear acción: [bess_action(1), charger_actions(38)]
       
            bess_action = float(action[0]) if len(action) > 0 else 0.5
            charger_actions = action[1:1+self.n_chargers] if len(action) > 1 else np.zeros(self.n_chargers)
            
            # ===== DETERMINAR ESCENARIO DE CARGA ACTUAL =====
            # Seleccionar escenario basado en hora del día
            self.current_scenario = None
            for scenario in CHARGING_SCENARIOS:
                if scenario.hour_start <= hour_24 <= scenario.hour_end:
                    self.current_scenario = scenario
                    break
            
            # Calcular potencia disponible (afectada por escenario de escasez)
            available_power_ratio = self.current_scenario.available_power_ratio if self.current_scenario else 1.0
            max_available_power = (solar_h + BESS_MAX_POWER_KW * bess_soc_h / 100.0) * available_power_ratio
            
            # ===== SIMULACIÓN FÍSICA CON ACCIONES Y ESCASEZ =====
            # BESS: action[0] controla carga/descarga
            # Chargers: action[1:39] controla modulación (0-1 → 0-7.4 kW por socket)
            
            bess_discharge = max(0, bess_action - 0.5) * BESS_MAX_POWER_KW
            
            # ===== CARGAR VEHÍCULOS SEGÚN ACCIONES Y PRIORIDAD =====
            # Cuando hay ESCASEZ, el agente debe aprender a priorizar vehículos con mayor SOC
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
                    # Aplicar restricción de potencia proporcional
                    requested_power *= available_power_ratio
                
                # Entregar energía al vehículo (actualiza SOC)
                energy = state.charge(requested_power, duration_h=1.0)
                total_energy_delivered += energy
                total_charging_power += requested_power
                
                # Verificar si vehículo alcanzó 100% y contar
                if state.current_soc >= 100.0:
                    if state.vehicle_type == 'moto':
                        self.soc_tracker.total_motos_charged_100 += 1
                    else:
                        self.soc_tracker.total_mototaxis_charged_100 += 1
                    state.is_connected = False  # Desconectar vehículo cargado
            
            # Actualizar contadores de SOC por nivel
            self.soc_tracker.update_counts()
            
            # Modular demanda total de chargers
            charger_power_modulated = total_charging_power
            
            # ===== BALANCE ENERGÉTICO (USAR DATOS REALES SI DISPONIBLES) =====
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
            
            # ===== CÁLCULO DE CO2 (USAR DATOS REALES CUANDO DISPONIBLES) =====
            # Factor CO2 gasolina para motos/mototaxis: ~2.31 kg CO2/litro
            GASOLINA_KG_CO2_PER_LITRO = 2.31
            MOTO_LITROS_PER_100KM = 2.0
            MOTOTAXI_LITROS_PER_100KM = 3.0
            MOTO_KM_PER_KWH = 50.0
            MOTOTAXI_KM_PER_KWH = 30.0
            
            # CO2 DIRECTO: Emisiones evitadas por usar EV en lugar de gasolina
            # Usar proporción real de sockets motos/mototaxis
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
            
            co2_directo_evitado_kg = (litros_evitados_motos + litros_evitados_mototaxis) * GASOLINA_KG_CO2_PER_LITRO
            
            # CO2 INDIRECTO: USAR DATO REAL si disponible, sino calcular CON PEAK SHAVING
            if self.bess_co2 is not None and self.bess_co2.get('avoided_kg') is not None:
                if h < len(self.bess_co2['avoided_kg']):
                    co2_indirecto_evitado_kg = float(self.bess_co2['avoided_kg'][h])  # REAL
                else:
                    # Calcular: solar + BESS con peak shaving
                    solar_used = min(solar_h, charger_power_modulated + mall_demand_h)
                    
                    # BESS descargando con peak shaving
                    bess_discharge_benefit = bess_discharge_actual
                    if mall_demand_h > 2000.0:
                        # En pico: BESS reemplaza 100% + bonus por reducción de pico
                        peak_shaving_factor = 1.0 + (mall_demand_h - 2000.0) / max(1.0, mall_demand_h) * 0.5
                    else:
                        # Baseline: BESS aún ayuda con factor reducido
                        peak_shaving_factor = 0.5 + (mall_demand_h / 2000.0) * 0.5
                    
                    bess_co2_benefit = bess_discharge_benefit * peak_shaving_factor
                    
                    co2_indirecto_evitado_kg = (solar_used + bess_co2_benefit) * CO2_FACTOR_IQUITOS
            else:
                # Calcular: solar + BESS con peak shaving
                solar_used = min(solar_h, charger_power_modulated + mall_demand_h)
                
                # BESS descargando con peak shaving
                bess_discharge_benefit = bess_discharge_actual
                if mall_demand_h > 2000.0:
                    # En pico: BESS reemplaza 100% + bonus por reducción de pico
                    peak_shaving_factor = 1.0 + (mall_demand_h - 2000.0) / max(1.0, mall_demand_h) * 0.5
                else:
                    # Baseline: BESS aún ayuda con factor reducido
                    peak_shaving_factor = 0.5 + (mall_demand_h / 2000.0) * 0.5
                
                bess_co2_benefit = bess_discharge_benefit * peak_shaving_factor
                
                co2_indirecto_evitado_kg = (solar_used + bess_co2_benefit) * CO2_FACTOR_IQUITOS
            
            # CO2 GRID: Emisiones por importar del grid térmico
            co2_grid_kg = grid_import * CO2_FACTOR_IQUITOS
            
            # ===== CÁLCULO DE COSTOS Y AHORROS (USAR DATOS REALES) =====
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
            
            # Ahorro por usar solar (energía gratis)
            ahorro_solar_soles = solar_used * tarifa_actual
            
            # Ahorro por usar BESS (descarga durante hora punta) - REAL si disponible
            if self.bess_peak_savings is not None and h < len(self.bess_peak_savings):
                ahorro_bess_soles = float(self.bess_peak_savings[h])  # REAL
            else:
                ahorro_bess_soles = bess_discharge_actual * tarifa_actual if is_hora_punta else 0.0
            
            # ===== CÁLCULO DE COMPONENTES DE REWARD MULTIOBJETIVO v5.3 =====
            # PRIORIZA CARGAR MÁS VEHÍCULOS para reducir CO2 directo e indirecto
            
            # 1. CO2 GRID (minimizar importación)
            co2_reward = -co2_grid_kg / 1000.0
            
            # 2. SOLAR (maximizar autoconsumo)
            solar_self_consumption = min(solar_h, total_demand)
            solar_reward = solar_self_consumption / max(1.0, total_demand)
            
            # 3. EV SATISFACTION (chargers reciben potencia solicitada)
            charger_satisfaction = total_energy_delivered / max(1.0, chargers_demand_h)
            ev_reward = min(1.0, charger_satisfaction)
            
            # 4. COST (minimizar importación cara, preferir solar gratis)
            cost_penalty = grid_import * 0.1
            cost_reward = -cost_penalty / 100.0
            
            # 5. GRID STABILITY (penalizar cambios grandes en demanda)
            bess_dispatch_smoothness = 1.0 - abs(bess_action - 0.5) * 0.1
            stability_reward = bess_dispatch_smoothness
            
            # ===== 6. REWARD DE PRIORIZACIÓN (NUEVO) =====
            # Premia cuando: 100% > 80% > 70% > 50% > 30% > 20% > 10%
            # Solo activo durante escasez de potencia
            prioritization_reward = self.soc_tracker.get_prioritization_reward(
                action, max_available_power, total_demand
            )
            
            # 7. REWARD DE COMPLETACIÓN (NUEVO)
            # Premia vehículos que alcanzan niveles altos de SOC
            completion_reward = self.soc_tracker.get_completion_reward()
            
            # ================================================================
            # [v5.3] REWARD QUE PRIORIZA CARGAR MÁS VEHÍCULOS
            # ================================================================
            # Contar vehículos cargando por tipo
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
            
            # Total vehículos cargando vs capacidad máxima (38 sockets)
            total_vehicles = motos_charging_count + mototaxis_charging_count
            vehicles_ratio = total_vehicles / 38.0  # MAX 38
            
            # Componentes de reward v5.3:
            r_vehicles_charging = vehicles_ratio * 0.25        # 25% - Más vehículos cargando
            r_vehicles_100 = (motos_100_count + taxis_100_count) / 309.0 * 0.20  # 20% - Completar al 100%
            r_co2_avoided = np.clip((co2_directo_evitado_kg + co2_indirecto_evitado_kg) / 50.0, 0.0, 0.10)  # 10% - CO2 evitado
            
            # Penalizar grid import alto (incentiva solar)
            r_grid_penalty = -np.clip(grid_import / 500.0, 0.0, 0.10)  # -10% max
            
            # Bonus por usar solar para EVs
            if charger_power_modulated > 0.1:
                solar_for_ev = min(solar_h, charger_power_modulated) / charger_power_modulated
            else:
                solar_for_ev = 0.0
            r_solar_to_ev = solar_for_ev * 0.10  # 10% - Solar → EV
            
            # Bonus BESS (descargar durante pico, cargar con excedente)
            bess_direction = bess_action - 0.5  # -0.5 → +0.5
            is_peak = 6 <= hour_24 <= 22
            if is_peak and solar_h < chargers_demand_h and bess_direction > 0:
                r_bess = 0.08  # Bonus: descargar BESS cuando hay déficit solar
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
            
            # Time penalty: urgencia de completar vehículos antes de fin de día
            hour_norm = hour_24 / 24.0
            daily_target = 309  # 270 motos + 39 mototaxis
            daily_completed = self.soc_tracker.total_motos_charged_100 + self.soc_tracker.total_mototaxis_charged_100
            if hour_norm > 0.5:  # Segunda mitad del día
                progress = daily_completed / daily_target
                r_time_urgency = 0.02 if progress > hour_norm else -0.02
            else:
                r_time_urgency = 0.0
            
            # COMBINAR REWARD COMPONENTS v5.3
            reward_custom = (
                r_vehicles_charging +  # 25% - Prioridad #1: Más vehículos cargando
                r_vehicles_100 +       # 20% - Prioridad #2: Completar cargas
                r_co2_avoided +        # 10% - CO2 evitado
                r_grid_penalty +       # -10% max - Penalidad grid
                r_solar_to_ev +        # 10% - Usar solar para EVs
                r_bess +               # 8% - Coordinación BESS
                r_socket_eff +         # 5% - Eficiencia sockets
                r_time_urgency         # ±2% - Urgencia temporal
            )
            
            # ===== REWARD MULTIOBJETIVO v6.0 (NUEVO: w_vehicles_charged = 0.25) =====
            # v6.0 rebalances weights para MAXIMIZAR VEHÍCULOS sin degradar CO2
            # 
            # w_co2 = 0.45           (Evitar grid import de térmico)
            # w_solar = 0.15         (Usar solar directamente)
            # w_vehicles_charged = 0.25 (🆕 MAXIMIZAR MOTOS + MOTOTAXIS a 100%)
            # w_stability = 0.05     (Estabilidad grid)
            # w_bess_eff = 0.05      (Eficiencia BESS)
            # w_prioritization = 0.05 (Respetar urgencia)
            # Total = 1.00
            
            W_CO2 = 0.45
            W_SOLAR = 0.15
            W_VEHICLES_CHARGED = 0.25  # 🆕 NEW v6.0
            W_STABILITY = 0.05
            W_BESS_EFF = 0.05
            W_PRIORITIZATION = 0.05
            
            # Calcula reward com pesos explícitos v6.0
            if self.reward_weights is not None:
                # Usar reward_weights pero ajustados a v6.0
                base_reward = (
                    W_CO2 * co2_reward +
                    W_SOLAR * solar_reward +
                    W_VEHICLES_CHARGED * ev_reward +  # 🆕 Rebalanced: was ev_satisfaction
                    0.04 * cost_reward +               # Costo (reducido)
                    W_STABILITY * stability_reward
                )
            else:
                # No hay weights explícitos: construcción manual v6.0
                # CO2: minimizar grid import (directo)
                co2_component = W_CO2 * (-grid_import / 500.0)
                
                # SOLAR: maximizar autoconsumo directo
                solar_component = W_SOLAR * (solar_h / max(1.0, total_demand))
                
                # VEHICLES CHARGED: maximizar vehículos a 100% (🆕)
                total_charged_100 = motos_100_count + taxis_100_count
                vehicles_component = W_VEHICLES_CHARGED * (total_vehicles / 38.0)  # Cargando ahora
                
                # STABILITY: suavizar cambios en BESS
                stability_component = W_STABILITY * (1.0 - abs(bess_action - 0.5))
                
                # BESS EFFICIENCY: descargar en pico, cargar en valle
                if is_peak and bess_action > 0.55:  # Descargando en pico
                    bess_eff_component = W_BESS_EFF * 0.2
                elif not is_peak and bess_action < 0.45:  # Cargando en valle
                    bess_eff_component = W_BESS_EFF * 0.2
                else:
                    bess_eff_component = -W_BESS_EFF * 0.1
                
                # PRIORITIZATION: respetar urgencia
                prioritization_component = W_PRIORITIZATION * prioritization_reward
                
                base_reward = (
                    co2_component +
                    solar_component +
                    vehicles_component +
                    stability_component +
                    bess_eff_component +
                    prioritization_component
                )
            
            # Mezclar: base multiobjetivo v6.0 + 10% ajustes de completación
            reward = base_reward * 0.90 + completion_reward * 0.10
            reward = float(np.clip(reward, -1.0, 1.0))
            
            # Acumular métricas por episodio
            self.episode_reward += reward
            self.episode_solar_kwh += solar_h
            self.episode_grid_import_kwh += grid_import
            self.episode_co2_avoided += max(0, solar_h - grid_import)
            self.episode_ev_satisfied += charger_satisfaction * 100.0
            self.episode_prioritization_reward += prioritization_reward
            self.episode_completion_reward += completion_reward
            
            # Acumular métricas BESS - USAR DATOS REALES DEL DATASET
            # Los valores reales ya fueron calculados arriba de energy_flows
            if h < 8760:
                # USAR FLUJOS REALES del dataset bess_ano_2024.csv
                self.episode_bess_discharge_kwh += real_bess_discharge
                self.episode_bess_charge_kwh += real_bess_charge
            else:
                # FALLBACK cuando h >= 8760: usar cálculo basado en acción
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
            
            # Acumular métricas CO2
            self.episode_co2_directo_evitado_kg += co2_directo_evitado_kg
            self.episode_co2_indirecto_evitado_kg += co2_indirecto_evitado_kg
            self.episode_co2_grid_kg += co2_grid_kg
            
            # Acumular métricas costos
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
            
            # ===== ROTACIÓN DE VEHÍCULOS (simular llegadas/salidas) =====
            # Cada hora, ciertos vehículos se van y llegan nuevos
            if hour_24 in [6, 9, 12, 15, 18, 21]:  # Horas de rotación
                for socket_id in range(self.NUM_CHARGERS):
                    state = self.soc_tracker.vehicle_states[socket_id]
                    # Si vehículo desconectado o muy tiempo (>4h), reemplazar
                    if state is None or not state.is_connected or (h - state.arrival_hour > 4):
                        # 70% probabilidad de nuevo vehículo
                        if np.random.random() < 0.7:
                            initial_soc = np.random.uniform(0.0, 5.0)  # Dataset real: vehículos llegan vacíos
                            self.soc_tracker.spawn_vehicle(socket_id, hour=h, initial_soc=initial_soc)
            
            # Mover al siguiente timestep
            self.current_step += 1
            done = self.current_step >= self.hours_per_year
            
            # Obtener métricas de tracking
            soc_metrics = self.soc_tracker.get_metrics()
            
            obs = self._make_observation(self.current_step)
            truncated = False
            
            # Determinar escasez actual
            scarcity_level = self.current_scenario.get_scarcity_level() if self.current_scenario else 'NONE'
            
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
                'prioritization_reward': float(prioritization_reward),
                'completion_reward': float(completion_reward),
                'scarcity_level': scarcity_level,
                'available_power_ratio': available_power_ratio,
                'episode_reward': self.episode_reward if done else None,
                'episode_solar_kwh': self.episode_solar_kwh if done else None,
                **{f'soc_{k}': v for k, v in soc_metrics.items()},  # Métricas SOC
            }
            
            # Mostrar progreso cada 100 steps (con info de escasez y BESS)
            if self.current_step % 100 == 0:
                scarcity_indicator = f'[{scarcity_level}]' if scarcity_level != 'NONE' else ''
                # BESS action: 0-0.5=carga, 0.5=idle, 0.5-1=descarga
                bess_mode = 'CHG' if bess_action < 0.45 else ('DIS' if bess_action > 0.55 else 'IDL')
                print(f'    [EP {self.episode_num:02d}] h={self.current_step:5d}/8760 | Solar={solar_h:6.1f}kW | BESS={bess_soc_h:4.1f}%/{bess_mode} | Grid={grid_import:6.1f}kW | EV={charger_satisfaction:.2f} | Prio={prioritization_reward:+.3f} {scarcity_indicator}')
            
            # Mostrar resumen al final del episodio CON VEHICLE METRICS COMPLETOS
            if done:
                print(f'    [EP {self.episode_num:02d}] ✅ EPISODIO COMPLETADO (MULTIOBJETIVO + PRIORIZACIÓN SOC):')
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
                print(f'         🌞 Solar→EV (REAL):   {self.episode_real_pv_to_ev_kwh:12,.0f} kWh')
                print(f'         🔋 BESS→EV (REAL):    {self.episode_real_bess_to_ev_kwh:12,.0f} kWh')
                print(f'         ⚡ Grid Import (REAL):{self.episode_real_grid_import_kwh:12,.0f} kWh')
                print(f'         🌿 CO2 Evitado (REAL):{self.episode_real_co2_avoided_kg:12,.0f} kg')
                print(f'         💰 Costo Grid (REAL): {self.episode_real_cost_soles:12,.2f} soles')
                print(f'         💰 Ahorro Pico (REAL):{self.episode_real_peak_savings:12,.2f} soles')
                print()
                # BESS métricas (calculadas por agente)
                print(f'         --- BESS AGENTE ---')
                print(f'         🔋 BESS Descarga:    {self.episode_bess_discharge_kwh:12.1f} kWh')
                print(f'         🔋 BESS Carga:       {self.episode_bess_charge_kwh:12.1f} kWh')
                print(f'         🔋 BESS Ciclos:      {self.episode_bess_cycles:12d}')
                print()
                # CO2 calculados por agente
                print(f'         --- CO2 CALCULADO ---')
                print(f'         📊 CO2 Directo Evit:  {self.episode_co2_directo_evitado_kg:12,.0f} kg (vs gasolina)')
                print(f'         📊 CO2 Ind. Evit:     {self.episode_co2_indirecto_evitado_kg:12,.0f} kg (solar vs grid)')
                print(f'         📊 CO2 Grid Emitido:  {self.episode_co2_grid_kg:12,.0f} kg')
                print(f'         --- COSTOS CALCULADOS ---')
                print(f'         💰 Costo Grid:        {self.episode_costo_grid_soles:12,.2f} soles')
                print(f'         💰 Ahorro Solar:      {self.episode_ahorro_solar_soles:12,.2f} soles')
                print(f'         💰 Ahorro BESS:       {self.episode_ahorro_bess_soles:12,.2f} soles')
                print()
                # MOTOS por nivel SOC (30 sockets)
                m = soc_metrics
                print(f'         🏍️  MOTOS @ SOC:     10%={m["motos_10"]:3d} | 20%={m["motos_20"]:3d} | 30%={m["motos_30"]:3d} | 50%={m["motos_50"]:3d} | 70%={m["motos_70"]:3d} | 80%={m["motos_80"]:3d} | 100%={m["motos_100"]:3d}')
                print(f'         🛺 MOTOTAXIS @ SOC:  10%={m["mototaxis_10"]:3d} | 20%={m["mototaxis_20"]:3d} | 30%={m["mototaxis_30"]:3d} | 50%={m["mototaxis_50"]:3d} | 70%={m["mototaxis_70"]:3d} | 80%={m["mototaxis_80"]:3d} | 100%={m["mototaxis_100"]:3d}')
                print(f'         📊 PRIORIZACIÓN:     Accuracy={m["prioritization_accuracy"]*100:.1f}% | Decisiones bajo escasez: {m["scarcity_decisions"]}')
                print(f'         ✅ CARGADOS AL 100%: {m["total_charged_100"]} vehículos')
                if self.reward_weights:
                    print(f'         Pesos usados:        CO2={self.reward_weights.co2:.2f} | Solar={self.reward_weights.solar:.2f} | EV={self.reward_weights.ev_satisfaction:.2f} | Prio={W_PRIORITIZATION:.2f}')
                print()
            
            return obs, reward, done, truncated, info
        
        def _make_observation(self, hour_idx: int) -> np.ndarray:
            """
            Crea observación v5.3 (156-dim) con COMUNICACIÓN COMPLETA del sistema.

            NORMALIZACIÓN CRÍTICA:
            Todas las features están en rango ~[0,1] para estabilidad del training.
            
            COMUNICACIÓN DEL SISTEMA:
            - El agente ve el estado completo de BESS, Solar, EVs, Cargadores
            - Puede coordinar carga de motos/mototaxis con disponibilidad solar
            - Sabe cuántos vehículos están cargando y cuántos faltan
            - Recibe señales de urgencia y oportunidad
            """
            obs = np.zeros(self.OBS_DIM, dtype=np.float32)
            h = hour_idx % self.HOURS_PER_YEAR
            hour_24 = h % 24
            day_of_year = (h // 24) % 365

            # ================================================================
            # [0-7] ENERGÍA DEL SISTEMA (8 features)
            # ================================================================
            solar_kw = float(self.solar[h]) if h < len(self.solar) else 0.0
            mall_kw = float(self.mall[h]) if h < len(self.mall) else 0.0
            bess_soc = float(self.bess_soc[h]) / 100.0 if h < len(self.bess_soc) else 0.5
            
            # Calcular balance energético
            ev_demand_estimate = float(self.chargers[h].sum()) if h < len(self.chargers) else 0.0
            total_demand = mall_kw + ev_demand_estimate
            solar_surplus = max(0.0, solar_kw - total_demand)
            grid_import_needed = max(0.0, total_demand - solar_kw)
            
            # BESS energía disponible (SOC × capacidad máx × eficiencia)
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
            # [84-121] OCUPACIÓN POR SOCKET (38 features)
            # ================================================================
            occupancy = (raw_demands > 0.1).astype(np.float32)
            obs[84:122] = occupancy

            # ================================================================
            # [122-137] ESTADO DE VEHÍCULOS (16 features) - CRÍTICO PARA APRENDIZAJE
            # ================================================================
            motos_sockets = occupancy[:30]  # Primeros 30 sockets = motos
            taxis_sockets = occupancy[30:]  # Últimos 8 sockets = mototaxis
            
            self.motos_charging_now = int(np.sum(motos_sockets))
            self.mototaxis_charging_now = int(np.sum(taxis_sockets))
            
            # Estimar vehículos en cola según hora pico
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
            
            # Estimar vehículos completados
            vehicles_per_hour = max(1, self.motos_charging_now // 2)
            taxis_per_hour = max(0, self.mototaxis_charging_now // 3)
            self.motos_charged_today += vehicles_per_hour
            self.mototaxis_charged_today += taxis_per_hour
            
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
            obs[135] = solar_for_ev_ratio                                            # Ratio solar→EV
            obs[136] = np.clip(self.daily_co2_avoided / 500.0, 0.0, 1.0)             # CO2 evitado hoy
            obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)                      # CO2 potencial

            # ================================================================
            # [138-143] TIME FEATURES (6 features)
            # ================================================================
            obs[138] = float(hour_24) / 24.0                                         # Hora
            obs[139] = float(day_of_year % 7) / 7.0                                  # Día semana
            obs[140] = float((day_of_year // 30) % 12) / 12.0                        # Mes
            obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0                            # Hora pico
            obs[142] = float(self.context.co2_factor_kg_per_kwh) if self.context else CO2_FACTOR_IQUITOS  # Factor CO2
            obs[143] = 0.15                                                          # Tarifa

            # ================================================================
            # [144-155] COMUNICACIÓN INTER-SISTEMA (12 features)
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
            # 🆕 v6.0 [156-193] PER-SOCKET SOC (38 features)
            # Visibilidad individual de SOC por socket - CRÍTICO para v6.0
            # ================================================================
            # Usar potencia entregada como proxy de SOC actual
            socket_power = obs[46:84]  # Potencia actual por socket normalizada
            # Estimar SOC: suma acumulada de potencia × margen de seguridad
            if not hasattr(self, '_socket_soc_accumulated'):
                self._socket_soc_accumulated = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
            
            # Incrementar SOC según potencia × eficiencia
            soc_increment = socket_power * 0.05  # ~5% SOC por hora a potencia máxima
            self._socket_soc_accumulated = np.clip(self._socket_soc_accumulated + soc_increment, 0.0, 1.0)
            
            # Reset SOC cuando socket se desconecta (ocupancy = 0)
            occupancy = obs[84:122]
            self._socket_soc_accumulated = self._socket_soc_accumulated * occupancy
            
            obs[156:194] = np.clip(self._socket_soc_accumulated, 0.0, 1.0)

            # ================================================================
            # 🆕 v6.0 [194-231] TIME REMAINING PER SOCKET (38 features)
            # Tiempo para llegar a 100% SOC por socket - CRÍTICO para urgencia
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
            
            self._socket_time_remaining = np.clip(time_to_100pct / 8.0, 0.0, 1.0)  # Normalizar a 8 horas máx
            obs[194:232] = self._socket_time_remaining

            # ================================================================
            # 🆕 v6.0 [232-237] BIDIRECTIONAL COMMUNICATION SIGNALS (6 features)
            # Señales explícitas: BESS supply, Solar available, Grid penalty (por tipo vehículo)
            # ================================================================
            # BESS dispatch: disponibilidad de energía BESS para motos vs taxis
            bess_available_motos = min(1.0, bess_energy_available / max(1.0, 30 * 7.4))  # Capacidad motos
            bess_available_taxis = min(1.0, bess_energy_available / max(1.0, 8 * 7.4))   # Capacidad taxis
            
            # Solar bypass: excedente solar disponible (sin pasar por BESS)
            solar_excess_motos = min(1.0, solar_surplus / max(1.0, 30 * 7.4))
            solar_excess_taxis = min(1.0, solar_surplus / max(1.0, 8 * 7.4))
            
            # Grid import penalty: costo CO2 de importar (inverso)
            grid_penalty_motos = grid_import_needed / max(1.0, 30 * 7.4)
            grid_penalty_taxis = grid_import_needed / max(1.0, 8 * 7.4)
            
            obs[232] = np.clip(bess_available_motos, 0.0, 1.0)    # BESS → Motos
            obs[233] = np.clip(bess_available_taxis, 0.0, 1.0)    # BESS → Taxis
            obs[234] = np.clip(solar_excess_motos, 0.0, 1.0)      # Solar → Motos
            obs[235] = np.clip(solar_excess_taxis, 0.0, 1.0)      # Solar → Taxis
            obs[236] = np.clip(grid_penalty_motos, 0.0, 1.0)      # Grid cost → Motos
            obs[237] = np.clip(grid_penalty_taxis, 0.0, 1.0)      # Grid cost → Taxis

            # ================================================================
            # 🆕 v6.0 [238-245] PRIORITY/URGENCY/CAPACITY AGGREGATES (8 features)
            # ================================================================
            # Contar cuántos sockets tienen baja SOC (urgentes)
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
        reward_weights=reward_weights,  # ✅ Weights multiobjetivo
        context=context,  # ✅ Contexto Iquitos
        charger_max_power_kw=charger_max_power,  # ✅ estadísticas reales
        charger_mean_power_kw=charger_mean_power,  # ✅ estadísticas reales
        bess_peak_savings=bess_peak_savings,  # ✅ ahorros pico REALES
        bess_tariff=bess_tariff,  # ✅ tarifa OSINERGMIN REAL
        energy_flows=energy_flows,  # ✅ flujos energía REALES
        # ===== NUEVOS DATOS REALES =====
        solar_data=solar_data,  # ✅ Todas columnas solares (GHI, DNI, temp, etc.)
        chargers_moto=chargers_moto,  # ✅ Sockets MOTOS separados
        chargers_mototaxi=chargers_mototaxi,  # ✅ Sockets MOTOTAXIS separados
        n_moto_sockets=n_moto_sockets,  # ✅ Cantidad real de sockets motos
        n_mototaxi_sockets=n_mototaxi_sockets,  # ✅ Cantidad real de sockets mototaxis
        bess_ev_demand=bess_ev_demand,  # ✅ Demanda EV REAL por hora
        bess_mall_demand=bess_mall_demand,  # ✅ Demanda Mall REAL por hora
        bess_pv_generation=bess_pv_generation,  # ✅ PV generation REAL por hora
        # 🆕 TODAS LAS 27 VARIABLES OBSERVABLES
        observable_variables=observable_variables_df  # ✅ Todas las 27 columnas del dataset_builder
    )
    print(f'  ✅ Ambiente REAL creado con datos OE2 100% REALES:')
    print(f'     - Observation space: {env.OBS_DIM} dims (🆕 v6.0: 156 base + 90 new features = bidirectional communication)')
    print(f'     - Action space:      {env.ACTION_DIM} dims (BESS + {chargers_hourly.shape[1]} sockets)')
    print(f'     - Solar data:        {len(solar_data)} columnas REALES (GHI, DNI, temp, etc.)')
    print(f'     - MOTOS:             {n_moto_sockets} sockets (30 máx)')
    print(f'     - MOTOTAXIS:         {n_mototaxi_sockets} sockets (8 máx)')
    print(f'     - Energy flows:      {len(energy_flows)} flujos REALES')
    print(f'     - 🆕 Observable vars: 27 columnas del dataset_builder (todas las reales)')
    print(f'     - EV Demand REAL:    {"SÍ" if bess_ev_demand is not None else "NO"}')
    print(f'     - Mall Demand REAL:  {"SÍ" if bess_mall_demand is not None else "NO"}')
    print(f'     - COMUNICACIÓN:      BESS↔Solar↔EV↔Cargadores↔Motos↔Mototaxis + Dataset_Builder')
    
    # Get and validate spaces
    if isinstance(env.action_space, list):
        act_dim = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
    else:
        act_dim = env.action_space.shape[0] if hasattr(env.action_space, 'shape') else 39
    
    obs_dim = env.observation_space.shape[0] if hasattr(env.observation_space, 'shape') else 246  # v6.0: 246-dim
    
    print(f'  Observation space: {obs_dim} (🆕 v6.0: 156 base + 38 per-socket SOC + 38 time remaining + 14 signals)')
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
        checkpoints = sorted(CHECKPOINT_DIR.glob('sac_model_*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
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
        name_prefix='sac_model',
        save_replay_buffer=False,
    )
    
    # ===== SAC METRICS CALLBACK - MÉTRICAS COMPLETAS =====
    # Loguea: Actor/Critic loss, Q-values, Entropy, α, Buffer fill, Actions stats
    class SACMetricsCallback(BaseCallback):
        """Callback para loguear métricas SAC detalladas.
        
        Métricas logueadas:
        - Actor loss, Critic Q1/Q2 loss
        - Mean Q-value (alerta si se dispara)
        - Entropy y α (alpha)
        - Replay buffer fill %
        - Mean/Std de acciones
        - Eval episodic return (determinístico, sin ruido)
        - Updates per step ratio
        
        Alertas:
        - Q-values > 1000 → posible sobreestimación
        - Entropy < 0.1 → política muy determinística
        - α < 0.01 → exploración colapsada
        
        Gráficas generadas al final del entrenamiento:
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
            
            # Historial de métricas para detectar tendencias (con steps para eje X)
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
            # DETECCIÓN ROBUSTA DE PROBLEMAS v2.0 (SAC)
            # ========================================================================
            
            # Baselines para detección de colapso TEMPRANO
            self._initial_entropy: Optional[float] = None
            self._initial_alpha: Optional[float] = None
            self._initial_action_std: Optional[float] = None
            self._baseline_samples: int = 0
            self._entropy_baseline_sum: float = 0.0
            self._alpha_baseline_sum: float = 0.0
            self._std_baseline_sum: float = 0.0
            
            # Detección de colapso TEMPRANO (¿ocurrió antes del 30% del training?)
            self.early_entropy_collapse_count: int = 0
            self.early_alpha_collapse_count: int = 0
            self.early_std_collapse_count: int = 0
            
            # Contadores de problemas CONSECUTIVOS (más severos)
            self.consecutive_q_overflow: int = 0
            self.consecutive_entropy_collapse: int = 0
            self.consecutive_alpha_collapse: int = 0
            self.consecutive_std_collapse: int = 0
            
            # Señales COMBINADAS (más severas)
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
            
            # ===== CITYLEARN KPIs (evaluación vs pasos) =====
            self.kpi_steps_history: List[int] = []
            self.electricity_consumption_history: List[float] = []
            self.electricity_cost_history: List[float] = []
            self.carbon_emissions_history: List[float] = []
            self.ramping_history: List[float] = []
            self.avg_daily_peak_history: List[float] = []
            self.one_minus_load_factor_history: List[float] = []
            
            # Acumuladores KPI (ventana de 24 horas)
            self._kpi_window_size: int = 24  # 24 steps = 1 día
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
            self._actions_at_low: int = 0  # Acciones en límite inferior (< 0.05)
            self._actions_at_high: int = 0  # Acciones en límite superior (> 0.95)
            self._total_action_count: int = 0
            
            # ===== TRACE Y TIMESERIES RECORDS (como PPO/A2C) =====
            self.trace_records: List[Dict[str, Any]] = []
            self.timeseries_records: List[Dict[str, Any]] = []
            
            # Episode tracking
            self.episode_count: int = 0
            self.step_in_episode: int = 0
            self.current_episode_reward: float = 0.0
            
            # Métricas por episodio
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
            """Extraer métricas internas de SAC."""
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
                
                # Entropy coefficient (α)
                if 'train/ent_coef' in log_dict:
                    metrics['alpha'] = float(log_dict['train/ent_coef'])
                elif 'train/ent_coef_loss' in log_dict:
                    # Si hay loss del ent_coef, está en auto-tune
                    metrics['ent_coef_loss'] = float(log_dict['train/ent_coef_loss'])
                
                # Entropy del policy
                if 'train/entropy' in log_dict:
                    metrics['entropy'] = float(log_dict['train/entropy'])
                
                # Learning rate
                if 'train/learning_rate' in log_dict:
                    metrics['learning_rate'] = float(log_dict['train/learning_rate'])
            
            # Replay buffer fill %
            if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer is not None:
                buffer = self.model.replay_buffer
                buffer_size = buffer.buffer_size
                current_size = buffer.size() if hasattr(buffer, 'size') else buffer.pos
                metrics['buffer_fill_pct'] = 100.0 * current_size / buffer_size
                metrics['buffer_size'] = current_size
            
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
            
            # Intentar obtener Q-values medios del critic
            if hasattr(self.model, 'critic') and hasattr(self.model, 'replay_buffer'):
                try:
                    # Sample pequeño para estimar Q-values
                    if self.model.replay_buffer.size() > 100:
                        replay_data = self.model.replay_buffer.sample(min(100, self.model.replay_buffer.size()))
                        with torch.no_grad():
                            obs = replay_data.observations
                            actions = replay_data.actions
                            q1, q2 = self.model.critic(obs, actions)
                            metrics['mean_q1'] = float(q1.mean().cpu().numpy())
                            metrics['mean_q2'] = float(q2.mean().cpu().numpy())
                            metrics['mean_q'] = (metrics['mean_q1'] + metrics['mean_q2']) / 2
                except Exception:
                    pass  # No critical si falla
            
            # Estadísticas de acciones del actor
            if hasattr(self.model, 'actor'):
                try:
                    if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer.size() > 100:
                        replay_data = self.model.replay_buffer.sample(100)
                        with torch.no_grad():
                            # Obtener acciones del actor
                            action_dist = self.model.actor(replay_data.observations)
                            if hasattr(action_dist, 'mean'):
                                mean_actions = action_dist.mean
                                metrics['action_mean'] = float(mean_actions.mean().cpu().numpy())
                                metrics['action_std'] = float(mean_actions.std().cpu().numpy())
                            if hasattr(action_dist, 'log_std'):
                                metrics['log_std'] = float(action_dist.log_std.mean().cpu().numpy())
                except Exception:
                    pass  # No critical si falla
            
            return metrics
        
        def _eval_deterministic(self) -> Optional[float]:
            """Evaluar política de forma determinística (sin ruido).
            
            Ejecuta un mini-episodio con acciones = media de la distribución,
            sin muestreo estocástico. Esto da el 'eval episodic return'.
            """
            try:
                eval_env = self.model.get_env()
                if eval_env is None:
                    return None
                
                obs = eval_env.reset()
                total_reward = 0.0
                done = False
                step_count = 0
                max_eval_steps = 1000  # Límite para evaluación rápida
                
                while not done and step_count < max_eval_steps:
                    # Acción DETERMINÍSTICA (mean de la distribución)
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
            Verificar condiciones de alerta con detección robusta v2.0.
            
            DETECCIÓN ROBUSTA (SAC) v2.0:
            ==============================
            1. Baselines dinámicos para entropy, alpha, action_std
            2. Detección de colapso TEMPRANO (antes del 30% del training)
            3. Problemas CONSECUTIVOS (más severos que esporádicos)
            4. Señal COMBINADA: entropy + alpha + std todos colapsando
            5. Recomendaciones específicas por tipo de problema
            
            Referencias:
            - [Haarnoja et al. 2018] SAC with automatic temperature tuning
            - [Henderson et al. 2018] Deep RL That Matters - diagnóstico
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
            # 1. Q-VALUE MUY ALTO (→ reward scale mal / LR alto / targets inestables)
            # ====================================================================
            if mean_q is not None and abs(mean_q) > self._q_warning_threshold:
                self.consecutive_q_overflow += 1
                self.q_overflow_alerts += 1
                self._problem_summary['q_overflow'] += 1
                
                severity = "SEVERE" if abs(mean_q) > 5000 else "WARNING"
                if abs(mean_q) > 5000:
                    self._problem_summary['q_overflow_severe'] += 1
                
                if self.consecutive_q_overflow <= 3 or self.consecutive_q_overflow % 10 == 0:
                    alerts.append(f"⚠️  Q-VALUE {severity}: {mean_q:.1f} (>1000)")
                    if self.consecutive_q_overflow >= 3:
                        alerts.append(f"        → {self.consecutive_q_overflow} veces CONSECUTIVAS")
                        alerts.append(f"        → Acción: Reducir reward scale, reducir LR, verificar target update")
            else:
                if self.consecutive_q_overflow > 0:
                    self.consecutive_q_overflow = 0
            
            # ====================================================================
            # 2. ENTROPY COLAPSANDO (→ política muy determinística)
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
                            alerts.append(f"⚠️  ENTROPY COLAPSO TEMPRANO: {entropy:.4f} "f"({entropy_ratio*100:.0f}% del baseline {self._initial_entropy:.4f})")
                            alerts.append(f"        → Progreso: {training_progress*100:.0f}% | Colapso muy temprano")
                            alerts.append(f"        → Acción URGENTE: Aumentar ent_coef, usar target_entropy mayor")
                        else:
                            alerts.append(f"⚠️  ENTROPY BAJA: {entropy:.4f} (política muy determinística)")
                            alerts.append(f"        → Acción: Aumentar ent_coef de 'auto' a valor fijo (0.1-0.5)")
                else:
                    self.consecutive_entropy_collapse = 0
            
            # ====================================================================
            # 3. ALPHA MUY BAJO (→ exploración colapsada)
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
                            alerts.append(f"⚠️  ALPHA COLAPSO TEMPRANO: {alpha:.4f} "f"({alpha_ratio*100:.0f}% del baseline)")
                            alerts.append(f"        → Progreso: {training_progress*100:.0f}% | Alpha cayó muy rápido")
                            alerts.append(f"        → Acción: Ajustar target_entropy, revisar reward scale")
                        else:
                            alerts.append(f"⚠️  ALPHA BAJO: {alpha:.4f} (exploración colapsada)")
                            alerts.append(f"        → Acción: Usar ent_coef fijo en lugar de 'auto'")
                else:
                    self.consecutive_alpha_collapse = 0
            
            # ====================================================================
            # 4. ACTION STD MUY BAJA (→ exploración muriendo)
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
                            alerts.append(f"⚠️  ACTION STD COLAPSO TEMPRANO: {action_std:.4f} "f"({std_ratio*100:.0f}% del baseline)")
                            alerts.append(f"        → Progreso: {training_progress*100:.0f}% | Exploración muriendo muy rápido")
                            alerts.append(f"        → Acción URGENTE: Aumentar ent_coef, verificar init de actor")
                        else:
                            alerts.append(f"⚠️  ACTION STD BAJA: {action_std:.4f} (exploración muriendo)")
                            alerts.append(f"        → Acción: Aumentar ent_coef, reiniciar con mayor exploración inicial")
                else:
                    self.consecutive_std_collapse = 0
            
            # ====================================================================
            # 5. SEÑAL COMBINADA: COLAPSO DE EXPLORACIÓN TOTAL (entrenamientos muy grave)
            # ====================================================================
            # Si entropy + alpha + std todos están colapsando simultáneamente
            entropy_low = entropy is not None and entropy < 0.1
            alpha_low = alpha is not None and alpha < 0.01
            std_low = action_std is not None and action_std < 0.05
            
            if entropy_low and alpha_low and std_low:
                self.combined_exploration_collapse_count += 1
                self._problem_summary['combined_exploration_collapse'] += 1
                
                if self.combined_exploration_collapse_count <= 3 or self.combined_exploration_collapse_count % 5 == 0:
                    alerts.append(f"❌  [CRITICAL] COLAPSO TOTAL DE EXPLORACIÓN detectado")
                    alerts.append(f"        → Entropy: {entropy:.4f} | Alpha: {alpha:.4f} | Std: {action_std:.4f}")
                    alerts.append(f"        → El agente ha dejado de explorar completamente")
                    alerts.append(f"        → Acción URGENTE: Reiniciar con ent_coef=0.2, verificar reward shaping")
            
            # Contar problemas consecutivos totales
            total_consecutive = (self.consecutive_q_overflow + self.consecutive_entropy_collapse + 
                                self.consecutive_alpha_collapse + self.consecutive_std_collapse)
            if total_consecutive >= 10:
                self._problem_summary['consecutive_problems'] += 1
            
            return alerts
        
        def _print_problem_summary(self) -> None:
            """
            Imprime resumen de problemas detectados durante el entrenamiento SAC.
            Incluye recomendaciones específicas para cada tipo de problema.
            """
            print('\n' + '=' * 80)
            print('RESUMEN DE PROBLEMAS DETECTADOS (SAC)')
            print('=' * 80)
            
            total_problems = sum(self._problem_summary.values())
            
            if total_problems == 0:
                print('  ✅ No se detectaron problemas significativos durante el entrenamiento')
            else:
                print(f'  Total de eventos problemáticos: {total_problems}')
                print()
                
                # Problemas CRÍTICOS
                if self._problem_summary['combined_exploration_collapse'] > 0:
                    print(f'  ❌ CRÍTICO - Colapso TOTAL de exploración: {self._problem_summary["combined_exploration_collapse"]} veces')
                    print(f'      → Solución: Aumentar ent_coef a 0.2, usar target_entropy=-dim(action)')
                
                if self._problem_summary['q_overflow_severe'] > 0:
                    print(f'  ❌ CRÍTICO - Q-values extremamente altos (>5000): {self._problem_summary["q_overflow_severe"]} veces')
                    print(f'      → Solución: Dividir rewards por 10, reducir LR a 1e-4, aumentar tau')
                
                if self._problem_summary['early_entropy_collapse'] > 0:
                    print(f'  ❌ CRÍTICO - Entropy colapsó TEMPRANO: {self._problem_summary["early_entropy_collapse"]} veces')
                    print(f'      → Solución: Aumentar ent_coef a 0.1-0.5 (no usar "auto")')
                
                if self._problem_summary['early_alpha_collapse'] > 0:
                    print(f'  ❌ CRÍTICO - Alpha colapsó TEMPRANO: {self._problem_summary["early_alpha_collapse"]} veces')
                    print(f'      → Solución: Fijar target_entropy más negativo, revisar reward scale')
                
                if self._problem_summary['early_std_collapse'] > 0:
                    print(f'  ❌ CRÍTICO - Action Std colapsó TEMPRANO: {self._problem_summary["early_std_collapse"]} veces')
                    print(f'      → Solución: Verificar init del actor, aumentar ruido inicial')
                
                # Problemas moderados
                if self._problem_summary['q_overflow'] > 0:
                    print(f'  ⚠️  Q-values altos (>1000): {self._problem_summary["q_overflow"]} veces')
                
                if self._problem_summary['entropy_collapse'] > 0:
                    print(f'  ⚠️  Entropy baja (<0.1): {self._problem_summary["entropy_collapse"]} veces')
                
                if self._problem_summary['alpha_collapse'] > 0:
                    print(f'  ⚠️  Alpha bajo (<0.01): {self._problem_summary["alpha_collapse"]} veces')
                
                if self._problem_summary['std_collapse'] > 0:
                    print(f'  ⚠️  Action Std bajo (<0.05): {self._problem_summary["std_collapse"]} veces')
            
            # Recomendaciones finales basadas en patrones
            print()
            print('  RECOMENDACIONES PARA SIGUIENTE ENTRENAMIENTO:')
            if self._problem_summary['combined_exploration_collapse'] > 3:
                print('    1. ❌ URGENTE: ent_coef="auto" → ent_coef=0.2 (forzar exploración)')
            if self._problem_summary['q_overflow'] > 10:
                print('    2. Reward scale: Dividir rewards por 10 o usar reward normalization')
            if self._problem_summary['early_entropy_collapse'] > 3:
                print('    3. target_entropy: Usar -dim(action_space) o valor más negativo')
            if self._problem_summary['early_std_collapse'] > 3:
                print('    4. Actor init: Verificar log_std_init, usar valores más altos')
            if total_problems == 0:
                print('    ✓ Hiperparámetros actuales funcionan bien')
            
            print('=' * 80 + '\n')
        
        def _on_step(self) -> bool:
            current_step = self.model.num_timesteps
            
            # ===== RECOLECTAR KPIs CITYLEARN =====
            self._collect_kpi_data()
            
            # ===== TRACK ACTION DISTRIBUTION & SATURATION =====
            self._track_action_distribution()
            
            # ===== REGISTRAR TRACE Y TIMESERIES (como PPO/A2C) =====
            self._record_trace_and_timeseries()
            
            # ===== EVALUACIÓN DETERMINÍSTICA PERIÓDICA =====
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
                
                # Formatear línea de log
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
                    parts.append(f"α={metrics['alpha']:.4f}")
                
                # Buffer fill
                if 'buffer_fill_pct' in metrics:
                    parts.append(f"Buf={metrics['buffer_fill_pct']:.1f}%")
                
                # Updates per step
                if 'updates_per_step' in metrics:
                    parts.append(f"Upd/s={metrics['updates_per_step']:.2f}")
                
                # Learning rate
                lr = metrics.get('learning_rate', self.model.learning_rate)
                parts.append(f"LR={lr:.1e}")
                
                print(f"    {' | '.join(parts)}")
                
                # Verificar alertas
                alerts = self._check_alerts(metrics)
                for alert in alerts:
                    print(f"    {alert}")
                
                self.last_step = current_step
            
            return True
        
        def _collect_kpi_data(self) -> None:
            """
            Recolectar datos para KPIs CityLearn de evaluación.
            
            KPIs estándar CityLearn calculados sobre carga neta agregada:
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
            
            # Extraer métricas del step actual
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
            
            # Calcular KPIs cada _kpi_window_size steps (24 horas = 1 día)
            if len(self._kpi_loads) >= self._kpi_window_size:
                self._calculate_and_store_kpis()
        
        def _calculate_and_store_kpis(self) -> None:
            """
            Calcular y almacenar KPIs para la ventana actual.
            
            Fórmulas estándar CityLearn:
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
            Trackear distribución de acciones y saturación.
            
            Métricas:
            - Histograma de todas las acciones tomadas
            - % de acciones saturadas (pegadas al límite 0 o 1)
            - Detección de políticas degeneradas que solo usan extremos
            """
            # Obtener acción actual del modelo
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
            
            # Contar saturación (acciones en límites)
            for a in actions:
                self._total_action_count += 1
                if a < 0.05:  # Cerca del límite inferior
                    self._actions_at_low += 1
                elif a > 0.95:  # Cerca del límite superior
                    self._actions_at_high += 1
        
        def _record_trace_and_timeseries(self) -> None:
            """
            Registrar datos de trace y timeseries para exportación CSV.
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
            
            # Extraer métricas del info
            co2_grid = info.get('co2_grid_kg', 0.0)
            solar_kwh = info.get('solar_generation_kwh', info.get('solar_kw', 0.0))
            ev_charging = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))
            grid_import = info.get('grid_import_kwh', info.get('grid_import_kw', 0.0))
            bess_power = info.get('bess_power_kw', 0.0)
            bess_soc = info.get('bess_soc', 0.0)
            mall_demand = info.get('mall_demand_kw', 0.0)
            
            # Acumular métricas del episodio
            self._current_co2_grid += co2_grid
            self._current_solar_kwh += solar_kwh
            self._current_ev_charging += ev_charging
            self._current_grid_import += grid_import
            if bess_power > 0:
                self._current_bess_discharge += bess_power
            else:
                self._current_bess_charge += abs(bess_power)
            
            # Registrar trace (cada step)
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'reward': reward,
                'cumulative_reward': self.current_episode_reward,
                'co2_grid_kg': co2_grid,
                'solar_generation_kwh': solar_kwh,
                'ev_charging_kwh': ev_charging,
                'grid_import_kwh': grid_import,
                'bess_power_kw': bess_power,
                'bess_soc': bess_soc,
            }
            self.trace_records.append(trace_record)
            
            # Registrar timeseries (cada hora simulada)
            timeseries_record = {
                'timestep': self.num_timesteps,
                'hour': self.step_in_episode % 8760,
                'solar_kw': solar_kwh,
                'mall_demand_kw': mall_demand,
                'ev_charging_kw': ev_charging,
                'grid_import_kw': grid_import,
                'bess_power_kw': bess_power,
                'bess_soc': bess_soc,
            }
            self.timeseries_records.append(timeseries_record)
            
            # Si episodio terminó
            if done:
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                self.episode_bess_discharge_kwh.append(self._current_bess_discharge)
                self.episode_bess_charge_kwh.append(self._current_bess_charge)
                
                self.episode_count += 1
                
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
            """Resumen al final del entrenamiento y generación de gráficas."""
            print()
            print("    === RESUMEN MÉTRICAS SAC ===")
            if self.q_value_history:
                print(f"    Q-value: min={min(self.q_value_history):.1f}, max={max(self.q_value_history):.1f}, final={self.q_value_history[-1]:.1f}")
            if self.entropy_history:
                print(f"    Entropy: start={self.entropy_history[0]:.3f}, final={self.entropy_history[-1]:.3f}")
            if self.alpha_history:
                print(f"    Alpha (α): start={self.alpha_history[0]:.4f}, final={self.alpha_history[-1]:.4f}")
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
            print("    === RESUMEN SATURACIÓN ACCIONES ===")
            if self._total_action_count > 0:
                pct_low = 100.0 * self._actions_at_low / self._total_action_count
                pct_high = 100.0 * self._actions_at_high / self._total_action_count
                pct_saturated = pct_low + pct_high
                print(f"    Total acciones tracked: {self._total_action_count:,}")
                print(f"    En límite inferior (<0.05): {pct_low:.1f}%")
                print(f"    En límite superior (>0.95): {pct_high:.1f}%")
                print(f"    Total saturadas: {pct_saturated:.1f}%")
                if pct_saturated > 30:
                    print(f"    ⚠️ ALTA SATURACIÓN: Política puede estar degenerada")
            
            # NUEVO v2.0: Imprimir resumen de problemas detectados con recomendaciones
            self._print_problem_summary()
            
            # Generar gráficas de diagnóstico SAC
            if len(self.steps_history) > 1:
                self._generate_sac_graphs()
            
            # Generar gráficas de KPIs CityLearn
            if len(self.kpi_steps_history) > 1:
                self._generate_kpi_graphs()
            
            # Generar histograma de acciones
            if len(self._all_actions) > 0:
                self._generate_action_histogram()
        
        def _generate_sac_graphs(self) -> None:
            """
            Genera gráficas de diagnóstico para SAC.
            
            GRÁFICAS GENERADAS:
            ===================
            1. Critic/Q Loss vs Steps
               - Q1 y Q2 loss separados si disponibles
               - Si se dispara → reward scale mal / LR alto
            
            2. Actor Loss vs Steps
               - Mide qué tan bien el actor maximiza Q
               - Fluctuante es normal, tendencia decreciente es buena
            
            3. Alpha (temperatura) y Entropy vs Steps
               - Con auto-tuning, α refleja cuánta aleatoriedad mantiene
               - Entropy debe decrecer gradualmente, NO colapsar a 0
            
            4. Mean Q-value vs Steps
               - Si Q se dispara > 1000 → sobreestimación
               - Típico: crece gradualmente y se estabiliza
            
            5. Std de acciones / log_std vs Steps
               - Colapso de std temprano = exploración muere
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
                                 '(Si se dispara → reward scale mal / LR alto / targets inestables)', fontsize=14)
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
                    
                    # Línea de referencia en 0
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
                        
                        # Línea de warning
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
                                     label='Alpha (α)', alpha=0.8)
                        
                        if len(alpha) >= 10:
                            window = min(10, len(alpha) // 3)
                            alpha_smooth = pd.Series(alpha).rolling(window=window, center=True).mean()
                            ax3_twin.plot(steps_k[:len(alpha_smooth)], alpha_smooth, 'orange', 
                                         linewidth=2.5, label='Alpha (smooth)', alpha=1.0)
                        
                        ax3_twin.set_ylabel('Alpha (α)', fontsize=12, color='orange')
                        ax3_twin.axhline(y=0.01, color='darkred', linestyle=':', linewidth=1.5, 
                                        label='α warning (0.01)')
                        ax3_twin.legend(loc='upper right')
                    
                    ax3.set_title('SAC: Alpha (temperatura) y Entropy vs Training Steps\n'
                                 '(Con auto-tuning, α refleja cuánta aleatoriedad mantiene)', fontsize=14)
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
                    
                    # Líneas de referencia
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
                                 '(Si Q se dispara > 1000 → reward scale mal / LR alto / targets inestables)', 
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
                        
                        # Línea de warning
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
                                 '(Colapso de std temprano = exploración muere)', fontsize=14)
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
                    axes[1, 0].set_ylabel('Alpha (α)')
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
                
                print(f'  [OK] 6 gráficas SAC generadas en: {self.output_dir}')
                
            except Exception as e:
                print(f'  [WARNING] Error generando gráficas SAC: {e}')
                import traceback
                traceback.print_exc()
        
        def _generate_kpi_graphs(self) -> None:
            """
            Generar gráficos de KPIs CityLearn vs Training Steps para SAC.
            
            GRÁFICOS GENERADOS:
            1. Electricity Consumption (net) vs Steps
            2. Electricity Cost vs Steps
            3. Carbon Emissions vs Steps
            4. Ramping vs Steps
            5. Average Daily Peak vs Steps
            6. (1 - Load Factor) vs Steps
            7. Dashboard KPIs combinado 2×3
            """
            
            if len(self.kpi_steps_history) < 2:
                print('     ⚠️ Insuficientes datos para gráficos KPIs (< 2 puntos)')
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Función helper para suavizado
            def smooth(data: list, window: int = 5) -> np.ndarray:
                """Rolling mean para suavizar curvas."""
                if len(data) < window:
                    return np.array(data)
                return pd.Series(data).rolling(window=window, min_periods=1).mean().values
            
            steps = np.array(self.kpi_steps_history)
            steps_k = steps / 1000.0  # En miles
            
            # ====================================================================
            # GRÁFICO 1: ELECTRICITY CONSUMPTION vs STEPS
            # ====================================================================
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                consumption = np.array(self.electricity_consumption_history)
                ax.plot(steps_k, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
                ax.plot(steps_k, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
                
                # Línea de tendencia
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
                    ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_electricity_consumption.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_electricity_consumption.png')
            except Exception as e:
                print(f'     ❌ Error en consumption graph: {e}')
            
            # ====================================================================
            # GRÁFICO 2: ELECTRICITY COST vs STEPS
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
                    ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_electricity_cost.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_electricity_cost.png')
            except Exception as e:
                print(f'     ❌ Error en cost graph: {e}')
            
            # ====================================================================
            # GRÁFICO 3: CARBON EMISSIONS vs STEPS
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
                ax.set_ylabel('Carbon Emissions (kg CO₂/day)')
                ax.set_title('SAC: Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                
                # Anotar reducción CO2
                if len(emissions) > 1:
                    reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                    color = 'green' if reduction > 0 else 'red'
                    ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% CO₂', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_carbon_emissions.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_carbon_emissions.png')
            except Exception as e:
                print(f'     ❌ Error en emissions graph: {e}')
            
            # ====================================================================
            # GRÁFICO 4: RAMPING vs STEPS
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
                    ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% ramping', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_ramping.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_ramping.png')
            except Exception as e:
                print(f'     ❌ Error en ramping graph: {e}')
            
            # ====================================================================
            # GRÁFICO 5: AVERAGE DAILY PEAK vs STEPS
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
                
                # Anotar reducción de pico
                if len(peak) > 1:
                    reduction = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                    color = 'green' if reduction > 0 else 'red'
                    ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% peak', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_daily_peak.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_daily_peak.png')
            except Exception as e:
                print(f'     ❌ Error en peak graph: {e}')
            
            # ====================================================================
            # GRÁFICO 6: (1 - LOAD FACTOR) vs STEPS
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
                    ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%', 
                               xy=(0.98, 0.02), xycoords='axes fraction',
                               fontsize=10, color=color, ha='right')
                
                plt.tight_layout()
                plt.savefig(self.output_dir / 'kpi_load_factor.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_load_factor.png')
            except Exception as e:
                print(f'     ❌ Error en load factor graph: {e}')
            
            # ====================================================================
            # GRÁFICO 7: DASHBOARD KPIs COMBINADO 2×3
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
                ax.set_title('CO₂ Emissions (kg/day)')
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
                
                # Calcular mejoras para título
                improvements = []
                if len(consumption) > 1:
                    imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                    if imp > 0:
                        improvements.append(f'Cons: {imp:.1f}%↓')
                if len(emissions) > 1:
                    imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                    if imp > 0:
                        improvements.append(f'CO₂: {imp:.1f}%↓')
                if len(peak) > 1:
                    imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                    if imp > 0:
                        improvements.append(f'Peak: {imp:.1f}%↓')
                
                title = 'CityLearn KPIs Dashboard - SAC Training'
                if improvements:
                    title += f'\n✅ Improvements: {", ".join(improvements)}'
                
                fig.suptitle(title, fontsize=14, fontweight='bold')
                plt.tight_layout(rect=[0, 0, 1, 0.96])
                plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
                plt.close(fig)
                print('     ✅ kpi_dashboard.png')
                
            except Exception as e:
                print(f'     ❌ Error en KPI dashboard: {e}')
            
            print(f'     📁 Gráficos KPIs guardados en: {self.output_dir}')
        
        def _generate_action_histogram(self) -> None:
            """
            Generar histograma de distribución de acciones y gráfico de saturación.
            
            GRÁFICOS GENERADOS:
            1. Histograma de todas las acciones (6 subplots si hay múltiples canales)
            2. Gráfico de barras mostrando % saturación por canal
            
            Diagnósticos:
            - Distribución uniforme = buena exploración
            - Picos en 0 o 1 = política degenerada (solo extremos)
            - Alta saturación (>30%) = reward boundary issues
            """
            if len(self._all_actions) == 0:
                print('     ⚠️ No hay datos de acciones para histograma')
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Concatenar todas las acciones
                all_actions = np.vstack(self._all_actions)  # Shape: (samples, action_dim)
                n_samples, action_dim = all_actions.shape
                
                # ================================================================
                # FIGURA 1: Histograma de distribución de acciones
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
                
                # Colores para saturación
                for i in range(min(action_dim, len(axes))):
                    ax = axes[i]
                    action_values = all_actions[:, i]
                    
                    # Calcular saturación para este canal
                    pct_low = 100.0 * np.sum(action_values < 0.05) / len(action_values)
                    pct_high = 100.0 * np.sum(action_values > 0.95) / len(action_values)
                    
                    # Histograma
                    n, bins, patches = ax.hist(action_values, bins=50, density=True, 
                                               alpha=0.7, color='steelblue', edgecolor='white')
                    
                    # Colorear barras de saturación
                    for j, patch in enumerate(patches):
                        if bins[j] < 0.05:
                            patch.set_facecolor('red')
                        elif bins[j] > 0.95:
                            patch.set_facecolor('red')
                    
                    # Anotaciones
                    ax.axvline(x=0.05, color='red', linestyle='--', alpha=0.5)
                    ax.axvline(x=0.95, color='red', linestyle='--', alpha=0.5)
                    ax.set_xlim(0, 1)
                    
                    # Título con saturación
                    sat_total = pct_low + pct_high
                    color = 'red' if sat_total > 30 else 'orange' if sat_total > 15 else 'green'
                    if i == 0:
                        ax.set_title(f'BESS ({sat_total:.0f}% sat)', fontsize=9, color=color)
                    else:
                        ax.set_title(f'Socket {i} ({sat_total:.0f}%)', fontsize=9, color=color)
                    
                    ax.set_xlabel('Action', fontsize=8)
                    ax.tick_params(axis='both', which='major', labelsize=7)
                
                # Ocultar ejes vacíos
                for i in range(action_dim, len(axes)):
                    axes[i].axis('off')
                
                fig.suptitle(f'SAC Action Distribution ({n_samples:,} samples)\n'
                            f'Red zones = saturation (< 0.05 or > 0.95)', 
                            fontsize=12, fontweight='bold')
                plt.tight_layout(rect=[0, 0, 1, 0.95])
                plt.savefig(self.output_dir / 'sac_action_histogram.png', dpi=150)
                plt.close(fig)
                print('     ✅ sac_action_histogram.png')
                
                # ================================================================
                # FIGURA 2: Saturation Summary Bar Chart
                # ================================================================
                fig, ax = plt.subplots(figsize=(12, 5))
                
                # Calcular saturación por canal
                sat_low = []
                sat_high = []
                for i in range(action_dim):
                    action_values = all_actions[:, i]
                    sat_low.append(100.0 * np.sum(action_values < 0.05) / len(action_values))
                    sat_high.append(100.0 * np.sum(action_values > 0.95) / len(action_values))
                
                x = np.arange(min(action_dim, 40))  # Limitar a 40 canales para visualización
                width = 0.35
                
                bars1 = ax.bar(x - width/2, sat_low[:len(x)], width, label='Low (<0.05)', color='blue', alpha=0.7)
                bars2 = ax.bar(x + width/2, sat_high[:len(x)], width, label='High (>0.95)', color='orange', alpha=0.7)
                
                # Línea de warning
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
                print('     ✅ sac_action_saturation.png')
                
            except Exception as e:
                print(f'     ❌ Error en action histogram: {e}')
                import traceback
                traceback.print_exc()
    
    # NUEVO: SAC Metrics Callback con generación de gráficas
    sac_metrics_callback = SACMetricsCallback(
        log_freq=500, 
        eval_freq=8760, 
        output_dir=OUTPUT_DIR,  # Directorio para guardar gráficas
        verbose=0
    )
    
    callback_list = CallbackList([checkpoint_callback, sac_metrics_callback])
    
    print('[8] ENTRENAMIENTO SAC - 15 EPISODIOS COMPLETOS (OPTIMIZADO)')
    print('-' * 80)
    print(f'  Total timesteps: 131,400 (15 episodios × 8,760 h/episodio)')
    print(f'  Checkpoint cada: 1,000 steps')
    print(f'  Warmup steps:    {sac_config.learning_starts:,} (random exploration)')
    print(f'  Batch size:      {sac_config.batch_size}')
    print(f'  Buffer size:     {sac_config.buffer_size:,}')
    print(f'  τ (tau):         {sac_config.tau}')
    print(f'  γ (gamma):       {sac_config.gamma}')
    print(f'  Train freq:      {sac_config.train_freq}')
    print(f'  Gradient steps:  {sac_config.gradient_steps} (updates per env step)')
    print(f'  Entropy coef:    {sac_config.ent_coef}')
    print(f'  Target entropy:  {sac_config.target_entropy}')
    print(f'  Learning rate:   {sac_config.learning_rate}')
    print(f'  Networks:        Actor/Critic {list(sac_config.policy_kwargs.get("net_arch", {}).get("pi", [256, 256]))}')
    print(f'  Datos: Datos reales OE2 (solar 8.29GWh + chargers + mall 12.37GWh + BESS 940kWh)')
    print(f'  Device: {DEVICE.upper()}')
    print()
    print('  MÉTRICAS LOGUEADAS (cada 500 steps):')
    print('  - Actor loss, Critic loss (Q1/Q2)')
    print('  - Mean Q-value (alerta si > 1000)')
    print('  - Entropy y α (alerta si entropy < 0.1 o α < 0.01)')
    print('  - Replay buffer fill %')
    print('  - Updates per step (ratio real)')
    print('  - Mean/Std acciones, log_std')
    print('  EVAL (cada 8760 steps = 1 episodio):')
    print('  - Eval Return (determinístico, sin ruido)')
    print()
    print('  Progreso por episodio (cada 100 timesteps dentro del episodio):')
    print('-' * 80)
    print()
    
    try:
        agent.learn(
            total_timesteps=131_400,  # 15 episodios × 8,760 steps (+ 5 episodios para mejor convergencia)
            callback=callback_list,
            reset_num_timesteps=False,
            progress_bar=True,
            log_interval=1,
        )
        print('\n✅ Entrenamiento SAC completado exitosamente')
    except KeyboardInterrupt:
        print('\n⚠ Entrenamiento interrumpido por usuario')
        agent.save(CHECKPOINT_DIR / 'sac_model_interrupted.zip')
    except Exception as e:
        print(f'\n❌ Error durante entrenamiento: {e}')
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Guardar checkpoint final
        final_path = CHECKPOINT_DIR / f'sac_model_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        agent.save(final_path)
        print(f'✅ Checkpoint final guardado: {final_path.name}')
    
    # ========== GUARDAR ARCHIVOS DE SALIDA (como PPO/A2C) ==========
    print()
    print('  GUARDANDO ARCHIVOS DE SALIDA:')
    
    # 1. trace_sac.csv - Registro detallado de cada step
    if sac_metrics_callback.trace_records:
        trace_df = pd.DataFrame(sac_metrics_callback.trace_records)
        trace_path = OUTPUT_DIR / 'trace_sac.csv'
        trace_df.to_csv(trace_path, index=False, encoding='utf-8')
        print(f'    ✓ trace_sac.csv: {len(trace_df):,} registros → {trace_path}')
    else:
        print('    ⚠ trace_sac.csv: Sin registros')
    
    # 2. timeseries_sac.csv - Series temporales horarias
    if sac_metrics_callback.timeseries_records:
        ts_df = pd.DataFrame(sac_metrics_callback.timeseries_records)
        ts_path = OUTPUT_DIR / 'timeseries_sac.csv'
        ts_df.to_csv(ts_path, index=False, encoding='utf-8')
        print(f'    ✓ timeseries_sac.csv: {len(ts_df):,} registros → {ts_path}')
    else:
        print('    ⚠ timeseries_sac.csv: Sin registros')
    
    # 3. result_sac.json - Resumen completo del entrenamiento
    result_summary = {
        'agent': 'SAC',
        'version': 'v5.3',
        'timestamp': datetime.now().isoformat(),
        'total_timesteps': agent.num_timesteps,
        'episodes_completed': sac_metrics_callback.episode_count,
        'model_path': str(final_path),
        'metrics_summary': {
            'final_q_value': sac_metrics_callback.q_value_history[-1] if sac_metrics_callback.q_value_history else None,
            'final_entropy': sac_metrics_callback.entropy_history[-1] if sac_metrics_callback.entropy_history else None,
            'final_alpha': sac_metrics_callback.alpha_history[-1] if sac_metrics_callback.alpha_history else None,
            'final_action_std': sac_metrics_callback.action_std_history[-1] if sac_metrics_callback.action_std_history else None,
        },
        'episode_rewards': sac_metrics_callback.episode_rewards,
        'episode_co2_grid_kg': sac_metrics_callback.episode_co2_grid,
        'episode_solar_kwh': sac_metrics_callback.episode_solar_kwh,
        'episode_ev_charging_kwh': sac_metrics_callback.episode_ev_charging,
        'episode_grid_import_kwh': sac_metrics_callback.episode_grid_import,
        'episode_bess_discharge_kwh': sac_metrics_callback.episode_bess_discharge_kwh,
        'episode_bess_charge_kwh': sac_metrics_callback.episode_bess_charge_kwh,
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
    print(f'    ✓ result_sac.json: Resumen completo → {result_path}')
    
    print()
    print('  ARCHIVOS GENERADOS:')
    print(f'    ✓ {OUTPUT_DIR}/result_sac.json')
    print(f'    ✓ {OUTPUT_DIR}/timeseries_sac.csv')
    print(f'    ✓ {OUTPUT_DIR}/trace_sac.csv')
    
    print()
    print('='*80)
    print(f'Fin: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*80)


if __name__ == '__main__':
    main()
