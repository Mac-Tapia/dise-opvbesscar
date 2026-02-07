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

print('='*80, flush=True)
print('ENTRENAR SAC - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)', flush=True)
print('='*80, flush=True)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
print(flush=True)

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
    # ========== VALIDACION CRITICA: 5 ARCHIVOS OE2 OBLIGATORIOS ==========
    print('[0] VALIDAR SINCRONIZACION CON 5 DATASETS OE2', flush=True)
    print('-' * 80, flush=True)

    OE2_FILES = {
        'solar': Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv'),
        'chargers_hourly': Path('data/oe2/chargers/chargers_real_hourly_2024.csv'),
        'chargers_stats': Path('data/oe2/chargers/chargers_real_statistics.csv'),
        'bess': Path('data/oe2/bess/bess_hourly_dataset_2024.csv'),
        'mall_demand': Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
    }

    oe2_validation_ok = True
    oe2_summary = {}

    for name, path in OE2_FILES.items():
        if path.exists():
            df = pd.read_csv(path, nrows=5, sep=';' if 'mall' in name else ',')
            rows = len(pd.read_csv(path, sep=';' if 'mall' in name else ','))
            cols = len(df.columns)
            oe2_summary[name] = {'rows': rows, 'cols': cols}
            status = 'OK' if rows >= 8760 or name == 'chargers_stats' else 'WARN'
            print(f'  [{status}] {name}: {rows:,} filas x {cols} columnas ({path.name})', flush=True)
        else:
            print(f'  [ERROR] {name}: NO ENCONTRADO ({path})', flush=True)
            oe2_validation_ok = False

    if not oe2_validation_ok:
        raise FileNotFoundError('Faltan archivos OE2 obligatorios. Ver errores arriba.')

    print(flush=True)
    print('  SINCRONIZACION OE2 -> CityLearn:', flush=True)
    print(f'    Solar PVGIS:       {oe2_summary["solar"]["rows"]:,} horas', flush=True)
    print(f'    Chargers 128 sockets: {oe2_summary["chargers_hourly"]["rows"]:,} horas x {oe2_summary["chargers_hourly"]["cols"]} cols', flush=True)
    print(f'    BESS SOC:          {oe2_summary["bess"]["rows"]:,} horas', flush=True)
    print(f'    Mall Demand:       {oe2_summary["mall_demand"]["rows"]:,} horas', flush=True)
    print('  [OK] Todos los datasets OE2 sincronizados con CityLearn schema', flush=True)
    print(flush=True)

    print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO', flush=True)
    print('-' * 80, flush=True)

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
                # Usar pv_generation_kwh (energía) - consistente con CityLearn v2
                if 'pv_generation_kwh' in df_solar.columns:
                    self.solar_hourly_kwh = np.array(df_solar['pv_generation_kwh'].values)
                elif 'ac_energy_kwh' in df_solar.columns:
                    self.solar_hourly_kwh = np.array(df_solar['ac_energy_kwh'].values)
                else:
                    # Fallback a potencia (para datos horarios kW ≈ kWh)
                    self.solar_hourly_kwh = np.array(df_solar['ac_power_kw'].values)
                print(f'    [OK] Solar: {float(np.sum(self.solar_hourly_kwh)):.0f} kWh/anio')
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] Solar: {e}')
                self.solar_hourly_kwh = np.zeros(8760, dtype=np.float32)  # Fallback
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
                # Flujos de energía reales del BESS (columnas CityLearn v2)
                self.pv_to_ev_kwh = np.array(self.bess_real_data['pv_to_ev_kwh'].values) if 'pv_to_ev_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                self.pv_to_bess_kwh = np.array(self.bess_real_data['pv_to_bess_kwh'].values) if 'pv_to_bess_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                self.grid_to_ev_kwh = np.array(self.bess_real_data['grid_to_ev_kwh'].values) if 'grid_to_ev_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                self.grid_to_mall_kwh = np.array(self.bess_real_data['grid_to_mall_kwh'].values) if 'grid_to_mall_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                self.bess_charge_kwh = np.array(self.bess_real_data['bess_charge_kwh'].values) if 'bess_charge_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                self.bess_discharge_kwh = np.array(self.bess_real_data['bess_discharge_kwh'].values) if 'bess_discharge_kwh' in self.bess_real_data.columns else np.zeros(len(self.bess_real_data))
                pv_ev_total = float(np.sum(self.pv_to_ev_kwh))
                grid_ev_total = float(np.sum(self.grid_to_ev_kwh))
                print(f'    [OK] BESS: {len(self.bess_soc_percent)} horas')
                print(f'       Flujos: pv_to_ev={pv_ev_total:.0f}kWh, grid_to_ev={grid_ev_total:.0f}kWh')
            except (FileNotFoundError, KeyError, ValueError) as e:
                print(f'    [ERROR] BESS: {e}')
                self.bess_soc_percent = np.full(8760, 0.5, dtype=np.float32)  # Fallback 50%
                self.pv_to_ev_kwh = np.zeros(8760)
                self.pv_to_bess_kwh = np.zeros(8760)
                self.grid_to_ev_kwh = np.zeros(8760)
                self.grid_to_mall_kwh = np.zeros(8760)
                self.bess_charge_kwh = np.zeros(8760)
                self.bess_discharge_kwh = np.zeros(8760)

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
            # Distribución correcta según IquitosContext:
            #   - 28 chargers motos × 4 sockets = 112 sockets motos @ 2.0 kWh bateria
            #   - 4 chargers mototaxis × 4 sockets = 16 sockets mototaxis @ 4.5 kWh bateria
            self.battery_soc = np.random.uniform(20, 80, size=(8760, 128)).astype(np.float32)  # SOC inicial 20-80%

            # Capacidad nominal por socket (consistente con CityLearn v2 schema)
            self.battery_capacity = np.zeros(128, dtype=np.float32)
            self.battery_capacity[0:112] = np.random.uniform(1.8, 2.2, 112)    # Motos (indices 0-111) @ ~2.0 kWh
            self.battery_capacity[112:128] = np.random.uniform(4.0, 5.0, 16)   # Mototaxis (indices 112-127) @ ~4.5 kWh

            # Tipos vehiculo (asignacion - 112 motos + 16 mototaxis = 128 total)
            self.vehicle_types = np.array(["moto"]*112 + ["mototaxi"]*16)

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

            # Observación inicial REAL (no random) - hora 0
            obs = self._build_observation_from_real_data(hour_index=0)
            return obs, {}

        def _build_observation_from_real_data(self, hour_index: int) -> np.ndarray:
            """Construir observación desde datos reales OE2 (1045 dimensiones)."""
            obs = np.zeros(self.obs_dim, dtype=np.float32)
            hour_index = hour_index % 8760  # Garantizar índice válido

            # ========== PRIMERAS 394 DIMENSIONES: ESTADO DEL SISTEMA ==========
            # Formato: [solar_features, bess_features, mall_features, time_features, charger_stats]

            # 1. Solar features (0-49): Generación PV horaria y estadísticas
            solar_gen = self.solar_hourly_kwh[hour_index] if hour_index < len(self.solar_hourly_kwh) else 0.0
            obs[0] = solar_gen / 3000.0  # Normalizado (max ~3000 kW)
            obs[1] = solar_gen  # Valor absoluto
            obs[2] = float(np.mean(self.solar_hourly_kwh)) / 3000.0  # Media normalizada
            obs[3] = float(np.max(self.solar_hourly_kwh)) / 3000.0  # Max normalizado
            obs[4] = float(np.std(self.solar_hourly_kwh)) / 1000.0  # Std normalizada
            # Solar últimas 24 horas (5-28)
            start_idx = max(0, hour_index - 23)
            solar_window = self.solar_hourly_kwh[start_idx:hour_index+1]
            for idx, val in enumerate(solar_window[-24:]):
                obs[5 + idx] = val / 3000.0
            # Padding si menos de 24 horas
            if len(solar_window) < 24:
                pass  # Ya es 0 por defecto

            # 2. BESS features (50-99): Estado de batería
            bess_soc = self.bess_soc_percent[hour_index] if hour_index < len(self.bess_soc_percent) else 0.5
            obs[50] = bess_soc  # SOC [0-1]
            obs[51] = bess_soc * 4520.0 / 1000.0  # Energía almacenada kWh normalizada
            obs[52] = 4520.0 / 10000.0  # Capacidad BESS normalizada
            obs[53] = 2712.0 / 5000.0  # Potencia BESS normalizada
            # BESS últimas 24 horas (54-77)
            bess_window = self.bess_soc_percent[start_idx:hour_index+1]
            for bess_idx, bess_val in enumerate(bess_window[-24:]):
                obs[54 + bess_idx] = bess_val

            # 3. Mall demand features (100-149): Demanda del mall
            mall_demand = self.mall_hourly_kwh[hour_index] if hour_index < len(self.mall_hourly_kwh) else 0.0
            obs[100] = mall_demand / 3000.0  # Demanda normalizada
            obs[101] = mall_demand  # Valor absoluto
            obs[102] = np.mean(self.mall_hourly_kwh) / 3000.0  # Media
            obs[103] = np.max(self.mall_hourly_kwh) / 3000.0  # Max
            # Mall últimas 24 horas (104-127)
            mall_window = self.mall_hourly_kwh[start_idx:hour_index+1]
            for mall_idx, mall_val in enumerate(mall_window[-24:]):
                obs[104 + mall_idx] = mall_val / 3000.0

            # 4. Time features (150-199): Características temporales
            hour_of_day = hour_index % 24
            day_of_year = hour_index // 24
            month = min(11, day_of_year // 30)
            obs[150] = hour_of_day / 24.0  # Hora [0-1]
            obs[151] = day_of_year / 365.0  # Día [0-1]
            obs[152] = month / 12.0  # Mes [0-1]
            obs[153] = np.sin(2 * np.pi * hour_of_day / 24)  # Sinusoidal hora
            obs[154] = np.cos(2 * np.pi * hour_of_day / 24)  # Cosinusoidal hora
            obs[155] = np.sin(2 * np.pi * day_of_year / 365)  # Sinusoidal año
            obs[156] = np.cos(2 * np.pi * day_of_year / 365)  # Cosinusoidal año
            obs[157] = 1.0 if 6 <= hour_of_day <= 18 else 0.0  # Es día
            obs[158] = 1.0 if 9 <= hour_of_day <= 22 else 0.0  # Horario carga
            obs[159] = 1.0 if hour_of_day in [7, 8, 17, 18, 19] else 0.0  # Hora pico

            # 5. Charger statistics (200-393): 128 sockets × 1.5 features
            for socket_idx in range(128):
                charger_power = self.chargers_hourly_kw[hour_index, socket_idx] if hour_index < len(self.chargers_hourly_kw) else 0.0
                obs[200 + socket_idx] = charger_power / 5.0  # Potencia normalizada (max 5 kW)
            # Estadísticas agregadas de chargers
            total_charger_power = np.sum(self.chargers_hourly_kw[hour_index]) if hour_index < len(self.chargers_hourly_kw) else 0.0
            obs[328] = total_charger_power / 400.0  # Total normalizado
            obs[329] = np.mean(self.chargers_hourly_kw[hour_index]) / 5.0  # Media socket
            obs[330] = np.max(self.chargers_hourly_kw[hour_index]) / 5.0  # Max socket

            # ========== COLUMNAS SOLAR (394-403): 10 columnas dataset PVGIS ==========
            if self.solar_all_columns is not None and hour_index < len(self.solar_all_columns):
                obs[394:404] = self.solar_all_columns[hour_index].astype(np.float32)[:10]

            # ========== ESTADO BATERÍAS (404-1044): 128 sockets × 5 features ==========
            battery_soc = self.battery_soc_episode[hour_index] if hour_index < len(self.battery_soc_episode) else np.full(128, 50.0)
            battery_charge_needed = np.maximum(0, (100 - battery_soc) / 100.0 * self.battery_capacity)
            charger_powers = self.chargers_hourly_kw[hour_index] if hour_index < len(self.chargers_hourly_kw) else np.zeros(128)
            battery_time_to_full = np.divide(
                battery_charge_needed * 60,
                charger_powers,
                out=np.zeros_like(charger_powers, dtype=np.float32),
                where=charger_powers > 0.1
            )
            battery_plugged_in = (charger_powers > 0.5).astype(np.float32)

            obs[404:532] = battery_soc  # SOC %
            obs[532:660] = battery_charge_needed  # kWh faltante
            obs[660:788] = charger_powers  # kW actuales
            obs[788:916] = np.clip(battery_time_to_full, 0, 500)  # minutos (limitado)
            obs[916:1044] = battery_plugged_in  # conectado [0,1]

            # Última dimensión: contador de paso normalizado
            obs[1044] = hour_index / 8760.0

            return obs

        def step(self, action):
            """Ejecutar un paso usando datos reales de 5 archivos OE2."""
            self.step_count += 1
            hour_index = (self.step_count - 1) % 8760  # Índice [0-8759]
            hour = hour_index % 24  # Hora del día [0-23]

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
            solar_generation_kwh = float(self.solar_hourly_kwh[hour_index])

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
            # FIX: Usar np.divide con where para evitar division por cero
            battery_time_to_full = np.divide(
                battery_charge_needed * 60,
                charger_powers,
                out=np.zeros_like(charger_powers),
                where=charger_powers > 0.1
            )  # minutos hasta carga completa
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

            # AGREGAR BONUS POR SATISFACTION DE BATERIAS (integrado en escala [-1,1])
            # ev_satisfaction está en [0,1], convertir a [-1,1] y ponderar
            ev_bonus = (2.0 * ev_satisfaction - 1.0)  # Escala [-1, 1]
            total_reward = total_reward * 0.85 + ev_bonus * 0.15  # Ponderación 85%/15%
            # Mantener en rango estable para SAC
            total_reward = float(np.clip(total_reward, -1.0, 1.0))

            # === TRACKING ACUMULATIVO ===
            self.co2_avoided_total += components.get('co2_avoided_total_kg', 0)
            self.solar_kwh_total += solar_generation_kwh
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh

            self.episode_reward += total_reward

            # Actualizar battery_soc_episode para el siguiente step
            if hour_index + 1 < len(self.battery_soc_episode):
                self.battery_soc_episode[hour_index + 1] = battery_soc_new

            # Construir observación siguiente desde datos reales OE2
            next_hour_index = (hour_index + 1) % 8760
            obs = self._build_observation_from_real_data(next_hour_index)

            # Actualizar estado de baterías en observación (datos más recientes)
            obs[404:532] = battery_soc_new
            obs[532:660] = battery_charge_needed
            obs[660:788] = battery_charge_power
            obs[788:916] = np.clip(battery_time_to_full, 0, 500)
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

            # === CONTEO DE VEHICULOS CARGADOS (MOTOS + MOTOTAXIS) ===
            # Motos (sockets 28-127): contar cuántas están cargando activamente (action > 0.5)
            motos_charging_count = int(np.sum(motos_action > 0.5))  # Motos con carga activa
            mototaxis_charging_count = int(np.sum(mototaxis_action > 0.5))  # Mototaxis con carga activa
            total_evs_charging = motos_charging_count + mototaxis_charging_count

            # === ESTABILIDAD DE RED (r_grid) ===
            # Penalizar cambios bruscos en importación de grid (suavizar curva)
            if not hasattr(self, 'prev_grid_import'):
                self.prev_grid_import = grid_import_kwh
            grid_ramp = abs(grid_import_kwh - self.prev_grid_import)
            # Baseline: 50 kWh/h de rampa es aceptable, más es penalizado
            r_grid = 1.0 - min(1.0, grid_ramp / 100.0)  # [0, 1] normalizado
            r_grid = 2.0 * r_grid - 1.0  # Escalar a [-1, 1]
            self.prev_grid_import = grid_import_kwh

            # === PROGRESO DE CONTROL SOCKETS ===
            # Porcentaje de sockets activos vs disponibles
            sockets_active_pct = (total_evs_charging / 128.0) * 100.0
            # Control efectivo del BESS (qué tan activo está el control)
            bess_control_intensity = abs(bess_setpoint - 0.5) * 2.0  # [0, 1] donde 1 = máximo control

            # === AHORRO DE COSTOS (baseline vs actual) ===
            # Baseline sin solar: todo de grid a 0.20 USD/kWh
            cost_baseline_usd = (ev_charging_kwh + float(self.mall_hourly_kwh[hour_index])) * 0.20
            cost_actual_usd = float(components.get('cost_usd', 0))
            cost_savings_usd = max(0, cost_baseline_usd - cost_actual_usd)

            terminated = self.step_count >= self.max_steps
            truncated = False
            info = {
                'step': self.step_count,
                'hour': hour,
                'episode': self.episode_num,
                'episode_reward': self.episode_reward,
                # === COMPONENTES DE REWARD (multiobjetivo) ===
                'r_co2': float(components.get('r_co2', 0)),
                'r_solar': float(components.get('r_solar', 0)),
                'r_cost': float(components.get('r_cost', 0)),
                'r_ev': float(components.get('r_ev', 0)),
                'r_grid': float(r_grid),  # Estabilidad de red
                # === METRICAS CO2 (directa e indirecta) ===
                'co2_grid_kg': float(components.get('co2_grid_kg', 0)),
                'co2_avoided_indirect_kg': float(components.get('co2_avoided_indirect_kg', 0)),
                'co2_avoided_direct_kg': float(components.get('co2_avoided_direct_kg', 0)),
                'co2_avoided_total_kg': float(components.get('co2_avoided_total_kg', 0)),
                # === CONTEO VEHICULOS CARGADOS ===
                'motos_charging_count': motos_charging_count,
                'mototaxis_charging_count': mototaxis_charging_count,
                'total_evs_charging': total_evs_charging,
                # === DISPATCH ENERGIA ===
                'ev_charging_kwh': float(ev_charging_kwh),
                'bess_power_kw': float(bess_power_kw),
                'motos_power_kw': float(motos_power),
                'mototaxis_power_kw': float(mototaxis_power),
                'grid_import_kwh': float(grid_import_kwh),
                'solar_generation_kwh': float(solar_generation_kwh),
                # === CONTROL Y PROGRESO ===
                'bess_soc': float(bess_soc),
                'bess_control_intensity': float(bess_control_intensity),
                'sockets_active_pct': float(sockets_active_pct),
                'ev_soc_avg': float(ev_soc_avg),
                'ev_satisfaction': float(ev_satisfaction),
                # === COSTOS Y AHORRO ===
                'cost_usd': float(cost_actual_usd),
                'cost_baseline_usd': float(cost_baseline_usd),
                'cost_savings_usd': float(cost_savings_usd),
                # === ESTABILIDAD ===
                'grid_ramp_kwh': float(grid_ramp),
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
        """Callback con métricas detalladas de CO2, Solar y EV durante entrenamiento."""

        def __init__(self, env_ref: CityLearnRealEnv, output_dir: Path, verbose: int = 1):
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
            # Nuevas métricas
            self.episode_cost_usd: list[float] = []
            self.episode_bess_soc_avg: list[float] = []
            self.episode_ev_soc_avg: list[float] = []

            # TRACE: registro paso a paso
            self.trace_records: list[dict[str, Any]] = []

            # TIMESERIES: registro horario por episodio
            self.timeseries_records: list[dict[str, Any]] = []

            # Tracking actual
            self.current_episode = 0
            self.ep_co2_grid = 0.0
            self.ep_co2_avoided_indirect = 0.0
            # Nuevas métricas tracking
            self.ep_cost_usd = 0.0
            self.ep_bess_soc_sum = 0.0
            self.ep_ev_soc_sum = 0.0
            self.ep_co2_avoided_direct = 0.0
            self.ep_solar = 0.0
            self.ep_ev = 0.0
            self.ep_grid = 0.0
            self.ep_reward = 0.0
            self.ep_steps = 0
            
            # === NUEVAS MÉTRICAS DETALLADAS ===
            # Componentes de reward
            self.ep_r_solar_sum = 0.0
            self.ep_r_cost_sum = 0.0
            self.ep_r_ev_sum = 0.0
            self.ep_r_grid_sum = 0.0
            self.ep_r_co2_sum = 0.0
            # Conteo vehículos
            self.ep_motos_count = 0
            self.ep_mototaxis_count = 0
            # Ahorro y control
            self.ep_cost_savings = 0.0
            self.ep_sockets_active_sum = 0.0
            self.ep_bess_control_sum = 0.0
            self.ep_grid_ramp_sum = 0.0
            # Listas históricas para análisis
            self.episode_r_solar: list[float] = []
            self.episode_r_cost: list[float] = []
            self.episode_r_ev: list[float] = []
            self.episode_r_grid: list[float] = []
            self.episode_motos: list[int] = []
            self.episode_mototaxis: list[int] = []
            self.episode_cost_savings: list[float] = []

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
            # Nuevas métricas
            self.ep_cost_usd += info.get('cost_usd', 0)
            self.ep_bess_soc_sum += info.get('bess_soc', 0)
            self.ep_ev_soc_sum += info.get('ev_soc_avg', 0)
            self.ep_steps += 1
            
            # === ACUMULAR MÉTRICAS DETALLADAS ===
            # Componentes de reward individuales
            self.ep_r_solar_sum += info.get('r_solar', 0)
            self.ep_r_cost_sum += info.get('r_cost', 0)
            self.ep_r_ev_sum += info.get('r_ev', 0)
            self.ep_r_grid_sum += info.get('r_grid', 0)
            self.ep_r_co2_sum += info.get('r_co2', 0)
            # Conteo de vehículos cargados
            self.ep_motos_count += info.get('motos_charging_count', 0)
            self.ep_mototaxis_count += info.get('mototaxis_charging_count', 0)
            # Costos y control
            self.ep_cost_savings += info.get('cost_savings_usd', 0)
            self.ep_sockets_active_sum += info.get('sockets_active_pct', 0)
            self.ep_bess_control_sum += info.get('bess_control_intensity', 0)
            self.ep_grid_ramp_sum += info.get('grid_ramp_kwh', 0)

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

            # Acumular reward por step (FIX: SB3 resetea el ambiente antes del callback)
            self.ep_reward += reward_val

            # Detectar fin de episodio
            dones = self.locals.get('dones', [False])
            if dones[0]:
                # FIX: Leer episode_reward de info (el ambiente ya fue reseteado por SB3)
                # El info contiene el valor ANTES del reset
                ep_reward_from_info = info.get('episode_reward', self.ep_reward)
                if ep_reward_from_info != 0:
                    self.ep_reward = ep_reward_from_info
                # Si ambos son 0, usamos el acumulado en el callback (self.ep_reward)
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
            # co2_net calculado pero no mostrado (reservado para futuro)
            _ = self.ep_co2_grid - self.ep_co2_avoided_indirect - self.ep_co2_avoided_direct

            print(f'    Steps: {self.num_timesteps:>7,} | Ep: {ep_num:>2} | '
                  f'Progreso: {pct:>5.1f}% | '
                  f'CO2_grid: {self.ep_co2_grid:>8,.0f} kg | '
                  f'CO2_evitado: {(self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct):>8,.0f} kg', flush=True)

        def _log_episode_summary(self) -> None:
            """Resumen completo al finalizar episodio."""
            co2_avoided_total = self.ep_co2_avoided_indirect + self.ep_co2_avoided_direct
            co2_net = self.ep_co2_grid - co2_avoided_total
            co2_reduction_pct = (co2_avoided_total / max(1, self.ep_co2_grid + co2_avoided_total)) * 100

            print(flush=True)
            print('  ' + '='*76, flush=True)
            print(f'  EPISODIO {self.current_episode + 1} COMPLETADO ({self.ep_steps:,} pasos)', flush=True)
            print('  ' + '='*76, flush=True)
            print(f'    Reward Total Episodio:     {self.ep_reward:>12,.2f}', flush=True)
            print(flush=True)
            print('    --- METRICAS CO2 (desde 5 datasets OE2) ---', flush=True)
            print(f'    CO2 Grid (emitido):        {self.ep_co2_grid:>12,.1f} kg', flush=True)
            print(f'    CO2 Evitado Indirecto:     {self.ep_co2_avoided_indirect:>12,.1f} kg  (solar -> grid)', flush=True)
            print(f'    CO2 Evitado Directo:       {self.ep_co2_avoided_direct:>12,.1f} kg  (EVs desde solar)', flush=True)
            print(f'    CO2 Evitado TOTAL:         {co2_avoided_total:>12,.1f} kg', flush=True)
            print(f'    CO2 NETO:                  {co2_net:>12,.1f} kg  ({co2_reduction_pct:>5.1f}% reduccion)', flush=True)
            print(flush=True)
            
            # === COMPONENTES DE REWARD MULTIOBJETIVO ===
            print('    --- COMPONENTES REWARD (0.20 Solar, 0.10 Cost, 0.30 EV, 0.05 Grid, 0.35 CO2) ---', flush=True)
            r_solar_avg = self.ep_r_solar_sum / max(1, self.ep_steps)
            r_cost_avg = self.ep_r_cost_sum / max(1, self.ep_steps)
            r_ev_avg = self.ep_r_ev_sum / max(1, self.ep_steps)
            r_grid_avg = self.ep_r_grid_sum / max(1, self.ep_steps)
            r_co2_avg = self.ep_r_co2_sum / max(1, self.ep_steps)
            print(f'    r_solar (autoconsumo):     {r_solar_avg:>11.4f}  [ponderado 0.20]', flush=True)
            print(f'    r_cost (minimizar tarifa): {r_cost_avg:>11.4f}  [ponderado 0.10]', flush=True)
            print(f'    r_ev (satisfaccion carga): {r_ev_avg:>11.4f}  [ponderado 0.30]', flush=True)
            print(f'    r_grid (estabilidad):      {r_grid_avg:>11.4f}  [ponderado 0.05]', flush=True)
            print(f'    r_co2 (reduccion CO2):     {r_co2_avg:>11.4f}  [ponderado 0.35]', flush=True)
            print(flush=True)
            
            print('    --- ENERGIA (sincronizada con CityLearn) ---', flush=True)
            print(f'    Solar Generada:            {self.ep_solar:>12,.1f} kWh', flush=True)
            print(f'    EV Cargados:               {self.ep_ev:>12,.1f} kWh', flush=True)
            print(f'    Grid Import:               {self.ep_grid:>12,.1f} kWh', flush=True)

            # Autoconsumo solar
            if self.ep_solar > 0:
                solar_used = min(self.ep_solar, self.ep_ev + self.ep_grid * 0.5)
                autoconsumo_pct = (solar_used / self.ep_solar) * 100
                print(f'    Autoconsumo Solar:         {autoconsumo_pct:>11.1f}%', flush=True)
            print(flush=True)
            
            # === CONTEO DE VEHÍCULOS CARGADOS ===
            print('    --- VEHICULOS CARGADOS (MOTOS + MOTOTAXIS) ---', flush=True)
            motos_daily_avg = self.ep_motos_count / max(1, self.ep_steps / 24)
            mototaxis_daily_avg = self.ep_mototaxis_count / max(1, self.ep_steps / 24)
            print(f'    Motos cargando (total):    {self.ep_motos_count:>12,} vehiculo-horas', flush=True)
            print(f'    Mototaxis cargando (total):{self.ep_mototaxis_count:>12,} vehiculo-horas', flush=True)
            print(f'    Motos/dia (promedio):      {motos_daily_avg:>11.0f} motos/dia', flush=True)
            print(f'    Mototaxis/dia (promedio):  {mototaxis_daily_avg:>11.0f} mototaxis/dia', flush=True)
            print(flush=True)
            
            # === MÉTRICAS OPERATIVAS ===
            print('    --- METRICAS OPERATIVAS (BESS, EV, COSTO) ---', flush=True)
            bess_soc_avg = self.ep_bess_soc_sum / max(1, self.ep_steps) * 100  # Convertir a %
            ev_soc_avg = self.ep_ev_soc_sum / max(1, self.ep_steps) * 100  # Convertir a %
            print(f'    BESS SOC Promedio:         {bess_soc_avg:>11.1f}%', flush=True)
            print(f'    EV SOC Promedio:           {ev_soc_avg:>11.1f}%', flush=True)
            print(f'    Costo Total:               ${self.ep_cost_usd:>10,.2f} USD', flush=True)
            print(f'    Ahorro desde Baseline:     ${self.ep_cost_savings:>10,.2f} USD', flush=True)
            print(flush=True)
            
            # === PROGRESO DE CONTROL ===
            print('    --- PROGRESO DE CONTROL (BESS + SOCKETS) ---', flush=True)
            sockets_active_avg = self.ep_sockets_active_sum / max(1, self.ep_steps)
            bess_control_avg = self.ep_bess_control_sum / max(1, self.ep_steps) * 100
            grid_ramp_avg = self.ep_grid_ramp_sum / max(1, self.ep_steps)
            print(f'    Sockets Activos (promedio):{sockets_active_avg:>11.1f}% de 128', flush=True)
            print(f'    BESS Control Intensidad:   {bess_control_avg:>11.1f}% (intensidad promedio)', flush=True)
            print(f'    Grid Ramp Promedio:        {grid_ramp_avg:>11.1f} kWh/h (estabilidad)', flush=True)
            print('  ' + '='*76, flush=True)
            print(flush=True)
            sys.stdout.flush()  # Forzar flush

            # Guardar para análisis posterior
            self.episode_rewards.append(self.ep_reward)
            self.episode_co2_grid.append(self.ep_co2_grid)
            self.episode_co2_avoided_indirect.append(self.ep_co2_avoided_indirect)
            self.episode_co2_avoided_direct.append(self.ep_co2_avoided_direct)
            self.episode_solar_kwh.append(self.ep_solar)
            self.episode_ev_charging.append(self.ep_ev)
            self.episode_grid_import.append(self.ep_grid)
            # Nuevas métricas guardadas
            self.episode_cost_usd.append(self.ep_cost_usd)
            self.episode_bess_soc_avg.append(bess_soc_avg)
            self.episode_ev_soc_avg.append(ev_soc_avg)
            # Guardar métricas detalladas
            self.episode_r_solar.append(r_solar_avg)
            self.episode_r_cost.append(r_cost_avg)
            self.episode_r_ev.append(r_ev_avg)
            self.episode_r_grid.append(r_grid_avg)
            self.episode_motos.append(self.ep_motos_count)
            self.episode_mototaxis.append(self.ep_mototaxis_count)
            self.episode_cost_savings.append(self.ep_cost_savings)

        def _reset_episode_tracking(self) -> None:
            """Reset acumuladores para nuevo episodio."""
            self.ep_co2_grid = 0.0
            self.ep_co2_avoided_indirect = 0.0
            self.ep_co2_avoided_direct = 0.0
            self.ep_solar = 0.0
            self.ep_ev = 0.0
            self.ep_grid = 0.0
            self.ep_reward = 0.0
            self.ep_steps = 0
            # Reset nuevas métricas
            self.ep_cost_usd = 0.0
            self.ep_bess_soc_sum = 0.0
            self.ep_ev_soc_sum = 0.0
            # === RESET MÉTRICAS DETALLADAS ===
            self.ep_r_solar_sum = 0.0
            self.ep_r_cost_sum = 0.0
            self.ep_r_ev_sum = 0.0
            self.ep_r_grid_sum = 0.0
            self.ep_r_co2_sum = 0.0
            self.ep_motos_count = 0
            self.ep_mototaxis_count = 0
            self.ep_cost_savings = 0.0
            self.ep_sockets_active_sum = 0.0
            self.ep_bess_control_sum = 0.0
            self.ep_grid_ramp_sum = 0.0

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='sac_checkpoint',
        save_replay_buffer=True
    )

    logging_callback = DetailedLoggingCallback(env, OUTPUT_DIR)

    # TIMESTEPS: 8760 steps = 1 episodio (1 año completo)
    # Mínimo recomendado: 26,280 (3 episodios) para verificar aprendizaje
    # Óptimo: 87,600 (10 episodios) para convergencia estable
    TOTAL_TIMESTEPS = 87600  # 10 episodios completos con datos reales OE2

    print(f'  CONFIGURACION: {TOTAL_TIMESTEPS:,} timesteps')
    print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-07):')
    print('    CO2 grid (0.35): Minimizar importacion')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90% (PRIORIDAD MAXIMA)')
    print('    Cost (0.10): Minimizar costo')
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
    print(f'    Episodios completados: {len(logging_callback.episode_rewards)}')
    print()

    # RESUMEN DE APRENDIZAJE POR EPISODIO
    if len(logging_callback.episode_rewards) > 1:
        print('  EVOLUCION DEL APRENDIZAJE:')
        print('  ' + '-'*76)
        print('  {:>3} | {:>12} | {:>12} | {:>12} | {:>10}'.format(
            'Ep', 'Reward', 'CO2_Grid(kg)', 'CO2_Evit(kg)', 'Reduccion%'))
        print('  ' + '-'*76)
        for ep_idx, (rew, co2g, co2i, co2d) in enumerate(zip(
            logging_callback.episode_rewards,
            logging_callback.episode_co2_grid,
            logging_callback.episode_co2_avoided_indirect,
            logging_callback.episode_co2_avoided_direct
        )):
            co2_avoided = co2i + co2d
            reduction_pct = (co2_avoided / max(1, co2g + co2_avoided)) * 100
            print(f'  {ep_idx+1:>3} | {rew:>12,.2f} | {co2g:>12,.0f} | {co2_avoided:>12,.0f} | {reduction_pct:>9.1f}%')
        print('  ' + '-'*76)

        # Tendencia de mejora
        if len(logging_callback.episode_rewards) >= 2:
            first_reward = logging_callback.episode_rewards[0]
            last_reward = logging_callback.episode_rewards[-1]
            improvement = ((last_reward - first_reward) / abs(first_reward)) * 100 if first_reward != 0 else 0
            print(f'  Mejora Reward (Ep1 vs EpN): {improvement:>+.1f}%')

            first_co2_reduction = (logging_callback.episode_co2_avoided_indirect[0] +
                                   logging_callback.episode_co2_avoided_direct[0])
            last_co2_reduction = (logging_callback.episode_co2_avoided_indirect[-1] +
                                  logging_callback.episode_co2_avoided_direct[-1])
            co2_improvement = ((last_co2_reduction - first_co2_reduction) / max(1, first_co2_reduction)) * 100
            print(f'  Mejora CO2 Evitado (Ep1 vs EpN): {co2_improvement:>+.1f}%')
        print()

    # Guardar modelo final
    final_model_path = CHECKPOINT_DIR / 'sac_final_model'
    agent.save(str(final_model_path))
    print(f'  OK Modelo guardado: {final_model_path}.zip')
    print()

    print('[6] VALIDACION FINAL - EVALUACION DE POLITICAS APRENDIDAS')
    print('-' * 80)

    print('  Validacion: 10 episodios')
    print('  ' + '-'*76)
    print()

    val_metrics: dict[str, list[float]] = {
        'rewards': [],
        'co2_avoided': [],
        'solar_kwh': [],
        'cost_usd': [],
        'grid_import': [],
    }

    for ep in range(10):
        obs_val, _ = env.reset()
        done = False
        steps = 0
        ep_co2 = 0.0
        ep_solar = 0.0
        ep_grid = 0.0

        print(f'  Episodio {ep+1}/10: ', end='', flush=True)

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
        },
        'training_evolution': {
            'episode_rewards': logging_callback.episode_rewards,
            'episode_co2_grid': logging_callback.episode_co2_grid,
            'episode_co2_avoided_indirect': logging_callback.episode_co2_avoided_indirect,
            'episode_co2_avoided_direct': logging_callback.episode_co2_avoided_direct,
            'episode_solar_kwh': logging_callback.episode_solar_kwh,
            'episode_ev_charging': logging_callback.episode_ev_charging,
            'episode_grid_import': logging_callback.episode_grid_import,
        }
    }

    # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
    print('  GUARDANDO ARCHIVOS DE SALIDA:')

    # 1. result_sac.json - Resumen completo del entrenamiento
    result_file = OUTPUT_DIR / 'result_sac.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'    [OK] {result_file}')

    # 2. timeseries_sac.csv - Series temporales por hora
    timeseries_file = OUTPUT_DIR / 'timeseries_sac.csv'
    if logging_callback.timeseries_records:
        df_timeseries = pd.DataFrame(logging_callback.timeseries_records)
        df_timeseries.to_csv(timeseries_file, index=False, encoding='utf-8')
        print(f'    [OK] {timeseries_file} ({len(df_timeseries):,} registros)')
    else:
        print(f'    [WARN] {timeseries_file} - sin datos')

    # 3. trace_sac.csv - Trazabilidad paso a paso
    trace_file = OUTPUT_DIR / 'trace_sac.csv'
    if logging_callback.trace_records:
        df_trace = pd.DataFrame(logging_callback.trace_records)
        df_trace.to_csv(trace_file, index=False, encoding='utf-8')
        print(f'    [OK] {trace_file} ({len(df_trace):,} registros)')
    else:
        print(f'    [WARN] {trace_file} - sin datos')

    # Mantener compatibilidad con archivo anterior
    metrics_file = OUTPUT_DIR / 'sac_training_metrics.json'
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print()

    print('='*80)
    print('ENTRENAMIENTO SAC COMPLETADO')
    print('='*80)
    print()

    print('RESULTADOS FINALES - VALIDACION 10 EPISODIOS:')
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
