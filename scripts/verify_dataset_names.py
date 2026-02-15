#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION DE NOMBRES DE DATASETS - Listado completo
========================================================
Verifica que los nombres de datasets cargados en los scripts de entrenamiento
sean correctos y coincidan con los archivos reales en el sistema.
"""

from pathlib import Path
import pandas as pd
import sys

# Rutas canonicas de datasets
DATASET_PATHS = {
    'SOLAR': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
    'CHARGERS': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
    'BESS': Path('data/oe2/bess/bess_ano_2024.csv'),
    'MALL_DEMAND': Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
}

print('=' * 100)
print('VERIFICACION DE DATASETS - NOMBRES Y RUTAS REALES')
print('=' * 100)
print()

# 1. Verificar que existan
print('[PASO 1] VERIFICAR EXISTENCIA DE ARCHIVOS')
print('-' * 100)

all_exist = True
for dataset_name, path in DATASET_PATHS.items():
    exists = path.exists()
    status = '[OK] EXISTE' if exists else '[X] NO EXISTE'
    print(f'  {dataset_name:20} | {status:15} | {path}')
    if not exists:
        all_exist = False

print()

# 2. Si existen, cargar y mostrar estructura
if all_exist:
    print('[PASO 2] ESTRUCTURA DE CADA DATASET')
    print('-' * 100)
    print()
    
    for dataset_name, path in DATASET_PATHS.items():
        try:
            print(f'  [GRAPH] {dataset_name}')
            print(f'     Ruta: {path}')
            
            # Detectar separador
            with open(path, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
            
            if ',' in header:
                sep = ','
            elif ';' in header:
                sep = ';'
            else:
                sep = ','
            
            # Cargar
            df = pd.read_csv(path, sep=sep, nrows=5)
            
            print(f'     Separador: "{sep}"')
            print(f'     Filas totales: {len(pd.read_csv(path, sep=sep))}')
            print(f'     Columnas: {len(df.columns)}')
            print(f'     Primeras columnas (primeras 3):')
            for i, col in enumerate(df.columns[:3]):
                print(f'       [{i}] {col}')
            
            # Mostrar primeras filas
            print(f'     Primeras 3 filas:')
            print(df.head(3).to_string(index=False).replace('\n', '\n       '))
            
            print()
        except Exception as e:
            print(f'     [X] Error al cargar: {e}')
            print()

print('[PASO 3] NOMBRES DE COLUMNAS PARA OBSERVABLES (27 columnas esperadas)')
print('-' * 100)
print()

# Cargar y mostrar columnas reales vs esperadas
EXPECTED_COLS = {
    'CHARGERS': [
        'is_hora_punta', 'tarifa_aplicada_soles', 'ev_energia_total_kwh',
        'ev_costo_carga_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
        'ev_co2_reduccion_motos_kg', 'ev_co2_reduccion_mototaxis_kg',
        'ev_reduccion_directa_co2_kg', 'ev_demand_kwh'
    ],
    'SOLAR': [
        'is_hora_punta', 'tarifa_aplicada_soles', 'ahorro_solar_soles',
        'reduccion_indirecta_co2_kg', 'co2_evitado_mall_kg', 'co2_evitado_ev_kg'
    ],
    'BESS': [
        'bess_soc_percent', 'bess_charge_kwh', 'bess_discharge_kwh',
        'bess_to_mall_kwh', 'bess_to_ev_kwh'
    ],
    'MALL_DEMAND': [
        'mall_demand_kwh', 'mall_demand_reduction_kwh', 'mall_cost_soles'
    ],
}

if all_exist:
    for dataset_name in ['CHARGERS', 'SOLAR', 'BESS', 'MALL_DEMAND']:
        path = DATASET_PATHS[dataset_name]
        print(f'  {dataset_name}:')
        
        try:
            # Detectar sep
            with open(path, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
            sep = ';' if ';' in header else ','
            
            df = pd.read_csv(path, sep=sep, nrows=1)
            
            expected = EXPECTED_COLS.get(dataset_name, [])
            print(f'     Columnas esperadas: {expected}')
            print(f'     Columnas reales en archivo:')
            for i, col in enumerate(df.columns[:len(expected)]):
                expected_col = expected[i] if i < len(expected) else 'N/A'
                match = '[OK]' if col == expected_col else '[!] '
                print(f'       [{i}] {col:40} {match} (esperado: {expected_col})')
            
            print()
        except Exception as e:
            print(f'     [X] Error: {e}')
            print()

print('[PASO 4] RESUMEN DE SINCRONIZACION')
print('-' * 100)
print()

if all_exist:
    print('  [OK] ESTADO: TODOS LOS DATASETS EXISTEN')
    print()
    print('  RECOMENDACIONES:')
    print('  - SAC, PPO, A2C usan TODAS las 27 columnas')
    print('  - Verificar que los nombres de columnas coincidan EXACTAMENTE')
    print('  - Si hay discrepancias, actualizar los nombres en:')
    print('    * scripts/train/train_sac_multiobjetivo.py')
    print('    * scripts/train/train_ppo_multiobjetivo.py')
    print('    * scripts/train/train_a2c_multiobjetivo.py')
    print()
else:
    print('  [X] ESTADO: FALTAN DATASETS')
    print()
    print('  Archivos faltantes:')
    for dataset_name, path in DATASET_PATHS.items():
        if not path.exists():
            print(f'    [X] {dataset_name}: {path}')
    print()
    print('  ACCION: Verificar rutas en data/oe2/ o en archivos de configuracion')

print('=' * 100)
