#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALISIS DETALLADO DE ESTRUCTURA CHARGERS.CSV
Para actualizar train_sac.py con TODAS las columnas
"""
import pandas as pd
from pathlib import Path
import numpy as np

dataset_path = Path('data/iquitos_ev_mall')
chargers_path = dataset_path / 'chargers_timeseries.csv'

df = pd.read_csv(chargers_path)

print('='*100)
print('ESTRUCTURA DETALLADA DE CHARGERS_TIMESERIES.CSV')
print('='*100)
print()

# 1. Categorías de columnas
print('[1] CATEGORIZACIÓN DE COLUMNAS')
print('-'*100)

datetime_cols = [c for c in df.columns if 'datetime' in c.lower() or 'time' in c.lower()]
socket_power_cols = [c for c in df.columns if 'socket' in c.lower() and 'power' in c.lower()]
socket_soc_cols = [c for c in df.columns if 'socket' in c.lower() and 'soc' in c.lower()]
socket_battery_cols = [c for c in df.columns if 'socket' in c.lower() and 'battery' in c.lower()]
co2_cols = [c for c in df.columns if 'co2' in c.lower()]
moto_cols = [c for c in df.columns if 'motos' in c.lower() and 'taxi' not in c.lower()]
mototaxi_cols = [c for c in df.columns if 'mototaxi' in c.lower() or ('taxi' in c.lower() and 'motos' not in c.lower())]
charger_cols = [c for c in df.columns if 'cargador' in c.lower() and 'socket' not in c.lower()]
energy_cols = [c for c in df.columns if 'energia' in c.lower() or 'energy' in c.lower()]
other_cols = [c for c in df.columns if c not in 
             datetime_cols + socket_power_cols + socket_soc_cols + socket_battery_cols +
             co2_cols + moto_cols + mototaxi_cols + charger_cols + energy_cols]

print(f'DateTime:              {len(datetime_cols):3d} columnas')
print(f'Socket Power:          {len(socket_power_cols):3d} columnas')
print(f'Socket SOC:            {len(socket_soc_cols):3d} columnas')
print(f'Socket Battery:        {len(socket_battery_cols):3d} columnas')
print(f'CO2:                   {len(co2_cols):3d} columnas')
print(f'Motos:                 {len(moto_cols):3d} columnas')
print(f'Mototaxis:             {len(mototaxi_cols):3d} columnas')
print(f'Chargers (agregados):  {len(charger_cols):3d} columnas')
print(f'Energía:               {len(energy_cols):3d} columnas')
print(f'Otros:                 {len(other_cols):3d} columnas')
print(f'{"─"*60}')
print(f'TOTAL:                 {df.shape[1]:3d} columnas')
print()

# 2. Análisis de sockets
print('[2] ANÁLISIS DE SOCKETS INDIVIDUALES')
print('-'*100)

socket_ids = set()
for col in df.columns:
    if 'socket_' in col.lower():
        parts = col.lower().split('socket_')
        if len(parts) > 1:
            sock_id = parts[1].split('_')[0]
            try:
                socket_ids.add(int(sock_id))
            except:
                pass

print(f'Total sockets únicos detectados: {len(socket_ids)}')
print(f'Socket IDs: {sorted(list(socket_ids))[:20]}...')
print()

# 3. Columnas por socket
print('[3] COLUMNAS POR SOCKET (ejemplo socket_000)')
print('-'*100)

socket_000_cols = [c for c in df.columns if 'socket_000' in c.lower()]
print(f'Socket 000 tiene {len(socket_000_cols)} columnas:')
for col in socket_000_cols:
    print(f'  - {col}')
print()

# 4. Análisis numérico vs categórico
print('[4] TIPOS DE DATOS')
print('-'*100)

dtypes_count = df.dtypes.value_counts()
for dtype, count in dtypes_count.items():
    print(f'  {str(dtype):20s}: {count:3d} columnas')

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
print(f'\nColumnas numéricas: {len(numeric_cols)}')
print()

# 5. Columnas recomendadas para observación
print('[5] COLUMNAS RECOMENDADAS PARA USAR EN OBSERVATION')
print('-'*100)

key_cols = socket_power_cols + socket_soc_cols + co2_cols + moto_cols + mototaxi_cols

print(f'\nRecomendadas para RL observation ({len(key_cols)} columnas):')
print(f'  - Socket Power (${len(socket_power_cols)} columnas) - Potencia actual cargada')
print(f'  - Socket SOC (${len(socket_soc_cols)} columnas) - Estado de carga de baterías')
print(f'  - CO2 Reducción (${len(co2_cols)} columnas) - Impacto ambiental por fuente')
print(f'  - Motos (${len(moto_cols)} columnas) - Métricas agregadas motos')
print(f'  - Mototaxis (${len(mototaxi_cols)} columnas) - Métricas agregadas mototaxis')
print()

# 6. Estadísticas
print('[6] ESTADÍSTICAS DE VALORES')
print('-'*100)

print(f'\nPrimeras 5 socket_power_cols:')
for col in socket_power_cols[:5]:
    print(f'  {col}: min={df[col].min():.2f}, mean={df[col].mean():.2f}, max={df[col].max():.2f}')

print(f'\nPrimeras 5 co2_cols:')
for col in co2_cols[:5]:
    print(f'  {col}: min={df[col].min():.2f}, mean={df[col].mean():.2f}, max={df[col].max():.2f}')

print()
print('='*100)
print('RECOMENDACIÓN FINAL:')
print('='*100)
print(f'''
En lugar de usar solo 38 sockets, usar TODAS las columnas:

chargers_timeseries = df[{len(numeric_cols)} columnas numéricas]
Dimensión: (8760 horas, {len(numeric_cols)} features)

Esto da al agente X{len(numeric_cols)/38:.1f} más información de entrada.

Estructura recomendada:
  chargers_data['socket_power'] = (8760, {len(socket_power_cols)})  # Potencia actual
  chargers_data['socket_soc'] = (8760, {len(socket_soc_cols)})      # Estado carga
  chargers_data['co2_avoided'] = (8760, {len(co2_cols)})            # CO2 por socket
  chargers_data['motos_metrics'] = (8760, {len(moto_cols)})         # Métricas motos
  chargers_data['mototaxis_metrics'] = (8760, {len(mototaxi_cols)}) # Métricas mototaxis

TOTAL OBSERVATION: {len(numeric_cols):,} features por timestep
''')
