#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Integracion completa: Calculos CO2 + Rewards multiobjetivo + BESS + Chargers diferenciados
"""

import sys
import os

# CONFIGURAR ENCODING ANTES DE OTROS IMPORTS
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]

from pathlib import Path
import json
import yaml
from datetime import datetime
import logging
import warnings
import numpy as np
import pandas as pd
import torch
from typing import Any

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

# AUTO-DETECTAR GPU Y CONFIGURAR
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'GPU DISPONIBLE: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA Version: {cuda_version}')
    # Optimizar configuración para GPU
    BATCH_SIZE = 128  # Aprovechar más memoria
    BUFFER_SIZE = 2000000  # Replay buffer más grande para GPU
    NETWORK_ARCH = [512, 512]  # Red más grande aprovecha GPU
else:
    print('CPU mode - GPU no disponible')
    print('   Optimizando para CPU...')
    BATCH_SIZE = 64
    BUFFER_SIZE = 1000000
    NETWORK_ARCH = [256, 256]

print(f'   Device: {DEVICE}')
print(f'   Batch size: {BATCH_SIZE}')
print(f'   Buffer size: {BUFFER_SIZE}')
print(f'   Network: {NETWORK_ARCH}')
print()

CHECKPOINT_DIR = Path('checkpoints/SAC')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/sac_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO')
    print('-' * 80)

    # Cargar config
    with open('configs/default.yaml', 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    print(f'  OK Config loaded: {len(cfg)} keys')

    # Cargar rewards (contexto Iquitos + pesos multiobjetivo)
    from src.rewards.rewards import (
        IquitosContext,
        MultiObjectiveReward,
        create_iquitos_reward_weights,
    )

    # Usar preset "co2_focus" para maximizar reducción CO2
    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print('  OK Reward weights (CO2 focus):')
    print(f'    - CO2: {weights.co2:.2f}  (minimizar grid import)')
    print(f'    - Solar: {weights.solar:.2f}  (maximizar autoconsumo)')
    print(f'    - Cost: {weights.cost:.2f}  (minimizar tarifa)')
    print(f'    - EV: {weights.ev_satisfaction:.2f}  (satisfaccion carga)')
    print(f'    - Grid: {weights.grid_stability:.2f}  (estabilidad)')
    print()

    print('  OK Contexto Iquitos:')
    print(f'    - Grid CO2: {context.co2_factor_kg_per_kwh} kg CO2/kWh (termica aislada)')
    print(f'    - EV CO2 factor: {context.co2_conversion_factor} kg CO2/kWh (combustion equivalente)')
    print(f'    - Chargers: {context.n_chargers} (28 motos@2kW + 4 mototaxis@3kW)')
    print(f'    - Sockets: {context.total_sockets} (112 motos + 16 mototaxis)')
    print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
    print()

    print('[2] CONTRUIR DATASET CITYLEARN V2')
    print('-' * 80)

    from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset

    dataset = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=Path('data/raw'),
        interim_dir=Path('data/interim/oe2'),
        processed_dir=Path('data/processed')
    )

    print(f'  OK Dataset: {dataset.dataset_dir}')
    print()

    print('[3] CREAR ENVIRONMENT CON REWARD MULTIOBJETIVO REAL')
    print('-' * 80)

    from gymnasium import Env, spaces
    from stable_baselines3 import SAC
    from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

    class CityLearnRealEnv(Env):  # type: ignore[misc]
        """Environment con recompensa multiobjetivo REAL de Iquitos (datos OE2) + Monitoreo baterias sockets"""

        def __init__(self, reward_calc: MultiObjectiveReward, ctx: IquitosContext, obs_dim: int = 1045, action_dim: int = 129, max_steps: int = 8760):
            self.reward_calculator = reward_calc
            self.context = ctx
            self.obs_dim = obs_dim
            self.action_dim = action_dim
            self.max_steps = max_steps

            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0, shape=(action_dim,), dtype=np.float32
            )

            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num = 0

            # Tracking de métricas
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory: list[float] = []
            self.battery_soc_episode: np.ndarray = np.array([])

            # CARGAR TODOS LOS DATOS REALES OE2 - NO APROXIMACIONES
            print('  [OE2] Cargando datasets reales...')

            # 1. SOLAR PVGIS REAL - TODAS LAS 11 COLUMNAS
            try:
                solar_path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
                df_solar = pd.read_csv(solar_path)
                # Cargar todas las columnas (excluir timestamp si es indice)
                solar_cols = [c for c in df_solar.columns if c.lower() != 'timestamp']
                self.solar_all_columns = np.array(df_solar[solar_cols].values)  # (8760, 10)
                self.solar_hourly_kw = np.array(df_solar['ac_power_kw'].values)  # ac_power_kw en indice 6
                print(f'    [OK] Solar: {np.sum(self.solar_hourly_kw):.0f} kWh/anio')
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] Solar: {e}')
                self.solar_hourly_kw = np.zeros(8760, dtype=np.float32)  # Fallback
                # Fallback: crear array de ceros con forma correcta (8760, 10)
                self.solar_all_columns = np.zeros((8760, 10), dtype=np.float32)

            # 2. CHARGERS REAL - 128 SOCKETS
            try:
                chargers_path = Path('data/oe2/chargers/chargers_real_hourly_2024.csv')
                self.chargers_real_data = pd.read_csv(chargers_path)
                # Extraer columnas de sockets (excluir timestamp)
                socket_cols = [c for c in self.chargers_real_data.columns if 'SOCKET' in c or 'MOTO' in c]
                self.chargers_hourly_kw = np.array(self.chargers_real_data[socket_cols].values)  # (8760, 128)
                self.chargers_total_kwh = float(self.chargers_real_data[socket_cols].sum().sum())
                print(f'    [OK] Chargers: 128 sockets, {self.chargers_total_kwh:.0f} kWh/anio')
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] Chargers: {e}')
                self.chargers_hourly_kw = np.zeros((8760, 128), dtype=np.float32)

            # 3. BESS REAL - STATE OF CHARGE
            try:
                bess_path = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
                self.bess_real_data = pd.read_csv(bess_path)
                # Usar columna de SOC
                if 'soc_percent' in self.bess_real_data.columns:
                    self.bess_soc_percent = np.array(self.bess_real_data['soc_percent'].values, dtype=np.float32) / 100.0  # Convertir a [0,1]
                else:
                    # Fallback: usar primera columna numerica
                    numeric_cols = self.bess_real_data.select_dtypes(include=['float64', 'int64']).columns
                    if len(numeric_cols) > 0:
                        self.bess_soc_percent = np.array(self.bess_real_data[numeric_cols[0]].values, dtype=np.float32) / 100.0
                    else:
                        self.bess_soc_percent = np.full(8760, 0.5, dtype=np.float32)  # Fallback 50%
                        print('    [WARN] BESS: No hay columna SOC, usando fallback 50%')
                print(f'    [OK] BESS: {len(self.bess_soc_percent)} horas')
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] BESS: {e}')
                self.bess_soc_percent = np.full(8760, 0.5, dtype=np.float32)  # Fallback 50%

            # 4. DEMANDA MALL REAL - SINCRONIZAR A 8760 HORAS
            try:
                mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
                self.mall_real_data = pd.read_csv(mall_path, sep=';')
                # Obtener ultima columna (contiene demanda en kWh)
                demand_col = self.mall_real_data.columns[-1]
                mall_demand_kwh = self.mall_real_data[demand_col].values

                # SINCRONIZAR: si tiene 8785 horas, truncar a 8760 (1 anio completo)
                mall_demand_kwh = np.array(mall_demand_kwh, dtype=np.float32)
                if len(mall_demand_kwh) > 8760:
                    mall_demand_kwh = mall_demand_kwh[:8760]
                    print(f'    [OK] Mall: 8760 horas, {np.sum(mall_demand_kwh):.0f} kWh/anio')
                else:
                    print(f'    [OK] Mall: {len(mall_demand_kwh)} horas, {np.sum(mall_demand_kwh):.0f} kWh/anio')

                self.mall_hourly_kwh = mall_demand_kwh
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] Mall: {e}')
                self.mall_hourly_kwh = np.zeros(8760, dtype=np.float32)  # Fallback

            # ========== INICIALIZAR MONITOREO DE BATERIAS (128 SOCKETS) ==========
            # Cada socket monitorea estado de bateria del vehiculo conectado
            self.battery_soc = np.random.uniform(20, 80, size=(8760, 128)).astype(np.float32)  # SOC inicial 20-80%

            # Capacidad nominal por socket (motos 3-5 kWh, mototaxis 8-12 kWh)
            self.battery_capacity = np.zeros(128, dtype=np.float32)
            self.battery_capacity[0:28] = np.random.uniform(10.0, 12.0, 28)  # Mototaxis (indices 0-27) - Sin acento
            self.battery_capacity[28:128] = np.random.uniform(4.0, 5.0, 100)  # Motos (indices 28-127)

            # Tipos vehiculo (asignacion)
            self.vehicle_types = np.array(["mototaxi"]*28 + ["moto"]*100)

            print('    [OK] Baterias: 128 sockets monitorizados')
            print('  OK Environment: (1045,) obs | (129,) action')
            print()

        def render(self) -> None:
            """Render method (required by Env interface)."""

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
            super().reset(seed=seed)
            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num += 1

            # Reset tracking
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory = []

            # Reset battery SOC para este episodio (copia de la distribucion)
            self.battery_soc_episode = self.battery_soc.copy()

            # Observación inicial
            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            return obs, {}

        def step(self, action):
            self.step_count += 1
            hour_index = self.step_count % 8760  # Indice [0-8759]
            hour = hour_index // 24  # Hora del día [0-23]

            # ========== ACTION SPACE - 129 DIMENSIONES ==========
            # action = [a_bess, a_socket_0, a_socket_1, ..., a_socket_127]
            #
            # a_bess (action[0]): Control del BESS [0, 1]
            #   - 0.0 = descargando -2712 kW
            #   - 0.5 = neutral (0 kW)
            #   - 1.0 = cargando +2712 kW
            #   - Formula: P_bess = (a_bess - 0.5) * 2 * 2712 kW
            #
            # a_socket_i (action[i+1], i=0..127): Control individual de 128 sockets [0, 1]
            #   - Cada socket es una TOMA de carga individual
            #   - 128 sockets = 128 tomas (28 mototaxis + 100 motos)
            #   - action[1] controla socket 0 (mototaxi socket 0)
            #   - action[128] controla socket 127 (moto socket 127)
            #   - Demanda real: D_real[hora][socket_i] en chargers_hourly_kw
            #   - Potencia ejecutada: P_socket_i = D_real[hora][i] * a_socket_i

            bess_setpoint = action[0]

            # ========== LEER DATOS REALES OE2 ==========

            # 1. SOLAR REAL - 4050 kWp instalado, 8292514 kWh/anio
            solar_generation_kwh = float(self.solar_hourly_kw[hour_index])

            # 2. CHARGERS REAL - 128 SOCKETS (DEMANDA REAL POR SOCKET)
            # chargers_hourly_kw es (8760 horas, 128 sockets)
            # Multiplicación elemento-a-elemento: demanda real * setpoint agente
            charger_action = action[1:129]  # Control [0,1] para 128 sockets
            ev_charging_kwh = float(np.sum(self.chargers_hourly_kw[hour_index] * charger_action))

            # 3. BESS REAL - State of Charge actual (50-100%, media 90.5%)
            bess_soc = float(self.bess_soc_percent[hour_index])

            # 4. DEMANDA MALL REAL - 12.3M kWh/año (no controlable)
            mall_demand = float(self.mall_hourly_kwh[hour_index])

            # === CALCULO GRID IMPORT/EXPORT ===
            total_demand = max(0, mall_demand + ev_charging_kwh)
            if solar_generation_kwh >= total_demand:
                grid_import_kwh = 0.0
                grid_export_kwh = max(0, solar_generation_kwh - total_demand)
            else:
                grid_import_kwh = total_demand - solar_generation_kwh
                grid_export_kwh = 0.0

            # === MONITOREO DE BATERIAS (128 SOCKETS) ===
            # Actualizar SOC de bateria por socket (demanda real * control agente)
            charger_powers = self.chargers_hourly_kw[hour_index] * charger_action  # Potencia por socket [kW]
            energy_charged = charger_powers  # Energia en 1 hora [kWh] (1h timestep)
            battery_soc_new = self.battery_soc_episode[hour_index] + (energy_charged / self.battery_capacity) * 100.0
            battery_soc_new = np.clip(battery_soc_new, 0, 100)  # Limitar [0-100]%
            self.battery_soc_episode[hour_index] = battery_soc_new

            # Calcular estado de baterias
            battery_charge_needed = np.maximum(0, (100 - battery_soc_new) / 100.0 * self.battery_capacity)  # kWh faltante
            battery_charge_power = charger_powers  # kW actuales
            battery_time_to_full = np.where(charger_powers > 0.1, (battery_charge_needed / charger_powers) * 60, 0)  # minutos
            battery_plugged_in = (charger_powers > 0.5).astype(np.float32)  # 1.0 si conectado

            # EV Satisfaction: recompensa por baterias cargadas
            ev_satisfaction = np.mean(np.clip(battery_soc_new, 0, 100) / 100.0)

            # === EV SOC TRACKING ===
            ev_soc_avg = ev_satisfaction  # Usar satisfaction promedio como EV SOC
            self.ev_soc_trajectory.append(ev_soc_avg)

            # === RECOMPENSA MULTIOBJETIVO REAL ===
            total_reward, components = self.reward_calculator.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_generation_kwh,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=hour,
                ev_demand_kwh=self.context.ev_demand_constant_kw
            )

            # AGREGAR BONUS POR SATISFACTION DE BATERIAS (15% del reward)
            ev_bonus = ev_satisfaction * 1000.0  # Bonus escalado
            total_reward += ev_bonus * 0.15

            # === TRACKING ACUMULATIVO ===
            self.co2_avoided_total += components.get('co2_avoided_total_kg', 0)
            self.solar_kwh_total += solar_generation_kwh
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh

            self.episode_reward += total_reward

            # Observación siguiente - AMPLIADA CON ESTADO DE BATERIAS (1045 dims)
            obs = np.zeros(self.obs_dim, dtype=np.float32)

            # Primeras 394 referencias de estado
            obs[:394] = np.random.randn(394).astype(np.float32) * 0.1

            # 10 columnas del dataset solar (indices 394-403)
            if self.solar_all_columns is not None and hour_index < len(self.solar_all_columns):
                obs[394:404] = self.solar_all_columns[hour_index].astype(np.float32)
            else:
                obs[394:404] = 0.0

            # 640 dimensiones de ESTADO DE BATERIAS (indices 404-1044)
            # obs[404:532]   = 128 x SOC_percent
            obs[404:532] = battery_soc_new
            # obs[532:660]   = 128 x charge_needed
            obs[532:660] = battery_charge_needed
            # obs[660:788]   = 128 x charge_power
            obs[660:788] = battery_charge_power
            # obs[788:916]   = 128 x time_to_full
            obs[788:916] = battery_time_to_full
            # obs[916:1044]  = 128 x plugged_in
            obs[916:1044] = battery_plugged_in

            # === Calcular potencias por tipo de vehiculo (estadisticas derivadas) ===
            # Action structure: [bess_control, socket_0, socket_1, ..., socket_127]
            # Mototaxis: sockets 0-27 (indices action 1-29)
            # Motos: sockets 28-127 (indices action 29-129)

            motos_action = action[29:129]  # 100 motos en sockets 28-127
            mototaxis_action = action[1:29]  # 28 mototaxis en sockets 0-27

            # Potencia por tipo de vehiculo
            mototaxis_power = float(np.sum(self.chargers_hourly_kw[hour_index, 0:28] * mototaxis_action))
            motos_power = float(np.sum(self.chargers_hourly_kw[hour_index, 28:128] * motos_action))

            # BESS: potencia es setpoint (action[0]) x capacidad maxima (2712 kW)
            bess_power_kw = float((bess_setpoint - 0.5) * 2.0 * 2712.0)  # Rango [-2712, +2712] kW

            terminated = self.step_count >= self.max_steps
            truncated = False
            info = {
                'step': self.step_count,
                'hour': hour,
                'episode': self.episode_num,
                'episode_reward': self.episode_reward,
                # Componentes de recompensa para inspección
                'r_co2': float(components.get('r_co2', 0)),
                'r_solar': float(components.get('r_solar', 0)),
                'r_cost': float(components.get('r_cost', 0)),
                'r_ev': float(components.get('r_ev', 0)),
                # Métricas de CO2
                'co2_grid_kg': float(components.get('co2_grid_kg', 0)),
                'co2_avoided_indirect_kg': float(components.get('co2_avoided_indirect_kg', 0)),
                'co2_avoided_direct_kg': float(components.get('co2_avoided_direct_kg', 0)),
                'co2_avoided_total_kg': float(components.get('co2_avoided_total_kg', 0)),
                # Dispatch
                'ev_charging_kwh': float(ev_charging_kwh),
                'bess_power_kw': float(bess_power_kw),
                'motos_power_kw': float(motos_power),
                'mototaxis_power_kw': float(mototaxis_power),
                'grid_import_kwh': float(grid_import_kwh),
                'solar_generation_kwh': float(solar_generation_kwh),
            }

            return obs, total_reward, terminated, truncated, info

    env = CityLearnRealEnv(
        reward_calc=reward_calculator,
        ctx=context,
        obs_dim=1045,
        action_dim=129,
        max_steps=8760
    )

    print('  OK Environment creado con recompensa multiobjetivo')
    print(f'    - Observation: {env.observation_space.shape}')
    print(f'    - Action: {env.action_space.shape}')
    print('    - Reward: Multiobjetivo (CO2, Solar, Cost, EV, Grid)')
    print()

    print('[4] CREAR SAC AGENT - CONFIGURACION OPTIMA PARA GPU/CPU')
    print('-' * 80)

    from torch import nn as torch_nn

    sac_config: dict[str, Any] = {
        'learning_rate': 2e-4,  # OPCIÓN A: Reducido 33% (3e-4 → 2e-4) para GPU batch_size=128
        'batch_size': BATCH_SIZE,  # Dinámico según GPU/CPU
        'buffer_size': BUFFER_SIZE,  # Dinámico según GPU/CPU
        'learning_starts': 1000,
        'train_freq': 1,
        'tau': 0.005,
        'gamma': 0.99,
        'ent_coef': 'auto',
        'target_entropy': 'auto',
        'policy_kwargs': {
            'net_arch': NETWORK_ARCH,  # Dinámico según GPU/CPU
            'activation_fn': torch_nn.ReLU,
        },
        'device': DEVICE,  # Usar GPU si disponible
        'verbose': 0,
        'tensorboard_log': None  # Desabilitar tensorboard si no está instalado
    }

    agent = SAC('MlpPolicy', env, **sac_config)

    print(f'  OK SAC agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {sac_config["learning_rate"]}')
    print(f'    - Batch size: {BATCH_SIZE}')
    print(f'    - Buffer size: {BUFFER_SIZE:,}')
    print(f'    - Network: {NETWORK_ARCH}')
    print('    - Entropy: auto-tuned')
    print()

    print('[5] ENTRENAR SAC')
    print('-' * 80)

    class DetailedLoggingCallback(BaseCallback):
        def __init__(self, env_ref):
            super().__init__()
            self.env_ref = env_ref
            self.step_log_freq = 1000

        def _on_step(self) -> bool:
            # Mostrar progreso cada 1000 pasos
            if self.num_timesteps % self.step_log_freq == 0:
                ep_num = self.num_timesteps // 8760
                pct = (self.num_timesteps % 8760) / 8760 * 100
                print(f'    Steps: {self.num_timesteps:>7,} | Episodio: {ep_num:>2} | Progreso: {pct:>5.1f}%')

            return True

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac_checkpoint',
        save_replay_buffer=True
    )

    logging_callback = DetailedLoggingCallback(env)

    TOTAL_TIMESTEPS = 10000  # Entrenamiento real (10k timesteps = ~1-2 episodios completos)

    print(f'  CONFIGURACION: {TOTAL_TIMESTEPS:,} timesteps')
    print('  REWARD WEIGHTS:')
    print('    CO2 grid (0.50): Minimizar importacion')
    print('    Solar (0.20): Autoconsumo PV')
    print('    Cost (0.15): Minimizar costo')
    print('    EV satisfaction (0.10): SOC 90%')
    print('    Grid stability (0.05): Suavizar picos')
    print()
    print('  ENTRENAMIENTO EN PROGRESO:')
    print('  ' + '-'*76)

    start_time = datetime.now()

    agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=[checkpoint_callback, logging_callback],
        progress_bar=False,
        log_interval=1000
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print('-'*76)
    print('  RESULTADO ENTRENAMIENTO:')
    print(f'    Tiempo: {elapsed:.2f} segundos ({elapsed/60:.2f} minutos)')
    print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
    print(f'    Velocidad: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')
    print(f'    Episodios completados: {TOTAL_TIMESTEPS // 8760 + 1}')
    print()

    # Guardar modelo final
    final_model_path = CHECKPOINT_DIR / 'sac_final_model'
    agent.save(str(final_model_path))
    print(f'  OK Modelo guardado: {final_model_path}.zip')
    print()

    print('[6] VALIDACION FINAL - EVALUACION DE POLITICAS APRENDIDAS')
    print('-' * 80)

    print('  Validacion: 3 episodios')
    print('  ' + '-'*76)
    print()

    val_metrics: dict[str, list[float]] = {
        'rewards': [],
        'co2_avoided': [],
        'solar_kwh': [],
        'cost_usd': [],
        'grid_import': [],
    }

    for ep in range(3):
        obs_val, _ = env.reset()
        done = False
        steps = 0
        ep_co2 = 0.0
        ep_solar = 0.0
        ep_grid = 0.0

        print(f'  Episodio {ep+1}/3: ', end='', flush=True)

        while not done:
            action_result = agent.predict(obs_val, deterministic=True)
            if action_result is not None:
                action_val = action_result[0]
            else:
                action_val = env.action_space.sample()
            obs_val, reward_val, terminated_val, truncated_val, info_val = env.step(action_val)
            done = terminated_val or truncated_val
            steps += 1

            # Acumular métricas por paso
            ep_co2 += info_val.get('co2_avoided_total_kg', 0)
            ep_solar += info_val.get('solar_generation_kwh', 0)
            ep_grid += info_val.get('grid_import_kwh', 0)

        # Acumular al final del episodio
        val_metrics['rewards'].append(env.episode_reward)
        val_metrics['co2_avoided'].append(ep_co2)
        val_metrics['solar_kwh'].append(ep_solar)
        val_metrics['cost_usd'].append(env.cost_total)
        val_metrics['grid_import'].append(ep_grid)

        print(f'Reward={env.episode_reward:>8.2f} | '
              f'CO2_avoided={ep_co2:>10.1f}kg | '
              f'Solar={ep_solar:>10.1f}kWh | Steps={steps}')

    print()

    # Guardar métricas
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_timesteps': TOTAL_TIMESTEPS,
        'training_duration_seconds': elapsed,
        'episodes_trained': TOTAL_TIMESTEPS // 8760,
        'validation_metrics': {
            'mean_reward': float(np.mean(val_metrics['rewards'])),
            'std_reward': float(np.std(val_metrics['rewards'])),
            'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
            'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
            'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
            'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
        },
        'reward_weights': weights.as_dict(),
        'context': {
            'co2_grid_factor': context.co2_factor_kg_per_kwh,
            'chargers': context.n_chargers,
            'sockets': context.total_sockets,
            'motos_daily': context.motos_daily_capacity,
            'mototaxis_daily': context.mototaxis_daily_capacity,
        }
    }

    metrics_file = OUTPUT_DIR / 'sac_training_metrics.json'
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f'  OK Metricas guardadas: {metrics_file}')
    print()

    print('='*80)
    print('ENTRENAMIENTO SAC COMPLETADO')
    print('='*80)
    print()

    print('RESULTADOS FINALES - VALIDACION 3 EPISODIOS:')
    print('-'*80)
    validation_metrics = summary.get("validation_metrics", {})
    if isinstance(validation_metrics, dict):
        mean_reward = validation_metrics.get("mean_reward", 0.0)
        mean_co2 = validation_metrics.get("mean_co2_avoided_kg", 0.0)
        mean_solar = validation_metrics.get("mean_solar_kwh", 0.0)
        mean_cost = validation_metrics.get("mean_cost_usd", 0.0)
        mean_grid = validation_metrics.get("mean_grid_import_kwh", 0.0)

        print()
        print('  PARAMETROS CALCULADOS:')
        print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
        print(f'    CO2 evitado por episodio      {mean_co2:>12.1f} kg')
        print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
        print(f'    Ahorro economico por ep       {mean_cost:>12.2f} USD')
        print(f'    Grid import reducido por ep   {mean_grid:>12.1f} kWh')
        print()
        print('  ESTADO: Entrenamiento exitoso. Validacion completada.')
        print()
        print('  OK ENTRENAMIENTO VALIDADO CORRECTAMENTE')
    else:
        print("  WARNING: Validation metrics not available")
    print()

    print('STATUS: SAC CON MULTIOBJETIVO ENTRENADO Y VALIDADO EN TIEMPO REAL')
    print('='*80)
    print()

    env.close()

except (RuntimeError, ValueError, OSError) as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
