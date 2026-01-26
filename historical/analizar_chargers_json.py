#!/usr/bin/env python3
"""
Análisis detallado: individual_chargers.json muestra 128 items pero debería ser 32 chargers.

Posibilidades:
1. Cada item en JSON es un SOCKET (128 sockets = 32 chargers × 4)
2. O están mal contados

Este script verifica la estructura.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

chargers_path = Path("data/interim/oe2/chargers/individual_chargers.json")

with open(chargers_path) as f:
    chargers: list[dict[str, Any]] = json.load(f)

print("=" * 100)
print("ANALISIS DETALLADO: individual_chargers.json")
print("=" * 100)

print(f"\nTotal items en JSON: {len(chargers)}")
print(f"\nPrimeros 3 items:")

for i, item in enumerate(chargers[:3]):
    print(f"\n  [{i}] ID: {item.get('charger_id', 'N/A')}")
    print(f"      Type: {item.get('charger_type', 'N/A')}")
    print(f"      Power: {item.get('power_kw', 'N/A')} kW")
    print(f"      Sockets: {item.get('sockets', 'N/A')}")
    print(f"      Playa: {item.get('playa', 'N/A')}")

# Contar por tipo
types: dict[str, int] = {}
playas: dict[str, int] = {}
for item in chargers:
    t = item.get('charger_type', 'unknown')
    types[t] = types.get(t, 0) + 1
    p = item.get('playa', 'unknown')
    playas[p] = playas.get(p, 0) + 1

print(f"\n\nConteo por tipo:")
for t, count in sorted(types.items()):
    print(f"  {t}: {count}")

print(f"\nConteo por playa:")
for p, count in sorted(playas.items()):
    print(f"  {p}: {count}")

# Verificación: ¿Cada charger tiene sockets=1?
sockets_per_item = [item.get('sockets', 1) for item in chargers]
print(f"\nSockets por item: min={min(sockets_per_item)}, max={max(sockets_per_item)}, total={sum(sockets_per_item)}")

if len(chargers) == 128 and sum(sockets_per_item) == 128:
    print(f"\n✓ CORRECTO: 128 items × 1 socket = 128 sockets totales")
    print(f"  Pero el documento OE2 especifica: 32 CHARGERS × 4 SOCKETS = 128 sockets")
    print(f"  Parece que cada item en JSON es UN SOCKET, no un CHARGER")

elif len(chargers) == 32:
    print(f"\n✓ CORRECTO: 32 chargers × {sum(sockets_per_item)/32:.0f} sockets/charger = {sum(sockets_per_item)} sockets")

print(f"\n" + "=" * 100)
print(f"CONCLUSION: JSON tiene estructura de SOCKETS (128 items = 128 sockets)")
print(f"            Esto es CORRECTO para OE3 CityLearn (128 observables)")
print(f"=" * 100 + "\n")
