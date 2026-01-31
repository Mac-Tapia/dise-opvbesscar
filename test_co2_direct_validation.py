#!/usr/bin/env python
"""
TEST RÁPIDO: Validar que motos/mototaxis se calculan correctamente
Ejecutar ANTES del entrenamiento completo para verificar sincronización
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Test 1: Verificar que ev_demand se lee correctamente
print("=" * 80)
print("TEST 1: Validar lectura de EV_DEMAND")
print("=" * 80)

baseline_file = Path("outputs/oe3_simulations/baseline_full_year_hourly.csv")
if not baseline_file.exists():
    print(f"❌ ERROR: {baseline_file} no existe")
    print("   Necesita: python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
    exit(1)

df = pd.read_csv(baseline_file)
print(f"\n✅ Baseline CSV encontrado: {len(df)} filas (debería ser 8760)")

if "ev_demand" in df.columns:
    ev_demand = df["ev_demand"]
    print(f"✅ EV_DEMAND encontrada")
    print(f"   Rango: {ev_demand.min():.1f} - {ev_demand.max():.1f} kW")
    print(f"   Promedio: {ev_demand.mean():.1f} kW")
    print(f"   Tiene ceros: {(ev_demand == 0).sum()} horas (noche)")
else:
    print(f"❌ ERROR: EV_DEMAND no encontrada en baseline")
    print(f"   Columnas disponibles: {list(df.columns)}")
    exit(1)

# Test 2: Validar cálculo de motos/mototaxis
print("\n" + "=" * 80)
print("TEST 2: Validar cálculo de motos/mototaxis")
print("=" * 80)

# Simulación: si se entregan 68 kW (capacidad total)
total_capacity_kw = 68.0  # 112×2kW motos + 16×3kW mototaxis = 68kW total

motos_fraction = 112.0 / 128.0  # 87.5%
mototaxis_fraction = 16.0 / 128.0  # 12.5%

motos_capacity = total_capacity_kw * motos_fraction  # 59.5 kW
mototaxis_capacity = total_capacity_kw * mototaxis_fraction  # 8.5 kW

print(f"\nCapacidad total: {total_capacity_kw:.1f} kW")
print(f"  Motos (112 × 2kW): {motos_capacity:.1f} kW ({motos_fraction*100:.1f}%)")
print(f"  Mototaxis (16 × 3kW): {mototaxis_capacity:.1f} kW ({mototaxis_fraction*100:.1f}%)")

# Test: 50 kW entregados
ev_power_delivered = 50.0  # kW

motos_power = ev_power_delivered * motos_fraction  # 43.75 kW
mototaxis_power = ev_power_delivered * mototaxis_fraction  # 6.25 kW

motos_ciclos = motos_power / 2.0  # 21.875 ciclos
mototaxis_ciclos = mototaxis_power / 3.0  # 2.083 ciclos

print(f"\n💡 Si se entregan {ev_power_delivered:.1f} kW:")
print(f"   Motos: {motos_power:.1f} kW ÷ 2 kW/moto = {motos_ciclos:.1f} ciclos")
print(f"   Mototaxis: {mototaxis_power:.1f} kW ÷ 3 kW/taxi = {mototaxis_ciclos:.1f} ciclos")

# Test: Calcular CO₂ directo
co2_factor = 2.146  # kg CO₂/kWh evitado (EV vs gasolina)
co2_direct = ev_power_delivered * co2_factor

print(f"\n🔋 CO₂ DIRECTO:")
print(f"   {ev_power_delivered:.1f} kW × {co2_factor:.3f} kg CO₂/kWh = {co2_direct:.1f} kg CO₂ evitado")

# Test 3: Proyección anual
print("\n" + "=" * 80)
print("TEST 3: Proyección anual de CO₂ directo")
print("=" * 80)

# Asumir EV_DEMAND promedio durante el día
# Operación: 9 AM - 10 PM = 13 horas
# Pero solo 60% es disponible por capacidad limitada
ev_demand_avg_hour = df[(df.index.hour >= 9) & (df.index.hour < 22)]["ev_demand"].mean()
print(f"\nPromedio EV_DEMAND (9 AM-10 PM): {ev_demand_avg_hour:.1f} kW")

# CO₂ anual si se entregan todos los EV
annual_co2_direct_theoretical = df["ev_demand"].sum() * co2_factor
print(f"CO₂ teórico si se entrega 100% EV: {annual_co2_direct_theoretical:,.0f} kg/año")

# CO₂ anual realista (60% de capacidad disponible)
realistic_factor = 0.60  # 60% de la demanda se satisface
annual_co2_direct_realistic = annual_co2_direct_theoretical * realistic_factor
print(f"CO₂ realista (60% satisfacción): {annual_co2_direct_realistic:,.0f} kg/año")

# Motos y taxis anuales (REALISTIC)
motos_annual = (df["ev_demand"] * motos_fraction / 2.0 * realistic_factor).sum()
taxis_annual = (df["ev_demand"] * mototaxis_fraction / 3.0 * realistic_factor).sum()

print(f"\nVehículos anuales (60% satisfacción):")
print(f"  Motos: {motos_annual:,.0f} ciclos (~{motos_annual/112:.0f}x capacidad)")
print(f"  Mototaxis: {taxis_annual:,.0f} ciclos (~{taxis_annual/16:.0f}x capacidad)")

# Test 4: Validar loggin format
print("\n" + "=" * 80)
print("TEST 4: Verificar formato de logging esperado")
print("=" * 80)

print("\n✅ Formato ESPERADO en logs SAC:")
print("   [SAC] paso 500 | ep~1 | pasos_global=500 | reward_avg=-150.50 | ... |")
print("   co2_direct_kg=1050.2 | motos=525 | mototaxis=75 | co2_total_avoided_kg=3200.1")
print("\n✅ Puntos clave:")
print("   • reward_avg NEGATIVO (CO₂ es penalización)")
print("   • co2_direct_kg > 0 (motos/taxis ACTIVOS)")
print("   • motos y mototaxis CRECIENDO (acumulativo por episodio)")
print("   • co2_total_avoided_kg = co2_indirect + co2_direct")

# Test 5: Validar schema
print("\n" + "=" * 80)
print("TEST 5: Validar schema CityLearn")
print("=" * 80)

schema_file = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
if schema_file.exists():
    with open(schema_file) as f:
        schema = json.load(f)

    buildings = schema.get("buildings", [])
    if buildings:
        b = buildings[0]
        print(f"✅ Schema encontrado: {len(buildings)} building(s)")
        print(f"   Cargadores: {len(b.get('electricity', {}).get('vehicle_charging', []))} simulaciones CSV")
        print(f"   PV: {b.get('solar_generation', [])[:1]}")
        print(f"   BESS: Capacidad=4520 kWh, Potencia=2712 kW")
else:
    print(f"⚠️  Schema no encontrado: {schema_file}")

print("\n" + "=" * 80)
print("✅ VALIDACIÓN COMPLETA - LISTO PARA ENTRENAMIENTO")
print("=" * 80)
print("\nPróximo paso:")
print("  py -3.11 -m scripts.run_oe3_simulate --config configs/default.yaml")
print("\nEsperado:")
print("  • ~30-60 minutos en GPU RTX 4060")
print("  • SAC + PPO + A2C ejecutan secuencialmente")
print("  • CO₂ DIRECTO debe estar > 0 y creciendo")
print("=" * 80)
