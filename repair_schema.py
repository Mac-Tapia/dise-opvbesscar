#!/usr/bin/env python
"""Repair schema.json with missing critical fields"""
import json
from pathlib import Path
import shutil
from datetime import datetime

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')

# Backup
backup_path = schema_path.parent / f'schema_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
shutil.copy(schema_path, backup_path)
print(f"✅ Backup creado: {backup_path}")

# Load
with open(schema_path) as f:
    schema = json.load(f)

print("\n" + "="*70)
print("REPARACIÓN DEL SCHEMA")
print("="*70)

# Repair 1: episode_time_steps
old_val = schema.get('episode_time_steps')
schema['episode_time_steps'] = 8760
print(f"\n1. episode_time_steps:")
print(f"   Anterior: {old_val}")
print(f"   Nuevo: {schema['episode_time_steps']} ✅")

# Repair 2: PV peak_power
building = schema['buildings']['Mall_Iquitos']
pv_attrs = building['pv']['attributes']
old_val = pv_attrs.get('peak_power')
pv_attrs['peak_power'] = 4050.0
print(f"\n2. pv.attributes.peak_power:")
print(f"   Anterior: {old_val}")
print(f"   Nuevo: {pv_attrs['peak_power']} ✅")

# Repair 3: BESS power_output_nominal
bess_attrs = building['electrical_storage']['attributes']
old_val = bess_attrs.get('power_output_nominal')
bess_attrs['power_output_nominal'] = 1200.0
print(f"\n3. electrical_storage.attributes.power_output_nominal:")
print(f"   Anterior: {old_val}")
print(f"   Nuevo: {bess_attrs['power_output_nominal']} ✅")

# Nota: BESS capacity = 4520 se mantiene (es el valor OE2 dimensionado)
# En OE3 podría ser 2000, pero usaremos lo que está en el schema
print(f"\n4. electrical_storage.attributes.capacity:")
print(f"   Actual: {bess_attrs.get('capacity')} kWh (MANTENIDO - OE2 dimensionado)")

# Save
with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)

print(f"\n✅ Schema guardado: {schema_path}")

print("\n" + "="*70)
print("VALIDACIÓN POST-REPARACIÓN")
print("="*70)

with open(schema_path) as f:
    schema_test = json.load(f)

chargers = schema_test['buildings']['Mall_Iquitos'].get('chargers', {})
print(f"\n✓ episode_time_steps: {schema_test['episode_time_steps']}")
print(f"✓ central_agent: {schema_test['central_agent']}")
print(f"✓ seconds_per_time_step: {schema_test['seconds_per_time_step']}")
print(f"✓ pv.peak_power: {schema_test['buildings']['Mall_Iquitos']['pv']['attributes']['peak_power']}")
print(f"✓ bess.capacity: {schema_test['buildings']['Mall_Iquitos']['electrical_storage']['attributes']['capacity']}")
print(f"✓ bess.power_output_nominal: {schema_test['buildings']['Mall_Iquitos']['electrical_storage']['attributes']['power_output_nominal']}")
print(f"✓ chargers: {len(chargers)}")

print("\n✅ SCHEMA REPARADO EXITOSAMENTE")
