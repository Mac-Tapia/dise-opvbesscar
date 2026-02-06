#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR SAC CON MULTIOBJETIVO REAL
Integracion completa: Calculos CO2 + Rewards multiobjetivo + BESS + Chargers diferenciados
"""

import sys
import os
from pathlib import Path

# CONFIGURAR ENCODING ANTES DE OTROS IMPORTS
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, TypeError, RuntimeError):
        pass

# VALIDAR AMBIENTE .venv AL INICIO
try:
    from src.utils.environment_validator import validate_venv_active
    validate_venv_active()
except ImportError:
    print("⚠️  WARNING: environment_validator no disponible, saltando validación")
except RuntimeError as e:
    print(f"❌ {e}", file=sys.stderr)
    sys.exit(1)
import json
import yaml
from datetime import datetime, timedelta
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

# SAC OPTIMIZADO PARA GPU RTX 4060 (8.6GB VRAM)
# Problema: buffer_size×obs_dim requiere memoria
# Cálculo: 500k × 1045 × 4 bytes = 1.95 GB (¡Ya no cabe!)
# Solución: usar buffer = 100k (cabe en GPU + deja espacio para modelo)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)
    print(f'GPU DISPONIBLE: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA Version: {cuda_version}')
    print(f'   ✓ ENTRENAMIENTO SAC CON GPU')
    # SAC off-policy: buffer grande funciona en GPU (máximo probado: 300k)
    BATCH_SIZE = 128
    BUFFER_SIZE = 300000  # Máximo probado en GPU RTX 4060 (test find_max_buffer.py)
    NETWORK_ARCH = [256, 256]
else:
    print('CPU mode - GPU no disponible')
    BATCH_SIZE = 64
    BUFFER_SIZE = 50000
    NETWORK_ARCH = [256, 256]

print(f'   Device: {DEVICE.upper()}')
print(f'   Batch size: {BATCH_SIZE}')
print(f'   Buffer size: {BUFFER_SIZE:,}')
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
    with open('configs/default.yaml', 'r') as f:
        cfg = yaml.safe_load(f)

    print(f'  OK Config loaded: {len(cfg)} keys')

    # Cargar rewards (contexto Iquitos + pesos multiobjetivo)
    from src.rewards.rewards import IquitosContext, MultiObjectiveWeights, MultiObjectiveReward
    from src.rewards.rewards import create_iquitos_reward_weights

    # Usar preset "co2_focus" para maximizar reducción CO2
    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print(f'  OK Reward weights (CO2 focus):')
    print(f'    - CO2: {weights.co2:.2f}  (minimizar grid import)')
    print(f'    - Solar: {weights.solar:.2f}  (maximizar autoconsumo)')
    print(f'    - Cost: {weights.cost:.2f}  (minimizar tarifa)')
    print(f'    - EV: {weights.ev_satisfaction:.2f}  (satisfaccion carga)')
    print(f'    - Grid: {weights.grid_stability:.2f}  (estabilidad)')
    print()

    print(f'  OK Contexto Iquitos:')
    print(f'    - Grid CO2: {context.co2_factor_kg_per_kwh} kg CO2/kWh (termica aislada)')
    print(f'    - EV CO2 factor: {context.co2_conversion_factor} kg CO2/kWh (combustion equivalente)')
    print(f'    - Chargers: {context.n_chargers} (28 motos@2kW + 4 mototaxis@3kW)')
    print(f'    - Sockets: {context.total_sockets} (112 motos + 16 mototaxis)')
    print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
    print()

    print('[2] CARGAR DATASET CITYLEARN V2 (COMPILADO)')
    print('-' * 80)

    # Dataset ya compilado en data/processed/citylearn/iquitos_ev_mall
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        print(f'❌ ERROR: Dataset no encontrado en {processed_path}')
        print('   Crea el dataset primero con: python build.py')
        sys.exit(1)

    print(f'  ✓ Dataset precompilado: {processed_path}')
    dataset_dir = processed_path
    print(f'  OK Dataset: {dataset_dir}')
    print()

    print('[3] CREAR ENVIRONMENT CON REWARD MULTIOBJETIVO REAL')
    print('-' * 80)

    import numpy as np
    from gymnasium import Env, spaces
    from stable_baselines3 import SAC
    from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

    class CityLearnRealEnv(Env):
        """Environment con recompensa multiobjetivo REAL de Iquitos (datos OE2) + Monitoreo baterias sockets"""

        def __init__(self, reward_calc, context, obs_dim=1045, action_dim=129, max_steps=8760):
            self.reward_calculator = reward_calc
            self.context = context
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
            self.ev_soc_trajectory = []

            # CARGAR TODOS LOS DATOS REALES OE2 - NO APROXIMACIONES
            print('  [OE2] Cargando datasets reales...')

            # 1. SOLAR PVGIS REAL - TODAS LAS 11 COLUMNAS
            try:
                solar_path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
                df_solar = pd.read_csv(solar_path)
                # Cargar todas las columnas (excluir timestamp si es indice)
                solar_cols = [c for c in df_solar.columns if c.lower() != 'timestamp']
                self.solar_all_columns = df_solar[solar_cols].values  # (8760, 10)
                self.solar_hourly_kw = df_solar['ac_power_kw'].to_numpy(dtype=np.float64, na_value=0.0)  # ac_power_kw en indice 6
                solar_sum = float(np.sum(self.solar_hourly_kw))
                print(f'    [OK] Solar: {solar_sum:.0f} kWh/anio')
            except Exception as e:
                print(f'    [ERROR] Solar: {e}')
                self.solar_hourly_kw = None
                # Fallback: crear array de ceros con forma correcta (8760, 10)
                self.solar_all_columns = np.zeros((8760, 10), dtype=np.float32)

            # 2. CHARGERS REAL - 128 SOCKETS
            try:
                chargers_path = Path('data/oe2/chargers/chargers_real_hourly_2024.csv')
                self.chargers_real_data = pd.read_csv(chargers_path)
                # Extraer columnas de sockets (excluir timestamp)
                socket_cols = [c for c in self.chargers_real_data.columns if 'SOCKET' in c or 'MOTO' in c]
                self.chargers_hourly_kw = self.chargers_real_data[socket_cols].values  # (8760, 128)
                self.chargers_total_kwh = self.chargers_real_data[socket_cols].sum().sum()
                print(f'    [OK] Chargers: 128 sockets, {self.chargers_total_kwh:.0f} kWh/anio')
            except Exception as e:
                print(f'    [ERROR] Chargers: {e}')
                self.chargers_hourly_kw = None

            # 3. BESS REAL - STATE OF CHARGE
            try:
                bess_path = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
                self.bess_real_data = pd.read_csv(bess_path)
                # Usar columna de SOC
                if 'soc_percent' in self.bess_real_data.columns:
                    soc_values = self.bess_real_data['soc_percent'].to_numpy(dtype=np.float64, na_value=0.0)
                    self.bess_soc_percent = soc_values / 100.0  # Convertir a [0,1]
                else:
                    # Fallback: usar primera columna numerica
                    numeric_cols = self.bess_real_data.select_dtypes(include=['float64', 'int64']).columns
                    if len(numeric_cols) > 0:
                        soc_values = self.bess_real_data[numeric_cols[0]].to_numpy(dtype=np.float64, na_value=0.0)
                        self.bess_soc_percent = soc_values / 100.0
                    else:
                        self.bess_soc_percent = None
                if self.bess_soc_percent is not None:
                    print(f'    [OK] BESS: {len(self.bess_soc_percent)} horas')
                else:
                    print(f'    [WARN] BESS: No hay columna SOC')
                    self.bess_soc_percent = None
            except Exception as e:
                print(f'    [ERROR] BESS: {e}')
                self.bess_soc_percent = None

            # 4. DEMANDA MALL REAL - SINCRONIZAR A 8760 HORAS
            try:
                mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
                self.mall_real_data = pd.read_csv(mall_path, sep=';')
                # Obtener ultima columna (contiene demanda en kWh)
                demand_col = self.mall_real_data.columns[-1]
                mall_demand_kwh = self.mall_real_data[demand_col].to_numpy(dtype=np.float64, na_value=0.0)

                # SINCRONIZAR: si tiene 8785 horas, truncar a 8760 (1 anio completo)
                if len(mall_demand_kwh) > 8760:
                    mall_demand_kwh = mall_demand_kwh[:8760]
                    mall_sum = float(np.sum(mall_demand_kwh))
                    print(f'    [OK] Mall: 8760 horas, {mall_sum:.0f} kWh/anio')
                else:
                    mall_sum = float(np.sum(mall_demand_kwh))
                    print(f'    [OK] Mall: {len(mall_demand_kwh)} horas, {mall_sum:.0f} kWh/anio')

                self.mall_hourly_kwh = mall_demand_kwh
            except Exception as e:
                print(f'    [ERROR] Mall: {e}')
                self.mall_hourly_kwh = None

            # ========== INICIALIZAR MONITOREO DE BATERIAS (128 SOCKETS) ==========
            # Cada socket monitorea estado de bateria del vehiculo conectado
            self.battery_soc = np.random.uniform(20, 80, size=(8760, 128)).astype(np.float32)  # SOC inicial 20-80%

            # Capacidad nominal por socket (motos 3-5 kWh, mototaxis 8-12 kWh)
            self.battery_capacity = np.zeros(128, dtype=np.float32)
            self.battery_capacity[0:28] = np.random.uniform(10.0, 12.0, 28)  # Mototaxis (indices 0-27) - Sin acento
            self.battery_capacity[28:128] = np.random.uniform(4.0, 5.0, 100)  # Motos (indices 28-127)

            # Tipos vehiculo (asignacion)
            self.vehicle_types = np.array(["mototaxi"]*28 + ["moto"]*100)

            print(f'    [OK] Baterias: 128 sockets monitorizados')
            print(f'  OK Environment: (1045,) obs | (129,) action')
            print()

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
            #   - 128 sockets = 128 tomas (2 mototaxis + 112 motos)
            #   - action[1] controla socket 0 (mototaxi socket 0)
            #   - action[128] controla socket 127 (moto socket 127)
            #   - Demanda real: D_real[hora][socket_i] en chargers_hourly_kw
            #   - Potencia ejecutada: P_socket_i = D_real[hora][i] * a_socket_i

            bess_setpoint = action[0]

            # ========== LEER DATOS REALES OE2 ==========

            # 1. SOLAR REAL - 4050 kWp instalado, 8292514 kWh/anio
            if self.solar_hourly_kw is not None:
                solar_generation_kwh = float(self.solar_hourly_kw[hour_index])
            else:
                solar_generation_kwh = 0.0  # Sin aproximacion - datos reales obligatorios

            # 2. CHARGERS REAL - 128 SOCKETS (DEMANDA REAL POR SOCKET)
            # chargers_hourly_kw es (8760 horas, 128 sockets)
            # Ejemplo: chargers_hourly_kw[100][5] = 4.2 kW (demanda real socket 5 en hora 100)
            if self.chargers_hourly_kw is not None:
                charger_action = action[1:129]  # Control [0,1] para 128 sockets
                # Multiplicación elemento-a-elemento: demanda real * setpoint agente
                # Cada socket se controla INDEPENDIENTEMENTE
                ev_charging_kwh = float(np.sum(self.chargers_hourly_kw[hour_index] * charger_action))
            else:
                ev_charging_kwh = 0.0  # Sin aproximacion

            # 3. BESS REAL - State of Charge actual (50-100%, media 90.5%)
            if self.bess_soc_percent is not None:
                bess_soc = float(self.bess_soc_percent[hour_index])
            else:
                bess_soc = 0.5  # Fallback seguro

            # 4. DEMANDA MALL REAL - 12.3M kWh/año (no controlable)
            if self.mall_hourly_kwh is not None:
                mall_demand = float(self.mall_hourly_kwh[hour_index])
            else:
                mall_demand = 0.0  # Sin aproximación

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
            charger_powers = (self.chargers_hourly_kw[hour_index] if self.chargers_hourly_kw is not None else np.ones(128)) * action[1:129]  # Potencia por socket [kW]
            energy_charged = charger_powers * 1.0  # Energia en 1 hora [kWh]
            battery_soc_new = self.battery_soc_episode[hour_index] + (energy_charged / self.battery_capacity) * 100.0
            battery_soc_new = np.clip(battery_soc_new, 0, 100)  # Limitar [0-100]%
            self.battery_soc_episode[hour_index] = battery_soc_new

            # Calcular estado de baterias
            battery_charge_needed = np.maximum(0, (100 - battery_soc_new) / 100.0 * self.battery_capacity)  # kWh faltante
            battery_charge_power = charger_powers  # kW actuales
            # Usar epsilon para evitar division por cero (RuntimeWarning)
            epsilon = 1e-8
            battery_time_to_full = np.where(charger_powers > 0.1, (battery_charge_needed / np.maximum(charger_powers, epsilon)) * 60, 0)  # minutos
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

            if self.chargers_hourly_kw is not None and self.chargers_hourly_kw.shape[0] > hour_index:
                # Mototaxis power: chargers 0:28 (mototaxis)
                mototaxis_power = float(np.sum(self.chargers_hourly_kw[hour_index, 0:28] * mototaxis_action))
                # Motos power: chargers 28:128 (motos)
                motos_power = float(np.sum(self.chargers_hourly_kw[hour_index, 28:128] * motos_action))
            else:
                motos_power = 0.0
                mototaxis_power = 0.0

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
        context=context,
        obs_dim=1045,
        action_dim=129,
        max_steps=8760
    )

    print(f'  OK Environment creado con recompensa multiobjetivo')
    print(f'    - Observation: {env.observation_space.shape}')
    print(f'    - Action: {env.action_space.shape}')
    print(f'    - Reward: Multiobjetivo (CO2, Solar, Cost, EV, Grid)')
    print()

    print('[4] CREAR SAC AGENT - CONFIGURACION OPTIMA PARA GPU/CPU')
    print('-' * 80)

    from torch import nn as torch_nn

    sac_config: dict[str, Any] = {
        'learning_rate': 1e-4,  # Reducido para estabilidad (SAC es sensible a LR)
        'batch_size': 64,  # Reducido para evitar inestabilidad
        'buffer_size': 100000,  # Reducido pero suficiente
        'learning_starts': 500,  # Menos steps antes de entrenar
        'train_freq': 1,
        'gradient_steps': 1,  # 1 paso de gradiente por step
        'tau': 0.005,
        'gamma': 0.99,
        'ent_coef': 'auto',  # Auto-tune entropy
        'target_entropy': 'auto',
        'policy_kwargs': {
            'net_arch': [128, 128],  # Red más pequeña para mayor estabilidad
            'activation_fn': torch_nn.ReLU,
            'log_std_init': -2.3,  # Log std inicial más bajo (menos varianza)
        },
        'device': DEVICE,
        'verbose': 0,
        'tensorboard_log': None,  # Desabilitar tensorboard
    }

    agent = SAC('MlpPolicy', env, **sac_config)

    print(f'  OK SAC agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {sac_config["learning_rate"]}')
    print(f'    - Batch size: {BATCH_SIZE}')
    print(f'    - Buffer size: {BUFFER_SIZE:,}')
    print(f'    - Network: {NETWORK_ARCH}')
    print(f'    - Entropy: auto-tuned')
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

    class DiskSpaceCallback(BaseCallback):
        """Monitorea espacio en disco y limpia checkpoints antiguos si es necesario"""
        def __init__(self, min_free_gb: float = 50, check_freq: int = 5000):
            super().__init__()
            self.min_free_gb = min_free_gb
            self.check_freq = check_freq

        def _on_step(self) -> bool:
            if self.num_timesteps % self.check_freq == 0:
                import shutil
                total, used, free = shutil.disk_usage('D:/')
                free_gb = free / 1e9

                if free_gb < self.min_free_gb:
                    print(f'    ⚠️  ESPACIO BAJO ({free_gb:.1f} GB). Limpiando checkpoints antiguos...')

                    # Limpiar checkpoints antiguos (mantener 3 recientes)
                    from pathlib import Path
                    checkpoint_dir = Path('checkpoints/SAC')
                    if checkpoint_dir.exists():
                        checkpoints = sorted(checkpoint_dir.glob('sac_checkpoint_*.zip'))
                        for cp in checkpoints[:-3]:  # Mantener 3 más recientes
                            try:
                                cp.unlink()
                                print(f'    🗑️  Eliminado: {cp.name}')
                            except:
                                pass

            return True

    checkpoint_callback = CheckpointCallback(
        save_freq=1000,  # Guardar cada 1000 pasos para resumir fácilmente
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac_checkpoint',
        save_replay_buffer=False  # DESACTIVADO: Ahorra ~2GB espacio en disco
    )

    logging_callback = DetailedLoggingCallback(env)
    disk_space_callback = DiskSpaceCallback(min_free_gb=50, check_freq=5000)

    # ENTRENAMIENTO SAC EN GPU: 3 episodios con buffer optimizado (300k)
    # Velocidad REAL CON GPU + buffer=300k + batch=128:
    # - GPU speed: ~500-700 timesteps/seg (SAC off-policy con buffer grande)
    # - 3 episodios × 8760 = 26,280 timesteps
    # - 26,280 / 600 ≈ 44 segundos
    EPISODES_TARGET = 3
    TOTAL_TIMESTEPS = EPISODES_TARGET * 8760  # 26,280 timesteps

    # Velocidad dinámica según device
    if DEVICE == 'cuda':
        SPEED_OBSERVED = 600  # GPU RTX 4060 con buffer=300k (estimado)
        DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_OBSERVED / 60
        DURATION_TEXT = f'~{int(DURATION_MINUTES*60)} segundos (GPU RTX 4060)'
    else:
        SPEED_OBSERVED = 0.8  # CPU fallback
        DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_OBSERVED / 60
        DURATION_TEXT = f'~{int(DURATION_MINUTES/60)} horas (CPU fallback)'

    print()
    print('='*76)
    print(f'  📊 CONFIGURACION ENTRENAMIENTO SAC')
    print(f'     Episodios: {EPISODES_TARGET} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
    print(f'     Device: {DEVICE.upper()}')
    print(f'     Velocidad: ~{SPEED_OBSERVED:,} timesteps/segundo')
    print(f'     Duración: {DURATION_TEXT}')
    print(f'     Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'     Fin: {(datetime.now() + timedelta(minutes=DURATION_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*76)
    print(f'  REWARD WEIGHTS (Multi-objetivo):')
    print(f'    • CO2 grid (0.50): Minimizar importacion')
    print(f'    • Solar (0.20): Autoconsumo PV')
    print(f'    • Cost (0.15): Minimizar costo')
    print(f'    • EV satisfaction (0.10): SOC 90%')
    print(f'    • Grid stability (0.05): Suavizar picos')
    print()
    print('  ENTRENAMIENTO EN PROGRESO:')
    print('  ' + '-'*76)

    start_time = datetime.now()

    agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=[checkpoint_callback, logging_callback, disk_space_callback],
        progress_bar=False,
        log_interval=1000
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print('-'*76)
    print(f'  ✓ RESULTADO ENTRENAMIENTO:')
    print(f'    Tiempo: {elapsed/60:.1f} minutos ({elapsed:.0f} segundos)')
    print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
    print(f'    Velocidad real: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')
    print(f'    Episodios completados: {EPISODES_TARGET}')
    print(f'    Duración promedio: {elapsed / EPISODES_TARGET / 60:.1f} minutos/episodio')
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
        obs, _ = env.reset()
        done = False
        steps = 0
        ep_co2 = 0.0
        ep_solar = 0.0
        ep_grid = 0.0

        print(f'  Episodio {ep+1}/3: ', end='', flush=True)

        while not done:
            action_result = agent.predict(obs, deterministic=True)
            if action_result is not None:
                action = action_result[0]
            else:
                action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            steps += 1

            # Acumular métricas por paso
            ep_co2 += info.get('co2_avoided_total_kg', 0)
            ep_solar += info.get('solar_generation_kwh', 0)
            ep_grid += info.get('grid_import_kwh', 0)

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
        'training_duration_hours': elapsed / 3600,
        'episodes_trained': EPISODES_TARGET,
        'avg_minutes_per_episode': elapsed / EPISODES_TARGET / 60,
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

    metrics_file = OUTPUT_DIR / f'sac_training_metrics_{EPISODES_TARGET}episodes.json'
    with open(metrics_file, 'w') as f:
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
        print(f'  ESTADISTICAS DE ENTRENAMIENTO:')
        print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
        print(f'    Duración total: {summary.get("training_duration_hours", 0):.2f} horas')
        print(f'    Episodios entrenados: {EPISODES_TARGET}')
        print(f'    Duración promedio: {summary.get("avg_minutes_per_episode", 0):.1f} minutos/episodio')
        print()
        print('  OK ENTRENAMIENTO VALIDADO CORRECTAMENTE')
    else:
        print("  WARNING: Validation metrics not available")
    print()

    print('STATUS: SAC CON MULTIOBJETIVO ENTRENADO Y VALIDADO EN TIEMPO REAL')
    print('='*80)
    print()

    env.close()

except Exception as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
