#!/usr/bin/env python3
import pandas as pd

bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print('=' * 80)
print('VERIFICACION - CAPACIDAD REAL DEL BESS')
print('=' * 80)

# Buscar maximo de SOC
if 'soc_kwh' in bess_df.columns:
    max_soc = bess_df['soc_kwh'].max()
    min_soc = bess_df['soc_kwh'].min()
    med_soc = bess_df['soc_kwh'].mean()
    
    print('\nColumna: soc_kwh')
    print(f'  Maximo (capacidad): {max_soc:.1f} kWh')
    print(f'  Minimo (DoD): {min_soc:.1f} kWh')
    print(f'  Promedio: {med_soc:.1f} kWh')
    print(f'  Rango: {max_soc - min_soc:.1f} kWh')

if 'soc_percent' in bess_df.columns:
    print(f'\nColumna: soc_percent')
    print(f'  Maximo: {bess_df["soc_percent"].max():.1f}%')
    print(f'  Minimo: {bess_df["soc_percent"].min():.1f}%')

print('\n' + '=' * 80)
print('CONCLUSION:')
print(f'Capacidad real del BESS = {max_soc:.0f} kWh')
print(f'Valor en data_loader.py = 2000.0 kWh')
if max_soc != 2000:
    print(f'ERROR: DIFERENCIA = {max_soc - 2000:.0f} kWh')
    print('NECESARIO ACTUALIZAR data_loader.py')
else:
    print('OK: Valor coincide')
