import json

schema = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema.json'))

print('=== TOP-LEVEL KEYS ===')
for k in sorted(schema.keys()):
    if k != 'buildings':
        print(f'  {k}')

# Check if electric_vehicles_def exists
if 'electric_vehicles_def' in schema:
    print(f'\n⚠️  electric_vehicles_def FOUND (should NOT be there)')
    print(f'   Count: {len(schema["electric_vehicles_def"])}')
else:
    print(f'\n✓ electric_vehicles_def NOT present (correct)')

# Check building chargers
b = schema['buildings']['Mall_Iquitos']
evc = b.get('electric_vehicle_chargers', {})
print(f'\n✓ Building has electric_vehicle_chargers: {len(evc)} chargers')

# Check if building has electric_vehicles list
if 'electric_vehicles' in b:
    print(f'⚠️  Building has electric_vehicles list: {len(b["electric_vehicles"])} entries')
else:
    print(f'✓ Building has NO electric_vehicles list (correct)')

print('\n=== CHARGER SAMPLE ===')
first_charger = list(evc.values())[0]
print(f'Charger keys: {list(first_charger.keys())}')
print(f'Has charger_simulation: {("charger_simulation" in first_charger)}')
