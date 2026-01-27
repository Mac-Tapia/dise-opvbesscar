#!/usr/bin/env python
"""Find chargers location in schema"""
import json

with open('data/processed/citylearn/iquitos_ev_mall/schema.json') as f:
    schema = json.load(f)

building = schema['buildings']['Mall_Iquitos']

# Buscar chargers
if 'chargers' in building:
    chargers = building['chargers']
    print(f"✅ 'chargers' encontrado: {len(chargers)} items")
    if chargers:
        first_key = list(chargers.keys())[0]
        print(f"\nPrimer charger: {first_key}")
        print(f"  Estructura: {list(chargers[first_key].keys())}")
else:
    print("❌ 'chargers' NO encontrado en building")

# Buscar electrical_devices
if 'electrical_devices' in building:
    devs = building['electrical_devices']
    print(f"\n✅ 'electrical_devices' encontrado: {len(devs)} items")
else:
    print("❌ 'electrical_devices' NO encontrado")

# PV peak power
pv_attrs = building.get('pv', {}).get('attributes', {})
print(f"\nPV peak_power actual: {pv_attrs.get('peak_power')}")

# BESS capacity
bess_attrs = building.get('electrical_storage', {}).get('attributes', {})
print(f"BESS capacity actual: {bess_attrs.get('capacity')}")
print(f"BESS power_output_nominal actual: {bess_attrs.get('power_output_nominal')}")
