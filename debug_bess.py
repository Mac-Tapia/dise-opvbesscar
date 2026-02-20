import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('Columnas BESS disponibles:')
bess_cols = [c for c in df.columns if 'bess' in c.lower()]
for col in bess_cols:
    print(f'  {col}')

print()
print('Valores suma anual:')
print(f'  bess_charge_kw: {df["bess_charge_kw"].sum():,.0f}')
print(f'  bess_discharge_kw: {df["bess_discharge_kw"].sum():,.0f}')
print(f'  pv_to_bess_kw: {df["pv_to_bess_kw"].sum():,.0f}')
print()
print('Estadisticas bess_discharge_kw:')
print(f'  Min: {df["bess_discharge_kw"].min():.2f}')
print(f'  Max: {df["bess_discharge_kw"].max():.2f}')
print(f'  Mean: {df["bess_discharge_kw"].mean():.2f}')
print(f'  Count > 0: {(df["bess_discharge_kw"] > 0).sum()}')
print()
print('Primeras 10 filas:')
print(df[['hour', 'pv_to_bess_kw', 'bess_charge_kw', 'bess_discharge_kw']].head(10))
