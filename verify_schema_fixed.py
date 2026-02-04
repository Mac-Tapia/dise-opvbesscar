#!/usr/bin/env python
"""Verificar BESS y Mall Demand en CityLearn dataset"""

import json
from pathlib import Path
import pandas as pd

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
schema_dir = schema_path.parent

print('='*80)
print('[VERIFICATION] BESS + Mall Demand Profiles')
print('='*80)

# Load schema
schema = json.load(open(schema_path))
building = list(schema['buildings'].values())[0]
building_name = building.get('name')

print(f'\n✓ Edificio: {building_name}')
print(f'✓ Schema directorio: {schema_dir}')

# ============================================================================
# [1] BESS Configuration in Schema
# ============================================================================
print('\n' + '─'*80)
print('[1] BESS (Battery Energy Storage System) - Schema Configuration')
print('─'*80)

if 'electrical_storage' in building:
    bess = building['electrical_storage']
    print(f'✓ electrical_storage CONFIGURED')

    # Extract capacity
    cap = bess.get('capacity')
    if cap is None:
        cap = bess.get('attributes', {}).get('capacity')
    print(f'  • Capacidad: {cap} kWh')

    # Extract power
    power = bess.get('nominal_power')
    if power is None:
        power = bess.get('attributes', {}).get('nominal_power')
    print(f'  • Potencia nominal: {power} kW')

    # Energy simulation reference
    if 'energy_simulation' in bess:
        sim_file = bess['energy_simulation']
        print(f'  • Archivo simulacion: {sim_file}')
    else:
        print(f'  • Archivo simulacion: NO CONFIGURADO')
else:
    print(f'✗ electrical_storage NOT CONFIGURED')

# ============================================================================
# [2] Energy Simulation CSV
# ============================================================================
print('\n' + '─'*80)
print('[2] Main Energy Simulation CSV (Mall + Building Load)')
print('─'*80)

energy_csv_name = building.get('energy_simulation')
energy_csv = schema_dir / energy_csv_name if energy_csv_name else None

if energy_csv and energy_csv.exists():
    df = pd.read_csv(energy_csv)
    print(f'✓ {energy_csv_name} EXISTS')
    print(f'  • Rows: {len(df)} (expected: 8760 hourly)')
    print(f'  • Columns: {list(df.columns)}')

    # Find mall demand column
    for col in df.columns:
        if 'non_shiftable' in col.lower() or 'load' in col.lower():
            print(f'\n✓ Mall Demand Column: {col}')
            print(f'    - Min: {df[col].min():.1f} kW')
            print(f'    - Max: {df[col].max():.1f} kW')
            print(f'    - Mean: {df[col].mean():.1f} kW')
            print(f'    - Total: {df[col].sum():.0f} kWh (annual)')
else:
    print(f'✗ Energy CSV NOT FOUND: {energy_csv}')

# ============================================================================
# [3] BESS Energy Simulation File
# ============================================================================
print('\n' + '─'*80)
print('[3] BESS Energy Simulation CSV')
print('─'*80)

bess_sim_candidates = [
    'electrical_storage_simulation.csv',
    'bess_simulation.csv',
    'bess_soc.csv',
]

bess_sim_found = False
for candidate in bess_sim_candidates:
    bess_csv = schema_dir / candidate
    if bess_csv.exists():
        df = pd.read_csv(bess_csv)
        print(f'✓ {candidate} FOUND')
        print(f'  • Rows: {len(df)} (expected: 8760 hourly)')
        print(f'  • Columns: {list(df.columns)}')

        # Analyze SOC data
        col = df.columns[0]
        print(f'  • SOC Column: {col}')
        print(f'    - Min: {df[col].min():.0f} kWh')
        print(f'    - Max: {df[col].max():.0f} kWh')
        print(f'    - Mean: {df[col].mean():.0f} kWh')

        bess_sim_found = True
        break

if not bess_sim_found:
    print(f'✗ BESS simulation file NOT FOUND')
    print(f'  Searched for: {bess_sim_candidates}')

# ============================================================================
# [4] Charger Simulation Files
# ============================================================================
print('\n' + '─'*80)
print('[4] EV Charger Simulation Files (128 sockets)')
print('─'*80)

charger_files = sorted(schema_dir.glob('charger_simulation_*.csv'))
print(f'✓ Charger files found: {len(charger_files)}')

if len(charger_files) > 0:
    # Check if all have 8760 rows
    df_sample = pd.read_csv(charger_files[0])
    print(f'  • Sample file: {charger_files[0].name}')
    print(f'    - Rows: {len(df_sample)} (expected: 8760 hourly)')
    print(f'    - Columns: {list(df_sample.columns)[:3]}')

    # Verify all chargers have 8760 rows
    row_check = []
    for f in charger_files:
        df = pd.read_csv(f)
        row_check.append(len(df))

    if all(r == 8760 for r in row_check):
        print(f'  ✓ All {len(charger_files)} chargers have 8760 rows (correct)')
    else:
        invalid = [charger_files[i].name for i, r in enumerate(row_check) if r != 8760]
        print(f'  ✗ {len(invalid)} chargers have incorrect rows: {invalid[:3]}')

# ============================================================================
# [5] Summary
# ============================================================================
print('\n' + '='*80)
print('[SUMMARY] Configuration Status')
print('='*80)

checks = {
    'BESS Configuration': 'electrical_storage' in building,
    'BESS has energy_simulation': 'energy_simulation' in building.get('electrical_storage', {}),
    'Energy CSV exists': energy_csv and energy_csv.exists(),
    'Energy CSV has 8760 rows': energy_csv and energy_csv.exists() and len(pd.read_csv(energy_csv)) == 8760,
    'BESS sim file exists': bess_sim_found,
    'Charger files >= 128': len(charger_files) >= 128,
}

print()
for check, status in checks.items():
    symbol = '✓' if status else '✗'
    print(f'{symbol} {check}')

all_ok = all(checks.values())
print('\n' + '='*80)
if all_ok:
    print('✅ ALL COMPONENTS CORRECTLY CONFIGURED')
else:
    print('⚠️  Some components need review or data reconstruction')
print('='*80)
