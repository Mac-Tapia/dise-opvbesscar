#!/usr/bin/env python
"""
Regenerate charger CSV files with ALL required columns for CityLearn.
"""
import pandas as pd
from pathlib import Path
import numpy as np

chargers_dir = Path('data/processed/citylearn/iquitos_ev_mall')
charger_files = sorted([f for f in chargers_dir.glob('MOTO*.csv')])

print(f"Regenerating {len(charger_files)} charger files...")

for charger_file in charger_files:
    # Read CSV
    df = pd.read_csv(charger_file, index_col=0)
    
    # Determine power based on charger name
    if 'MOTO_TAXI' in charger_file.stem:
        power_kw = 3.0
    else:
        power_kw = 2.0
    
    # Add power column based on charger state
    df['electric_vehicle_charger_power'] = 0.0
    if 'electric_vehicle_charger_state' in df.columns:
        df.loc[df['electric_vehicle_charger_state'] == 1, 'electric_vehicle_charger_power'] = power_kw
    
    # Reset index to add timestamp as column
    df = df.reset_index()
    
    # Rename index column to 'Time'
    if df.columns[0] == 'timestep':
        df.rename(columns={'timestep': 'Time'}, inplace=True)
    
    # Reorder with Time first
    cols_order = ['Time', 'electric_vehicle_charger_state', 'electric_vehicle_charger_power']
    other_cols = [c for c in df.columns if c not in cols_order]
    df = df[cols_order + other_cols]
    
    # Save WITHOUT index
    df.to_csv(charger_file, index=False)
    
    if (charger_files.index(charger_file) + 1) % 32 == 0:
        print(f"  Fixed {charger_files.index(charger_file) + 1}/{len(charger_files)}")

print(f"✓ Regenerated all {len(charger_files)} charger CSV files")

# Verify
df_test = pd.read_csv(charger_files[0])
print(f"\nVerification - First charger:")
print(f"  Shape: {df_test.shape}")
print(f"  Columns: {df_test.columns.tolist()}")
print(f"  Power range: {df_test['electric_vehicle_charger_power'].min()}-{df_test['electric_vehicle_charger_power'].max()}")
