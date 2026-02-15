#!/usr/bin/env python3
"""List all available datasets with column information."""

import pandas as pd
import os
from pathlib import Path

print('[GRAPH] LISTADO DE DATASETS DISPONIBLES')
print('=' * 110)
print()

# Rutas de datos REALES (que existen)
data_paths = {
    'Solar Generation': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'BESS Data': 'data/oe2/bess/bess_ano_2024.csv',
    'Chargers Dataset': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'Mall Demand': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

# Tabla compacta
print(f"{'Status':<5} {'Dataset':<20} {'Filas':>10} {'Columnas':>10}")
print('-' * 110)

datasets_loaded = []

for name, path in data_paths.items():
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            n_rows, n_cols = df.shape
            datasets_loaded.append({
                'name': name,
                'path': path,
                'df': df,
                'rows': n_rows,
                'cols': n_cols
            })
            print(f"[OK]    {name:<18} {n_rows:>10,} {n_cols:>10}")
        except Exception as e:
            print(f"[X]    {name:<18} {'ERROR':<10} {str(e)[:30]}")
    else:
        print(f"[X]    {name:<18} {'FILE NOT FOUND':>10}")

print()
print('=' * 110)
print()
print('📄 DETALLE DE COLUMNAS:')
print()

for dataset in datasets_loaded:
    print(f"> {dataset['name']} (FILAS: {dataset['rows']:,} | COLUMNAS: {dataset['cols']})")
    print('  ' + '-' * 106)
    
    cols = list(dataset['df'].columns)
    
    # Mostrar todas las columnas
    for i, col in enumerate(cols, 1):
        dtype = str(dataset['df'][col].dtype)
        # Truncar nombre si es muy largo
        col_display = col[:50] + '...' if len(col) > 50 else col
        print(f"    {i:3d}. {col_display:<50} ({dtype})")
    
    print()

print('=' * 110)
print(f"\n[OK] Total datasets disponibles: {len(datasets_loaded)}")
print(f"[OK] Total columnas cargadas: {sum(d['cols'] for d in datasets_loaded)}")
print(f"[OK] Total filas cargadas: {sum(d['rows'] for d in datasets_loaded):,}")
