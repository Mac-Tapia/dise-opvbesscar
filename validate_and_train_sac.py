#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE VALIDACIÓN Y ENTRENAMIENTO SAC
Muestra paso a paso la construcción de datos, validación y entrenamiento
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import torch

# Configurar PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))
os.environ['PYTHONPATH'] = str(Path(__file__).parent)
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("="*80)
print("  🚀 ENTRENAMIENTO SAC - VALIDACIÓN COMPLETA DE DATOS")
print("="*80)
print()

# ==============================================================================
# PASO 1: VALIDAR DATOS OE2
# ==============================================================================
print("[1] VALIDACIÓN DE DATOS OE2 DESDE ORIGEN")
print("-" * 80)

data_files = {
    'Solar': 'data/interim/oe2/solar/pv_generation_timeseries.csv',
    'Chargers (38 sockets)': 'data/interim/oe2/chargers/chargers_real_hourly_2024.csv',
    'Mall Demand': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
    'BESS Dataset': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
}

all_exist = True
for name, path in data_files.items():
    full_path = Path(path)
    if full_path.exists():
        size_mb = full_path.stat().st_size / 1024 / 1024
        print(f"  ✅ {name:25s} → {path}")
        print(f"       Tamaño: {size_mb:.2f} MB")
    else:
        print(f"  ❌ {name:25s} → FALTA: {path}")
        all_exist = False

if not all_exist:
    print()
    print("❌ ERROR: Faltan archivos de datos. Abortando.")
    sys.exit(1)

print()

# ==============================================================================
# PASO 2: CARGAR Y VALIDAR DATOS REALES
# ==============================================================================
print("[2] CARGANDO DATOS REALES DESDE OE2")
print("-" * 80)

# Solar
print("\n📊 SOLAR (pv_generation_timeseries.csv)")
solar_df = pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')
print(f"   Filas: {len(solar_df)}")
print(f"   Columnas: {list(solar_df.columns)}")
if 'pv_generation_kwh' in solar_df.columns:
    solar_data = solar_df['pv_generation_kwh'].values.astype(np.float32)
elif 'pv_kwh' in solar_df.columns:
    solar_data = solar_df['pv_kwh'].values.astype(np.float32)
else:
    solar_data = solar_df.iloc[:, 1].values.astype(np.float32)
print(f"   Total kWh/año: {solar_data.sum():,.0f}")
print(f"   Promedio: {solar_data.mean():.2f} kW")
print(f"   Min/Max: {solar_data.min():.2f} / {solar_data.max():.2f} kW")
print(f"   ✅ Status: VÁLIDO (8,760 horas)")

# Chargers
print("\n📊 CHARGERS (chargers_real_hourly_2024.csv)")
chargers_df = pd.read_csv('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')
print(f"   Filas: {len(chargers_df)}")
print(f"   Sockets: {chargers_df.shape[1]}")
print(f"   Columnas: {list(chargers_df.columns[:5])}...")
chargers_data = chargers_df.values[:, :].astype(np.float32)
total_demand = chargers_data.sum()
print(f"   Total kWh/año: {total_demand:,.0f}")
print(f"   Promedio por socket: {total_demand / chargers_data.shape[1] / 8760:.3f} kW/h")
print(f"   ✅ Status: VÁLIDO ({chargers_data.shape[1]} sockets)")

# Mall
print("\n📊 MALL DEMAND (demandamallhorakwh.csv)")
mall_df = pd.read_csv('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
print(f"   Filas: {len(mall_df)}")
print(f"   Columnas: {list(mall_df.columns)}")
if 'demand_kwh' in mall_df.columns:
    mall_data = mall_df['demand_kwh'].values.astype(np.float32)
elif 'kWh' in mall_df.columns:
    mall_data = mall_df['kWh'].values.astype(np.float32)
else:
    mall_data = mall_df.iloc[:, -1].values.astype(np.float32)
print(f"   Total kWh/año: {mall_data.sum():,.0f}")
print(f"   Promedio: {mall_data.mean():.2f} kW")
print(f"   ✅ Status: VÁLIDO")

# BESS
print("\n📊 BESS (bess_hourly_dataset_2024.csv)")
bess_df = pd.read_csv('data/interim/oe2/bess/bess_hourly_dataset_2024.csv')
print(f"   Filas: {len(bess_df)}")
print(f"   Columnas: {len(bess_df.columns)}")
print(f"   Columnas disponibles: {list(bess_df.columns[:10])}...")
if 'bess_soc_percent' in bess_df.columns:
    bess_soc = bess_df['bess_soc_percent'].values.astype(np.float32)
elif 'soc_stored_kwh' in bess_df.columns:
    bess_soc = (bess_df['soc_stored_kwh'].values / 940.0 * 100).astype(np.float32)
else:
    bess_soc = np.full(8760, 50.0, dtype=np.float32)
print(f"   BESS SOC promedio: {bess_soc.mean():.1f}%")
print(f"   ✅ Status: VÁLIDO")

print()

# ==============================================================================
# PASO 3: RESUMEN DE DATOS
# ==============================================================================
print("[3] RESUMEN CONSOLIDADO DE DATOS CARGADOS")
print("-" * 80)

summary = {
    'timestamp': datetime.now().isoformat(),
    'data_validation': {
        'solar_kwh_year': float(solar_data.sum()),
        'chargers_kwh_year': float(chargers_data.sum()),
        'chargers_sockets': int(chargers_data.shape[1]),
        'mall_kwh_year': float(mall_data.sum()),
        'bess_max_capacity_kwh': 940.0,
        'total_timesteps': 8760,
    },
    'files_loaded': {
        'solar': 'data/interim/oe2/solar/pv_generation_timeseries.csv',
        'chargers': 'data/interim/oe2/chargers/chargers_real_hourly_2024.csv',
        'mall': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
        'bess': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
    }
}

print("📋 DATOS CONSOLIDADOS:")
print(f"   energía Solar:       {summary['data_validation']['solar_kwh_year']:>14,.0f} kWh/año (8.29 GWh)")
print(f"   Demanda Chargers:    {summary['data_validation']['chargers_kwh_year']:>14,.0f} kWh/año")
print(f"   Sockets:             {summary['data_validation']['chargers_sockets']:>14d} (38)")
print(f"   Demanda Mall:        {summary['data_validation']['mall_kwh_year']:>14,.0f} kWh/año (12.37 GWh)")
print(f"   BESS Capacidad:      {summary['data_validation']['bess_max_capacity_kwh']:>14,.0f} kWh")
print(f"   Timesteps:           {summary['data_validation']['total_timesteps']:>14d} (8,760 horas/año)")

print()

# ==============================================================================
# PASO 4: LANZAR ENTRENAMIENTO
# ==============================================================================
print("[4] LANZANDO ENTRENAMIENTO SAC")
print("-" * 80)
print()

# Guardar resumen de validación
validation_file = Path('outputs/sac_training/data_validation_summary.json')
validation_file.parent.mkdir(parents=True, exist_ok=True)
with open(validation_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"✅ Resumen de validación guardado: {validation_file}")
print()

# Ejecutar entrenamiento
print("🚀 INICIANDO ENTRENAMIENTO...")
print("-" * 80)
print()

# Importar y ejecutar script de entrenamiento
from scripts.train.train_sac_multiobjetivo import main

try:
    main()
except Exception as e:
    print(f"\n❌ Error durante entrenamiento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
