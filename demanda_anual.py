#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';')
total = df['kWh'].sum()

print(f'\n📊 DEMANDA MALL ANUAL (REAL)\n{"="*60}')
print(f'Energía total:    {total:>15,.0f} kWh')
print(f'Energía total:    {total/1000:>15,.2f} MWh')
print(f'Energía total:    {total/1000/1000:>15,.3f} GWh')
print(f'\nPromedio horario: {df["kWh"].mean():>15,.1f} kWh/h')
print(f'Promedio diario:  {total/365:>15,.1f} kWh/día')
print(f'Promedio mensual: {total/12:>15,.0f} kWh/mes')
print(f'\nMínimo horario:   {df["kWh"].min():>15,.0f} kWh/h')
print(f'Máximo horario:   {df["kWh"].max():>15,.0f} kWh/h')
print(f'{"="*60}\n')
