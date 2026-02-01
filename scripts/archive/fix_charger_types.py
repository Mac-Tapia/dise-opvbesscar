#!/usr/bin/env python3
"""Corregir tipos de chargers en JSON: mototaxi -> moto_taxi."""

import json
from pathlib import Path

file_path = Path('data/interim/oe2/chargers/individual_chargers.json')

# Leer el JSON
chargers = json.load(open(file_path, encoding='utf-8'))

# Corregir: mototaxi -> moto_taxi
for charger in chargers:
    if charger.get('charger_type') == 'mototaxi':
        charger['charger_type'] = 'moto_taxi'

# Guardar corregido
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(chargers, f, indent=2, ensure_ascii=False)

print("✓ Corregido individual_chargers.json: mototaxi -> moto_taxi")

# Verificar
chargers_fixed = json.load(open(file_path, encoding='utf-8'))
motos = sum(1 for ch in chargers_fixed if ch.get('charger_type') == 'moto')
mototaxis = sum(1 for ch in chargers_fixed if ch.get('charger_type') == 'moto_taxi')
print(f"✓ Motos:       {motos}")
print(f"✓ Mototaxis:   {mototaxis}")
print(f"✓ TOTAL:       {motos + mototaxis}")
