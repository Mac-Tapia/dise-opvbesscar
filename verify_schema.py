#!/usr/bin/env python
"""Verificar BESS y Mall Demand en schema del edificio"""

import json
from pathlib import Path
import pandas as pd

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')

print("=" * 80)
print("[SCHEMA VERIFICATION] BESS + Mall Demand Configuration")
print("=" * 80)

if not schema_path.exists():
    print(f"\n✗ Schema not found: {schema_path}")
    exit(1)

schema = json.load(open(schema_path))
building = list(schema['buildings'].values())[0]
building_name = building.get('name', 'Building_1')
building_dir = schema_path.parent / 'buildings' / building_name

# ============================================================================
# 1. BESS CONFIGURATION
# ============================================================================
print('\n[1] BESS (Battery Energy Storage System)')
print("-" * 80)

if 'electrical_storage' in building:
    bess = building['electrical_storage']
    print(f'  ✓ electrical_storage CONFIGURED')
    print(f'    - Type: {bess.get("type", "?")}')

    # Capacidad
    cap = bess.get('capacity') or (bess.get('attributes', {}).get('capacity'))
    print(f'    - Capacidad: {cap} kWh')

    # Potencia nominal
    power = bess.get('nominal_power') or (bess.get('attributes', {}).get('nominal_power'))
    print(f'    - Potencia nominal: {power} kW')

    # Energy simulation file
    if 'energy_simulation' in bess:
        print(f'    - ✓ Energy simulation: {bess["energy_simulation"]}')
    else:
        print(f'    - ✗ NO energy_simulation file configured')
else:
    print(f'  ✗ electrical_storage NOT CONFIGURED')

# ============================================================================
# 2. MALL DEMAND (non_shiftable_load)
# ============================================================================
print('\n[2] MALL DEMAND (non_shiftable_load)')
print("-" * 80)

energy_sim = building.get('energy_simulation', {})
if isinstance(energy_sim, dict) and 'non_shiftable_load' in energy_sim:
    nsl = energy_sim['non_shiftable_load']
    print(f'  ✓ non_shiftable_load IN SCHEMA')
    print(f'    - Value/Type: {type(nsl).__name__} = {nsl}')
else:
    print(f'  ! non_shiftable_load not in schema (loaded from CSV)')

# ============================================================================
# 3. BUILDING FILES
# ============================================================================
print('\n[3] BUILDING CSV FILES')
print("-" * 80)

if building_dir.exists():
    print(f'  ✓ Building directory: {building_dir.name}')

    csv_files = sorted(building_dir.glob('*.csv'))
    print(f'  ✓ Total CSV files: {len(csv_files)}')

    # Categorizar por tipo
    bess_files = [f for f in csv_files if 'electrical_storage' in f.name.lower()]
    charger_files = [f for f in csv_files if 'charger' in f.name.lower()]
    other_files = [f for f in csv_files if f not in bess_files + charger_files]

    if bess_files:
        print(f'\n  BESS Files: {len(bess_files)}')
        for f in bess_files:
            print(f'    • {f.name}')

    if charger_files:
        print(f'\n  Charger Files: {len(charger_files)}')
        print(f'    • charger_simulation_001.csv through charger_simulation_{len(charger_files):03d}.csv')

    if other_files:
        print(f'\n  Other Files: {len(other_files)}')
        for f in other_files[:5]:
            print(f'    • {f.name}')
        if len(other_files) > 5:
            print(f'    ... and {len(other_files)-5} more')
else:
    print(f'  ✗ Building directory NOT found')

# ============================================================================
# 4. DATA VALIDATION
# ============================================================================
print('\n[4] DATA VALIDATION (CSV Contents)')
print("-" * 80)

# BESS data
bess_csv = building_dir / 'electrical_storage_simulation.csv'
if bess_csv.exists():
    df_bess = pd.read_csv(bess_csv)
    print(f'\n  BESS Simulation: {bess_csv.name}')
    print(f'    ✓ Rows: {len(df_bess)} (expected: 8760 for hourly annual)')
    print(f'    ✓ Columns: {list(df_bess.columns)}')
    if len(df_bess) > 0:
        col = df_bess.columns[0]
        print(f'    ✓ SOC range: {df_bess[col].min():.1f} - {df_bess[col].max():.1f} kWh')
        print(f'    ✓ Mean SOC: {df_bess[col].mean():.1f} kWh')
else:
    print(f'\n  ✗ BESS simulation file NOT found: {bess_csv.name}')

# Mall demand data
mall_csv_candidates = [
    'non_shiftable_load.csv',
    'energy_simulation.csv',
]

mall_found = False
for candidate in mall_csv_candidates:
    path = building_dir / candidate
    if path.exists():
        df_mall = pd.read_csv(path)
        print(f'\n  Mall Demand: {candidate}')
        print(f'    ✓ Rows: {len(df_mall)}')
        print(f'    ✓ Columns: {list(df_mall.columns)[:5]}')

        # Find demand column
        for col in df_mall.columns:
            if any(tag in col.lower() for tag in ['load', 'demand', 'consumption']):
                print(f'    ✓ Demand column: {col}')
                print(f'      - Range: {df_mall[col].min():.1f} - {df_mall[col].max():.1f} kW')
                print(f'      - Mean: {df_mall[col].mean():.1f} kW')
                print(f'      - Total: {df_mall[col].sum():.0f} kWh (annual)')
                break

        mall_found = True
        break

if not mall_found:
    print(f'\n  ! Mall demand file not found in expected locations')

# ============================================================================
# 5. CHARGER VALIDATION
# ============================================================================
print('\n[5] EV CHARGER FILES')
print("-" * 80)

charger_files = sorted(building_dir.glob('charger_simulation_*.csv'))
print(f'  ✓ Charger simulation files: {len(charger_files)}')

if len(charger_files) > 0:
    # Sample first charger
    df_ch = pd.read_csv(charger_files[0])
    print(f'  ✓ First charger: {charger_files[0].name}')
    print(f'    - Rows: {len(df_ch)}')
    print(f'    - Columns: {list(df_ch.columns)}')

    # Verify all have 8760 rows
    invalid_chargers = []
    for f in charger_files:
        df = pd.read_csv(f)
        if len(df) != 8760:
            invalid_chargers.append(f.name)

    if invalid_chargers:
        print(f'  ✗ {len(invalid_chargers)} chargers have incorrect row count')
    else:
        print(f'  ✓ All {len(charger_files)} chargers have 8760 rows (hourly annual)')

# ============================================================================
# SUMMARY
# ============================================================================
print('\n' + "=" * 80)
print("SUMMARY")
print("=" * 80)

checks = {
    'BESS Configuration': 'electrical_storage' in building,
    'BESS Energy Simulation': bess_csv.exists() if 'electrical_storage' in building else False,
    'Mall Demand Data': mall_found,
    'Charger Files (128)': len(charger_files) == 128,
    'Charger Rows (8760)': all(len(pd.read_csv(f)) == 8760 for f in charger_files[:5]),  # Sample check
}

for check, status in checks.items():
    symbol = '✓' if status else '✗'
    print(f"  {symbol} {check}")

all_ok = all(checks.values())
print('\n' + "=" * 80)
if all_ok:
    print("✅ ALL CHECKS PASSED - Schema correctly configured!")
else:
    print("⚠️  SOME CHECKS FAILED - Review configuration")
print("=" * 80)
