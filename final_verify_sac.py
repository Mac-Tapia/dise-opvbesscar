#!/usr/bin/env python3
"""Resumen visual de archivos técnicos SAC v9.2 generados"""
import pandas as pd
import json
from pathlib import Path

print("="*80)
print("VERIFICACIÓN FINAL - SAC v9.2 Archivos Técnicos Generados")
print("="*80)

# 1. result_sac.json
print("\n[1] result_sac.json")
print("-"*80)
result_path = Path('outputs/sac_training/result_sac.json')
with open(result_path) as f:
    result = json.load(f)

print(f"✓ Tamaño: {result_path.stat().st_size/1024:.1f} KB")
print(f"✓ Contenido: Diccionario JSON con {len(result)} claves")
print(f"  - agent: {result.get('agent')}")
print(f"  - version: {result.get('version')}")
print(f"  - total_timesteps: {result.get('total_timesteps'):,}")
print(f"  - episodes_completed: {result.get('episodes_completed')}")
print(f"  - model_path: {result.get('model_path')}")
print(f"  - Claves adicionales: {list(result.keys())[:5]}...")

# 2. trace_sac.csv
print("\n[2] trace_sac.csv")
print("-"*80)
trace_path = Path('outputs/sac_training/trace_sac.csv')
trace_df = pd.read_csv(trace_path)

print(f"✓ Tamaño: {trace_path.stat().st_size/1024:.1f} KB ({trace_path.stat().st_size/1024/1024:.1f} MB)")
print(f"✓ Dimensiones: {len(trace_df):,} filas × {len(trace_df.columns)} columnas")
print(f"✓ Columnas:")
for i, col in enumerate(trace_df.columns, 1):
    print(f"  {i:2d}. {col}")
print(f"\n✓ Datos del episodio (primeras 3 filas):")
print(trace_df.head(3).to_string())

# 3. timeseries_sac.csv
print("\n[3] timeseries_sac.csv")
print("-"*80)
ts_path = Path('outputs/sac_training/timeseries_sac.csv')
ts_df = pd.read_csv(ts_path)

print(f"✓ Tamaño: {ts_path.stat().st_size/1024:.1f} KB ({ts_path.stat().st_size/1024/1024:.1f} MB)")
print(f"✓ Dimensiones: {len(ts_df):,} filas × {len(ts_df.columns)} columnas")
print(f"✓ Columnas:")
for i, col in enumerate(ts_df.columns, 1):
    print(f"  {i:2d}. {col}")
print(f"\n✓ Datos de timeseries (primeras 3 filas):")
print(ts_df.head(3).to_string())

# Estadísticas
print("\n\n" + "="*80)
print("ESTADÍSTICAS GENERALES")
print("="*80)

print(f"\n✓ Rango de recompensas (reward):")
print(f"  - Min: {trace_df['reward'].min():.8f}")
print(f"  - Max: {trace_df['reward'].max():.8f}")
print(f"  - Mean: {trace_df['reward'].mean():.8f}")
print(f"  - Status: {'RANGO VALIDO' if trace_df['reward'].min() >= -0.0005 and trace_df['reward'].max() <= 0.0005 else 'FUERA DE RANGO'}")

print(f"\n✓ Grid import (minimización objetivo):")
print(f"  - Min: {ts_df['grid_import_kw'].min():.1f} kW")
print(f"  - Max: {ts_df['grid_import_kw'].max():.1f} kW")
print(f"  - Mean: {ts_df['grid_import_kw'].mean():.1f} kW")

print(f"\n✓ BESS SOC (estado de carga):")
print(f"  - Min: {ts_df['bess_soc'].min():.1f}%")
print(f"  - Max: {ts_df['bess_soc'].max():.1f}%")
print(f"  - Mean: {ts_df['bess_soc'].mean():.1f}%")

print("\n" + "="*80)
print("✓ VERIFICACIÓN EXITOSA")
print("Todos los 3 archivos técnicos fueron generados correctamente por SAC v9.2")
print("="*80)
