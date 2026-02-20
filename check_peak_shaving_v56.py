#!/usr/bin/env python3
import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print('=' * 80)
print('MÉTRICAS DE PEAK SHAVING BESS v5.6 (AGGRESSIVE DISCHARGE)')
print('=' * 80)
print()
print('Peak Shaving BESS->MALL:')
print(f'  Total anual:          {df["bess_to_mall_kwh"].sum():,.0f} kWh/año')
print(f'  Promedio diario:      {df["bess_to_mall_kwh"].sum()/365:,.0f} kWh/día')
print(f'  Máximo horario:       {df["bess_to_mall_kwh"].max():,.0f} kW')
print(f'  Horas activas:        {(df["bess_to_mall_kwh"] > 0).sum()} horas')
print()

# Análisis de descarga a 1900 kW
mall_values = df['mall_kwh'].values
bess_to_mall = df['bess_to_mall_kwh'].values
peak_threshold = 1900.0

mall_above_1900 = (mall_values > peak_threshold).sum()
mall_above_peak_avg = mall_values[mall_values > peak_threshold].mean()
bess_peak_shaving_during_peaks = bess_to_mall[mall_values > peak_threshold].sum()

print('Análisis de corte > 1900 kW:')
print(f'  Horas con MALL > 1900 kW:  {mall_above_1900} horas')
print(f'  MALL promedio en picos:    {mall_above_peak_avg:,.0f} kW')
print(f'  BESS peak shaving total:   {bess_peak_shaving_during_peaks:,.0f} kWh')
print(f'  BESS promedio x pico:      {bess_peak_shaving_during_peaks/max(mall_above_1900, 1):.1f} kWh/hora')
print()

# Comparación con grid export
print('Energía exportada y peak shaving:')
print(f'  Grid export total:        {df["grid_export_kwh"].sum():,.0f} kWh/año')
print(f'  Peak shaving total:       {df["bess_to_mall_kwh"].sum():,.0f} kWh/año')
print(f'  Ratio peak/export:        {df["bess_to_mall_kwh"].sum() / max(df["grid_export_kwh"].sum(), 1) * 100:.1f}%')
print()

# Horarios de descarga agresiva
hour_of_day = np.arange(8760) % 24
for h in [0, 6, 12, 18, 22]:
    mask_hour = hour_of_day == h
    peak_at_hour = bess_to_mall[mask_hour].sum()
    if peak_at_hour > 0:
        print(f'  Hora {h:02d}h: {peak_at_hour:,.0f} kWh peak shaving')

print()
print('=' * 80)
