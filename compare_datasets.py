import pandas as pd

print('=' * 80)
print('COMPARACIÓN: DATASET ORIGINAL vs TRANSFORMADO')
print('=' * 80)

# Original
df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
print('\n📁 ORIGINAL: data/oe2/bess/bess_ano_2024.csv')
print(f'   {len(df_orig.columns)} columnas, {len(df_orig)} filas')
print('\n   Columnas:')
for i, col in enumerate(df_orig.columns, 1):
    print(f'      {i:2d}. {col}')

# Transformado
df_trans = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
print(f'\n📁 TRANSFORMADO: data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
print(f'   {len(df_trans.columns)} columnas, {len(df_trans)} filas')

# Totales relevantes ambo datasets
print('\n' + '=' * 80)
print('TOTALES: DESCARGA')
print('=' * 80)

print('\nORIGINAL:')
print(f'  bess_to_ev_kwh:        {df_orig["bess_to_ev_kwh"].sum():>15,.0f}')
print(f'  bess_to_mall_kwh:      {df_orig["bess_to_mall_kwh"].sum():>15,.0f}')
print(f'  Total descarga:        {(df_orig["bess_to_ev_kwh"].sum() + df_orig["bess_to_mall_kwh"].sum()):>15,.0f}')

print('\nTRANSFORMADO:')
print(f'  bess_to_ev_kwh:        {df_trans["bess_to_ev_kwh"].sum():>15,.0f}')
print(f'  bess_to_mall_kwh:      {df_trans["bess_to_mall_kwh"].sum():>15,.0f}')
print(f'  bess_energy_delivered_hourly_kwh: {df_trans["bess_energy_delivered_hourly_kwh"].sum():>15,.0f}')
print(f'  Total descarga (sum):  {(df_trans["bess_to_ev_kwh"].sum() + df_trans["bess_to_mall_kwh"].sum()):>15,.0f}')

# Chequear si hay discrepancias
print('\n' + '=' * 80)
print('DIAGNÓSTICO')
print('=' * 80)

orig_total = df_orig['bess_to_ev_kwh'].sum() + df_orig['bess_to_mall_kwh'].sum()
trans_total_sum = df_trans['bess_to_ev_kwh'].sum() + df_trans['bess_to_mall_kwh'].sum()
trans_total_delivered = df_trans['bess_energy_delivered_hourly_kwh'].sum()

print(f'\nDescarga Original:      {orig_total:>15,.0f} kWh')
print(f'Descarga Transformada:  {trans_total_sum:>15,.0f} kWh')
print(f'Diferencia:             {abs(orig_total - trans_total_sum):>15,.0f} kWh')
print(f'  → {"✓ COINCIDE" if abs(orig_total - trans_total_sum) < 10 else "❌ DIFERENTE"}')

print(f'\nbess_energy_delivered:  {trans_total_delivered:>15,.0f} kWh')
print(f'vs (ev+mall):           {trans_total_sum:>15,.0f} kWh')
print(f'Diferencia:             {abs(trans_total_delivered - trans_total_sum):>15,.0f} kWh')
print(f'  → {"✓ COINCIDE" if abs(trans_total_delivered - trans_total_sum) < 10 else "❌ DIFERENTE"}')
