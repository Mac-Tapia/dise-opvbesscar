import json
s = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'))
b = s['buildings']['Mall_Iquitos']
asset_types = [a.get('type') for a in b.get('assets', [])]
print("Asset types in schema:", asset_types)
print("Has PV?", 'PhotovoltaicSystem' in asset_types)
print("Has Battery?", 'Battery' in asset_types)
print("Total assets:", len(b.get('assets', [])))

# Show first 5 assets
for i, a in enumerate(b.get('assets', [])[:5]):
    print(f"  Asset {i}: {a.get('type')} - {a.get('_name', a.get('name', 'unnamed'))}")
