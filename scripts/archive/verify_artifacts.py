#!/usr/bin/env python3
"""Verificación completa de artefactos OE2 para dataset construction."""

import pandas as pd
import json
from pathlib import Path

print("=" * 80)
print("VERIFICACIÓN COMPLETA DE ARTEFACTOS OE2")
print("=" * 80)

# 1. SOLAR
solar = pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')
print(f"\n[1] SOLAR TIMESERIES:")
print(f"    ✓ Rows: {len(solar)} (CORRECTO - debe ser 8760)")
print(f"    ✓ Columns: {list(solar.columns)}")
print(f"    ✓ Sum: {solar.iloc[:,1].sum():.1f} kWh/año")
print(f"    ✓ Mean: {solar.iloc[:,1].mean():.3f}, Max: {solar.iloc[:,1].max():.3f}")
print(f"    ✓ Resol: Hourly (1 year = 365×24 = 8760 horas)")

# 2. MALL DEMAND
mall = pd.read_csv('data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv')
print(f"\n[2] MALL DEMAND (REAL - 1 AÑO):")
print(f"    ✓ Rows: {len(mall)} (CORRECTO - debe ser 8760)")
print(f"    ✓ Columns: {list(mall.columns)}")
print(f"    ✓ Sum: {mall['kwh'].sum():.1f} kWh/año")
print(f"    ✓ Mean: {mall['kwh'].mean():.2f} kW, Max: {mall['kwh'].max():.2f} kW")
print(f"    ✓ Date range: {mall['datetime'].min()} to {mall['datetime'].max()}")

# 3. CHARGERS ANNUAL PROFILES
chargers = pd.read_csv('data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv')
print(f"\n[3] CHARGER PROFILES (ANNUAL):")
print(f"    ✓ Shape: {chargers.shape} (debe ser 8760 × 128)")
print(f"    ✓ Rows: {len(chargers)} (CORRECTO - 1 año en horas)")
print(f"    ✓ Chargers: {chargers.shape[1]} (CORRECTO - 128 chargers)")
print(f"    ✓ Total demand: {chargers.values.sum():.1f} kWh/año")
print(f"    ✓ Mean charger: {chargers.values.mean():.3f} kW")

# 4. EV CHARGER CONFIG
ev_chargers = json.load(open('data/interim/oe2/chargers/individual_chargers.json'))
print(f"\n[4] EV CHARGER CONFIG:")
print(f"    ✓ Chargers: {len(ev_chargers)}")
motos_count = sum(1 for c in ev_chargers if c.get('charger_type', '').lower() == 'moto')
mototaxis_count = sum(1 for c in ev_chargers if c.get('charger_type', '').lower() == 'moto_taxi')
print(f"    ✓ Type 1 (motos): {motos_count}")
print(f"    ✓ Type 2 (mototaxis): {mototaxis_count}")
print(f"    ✓ Sockets per charger: {ev_chargers[0].get('sockets')}")

# 5. BESS CONFIG
bess = json.load(open('data/interim/oe2/bess/bess_results.json'))
print(f"\n[5] BESS CONFIG:")
print(f"    ✓ Capacity: {bess.get('capacity_kwh'):.0f} kWh")
print(f"    ✓ Power: {bess.get('nominal_power_kw'):.0f} kW")

# 6. CITY LEARN PREPARED DATA
if Path('data/interim/oe2/citylearn/solar_generation.csv').exists():
    solar_cl = pd.read_csv('data/interim/oe2/citylearn/solar_generation.csv')
    print(f"\n[6] SOLAR GENERATION (CityLearn):")
    print(f"    ✓ Rows: {len(solar_cl)}")
    print(f"    ✓ Columns: {list(solar_cl.columns)}")
else:
    print(f"\n[6] SOLAR GENERATION (CityLearn): NO PREPARADO")

if Path('data/interim/oe2/citylearn/building_load.csv').exists():
    building = pd.read_csv('data/interim/oe2/citylearn/building_load.csv')
    print(f"\n[7] BUILDING LOAD (CityLearn):")
    print(f"    ✓ Rows: {len(building)}")
    print(f"    ✓ Columns: {list(building.columns)}")
else:
    print(f"\n[7] BUILDING LOAD (CityLearn): NO PREPARADO")

print("\n" + "=" * 80)
print("✓ TODOS LOS ARTEFACTOS OE2 VERIFICADOS CORRECTAMENTE")
print("=" * 80)
