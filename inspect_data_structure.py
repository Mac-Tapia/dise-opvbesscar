#!/usr/bin/env python
"""Inspeccionar estructura real de archivos de datos OE2."""

import pandas as pd
import json
from pathlib import Path

print("=" * 80)
print("INSPECCIONANDO ESTRUCTURA DE DATOS OE2")
print("=" * 80)

# Cargar chargers
df_chargers = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
print('\n=== CHARGERS ===')
print(f'Shape: {df_chargers.shape} (filas, columnas)')
print(f'Primeras 10 columnas:')
for i, col in enumerate(df_chargers.columns[:10]):
    print(f'  [{i}] {col}')

print(f'\nÚltimas 10 columnas:')
for i, col in enumerate(df_chargers.columns[-10:], start=len(df_chargers.columns)-10):
    print(f'  [{i}] {col}')

# Buscar patrones
all_cols = list(df_chargers.columns)
moto_cols = [c for c in all_cols if 'moto' in c.lower()]
taxi_cols = [c for c in all_cols if 'taxi' in c.lower() or 'mototaxi' in c.lower()]
power_cols = []

# Intentar identificar columnas numéricas (sockets)
for col in df_chargers.columns[1:]:
    try:
        pd.to_numeric(df_chargers[col])
        power_cols.append(col)
    except:
        pass

print(f'\nColumnas numéricas (sockets): {len(power_cols)}')
print(f'Columnas con "moto": {len(moto_cols)}')
print(f'Columnas con "taxi": {len(taxi_cols)}')

if power_cols:
    print(f'\nPrimeros 5 sockets numéricos:')
    for col in power_cols[:5]:
        print(f'  {col}: max={df_chargers[col].max():.2f}, mean={df_chargers[col].mean():.2f}')

# Columnas no numéricas
print(f'\nColumnas NO numéricas (probablemente metadatos):')
for col in df_chargers.columns[:20]:
    try:
        pd.to_numeric(df_chargers[col])
    except:
        print(f'  {col}: valores únicos={df_chargers[col].nunique()}')
        if df_chargers[col].nunique() <= 10:
            print(f'    -> {df_chargers[col].unique().tolist()}')

# Cargar BESS
print('\n' + '=' * 80)
print('=== BESS ===')
df_bess = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
print(f'Shape: {df_bess.shape}')
print(f'Columnas: {list(df_bess.columns)}')

for col in df_bess.columns:
    if df_bess[col].dtype != 'object':
        print(f'  {col}: max={df_bess[col].max():.2f}, mean={df_bess[col].mean():.2f}')

# Cargar solar
print('\n' + '=' * 80)
print('=== SOLAR ===')
df_solar = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
print(f'Shape: {df_solar.shape}')
print(f'Columnas: {list(df_solar.columns)}')

for col in df_solar.columns:
    if df_solar[col].dtype != 'object':
        try:
            print(f'  {col}: max={df_solar[col].max():.2f}, mean={df_solar[col].mean():.2f}')
        except:
            pass

# Cargar mall
print('\n' + '=' * 80)
print('=== MALL ===')
df_mall = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv')
print(f'Shape: {df_mall.shape}')
print(f'Columnas: {list(df_mall.columns)}')

if len(df_mall.columns) > 0:
    for col in df_mall.columns:
        if df_mall[col].dtype != 'object':
            try:
                print(f'  {col}: max={df_mall[col].max():.2f}, mean={df_mall[col].mean():.2f}')
            except:
                pass

print("\n" + "=" * 80)
