import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día típico 180 (mismo que usa gráfica 00)
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 80)
print('DÍA 180 - DATOS CRUDOS QUE VE LA GRÁFICA 00')
print('=' * 80)
print()
print('COLUMNAS RELEVANTES:')
cols = ['bess_energy_stored_hourly_kwh', 'bess_energy_delivered_hourly_kwh', 
        'mall_kwh', 'pv_kwh', 'soc_percent']
print(day_df[cols].to_string())
print()
print('MALL DEMAND (kW):')
print(f'  MIN: {day_df["mall_kwh"].min():.2f} kW')
print(f'  MAX: {day_df["mall_kwh"].max():.2f} kW')
print(f'  Excede 1900 kW: {day_df["mall_kwh"].max() > 1900}')
print()
print('BESS SOC (%):')
print(f'  MIN: {day_df["soc_percent"].min():.2f}%')
print(f'  MAX: {day_df["soc_percent"].max():.2f}%')
print(f'  Toca 20% minimo: {day_df["soc_percent"].min() <= 20}')
print()
print('=' * 80)
print('AÑO COMPLETO - VERIFICACIÓN DE LÍMITES')
print('=' * 80)
print()
print('MALL DEMAND (AÑO COMPLETO):')
print(f'  MIN: {df["mall_kwh"].min():.2f} kW')
print(f'  MAX: {df["mall_kwh"].max():.2f} kW')
print(f'  Media: {df["mall_kwh"].mean():.2f} kW')
print(f'  Horas > 1900 kW: {(df["mall_kwh"] > 1900).sum()} de {len(df)}')
print()
print('BESS SOC (AÑO COMPLETO):')
print(f'  MIN: {df["soc_percent"].min():.2f}%')
print(f'  MAX: {df["soc_percent"].max():.2f}%')
print(f'  Horas <= 20%: {(df["soc_percent"] <= 20).sum()} de {len(df)}')
print(f'  Horas entre 20-30%: {((df["soc_percent"] > 20) & (df["soc_percent"] <= 30)).sum()} de {len(df)}')
