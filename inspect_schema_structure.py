#!/usr/bin/env python
"""Inspect schema.json structure in detail"""
import json
from pathlib import Path

schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")

if not schema_path.exists():
    print(f"❌ Schema no encontrado en: {schema_path}")
    exit(1)

with open(schema_path) as f:
    schema = json.load(f)

print("=" * 70)
print("ESTRUCTURA DEL SCHEMA - VALORES CRÍTICOS")
print("=" * 70)

print("\n1. PARÁMETROS GLOBALES DEL SCHEMA:")
print(f"   episode_time_steps: {schema.get('episode_time_steps')} (ESPERADO: 8760)")
print(f"   simulation_start_time_step: {schema.get('simulation_start_time_step')}")
print(f"   simulation_end_time_step: {schema.get('simulation_end_time_step')}")
print(f"   central_agent: {schema.get('central_agent')} (ESPERADO: True)")
print(f"   seconds_per_time_step: {schema.get('seconds_per_time_step')} (ESPERADO: 3600)")
print(f"   random_seed: {schema.get('random_seed')}")

building = schema.get('buildings', {}).get('Mall_Iquitos', {})
if not building:
    print("\n❌ Building 'Mall_Iquitos' no encontrado")
    exit(1)

print(f"\n2. BUILDING 'Mall_Iquitos' - Claves presentes:")
keys = list(building.keys())
print(f"   Total keys: {len(keys)}")
print(f"   Keys: {keys[:15]}{'...' if len(keys) > 15 else ''}")

# BESS
bess = building.get('electrical_storage', {})
print(f"\n3. ELECTRICAL STORAGE (BESS):")
print(f"   Presente: {'✅ SÍ' if bess else '❌ NO'}")
if bess:
    attrs = bess.get('attributes', {})
    print(f"   capacity: {attrs.get('capacity')} (ESPERADO: 2000 kWh OE3)")
    print(f"   power_output_nominal: {attrs.get('power_output_nominal')} (ESPERADO: 1200 kW)")

# PV
pv = building.get('pv', {})
print(f"\n4. FOTOVOLTAICA (PV):")
print(f"   Presente: {'✅ SÍ' if pv else '❌ NO'}")
if pv:
    attrs = pv.get('attributes', {})
    print(f"   peak_power: {attrs.get('peak_power')} (ESPERADO: 4050 kWp)")

# Chargers
chargers = building.get('electrical_devices', {})
print(f"\n5. CHARGERS (ELECTRICAL DEVICES):")
print(f"   Total: {len(chargers)} (ESPERADO: 128)")
if chargers:
    first_charger_key = list(chargers.keys())[0]
    first_charger = chargers[first_charger_key]
    print(f"   Ejemplo (primero): {first_charger_key}")
    print(f"     - Atributos: {list(first_charger.get('attributes', {}).keys())}")

# Errores detectados
print("\n" + "=" * 70)
print("VALIDACIÓN - ERRORES DETECTADOS:")
print("=" * 70)

errors = []
if schema.get('episode_time_steps') is None:
    errors.append("❌ episode_time_steps es None (DEBE SER 8760)")

if schema.get('episode_time_steps') != 8760:
    errors.append(f"❌ episode_time_steps = {schema.get('episode_time_steps')} (DEBE SER 8760)")

if building.get('pv', {}).get('attributes', {}).get('peak_power') is None:
    errors.append("❌ pv.attributes.peak_power es None (DEBE SER 4050)")

if len(chargers) != 128:
    errors.append(f"❌ Chargers: {len(chargers)} (DEBE SER 128)")

if schema.get('central_agent') != True:
    errors.append(f"❌ central_agent: {schema.get('central_agent')} (DEBE SER True)")

if errors:
    for err in errors:
        print(err)
    print(f"\n⚠️  TOTAL ERRORES: {len(errors)}")
else:
    print("✅ TODOS LOS VALORES CRÍTICOS SON CORRECTOS")

print("\n" + "=" * 70)
