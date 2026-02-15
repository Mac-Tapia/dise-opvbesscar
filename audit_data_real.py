#!/usr/bin/env python3
"""
AUDITORIA INTEGRAL: Verificar que SOLO se usan datos REALES OE2
eleimnar cualquier sintético o hardcoded
"""
import re
import pandas as pd
from pathlib import Path

print('='*80)
print('AUDITORIA INTEGRAL: DATOS REALES vs SINTETICOS')
print('='*80)
print()

filepath = Path('scripts/train/train_sac_multiobjetivo.py')
content = filepath.read_text(encoding='utf-8')

# 1. Verificar que TODOS los datasets cargen desde archivos reales
print('[1] VERIFICACION DE ORIGEN DE DATOS')
print('-'*80)

real_files = {
    'SOLAR': 'data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv',
    'CHARGERS': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'MALL': 'data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
}

print('Archivos reales esperados:')
for name, path in real_files.items():
    p = Path(path)
    if p.exists():
        size = p.stat().st_size / 1024 / 1024
        print(f'  [OK] {name:12} {size:7.2f} MB  {path}')
    else:
        print(f'  [MISSING] {name:12}  {path}')

print()
print('[2] BUSCAR DATOS SINTETICOS O HARDCODED EN CODIGO')
print('-'*80)

# Patrones que indican datos sinteticos
synthetic_issues = []

# Check for random generation
if 'np.random' in content:
    count = content.count('np.random')
    print(f'  [WARN] np.random encontrado {count} veces')
    synthetic_issues.append(f'np.random ({count} uses)')

# Check for hardcoded arrays
hardcoded_zeros = content.count('np.zeros')
hardcoded_ones = content.count('np.ones')
if hardcoded_zeros > 0:
    print(f'  [WARN] np.zeros encontrado {hardcoded_zeros} veces')
    synthetic_issues.append(f'np.zeros ({hardcoded_zeros} uses)')
if hardcoded_ones > 0:
    print(f'  [WARN] np.ones encontrado {hardcoded_ones} veces')
    synthetic_issues.append(f'np.ones ({hardcoded_ones} uses)')

# Check for simulated vehicles
if 'spawn_vehicle' in content or 'VehicleSOCState' in content:
    count = content.count('spawn_vehicle') + content.count('VehicleSOCState')
    print(f'  [WARN] Datos sinteticos de vehiculos: {count} references')
    synthetic_issues.append('Simulated vehicles (spawn_vehicle)')

if not synthetic_issues:
    print('  [OK] NO ENCONTRADOS patrones sinteticos')

print()
print('[3] FUNCIONES DE CARGA DE DATOS REALES')
print('-'*80)

functions = {
    'load_datasets_from_processed': False,
    'load_observable_variables': False,
    'validate_solar_timeseries_hourly': False,
    'RealOE2Environment': False,
}

for func_name in functions:
    if f'def {func_name}' in content or f'class {func_name}' in content:
        functions[func_name] = True
        print(f'  [OK] {func_name} definida')
    else:
        print(f'  [ERROR] {func_name} NO ENCONTRADA')

print()
print('[4] CARGAS DE DATOS REALES EN load_datasets_from_processed()')
print('-'*80)

# Find function and check what it loads
if 'def load_datasets_from_processed' in content:
    # Extract function
    match = re.search(
        r'def load_datasets_from_processed\(\):.*?(?=\ndef |\nclass |\Z)',
        content,
        re.DOTALL
    )
    if match:
        func_text = match.group(0)
        
        # Check for each file
        checks = [
            ('SOLAR', 'pv_generation_hourly_citylearn_v2.csv', 'ac_power_kw'),
            ('CHARGERS', 'chargers_ev_ano_2024_v3.csv', 'chargers_hourly'),
            ('MALL', 'demandamallhorakwh.csv', 'mall'),
            ('BESS', 'bess_ano_2024.csv', 'bess_soc'),
        ]
        
        for name, filename, var_pattern in checks:
            has_file = filename in func_text
            has_var = var_pattern in func_text
            
            if has_file and has_var:
                print(f'  [OK] {name:12} carga archivo real y asigna a variable')
            elif has_file:
                print(f'  [PARTIAL] {name:12} carga archivo pero variable puede estar mal')
            else:
                print(f'  [ERROR] {name:12} NO carga archivo real')

print()
print('[5] CONSTANTES REALES vs HARDCODED')
print('-'*80)

constants = {
    'BESS_CAPACITY_KWH': '940.0',
    'CO2_FACTOR_IQUITOS': '0.4521',
    'SOLAR_MAX_KW': '4100.0',
    'CHARGER_MAX_KW': '10.0',
    'HOURS_PER_YEAR': '8760',
}

for const_name, expected_value in constants.items():
    pattern = f'{const_name}\\s*=\\s*[^#]*'
    match = re.search(pattern, content)
    if match:
        actual = match.group(0)
        if expected_value in actual:
            print(f'  [OK] {const_name} = {expected_value}')
        else:
            print(f'  [WARN] {const_name} VALUE MISMATCH')
            print(f'        Expected: {expected_value}')
            print(f'        Found: {actual[:60]}')
    else:
        print(f'  [MISSING] {const_name}')

print()
print('='*80)
print('RESUMEN')
print('='*80)

# Calculate score
issues = len(synthetic_issues)
if issues == 0:
    print('[OK] CODIGO SINCRONIZADO CON DATOS REALES OE2')
    print('     NO ENCONTRADOS:')
    print('       - Datos sinteticos hardcoded')
    print('       - Variable aleatoria (np.random)')
    print('       - Calulos simulados')
else:
    print(f'[WARN] {issues} PROBLEMAS ENCONTRADOS:')
    for issue in synthetic_issues:
        print(f'       - {issue}')
    print()
    print('ACCIONES REQUERIDAS:')
    print('  1. Eliminar np.random en favor de datos cargados')
    print('  2. Verificar que TODAS variables usen datos cargados')
    print('  3. Validar integridad 8,760 horas (1 anno)')

print()
