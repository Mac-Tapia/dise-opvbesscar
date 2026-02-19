#!/usr/bin/env python3
"""Validar que el dataset tenga todas las columnas CO2 y vehículos necesarias."""

import pandas as pd
from pathlib import Path
import json

dataset_base = Path('data/iquitos_ev_mall')

print("="*100)
print("🔍 VALIDACIÓN DE COLUMNAS CO2 Y VEHÍCULOS EN DATASET")
print("="*100)
print()

# 1. CHARGERS - Buscar columnas CO2 y vehículos
print("1️⃣ CHARGERS_TIMESERIES.CSV")
print("-"*100)
chargers_path = dataset_base / 'chargers_timeseries.csv'
if chargers_path.exists():
    df_chargers = pd.read_csv(chargers_path, nrows=2)
    all_cols = list(df_chargers.columns)
    
    # Filtrar columnas importantes
    co2_cols = [c for c in all_cols if 'co2' in c.lower()]
    vehicle_cols = [c for c in all_cols if 'vehicle' in c.lower() or 'moto' in c.lower() or 'taxi' in c.lower()]
    socket_cols = [c for c in all_cols if 'socket' in c.lower()]
    
    print(f"  Total columnas: {len(all_cols)}")
    print(f"  Columnas CO2: {len(co2_cols)}")
    if co2_cols:
        for col in co2_cols[:10]:
            print(f"    ✓ {col}")
    else:
        print(f"    ❌ NO HAY COLUMNAS CO2 EN CHARGERS")
    
    print(f"  Columnas Vehicle/Moto: {len(vehicle_cols)}")
    if vehicle_cols:
        for col in vehicle_cols[:10]:
            print(f"    ✓ {col}")
    
    print(f"  Columnas Socket: {len(socket_cols)} (motos 1-30, mototaxis 31-38)")
    
    # Muestra datos reales
    print(f"\n  Primeras filas de datos:")
    print(df_chargers[socket_cols[:5]].iloc[0] if socket_cols else "No hay socket cols")
    print()

# 2. CHARGERS DATA (JSON) - revisar metadatos
print("2️⃣ CHARGERS JSON METADATA")
print("-"*100)
chargers_json_path = Path('data/interim/oe2/chargers/chargers_individual_descriptive.json')
if chargers_json_path.exists():
    with open(chargers_json_path) as f:
        chargers_meta = json.load(f)
    print(f"  Chargers definidos en JSON: {len(chargers_meta)}")
    if chargers_meta:
        first_key = list(chargers_meta.keys())[0]
        print(f"  Ejemplo (charger_0): {chargers_meta[first_key]}")
else:
    print(f"  ❌ NO EXISTE: {chargers_json_path}")
print()

# 3. MALL DEMAND - Buscar columnas
print("3️⃣ MALL_DEMAND.CSV")
print("-"*100)
mall_path = dataset_base / 'mall_demand.csv'
if mall_path.exists():
    df_mall = pd.read_csv(mall_path, nrows=2)
    all_cols = list(df_mall.columns)
    
    co2_cols = [c for c in all_cols if 'co2' in c.lower()]
    demand_cols = [c for c in all_cols if 'demand' in c.lower() or 'kwh' in c.lower() or 'kw' in c.lower()]
    
    print(f"  Total columnas: {len(all_cols)}")
    print(f"  Columnas CO2: {co2_cols if co2_cols else '❌ NINGUNA'}")
    print(f"  Columnas Demand: {demand_cols}")
    print(f"  Datos de ejemplo:")
    print(f"    {df_mall.iloc[0].to_dict()}")
else:
    print(f"  ❌ NO EXISTE: {mall_path}")
print()

# 4. BESS TIMESERIES - Buscar columnas
print("4️⃣ BESS_TIMESERIES.CSV")
print("-"*100)
bess_path = dataset_base / 'bess_timeseries.csv'
if bess_path.exists():
    df_bess = pd.read_csv(bess_path, nrows=2)
    all_cols = list(df_bess.columns)
    
    co2_cols = [c for c in all_cols if 'co2' in c.lower()]
    soc_cols = [c for c in all_cols if 'soc' in c.lower()]
    
    print(f"  Total columnas: {len(all_cols)}")
    print(f"  Columnas CO2: {co2_cols if co2_cols else '❌ NINGUNA'}")
    print(f"  Columnas SOC: {soc_cols}")
    print(f"  Todas columnas: {all_cols}")
    print(f"  Datos de ejemplo:")
    print(f"    {df_bess.iloc[0].to_dict()}")
else:
    print(f"  ❌ NO EXISTE: {bess_path}")
print()

# 5. SOLAR - Validar
print("5️⃣ SOLAR_GENERATION.CSV")
print("-"*100)
solar_path = dataset_base / 'solar_generation.csv'
if solar_path.exists():
    df_solar = pd.read_csv(solar_path)
    print(f"  Shape: {df_solar.shape}")
    print(f"  Columnas: {list(df_solar.columns)}")
    print(f"  Datos de ejemplo:")
    print(f"    {df_solar.iloc[0].to_dict()}")
else:
    print(f"  ❌ NO EXISTE: {solar_path}")
print()

# 6. CONFIG JSON - Check available
print("6️⃣ DATASET_CONFIG_V7.JSON")
print("-"*100)
config_path = dataset_base / 'dataset_config_v7.json'
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"  Keys en config: {list(config.keys())}")
    print(f"  Estructura: {json.dumps(config, indent=2)[:500]}...")
else:
    print(f"  ❌ NO EXISTE: {config_path}")

print()
print("="*100)
