#!/usr/bin/env python
"""Verify CityLearn v2 dataset completeness"""

import json
from pathlib import Path
import pandas as pd

city_learn_dir = Path('data/oe2/citylearn')
required_files = ['bess_schema_params.json', 'bess_solar_generation.csv', 'building_load.csv']

print('=== VERIFICACION DE ARCHIVOS CITYLEARN v2 ===\n')
for file in required_files:
    path = city_learn_dir / file
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    status = '✅' if exists else '❌'
    print(f'{status} {file}: {size:,} bytes')

# Cargar y validar estructura
print('\n=== VALIDACION DE ESTRUCTURA ===\n')

# BESS Config
with open(city_learn_dir / 'bess_schema_params.json') as f:
    params = json.load(f)
    print('✅ BESS Config loaded:')
    cap = params['electrical_storage']['capacity']
    pow = params['electrical_storage']['nominal_power']
    eff = params['electrical_storage']['efficiency']
    print(f'   - Capacity: {cap} kWh')
    print(f'   - Power: {pow} kW')
    print(f'   - Efficiency: {eff*100}%')

# Solar data
solar = pd.read_csv(city_learn_dir / 'bess_solar_generation.csv')
print(f'\n✅ Solar Generation:')
print(f'   - Filas: {len(solar)}')
print(f'   - Min: {solar["solar_generation"].min():.1f} kW')
print(f'   - Max: {solar["solar_generation"].max():.1f} kW')
print(f'   - Media: {solar["solar_generation"].mean():.1f} kW')

# Load data
load = pd.read_csv(city_learn_dir / 'building_load.csv')
print(f'\n✅ Building Load (Mall):')
print(f'   - Filas: {len(load)}')
print(f'   - Min: {load["non_shiftable_load"].min():.1f} kW')
print(f'   - Max: {load["non_shiftable_load"].max():.1f} kW')
print(f'   - Media: {load["non_shiftable_load"].mean():.1f} kW')
print(f'   - Total anual: {load["non_shiftable_load"].sum():.0f} kWh')

print('\n=== LISTO PARA TRAINING RL ===')
print('✅ CityLearn v2 environment puede entrenarse con estos datos')
print('\nPróximos pasos:')
print('1. Entrenar agentes RL (SAC/PPO/A2C) con estos datos')
print('2. Comparar mejora vs baseline (sin BESS)')
print('3. Analizar CO2 reducido y autoconsumo solar')
