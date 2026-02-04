#!/usr/bin/env python3
"""Verificar carga de datasets críticos: BESS, mall demand, solar."""

from pathlib import Path
import json
import pandas as pd

print("=" * 80)
print("VERIFICACIÓN DE DATASETS CRÍTICOS")
print("=" * 80)
print()

# 1. BESS
print("[1] BESS RESULTS")
bess_path = Path("data/interim/oe2/bess/bess_results.json")
if bess_path.exists():
    with open(bess_path) as f:
        bess = json.load(f)
    print(f"  ✓ Archivo existe: {bess_path}")
    print(f"  - Capacidad: {bess.get('capacity_kwh', 'N/A')} kWh")
    print(f"  - Potencia: {bess.get('nominal_power_kw', 'N/A')} kW")
    print(f"  - SOC inicial: {bess.get('initial_soc', 'N/A')}")
else:
    print(f"  ✗ MISSING: {bess_path}")

print()

# 2. Mall Demand
print("[2] MALL DEMAND")
mall_candidates = [
    Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv"),
    Path("data/interim/oe2/demandamall/demanda_mall_kwh.csv"),
]
mall_df = None
mall_path = None
for path in mall_candidates:
    if path.exists():
        mall_df = pd.read_csv(path)
        mall_path = path
        break

if mall_df is not None:
    print(f"  ✓ Archivo existe: {mall_path}")
    print(f"  - Registros: {len(mall_df)}")
    print(f"  - Columnas: {list(mall_df.columns)}")
    # Find numeric column
    numeric_cols = mall_df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) > 0:
        total_kwh = mall_df[numeric_cols[-1]].sum()
        print(f"  - Total demanda: {total_kwh:,.0f} kWh")
    print(f"  - Primeros 5 registros:")
    print(f"    {mall_df.head().to_string()}")
else:
    print(f"  ✗ MISSING: No mall demand file found in:")
    for path in mall_candidates:
        print(f"     - {path}")

print()

# 3. Solar
print("[3] SOLAR GENERATION")
solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
if solar_path.exists():
    solar_df = pd.read_csv(solar_path)
    print(f"  ✓ Archivo existe: {solar_path}")
    print(f"  - Registros: {len(solar_df)}")
    print(f"  - Columnas: {list(solar_df.columns)}")
    # Find numeric column
    numeric_cols = solar_df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) > 0:
        total_kwh = solar_df[numeric_cols[-1]].sum()
        print(f"  - Total generación: {total_kwh:,.0f} kWh")
        print(f"  - Media: {solar_df[numeric_cols[-1]].mean():.2f} kW")
else:
    print(f"  ✗ MISSING: {solar_path}")

print()
print("=" * 80)
print("FIN VERIFICACIÓN")
print("=" * 80)
