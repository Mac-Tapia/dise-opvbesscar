#!/usr/bin/env python
"""Verificación rápida del dataset antes de entrenamiento."""
from pathlib import Path
import pandas as pd
import json

print("[DATASET VERIFICATION]")
print("=" * 60)

# Verificar solar
solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
if solar_path.exists():
    df = pd.read_csv(solar_path)
    status = "✅ OK" if len(df) == 8760 else f"❌ ERROR ({len(df)} rows)"
    print(f"[SOLAR] {status} - {len(df)} rows")
else:
    print("[SOLAR] ❌ NOT FOUND")

# Verificar chargers
chargers_path = Path("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv")
if chargers_path.exists():
    df = pd.read_csv(chargers_path)
    status = "✅ OK" if df.shape == (8760, 128) else f"⚠️ CHECK ({df.shape})"
    print(f"[CHARGERS] {status} - shape={df.shape}")
else:
    print("[CHARGERS] ℹ️ Not found (will expand from daily)")

# Verificar schema
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
if schema_path.exists():
    with open(schema_path) as f:
        schema = json.load(f)
    buildings = len(schema.get("buildings", {}))
    timesteps = schema.get("simulation_end_time_step", 0)
    print(f"[SCHEMA] ✅ OK - {buildings} building(s), timesteps={timesteps}")
else:
    print("[SCHEMA] ❌ NOT FOUND")

print("=" * 60)
print("[READY TO TRAIN]")
