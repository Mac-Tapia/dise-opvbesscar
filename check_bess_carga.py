import pandas as pd
from pathlib import Path

# Check transformed dataset
path1 = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
if path1.exists():
    df = pd.read_csv(path1)
    print('=== TRANSFORMED DATASET ===')
    print('Columnas:', list(df.columns))
    print()
    print('Tiene pv_to_bess_kw:', 'pv_to_bess_kw' in df.columns)
    print('Tiene pv_to_bess_kwh:', 'pv_to_bess_kwh' in df.columns)
    if 'pv_to_bess_kw' in df.columns:
        print('Total pv_to_bess_kw:', df['pv_to_bess_kw'].sum())
else:
    print('No existe:', path1)

# Check original dataset
path2 = Path('data/oe2/bess/bess_ano_2024.csv')
if path2.exists():
    df = pd.read_csv(path2)
    print('\n=== ORIGINAL DATASET ===')
    print('Total columnas:', len(df.columns))
    print('Columnas:', df.columns.tolist())
    print()
    print('Tiene pv_to_bess_kw:', 'pv_to_bess_kw' in df.columns)
    print('Tiene pv_to_bess_kwh:', 'pv_to_bess_kwh' in df.columns)
    if 'pv_to_bess_kwh' in df.columns:
        print('Total pv_to_bess_kwh:', df['pv_to_bess_kwh'].sum())
