#!/usr/bin/env python3
"""Verificar que archivos en iquitos_ev_mall coinciden con reporte"""

import pandas as pd
from pathlib import Path

print('=' * 80)
print('VERIFICACION DE ARCHIVOS - iquitos_ev_mall/')
print('=' * 80)

dir_path = Path('data/processed/citylearn/iquitos_ev_mall')

# Archivos que reporté
reported_files = {
    'citylearnv2_combined_dataset.csv': {'expected_rows': 8760, 'expected_cols': 22},
    'solar_generation.csv': {'expected_rows': 8760, 'expected_cols': 11},
    'bess_timeseries.csv': {'expected_rows': 8760, 'expected_cols': 27},
    'chargers_timeseries.csv': {'expected_rows': 8760, 'expected_cols': 1060},
    'mall_demand.csv': {'expected_rows': 8760, 'expected_cols': 6},
    'dataset_config_v7.json': {'type': 'json'},
}

print('\n📂 ARCHIVOS QUE REPORTÉ:')
for filename, specs in reported_files.items():
    print(f'  • {filename}')

print('\n📂 ARCHIVOS QUE EXISTEN EN CARPETA:')
actual_files = sorted([f.name for f in dir_path.glob('*')])
for filename in actual_files:
    filepath = dir_path / filename
    size_mb = filepath.stat().st_size / (1024*1024)
    print(f'  • {filename:<40} ({size_mb:.2f} MB)')

print('\n' + '=' * 80)
print('VALIDACIÓN DE CONTENIDO:')
print('=' * 80)

# Verificar shape de cada CSV
csv_files = [f for f in actual_files if f.endswith('.csv')]
print(f'\nCSV Files ({len(csv_files)}):')
for csv_file in csv_files:
    filepath = dir_path / csv_file
    df = pd.read_csv(filepath)
    expected = reported_files.get(csv_file, {})
    exp_rows = expected.get('expected_rows', '?')
    exp_cols = expected.get('expected_cols', '?')
    
    match_rows = '✅' if df.shape[0] == exp_rows else f'❌ ({exp_rows} expected)'
    match_cols = '✅' if df.shape[1] == exp_cols else f'❌ ({exp_cols} expected)'
    
    print(f'\n  {csv_file}')
    print(f'    Rows: {df.shape[0]} {match_rows}')
    print(f'    Cols: {df.shape[1]} {match_cols}')
    print(f'    Cols list: {list(df.columns)[:5]}...')

# Check JSON
import json
json_files = [f for f in actual_files if f.endswith('.json')]
print(f'\nJSON Files ({len(json_files)}):')
for json_file in json_files:
    filepath = dir_path / json_file
    with open(filepath) as f:
        data = json.load(f)
    print(f'\n  {json_file}')
    print(f'    Keys: {list(data.keys())}')
    if 'system' in data:
        print(f'    BESS capacity: {data["system"].get("bess_capacity_kwh")} kWh ✅')

print('\n' + '=' * 80)
print('VERIFICACIÓN COMPLETADA')
print('=' * 80)

# List comparison
reported_names = set(reported_files.keys())
actual_names = set(actual_files)

if reported_names == actual_names:
    print('✅ COINCIDEN PERFECTAMENTE')
    print('   Todos los archivos reportados existen y tienen los nombres correctos')
else:
    print('⚠️ DISCREPANCIAS ENCONTRADAS:')
    if reported_names - actual_names:
        print(f'   Reporté pero no existen: {reported_names - actual_names}')
    if actual_names - reported_names:
        print(f'   Existen pero no reporté: {actual_names - reported_names}')
