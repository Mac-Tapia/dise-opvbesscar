#!/usr/bin/env python
"""Verify that schema has 128 chargers with correct CSV references."""

import json
from pathlib import Path

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
with open(schema_path) as f:
    schema = json.load(f)

chargers = schema['buildings']['Mall_Iquitos']['chargers']
print(f'✓ Total chargers en schema: {len(chargers)}')
print(f'✓ Primeros 5 nombres: {list(chargers.keys())[:5]}')
print(f'✓ Últimos 5 nombres: {list(chargers.keys())[-5:]}')

# Verificar que apuntan a archivos correctos
print('\n' + '='*70)
print('VERIFICACIÓN DE ARCHIVOS CSV')
print('='*70)

first_charger_name = list(chargers.keys())[0]
first_charger = chargers[first_charger_name]
print(f'\n✓ Primer charger ({first_charger_name}):')
print(f'  - CSV file: {first_charger.get("charger_simulation", "N/A")}')
if 'attributes' in first_charger:
    print(f'  - Nominal power: {first_charger["attributes"].get("nominal_power", "N/A")} kW')

last_charger_name = list(chargers.keys())[-1]
last_charger = chargers[last_charger_name]
print(f'\n✓ Último charger ({last_charger_name}):')
print(f'  - CSV file: {last_charger.get("charger_simulation", "N/A")}')
if 'attributes' in last_charger:
    print(f'  - Nominal power: {last_charger["attributes"].get("nominal_power", "N/A")} kW')

# Verify all CSV files exist
print('\n' + '='*70)
print('VERIFICACIÓN DE EXISTENCIA DE ARCHIVOS')
print('='*70)

building_dir = Path('data/processed/citylearn/iquitos_ev_mall/buildings/Mall_Iquitos')
csv_files = list(building_dir.glob('charger_simulation_*.csv'))
print(f'\n✓ Archivos CSV encontrados en filesystem: {len(csv_files)}')

# Check if all chargers have matching CSV files
missing_csv = 0
for charger_name, charger_data in chargers.items():
    csv_file = charger_data.get('charger_simulation', '')
    csv_path = Path('data/processed/citylearn/iquitos_ev_mall') / csv_file
    if not csv_path.exists():
        missing_csv += 1
        if missing_csv <= 5:
            print(f'  ⚠️ FALTA: {charger_name} -> {csv_file}')

if missing_csv == 0:
    print(f'\n✅ TODOS los 128 chargers tienen archivos CSV válidos')
else:
    print(f'\n❌ {missing_csv} chargers sin archivos CSV')

print('\n' + '='*70)
print('RESULTADO FINAL')
print('='*70)
if len(chargers) == 128 and missing_csv == 0:
    print('\n✅ ✅ ✅ SCHEMA CORRECTAMENTE CONFIGURADO CON 128 CHARGERS')
    print('   Lista para inicializar CityLearn y entrenar agentes RL')
else:
    print(f'\n❌ Problemas detectados:')
    print(f'   - Chargers en schema: {len(chargers)} (esperados: 128)')
    print(f'   - Chargers sin CSV: {missing_csv}')
