#!/usr/bin/env python3
"""Fix chargers_timeseries.csv by removing categorical columns."""

import pandas as pd
import numpy as np
from pathlib import Path

# Load the problematic CSV
chargers_path = Path("data/iquitos_ev_mall/chargers_timeseries.csv")
print(f"[1] Loading chargers CSV: {chargers_path}")
df = pd.read_csv(chargers_path)
print(f"    Before: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"    Dtypes sample: {df.dtypes.head(20).to_dict()}")

# Identify and drop categorical columns (columns that contain strings)
categorical_cols = []
numeric_cols = ['datetime']  # Keep datetime

for col in df.columns:
    if col == 'datetime':
        continue
    try:
        # Try to convert to numeric
        pd.to_numeric(df[col], errors='raise')
        numeric_cols.append(col)
    except (ValueError, TypeError):
        categorical_cols.append(col)
        print(f"   [CAT] {col} - contains: {df[col].unique()[:3]}")

print(f"\n[2] Found {len(numeric_cols)} numeric columns and {len(categorical_cols)} categorical columns")
print(f"    Numeric: {numeric_cols[:10]}...")
print(f"    Categorical: {categorical_cols}")

# Create numeric-only DataFrame
df_numeric = df[numeric_cols].copy()

# Ensure all numeric columns are actually float (except datetime)
for col in df_numeric.columns:
    if col != 'datetime':
        df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')

print(f"\n[3] Numeric-only DataFrame: {df_numeric.shape[0]} rows × {df_numeric.shape[1]} columns")
print(f"    Dtypes: {df_numeric.dtypes.unique()}")

# Save the cleaned CSV
df_numeric.to_csv(chargers_path, index=False)
print(f"\n[4] ✅ Saved cleaned chargers_timeseries.csv ({df_numeric.shape[1]} numeric columns)")

# Verify the save
df_verify = pd.read_csv(chargers_path)
print(f"    Verification: {df_verify.shape[0]} rows × {df_verify.shape[1]} columns")
print(f"    Column sample: {list(df_verify.columns[:10])}")
