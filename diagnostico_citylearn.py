"""Diagnóstico rápido del dataset CityLearn para detectar terminación prematura."""
import json
import pandas as pd
from pathlib import Path

dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
schema_path = dataset_dir / "schema_pv_bess.json"

print("="*80)
print("DIAGNÓSTICO DATASET CITYLEARN")
print("="*80)

# 1. Verificar schema
print("\n1. SCHEMA CONFIGURATION:")
with open(schema_path, 'r') as f:
    schema = json.load(f)

print(f"  episode_time_steps: {schema.get('episode_time_steps', 'NOT SET')}")
print(f"  simulation_start_time_step: {schema.get('simulation_start_time_step', 'NOT SET')}")
print(f"  simulation_end_time_step: {schema.get('simulation_end_time_step', 'NOT SET')}")
print(f"  root_directory: {schema.get('root_directory', 'NOT SET')}")

# 2. Verificar Building_1.csv
print("\n2. BUILDING_1.CSV:")
building_csv = dataset_dir / "Building_1.csv"
if building_csv.exists():
    df = pd.read_csv(building_csv)
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  NaNs por columna:")
    for col in df.columns:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            print(f"    {col}: {nan_count} NaNs")
    print(f"\n  Primeras 5 filas:")
    print(df.head())
    print(f"\n  Últimas 5 filas:")
    print(df.tail())
else:
    print("  ❌ NO EXISTE")

# 3. Verificar charger CSVs
print("\n3. CHARGER CSVs:")
charger_csvs = list(dataset_dir.glob("charger_simulation_*.csv"))
print(f"  Total chargers encontrados: {len(charger_csvs)}")
if charger_csvs:
    # Verificar primeros 3
    for csv_path in sorted(charger_csvs)[:3]:
        df_charger = pd.read_csv(csv_path)
        print(f"  {csv_path.name}: {len(df_charger)} rows, columns={list(df_charger.columns)[:3]}...")

# 4. Verificar buildings en schema
print("\n4. BUILDINGS EN SCHEMA:")
buildings = schema.get('buildings', {})
if isinstance(buildings, dict):
    print(f"  Type: dict")
    print(f"  Buildings count: {len(buildings)}")
    print(f"  Building IDs: {list(buildings.keys())[:5]}...")
elif isinstance(buildings, list):
    print(f"  Type: list")
    print(f"  Buildings count: {len(buildings)}")
else:
    print(f"  Type: {type(buildings)}")

print("\n" + "="*80)
print("FIN DIAGNÓSTICO")
print("="*80)
