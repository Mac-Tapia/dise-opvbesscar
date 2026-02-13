#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

print('='*100)
print('ANÁLISIS PROFUNDO: DATASET DE CHARGERS - VALIDAR ACTION SPACE')
print('='*100)
print()

# Load chargers dataset
charger_path = Path('data/processed/citylearn/iquitos_ev_mall/chargers/chargers_real_hourly_2024.csv')
df = pd.read_csv(charger_path)

print(f'Dataset: {charger_path}')
print(f'Dimensiones: {df.shape[0]} filas × {df.shape[1]} columnas')
print()

# Analyze columns
print('COLUMNAS DETECTADAS:')
print('-' * 100)
all_cols = list(df.columns)
print(f'\nTotal columnas: {len(all_cols)}')
print(f'\nPrimeras 15 columnas:')
for i, col in enumerate(all_cols[:15], 1):
    print(f'  {i:3d}. {col}')

print(f'\nÚltimas 10 columnas:')
for i, col in enumerate(all_cols[-10:], len(all_cols)-9):
    print(f'  {i:3d}. {col}')

# Classify columns
timestamp_cols = [c for c in all_cols if 'timestamp' in c.lower() or 'time' in c.lower() or 'fecha' in c.lower() or 'date' in c.lower()]
moto_cols = [c for c in all_cols if 'MOTO' in c and 'SOCKET' in c]
mototaxi_cols = [c for c in all_cols if 'MOTOTAXI' in c or 'TAXI' in c]
other_cols = [c for c in all_cols if c not in timestamp_cols and c not in moto_cols and c not in mototaxi_cols]

print()
print('CLASIFICACIÓN DE COLUMNAS:')
print('-' * 100)
print(f'Timestamp columns:        {len(timestamp_cols)}')
for col in timestamp_cols:
    print(f'  - {col}')

print(f'\nMoto SOCKET columns:      {len(moto_cols)}')
moto_nums = set()
for col in moto_cols:
    parts = col.split('_')
    if len(parts) >= 2:
        moto_num = parts[1]
        moto_nums.add(moto_num)

print(f'  Motos únicos: {len(moto_nums)}')
print(f'  Numeros: {sorted(list(moto_nums))}')
print(f'  Total SOCKET columns: {len(moto_cols)}')
print(f'  Muestra:')
for col in moto_cols[:8]:
    print(f'    - {col}')

print(f'\nMototaxi SOCKET columns:  {len(mototaxi_cols)}')
if mototaxi_cols:
    for col in mototaxi_cols[:8]:
        print(f'    - {col}')
else:
    print('  (NINGUNA)')

print(f'\nOther columns:            {len(other_cols)}')
if other_cols:
    for col in other_cols:
        print(f'    - {col}')

# Data statistics
print()
print('ESTADÍSTICAS DE DATOS:')
print('-' * 100)
print(f'Filas (timesteps):        {len(df)} (esperado 8760 para 1 año)')
print(f'Total columnas:           {df.shape[1]}')
print(f'Columnas de ACCIÓN:       {len(moto_cols) + len(mototaxi_cols)}')

# Sample data
print()
print('MUESTRA DE DATOS (primeras 2 filas):')
print('-' * 100)
print(df.iloc[:2].to_string())

# Data type and range
print()
print('RANGO Y TIPO DE DATOS (primeros 5 sockets):')
print('-' * 100)
for col in moto_cols[:5]:
    print(f'  {col:30s}: min={df[col].min():8.2f}, max={df[col].max():8.2f}, mean={df[col].mean():8.2f}')

# Summary
print()
print('='*100)
print('RESUMEN FINAL:')
print('='*100)
action_cols = len(moto_cols) + len(mototaxi_cols)
print(f'✓ Total Chargers (MOTO):    {len(moto_nums)} unidades')
print(f'✓ Total Sockets de Control: {action_cols}')
print(f'✓ Data Timesteps:           {len(df)} filas (hourly = 1 año)')
print(f'✓ ACTION SPACE PARA SAC:    ({action_cols},)')
print()
print(f'Validación v5.2:')
print(f'  - Config menciona: 19 cargadores × 2 tomas = 38 sockets')
print(f'  - Datos reales:    {len(moto_nums)} cargadores × {action_cols // len(moto_nums) if moto_nums else 0} tomas = {action_cols} sockets')
print()
