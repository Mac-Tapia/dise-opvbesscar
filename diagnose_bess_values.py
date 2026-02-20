import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('=' * 80)
print('DIAGNÓSTICO: ¿DE DÓNDE VIENEN 487,819 kWh Y 0 kWh?')
print('=' * 80)

# Chequear qué columnas existen y sus sumas
print('\nCOLUMNAS RELACIONADAS A BESS:')
bess_cols = [col for col in df.columns if 'bess' in col.lower()]
for col in bess_cols:
    try:
        total = df[col].sum()
        print(f"  {col:40s}: {total:>15,.0f}")
    except Exception as e:
        print(f"  {col:40s}: ERROR - {type(df[col].iloc[0]).__name__}")

print('\nCOLUMNAS RELACIONADAS A kW (POTENCIA):')
kw_cols = [col for col in df.columns if col.endswith('_kw')]
for col in kw_cols[:15]:
    total = df[col].sum()
    print(f"  {col:40s}: {total:>15,.0f}")

print('\n' + '=' * 80)
print('BÚSQUEDA: ¿Qué suma a 487,819?')
print('=' * 80)

# Probar diferentes sumas
candidates = {
    'bess_to_ev_kwh': df['bess_to_ev_kwh'].sum(),
    'bess_to_mall_kwh': df['bess_to_mall_kwh'].sum(),
    'bess_to_ev + bess_to_mall': df['bess_to_ev_kwh'].sum() + df['bess_to_mall_kwh'].sum(),
    'pv_to_bess_kwh': df['pv_to_bess_kwh'].sum(),
    'ev_kwh / 2': df['ev_kwh'].sum() / 2,
}

for desc, val in candidates.items():
    match = "✓ MATCH!" if abs(val - 487819) < 100 else ""
    print(f"  {desc:40s}: {val:>15,.0f} {match}")

# Chequear primeras y últimas filas
print('\n' + '=' * 80)
print('PRIMERAS 5 FILAS DEL DATASET')
print('=' * 80)
print(df[['pv_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh', 'pv_to_bess_kwh', 
          'pv_to_bess_kw', 'bess_charge_kw', 'bess_discharge_kw', 'bess_energy_stored_hourly_kwh', 
          'bess_energy_delivered_hourly_kwh']].head())

print('\nÚLTIMAS 5 FILAS DEL DATASET')
print('=' * 80)
print(df[['pv_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh', 'pv_to_bess_kwh',
          'pv_to_bess_kw', 'bess_charge_kw', 'bess_discharge_kw', 'bess_energy_stored_hourly_kwh',
          'bess_energy_delivered_hourly_kwh']].tail())

# Chequear si la columna 'pv_to_bess_kw' suma a algo parecido
print('\n' + '=' * 80)
print('SUMAS DE POTENCIA (kW) vs ENERGÍA (kWh)')
print('=' * 80)
print(f"  bess_charge_kw.sum():               {df['bess_charge_kw'].sum():>15,.0f}")
print(f"  bess_discharge_kw.sum():            {df['bess_discharge_kw'].sum():>15,.0f}")
print(f"  pv_to_bess_kw.sum():                {df['pv_to_bess_kw'].sum():>15,.0f}")
print(f"  pv_to_bess_kwh.sum():               {df['pv_to_bess_kwh'].sum():>15,.0f}")
