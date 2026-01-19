#!/usr/bin/env python3
"""Verificar observables de playas en schema"""

import json

schema = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema_with_128_chargers.json'))

print('OBSERVABLES EN SCHEMA CITYLEARN')
print('='*80)

# Observables de carga
ev_obs = [k for k in schema['observations'].keys() if 'ev_charging' in k or 'charger' in k]

print(f'Total observables EV: {len(ev_obs)}')

print(f'\nObservables agregados:')
for obs in sorted(ev_obs)[:3]:
    print(f'  - {obs}')

print(f'\nObservables individuales Motos (primeros 5):')
for obs in sorted(ev_obs)[3:8]:
    print(f'  - {obs}')

print(f'\nObservables individuales Mototaxis (ultimos 5):')
for obs in sorted(ev_obs)[-5:]:
    print(f'  - {obs}')

# Cargar metadata
metadata = json.load(open('data/processed/citylearn/iquitos_ev_mall/charger_metadata.json'))
print(f'\nMETADATA DE 128 CHARGERS')
print('='*80)
total = metadata['total_chargers']
print(f'Total chargers: {total}')
print(f'\nPlayas:')
for playa, info in metadata['playas'].items():
    print(f'  {playa}:')
    chargers_count = info['chargers']
    sockets_count = info['sockets']
    potencia = info['total_power_kw']
    print(f'    - Chargers: {chargers_count}')
    print(f'    - Sockets: {sockets_count}')
    print(f'    - Potencia: {potencia:.0f} kW')
