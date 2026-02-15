#!/usr/bin/env python
import pandas as pd
from pathlib import Path

# VER COLUMNAS EXACTAS DE CADA DATASET
datasets = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS': 'data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv',
    'Mall': 'data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv',
}

for name, path in datasets.items():
    p = Path(path)
    if p.exists():
        df = pd.read_csv(p)
        print(f'\n{name} ({len(df)} filas, {len(df.columns)} columnas):')
        for i, col in enumerate(df.columns[:15]):
            print(f'  [{i:2d}] {col}')
        if len(df.columns) > 15:
            print(f'  ... y {len(df.columns)-15} más')
    else:
        print(f'\n{name}: {path} NOT FOUND')
