#!/usr/bin/env python3
"""Verificar esquemas de los 5 datasets OE2."""
import pandas as pd
from pathlib import Path

datasets = {
    'solar': 'data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv',
    'chargers': 'data/oe2/chargers/chargers_real_hourly_2024.csv',
    'bess': 'data/oe2/bess/bess_hourly_dataset_2024.csv',
    'mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

print("=" * 80)
print("ESQUEMAS DE LOS 5 DATASETS OE2")
print("=" * 80)

for name, path in datasets.items():
    p = Path(path)
    if not p.exists():
        print(f"\n{name.upper()}: [NO EXISTE] {path}")
        continue
    
    sep = ';' if name == 'mall' else ','
    df = pd.read_csv(p, sep=sep)
    
    print(f"\n{name.upper()}:")
    print(f"  Path: {path}")
    print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"  Columns: {list(df.columns)[:20]}")
    if len(df.columns) > 20:
        print(f"  ... y {len(df.columns) - 20} columnas más")
    print(f"  Dtypes: {dict(list(df.dtypes.items())[:5])}")
