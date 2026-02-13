#!/usr/bin/env python3
"""
Corrección y reformateo del dataset BESS v5.4
Asegurar DatetimeIndex y compatibilidad completa con CityLearn
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
import numpy as np

DATASET_PATH = Path('data/oe2/bess/bess_simulation_hourly.csv')
YEAR = 2024

print("\n" + "="*80)
print("CORRECCIÓN Y REFORMATEO - Dataset BESS v5.4 para CityLearn")
print("="*80)

# Cargar dataset
print("\n[1] Cargando dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"   ✓ {len(df)} filas × {len(df.columns)} columnas")

# Crear índice datetime correcto
print("\n[2] Corrigiendo índice (datetime)...")
datetime_index = pd.date_range(start=f'{YEAR}-01-01', periods=len(df), freq='h', tz=None)
df_fixed = df.copy()
df_fixed.index = datetime_index
df_fixed.index.name = 'datetime'

print(f"   ✓ Índice datetime: {df_fixed.index[0]} a {df_fixed.index[-1]}")
print(f"   ✓ Tipo: {type(df_fixed.index)}")
print(f"   ✓ Frecuencia: {pd.infer_freq(df_fixed.index)}")

# Asegurar tipos de datos
print("\n[3] Validando tipos de datos...")
numeric_cols = df_fixed.select_dtypes(include=[np.number]).columns.tolist()
print(f"   ✓ {len(numeric_cols)} columnas numéricas")

# Limpiar valores NaN muy pequeños
print("\n[4] Limpieza de valores infinitesimales...")
for col in numeric_cols:
    tiny_mask = (df_fixed[col].abs() < 1e-10) & (df_fixed[col] != 0)
    if tiny_mask.any():
        df_fixed.loc[tiny_mask, col] = 0.0
        print(f"   ✓ {col}: {tiny_mask.sum()} valores infinitesimales → 0")

# Validar ranges
print("\n[5] Validando ranges...")
issues = []
if (df_fixed['bess_soc_percent'] < 0).any() or (df_fixed['bess_soc_percent'] > 100).any():
    issues.append("bess_soc_percent fuera de rango")
if (df_fixed['peak_reduction_savings_normalized'] < 0).any() or (df_fixed['peak_reduction_savings_normalized'] > 1).any():
    issues.append("peak_reduction_savings_normalized fuera de rango")
if (df_fixed['co2_avoided_indirect_normalized'] < 0).any() or (df_fixed['co2_avoided_indirect_normalized'] > 1).any():
    issues.append("co2_avoided_indirect_normalized fuera de rango")

if issues:
    print(f"   ⚠ Advertencias: {issues}")
else:
    print(f"   ✓ Todos los ranges correctos")

# Guardar versión corregida
print("\n[6] Guardando dataset corregido...")
df_fixed.to_csv(DATASET_PATH)
print(f"   ✓ Guardado: {DATASET_PATH}")
print(f"   ✓ Tamaño: {DATASET_PATH.stat().st_size / 1024 / 1024:.2f} MB")

# Verificación final
print("\n[7] Verificación final...")
df_verify = pd.read_csv(DATASET_PATH, index_col=0, parse_dates=True)
print(f"   ✓ Índice verificado: {type(df_verify.index)}")
print(f"   ✓ Filas: {len(df_verify):,}")
print(f"   ✓ Columnas: {len(df_verify.columns)}")
print(f"   ✓ Fechas: {df_verify.index[0].date()} a {df_verify.index[-1].date()}")
print(f"   ✓ Sin valores nulos: {df_verify.isnull().sum().sum() == 0}")

# Resumen de métricas v5.4
print("\n[8] Métricas v5.4 actualizadas...")
print(f"   ✓ Ahorros total: S/. {df_verify['peak_reduction_savings_soles'].sum():,.0f}/año")
print(f"   ✓ CO2 indirecto: {df_verify['co2_avoided_indirect_kg'].sum()/1000:.1f} ton/año")

print("\n" + "="*80)
print("✅ DATASET CORREGIDO Y LISTO PARA CITYLEARN + ENTRENAMIENTO AGENTES")
print("="*80 + "\n")
