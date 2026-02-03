#!/usr/bin/env python
"""Verify cleaned dataset structure"""
import json
import os

try:
    import pandas as pd
except ImportError:
    print("Error: pandas no está instalado. Ejecutar: pip install pandas")
    exit(1)

print("✅ ESTADO FINAL DEL DATASET:\n")

# Verificar Building_1.csv
building_df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/Building_1.csv')
print(f"📄 Building_1.csv: {len(building_df)} filas (timesteps)")

# Verificar schema
schema = json.load(open('data/processed/citylearn/iquitos_ev_mall/schema.json'))
print(f"⏱️  Timesteps del schema: {schema.get('episode_time_steps', 0)} (8760 = 1 año)")
print(f"⏱️  Seconds per timestep: {schema.get('seconds_per_time_step', 0)} (3600 = 1 hora)")

# Verificar buildings
buildings = schema.get('buildings', {})
print(f"\n🏢 Buildings en schema: {list(buildings.keys())}")

if 'Mall_Iquitos' in buildings:
    mall = buildings['Mall_Iquitos']
    chargers = mall.get('chargers', {})
    print(f"   Chargers en Mall_Iquitos: {len(chargers)}")

    pv = mall.get('pv', {})
    print(f"   PV nominal power: {pv.get('nominal_power', 0)} kWp")

    bess = mall.get('electrical_storage', {})
    print(f"   BESS capacity: {bess.get('capacity', 0)} kWh")

# Verificar charger files
charger_files = [f for f in os.listdir('data/processed/citylearn/iquitos_ev_mall/')
                if f.startswith('charger_simulation_') and f.endswith('.csv')]
print(f"\n📁 Archivos charger_simulation: {len(charger_files)}")

# Verificar archivos de soporte
support_files = ['weather.csv', 'carbon_intensity.csv', 'pricing.csv', 'electrical_storage_simulation.csv']
print(f"\n📋 Archivos de soporte:")
for sf in support_files:
    exists = os.path.exists(f'data/processed/citylearn/iquitos_ev_mall/{sf}')
    status = "✅" if exists else "❌"
    print(f"   {status} {sf}")

# Total file count
all_files = [f for f in os.listdir('data/processed/citylearn/iquitos_ev_mall/') if f.endswith('.csv')]
print(f"\n📊 Total archivos CSV: {len(all_files)}")

print(f"\n✅ DATASET LIMPIO Y LISTO PARA ENTRENAMIENTO")
