#!/usr/bin/env python3
"""Validación de datos reales OE2 para entrenamiento PPO"""
from pathlib import Path
import pandas as pd
import numpy as np

print('='*80)
print('VALIDACION Y CONSTRUCTION DE DATOS REALES OE2 PARA PPO')
print('='*80)
print()

# Archivos OE2 obligatorios
oe2_files = {
    'solar': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
    'chargers': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
    'bess': Path('data/oe2/bess/bess_ano_2024.csv'),
    'mall': Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
}

all_ok = True
oe2_summary = {}

print('Validando archivos OE2:')
print('-'*80)

for name, path in oe2_files.items():
    if path.exists():
        df = pd.read_csv(path)
        oe2_summary[name] = {
            'rows': len(df),
            'cols': len(df.columns),
            'path': str(path)
        }
        print(f'✓ {name:12} {len(df):6,d} rows × {len(df.columns):3d} cols')
        
        # Validación específica
        if name == 'solar' and len(df) != 8760:
            print(f'  WARNING: {name} tiene {len(df)} rows, esperado 8760 (hourly year)')
        elif name == 'chargers' and len(df) != 365:
            print(f'  WARNING: {name} tiene {len(df)} rows, esperado 365 (daily year)')
            
    else:
        print(f'✗ {name:12} NOT FOUND: {path}')
        all_ok = False

print()
if all_ok:
    print('✓ Todos los archivos OE2 presentes')
    print()
    print('Summary OE2:')
    for name, info in oe2_summary.items():
        print(f'  {name:12} {info["rows"]:6,d} rows × {info["cols"]:3d} cols')
else:
    print('✗ Faltan algunos archivos OE2')
    exit(1)

print()
print('='*80)
print('Datos reales validados - Listo para PPO training')
print('='*80)
