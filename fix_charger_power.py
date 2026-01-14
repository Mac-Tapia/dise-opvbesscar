#!/usr/bin/env python
"""
Fix charger CSV files to include power column and ensure correct structure for CityLearn.
"""
import pandas as pd
from pathlib import Path
import json

# Load config
with open('configs/default.yaml') as f:
    import yaml
    cfg = yaml.safe_load(f)

chargers_dir = Path('data/processed/citylearn/iquitos_ev_mall')
charger_files = sorted([f for f in chargers_dir.glob('MOTO*.csv')])

print(f"Found {len(charger_files)} charger files")

# Get charger specs from OE2 results
chargers_results_path = Path('data/interim/oe2/chargers/chargers_results.json')
with open(chargers_results_path) as f:
    chargers_results = json.load(f)

# Create mapping of charger name to power
charger_specs = {}
for charger_info in chargers_results.get('chargers', []):
    name = charger_info.get('name', '')
    power = charger_info.get('power_kw', 2.0)
    charger_specs[name] = power

print(f"Loaded {len(charger_specs)} charger specs from OE2")

# Fix each charger CSV
for charger_file in charger_files:
    charger_name = charger_file.stem  # e.g., "MOTO_CH_001"
    
    # Read existing CSV
    df = pd.read_csv(charger_file)
    
    # Get power rating (use defaults: 2kW for motos, 3kW for mototaxis)
    if charger_name in charger_specs:
        power_kw = charger_specs[charger_name]
    elif 'MOTO_TAXI' in charger_name:
        power_kw = 3.0
    else:
        power_kw = 2.0
    
    # Add power column based on state
    # When state=1 (connected), charger delivers its rated power
    # When state=3 (commuting), charger power is 0
    df['electric_vehicle_charger_power'] = 0.0
    df.loc[df['electric_vehicle_charger_state'] == 1, 'electric_vehicle_charger_power'] = power_kw
    
    # Reorder columns for clarity
    column_order = [
        'electric_vehicle_charger_state',
        'electric_vehicle_charger_power',
        'electric_vehicle_id',
        'electric_vehicle_departure_time',
        'electric_vehicle_required_soc_departure',
        'electric_vehicle_estimated_arrival_time',
        'electric_vehicle_estimated_soc_arrival',
    ]
    
    # Only include columns that exist
    column_order = [c for c in column_order if c in df.columns]
    df = df[column_order]
    
    # Save corrected CSV
    df.to_csv(charger_file, index=False)
    
    if (charger_files.index(charger_file) + 1) % 10 == 0:
        print(f"  Fixed {charger_files.index(charger_file) + 1}/{len(charger_files)}")

print(f"✓ Fixed all {len(charger_files)} charger CSV files with power column")
