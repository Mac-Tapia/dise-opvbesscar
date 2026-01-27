import json
s = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema.json'))
bld = s['buildings']['Mall_Iquitos']
print(f"Chargers type: {type(bld['chargers'])}")
print(f"Chargers count: {len(bld['chargers'])}")
if len(bld['chargers']) > 0:
    chargers_list = list(bld['chargers'].values()) if isinstance(bld['chargers'], dict) else bld['chargers']
    if len(chargers_list) > 0:
        print(f"First charger type: {type(chargers_list[0])}")
        if isinstance(chargers_list[0], dict):
            print(f"First charger keys: {list(chargers_list[0].keys())[:5]}")
        print(f"First charger: {chargers_list[0]}")

    # También mostrar las primeras 5 claves del dict de chargers
    if isinstance(bld['chargers'], dict):
        print(f"Charger keys (first 5): {list(bld['chargers'].keys())[:5]}")
