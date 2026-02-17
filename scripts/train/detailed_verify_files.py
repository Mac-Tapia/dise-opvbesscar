#!/usr/bin/env python3
"""Verificación detallada de archivos técnicos SAC v9.2"""
import json
from pathlib import Path

print("="*80)
print("VERIFICACIÓN DETALLADA - SAC v9.2 Archivos Técnicos")
print("="*80)

# 1. result_sac.json
print("\n1. result_sac.json")
print("-"*80)
result_path = Path('outputs/sac_training/result_sac.json')
if result_path.exists():
    with open(result_path) as f:
        result = json.load(f)
    
    size_kb = result_path.stat().st_size / 1024
    print(f"✓ Tamaño: {size_kb:.1f} KB")
    print(f"✓ Contenido (claves JSON):")
    for key in result.keys():
        if isinstance(result[key], list):
            print(f"  - {key}: Lista con {len(result[key])} elementos")
        elif isinstance(result[key], dict):
            print(f"  - {key}: Diccionario con {len(result[key])} claves")
        else:
            val_str = str(result[key])[:50]
            print(f"  - {key}: {type(result[key]).__name__} = {val_str}")

# 2. trace_sac.csv
print("\n2. trace_sac.csv")
print("-"*80)
trace_path = Path('outputs/sac_training/trace_sac.csv')
if trace_path.exists():
    size_kb = trace_path.stat().st_size / 1024
    with open(trace_path) as f:
        header = f.readline().strip()
        lines = sum(1 for _ in f)
    
    print(f"✓ Tamaño: {size_kb:.1f} KB")
    print(f"✓ Filas de datos: {lines:,}")
    print(f"✓ Columnas ({len(header.split(','))} total):")
    cols = header.split(',')
    for i, col in enumerate(cols, 1):
        print(f"  {i:2d}. {col}")
    
    # Mostrar primeras filas
    print(f"✓ Primeras 2 filas de datos (sample):")
    with open(trace_path) as f:
        f.readline()  # skip header
        for i in range(2):
            row = f.readline().strip()
            print(f"  {i+1}: {row[:100]}...")

# 3. timeseries_sac.csv
print("\n3. timeseries_sac.csv")
print("-"*80)
ts_path = Path('outputs/sac_training/timeseries_sac.csv')
if ts_path.exists():
    size_kb = ts_path.stat().st_size / 1024
    with open(ts_path) as f:
        header = f.readline().strip()
        lines = sum(1 for _ in f)
    
    print(f"✓ Tamaño: {size_kb:.1f} KB")
    print(f"✓ Filas de datos: {lines:,}")
    print(f"✓ Columnas ({len(header.split(','))} total):")
    cols = header.split(',')
    for i, col in enumerate(cols, 1):
        print(f"  {i:2d}. {col}")
    
    # Mostrar primeras filas
    print(f"✓ Primeras 2 filas de datos (sample):")
    with open(ts_path) as f:
        f.readline()  # skip header
        for i in range(2):
            row = f.readline().strip()
            print(f"  {i+1}: {row[:100]}...")

print("\n" + "="*80)
print("RESUMEN:")
print("-"*80)
print(f"✓ result_sac.json:   {result_path.exists()} - {result_path.stat().st_size/1024:.1f} KB")
print(f"✓ trace_sac.csv:     {trace_path.exists()} - {trace_path.stat().st_size/1024:.1f} KB")
print(f"✓ timeseries_sac.csv: {ts_path.exists()} - {ts_path.stat().st_size/1024:.1f} KB")
print("\n✓ VERIFICACIÓN EXITOSA - Todos los archivos técnicos fueron generados")
print("="*80)
