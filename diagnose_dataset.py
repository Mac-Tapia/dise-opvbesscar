import pandas as pd
import numpy as np

# Cargar dataset BESS original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print('=' * 80)
print('DIAGNÓSTICO: Dataset BESS Original')
print('=' * 80)
print(f'\nDimensiones: {df.shape}')
print(f'Filas: {len(df)}, Columnas: {len(df.columns)}')

# Revisar columnas
print('\nColumnas disponibles:')
for i, col in enumerate(df.columns, 1):
    print(f'  {i:2d}. {col}')

# Verificar datos críticos
print('\n' + '=' * 80)
print('DATOS CRÍTICOS')
print('=' * 80)

if 'bess_discharge_kwh' in df.columns:
    descarga = df['bess_discharge_kwh'].sum()
    print(f'Descarga BESS total: {descarga:,.0f} kWh')
    print(f'  - Horas con descarga: {(df["bess_discharge_kwh"] > 0).sum()}')
else:
    print('ERROR: Columna bess_discharge_kwh NO existe')
    cols_bess = [c for c in df.columns if 'discharge' in c.lower() or 'bess' in c.lower()]
    print(f'Columnas BESS encontradas: {cols_bess}')

if 'pv_generation_kwh' in df.columns:
    pv = df['pv_generation_kwh'].sum()
    print(f'Generación PV total: {pv:,.0f} kWh')
    print(f'  - PV máximo: {df["pv_generation_kwh"].max():,.0f} kW')
    print(f'  - PV mínimo: {df["pv_generation_kwh"].min():,.0f} kW')
elif 'pv_kwh' in df.columns:
    pv = df['pv_kwh'].sum()
    print(f'Generación PV total: {pv:,.0f} kWh')
else:
    print('ERROR: Columna PV NO existe')
    print('Columnas que contienen PV:', [c for c in df.columns if 'pv' in c.lower()])

# Primeras 5 filas
print('\nPrimeras 5 filas del dataset:')
print(df.head())

print('\nÚltimas 5 filas del dataset:')
print(df.tail())
