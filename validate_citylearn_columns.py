#!/usr/bin/env python3
"""
Validacion de columnas para CityLearn v2
Verifica que grid_export_kwh y bess_to_mall_kwh existan con datos completos
"""
import pandas as pd
import numpy as np
from pathlib import Path

output_dir = Path("data/oe2/bess")
csv_file = output_dir / "bess_ano_2024.csv"

print("=" * 80)
print("VALIDACION CityLearn v2 - COLUMNAS ENERGETICAS")
print("=" * 80)

if not csv_file.exists():
    print(f"ERROR: Archivo {csv_file} no existe")
    exit(1)

# Cargar CSV
df = pd.read_csv(csv_file)

print(f"\n[ESTRUCTURA DEL ARCHIVO]")
print(f"  Filas:   {len(df)}")
print(f"  Columnas: {len(df.columns)}")

# Verificar columnas requeridas
required_cols = ['grid_export_kwh', 'bess_to_mall_kwh']
print(f"\n[COLUMNAS REQUERIDAS PARA RL]")
for col in required_cols:
    if col in df.columns:
        print(f"  [OK] {col} - Presente")
    else:
        print(f"  [ERROR] {col} - FALTANTE")

# Verificar integridad de datos
print(f"\n[VALIDACION DE DATOS]")
print(f"\n  grid_export_kwh (Exportacion a red publica):")
print(f"    - Tipo:        {df['grid_export_kwh'].dtype}")
print(f"    - Valores:     MIN={df['grid_export_kwh'].min():.2f} kWh, MAX={df['grid_export_kwh'].max():.2f} kWh")
print(f"    - Suma anual:  {df['grid_export_kwh'].sum():.2f} kWh")
print(f"    - NaN valores: {df['grid_export_kwh'].isna().sum()}")
print(f"    - Negativos:   {(df['grid_export_kwh'] < 0).sum()}")

print(f"\n  bess_to_mall_kwh (Reduccion pico demanda de MALL):")
print(f"    - Tipo:        {df['bess_to_mall_kwh'].dtype}")
print(f"    - Valores:     MIN={df['bess_to_mall_kwh'].min():.2f} kWh, MAX={df['bess_to_mall_kwh'].max():.2f} kWh")
print(f"    - Suma anual:  {df['bess_to_mall_kwh'].sum():.2f} kWh")
print(f"    - NaN valores: {df['bess_to_mall_kwh'].isna().sum()}")
print(f"    - Negativos:   {(df['bess_to_mall_kwh'] < 0).sum()}")

# Verificar 8,760 horas
print(f"\n[VERIFICACION TEMPORAL]")
print(f"  Total horas (8,760):     {len(df) == 8760}")
print(f"  Horas faltantes:         {8760 - len(df)}")

# Mostrar datos de ejemplo
print(f"\n[MUESTRA DE DATOS - PRIMERAS 5 HORAS]")
sample_cols = ['datetime', 'pv_kwh', 'ev_kwh', 'grid_export_kwh', 'bess_to_mall_kwh', 'soc_percent']
print(df[sample_cols].head().to_string())

print(f"\n[MUESTRA DE DATOS - ULTIMAS 5 HORAS]")
print(df[sample_cols].tail().to_string())

# Verificar integridad general
is_valid = (
    len(df) == 8760 and
    'grid_export_kwh' in df.columns and
    'bess_to_mall_kwh' in df.columns and
    df['grid_export_kwh'].isna().sum() == 0 and
    df['bess_to_mall_kwh'].isna().sum() == 0 and
    (df['grid_export_kwh'] >= 0).all() and
    (df['bess_to_mall_kwh'] >= 0).all()
)

print(f"\n{'=' * 80}")
if is_valid:
    print("[OK] DATASET LISTO PARA CityLearn v2")
    print(f"  - Ambas columnas presentes y completas")
    print(f"  - 8,760 horas sin errores")
    print(f"  - Sin valores NaN ni negativos")
else:
    print("[ERROR] Dataset NO cumple requisitos CityLearn v2")
    if len(df) != 8760:
        print(f"  - [!] Faltan {8760 - len(df)} horas")
    if df['grid_export_kwh'].isna().sum() > 0:
        print(f"  - [!] grid_export_kwh tiene {df['grid_export_kwh'].isna().sum()} NaN")
    if df['bess_to_mall_kwh'].isna().sum() > 0:
        print(f"  - [!] bess_to_mall_kwh tiene {df['bess_to_mall_kwh'].isna().sum()} NaN")
    if (df['grid_export_kwh'] < 0).any():
        print(f"  - [!] grid_export_kwh tiene valores negativos")
    if (df['bess_to_mall_kwh'] < 0).any():
        print(f"  - [!] bess_to_mall_kwh tiene valores negativos")

print("=" * 80)
