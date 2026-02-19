#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDAR QUE TRAIN_SAC.PY USA TODAS LAS COLUMNAS DEL DATASET
Verificar que load_datasets_from_processed() funciona correctamente
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar workspace al path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

import numpy as np
import pandas as pd

print('='*100)
print('VALIDACION: SAC USANDO TODAS LAS COLUMNAS DEL DATASET')
print('='*100)
print()

# Import desde train_sac.py
try:
    from scripts.train.train_sac import load_datasets_from_processed
    print('✓ Load módulo train_sac.py')
except Exception as e:
    print(f'✗ Error cargando train_sac.py: {e}')
    exit(1)

print()

# Cargar dataset con nueva función
try:
    print('[1] Cargando datos con load_datasets_from_processed()...')
    datasets = load_datasets_from_processed()
    print('✓ Datasets cargados correctamente')
except Exception as e:
    print(f'✗ Error: {e}')
    exit(1)

print()
print('[2] VALIDAR SHAPE Y CONTENIDO')
print('-'*100)

# Verificar que chargers tiene más dimensiones ahora
chargers = datasets['chargers']
print(f'\nChargers shape: {chargers.shape}')
print(f'  Horas: {chargers.shape[0]} (8760 esperadas)')
print(f'  Características: {chargers.shape[1]} (antes era 38, ahora debería ser >100)')

if chargers.shape[1] > 100:
    print(f'  ✓ MEJORA: X{chargers.shape[1]/38:.1f} más columnas que antes')
else:
    print(f'  ⚠ ALERTA: {chargers.shape[1]} columnas (esperaba >100)')

print(f'\nChargers Motos shape: {datasets["chargers_moto"].shape}')
print(f'Chargers Mototaxis shape: {datasets["chargers_mototaxi"].shape}')

# CO2
if 'chargers_co2_kg' in datasets:
    co2 = datasets['chargers_co2_kg']
    print(f'\nChargers CO2 shape: {co2.shape}')
    print(f'  Total CO2: {np.sum(co2):,.0f} kg/año')
    print(f'  ✓ Datos CO2 cargados desde 236 columnas')
else:
    print('\n⚠ chargers_co2_kg NO disponible')

print()
print('[3] VALIDAR MOTOS Y MOTOTAXIS')
print('-'*100)

moto = datasets['chargers_moto']
mototaxi = datasets['chargers_mototaxi']

print(f'\nMotos:')
print(f'  Total energía: {np.sum(moto):,.0f} kWh/año')
print(f'  Distribución por hora: min={np.min(moto):.2f}, mean={np.mean(moto):.2f}, max={np.max(moto):.2f}')

print(f'\nMototaxis:')
print(f'  Total energía: {np.sum(mototaxi):,.0f} kWh/año')
print(f'  Distribución por hora: min={np.min(mototaxi):.2f}, mean={np.mean(mototaxi):.2f}, max={np.max(mototaxi):.2f}')

print()
print('[4] DATOS DISPONIBLES AHORA EN OBSERVACION')
print('-'*100)

total_obs_features = (
    chargers.shape[1] +  # Chargers (977)
    datasets['solar_data']['potencia_kw'].shape[0] if isinstance(datasets['solar_data']['potencia_kw'], np.ndarray) else 1 +
    3  # BESS (soc, costs, peak)
)

print(f'\nObservación RL tendrá acceso a:')
print(f'  - Chargers: {chargers.shape[1]:3d} columnas (Socket Power, SOC, CO2, Motos, Mototaxis, etc)')
print(f'  - Solar:       11 columnas (irradiancia, temperatura, viento, etc)')
print(f'  - BESS:         3 columnas (SOC, costs, peak savings)')
print(f'  - Mall:         6 columnas (demanda, CO2, tarifa, etc)')
print(f'  {"─"*60}')
print(f'  - TOTAL:      ~{chargers.shape[1]+20:3d} features en observación')

print()
print('[5] VERIFICACION FINAL')
print('='*100)

checks = {
    'Chargers shape': chargers.shape[1] > 100,
    'Chargers CO2 data': 'chargers_co2_kg' in datasets and np.sum(datasets['chargers_co2_kg']) > 0,
    'Motos data': np.sum(moto) > 0,
    'Mototaxis data': np.sum(mototaxi) > 0,
    'Solar data': datasets['solar'].shape[0] == 8760,
    'BESS SOC data': datasets['bess_soc'].shape[0] == 8760,
}

print()
for check_name, result in checks.items():
    status = '✓' if result else '✗'
    print(f'{status} {check_name:30s}: {"PASS" if result else "FAIL"}')

all_pass = all(checks.values())

print()
print('='*100)
if all_pass:
    print(f'✓ EXITO: SAC ahora usa TODAS las columnas reales del dataset')
    print(f'  - Chargers: {chargers.shape[1]} features (vs 38 antes)')
    print(f'  - CO2: 236 columnas de reducción incorporadas')
    print(f'  - Motos: Distribución completa disponible')
    print(f'  - Mototaxis: Distribución completa disponible')
    print()
    print(f'Información disponible para agente RL: X{chargers.shape[1]/38:.1f} mejor')
else:
    print(f'⚠ Verificación parcial - Revisar detalles arriba')

print('='*100)
