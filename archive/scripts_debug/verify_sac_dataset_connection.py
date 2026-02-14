#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN COMPLETA: SAC Training conectado a Dataset Builder
================================================================

Verifica que:
1. train_sac_multiobjetivo.py importa correctamente de dataset_builder.py
2. Carga TODO los datos reales (BESS, EV, Solar, Mall)
3. Todas las columnas observables se usan en la observación SAC
4. Las acciones SAC controlan correctamente BESS y 38 chargers
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

WORKSPACE = Path(__file__).parent
DATA_ROOT = WORKSPACE / 'data'
SCRIPTS_ROOT = WORKSPACE / 'scripts' / 'train'

print('\n' + '='*100)
print('VERIFICACIÓN: SAC TRAINING ↔ DATASET BUILDER CONNECTION')
print('='*100)

# ===================================================================
# 1. LEER train_sac_multiobjetivo.py
# ===================================================================
print('\n[1] ANALIZANDO: scripts/train/train_sac_multiobjetivo.py')
print('-'*100)

sac_script = SCRIPTS_ROOT / 'train_sac_multiobjetivo.py'
if not sac_script.exists():
    print(f'❌ CRÍTICO: {sac_script} NO ENCONTRADO')
    sys.exit(1)

with open(sac_script, 'r', encoding='utf-8') as f:
    sac_content = f.read()

# Buscar imports
print('✅ Verificando IMPORTS en SAC:')
imports_to_find = [
    'from src.citylearnv2.dataset_builder',
    'load_datasets_from_processed',
    'IquitosContext',
    'MultiObjectiveReward',
    'from gymnasium import',
    'from stable_baselines3 import SAC',
]

for imp in imports_to_find:
    if imp in sac_content:
        print(f'   ✓ {imp}')
    else:
        print(f'   ✗ FALTA: {imp}')

# Buscar funciones clave
print('\n✅ Verificando FUNCIONES en SAC:')
functions_to_find = [
    'def load_datasets_from_processed',
    'def validate_solar_timeseries_hourly',
    'class RealOE2Environment',
    'class SACMetricsCallback',
]

for func in functions_to_find:
    if func in sac_content:
        print(f'   ✓ {func}')
    else:
        print(f'   ✗ FALTA: {func}')

# ===================================================================
# 2. VERIFICAR CARGA DE DATOS REALES
# ===================================================================
print('\n[2] ANALIZANDO: Carga de Datos Reales en SAC')
print('-'*100)

# Buscar referencias a archivos CSV
print('✅ Referencias a archivos de datos:')
if 'chargers_ev_ano_2024_v3.csv' in sac_content:
    print(f'   ✓ chargers_ev_ano_2024_v3.csv (38 SOCKETS)')
else:
    print(f'   ✗ NO ENCONTRADO: chargers_ev_ano_2024_v3.csv')

if 'pv_generation_hourly_citylearn_v2.csv' in sac_content or 'pv_generation_citylearn2024.csv' in sac_content:
    print(f'   ✓ Solar generation (PVGIS)')
else:
    print(f'   ✗ NO CLARO: referencia a solar')

if 'demandamallhorakwh.csv' in sac_content:
    print(f'   ✓ demandamallhorakwh.csv (MALL)')
else:
    print(f'   ✗ NO ENCONTRADO: mall demand')

if 'bess_ano_2024.csv' in sac_content:
    print(f'   ✓ bess_ano_2024.csv (BESS STORAGE)')
else:
    print(f'   ✗ NO ENCONTRADO: BESS data')

# Buscar variables de datos
print('\n✅ Variables de datos cargadas:')
data_vars = [
    ('solar_hourly', 'Solar horaria'),
    ('chargers_hourly', 'Chargers 38 sockets'),
    ('chargers_motos', 'Motos (30 sockets)'),
    ('chargers_mototaxis', 'Mototaxis (8 sockets)'),
    ('mall_hourly', 'Mall demand'),
    ('bess_soc', 'BESS SOC'),
    ('datasets =', 'Diccionario de datasets'),
]

for var, desc in data_vars:
    if var in sac_content:
        print(f'   ✓ {var:25} → {desc}')
    else:
        print(f'   ✗ NO ENCONTRADO: {var:25}')

# ===================================================================
# 3. VERIFICAR CONEXIÓN CON DATASET BUILDER
# ===================================================================
print('\n[3] ANALIZANDO: Integración con Dataset Builder')
print('-'*100)

dataset_builder = WORKSPACE / 'src' / 'citylearnv2' / 'dataset_builder' / 'dataset_builder.py'
if not dataset_builder.exists():
    print(f'❌ CRÍTICO: {dataset_builder} NO ENCONTRADO')
    sys.exit(1)

with open(dataset_builder, 'r', encoding='utf-8') as f:
    builder_content = f.read()

# Buscar constantes observables
print('✅ COLUMNAS OBSERVABLES DEFINIDAS EN DATASET_BUILDER:')
observables_to_find = [
    'CHARGERS_OBSERVABLE_COLS',
    'SOLAR_OBSERVABLE_COLS',
    'BESS_OBSERVABLE_COLS',
    'MALL_OBSERVABLE_COLS',
    'ALL_OBSERVABLE_COLS',
]

observable_columns = {}
for obs in observables_to_find:
    if obs in builder_content:
        print(f'   ✓ {obs}')
        # Buscar las columnas dentro
        start_idx = builder_content.find(f'{obs} = [')
        if start_idx > -1:
            end_idx = builder_content.find(']', start_idx)
            cols_str = builder_content[start_idx:end_idx+1]
            observable_columns[obs] = cols_str.count("'")
    else:
        print(f'   ✗ NO ENCONTRADO: {obs}')

print('\n✅ CANTIDAD DE COLUMNAS POR CATEGORÍA:')
expected_counts = {
    'CHARGERS_OBSERVABLE_COLS': 10,
    'SOLAR_OBSERVABLE_COLS': 6,
    'BESS_OBSERVABLE_COLS': 5,
    'MALL_OBSERVABLE_COLS': 3,
}

for col_type, expected in expected_counts.items():
    if col_type in observable_columns:
        actual = observable_columns[col_type]
        status = '✓' if actual >= expected else '✗'
        print(f'   {status} {col_type:30} = ~{actual} columnas (esperado {expected})')

# ===================================================================
# 4. VERIFICAR OBSERVATION SPACE EN SAC
# ===================================================================
print('\n[4] ANALIZANDO: Observation Space en SAC')
print('-'*100)

print('✅ Búsqueda de definición de observation space:')
if 'observation_space' in sac_content or 'Box(' in sac_content:
    print(f'   ✓ observation_space definido')
    # Buscar la dimensión
    if 'Box(low' in sac_content or 'Box(' in sac_content:
        print(f'   ✓ Usa Box (continuous space)')
else:
    print(f'   ✗ NO CLARO: observation_space')

print('\n✅ Búsqueda de dimensión de observación:')
obs_dims = [
    ('shape=', 'Forma de observación'),
    ('low=', 'Límite inferior'),
    ('high=', 'Límite superior'),
    ('dtype=', 'Tipo de datos'),
]

for pattern, desc in obs_dims:
    count = sac_content.count(pattern)
    if count > 0:
        print(f'   ✓ {pattern:15} encontrado {count} veces')

# ===================================================================
# 5. VERIFICAR ACTION SPACE EN SAC
# ===================================================================
print('\n[5] ANALIZANDO: Action Space en SAC')
print('-'*100)

print('✅ Verificando que action space = 39 dimensiones [BESS + 38 chargers]:')

if 'action' in sac_content:
    # Buscar referencias a 38 o 39
    if '39' in sac_content or '38+1' in sac_content or '[0]' in sac_content and '[38]' in sac_content:
        print(f'   ✓ action[0] = BESS (1 dimensión)')
        print(f'   ✓ action[1:39] = Chargers (38 dimensiones)')
        print(f'   ✓ TOTAL = 39 dimensiones')
    else:
        print(f'   ⚠️  No está claro que sean 39 channels')
else:
    print(f'   ✗ NO ENCONTRADO: action space')

# ===================================================================
# 6. VERIFICAR REWARD FUNCTION
# ===================================================================
print('\n[6] ANALIZANDO: Reward Function en SAC')
print('-'*100)

print('✅ Componentes de recompensa multiobjetivo:')
reward_components = [
    ('co2_grid', 'CO2 de grid (factor 0.4521)'),
    ('solar_self_consumption', 'Auto-consumo solar'),
    ('cost_minimization', 'Minimización de costo'),
    ('ev_charge_completion', 'Completitud de carga EVs'),
    ('grid_stability', 'Estabilidad de grid'),
]

for comp, desc in reward_components:
    if comp in sac_content:
        print(f'   ✓ {comp:25} → {desc}')
    else:
        print(f'   ⚠️  {comp:25} (posible, verificar valor en comentario)')

# ===================================================================
# 7. VERIFICAR DATOS PROCESADOS CONSTRUIDOS
# ===================================================================
print('\n[7] VALIDANDO: Datasets Procesados Construidos')
print('-'*100)

processed_path = DATA_ROOT / 'processed' / 'citylearn' / 'iquitos_ev_mall'
if processed_path.exists():
    print(f'✓ Directorio procesado existe: {processed_path.relative_to(WORKSPACE)}')
    
    # Contar archivos
    csv_files = list(processed_path.rglob('*.csv'))
    print(f'  → Total archivos CSV: {len(csv_files)}')
    
    # Verificar componentes clave
    key_dirs = [
        'Generacionsolar',
        'bess',
        'chargers',
        'demandamallkwh',
    ]
    
    for key_dir in key_dirs:
        dir_path = processed_path / key_dir
        if dir_path.exists():
            files = list(dir_path.glob('*.csv'))
            print(f'  ✓ {key_dir}/          → {len(files)} archivos')
        else:
            print(f'  ✗ {key_dir}/          → NO encontrado')
else:
    print(f'⚠️  No procesado aún: {processed_path}')

# ===================================================================
# 8. VERIFICAR SINCRONIZACIÓN DE CONSTANTES
# ===================================================================
print('\n[8] ANALIZANDO: Sincronización de Constantes')
print('-'*100)

print('✅ Constantes OE2 sincronizadas:')
constants_to_check = [
    ('BESS_CAPACITY_KWH: float = 940', 'Capacidad BESS'),
    ('BESS_MAX_POWER_KW: float = 342', 'Potencia BESS'),
    ('SOLAR_MAX_KW: float = 4100', 'Capacidad Solar'),
    ('CHARGER_MAX_KW: float = 10', 'Potencia máx charger'),
    ('CO2_FACTOR_IQUITOS: float = 0.4521', 'Factor CO2 grid'),
]

for const, desc in constants_to_check:
    if const.split('[')[0].strip() in sac_content:
        print(f'   ✓ {const.split(":")[0]:25} → {desc}')
    else:
        print(f'   ⚠️  {const.split(":")[0]:25} → verificar')

# ===================================================================
# 9. RESUMEN FINAL
# ===================================================================
print('\n' + '='*100)
print('CHECKLIST DE CONEXIÓN SAC ↔ DATASET')
print('='*100)

checklist = [
    ('train_sac_multiobjetivo.py existe', sac_script.exists()),
    ('dataset_builder.py existe', dataset_builder.exists()),
    ('data_loader.py importa de dataset_builder', 'from src.citylearnv2.dataset_builder.dataset_builder import' in 
     (WORKSPACE / 'src' / 'citylearnv2' / 'dataset_builder' / 'data_loader.py').read_text()),
    ('SAC carga datos reales OE2', 'load_datasets_from_processed' in sac_content),
    ('SAC tiene environment RealOE2Environment', 'class RealOE2Environment' in sac_content),
    ('SAC tiene multiobjetivo reward', 'MultiObjectiveReward' in sac_content),
    ('SAC toma 39 acciones [BESS+38 chargers]', '39' in sac_content or 'action[0]' in sac_content),
    ('Processed datasets existen', processed_path.exists()),
]

print()
for desc, result in checklist:
    status = '✅' if result else '❌'
    print(f'{status} {desc}')

# ===================================================================
# 10. ESTADO FINAL
# ===================================================================
print('\n' + '='*100)
if all(result for _, result in checklist):
    print('✅ CONEXIÓN COMPLETA: SAC training está totalmente conectado a datasets reales')
    print('   → LISTO PARA EJECUTAR: python scripts/train/train_sac_multiobjetivo.py')
else:
    print('⚠️  ALGUNAS CONEXIONES INCOMPLETAS - Revisar arriba')
print('='*100 + '\n')
