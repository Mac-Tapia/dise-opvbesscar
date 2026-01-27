#!/usr/bin/env python
"""Check current schema state"""
import json
from pathlib import Path

schema_file = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
with open(schema_file) as f:
    schema = json.load(f)

print("ESTADO ACTUAL DEL SCHEMA:")
print("=" * 60)
print(f"episode_time_steps: {schema.get('episode_time_steps')}")
print(f"simulation_start_time_step: {schema.get('simulation_start_time_step')}")
print(f"simulation_end_time_step: {schema.get('simulation_end_time_step')}")

building = schema['buildings']['Mall_Iquitos']
chargers = building.get('chargers', {})
pv = building.get('pv', {})
bess = building.get('electrical_storage', {})

print(f"\nChargers: {len(chargers)}")
print(f"PV peak_power: {pv.get('attributes', {}).get('peak_power')}")
print(f"BESS capacity: {bess.get('attributes', {}).get('capacity')}")
print(f"BESS power_output_nominal: {bess.get('attributes', {}).get('power_output_nominal')}")
