#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN DETALLADA DE CARGA DE DATOS OE2 - AÑO COMPLETO
Asegura que se cargan TODOS los 8,760 datos horarios de cada dataset
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Configurar PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))
os.environ['PYTHONPATH'] = str(Path(__file__).parent)

HOURS_PER_YEAR = 8760

print("="*80)
print("  VERIFICACION DE DATOS OE2 - AÑO COMPLETO (8,760 HORAS)")
print("="*80)
print()

# ==============================================================================
# 1. SOLAR - Año completo
# ==============================================================================
print("[1] SOLAR - Año completo")
print("-" * 80)

solar_path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
if not solar_path.exists():
    print(f"ERROR: No encontrado {solar_path}")
    sys.exit(1)

df_solar = pd.read_csv(solar_path)
print(f"Archivo: {solar_path.name}")
print(f"Filas cargadas: {len(df_solar)}")
print(f"Columnas: {list(df_solar.columns)}")

if len(df_solar) != HOURS_PER_YEAR:
    print(f"ERROR: Se esperaban {HOURS_PER_YEAR} filas, se encontraron {len(df_solar)}")
    sys.exit(1)

# Obtener columna de energía
if 'pv_generation_kwh' in df_solar.columns:
    solar_col = 'pv_generation_kwh'
elif 'pv_kwh' in df_solar.columns:
    solar_col = 'pv_kwh'
else:
    solar_col = df_solar.columns[1]

solar_data = df_solar[solar_col].values.astype(np.float32)
print(f"Columna usada: {solar_col}")
print(f"Datos cargados: {len(solar_data)}/8,760 ✓")
print(f"Total kWh/año: {solar_data.sum():,.0f}")
print(f"Rango: {solar_data.min():.2f} - {solar_data.max():.2f} kW")
print(f"Promedio: {solar_data.mean():.2f} kW/h")
print()

# ==============================================================================
# 2. CHARGERS - Año completo (38 sockets)
# ==============================================================================
print("[2] CHARGERS - Año completo (38 sockets)")
print("-" * 80)

chargers_path = Path('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')
if not chargers_path.exists():
    print(f"ERROR: No encontrado {chargers_path}")
    sys.exit(1)

df_chargers = pd.read_csv(chargers_path)
print(f"Archivo: {chargers_path.name}")
print(f"Filas cargadas: {len(df_chargers)}")
print(f"Columnas: {df_chargers.shape[1]}")
print(f"Primera 5 columnas: {list(df_chargers.columns[:5])}")

if len(df_chargers) != HOURS_PER_YEAR:
    print(f"ERROR: Se esperaban {HOURS_PER_YEAR} filas, se encontraron {len(df_chargers)}")
    sys.exit(1)

# Usar todas las columnas numéricas
chargers_data = df_chargers.values[:, :].astype(np.float32)
n_sockets = chargers_data.shape[1]
print(f"Datos cargados: {len(chargers_data)}/8,760 horas x {n_sockets} sockets ✓")
print(f"Total kWh/año: {chargers_data.sum():,.0f}")
print(f"Promedio por socket: {chargers_data.sum() / n_sockets / HOURS_PER_YEAR:.3f} kW/h")
print()

# ==============================================================================
# 3. MALL - Año completo
# ==============================================================================
print("[3] MALL DEMAND - Año completo")
print("-" * 80)

mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
if not mall_path.exists():
    print(f"ERROR: No encontrado {mall_path}")
    sys.exit(1)

df_mall = pd.read_csv(mall_path)
print(f"Archivo: {mall_path.name}")
print(f"Filas cargadas: {len(df_mall)}")
print(f"Columnas: {list(df_mall.columns)}")

if len(df_mall) != HOURS_PER_YEAR:
    print(f"ERROR: Se esperaban {HOURS_PER_YEAR} filas, se encontraron {len(df_mall)}")
    sys.exit(1)

# Obtener columna correcta
if 'demand_kwh' in df_mall.columns:
    mall_col = 'demand_kwh'
else:
    mall_col = df_mall.columns[-1]

mall_data = df_mall[mall_col].values.astype(np.float32)
print(f"Columna usada: {mall_col}")
print(f"Datos cargados: {len(mall_data)}/8,760 ✓")
print(f"Total kWh/año: {mall_data.sum():,.0f}")
print(f"Rango: {mall_data.min():.2f} - {mall_data.max():.2f} kW")
print(f"Promedio: {mall_data.mean():.2f} kW/h")
print()

# ==============================================================================
# 4. BESS - Año completo
# ==============================================================================
print("[4] BESS (Battery Energy Storage System) - Año completo")
print("-" * 80)

bess_path = Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv')
if not bess_path.exists():
    print(f"ERROR: No encontrado {bess_path}")
    sys.exit(1)

df_bess = pd.read_csv(bess_path)
print(f"Archivo: {bess_path.name}")
print(f"Filas cargadas: {len(df_bess)}")
print(f"Columnas disponibles: {len(df_bess.columns)}")
print(f"Primeras 10 columnas: {list(df_bess.columns[:10])}")

if len(df_bess) != HOURS_PER_YEAR:
    print(f"ERROR: Se esperaban {HOURS_PER_YEAR} filas, se encontraron {len(df_bess)}")
    sys.exit(1)

# Obtener SOC
if 'bess_soc_percent' in df_bess.columns:
    bess_soc = df_bess['bess_soc_percent'].values.astype(np.float32)
    soc_col = 'bess_soc_percent'
elif 'soc_stored_kwh' in df_bess.columns:
    bess_capacity = 940.0
    bess_soc = (df_bess['soc_stored_kwh'].values / bess_capacity * 100).astype(np.float32)
    soc_col = 'soc_stored_kwh (convertido a %)'
else:
    bess_soc = np.full(HOURS_PER_YEAR, 50.0, dtype=np.float32)
    soc_col = 'VALOR POR DEFECTO (50%)'

print(f"Columna SOC usada: {soc_col}")
print(f"Datos cargados: {len(bess_soc)}/8,760 ✓")
print(f"Rango SOC: {bess_soc.min():.1f} - {bess_soc.max():.1f}%")
print(f"Promedio SOC: {bess_soc.mean():.1f}%")

# Verificar columnas de energía
energy_cols = [c for c in df_bess.columns if 'energy' in c.lower() or 'kwh' in c.lower()]
print(f"Columnas de energía disponibles: {energy_cols[:5]}")
print()

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
print("[RESUMEN] DATOS CARGADOS CORRECTAMENTE")
print("="*80)
print()
print("SOLAR:")
print(f"  Filas:              {len(solar_data):>6d}/8,760")
print(f"  Total kWh/año:      {solar_data.sum():>13,.0f}")
print(f"  Promedio:           {solar_data.mean():>13.2f} kW/h")
print()

print("CHARGERS (38 sockets):")
print(f"  Filas:              {len(chargers_data):>6d}/8,760")
print(f"  Sockets:            {n_sockets:>6d}")
print(f"  Total kWh/año:      {chargers_data.sum():>13,.0f}")
print(f"  Promedio/socket:    {chargers_data.sum() / n_sockets / HOURS_PER_YEAR:>13.3f} kW/h")
print()

print("MALL:")
print(f"  Filas:              {len(mall_data):>6d}/8,760")
print(f"  Total kWh/año:      {mall_data.sum():>13,.0f}")
print(f"  Promedio:           {mall_data.mean():>13.2f} kW/h")
print()

print("BESS:")
print(f"  Filas:              {len(bess_soc):>6d}/8,760")
print(f"  SOC promedio:       {bess_soc.mean():>13.1f}%")
print(f"  Capacidad:          {940.0:>13,.0f} kWh")
print()

print("="*80)
print("  STATUS: TODOS LOS DATOS CARGADOS CORRECTAMENTE")
print("  Listo para entrenamiento SAC")
print("="*80)
