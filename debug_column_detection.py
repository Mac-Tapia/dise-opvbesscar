#!/usr/bin/env python3
"""Debug: verificar column detection logic."""

import pandas as pd
from pathlib import Path

mall_path = Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv")

# Load with proper separator
mall_df = pd.read_csv(mall_path, sep=";")
print("Columnas en CSV:", list(mall_df.columns))

# Simular la lógica de búsqueda de date_col
date_col = None
for col in mall_df.columns:
    col_norm = str(col).strip().lower()
    print(f"  Evaluando '{col}' -> '{col_norm}'")
    if col_norm in ("fecha", "horafecha", "datetime", "timestamp", "time") or "fecha" in col_norm:
        date_col = col
        print(f"    ✓ MATCH - date_col = {date_col}")
        break

if date_col is None:
    date_col = mall_df.columns[0]
    print(f"  No match found, using first column: {date_col}")

print(f"\ndate_col selected: {date_col}")

# Simular búsqueda de demand_col
demand_col = None
for col in mall_df.columns:
    if col == date_col:
        continue
    col_norm = str(col).strip().lower()
    print(f"  Evaluando '{col}' -> '{col_norm}'")
    if any(tag in col_norm for tag in ("kwh", "demanda", "power", "kw")):
        demand_col = col
        print(f"    ✓ MATCH - demand_col = {demand_col}")
        break

if demand_col is None:
    candidates = [c for c in mall_df.columns if c != date_col]
    demand_col = candidates[0] if candidates else date_col

print(f"\ndemand_col selected: {demand_col}")

# Rename
print(f"\nRenaming: {date_col} -> 'datetime', {demand_col} -> 'mall_kwh'")
mall_df = mall_df.rename(columns={date_col: "datetime", demand_col: "mall_kwh"})
print(f"Columnas después rename: {list(mall_df.columns)}")

# Try to parse
print(f"\nParsing datetime...")
mall_df["datetime"] = pd.to_datetime(mall_df["datetime"], errors="coerce")
print(f"✓ Datetime parsed OK")
print(f"\nPrimeros registros:")
print(mall_df.head(10))
