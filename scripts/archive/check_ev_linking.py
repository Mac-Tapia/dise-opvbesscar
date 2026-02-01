import json
from pathlib import Path

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
with open(schema_path, 'r') as f:
    schema = json.load(f)

building = schema['buildings']['Mall_Iquitos']
evc = building['electric_vehicle_chargers']

# Get first charger
charger_name = list(evc.keys())[0]
charger_def = evc[charger_name]

print(f"Charger: {charger_name}")
print(f"Keys: {list(charger_def.keys())}")
print(f"\nDefinition:")
for k, v in charger_def.items():
    if isinstance(v, dict):
        print(f"  {k}: (dict with {len(v)} keys)")
    elif isinstance(v, str) and len(v) > 50:
        print(f"  {k}: {v[:50]}...")
    else:
        print(f"  {k}: {v}")

# Check if there's an "electric_vehicles" list in the building
print(f"\n\nDoes building have 'electric_vehicles' key? {('electric_vehicles' in building)}")

# What SHOULD be there for CityLearn to recognize EVs?
print("\nFor CityLearn 2.5.0 to work, we need:")
print("  - electric_vehicles_def at schema level ✓")
print("  - electric_vehicle_chargers in building ✓")
print("  - Each charger MIGHT need reference to an EV")
print("  - OR electric_vehicles list in building (1:1 mapping with chargers?)")
