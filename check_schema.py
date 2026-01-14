import json

# Check schema structure
with open('data/processed/citylearn/iquitos_ev_mall/schema.json') as f:
    schema = json.load(f)

# Find chargers in building
if 'buildings' in schema:
    for bname, bdata in schema['buildings'].items():
        print(f"\nBuilding: {bname}")
        print(f"Building keys: {list(bdata.keys())}")
        
        if 'electric_vehicle_chargers' in bdata:
            chargers = bdata['electric_vehicle_chargers']
            print(f"  Found {len(chargers)} EV chargers")
            if len(chargers) > 0:
                c0 = chargers[0]
                print(f"  First charger keys: {list(c0.keys())}")
                print(f"  First charger data_file: {c0.get('data_file')}")
        break
