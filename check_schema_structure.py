import json
from pathlib import Path

# Load the generated schema
schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
with open(schema_path, 'r') as f:
    schema = json.load(f)

# Check for electric_vehicles_def
if 'electric_vehicles_def' in schema:
    print(f'✓ electric_vehicles_def found: {len(schema["electric_vehicles_def"])} EVs')
else:
    print('✗ electric_vehicles_def NOT FOUND')

# Check top-level keys
print(f'\nTop-level keys in schema:')
for k in sorted(schema.keys()):
    if k != 'buildings':
        print(f'  - {k}')

# Check building structure
if 'buildings' in schema:
    b_key = list(schema['buildings'].keys())[0]
    building = schema['buildings'][b_key]
    print(f'\nBuilding "{b_key}" keys:')
    for k in sorted(building.keys()):
        print(f'  - {k}')
        if k == 'electric_vehicles':
            print(f'    → Count: {len(building[k])}')
        if k == 'chargers':
            print(f'    → Charger count: {len(building[k])}')
