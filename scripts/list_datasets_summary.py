#!/usr/bin/env python3
"""List all available datasets with column information - SUMMARY VERSION."""

import pandas as pd
import os

print('[GRAPH] LISTADO DE DATASETS DISPONIBLES')
print('=' * 120)
print()

# Rutas de datos REALES (que existen)
data_paths = {
    'Solar Generation': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'BESS Data': 'data/oe2/bess/bess_ano_2024.csv',
    'Chargers Dataset': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'Mall Demand': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

# Tabla principal
print(f"{'Status':<5} {'Dataset Name':<20} {'Filas':>10} {'Columnas':>10} {'Ruta del archivo'}")
print('-' * 120)

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
            print(f"[OK]    {name:<18} {n_rows:>10,} {n_cols:>10}   {path}")
        except Exception as e:
            print(f"[X]    {name:<18} {'ERROR':>10} {str(e)[:40]}")
    else:
        print(f"[X]    {name:<18} {'NO EXISTE':>10}             {path}")

print()
print('=' * 120)
print()
print('📄 DETALLE DE COLUMNAS (primeras 15 columnas por dataset):')
print()

for dataset in datasets_loaded:
    print(f"> {dataset['name']} ")
    print(f"  Dimensiones: {dataset['rows']:,} filas × {dataset['cols']} columnas")
    print(f"  Ruta: {dataset['path']}")
    print('  ' + '-' * 115)
    print('  Columnas:')
    
    cols = list(dataset['df'].columns)
    
    # Mostrar primeras 15 columnas o todas si hay menos
    cols_to_show = cols[:15]
    for i, col in enumerate(cols_to_show, 1):
        dtype = str(dataset['df'][col].dtype)
        try:
            # Obtener stats basicos
            if 'float' in dtype or 'int' in dtype:
                min_val = dataset['df'][col].min()
                max_val = dataset['df'][col].max()
                stats_str = f" [min={min_val:.2f}, max={max_val:.2f}]"
            else:
                unique_count = dataset['df'][col].nunique()
                stats_str = f" [unique={unique_count}]"
        except:
            stats_str = ""
        
        col_display = col[:55] + '...' if len(col) > 55 else col
        print(f"    {i:2d}. {col_display:<55} ({dtype}){stats_str}")
    
    if len(cols) > 15:
        print(f"    ... y {len(cols) - 15} columnas mas")
    
    print()

print('=' * 120)
print(f"\n[OK] RESUMEN:")
print(f"  - Total datasets disponibles: {len(datasets_loaded)}")
print(f"  - Total columnas cargadas: {sum(d['cols'] for d in datasets_loaded):,}")
print(f"  - Total filas cargadas: {sum(d['rows'] for d in datasets_loaded):,}")
print(f"  - Tamano total en memoria: ~{sum(d['df'].memory_usage(deep=True).sum() / (1024**2) for d in datasets_loaded):.1f} MB")
