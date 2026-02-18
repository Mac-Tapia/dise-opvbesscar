#!/usr/bin/env python3
"""Análisis detallado de estructura de datos reales"""

import pandas as pd
import re

print('=' * 80)
print('ANÁLISIS DETALLADO - CHARGERS')
print('=' * 80)

chargers_df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
print(f'SHAPE: {chargers_df.shape}')
print(f'8760 filas (horas) x 1060 columnas')

print(f'\nPrimeras 20 NOMBRES DE COLUMNAS:')
for i, col in enumerate(chargers_df.columns[:20]):
    print(f'  {i:3d}: {col}')

print(f'\nColumnas 20-40:')
for i, col in enumerate(chargers_df.columns[20:40], start=20):
    print(f'  {i:3d}: {col}')

# Count sockets
socket_cols = [col for col in chargers_df.columns if 'socket_' in col]
print(f'\nTotal columnas con "socket_": {len(socket_cols)}')

# Extract unique socket IDs
socket_ids = set()
for col in chargers_df.columns:
    match = re.search(r'socket_(\d+)', col)
    if match:
        socket_ids.add(int(match.group(1)))

print(f'Socket IDs ÚNICOS: {sorted(socket_ids)}')
print(f'Total sockets: {len(socket_ids)}')

# Analizar cuántos parámetros por socket
params_per_socket = {}
for col in chargers_df.columns:
    match = re.search(r'socket_(\d+)_(.+)', col)
    if match:
        socket_id = int(match.group(1))
        param = match.group(2)
        if socket_id not in params_per_socket:
            params_per_socket[socket_id] = []
        params_per_socket[socket_id].append(param)

if params_per_socket:
    first_socket = min(params_per_socket.keys())
    print(f'\nParámetros por socket (socket_{first_socket:03d}): {len(params_per_socket[first_socket])}')
    print(f'  {params_per_socket[first_socket]}')

print('\n' + '=' * 80)
print('ANÁLISIS DETALLADO - BESS')
print('=' * 80)

bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
print(f'SHAPE: {bess_df.shape}')
print(f'\nTodas las COLUMNAS BESS:')
for i, col in enumerate(bess_df.columns):
    val = bess_df[col].iloc[0]
    print(f'  {i:2d}: {col:<40} = {val}')

# Look for capacity in specific columns
print(f'\n🔍 Buscando capacidad del BESS:')
capacity_cols = [col for col in bess_df.columns if 'capacity' in col.lower() or 'kwh' in col.lower()]
print(f'Columnas candidatas: {capacity_cols}')

print('\n' + '=' * 80)
print('RESUMEN')
print('=' * 80)
print(f'✅ Chargers: {len(socket_ids)} sockets')
print(f'✅ Parámetros por socket: ~{len(params_per_socket[first_socket]) if params_per_socket else 0}')
print(f'✅ Total columnas chargers: 1 (datetime) + {len(socket_ids)} sockets × ~{len(params_per_socket[first_socket]) if params_per_socket else 0} = ~{1 + len(socket_ids) * (len(params_per_socket[first_socket]) if params_per_socket else 0)}')
print(f'✅ BESS columnas: {len(bess_df.columns)}')
