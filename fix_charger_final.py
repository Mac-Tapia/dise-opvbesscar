#!/usr/bin/env python
"""
Fix charger CSV files - Remove index and ensure proper column structure.
"""
import pandas as pd
from pathlib import Path
import numpy as np

chargers_dir = Path('data/processed/citylearn/iquitos_ev_mall')
charger_files = sorted([f for f in chargers_dir.glob('MOTO*.csv')])

print(f"Fixing {len(charger_files)} charger files...")

for charger_file in charger_files:
    # Read CSV with index as integer column
    df = pd.read_csv(charger_file, index_col=0)
    
    # Reset index to make timestep a regular column
    df.reset_index(drop=False, inplace=True)
    df.rename(columns={'timestep': 'Time'}, inplace=True)
    
    # Ensure all columns are properly named for CityLearn
    # CityLearn expects columns without index
    df = df[['Time', 'electric_vehicle_charger_state', 'electric_vehicle_charger_power',
             'electric_vehicle_id', 'electric_vehicle_departure_time',
             'electric_vehicle_required_soc_departure', 'electric_vehicle_estimated_arrival_time',
             'electric_vehicle_estimated_soc_arrival']]
    
    # Save without index
    df.to_csv(charger_file, index=False)
    
    if (charger_files.index(charger_file) + 1) % 32 == 0:
        print(f"  Fixed {charger_files.index(charger_file) + 1}/{len(charger_files)}")

print(f"✓ Fixed all {len(charger_files)} charger CSV files")

# Verify
df_test = pd.read_csv(charger_files[0])
print(f"\nVerification - First charger structure:")
print(f"  Shape: {df_test.shape}")
print(f"  Columns: {df_test.columns.tolist()}")
print(f"  First row:\n{df_test.iloc[0]}")
