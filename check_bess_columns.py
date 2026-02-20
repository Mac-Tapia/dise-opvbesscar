import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('=' * 80)
print('COLUMNAS DEL DATASET TRANSFORMADO')
print('=' * 80)
print('\n'.join(f'  {i+1:2d}. {col}' for i, col in enumerate(df.columns)))
print(f'\nTOTAL: {len(df.columns)} columnas\n')

print('=' * 80)
print('TOTALES CÁLCULADOS (Suma anual)')
print('=' * 80)

# Columnas kWh
totals = {
    'pv_kwh': df['pv_kwh'].sum() if 'pv_kwh' in df.columns else 0,
    'bess_to_ev_kwh': df['bess_to_ev_kwh'].sum() if 'bess_to_ev_kwh' in df.columns else 0,
    'bess_to_mall_kwh': df['bess_to_mall_kwh'].sum() if 'bess_to_mall_kwh' in df.columns else 0,
    'pv_to_bess_kwh': df['pv_to_bess_kwh'].sum() if 'pv_to_bess_kwh' in df.columns else 0,
    'bess_energy_delivered_hourly_kwh': df['bess_energy_delivered_hourly_kwh'].sum() if 'bess_energy_delivered_hourly_kwh' in df.columns else 0,
    'bess_energy_stored_hourly_kwh': df['bess_energy_stored_hourly_kwh'].sum() if 'bess_energy_stored_hourly_kwh' in df.columns else 0,
}

for col, val in totals.items():
    print(f"  {col:40s}: {val:>15,.0f} kWh")

print('\n' + '=' * 80)
print('RESUMEN BESS')
print('=' * 80)
charge = totals['pv_to_bess_kwh'] or totals['bess_energy_stored_hourly_kwh']
discharge = totals['bess_to_ev_kwh'] + totals['bess_to_mall_kwh'] or totals['bess_energy_delivered_hourly_kwh']
print(f"\n  Carga (PV→BESS):           {charge:>15,.0f} kWh")
print(f"  Descarga a EV:             {totals['bess_to_ev_kwh']:>15,.0f} kWh")
print(f"  Descarga a Mall:           {totals['bess_to_mall_kwh']:>15,.0f} kWh")
print(f"  Descarga total:            {discharge:>15,.0f} kWh")

# Verificar si columnas kW existen y están correctas
print('\n' + '=' * 80)
print('COLUMNAS kW (Potencia)')
print('=' * 80)
kw_cols = [col for col in df.columns if '_kw' in col]
if kw_cols:
    for col in kw_cols[:10]:  # Primeras 10
        total = df[col].sum()
        print(f"  {col:40s}: {total:>15,.0f}")
else:
    print("  No hay columnas con '_kw'")
