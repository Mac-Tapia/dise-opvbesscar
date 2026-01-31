import json
from pathlib import Path

# Load the generated schema
schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
with open(schema_path, 'r') as f:
    schema = json.load(f)

building = schema['buildings']['Mall_Iquitos']

print("=== ELECTRIC VEHICLE CHARGERS ===")
if 'electric_vehicle_chargers' in building:
    evc = building['electric_vehicle_chargers']
    print(f"Type: {type(evc)}")
    print(f"Content (first 500 chars): {str(evc)[:500]}")
    if isinstance(evc, dict):
        print(f"Keys: {list(evc.keys())[:10]}")
    elif isinstance(evc, list):
        print(f"Items: {len(evc)}")
        if len(evc) > 0:
            print(f"First item: {evc[0]}")
else:
    print("NOT FOUND")

print("\n=== CHARGERS ===")
chargers = building['chargers']
print(f"Type: {type(chargers)}")
print(f"Count: {len(chargers)}")
for name, charger_def in list(chargers.items())[:2]:
    print(f"\n  Charger: {name}")
    for k, v in charger_def.items():
        if k != 'charger_simulation':
            print(f"    {k}: {v}")
        else:
            print(f"    charger_simulation: {v}")

print("\n=== ELECTRIC VEHICLES DEF (top-level) ===")
ev_def = schema['electric_vehicles_def']
print(f"Total: {len(ev_def)}")
first_ev_name = list(ev_def.keys())[0]
first_ev = ev_def[first_ev_name]
print(f"First EV: {first_ev_name}")
print(f"  Keys: {list(first_ev.keys())}")
