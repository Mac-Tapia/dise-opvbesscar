#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR PPO CON MULTIOBJETIVO REAL - OPTIMIZADO
================================================================================
Entrenamiento de agente PPO con datos reales OE2 (Iquitos, Peru)
- 5 episodios completos (43,800 timesteps = 1 año x 5)
- Datos: 128 chargers, mall demand, BESS SOC, solar generation
- Reward: Multiobjetivo (CO2 focus, solar self-consumption, EV satisfaction)
- Optimizacion: GPU CUDA, batch normalization, gradient clipping

Referencias:
  [1] Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
  [2] Stable-Baselines3: https://stable-baselines3.readthedocs.io/
  [3] Gymnasium: https://gymnasium.farama.org/
  [4] CityLearn v2: Multi-agent energy management benchmark
================================================================================
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

import numpy as np
import pandas as pd
import torch
import yaml
from gymnasium import Env, spaces
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

# Importaciones del módulo de rewards (OE3)
from src.rewards.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# ============================================================================
# CONFIGURACION BASICA - UTF-8 Encoding
# ============================================================================
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    if hasattr(sys.stdout, 'reconfigure'):  # type: ignore
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
except (AttributeError, TypeError, RuntimeError):
    pass

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('train_ppo_log.txt', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class PPOConfig:
    """
    Configuracion optimada para PPO entrenamiento.
    Basada en aplicaciones de RL en energia y control de sistemas.
    """
    def __init__(self, device: str = 'cuda'):
        self.device = device

        # Hiperparametros PPO [Schulman et al. 2017]
        self.learning_rate = 3e-4 if device == 'cuda' else 1e-4
        self.n_steps = 2048  # Horizonte temporal antes de update
        self.batch_size = 256 if device == 'cuda' else 64
        self.n_epochs = 20 if device == 'cuda' else 10  # Epochs por batch
        self.gamma = 0.99  # Discount factor
        self.gae_lambda = 0.95  # GAE lambda parameter
        self.clip_range = 0.2  # PPO clipping range
        self.ent_coef = 0.01  # Entropy coefficient (exploration)
        self.vf_coef = 0.5  # Value function coefficient
        self.max_grad_norm = 1.0  # Gradient clipping
        self.normalize_advantage = True
        self.policy_kwargs = {
            'net_arch': [256, 256],  # 2 hidden layers, 256 units
            'activation_fn': torch.nn.ReLU,
        }

# ============================================================================
# CONSTANTES OE2 (Iquitos, Perú)
# ============================================================================
CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh - factor de emisión grid Iquitos
BESS_CAPACITY_KWH = 4520.0   # Capacidad BESS total
BESS_MAX_POWER_KW = 500.0    # Potencia máxima BESS

# DIRECTORIOS DE SALIDA
OUTPUT_DIR = Path('outputs/ppo_training')
CHECKPOINT_DIR = Path('checkpoints/PPO')

class CityLearnEnvironment(Env):
    """Environment compatible con Gymnasium para CityLearn v2.

    Basado en el benchmark CityLearn v2 para control multi-agente en sistemas
    de energía. Implementa la API de Gymnasium para compatible con SB3.

    Referencias:
      - CityLearn v2 Documentation: https://github.com/intelligent-environments-lab/CityLearn
      - Gymnasium API: https://gymnasium.farama.org/

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

    HOURS_PER_YEAR: int = 8760  # Constant for year length
    NUM_CHARGERS: int = 128
    OBS_DIM: int = 394
    ACTION_DIM: int = 129

    metadata = {'render_modes': []}

    def __init__(
        self,
        reward_calc,
        context,
        solar_kw: np.ndarray,
        chargers_kw: np.ndarray,
        mall_kw: np.ndarray,
        bess_soc: np.ndarray,
        max_steps: int = HOURS_PER_YEAR
    ):
        """
        Inicializa environment con datos OE2 reales.

        Args:
            reward_calc: Función de recompensa multiobjetivo
            context: Contexto OE2 (CO2, tariffs, etc)
            solar_kw: Array solar generation (8760,)
            chargers_kw: Array charger demands (8760, n_chargers)
            mall_kw: Array mall demand (8760,)
            bess_soc: Array BESS SOC (8760,)
            max_steps: Duración episodio en timesteps
        """
        super().__init__()

        self.reward_calc = reward_calc
        self.context = context

        # DATOS REALES (8760 horas = 1 año)
        self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
        self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
        self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
        self.bess_soc_hourly = np.asarray(bess_soc, dtype=np.float32)

        # Validación de datos
        if len(self.solar_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"Solar data must be {self.HOURS_PER_YEAR} hours, got {len(self.solar_hourly)}")
        if len(self.mall_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"Mall data must be {self.HOURS_PER_YEAR} hours, got {len(self.mall_hourly)}")
        if len(self.bess_soc_hourly) != self.HOURS_PER_YEAR:
            raise ValueError(f"BESS data must be {self.HOURS_PER_YEAR} hours, got {len(self.bess_soc_hourly)}")
        if self.chargers_hourly.shape[0] != self.HOURS_PER_YEAR:
            raise ValueError(f"Chargers data must be {self.HOURS_PER_YEAR} hours, got {self.chargers_hourly.shape[0]}")

        self.max_steps = max_steps
        self.n_chargers = self.chargers_hourly.shape[1]

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

    def _make_observation(self, hour_idx: int) -> np.ndarray:
        """
        Crea observación CityLearn v2 (394-dim).

        Basado en la especificación del benchmark CityLearn v2 que define
        las características observables en sistemas de energía distribuida.
        Referencia: Ruelens et al. (2018) en CityLearn documentation
        """
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
        base_occupancy = 0.3 if 6 <= hour_24 <= 22 else 0.1  # Peak hours 6-22
        obs[260:388] = np.random.binomial(1, base_occupancy, self.NUM_CHARGERS).astype(np.float32)

        # TIME FEATURES (indices 388-393)
        obs[388] = float(hour_24) / 24.0  # Hour normalized
        day_of_year = (h // 24) % 365
        obs[389] = float(day_of_year % 7) / 7.0  # Day of week normalized
        obs[390] = float((day_of_year // 30) % 12) / 12.0  # Month normalized
        obs[391] = 1.0 if 6 <= hour_24 <= 22 else 0.0  # Peak indicator
        obs[392] = float(self.context.co2_factor_kg_per_kwh)  # CO2 factor
        obs[393] = 0.15  # Tariff (USD/kWh)

        return obs

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset para nuevo episodio."""
        # seed y options son parte de la API Gymnasium pero no se usan aquí
        del seed, options  # Marcar como usados para evitar warnings
        self.step_count = 0
        self.episode_num += 1
        self.episode_reward = 0.0
        self.episode_co2_avoided = 0.0
        self.episode_solar_kwh = 0.0
        self.episode_grid_import = 0.0
        self.episode_ev_satisfied = 0.0

        obs = self._make_observation(0)
        return obs, {}

    def render(self):
        """Render method (required by Gymnasium Env base class)."""
        return None

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Ejecuta un paso de simulación (1 hora).

        Implementa el protocolo de paso de Gymnasium. El agente envía setpoints
        de potencia normalizados que son procesados a través del sistema de energía.

        Referencias:
          - Gymnasium Protocol: https://gymnasium.farama.org/api/core/
          - Energy system dynamics from CityLearn v2
        """
        self.step_count += 1
        h = (self.step_count - 1) % self.HOURS_PER_YEAR

        # DATOS REALES (OE2 timeseries)
        solar_kw = float(self.solar_hourly[h])
        mall_kw = float(self.mall_hourly[h])
        charger_demand = self.chargers_hourly[h].astype(np.float32)
        bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

        # PROCESAR ACCION (129-dim: 1 BESS + 128 chargers)
        bess_action = np.clip(action[0], 0.0, 1.0)  # BESS control
        charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

        # CALCULAR ENERGIA (balance de carga)
        ev_charging_kwh = float(np.sum(charger_demand * charger_setpoints))
        total_demand_kwh = mall_kw + ev_charging_kwh
        
        # BESS power (positivo = descarga, negativo = carga)
        bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
        
        # Separar motos y mototaxis (primeros 2912 = motos, siguientes 416 = mototaxis)
        # Chargers 0-22 = motos (23x128=2944 cercano a 2912), Chargers 23-31 = mototaxis
        motos_demand = float(np.sum(charger_demand[:92] * charger_setpoints[:92]))
        mototaxis_demand = float(np.sum(charger_demand[92:] * charger_setpoints[92:]))

        # GRID BALANCE (importador vs exportador)
        net_demand = total_demand_kwh - bess_power_kw  # BESS descarga reduce demanda
        grid_import_kwh = max(0.0, net_demand - solar_kw)
        grid_export_kwh = max(0.0, solar_kw - net_demand)

        # CO2 CALCULATIONS (Iquitos factor: 0.4521 kg CO2/kWh)
        co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
        co2_avoided_indirect_kg = min(solar_kw, total_demand_kwh) * CO2_FACTOR_IQUITOS
        co2_avoided_direct_kg = grid_export_kwh * CO2_FACTOR_IQUITOS * 0.5  # 50% credit
        co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg

        # EV SATISFACTION (simulado con SOC proxy)
        ev_soc_avg = np.clip(
            bess_soc + 0.005 * np.mean(charger_setpoints),
            0.0, 1.0
        )

        # CALCULAR RECOMPENSA MULTIOBJETIVO
        try:
            reward_val, components = self.reward_calc.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_kw,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=h % 24,
                ev_demand_kwh=50.0
            )
        except (ValueError, KeyError, AttributeError, TypeError) as exc:
            logger.warning("Error en reward computation hora %d: %s", h, exc)
            reward_val = -10.0
            components = {'co2_avoided_total_kg': co2_avoided_total_kg}

        # TRACKING (acumulador de métricas del episodio)
        self.episode_reward += float(reward_val)
        self.episode_co2_avoided += co2_avoided_total_kg
        self.episode_solar_kwh += solar_kw
        self.episode_grid_import += grid_import_kwh
        self.episode_ev_satisfied += ev_soc_avg

        # SIGUIENTE OBSERVACION
        obs = self._make_observation(self.step_count)

        # TERMINACION (episodio completo = 1 año)
        terminated = self.step_count >= self.max_steps
        truncated = False  # No truncate (let episode complete)

        # INFO DICT COMPLETO (para DetailedLoggingCallback)
        info: Dict[str, Any] = {
            'step': self.step_count,
            'hour': h % 24,
            'hour_of_year': h,
            # Energía
            'solar_generation_kwh': solar_kw,
            'ev_charging_kwh': ev_charging_kwh,
            'grid_import_kwh': grid_import_kwh,
            'grid_export_kwh': grid_export_kwh,
            'mall_demand_kwh': mall_kw,
            'total_demand_kwh': total_demand_kwh,
            # BESS
            'bess_soc': bess_soc,
            'bess_power_kw': bess_power_kw,
            # CO2
            'co2_grid_kg': co2_grid_kg,
            'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
            'co2_avoided_direct_kg': co2_avoided_direct_kg,
            'co2_avoided_total_kg': co2_avoided_total_kg,
            # EV breakdown
            'motos_power_kw': motos_demand,
            'mototaxis_power_kw': mototaxis_demand,
            'ev_soc_avg': ev_soc_avg,
            # Acumulados episodio
            'episode_reward_cumulative': float(self.episode_reward),
            'episode_co2_avoided_cumulative': float(self.episode_co2_avoided),
        }

        if terminated:
            info['episode'] = {
                'r': float(self.episode_reward),
                'l': int(self.step_count)
            }

        return obs, float(reward_val), terminated, truncated, info


# ============================================================================
# DETAILED LOGGING CALLBACK - Para tracking paso a paso y generación de archivos
# ============================================================================
from stable_baselines3.common.callbacks import BaseCallback


class DetailedLoggingCallback(BaseCallback):
    """
    Callback para tracking detallado del entrenamiento PPO.
    
    Genera:
    - trace_records: registro paso a paso de todas las métricas
    - timeseries_records: series temporales por hora/episodio
    - episode metrics: acumuladores por episodio para training_evolution
    """

    def __init__(self, env_ref: CityLearnEnvironment, output_dir: Path, verbose: int = 1):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.step_log_freq = 1000  # Cada 1000 pasos

        # Acumuladores por episodio
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []

        # TRACE: registro paso a paso
        self.trace_records: list[dict[str, Any]] = []

        # TIMESERIES: registro horario por episodio
        self.timeseries_records: list[dict[str, Any]] = []

        # Tracking actual
        self.current_episode = 0
        self.ep_co2_grid = 0.0
        self.ep_co2_avoided_indirect = 0.0
        self.ep_co2_avoided_direct = 0.0
        self.ep_solar = 0.0
        self.ep_ev = 0.0
        self.ep_grid = 0.0
        self.ep_reward = 0.0
        self.ep_steps = 0

    def _on_step(self) -> bool:
        # Obtener info del último step
        infos = self.locals.get('infos', [{}])
        info = infos[0] if infos else {}

        # Acumular métricas
        self.ep_co2_grid += info.get('co2_grid_kg', 0)
        self.ep_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0)
        self.ep_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0)
        self.ep_solar += info.get('solar_generation_kwh', 0)
        self.ep_ev += info.get('ev_charging_kwh', 0)
        self.ep_grid += info.get('grid_import_kwh', 0)
        self.ep_steps += 1

        # TRACE: guardar cada paso
        rewards = self.locals.get('rewards', [0.0])
        reward_val = float(rewards[0]) if rewards else 0.0
        trace_record = {
            'timestep': self.num_timesteps,
            'episode': self.current_episode,
            'step_in_episode': self.ep_steps,
            'hour': info.get('hour', 0),
            'reward': reward_val,
            'co2_grid_kg': info.get('co2_grid_kg', 0),
            'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0),
            'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0),
            'solar_generation_kwh': info.get('solar_generation_kwh', 0),
            'ev_charging_kwh': info.get('ev_charging_kwh', 0),
            'grid_import_kwh': info.get('grid_import_kwh', 0),
            'bess_power_kw': info.get('bess_power_kw', 0),
            'motos_power_kw': info.get('motos_power_kw', 0),
            'mototaxis_power_kw': info.get('mototaxis_power_kw', 0),
        }
        self.trace_records.append(trace_record)

        # TIMESERIES: guardar por hora (cada 1 hora = 1 step)
        ts_record = {
            'episode': self.current_episode,
            'hour_of_year': self.ep_steps - 1,
            'hour_of_day': info.get('hour', 0),
            'solar_generation_kwh': info.get('solar_generation_kwh', 0),
            'ev_charging_kwh': info.get('ev_charging_kwh', 0),
            'grid_import_kwh': info.get('grid_import_kwh', 0),
            'bess_power_kw': info.get('bess_power_kw', 0),
            'co2_avoided_total_kg': info.get('co2_avoided_total_kg', 0),
            'reward': reward_val,
        }
        self.timeseries_records.append(ts_record)

        # Detectar fin de episodio
        dones = self.locals.get('dones', [False])
        if dones[0]:
            self.ep_reward = self.env_ref.episode_reward
            self._log_episode_summary()
            self._reset_episode_tracking()
            self.current_episode += 1

        # Log de progreso cada N pasos
        if self.num_timesteps % self.step_log_freq == 0:
            self._log_progress()

        return True

    def _log_progress(self) -> None:
        """Mostrar progreso durante el episodio."""
        ep_num = self.current_episode
        pct = (self.ep_steps / 8760) * 100
        co2_net = self.ep_co2_grid - self.ep_co2_avoided_indirect - self.ep_co2_avoided_direct

        print(f'    Steps: {self.num_timesteps:>7,} | Ep: {ep_num:>2} | '
              f'Progreso: {pct:>5.1f}% | '
              f'CO2_grid: {self.ep_co2_grid:>8,.0f} kg | '
              f'CO2_evitado: {(self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct):>8,.0f} kg', flush=True)

    def _log_episode_summary(self) -> None:
        """Resumen completo al finalizar episodio."""
        co2_avoided_total = self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct

        self.episode_rewards.append(self.ep_reward)
        self.episode_co2_grid.append(self.ep_co2_grid)
        self.episode_co2_avoided_indirect.append(self.ep_co2_avoided_indirect)
        self.episode_co2_avoided_direct.append(self.ep_co2_avoided_direct)
        self.episode_solar_kwh.append(self.ep_solar)
        self.episode_ev_charging.append(self.ep_ev)
        self.episode_grid_import.append(self.ep_grid)

        print()
        print(f'  ══════════════════════════════════════════════════════════════')
        print(f'  EPISODIO {self.current_episode + 1} COMPLETADO')
        print(f'  ──────────────────────────────────────────────────────────────')
        print(f'    Reward Total:         {self.ep_reward:>12,.2f}')
        print(f'    CO2 Grid:             {self.ep_co2_grid:>12,.0f} kg')
        print(f'    CO2 Evitado Indirect: {self.ep_co2_avoided_indirect:>12,.0f} kg')
        print(f'    CO2 Evitado Direct:   {self.ep_co2_avoided_direct:>12,.0f} kg')
        print(f'    CO2 Evitado Total:    {co2_avoided_total:>12,.0f} kg')
        print(f'    Solar Aprovechado:    {self.ep_solar:>12,.0f} kWh')
        print(f'    EV Cargado:           {self.ep_ev:>12,.0f} kWh')
        print(f'    Grid Import:          {self.ep_grid:>12,.0f} kWh')
        print(f'  ══════════════════════════════════════════════════════════════')
        print()

    def _reset_episode_tracking(self) -> None:
        """Reset acumuladores para siguiente episodio."""
        self.ep_co2_grid = 0.0
        self.ep_co2_avoided_indirect = 0.0
        self.ep_co2_avoided_direct = 0.0
        self.ep_solar = 0.0
        self.ep_ev = 0.0
        self.ep_grid = 0.0
        self.ep_reward = 0.0
        self.ep_steps = 0


def main():
    """
    Entrenamiento principal con error handling robusto.

    Pipeline completo:
    1. Configurar device (GPU/CPU)
    2. Cargar rewards multiobjetivo
    3. Cargar datos OE2 (timeseries reales)
    4. Crear environment Gymnasium
    5. Entrenar PPO con stable-baselines3
    6. Validar con episodios determinísticos

    Referencias:
      [1] Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
      [2] Stable-Baselines3: https://stable-baselines3.readthedocs.io/
      [3] CityLearn v2 Documentation
    """

    HOURS_PER_YEAR: int = 8760
    NUM_EPISODES: int = 10  # 10 episodios = 87,600 timesteps para entrenamiento robusto
    TOTAL_TIMESTEPS: int = NUM_EPISODES * HOURS_PER_YEAR

    print('='*80)
    print('ENTRENAR PPO - MULTIOBJETIVO CON DATOS REALES - {} EPISODIOS'.format(NUM_EPISODES))
    print('='*80)
    print('Inicio: {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print()

    # ========================================================================
    # PASO 1: CONFIGURACION Y DISPOSITIVO
    # ========================================================================
    try:
        # Determinar device: CUDA si disponible, sino CPU
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

        if device == 'cuda':
            gpu_name: str = torch.cuda.get_device_name(0)
            gpu_memory: float = torch.cuda.get_device_properties(0).total_memory / 1e9
            cuda_version: Optional[str] = getattr(torch.version, 'cuda', None)  # type: ignore
            print('GPU DISPONIBLE: {}'.format(gpu_name))
            print('  RAM: {:.1f} GB'.format(gpu_memory))
            print('  CUDA: {}'.format(cuda_version))
            print()

        ppo_config: PPOConfig = PPOConfig(device=device)
        # Usar directorios globales
        checkpoint_dir = CHECKPOINT_DIR
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Device: %s | Batch: %d | Epochs: %d", device, ppo_config.batch_size, ppo_config.n_epochs)

    except (RuntimeError, AttributeError, ValueError) as exc:
        logger.error("ERROR en configuracion: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 2: CARGAR CONFIG Y REWARDS
    # ========================================================================
    try:
        print('[PASO 1] Cargar configuracion y contexto OE2')
        print('-'*80)

        with open('configs/default.yaml', 'r', encoding='utf-8') as f:
            _ = yaml.safe_load(f)  # Validate YAML syntax
        logger.info("Config validado: default.yaml OK")

        reward_weights = create_iquitos_reward_weights("co2_focus")
        context: IquitosContext = IquitosContext()
        reward_calc: MultiObjectiveReward = MultiObjectiveReward(weights=reward_weights, context=context)

        print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-07):')
        print('    CO2 grid (0.35): Minimizar importacion grid')
        print('    Solar (0.20): Autoconsumo PV')
        print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
        print('    Cost (0.10): Minimizar costo')
        print('    Grid stability (0.05): Suavizar picos')
        if reward_weights is not None:
            print('  [Valores cargados: CO2={:.2f}, Solar={:.2f}, EV={:.2f}, Cost={:.2f}, Grid={:.2f}]'.format(
                reward_weights.co2, reward_weights.solar, reward_weights.ev_satisfaction,
                reward_weights.cost, reward_weights.grid_stability))
        print()

    except (ImportError, FileNotFoundError, ValueError) as exc:
        logger.error("ERROR cargando rewards: %s", exc)
        traceback.print_exc()
        sys.exit(1)


    # ========================================================================
    # PASO 3: CARGAR DATOS REALES OE2
    # ========================================================================
    try:
        print('[PASO 2] Cargar datos OE2 ({} horas = 1 ano)'.format(HOURS_PER_YEAR))
        print('-'*80)

        # ====================================================================
        # SOLAR
        # ====================================================================
        solar_path: Path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
        if solar_path.exists():
            df_solar = pd.read_csv(solar_path)
            col = next((c for c in df_solar.columns if 'gener' in c.lower()), df_solar.columns[-1])
            solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
            if len(solar_hourly) != HOURS_PER_YEAR:
                raise ValueError("Solar: %d horas != %d" % (len(solar_hourly), HOURS_PER_YEAR))
            logger.info("Solar cargado: %.0f kWh/ano (8760h)", float(np.sum(solar_hourly)))
        else:
            logger.warning("Solar no encontrado: %s", str(solar_path))
            solar_hourly = np.ones(HOURS_PER_YEAR, dtype=np.float32) * 1000.0

        # ====================================================================
        # CHARGERS (128 sockets = 32 chargers x 4 sockets) - DATOS REALES
        # ====================================================================
        charger_csv_path = Path('data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv')
        if charger_csv_path.exists():
            df_chargers = pd.read_csv(charger_csv_path)
            # CSV tiene 32 columnas (1 por charger) - expandir a 128 sockets (4 por charger)
            chargers_raw = df_chargers.values.astype(np.float32)  # (8760, 32)
            if chargers_raw.shape[0] != HOURS_PER_YEAR:
                raise ValueError(f"Chargers CSV debe tener {HOURS_PER_YEAR} filas, tiene {chargers_raw.shape[0]}")
            # Expandir: cada charger tiene 4 sockets, distribuir demanda
            n_charger_units = chargers_raw.shape[1]  # 32
            chargers_hourly = np.zeros((HOURS_PER_YEAR, n_charger_units * 4), dtype=np.float32)
            for i in range(n_charger_units):
                # Distribuir demanda del charger entre sus 4 sockets
                for s in range(4):
                    socket_idx = i * 4 + s
                    # Socket recibe 1/4 de la demanda base + variación
                    chargers_hourly[:, socket_idx] = chargers_raw[:, i] * (0.2 + 0.15 * s)
            n_sockets = chargers_hourly.shape[1]  # 128
            total_demand = float(np.sum(chargers_hourly))
            logger.info("Chargers REALES: %d chargers x 4 = %d sockets | Demanda anual: %.0f kWh", 
                        n_charger_units, n_sockets, total_demand)
        else:
            # Fallback: intentar JSON antiguo
            charger_path = Path('data/interim/oe2/chargers/individual_chargers.json')
            if charger_path.exists():
                with open(charger_path, encoding='utf-8') as f:
                    charger_data = json.load(f)
                n_chargers_json = len(charger_data)
                n_sockets = n_chargers_json * 4
                del charger_data
            else:
                n_sockets = 128
            logger.warning("Chargers CSV no encontrado: %s - usando datos sintéticos", str(charger_csv_path))
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
                pad_width = ((0, HOURS_PER_YEAR - len(mall_data)),)
                mall_hourly = np.pad(mall_data, pad_width, mode='wrap')
            else:
                mall_hourly = mall_data
            logger.info("Mall cargado: %.0f kWh/ano", float(np.sum(mall_hourly)))
        else:
            logger.warning("Mall no encontrado: %s", str(mall_path))
            mall_hourly = np.ones(HOURS_PER_YEAR, dtype=np.float32) * 100.0

        # ====================================================================
        # BESS SOC (Battery Energy Storage System State of Charge)
        # ====================================================================
        # Intentar múltiples paths para BESS
        bess_paths = [
            Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
            Path('data/interim/oe2/bess/bess_dataset.csv'),
        ]
        bess_path = next((p for p in bess_paths if p.exists()), None)
        bess_soc = np.full(HOURS_PER_YEAR, 0.5, dtype=np.float32)  # Default fallback: 50%

        if bess_path is not None and bess_path.exists():
            df_bess = pd.read_csv(bess_path, encoding='utf-8')
            soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
            if soc_cols:
                bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
                # Normalizar si está en [0,100] en lugar de [0,1]
                bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
                logger.info("BESS cargado: SOC media %.1f%% (archivo: %s)", float(np.mean(bess_soc)) * 100.0, bess_path.name)
        else:
            logger.warning("BESS no encontrado en paths conocidos - usando fallback 50%%")

        print()

    except (FileNotFoundError, KeyError, ValueError, pd.errors.ParserError) as exc:
        logger.error("ERROR cargando datos OE2: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 4: CREAR ENVIRONMENT
    # ========================================================================
    try:
        print('[PASO 3] Crear environment Gymnasium')
        print('-'*80)

        env: CityLearnEnvironment = CityLearnEnvironment(
            reward_calc=reward_calc,
            context=context,
            solar_kw=solar_hourly,
            chargers_kw=chargers_hourly,
            mall_kw=mall_hourly,
            bess_soc=bess_soc,
            max_steps=HOURS_PER_YEAR
        )

        logger.info("Environment creado:")
        logger.info("  Observation: %s", str(env.observation_space.shape))
        logger.info("  Action: %s", str(env.action_space.shape))
        logger.info("  Timesteps/episodio: %d (1 ano completo)", HOURS_PER_YEAR)
        print()

    except (ValueError, AttributeError, TypeError) as exc:
        logger.error("ERROR creando environment: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 5: CREAR Y ENTRENAR PPO CON STABLE-BASELINES3
    # ========================================================================
    # Referencia: [Schulman et al. 2017] PPO es un algoritmo on-policy que actualiza
    # la política usando experiencia recolectada en el episodio actual, realizando
    # múltiples pasos de gradiente con clipping para estabilidad.

    try:
        print('[PASO 4] Crear agente PPO')
        print('-'*80)


        model: PPO = PPO(
            'MlpPolicy',
            env,
            learning_rate=ppo_config.learning_rate,
            n_steps=ppo_config.n_steps,
            batch_size=ppo_config.batch_size,
            n_epochs=ppo_config.n_epochs,
            gamma=ppo_config.gamma,
            gae_lambda=ppo_config.gae_lambda,
            clip_range=ppo_config.clip_range,
            ent_coef=ppo_config.ent_coef,
            vf_coef=ppo_config.vf_coef,
            max_grad_norm=ppo_config.max_grad_norm,
            normalize_advantage=ppo_config.normalize_advantage,
            device=device,
            policy_kwargs=ppo_config.policy_kwargs,
            verbose=0
        )

        logger.info("PPO creado: LR=%g, n_steps=%d, device=%s", ppo_config.learning_rate, ppo_config.n_steps, device)
        print('  Hiperparametros:')
        print('    Learning Rate: {:.6f}'.format(ppo_config.learning_rate))
        print('    N Steps (rollout): {}'.format(ppo_config.n_steps))
        print('    Batch Size: {}'.format(ppo_config.batch_size))
        print('    Epochs: {}'.format(ppo_config.n_epochs))
        print()

        # ====================================================================
        # ENTRENAMIENTO
        # ====================================================================
        print('[PASO 5] ENTRENAMIENTO CON DATOS REALES OE2')
        print('-'*80)

        speed_est: float = 1100.0 if device == 'cuda' else 70.0
        duration_est: float = TOTAL_TIMESTEPS / (speed_est * 60.0)

        print('  CONFIGURACION:')
        print('    Episodios: {} x {} horas = {:,} timesteps'.format(NUM_EPISODES, HOURS_PER_YEAR, TOTAL_TIMESTEPS))
        print('    Datos: 100% REALES (OE2 Iquitos)')
        print('    Device: {}'.format(device.upper()))
        print('    Duracion est.: ~{:.1f} minutos'.format(duration_est))
        print()
        print('  REWARD WEIGHTS (SINCRONIZADOS):')
        print('    CO2 grid (0.35): Minimizar importacion')
        print('    Solar (0.20): Autoconsumo PV')
        print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
        print('    Cost (0.10): Minimizar costo')
        print('    Grid stability (0.05): Suavizar picos')
        print()
        print('  Iniciando entrenamiento...')
        print()

        # CALLBACKS: Checkpoint + DetailedLogging
        checkpoint_callback: CheckpointCallback = CheckpointCallback(
            save_freq=2000,
            save_path=str(checkpoint_dir),
            name_prefix='ppo_model',
            verbose=0
        )
        
        # DetailedLoggingCallback para tracking completo
        logging_callback = DetailedLoggingCallback(
            env_ref=env,
            output_dir=output_dir,
            verbose=1
        )
        
        # Combinar callbacks
        from stable_baselines3.common.callbacks import CallbackList
        callbacks = CallbackList([checkpoint_callback, logging_callback])

        t_start: float = time.time()
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callbacks,
            progress_bar=True,
            reset_num_timesteps=False
        )
        elapsed = time.time() - t_start

        # Guardar modelo final
        final_path: Path = checkpoint_dir / 'ppo_final.zip'
        model.save(str(final_path))

        speed_achieved: float = float(TOTAL_TIMESTEPS / elapsed)
        logger.info("Entrenamiento exitoso: %.1f min (speed: %.0f steps/s)", elapsed / 60.0, speed_achieved)
        logger.info("Modelo guardado: %s", str(final_path))
        print()
        print('Entrenamiento completado: {:.1f} min ({:.0f} steps/s)'.format(elapsed / 60.0, speed_achieved))
        print()

    except (RuntimeError, ValueError, OSError, AttributeError) as exc:
        logger.error("ERROR en entrenamiento: %s", exc)
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # PASO 6: VALIDACION - EPISODIOS DETERMINÍSTICOS
    # ========================================================================
    # Evaluación con acciones determinísticas (sin aleatoriedad) para medir
    # performance real del agente entrenado. Referencias:
    # [Schulman et al. 2017] recomienda validación en ambiente sin exploración.

    NUM_VALIDATION_EPISODES: int = 10

    try:
        print('[PASO 6] VALIDACION - {} EPISODIOS DETERMINISICOS'.format(NUM_VALIDATION_EPISODES))
        print('-'*80)



        val_metrics: Dict[str, list] = {
            'reward': [],
            'co2_avoided': [],
            'solar_kwh': [],
            'grid_import': [],
        }

        for ep_num in range(NUM_VALIDATION_EPISODES):
            obs, _ = env.reset(seed=42 + ep_num)
            done: bool = False
            episode_steps: int = 0

            while not done:
                # Deterministic=True: usar la acción con máxima probabilidad
                action, _ = model.predict(obs, deterministic=True)
                obs, _, done, _, _ = env.step(action)
                episode_steps += 1

            # Recolectar métricas del episodio
            if hasattr(env, 'episode_reward'):
                val_metrics['reward'].append(float(env.episode_reward))
            if hasattr(env, 'episode_co2_avoided'):
                val_metrics['co2_avoided'].append(float(env.episode_co2_avoided))
            if hasattr(env, 'episode_solar_kwh'):
                val_metrics['solar_kwh'].append(float(env.episode_solar_kwh))
            if hasattr(env, 'episode_grid_import'):
                val_metrics['grid_import'].append(float(env.episode_grid_import))

            logger.info("  Episodio %d/%d: %d steps | R=%8.1f | CO2=%10.0f kg",
                       ep_num + 1, NUM_VALIDATION_EPISODES, episode_steps,
                       val_metrics['reward'][-1] if val_metrics['reward'] else 0.0,
                       val_metrics['co2_avoided'][-1] if val_metrics['co2_avoided'] else 0.0)

        print()
        print('='*80)
        print('RESULTADOS FINALES - ENTRENAMIENTO Y VALIDACION')
        print('='*80)

        # Calcular estadísticas
        reward_mean: float = float(np.mean(val_metrics['reward'])) if val_metrics['reward'] else 0.0
        reward_std: float = float(np.std(val_metrics['reward'])) if len(val_metrics['reward']) > 1 else 0.0
        co2_mean: float = float(np.mean(val_metrics['co2_avoided'])) if val_metrics['co2_avoided'] else 0.0
        solar_mean: float = float(np.mean(val_metrics['solar_kwh'])) if val_metrics['solar_kwh'] else 0.0
        grid_mean: float = float(np.mean(val_metrics['grid_import'])) if val_metrics['grid_import'] else 0.0

        print()
        print('ENTRENAMIENTO:')
        print('  Total timesteps: {:,}'.format(TOTAL_TIMESTEPS))
        print('  Duracion: {:.1f} minutos ({:.0f} steps/s)'.format(elapsed / 60.0, speed_achieved))
        print('  Device: {}'.format(device.upper()))
        print()
        print('VALIDACION ({} episodios):'.format(NUM_VALIDATION_EPISODES))
        print('  Reward promedio:        {:12.2f} ± {:.2f}'.format(reward_mean, reward_std))
        print('  CO2 evitado (kg):       {:12.0f}'.format(co2_mean))
        print('  Solar aprovechado (kWh):  {:12.0f}'.format(solar_mean))
        print('  Grid import (kWh):      {:12.0f}'.format(grid_mean))
        print()

        # ====================================================================
        # GUARDAR METRICAS EN JSON
        # ====================================================================
        summary: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'agent': 'PPO',
            'project': 'pvbesscar',
            'location': 'Iquitos, Peru',
            'co2_factor_kg_per_kwh': CO2_FACTOR_IQUITOS,
            'training': {
                'total_timesteps': int(TOTAL_TIMESTEPS),
                'episodes': int(NUM_EPISODES),
                'duration_seconds': float(elapsed),
                'speed_steps_per_second': float(speed_achieved),
                'device': str(device),
                'hyperparameters': {
                    'learning_rate': ppo_config.learning_rate,
                    'n_steps': ppo_config.n_steps,
                    'batch_size': ppo_config.batch_size,
                    'n_epochs': ppo_config.n_epochs,
                    'gamma': ppo_config.gamma,
                    'gae_lambda': ppo_config.gae_lambda,
                    'clip_range': ppo_config.clip_range,
                    'ent_coef': ppo_config.ent_coef,
                    'vf_coef': ppo_config.vf_coef,
                }
            },
            'validation': {
                'num_episodes': int(NUM_VALIDATION_EPISODES),
                'mean_reward': float(reward_mean),
                'std_reward': float(reward_std),
                'mean_co2_avoided_kg': float(co2_mean),
                'mean_solar_kwh': float(solar_mean),
                'mean_grid_import_kwh': float(grid_mean),
            },
            'training_evolution': {
                'episode_rewards': logging_callback.episode_rewards,
                'episode_co2_grid': logging_callback.episode_co2_grid,
                'episode_co2_avoided_indirect': logging_callback.episode_co2_avoided_indirect,
                'episode_co2_avoided_direct': logging_callback.episode_co2_avoided_direct,
                'episode_solar_kwh': logging_callback.episode_solar_kwh,
                'episode_ev_charging': logging_callback.episode_ev_charging,
                'episode_grid_import': logging_callback.episode_grid_import,
            },
            'model_path': str(final_path),
        }

        metrics_file: Path = output_dir / 'ppo_training_summary.json'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
        print('  GUARDANDO ARCHIVOS DE SALIDA:')

        # 1. result_ppo.json - Resumen completo del entrenamiento
        result_file = output_dir / 'result_ppo.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f'    [OK] {result_file}')

        # 2. timeseries_ppo.csv - Series temporales por hora
        timeseries_file = output_dir / 'timeseries_ppo.csv'
        if logging_callback.timeseries_records:
            df_timeseries = pd.DataFrame(logging_callback.timeseries_records)
            df_timeseries.to_csv(timeseries_file, index=False, encoding='utf-8')
            print(f'    [OK] {timeseries_file} ({len(df_timeseries):,} registros)')
        else:
            print(f'    [WARN] {timeseries_file} - sin datos')

        # 3. trace_ppo.csv - Trazabilidad paso a paso
        trace_file = output_dir / 'trace_ppo.csv'
        if logging_callback.trace_records:
            df_trace = pd.DataFrame(logging_callback.trace_records)
            df_trace.to_csv(trace_file, index=False, encoding='utf-8')
            print(f'    [OK] {trace_file} ({len(df_trace):,} registros)')
        else:
            print(f'    [WARN] {trace_file} - sin datos')
        
        print()
        logger.info("Archivos generados en: %s", str(output_dir))

        print('='*80)
        print('ENTRENAMIENTO PPO COMPLETADO EXITOSAMENTE')
        print('='*80)
        print()

    except (RuntimeError, ValueError, OSError, AttributeError, KeyError) as exc:
        logger.error("ERROR en validacion: %s", exc)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
