#!/usr/bin/env python3
"""Construir CityLearn v2 con datos OE2 existentes - SIN crear nuevos datos"""

import sys
import os
from pathlib import Path
import yaml
import pandas as pd
import numpy as np
from typing import Any

# Configurar encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

print('='*60)
print('CONSTRUIR CITYLEARN v2 CON DATOS OE2')
print('='*60)
print()

try:
    # Step 1: Verificar datos disponibles en data/interim/oe2
    print('[1] Verificando datos disponibles en data/interim/oe2...')
    root_oe2 = Path('data/interim/oe2')

    archivos_disponibles = {}

    # Solar
    solar_path = root_oe2 / 'solar/pv_generation_timeseries.csv'
    if solar_path.exists():
        df_solar = pd.read_csv(solar_path)
        archivos_disponibles['solar'] = {
            'path': solar_path,
            'rows': len(df_solar),
            'status': 'OK'
        }
        print(f'    [OK] Solar: {len(df_solar)} filas')

    # Chargers specs
    chargers_path = root_oe2 / 'chargers/individual_chargers.json'
    if chargers_path.exists():
        archivos_disponibles['chargers_specs'] = {
            'path': chargers_path,
            'status': 'OK'
        }
        print(f'    [OK] Chargers specs: {chargers_path.name}')

    # BESS
    bess_path = root_oe2 / 'bess/bess_hourly_dataset_2024.csv'
    if bess_path.exists():
        df_bess = pd.read_csv(bess_path)
        archivos_disponibles['bess'] = {
            'path': bess_path,
            'rows': len(df_bess),
            'status': 'OK'
        }
        print(f'    [OK] BESS: {len(df_bess)} filas')

    # Mall demand
    mall_path = root_oe2 / 'mall_demand_hourly.csv'
    if mall_path.exists():
        df_mall = pd.read_csv(mall_path)
        archivos_disponibles['mall'] = {
            'path': mall_path,
            'rows': len(df_mall),
            'status': 'OK'
        }
        print(f'    [OK] Mall demand: {len(df_mall)} filas')

    print()

    # Step 2: Cargar config
    print('[2] Cargando configuración OE3...')
    with open('configs/default.yaml', 'r') as f:
        cfg = yaml.safe_load(f)
    print('    [OK] Configuración cargada')
    print()

    # Step 3: Construir dataset
    print('[3] Construyendo dataset CityLearn v2...')
    from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset

    dataset = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=Path('data/raw'),
        interim_dir=Path('data/interim/oe2'),
        processed_dir=Path('data/processed')
    )

    print(f'    [OK] Dataset construido')
    print(f'    - Directorio: {dataset.dataset_dir}')
    print(f'    - Schema: {dataset.schema_path}')
    print(f'    - Edificio: {dataset.building_name}')
    print()

    # Step 4: Crear environment
    print('[4] Creando environment CityLearn v2...')
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(str(dataset.schema_path))
    print('    [OK] Environment creado')
    print()

    # Step 5: Validar environment
    print('[5] Validando environment...')
    obs, info = env.reset()

    # Determine observation shape with proper type handling
    obs_shape: str = ""
    if isinstance(obs, list):
        obs_shape = f"{len(obs)} elementos"
        if len(obs) > 0:
            first_obs_item: Any = obs[0]
            # Check if first element has shape attribute (numpy array)
            if isinstance(first_obs_item, np.ndarray):
                obs_shape += f" (primer: {first_obs_item.shape})"
            elif isinstance(first_obs_item, (list, tuple)):
                obs_shape += f" (primer: {len(first_obs_item)} elementos)"
            else:
                obs_shape += f" (primer: escalar)"
    elif isinstance(obs, np.ndarray):
        obs_shape = str(obs.shape)
    else:
        obs_shape = f"{len(obs)} elementos"

    print(f'    [OK] Reset successful')
    print(f'    - Observation: {obs_shape}')
    print(f'    - Buildings: {len(env.buildings)}')
    print(f'    - Episode length: {env.time_steps - env.time_step} steps')
    print()

    # Step 6: Test step
    print('[6] Ejecutando test step...')
    # Para CityLearn v2, action_space es una lista de espacios, no un espacio único
    actions_list: list[Any] = []
    if isinstance(env.action_space, list):
        for space in env.action_space:
            action_sample = space.sample()
            # Convert numpy arrays to lists if needed
            if isinstance(action_sample, np.ndarray):
                actions_list.append(action_sample.tolist())
            else:
                actions_list.append(action_sample)
    else:
        for _ in range(len(env.buildings)):
            action_sample = env.action_space.sample()
            if isinstance(action_sample, np.ndarray):
                actions_list.append(action_sample.tolist())
            else:
                actions_list.append(action_sample)

    obs, reward, terminated, truncated, info = env.step(actions_list)
    print(f'    [OK] Step ejecutado')
    print(f'    - Reward: {reward}')
    print(f'    - Terminated: {terminated}')
    print()

    print('='*60)
    print('OK: CITYLEARN v2 CONSTRUIDO Y VALIDADO')
    print('='*60)
    print()
    print('LISTO PARA ENTRENAR AGENTES:')
    print('  $ python -m scripts.run_agent_training --agent SAC')
    print('  $ python -m scripts.run_agent_training --agent PPO')
    print('  $ python -m scripts.run_agent_training --agent A2C')
    print()

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    print()
    print('='*60)
    print('FALLO AL CONSTRUIR CITYLEARN v2')
    print('='*60)
    sys.exit(1)
