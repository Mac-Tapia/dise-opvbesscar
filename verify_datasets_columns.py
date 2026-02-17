#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar TODAS las columnas de los datasets OE2"""

from pathlib import Path
import pandas as pd

print("="*80)
print("VERIFICACION COMPLETA DE DATASETS - TODAS LAS COLUMNAS")
print("="*80)

datasets = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
    'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv'
}

for name, path_str in datasets.items():
    path = Path(path_str)
    print(f"\n[{name.upper()}] {path.name}")
    print("-" * 80)
    
    if not path.exists():
        print(f"  ❌ NO ENCONTRADO")
        continue
    
    try:
        df = pd.read_csv(path)
        print(f"  Filas: {len(df)} (esperadas: 8,760)")
        print(f"  Columnas: {len(df.columns)}")
        print(f"  Tamaño: {path.stat().st_size / 1e6:.2f} MB")
        
        # Check filas
        if len(df) == 8760:
            print(f"  [✓] Filas correctas (8,760 = 365 días × 24 horas)")
        else:
            print(f"  [⚠️] Filas incorrectas ({len(df)} != 8,760)")
        
        # Mostrar columnas
        print(f"\n  Columnas ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            print(f"    {i:2d}. {col:40s} | {dtype:10s} | {non_null:5d} valores")
        
        # Estadísticas
        print(f"\n  Estadísticas:")
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols[:5]:  # Mostrar primeros 5
            print(f"    - {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*80)
print("RESUMEN - DATASETS LISTOS PARA ENTRENAR A2C/PPO/SAC")
print("="*80)

# Verificar que todos existen y tienen 8,760 filas
all_ok = True
for name, path_str in datasets.items():
    path = Path(path_str)
    if path.exists():
        df = pd.read_csv(path)
        if len(df) == 8760:
            print(f"  ✓ {name:10s}: OK (8,760 filas, {len(df.columns)} columnas)")
        else:
            print(f"  ✗ {name:10s}: ERROR (8,760 filas esperadas, {len(df)} encontradas)")
            all_ok = False
    else:
        print(f"  ✗ {name:10s}: NO ENCONTRADO")
        all_ok = False

if all_ok:
    print("\n✅ TODOS LOS DATASETS VALIDOS - LISTO PARA ENTRENAR SAC")
else:
    print("\n❌ PROBLEMAS CON DATASETS - REVISAR ARRIBA")
