#!/usr/bin/env python3
"""Inspeccionar estructura de cargadores en OE2."""

import json
from pathlib import Path

oe2_path = Path('data/interim/oe2/chargers')

print("[OE2 CHARGERS INSPECTION]", flush=True)
print("=" * 70)

# [1] Resultados OE2
try:
    results = json.loads((oe2_path / 'chargers_results.json').read_text())
    print(f"\n[1] OE2 Chargers Results:")
    print(f"    n_chargers_recommended: {results.get('n_chargers_recommended')}")
    print(f"    total_sockets: {results.get('total_sockets')}")
    print(f"    config: {results.get('config')}")
except Exception as e:
    print(f"[ERROR] {e}")

# [2] Cargadores individuales
try:
    chargers = json.loads((oe2_path / 'individual_chargers.json').read_text())
    print(f"\n[2] Individual Chargers (OE2):")
    print(f"    Total entries: {len(chargers)}")
    if chargers:
        print(f"    First charger: {chargers[0]}")
        print(f"    Last charger: {chargers[-1]}")
except Exception as e:
    print(f"[ERROR] {e}")

# [3] Distribución por tipo
try:
    chargers = json.loads((oe2_path / 'individual_chargers.json').read_text())
    motos = [c for c in chargers if 'moto' in c.get('charger_type', '').lower() and 'taxi' not in c.get('charger_type', '').lower()]
    mototaxis = [c for c in chargers if 'taxi' in c.get('charger_type', '').lower()]

    print(f"\n[3] Distribution by Type:")
    print(f"    Motos chargers: {len(motos)}")
    print(f"    Mototaxis chargers: {len(mototaxis)}")
    print(f"    Total chargers (devices): {len(chargers)}")
    print(f"    Total sockets (tomas): {len(chargers) * 4}")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 70 + "\n", flush=True)
