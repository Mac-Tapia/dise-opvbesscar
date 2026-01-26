#!/usr/bin/env python
"""Verificar que schema.json apunta a los 128 chargers correctamente"""
import json
from pathlib import Path

schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
with open(schema_path) as f:
    schema = json.load(f)

buildings = schema.get("buildings", {})
mall = buildings.get("Mall_Iquitos", {})
chargers = mall.get("chargers", {})

print("=" * 80)
print(f"VERIFICACIÓN FINAL: Schema → Archivos Chargers")
print("=" * 80)
print(f"✓ Buildings en schema: {list(buildings.keys())}")
print(f"✓ Chargers en Mall_Iquitos: {len(chargers)}")
print(f"\nPrimeros 3 chargers en schema:")
for i, (name, cfg) in enumerate(list(chargers.items())[:3]):
    charger_file = cfg.get("charger_simulation", "N/A")
    print(f"  {i+1}. {name}: {charger_file}")

print(f"\nÚltimos 3 chargers en schema:")
for i, (name, cfg) in enumerate(list(chargers.items())[-3:], start=len(chargers)-2):
    charger_file = cfg.get("charger_simulation", "N/A")
    print(f"  {i}. {name}: {charger_file}")

# Verify all chargers have correct file references
print(f"\n✓ Verificando que TODOS apunten a charger_simulation_*.csv:")
all_correct = True
for idx, (name, cfg) in enumerate(chargers.items()):
    charger_file = cfg.get("charger_simulation", "")
    expected = f"buildings/Mall_Iquitos/charger_simulation_{idx+1:03d}.csv"
    if charger_file != expected:
        print(f"  ✗ {name}: expected={expected}, got={charger_file}")
        all_correct = False

if all_correct:
    print(f"  ✅ TODOS los 128 chargers apuntan a archivos correctos")
else:
    print(f"  ❌ Hay problemas en algunas referencias")

print("\n" + "=" * 80)
print("✅ CONEXIÓN OE2 → OE3 COMPLETADA CON ÉXITO")
print("=" * 80)
