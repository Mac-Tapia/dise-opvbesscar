import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['hour'] = pd.to_datetime(df['datetime']).dt.hour

criticas = df[(df['hour'] >= 17) & (df['hour'] <= 22)].copy()

# Analizar energía
print("\nENERGIA DISPONIBLE vs DESCARGADA (17h-22h):")
print("-" * 100)

soc_init = criticas.iloc[0]['bess_soc_percent']
capacity = 1700
soc_min = 20

# Energía teórica disponible
energy_available_theory = (soc_init - soc_min) / 100 * capacity
print(f"Energía teórica disponible: ({soc_init:.1f}%-{soc_min}%) × {capacity} = {energy_available_theory:.0f} kWh")
print(f"En {len(criticas)} horas: {energy_available_theory / len(criticas):.1f} kWh/h = {energy_available_theory/len(criticas):.1f} kW")

# Energía real descargada
ev_descargado = criticas['bess_to_ev_kwh'].sum()
mall_descargado = criticas['bess_to_mall_kwh'].sum()
total_descargado = ev_descargado + mall_descargado

print(f"\nEnergía real descargada: {total_descargado:.0f} kWh")
print(f"  EV: {ev_descargado:.0f} kWh")
print(f"  MALL: {mall_descargado:.0f} kWh")
print(f"  Promedio horario: {total_descargado / len(criticas):.1f} kWh/h = {total_descargado/len(criticas):.1f} kW")

# Diferencia
diferencia = energy_available_theory - total_descargado
print(f"\nDiferencia (no descargada): {diferencia:.0f} kWh ({diferencia/energy_available_theory*100:.1f}% del disponible)")

# Calcular potencia promedio requerida
print(f"\nPOTENCIA PROMEDIO REQUERIDA (17h-22h):")
print("-" * 100)
ev_demand_total = criticas['ev_demand_kwh'].sum()
mall_demand_total = criticas['mall_demand_kwh'].sum()

print(f"EV demand total: {ev_demand_total:.0f} kWh ({ev_demand_total/len(criticas):.1f} kW promedio)")
print(f"MALL demand total: {mall_demand_total:.0f} kWh ({mall_demand_total/len(criticas):.1f} kW promedio)")
print(f"Demanda combinada: {ev_demand_total + mall_demand_total:.0f} kWh ({(ev_demand_total+mall_demand_total)/len(criticas):.1f} kW promedio)")

# Cobertura BESS vs total (incluyendo PV)
pv_to_ev = criticas['pv_to_ev_kwh'].sum()
print(f"\nCobertura EV:")
print(f"  PV directo: {pv_to_ev:.0f} kWh")
print(f"  BESS: {ev_descargado:.0f} kWh")
print(f"  Total: {pv_to_ev + ev_descargado:.0f} kWh / {ev_demand_total:.0f} kWh = {(pv_to_ev + ev_descargado) / ev_demand_total * 100:.1f}%")

print("\n" + "=" * 100)
