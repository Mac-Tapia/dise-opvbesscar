#!/usr/bin/env python3
"""
Verificar que SAC está usando TODAS las columnas CO2 y de vehículos disponibles.
"""

import pandas as pd
from pathlib import Path
import numpy as np

dataset_base = Path('data/iquitos_ev_mall')

print("="*110)
print("✅ VALIDACIÓN DE USO DE COLUMNAS EN TRAIN_SAC.PY")
print("="*110)
print()

# Cargar datasets
print("[1] CARGAR TODOS LOS DATOS DEL DATASET")
print("-"*110)

df_chargers = pd.read_csv(dataset_base / 'chargers_timeseries.csv')
df_mall = pd.read_csv(dataset_base / 'mall_demand.csv')
df_bess = pd.read_csv(dataset_base / 'bess_timeseries.csv')
df_solar = pd.read_csv(dataset_base / 'solar_generation.csv')

print(f"✓ CHARGERS: {df_chargers.shape[0]} filas × {df_chargers.shape[1]} columnas")
print(f"✓ MALL:     {df_mall.shape[0]} filas × {df_mall.shape[1]} columnas")
print(f"✓ BESS:     {df_bess.shape[0]} filas × {df_bess.shape[1]} columnas")
print(f"✓ SOLAR:    {df_solar.shape[0]} filas × {df_solar.shape[1]} columnas")
print()

# Identificar columnas por categoría
print("[2] IDENTIFICAR COLUMNAS DISPONIBLES")
print("-"*110)

# COLUMNAS CO2
co2_chargers = [c for c in df_chargers.columns if 'co2' in c.lower()]
co2_mall = [c for c in df_mall.columns if 'co2' in c.lower()]
co2_bess = [c for c in df_bess.columns if 'co2' in c.lower()]
co2_solar = [c for c in df_solar.columns if 'co2' in c.lower() or 'reduccion' in c.lower()]

print(f"COLUMNAS CO2 DISPONIBLES:")
print(f"  CHARGERS: {len(co2_chargers)} columnas")
for col in co2_chargers[:5]:
    valor = df_chargers[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f}")
print(f"    ... (+{len(co2_chargers)-5} columnas más)")
print()

print(f"  MALL: {len(co2_mall)} columnas")
for col in co2_mall:
    valor = df_mall[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f}")
print()

print(f"  BESS: {len(co2_bess)} columnas")
for col in co2_bess:
    valor = df_bess[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f}")
print()

print(f"  SOLAR: {len(co2_solar)} columnas")
for col in co2_solar:
    valor = df_solar[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f}")
print()

# COLUMNAS VEHÍCULOS
vehicle_cols = [c for c in df_chargers.columns if any(x in c.lower() for x in ['moto', 'taxi', 'ev_energia', 'cargada', 'acumulado'])]
print(f"COLUMNAS DE VEHÍCULOS DISPONIBLES:")
print(f"  TOTAL: {len(vehicle_cols)} columnas")
for col in vehicle_cols[:15]:
    valor = df_chargers[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f}")
print(f"    ... (+{len(vehicle_cols)-15} columnas más)")
print()

# COLUMNAS SOCKETS
socket_power_cols = [c for c in df_chargers.columns if 'socket_' in c and 'power' in c.lower()]
socket_co2_cols = [c for c in df_chargers.columns if 'socket_' in c and 'co2' in c.lower()]

print(f"COLUMNAS DE SOCKETS (38 SOCKETS):")
print(f"  Power: {len(socket_power_cols)} columnas")
for col in socket_power_cols[:5]:
    valor = df_chargers[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f} kW")
print(f"    ... (+{len(socket_power_cols)-5} columnas más)")
print()

print(f"  CO2 per Socket: {len(socket_co2_cols)} columnas")
for col in socket_co2_cols[:5]:
    valor = df_chargers[col].iloc[0]
    print(f"    ✓ {col:<45} = {valor:.2f} kg")
print(f"    ... (+{len(socket_co2_cols)-5} columnas más)")
print()

# Validación cruzada: motos vs mototaxis
print("[3] VALIDAR SEPARACIÓN MOTOS vs MOTOTAXIS")
print("-"*110)

motos_energy_col = [c for c in df_chargers.columns if c == 'ev_energia_motos_kwh']
mototaxis_energy_col = [c for c in df_chargers.columns if c == 'ev_energia_mototaxis_kwh']
motos_co2_col = [c for c in df_chargers.columns if c == 'co2_reduccion_motos_kg']
mototaxis_co2_col = [c for c in df_chargers.columns if c == 'co2_reduccion_mototaxis_kg']

if motos_energy_col:
    motos_energy = df_chargers[motos_energy_col[0]].sum()
    print(f"✓ Motos - Energía total anual: {motos_energy:,.1f} kWh")
    
if mototaxis_energy_col:
    mototaxis_energy = df_chargers[mototaxis_energy_col[0]].sum()
    print(f"✓ Mototaxis - Energía total anual: {mototaxis_energy:,.1f} kWh")

if motos_co2_col:
    motos_co2 = df_chargers[motos_co2_col[0]].sum()
    print(f"✓ Motos - CO2 evitado anual: {motos_co2:,.1f} kg")
    
if mototaxis_co2_col:
    mototaxis_co2 = df_chargers[mototaxis_co2_col[0]].sum()
    print(f"✓ Mototaxis - CO2 evitado anual: {mototaxis_co2:,.1f} kg")

print()

# Validar que train_sac.py está usando estos datos
print("[4] DATOS USADOS EN train_sac.py (SEGÚN CÓDIGO ACTUAL)")
print("-"*110)

# Leer train_sac.py para ver qué columnas carga
train_sac_path = Path('scripts/train/train_sac.py')
if train_sac_path.exists():
    with open(train_sac_path) as f:
        code = f.read()
    
    # Buscar qué se carga en load_datasets_from_processed
    if 'chargers_hourly' in code:
        print("✓ Carga chargers_hourly")
    if 'solar_hourly' in code:
        print("✓ Carga solar_hourly")
    if 'mall_hourly' in code:
        print("✓ Carga mall_hourly")
    if 'bess_soc' in code:
        print("✓ Carga bess_soc")
    
    # Buscar dimensiones
    import re
    match = re.search(r'chargers_hourly\[:.*?,\s*:(\d+)\]', code)
    if match:
        n_sockets = int(match.group(1))
        print(f"  → Cargando {n_sockets} sockets del dataset")
    
    print()
    print("⚠️  PROBLEMA IDENTIFICADO:")
    print("-"*110)
    print("El código en load_datasets_from_processed() está:")
    print("  ❌ Solo extrayendo potencia por socket (chargers_hourly)")
    print("  ❌ NO está cargando: co2_reduccion_motos_kg")
    print("  ❌ NO está cargando: co2_reduccion_mototaxis_kg")
    print("  ❌ NO está cargando: motos_cargadas_hora")
    print("  ❌ NO está cargando: mototaxis_cargadas_hora")
    print("  ❌ NO está cargando: mall_co2_indirect_kg")
    print("  ❌ NO está cargando: co2_avoided_indirect_kg (BESS)")
    print()
    print("✅ SOLUCIÓN REQUERIDA:")
    print("-"*110)
    print("Modificar load_datasets_from_processed() para incluir:")
    print("  → co2_reduccion_motos_kg")
    print("  → co2_reduccion_mototaxis_kg")
    print("  → motos_cargadas_hora")
    print("  → mototaxis_cargadas_hora")
    print("  → mall_co2_indirect_kg")
    print("  → co2_avoided_indirect_kg")
    print()

print("="*110)
