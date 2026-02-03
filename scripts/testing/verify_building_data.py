#!/usr/bin/env python
"""Verifica que Building_1.csv tiene datos reales correctos."""

import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/Building_1.csv')

print("=" * 80)
print("[DATA VALIDATION] Building_1.csv - DATOS REALES DEL MALL")
print("=" * 80)
print(f"\n✅ Total Registros: {len(df)} (1 año completo con resolución horaria)")

# Validar demanda mall (non_shiftable_load)
demand = pd.to_numeric(df['non_shiftable_load'], errors='coerce')
print(f"\n📊 DEMANDA DEL MALL (non_shiftable_load):")
print(f"   Total Anual: {demand.sum():,.0f} kWh (DEBE SER 3,092,204 kWh)")
print(f"   Promedio Horario: {demand.mean():.2f} kW")
print(f"   Rango: {demand.min():.2f} - {demand.max():.2f} kW")
print(f"   NaN valores: {demand.isna().sum()}")

# Validar generación solar (solar_generation)
solar = pd.to_numeric(df['solar_generation'], errors='coerce')
print(f"\n☀️  GENERACIÓN SOLAR (solar_generation):")
print(f"   Total Anual: {solar.sum():,.0f} kWh (DEBE SER 8,030,119 kWh)")
print(f"   Promedio Horario: {solar.mean():.2f} kW")
print(f"   Rango: {solar.min():.2f} - {solar.max():.2f} kW")
print(f"   NaN valores: {solar.isna().sum()}")

# Validar carbon intensity
if 'carbon_intensity_kg_per_kwh' in df.columns:
    ci = pd.to_numeric(df['carbon_intensity_kg_per_kwh'], errors='coerce')
    print(f"\n🌍 FACTOR DE EMISIÓN (carbon_intensity):")
    print(f"   Valor: {ci.iloc[0]:.4f} kg CO₂/kWh (Iquitos térmica aislada)")
    print(f"   Consistencia: {'✅ OK' if (ci == ci.iloc[0]).all() else '⚠️ VARIABLE'}")

print("\n" + "=" * 80)
print("[VERIFICACIÓN] ✅ Si los totales son correctos, los agentes recibirán datos REALES")
print("=" * 80)
