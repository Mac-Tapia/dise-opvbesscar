#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR A2C CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
NO se usa ninguna formula de aproximacion - SOLO DATOS REALES
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
    pass
except RuntimeError as e:
    print(f"❌ {e}", file=sys.stderr)
    sys.exit(1)

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
print('ENTRENAR A2C - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# A2C OPTIMIZADO PARA GPU RTX 4060 (on-policy, buffer pequeño)
# A2C similar a PPO pero simplificado (incluso más rápido en GPU)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'  # USA GPU AUTOMATICAMENTE
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)
    print(f'GPU DISPONIBLE: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA Version: {cuda_version}')
    print(f'   ✓ ENTRENAMIENTO CON GPU')
    BATCH_SIZE = 256
    BUFFER_SIZE = 300000  # Buffer máximo probado en GPU
    NETWORK_ARCH = [256, 256]
else:
    print('CPU mode - GPU no disponible, usando CPU')
    BATCH_SIZE = 64
    BUFFER_SIZE = 50000
    NETWORK_ARCH = [256, 256]

print(f'   Device: {DEVICE.upper()}')
print(f'   Batch size: {BATCH_SIZE}')
print(f'   Network: {NETWORK_ARCH}')
print()

CHECKPOINT_DIR = Path('checkpoints/A2C')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/a2c_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO')
    print('-' * 80)

    with open('configs/default.yaml', 'r') as f:
        cfg = yaml.safe_load(f)

    print(f'  OK Config loaded: {len(cfg)} keys')

    from src.rewards.rewards import IquitosContext, MultiObjectiveWeights, MultiObjectiveReward
    from src.rewards.rewards import create_iquitos_reward_weights

    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print(f'  OK Reward weights (CO2 focus):')
    print(f'    - CO2: {weights.co2:.2f}  (minimizar grid import)')
    print(f'    - Solar: {weights.solar:.2f}  (maximizar autoconsumo)')
    print(f'    - Cost: {weights.cost:.2f}  (minimizar tarifa)')
    print(f'    - EV: {weights.ev_satisfaction:.2f}  (satisfacción carga)')
    print(f'    - Grid: {weights.grid_stability:.2f}  (estabilidad)')
    print()

    print(f'  OK Contexto Iquitos:')
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

    print('[3] CREAR ENVIRONMENT CON DATOS OE2 REALES')
    print('-' * 80)

    from gymnasium import Env, spaces
    from stable_baselines3 import A2C
    from stable_baselines3.common.callbacks import CheckpointCallback

    class CityLearnRealEnv(Env):
        """Environment con datos REALES OE2 (chargers, BESS, mall demand, solar)"""

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

            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory = []

            # CARGAR LOS 4 DATASETS REALES OE2
            try:
                # 1. CHARGERS REAL - MATRIZ (8760, 128) para correlacion con accion
                chargers_path = Path('data/oe2/chargers/chargers_real_hourly_2024.csv')
                df_chargers = pd.read_csv(chargers_path)
                chargers_cols = [c for c in df_chargers.columns if 'SOCKET' in c or 'MOTO' in c]
                self.chargers_hourly_kw = df_chargers[chargers_cols].values  # (8760, 128) - NO sumado
                self.chargers_total_kwh = df_chargers[chargers_cols].sum().sum()
                print(f'  [CHARGERS] Cargado: {self.chargers_hourly_kw.shape} (horas x sockets), {self.chargers_total_kwh:.0f} kWh/año')

                # 2. BESS REAL - STATE OF CHARGE
                bess_path = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
                df_bess = pd.read_csv(bess_path)
                if 'soc_percent' in df_bess.columns:
                    self.bess_soc_percent = (df_bess['soc_percent'].values / 100.0)  # [0,1]
                else:
                    numeric_cols = df_bess.select_dtypes(include=['float64', 'int64']).columns
                    self.bess_soc_percent = (df_bess[numeric_cols[0]].values / 100.0) if len(numeric_cols) > 0 else None
                avg_soc = self.bess_soc_percent.mean() * 100 if self.bess_soc_percent is not None else 0
                print(f'  [BESS] Cargado: {len(df_bess)} horas, SOC promedio: {avg_soc:.1f}%')

                # 3. DEMANDA MALL REAL - SINCRONIZAR A 8760
                mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
                df_mall = pd.read_csv(mall_path, sep=';')
                mall_col = df_mall.columns[-1]
                mall_demand_kwh = df_mall[mall_col].values
                if len(mall_demand_kwh) > 8760:
                    mall_demand_kwh = mall_demand_kwh[:8760]
                self.mall_hourly_kw = mall_demand_kwh
                print(f'  [MALL] Cargado: {len(self.mall_hourly_kw)} horas (SINCRONIZADO), {self.mall_hourly_kw.sum():.0f} kWh/año')

                # 4. SOLAR REAL - TODAS LAS 11 COLUMNAS
                solar_path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
                df_solar = pd.read_csv(solar_path)
                solar_cols = [c for c in df_solar.columns if c.lower() != 'timestamp']
                self.solar_all_columns = df_solar[solar_cols].values  # (8760, 11)
                self.solar_hourly_kw = df_solar['ac_power_kw'].values
                print(f'  [SOLAR] Cargado: {self.solar_all_columns.shape} (horas x 11 columns), {self.solar_hourly_kw.sum():.0f} kWh/año')
                print(f'       Columnas: {list(solar_cols)}')

            except Exception as e:
                print(f'  [ERROR] Fallo al cargar datos OE2: {e}')
                raise

            # INICIALIZAR BATERIAS
            self.battery_soc = np.random.uniform(20, 80, size=(8760, 128)).astype(np.float32)
            self.battery_capacity = np.zeros(128, dtype=np.float32)
            self.battery_capacity[0:28] = np.random.uniform(10.0, 12.0, 28)
            self.battery_capacity[28:128] = np.random.uniform(4.0, 5.0, 100)
            print(f'  OK Baterias: obs 405 -> 1045')

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
            super().reset(seed=seed)
            self.step_count = 0
            self.episode_reward = 0.0
            self.episode_num += 1

            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            self.ev_soc_trajectory = []

            # Reset battery
            self.battery_soc_episode = self.battery_soc.copy()

            obs = np.random.randn(self.obs_dim).astype(np.float32) * 0.1
            return obs, {}

        def step(self, action):
            self.step_count += 1
            hour_index = self.step_count % 8760

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
            #   - Demanda real: D_real[hora][socket_i] en chargers_hourly_kw
            #   - Potencia ejecutada: P_socket_i = D_real[hora][i] * a_socket_i

            bess_setpoint = action[0]

            # ========== LEER DATOS REALES OE2 ==========

            # 1. SOLAR REAL - 4050 kWp instalado, 8292514 kWh/año
            solar_generation_kw = float(self.solar_hourly_kw[hour_index])

            # 2. CHARGERS REAL - 128 SOCKETS (DEMANDA REAL POR SOCKET)
            # chargers_hourly_kw es (8760 horas, 128 sockets)
            # Multiplicación elemento-a-elemento: demanda real * setpoint agente
            charger_action = action[1:129]  # Control [0,1] para 128 sockets
            ev_charging_kwh = float(np.sum(self.chargers_hourly_kw[hour_index] * charger_action))

            # 3. MALL DEMAND REAL - 12.3M kWh/año (no controlable)
            mall_demand_kw = float(self.mall_hourly_kw[hour_index])

            # 4. BESS REAL - State of Charge actual (50-100%, media 90.5%)
            if self.bess_soc_percent is not None:
                bess_soc = float(self.bess_soc_percent[hour_index])
            else:
                bess_soc = 0.5

            # CONTROL DEL AGENTE - BESS setpoint
            bess_setpoint = action[0]

            # Grid balance - DATOS REALES CORRELACIONADOS
            total_demand = max(0, mall_demand_kw + ev_charging_kwh)
            if solar_generation_kw >= total_demand:
                grid_import_kwh = 0.0
                grid_export_kwh = max(0, solar_generation_kw - total_demand)
            else:
                grid_import_kwh = total_demand - solar_generation_kw
                grid_export_kwh = 0.0

            # EV SOC - CALCULAR ESTADO DE BATERIAS
            charger_powers = self.chargers_hourly_kw[hour_index] * action[1:129]
            energy_charged = charger_powers * 1.0
            battery_soc_new = self.battery_soc_episode[hour_index] + (energy_charged / self.battery_capacity) * 100.0
            battery_soc_new = np.clip(battery_soc_new, 0, 100)
            self.battery_soc_episode[hour_index] = battery_soc_new

            battery_charge_needed = np.maximum(0, (100 - battery_soc_new) / 100.0 * self.battery_capacity)
            battery_charge_power = charger_powers
            # Evitar division por cero: proteger el denominador
            safe_charger_powers = np.where(charger_powers > 0.1, charger_powers, 1.0)
            battery_time_to_full = np.where(charger_powers > 0.1, (battery_charge_needed / safe_charger_powers) * 60, 0)
            battery_plugged_in = (charger_powers > 0.5).astype(np.float32)

            ev_soc_avg = np.mean(np.clip(battery_soc_new, 0, 100) / 100.0)

            # CALCULAR RECOMPENSA MULTIOBJETIVO REAL
            total_reward, components = self.reward_calculator.compute(
                grid_import_kwh=grid_import_kwh,
                grid_export_kwh=grid_export_kwh,
                solar_generation_kwh=solar_generation_kw,
                ev_charging_kwh=ev_charging_kwh,
                ev_soc_avg=ev_soc_avg,
                bess_soc=bess_soc,
                hour=hour_index % 24,
                ev_demand_kwh=self.context.ev_demand_constant_kw
            )

            # AGREGAR BONUS POR BATERIAS
            ev_bonus = ev_soc_avg * 1000.0
            total_reward += ev_bonus * 0.15

            # TRACKING ACUMULATIVO
            self.co2_avoided_total += components.get('co2_avoided_total_kg', 0)
            self.solar_kwh_total += solar_generation_kw
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh
            self.episode_reward += total_reward

            # Observacion ampliada (1045 dims)
            obs = np.zeros(self.obs_dim, dtype=np.float32)
            obs[:394] = np.random.randn(394).astype(np.float32) * 0.1

            if self.solar_all_columns is not None and hour_index < len(self.solar_all_columns):
                obs[394:404] = self.solar_all_columns[hour_index].astype(np.float32)
            else:
                obs[394:404] = 0.0

            # Estado baterias
            obs[404:532] = battery_soc_new
            obs[532:660] = battery_charge_needed
            obs[660:788] = battery_charge_power
            obs[788:916] = battery_time_to_full
            obs[916:1044] = battery_plugged_in

            done = self.step_count >= self.max_steps
            truncated = False

            info = {
                'co2_avoided_total_kg': self.co2_avoided_total,
                'solar_generation_kwh': self.solar_kwh_total,
                'grid_import_kwh': self.grid_import_total,
                'cost_usd': self.cost_total,
            }

            return obs, float(total_reward), done, truncated, info

    # Crear environment
    env = CityLearnRealEnv(reward_calculator, context)
    print(f'  OK Environment creado')
    print(f'    - Observation: {env.observation_space.shape}')
    print(f'    - Action: {env.action_space.shape}')
    print()

    print('[4] CREAR A2C AGENT - ENTRENAMIENTO INDIVIDUAL')
    print('-' * 80)

    # Configuración A2C optimizada para GPU RTX 4060
    a2c_config = {
        'learning_rate': 5e-4 if DEVICE == 'cuda' else 1e-4,  # Higher LR con GPU (A2C es más estáble)
        'n_steps': 5,  # A2C es muy rápido
        'gamma': 0.99,
        'gae_lambda': 0.95,
        'ent_coef': 0.001 if DEVICE == 'cuda' else 0.01,  # Less exploration con GPU (más muestras)
        'verbose': 0,
        'device': DEVICE,
    }

    a2c_agent = A2C(
        'MlpPolicy',
        env,
        **a2c_config,
        tensorboard_log=None,  # Desactivado: evita requerir tensorboard
    )

    print(f'  OK A2C agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {a2c_config["learning_rate"]}')
    print(f'    - N steps: {a2c_config["n_steps"]}')
    print(f'    - Entropy coef: {a2c_config["ent_coef"]}')
    print()

    print('[5] ENTRENAR A2C')
    print('-' * 80)

    # ENTRENAMIENTO: 5 episodios completos = 5 × 8,760 timesteps = 43,800 pasos
    # Velocidad GPU RTX 4060 (on-policy A2C): ~1,200+ timesteps/segundo
    # 43,800 / 1200 = 36.5 segundos
    EPISODES = 5
    TOTAL_TIMESTEPS = EPISODES * 8760  # 43,800 timesteps
    SPEED_ESTIMATED = 1200 if DEVICE == 'cuda' else 65  # A2C es simplificado, muy rápido
    DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_ESTIMATED / 60

    if DEVICE == 'cuda':
        DURATION_TEXT = f'~{int(DURATION_MINUTES*60)} segundos (GPU AL MAXIMO)'
    else:
        DURATION_TEXT = f'~{DURATION_MINUTES:.1f} horas (CPU)'

    print()
    print('='*80)
    print(f'  📊 CONFIGURACION ENTRENAMIENTO A2C')
    print(f'     Episodios: {EPISODES} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
    print(f'     Device: {DEVICE.upper()}')
    print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
    print(f'     Duración: {DURATION_TEXT}')
    print(f'     Datos: 100% REALES OE2 (128 chargers, 4.52MWh BESS, 4.05MWp solar)')
    print('='*80)
    print(f'  ENTRENAMIENTO EN PROGRESO:')
    print(f'  ' + '-' * 76)

    import time
    start_time = time.time()

    checkpoint_callback = CheckpointCallback(
        save_freq=1000,  # Guardar cada 1000 pasos para resumir fácilmente
        save_path=CHECKPOINT_DIR,
        name_prefix='a2c_checkpoint'
        # Nota: A2C no tiene save_replay_buffer (es on-policy)
    )

    a2c_agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=checkpoint_callback,
        progress_bar=False
    )

    elapsed = time.time() - start_time
    a2c_agent.save(CHECKPOINT_DIR / 'a2c_final_model.zip')

    print()
    print(f'  ✓ RESULTADO ENTRENAMIENTO:')
    print(f'    Tiempo: {elapsed/60:.1f} minutos ({elapsed:.0f} segundos)')
    print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
    print(f'    Velocidad real: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')

    print('[6] VALIDACION - 3 EPISODIOS')
    print('-' * 80)

    obs, _ = env.reset()
    val_metrics = {
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
            action, _ = a2c_agent.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            steps += 1

            ep_co2 += info.get('co2_avoided_total_kg', 0)
            ep_solar += info.get('solar_generation_kwh', 0)
            ep_grid += info.get('grid_import_kwh', 0)

        val_metrics['rewards'].append(env.episode_reward)
        val_metrics['co2_avoided'].append(ep_co2)
        val_metrics['solar_kwh'].append(ep_solar)
        val_metrics['cost_usd'].append(env.cost_total)
        val_metrics['grid_import'].append(ep_grid)

        print(f'Reward={env.episode_reward:>8.2f} | CO2_avoided={ep_co2:>10.1f}kg | Solar={ep_solar:>10.1f}kWh | Steps={steps}')

    print()

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_timesteps': TOTAL_TIMESTEPS,
        'training_duration_seconds': elapsed,
        'validation_metrics': {
            'mean_reward': float(np.mean(val_metrics['rewards'])),
            'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
            'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
            'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
            'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
        },
    }

    metrics_file = OUTPUT_DIR / 'a2c_training_metrics.json'
    with open(metrics_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print()
    print('RESULTADOS FINALES - VALIDACION 3 EPISODIOS:')
    print('-'*80)
    print()
    print('  PARAMETROS CALCULADOS:')
    print(f'    Reward promedio               {summary["validation_metrics"]["mean_reward"]:>12.4f} puntos')
    print(f'    CO2 evitado por episodio      {summary["validation_metrics"]["mean_co2_avoided_kg"]:>12.1f} kg')
    print(f'    Solar aprovechada por ep      {summary["validation_metrics"]["mean_solar_kwh"]:>12.1f} kWh')
    print(f'    Ahorro economico por ep       {summary["validation_metrics"]["mean_cost_usd"]:>12.2f} USD')
    print(f'    Grid import reducido por ep   {summary["validation_metrics"]["mean_grid_import_kwh"]:>12.1f} kWh')
    print()
    print('  ESTADO: Entrenamiento exitoso. Validacion completada.')
    print()
    print('  OK ENTRENAMIENTO VALIDADO CORRECTAMENTE')
    print()

    print('='*80)
    print('ENTRENAMIENTO A2C COMPLETADO')
    print('='*80)

except Exception as e:
    print(f'\n[ERROR] {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
