#!/usr/bin/env python3
"""Diagnosticar parsing de mall demand CSV."""

import pandas as pd
from pathlib import Path

mall_path = Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv")

print("=" * 80)
print("DIAGNÓSTICO: PARSING DE MALL DEMAND CSV")
print("=" * 80)
print()

# Leer sin parsear primero
print("[1] Lectura RAW (primeras 10 líneas):")
with open(mall_path) as f:
    for i, line in enumerate(f):
        if i < 10:
            print(f"  {line.rstrip()}")
        else:
            break

print()

# Intentar diferentes parseos
print("[2] Intentar parse con separator ';':")
try:
    df_semi = pd.read_csv(mall_path, sep=";")
    print(f"  ✓ SUCCESS: {df_semi.shape}")
    print(f"  Columnas: {list(df_semi.columns)}")
    print(f"  Primeros 5 registros:")
    print(df_semi.head())
except Exception as e:
    print(f"  ✗ FAILED: {e}")

print()

# Intentar parse por defecto
print("[3] Intentar parse con separator por defecto (','):")
try:
    df_comma = pd.read_csv(mall_path)
    print(f"  ✓ SUCCESS: {df_comma.shape}")
    print(f"  Columnas: {list(df_comma.columns)}")
    print(f"  Primeros 5 registros:")
    print(df_comma.head())
except Exception as e:
    print(f"  ✗ FAILED: {e}")

print()

# Agregar a horario
print("[4] Agregación a horario:")
df_semi["FECHAHORA;kWh"].str.split(";", expand=True)
try:
    # Split the combined column
    df_split = df_semi["FECHAHORA;kWh"].str.split(";", expand=True)
    print(f"  Split result shape: {df_split.shape}")
    print(f"  Primeros registros:")
    print(df_split.head(10))

    # Parse datetime and aggregate
    df_split.columns = ['datetime', 'kwh']
    df_split['datetime'] = pd.to_datetime(df_split['datetime'], format='%d/%m/%Y %H:%M', errors='coerce')
    df_split['kwh'] = pd.to_numeric(df_split['kwh'], errors='coerce')

    df_split = df_split.set_index('datetime').sort_index()
    df_hourly = df_split['kwh'].resample('h').sum()

    print(f"  ✓ Agregación OK: {len(df_hourly)} registros horarios")
    print(f"  Total: {df_hourly.sum():,.0f} kWh")
    print(f"  Primeras 24 horas:")
    print(df_hourly.head(24))

except Exception as e:
    print(f"  ✗ FAILED: {e}")

print()
print("=" * 80)
