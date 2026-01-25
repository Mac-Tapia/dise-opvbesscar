#!/usr/bin/env python
"""Quick test of charger JSON structure."""

import json

c = json.load(open('data/interim/oe2/chargers/individual_chargers.json'))
print(f'Total chargers: {len(c)}')
print(f'First charger keys: {list(c[0].keys())}')

charger = c[0]
hourly = charger['hourly_load_profile']
print(f'Hourly profile type: {type(hourly)}')
print(f'Hourly profile length: {len(hourly)}')

if isinstance(hourly, list):
    print(f'First hourly item: {hourly[0]}')
    print(f'Second hourly item: {hourly[1]}')

# Also check if there's a separate CSV with profiles
import os
csv_files = [f for f in os.listdir('data/interim/oe2/chargers/') if f.endswith('.csv')]
print(f'\nCSV files in chargers/: {csv_files}')

if 'charger_hourly_profiles.csv' in csv_files:
    import pandas as pd
    df = pd.read_csv('data/interim/oe2/chargers/charger_hourly_profiles.csv')
    print(f'Charger hourly profiles shape: {df.shape}')
    print(f'Charger hourly profiles columns: {list(df.columns[:5])}...')
