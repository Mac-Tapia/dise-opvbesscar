#!/usr/bin/env python3
import json
s = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema.json'))
b = s['buildings']['Mall_Iquitos']
n_chargers = len(b.get('chargers', {}))
print(f'✅ Chargers en schema: {n_chargers}')
chargers = list(b.get('chargers', {}).keys())
print(f'Primeros 3: {chargers[:3]}')
print(f'Ultimos 3: {chargers[-3:]}')
