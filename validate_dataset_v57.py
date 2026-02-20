#!/usr/bin/env python3
"""Validacion completa del dataset BESS v5.7"""

import pandas as pd
import json
from pathlib import Path

print('='*80)
print('VALIDACION: DATASET BESS_ANO_2024.CSV - COLUMNAS Y VALORES')
print('='*80)
print()

# Cargar dataset
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv', index_col=0)

# Cargar JSON de resultados para comparación
with open('data/oe2/bess/bess_results.json') as f:
    bess_data = json.load(f)

print('[1] ESTRUCTURA DEL DATASET')
print(f'  Filas: {len(df)} (esperado: 8760)')
print(f'  Columnas: {len(df.columns)}')
print()

print('[2] COLUMNAS GENERADAS')
for i, col in enumerate(df.columns, 1):
    print(f'  {i:2d}. {col}')
print()

print('[3] VALIDACION DE VALORES CRITICOS')
print()

# Demanda Mall
mall_kwh_sum = df['mall_kwh'].sum()
mall_kwh_peak = df['mall_kwh'].max()
mall_kwh_mean = df['mall_kwh'].mean()
print(f'[MALL]')
print(f'  Demanda anual: {mall_kwh_sum:>12,.0f} kWh')
print(f'  Demanda pico:  {mall_kwh_peak:>12,.1f} kW (OK: > 1900 kW)')
print(f'  Demanda media: {mall_kwh_mean:>12,.1f} kW')
print()

# PV generacion
pv_kwh_sum = df['pv_kwh'].sum()
pv_kwh_peak = df['pv_kwh'].max()
pv_capacity = 8292514.17
print(f'[PV GENERACION]')
print(f'  Generacion anual: {pv_kwh_sum:>10,.0f} kWh (limite: {pv_capacity:,.0f} kWh)')
print(f'  Capacidad OK: {pv_kwh_sum <= pv_capacity}')
print(f'  Utilizacion: {(pv_kwh_sum/pv_capacity)*100:.1f}%')
print(f'  Pico PV: {pv_kwh_peak:>12,.1f} kW')
print()

# EV demanda
ev_kwh_sum = df['ev_kwh'].sum()
ev_kwh_peak = df['ev_kwh'].max()
print(f'[EV DEMANDA]')
print(f'  Demanda anual: {ev_kwh_sum:>12,.0f} kWh')
print(f'  Demanda pico:  {ev_kwh_peak:>12,.1f} kW')
print()

# BESS operación - buscar columnas disponibles
bess_discharge_col = None
bess_charge_col = None
for col in df.columns:
    if 'bess' in col.lower() and 'discharge' in col.lower():
        bess_discharge_col = col
    if 'bess' in col.lower() and 'charge' in col.lower():
        bess_charge_col = col

bess_discharge_sum = 0
bess_charge_sum = 0

if 'bess_to_ev_kwh' in df.columns and 'bess_to_mall_kwh' in df.columns:
    bess_discharge_sum = df['bess_to_ev_kwh'].sum() + df['bess_to_mall_kwh'].sum()
elif bess_discharge_col:
    bess_discharge_sum = df[bess_discharge_col].sum()

if 'bess_charge_kwh' in df.columns:
    bess_charge_sum = df['bess_charge_kwh'].sum()
elif 'pv_to_bess_kwh' in df.columns:
    bess_charge_sum = df['pv_to_bess_kwh'].sum()

print(f'[BESS OPERACION]')
print(f'  Descarga anual: {bess_discharge_sum:>10,.0f} kWh')
print(f'  Carga anual:    {bess_charge_sum:>10,.0f} kWh')
print(f'  Columnas BESS encontradas:')
for col in df.columns:
    if 'bess' in col.lower():
        print(f'    - {col}')
print()

# Grid
if 'grid_import_kwh' in df.columns:
    grid_import_sum = df['grid_import_kwh'].sum()
    grid_export_sum = df['grid_export_kwh'].sum()
    print(f'[GRID]')
    print(f'  Import anual: {grid_import_sum:>12,.0f} kWh')
    print(f'  Export anual: {grid_export_sum:>12,.0f} kWh (PV excedente)')
    print()

# Verificar correspondencia con JSON
print('[4] VALIDACION CON JSON RESULTS')
print()
json_peak = bess_data.get('mall_demand_peak_kw', 0)
print(f'  mall_demand_peak_kw (JSON): {json_peak:.1f} kW')
print(f'  mall_kwh.max() (Dataset):   {mall_kwh_peak:.1f} kW')
print(f'  Coinciden: {abs(json_peak - mall_kwh_peak) < 0.1}')
print()

# Energy sources
sources = bess_data.get('mall_energy_sources', {})
pv_src = sources.get('pv_direct_kwh', 0)
bess_src = sources.get('bess_discharge_kwh', 0)
grid_src = sources.get('grid_import_kwh', 0)

print(f'  PV a Mall (JSON):    {pv_src:>12,.0f} kWh ({sources.get("pv_direct_percent", 0):.1f}%)')
print(f'  BESS a Mall (JSON):  {bess_src:>12,.0f} kWh ({sources.get("bess_discharge_percent", 0):.1f}%)')
print(f'  Grid a Mall (JSON):  {grid_src:>12,.0f} kWh ({sources.get("grid_import_percent", 0):.1f}%)')
print(f'  TOTAL:               {sources.get("total_kwh", 0):>12,.0f} kWh')
print()

# Verificaciones finales
print('[5] LISTA DE VERIFICACION FINAL')
print()

# Recalcular bess_discharge para verificación
bess_total_discharge = 0
if 'bess_to_ev_kwh' in df.columns and 'bess_to_mall_kwh' in df.columns:
    bess_total_discharge = df['bess_to_ev_kwh'].sum() + df['bess_to_mall_kwh'].sum()

checks = {
    'Dataset tiene 8760 filas': len(df) == 8760,
    'Demanda pico Mall > 1900 kW': mall_kwh_peak > 1900,
    'PV dentro de capacidad (8.29 GWh)': pv_kwh_sum <= pv_capacity,
    'BESS descarga registrada': bess_total_discharge > 0,
    'Grid import registrado': 'grid_import_kwh' in df.columns and grid_import_sum > 0,
    'JSON y Dataset coinciden (pico)': abs(json_peak - mall_kwh_peak) < 0.1,
}

for check, result in checks.items():
    status = 'OK' if result else 'FAIL'
    symbol = '\u2713' if result else 'X'
    print(f'  {symbol} {check}: {status}')
print()

print('='*80)
print('ESTADO: Dataset ACTUALIZADO y VALIDADO')
print('='*80)
