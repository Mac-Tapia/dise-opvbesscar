#!/usr/bin/env python3
"""Automatically list all CSV datasets with their specifications."""

import pandas as pd
import os
from pathlib import Path

print('[GRAPH] LISTADO COMPLETO DE DATASETS (Todos los CSV encontrados)')
print('=' * 140)
print()

# Encontrar todos los CSV
csv_files = []
for root, dirs, files in os.walk('data'):
    for file in files:
        if file.endswith('.csv'):
            filepath = os.path.join(root, file)
            csv_files.append(filepath)

csv_files.sort()

# Cargar informacion
print(f"{'#':<3} {'Status':<5} {'Dataset (Nombre)':<50} {'Filas':>10} {'Cols':>5} {'MB':>8}")
print('-' * 140)

datasets = []
idx = 1

for filepath in csv_files:
    try:
        df = pd.read_csv(filepath)
        n_rows, n_cols = df.shape
        size_mb = df.memory_usage(deep=True).sum() / (1024**2)
        
        # Nombre corto
        short_name = filepath.replace('data/', '')
        if len(short_name) > 48:
            short_name = '...' + short_name[-45:]
        
        print(f"{idx:<3} [OK]    {short_name:<50} {n_rows:>10,} {n_cols:>5} {size_mb:>8.2f}")
        
        datasets.append({
            'idx': idx,
            'path': filepath,
            'name': short_name,
            'df': df,
            'rows': n_rows,
            'cols': n_cols,
            'size_mb': size_mb
        })
        idx += 1
        
    except Exception as e:
        print(f"{idx:<3} [X]    {filepath:<50} ERROR: {str(e)[:30]}")
        idx += 1

print()
print('=' * 140)
print()

# Agrupar por carpeta
print('📁 DATASETS AGRUPADOS POR CARPETA:')
print()

from collections import defaultdict
by_folder = defaultdict(list)

for ds in datasets:
    folder = ds['path'].split('/')[1] if '/' in ds['path'] else 'root'
    by_folder[folder].append(ds)

for folder in sorted(by_folder.keys()):
    datasets_in_folder = by_folder[folder]
    total_cols = sum(d['cols'] for d in datasets_in_folder)
    total_rows = sum(d['rows'] for d in datasets_in_folder)
    total_size = sum(d['size_mb'] for d in datasets_in_folder)
    
    print(f"> {folder}/ ({len(datasets_in_folder)} datasets | {total_rows:,} filas | {total_cols:,} cols | {total_size:.1f} MB)")
    for ds in datasets_in_folder:
        name_only = ds['name'].split('/')[-1]
        print(f"  - {name_only:<40} {ds['rows']:>8,} filas | {ds['cols']:>3} cols")
    print()

print('=' * 140)
print()

# Estadisticas generales
print(f"[OK] RESUMEN GENERAL:")
print(f"   Total datasets: {len(datasets)}")
print(f"   Total filas: {sum(d['rows'] for d in datasets):,}")
print(f"   Total columnas: {sum(d['cols'] for d in datasets):,}")
print(f"   Tamano total: {sum(d['size_mb'] for d in datasets):.1f} MB")
print()
print(f"   Dataset mas grande: {max(datasets, key=lambda x: x['size_mb'])['name']} ({max(d['size_mb'] for d in datasets):.1f} MB)")
print(f"   Dataset con mas filas: {max(datasets, key=lambda x: x['rows'])['name']} ({max(d['rows'] for d in datasets):,} filas)")
print(f"   Dataset con mas columnas: {max(datasets, key=lambda x: x['cols'])['name']} ({max(d['cols'] for d in datasets)} cols)")
