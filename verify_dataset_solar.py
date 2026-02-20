import pandas as pd
from pathlib import Path

csv_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

df = pd.read_csv(csv_path)
print(f'\n✓ Dataset ubicacion: {csv_path}')
print(f'✓ Dataset tamaño: {df.shape[0]} filas × {df.shape[1]} columnas')
print(f'\n✓ Columnas de validacion solar:')
print(f'  - pv_generation_kw: {"pv_generation_kw" in df.columns}')
print(f'  - pv_to_grid_kw: {"pv_to_grid_kw" in df.columns}')
print(f'  - co2_from_grid_kg: {"co2_from_grid_kg" in df.columns}')
print(f'  - bess_soc_percent: {"bess_soc_percent" in df.columns}')

print(f'\n✓ Generacion solar anual:')
print(f'  Total: {df["pv_kwh"].sum()/1e6:.2f} GWh ({df["pv_kwh"].sum():,.0f} kWh)')
print(f'  Capacidad maxima: 8.29 GWh (8,292,514.17 kWh)')
print(f'  Utilizacion: {(df["pv_kwh"].sum() / 8_292_514.17) * 100:.1f}%')

print(f'\n✓ Dataset listo para balance.py y RL agents')
