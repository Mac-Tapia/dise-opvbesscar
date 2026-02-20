import pandas as pd

# Cargar con rutas actuales (sin cambios)
df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print('DIAGNÓSTICO - Rutas originales sin cambios:')
print('=' * 80)
print(f'\nDataset ORIGINAL: data/oe2/bess/bess_ano_2024.csv')
print(f'  Filas: {len(df_orig)}')
print(f'  Descarga: {df_orig["bess_energy_delivered_hourly_kwh"].sum():,.0f} kWh')
print(f'  Carga: {df_orig["bess_energy_stored_hourly_kwh"].sum():,.0f} kWh')
print(f'  PV generada: {df_orig["pv_kwh"].sum():,.0f} kWh')

print(f'\nColumnas con BESS:')
cols_bess = [c for c in df_orig.columns if 'bess' in c.lower() or 'discharge' in c.lower()]
for col in cols_bess:
    val = df_orig[col].sum()
    print(f'  {col}: {val:,.0f}')
