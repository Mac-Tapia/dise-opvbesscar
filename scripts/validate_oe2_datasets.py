"""Validar datasets OE2 para entrenamiento"""
import pandas as pd
from pathlib import Path

datasets = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'Mall Demand': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS Storage': 'data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv',
}

print('[VALIDACION OE2 DATASETS]')
print()
all_ok = True
for name, path in datasets.items():
    p = Path(path)
    if p.exists():
        try:
            df = pd.read_csv(p, sep=';' if 'mall' in path.lower() else None)
            mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            print(f'  {name:20s}: OK - {len(df):,} rows | {len(df.columns):3d} cols | {mb:.2f} MB')
        except Exception as e:
            print(f'  {name:20s}: ERROR - {e}')
            all_ok = False
    else:
        print(f'  {name:20s}: FALTANTE')
        all_ok = False

print()
status = 'ALL DATASETS READY' if all_ok else 'MISSING DATASETS'
print(f'  Status: {status}')
