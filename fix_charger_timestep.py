#!/usr/bin/env python
"""
Fix charger CSV files to include proper timestep index for CityLearn.
CityLearn expects charger data to have a proper time index.
"""
import pandas as pd
from pathlib import Path
import numpy as np

chargers_dir = Path('data/processed/citylearn/iquitos_ev_mall')
charger_files = sorted([f for f in chargers_dir.glob('MOTO*.csv')])

print(f"Fixing {len(charger_files)} charger files with proper timestep indexing...")

for charger_file in charger_files:
    # Read existing CSV
    df = pd.read_csv(charger_file)
    
    # Add timestep column (0 to 8760)
    df.insert(0, 'timestep', np.arange(len(df)))
    
    # Set timestep as index (CityLearn expects this)
    df = df.set_index('timestep')
    
    # Save corrected CSV
    df.to_csv(charger_file)
    
    if (charger_files.index(charger_file) + 1) % 32 == 0:
        print(f"  Fixed {charger_files.index(charger_file) + 1}/{len(charger_files)}")

print(f"✓ Fixed all {len(charger_files)} charger CSV files with proper timestep index")

# Verify
df_test = pd.read_csv(charger_files[0], index_col=0)
print(f"\nVerification - First charger structure:")
print(f"  Index name: {df_test.index.name}")
print(f"  Shape: {df_test.shape}")
print(f"  Columns: {df_test.columns.tolist()[:3]}...")
