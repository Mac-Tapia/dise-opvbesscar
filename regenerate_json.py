#!/usr/bin/env python
"""Regenerar dataset_config_v7.json forzadamente."""

import json
from pathlib import Path
from src.dataset_builder_citylearn.data_loader import build_citylearn_dataset, save_citylearn_dataset

print("="*80)
print("Regenerando dataset_config_v7.json...")
print("="*80)

# Forzar regeneración completa
dataset = build_citylearn_dataset()
output_dir = save_citylearn_dataset(dataset)

# Leer y mostrar lo que se guardó
config_path = output_dir / "dataset_config_v7.json"
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

print("\n✅ JSON GENERADO CON CONTENIDO:")
print("\nSECCION VEHICLES:")
print(json.dumps(config.get("vehicles"), indent=2))

print("\n\nSECCION DEMAND:")
print(json.dumps(config.get("demand"), indent=2))

print("\n\nSECCION SOLAR:")
print(json.dumps(config.get("solar"), indent=2))

print("\nSECCION SYSTEM:")
system = config.get("system", {})
print(f"  PV: {system.get('pv_capacity_kwp')} kWp")
print(f"  BESS: {system.get('bess_capacity_kwh')} kWh")
print(f"  Chargers: {system.get('n_chargers')} × {system.get('charger_power_kw')} kW")
print(f"  Sockets: {system.get('n_sockets')}")

print("\n" + "="*80)
print("✅ ACTUALIZACIÓN COMPLETADA")
print(f"Archivo: {config_path}")
print("="*80)
