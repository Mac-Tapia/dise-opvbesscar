#!/usr/bin/env python
"""Diagnose CityLearn environment performance"""
from citylearn.citylearn import CityLearnEnv
import time
from pathlib import Path

# Find schema
schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
if not schema_path.exists():
    print("ERROR: No schema file found")
    exit(1)

print(f"Loading schema: {schema_path}\n")

# Create environment
env = CityLearnEnv(str(schema_path))

# Diagnostics
print('=== ENVIRONMENT DIAGNOSTICS ===')
print(f'Buildings: {len(env.buildings)}')
b = env.buildings[0]
print(f'Building name: {b.name}')
print(f'Has chargers: {hasattr(b, "chargers")}')
print(f'Has electric_vehicles: {hasattr(b, "electric_vehicles")}')

if hasattr(b, 'electric_vehicles'):
    print(f'Electric vehicles count: {len(b.electric_vehicles)}')
    if len(b.electric_vehicles) > 0:
        ev = b.electric_vehicles[0]
        print(f'  - First EV type: {type(ev).__name__}')
        print(f'  - Has battery: {hasattr(ev, "battery")}')

# Check passive devices
if hasattr(b, 'passive_devices'):
    device_types: dict[str, int] = {}
    for d in b.passive_devices:
        dtype = type(d).__name__
        device_types[dtype] = device_types.get(dtype, 0) + 1
    print(f'Passive devices: {device_types}')

# Reset and measure
print(f'\n=== PERFORMANCE MEASUREMENT ===')
obs, info = env.reset()
print(f'Observation length: {len(obs)}')

# Time 100 steps
start = time.time()
for i in range(100):
    obs, reward, done, truncated, info = env.step([0.5] * 126)
elapsed = time.time() - start

steps_per_sec = 100 / elapsed
print(f'100 steps: {elapsed:.3f} seconds')
print(f'Performance: {steps_per_sec:.0f} steps/second')

# Extrapolate
full_year = (8760 * elapsed) / 100
print(f'\nProjected 8,760 steps: {full_year:.1f} seconds ({full_year/60:.2f} minutes)')
print(f'Expected (realistic):   250-300 seconds (4-5 minutes)')
print(f'RATIO (actual/expected): {full_year/275:.1f}x')

if full_year < 60:
    print('\n⚠️  ENVIRONMENT STILL SIMPLIFIED - Should be 4-5 minutes, is <1 minute')
    print('Checking what might be missing...')

    # Check for physics simulation details
    print('\nChecking physics simulation:')
    print(f'  - BESS has dynamics: Check electrical_storage_simulation.csv')
    print(f'  - Chargers active: {len(b.electric_vehicles)} EVs')
    print(f'  - PV generation: Check weather.csv')
