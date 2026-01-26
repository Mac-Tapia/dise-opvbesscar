#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('data/interim/oe2/bess/bess_operation_profile.csv')

print("BESS Profile Verification")
print("=" * 60)
print(f"Filas: {len(df)}")
print(f"Columnas: {list(df.columns)}")
print(f"\nPrimeras 5 filas:")
print(df.head())
print(f"\nResumen SOC:")
print(f"Media: {df['soc_percent'].mean():.1f}%")
print(f"Min: {df['soc_percent'].min():.1f}%")
print(f"Max: {df['soc_percent'].max():.1f}%")
print(f"\nCarga/Descarga Anual:")
print(f"Carga total: {df['charge_energy_kwh'].sum():.0f} kWh")
print(f"Descarga total: {df['discharge_energy_kwh'].sum():.0f} kWh")
