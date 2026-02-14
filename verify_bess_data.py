import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
print('=' * 80)
print('VERIFICACIÓN DATOS BESS - bess_simulation_hourly.csv')
print('=' * 80)
print(f'Total filas: {len(df)}')
print(f'Total columnas: {len(df.columns)}')
print()
print('Columnas principales (8,760 horas):')
for col in ['pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh', 'pv_to_bess_kwh', 'pv_to_ev_kwh', 'pv_to_mall_kwh', 'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_soc_percent']:
    if col in df.columns:
        print(f'  {col:30} Sum={df[col].sum():12,.1f}  Mean={df[col].mean():10,.1f}  Max={df[col].max():10,.1f}')
print()
print('Balance energético horario (promedio):')
mean_pv = df['pv_generation_kwh'].mean()
mean_ev = df['ev_demand_kwh'].mean()
mean_mall = df['mall_demand_kwh'].mean()
mean_pv_to_ev = df['pv_to_ev_kwh'].mean()
mean_pv_to_bess = df['pv_to_bess_kwh'].mean()
mean_pv_to_mall = df['pv_to_mall_kwh'].mean()
print(f'  PV generado:              {mean_pv:10.2f} kW/h')
print(f'  PV → EV:                  {mean_pv_to_ev:10.2f} kW/h')
print(f'  PV → BESS:                {mean_pv_to_bess:10.2f} kW/h')
print(f'  PV → MALL:                {mean_pv_to_mall:10.2f} kW/h')
print(f'  Suma distribuido:         {mean_pv_to_ev + mean_pv_to_bess + mean_pv_to_mall:10.2f} kW/h')
print()
print('SOC Statistics:')
print(f'  SOC Min: {df["bess_soc_percent"].min():.1f}%')
print(f'  SOC Max: {df["bess_soc_percent"].max():.1f}%')
print(f'  SOC Mean: {df["bess_soc_percent"].mean():.1f}%')
print()
print('BESS Mode distribution:')
if 'bess_mode' in df.columns:
    print(df['bess_mode'].value_counts())
print()
print('=' * 80)
print('PRIMERAS 24 HORAS (DIA 1):')
print('=' * 80)
print(df.head(24)[['datetime', 'pv_generation_kwh', 'ev_demand_kwh', 'pv_to_ev_kwh', 'pv_to_bess_kwh', 'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_soc_percent', 'bess_mode']].to_string())
print()
print('=' * 80)
print('VERIFICACIÓN: PV debe cumplirse: pv_to_ev + pv_to_bess + pv_to_mall <= pv_generation')
print('=' * 80)
df['pv_check'] = df['pv_to_ev_kwh'] + df['pv_to_bess_kwh'] + df['pv_to_mall_kwh']
violations = df[df['pv_check'] > df['pv_generation_kwh'] + 0.01]
if len(violations) > 0:
    print(f'ERROR: {len(violations)} violaciones encontradas!')
    print(violations[['pv_generation_kwh', 'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_check']].head(10))
else:
    print('✓ CORRECTO: PV balance es correcto en todas las horas')
