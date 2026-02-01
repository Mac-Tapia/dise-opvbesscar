#!/usr/bin/env python3
"""Analizar configuración de tipos de chargers."""

import json

print("\n" + "=" * 80)
print("ANÁLISIS DE TIPOS DE CHARGERS")
print("=" * 80)

chargers = json.load(open('data/interim/oe2/chargers/individual_chargers.json'))

print(f"\nTotal chargers: {len(chargers)}\n")

# Conteo por tipo
motos = [ch for ch in chargers if ch.get('charger_type', '').lower() == 'moto']
mototaxis = [ch for ch in chargers if ch.get('charger_type', '').lower() == 'moto_taxi']
undefined = [ch for ch in chargers if ch.get('charger_type', '').lower() not in ['moto', 'moto_taxi']]

print(f"Motos (2kW):       {len(motos)} chargers")
print(f"Mototaxis (3kW):   {len(mototaxis)} chargers")
print(f"Undefined/otros:   {len(undefined)} chargers")
print(f"TOTAL:             {len(motos) + len(mototaxis) + len(undefined)} chargers")

# Verificar primeros y últimos
print(f"\n--- PRIMEROS 5 ---")
for i, ch in enumerate(chargers[:5]):
    print(f"{i:3d}: type={ch.get('charger_type', 'N/A'):12s} power={ch.get('power_kw', 0)}kW")

print(f"\n--- ÚLTIMOS 5 ---")
for i, ch in enumerate(chargers[-5:], start=len(chargers)-5):
    print(f"{i:3d}: type={ch.get('charger_type', 'N/A'):12s} power={ch.get('power_kw', 0)}kW")

# Verificar alrededor de índice 112 (donde debería cambiar de motos a mototaxis)
print(f"\n--- ALREDEDOR DE ÍNDICE 112 (transición) ---")
for i in range(110, min(118, len(chargers))):
    ch = chargers[i]
    print(f"{i:3d}: type={ch.get('charger_type', 'N/A'):12s} power={ch.get('power_kw', 0)}kW")

# Estadísticas de potencia
print(f"\n--- ESTADÍSTICAS DE POTENCIA ---")
powers = {ch.get('power_kw', 0): 0 for ch in chargers}
for ch in chargers:
    powers[ch.get('power_kw', 0)] = powers.get(ch.get('power_kw', 0), 0) + 1

for power, count in sorted(powers.items()):
    print(f"{power}kW:  {count} chargers")

print("\n" + "=" * 80)
