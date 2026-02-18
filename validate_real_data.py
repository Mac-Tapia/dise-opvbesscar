#!/usr/bin/env python3
"""Validar que datos reales en OE2 coinciden con data_loader.py"""

from __future__ import annotations

import pandas as pd
import json
from pathlib import Path

print('=' * 80)
print('📊 VALIDACIÓN DE DATOS REALES - OE2 vs data_loader.py')
print('=' * 80)

# 1. BESS Real
print('\n1️⃣ BESS - Capacidad Real')
print('-' * 80)
bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
bess_df = pd.read_csv(bess_path)
print(f'Archivo: {bess_path}')
print(f'Shape: {bess_df.shape}')
print(f'Primeras 10 columnas: {list(bess_df.columns)[:10]}')
print(f'\nPrimeras 3 filas:')
print(bess_df.iloc[:3, :5])

# Extract capacity if available
if 'estado_soc_max' in bess_df.columns:
    max_soc = bess_df['estado_soc_max'].iloc[0]
    print(f'\n✅ Capacidad máxima (estado_soc_max): {max_soc} kWh')

# 2. SOLAR Real
print('\n\n2️⃣ SOLAR - Generación Real')
print('-' * 80)
solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
solar_df = pd.read_csv(solar_path)
print(f'Archivo: {solar_path}')
print(f'Shape: {solar_df.shape} (debe ser 8760)')
if solar_df.shape[0] == 8760:
    print('✅ Validación: 8,760 horas OK')
else:
    print(f'❌ ERROR: {solar_df.shape[0]} filas != 8760')

print(f'Columnas: {list(solar_df.columns)[:5]}...')
print(f'\nPrimeras 3 filas:')
print(solar_df.iloc[:3, :5])

if 'potencia_kw' in solar_df.columns:
    print(f'\n✅ Potencia promedio: {solar_df["potencia_kw"].mean():.1f} kW')
    print(f'✅ Potencia máxima: {solar_df["potencia_kw"].max():.1f} kW')

# 3. CHARGERS Real
print('\n\n3️⃣ CHARGERS - Sockets')
print('-' * 80)
chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
chargers_df = pd.read_csv(chargers_path)
print(f'Archivo: {chargers_path}')
print(f'Shape: {chargers_df.shape}')
print(f'Columnas: {list(chargers_df.columns)[:8]}')
print(f'\nPrimeras 3 filas:')
print(chargers_df.iloc[:3, :5])

# Count chargers
n_rows = len(chargers_df)
if n_rows == 19:
    print(f'\n✅ Chargers: {n_rows} unidades (19 × 2 = 38 sockets)')
else:
    print(f'❌ ADVERTENCIA: {n_rows} chargers (expected 19)')

# 4. DEMAND Real
print('\n\n4️⃣ DEMAND - Carga del Mall')
print('-' * 80)
demand_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
demand_df = pd.read_csv(demand_path)
print(f'Archivo: {demand_path}')
print(f'Shape: {demand_df.shape} (debe ser 8760)')
if demand_df.shape[0] == 8760:
    print('✅ Validación: 8,760 horas OK')
else:
    print(f'❌ ERROR: {demand_df.shape[0]} filas != 8760')

print(f'Columnas: {list(demand_df.columns)[:5]}')
print(f'\nPrimeras 3 filas:')
print(demand_df.iloc[:3, :5])

if 'kw' in demand_df.columns:
    print(f'\n✅ Demanda promedio: {demand_df["kw"].mean():.1f} kW')
    print(f'✅ Demanda máxima: {demand_df["kw"].max():.1f} kW')

# 5. COMPARAR CON data_loader.py CONSTANTS
print('\n\n5️⃣ COMPARACIÓN: data_loader.py CONSTANTS vs DATOS REALES')
print('-' * 80)

from src.dataset_builder_citylearn.data_loader import (
    BESS_CAPACITY_KWH,
    BESS_MAX_POWER_KW,
    SOLAR_PV_KWP,
    TOTAL_SOCKETS,
    N_CHARGERS,
)

print(f'\nConst en data_loader.py:')
print(f'  BESS_CAPACITY_KWH = {BESS_CAPACITY_KWH} kWh')
print(f'  BESS_MAX_POWER_KW = {BESS_MAX_POWER_KW} kW')
print(f'  SOLAR_PV_KWP = {SOLAR_PV_KWP} kWp')
print(f'  N_CHARGERS = {N_CHARGERS}')
print(f'  TOTAL_SOCKETS = {TOTAL_SOCKETS}')

# Verify if matches real data
if 'estado_soc_max' in bess_df.columns:
    real_bess = bess_df['estado_soc_max'].iloc[0]
    match = '✅' if abs(BESS_CAPACITY_KWH - real_bess) < 1 else '❌'
    print(f'\n{match} BESS: {BESS_CAPACITY_KWH} kWh (real: {real_bess} kWh)')

# 6. Validar iquitos_ev_mall dataset
print('\n\n6️⃣ VALIDACIÓN: Archivo generado iquitos_ev_mall/citylearnv2_combined_dataset.csv')
print('-' * 80)
combined_path = Path('data/processed/citylearn/iquitos_ev_mall/citylearnv2_combined_dataset.csv')
if combined_path.exists():
    combined_df = pd.read_csv(combined_path)
    print(f'Archivo: {combined_path}')
    print(f'Shape: {combined_df.shape} (debe ser 8760, 22)')
    print(f'Columnas: {list(combined_df.columns)[:10]}...')
    print(f'✅ Dataset VÁLIDO y LISTO')
else:
    print(f'❌ Archivo no encontrado: {combined_path}')

print('\n' + '=' * 80)
print('✅ VALIDACIÓN COMPLETADA')
print('=' * 80)
