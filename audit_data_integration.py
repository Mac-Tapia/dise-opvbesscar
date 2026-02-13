#!/usr/bin/env python3
"""Auditoría completa de carga y uso de datos BESS, costos y CO2"""
from pathlib import Path
import pandas as pd
import json
import re

print('='*80)
print('AUDITORÍA DE DATOS - Verificar qué se carga en el entrenamiento')
print('='*80)
print()

# 1. Revisar BESS dataset real
bess_file = Path('data/oe2/bess/bess_simulation_hourly.csv')
if bess_file.exists():
    df_bess = pd.read_csv(bess_file)
    soc_max = df_bess['soc_kwh'].max()
    print('1. BESS DATASET REAL (data/oe2/bess/bess_simulation_hourly.csv):')
    print(f'   Max SOC: {soc_max:.0f} kWh')
    print(f'   Columns: {list(df_bess.columns)[:10]}...')
    print()

    # 2. Verificar datos de costos
    print('2. DATOS DE COSTOS EN BESS DATASET:')
    if 'cost_grid_import_soles' in df_bess.columns:
        cost_sum = df_bess['cost_grid_import_soles'].sum()
        print(f'   [OK] cost_grid_import_soles: suma={cost_sum:.2f} soles')
    else:
        print('   [X] cost_grid_import_soles: NO ENCONTRADO')
    
    if 'savings_bess_soles' in df_bess.columns:
        savings = df_bess['savings_bess_soles'].sum()
        print(f'   [OK] savings_bess_soles: suma={savings:.2f} soles')
    else:
        print('   [X] savings_bess_soles: NO ENCONTRADO')
    
    if 'tariff_soles_kwh' in df_bess.columns:
        peak_tariff = df_bess[df_bess['is_peak_hour']==1]['tariff_soles_kwh'].iloc[0] if len(df_bess[df_bess['is_peak_hour']==1]) > 0 else None
        normal_tariff = df_bess[df_bess['is_peak_hour']==0]['tariff_soles_kwh'].iloc[0] if len(df_bess[df_bess['is_peak_hour']==0]) > 0 else None
        if peak_tariff:
            print(f'   [OK] tariff_soles_kwh: picos={peak_tariff:.2f}, normal={normal_tariff:.2f}')
    else:
        print('   [X] tariff_soles_kwh: NO ENCONTRADO')
    print()

    # 3. Verificar datos de CO2
    print('3. DATOS DE CO2 EN BESS DATASET:')
    if 'co2_grid_kg' in df_bess.columns:
        co2_grid = df_bess['co2_grid_kg'].sum()
        print(f'   [OK] co2_grid_kg: {co2_grid:.0f} kg/año')
    else:
        print('   [X] co2_grid_kg: NO ENCONTRADO')
    
    if 'co2_avoided_kg' in df_bess.columns:
        co2_avoided = df_bess['co2_avoided_kg'].sum()
        print(f'   [OK] co2_avoided_kg: {co2_avoided:.0f} kg/año')
    else:
        print('   [X] co2_avoided_kg: NO ENCONTRADO')
    print()

# 4. Verificar qué tan bien está configurado el reward para CO2
print('4. FACTOR CO2 EN train_sac_multiobjetivo.py:')
with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
    has_co2_factor = False
    for i, line in enumerate(f, 1):
        if 'CO2_FACTOR' in line or '0.4521' in line:
            print(f'   Line {i}: {line.strip()}')
            has_co2_factor = True
    if not has_co2_factor:
        print('   [X] NO SE ENCONTRÓ CO2_FACTOR en el archivo')
print()

# 5. Verificar BESS capacity en train_sac
print('5. BESS CAPACITY EN train_sac_multiobjetivo.py:')
with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
    content = f.read()
    bess_cap_matches = [(i+1, line.strip()) for i, line in enumerate(content.split('\n')) if 'BESS_CAPACITY' in line]
    if bess_cap_matches:
        for line_num, line_text in bess_cap_matches:
            print(f'   Line {line_num}: {line_text}')
    else:
        print('   [X] NO SE ENCONTRÓ BESS_CAPACITY')
print()

# 6. Verificar si hay configuración en JSON/YAML
print('6. CONFIGURACIÓN EN ARCHIVOS JSON/YAML:')
config_files = [
    'configs/default.yaml',
    'configs/sac_optimized.json',
    'configs/agents/sac_config.yaml',
]
for cf in config_files:
    p = Path(cf)
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
            has_bess = '1700' in content or '4520' in content or 'bess' in content.lower()
            status = '[OK]' if has_bess else '[X]'
            print(f'   {status} {cf}: {"Configura BESS" if has_bess else "No contiene config BESS"}')
    else:
        print(f'   [X] {cf}: NO EXISTE')
print()

# 7. Verificar cómo se cargan datos en load_datasets_from_processed()
print('7. VERIFICAR FUNCIÓN load_datasets_from_processed() EN train_sac.py:')
with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    in_func = False
    func_lines = []
    for i, line in enumerate(lines):
        if 'def load_datasets_from_processed' in line:
            in_func = True
            print(f'   Encontrada en línea {i+1}')
        if in_func:
            func_lines.append((i+1, line.rstrip()))
            if line.strip() and not line[0].isspace() and i > 0 and in_func and 'def load_datasets_from_processed' not in line:
                break
    
    # Buscar referencias a BESS en la función
    bess_refs = [l for l in func_lines if 'bess' in l[1].lower()]
    if bess_refs:
        print('   Referencias a BESS encontradas:')
        for line_num, line_text in bess_refs[:5]:
            print(f'      Line {line_num}: {line_text[:70]}...')
    else:
        print('   [X] NO hay referencias a BESS en load_datasets_from_processed()')
print()

# 8. Verificar data_loader.py
print('8. REVISAR src/dimensionamiento/oe2/disenocargadoresev/data_loader.py:')
data_loader_path = Path('src/dimensionamiento/oe2/disenocargadoresev/data_loader.py')
if data_loader_path.exists():
    with open(data_loader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar clase BESSData
    if 'class BESSData' in content:
        print('   [OK] Clase BESSData encontrada')
        # Extraer parámetros
        match = re.search(r'class BESSData.*?(?=class |\Z)', content, re.DOTALL)
        if match:
            class_def = match.group(0)
            params = re.findall(r'(\w+):\s*float', class_def)
            print(f'   Parámetros: {", ".join(params[:5])}')
    else:
        print('   [X] Clase BESSData NO encontrada')
    
    # Buscar si data_loader es importado en train_sac
    with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
        if 'data_loader' in f.read():
            print('   [OK] data_loader está siendo importado en train_sac_multiobjetivo.py')
        else:
            print('   [X] data_loader NO está siendo importado en train_sac_multiobjetivo.py')
else:
    print(f'   [X] Archivo no encontrado en {data_loader_path}')

print()
print('='*80)
print('RESUMEN: Esta auditoría identifica qué datos están disponibles y cómo se cargan')
print('='*80)
