import pandas as pd

# Check transformed dataset
df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('=== DATASET TRANSFORMADO ===')
print(f'Total filas: {len(df)}')
print()
print('Columnas disponibles de BESS:')
for col in sorted(df.columns):
    if 'bess' in col.lower() or 'to_' in col.lower():
        print(f'  {col}: sum={df[col].sum():,.0f}, min={df[col].min():.2f}, max={df[col].max():.2f}')

print()
print('=== Descarga BESS (PV a EV vs PV a Mall) ===')
if 'bess_to_ev_kwh' in df.columns:
    print(f'bess_to_ev_kwh: {df["bess_to_ev_kwh"].sum():,.0f} kWh')
if 'bess_to_mall_kwh' in df.columns:
    print(f'bess_to_mall_kwh: {df["bess_to_mall_kwh"].sum():,.0f} kWh')

# Check sum in original dataset
print()
print('=== DATASET ORIGINAL ===')
df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
print(f'bess_to_ev_kwh: {df_orig["bess_to_ev_kwh"].sum():,.0f} kWh')
print(f'bess_to_mall_kwh: {df_orig["bess_to_mall_kwh"].sum():,.0f} kWh')
print(f'Total descarga: {df_orig["bess_to_ev_kwh"].sum() + df_orig["bess_to_mall_kwh"].sum():,.0f} kWh')
