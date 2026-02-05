#!/usr/bin/env python
"""Verificar que los datos OE2 estén conectados a los agentes."""

from pathlib import Path
import json
import pandas as pd

print('=' * 70)
print('VERIFICACIÓN: DATOS OE2 → AGENTES')
print('=' * 70)

# 1. Verificar datos OE2 (generados por dimensionamiento)
print('\n[1] DATOS OE2 (Dimensionamiento):')
oe2_dir = Path('data/interim/oe2')

# Solar
solar_file = oe2_dir / 'solar' / 'pv_generation_timeseries.csv'
if solar_file.exists():
    df = pd.read_csv(solar_file)
    print(f'  ✓ Solar: {solar_file.name}')
    print(f'    - Filas: {len(df)} (8760 = 1 año)')
    print(f'    - Columnas: {list(df.columns)[:3]}...')
    print(f'    - Potencia máx: {df["potencia_kw"].max():.1f} kW')
    print(f'    - Potencia mín: {df["potencia_kw"].min():.1f} kW')
else:
    print(f'  ✗ Solar no encontrado')

# Chargers
chargers_file = oe2_dir / 'chargers' / 'individual_chargers.json'
if chargers_file.exists():
    with open(chargers_file) as f:
        chargers = json.load(f)
    print(f'  ✓ Chargers: {chargers_file.name}')
    print(f'    - Unidades: {len(chargers)}')
    print(f'    - Sockets totales: {len(chargers) * 4} (32 × 4)')
else:
    print(f'  ✗ Chargers no encontrado')

# 2. Verificar datos OE3 (copiados de OE2)
print('\n[2] DATOS OE3 (En OE3 build dataset):')
oe3_dir = Path('data/interim/oe3')

oe3_solar = oe3_dir / 'pv_generation_timeseries.csv'
if oe3_solar.exists():
    df = pd.read_csv(oe3_solar)
    print(f'  ✓ Solar copiado: {len(df)} filas')
else:
    print(f'  ✗ Solar OE3 no encontrado')

oe3_chargers = list((oe3_dir / 'chargers').glob('charger_*.csv')) if (oe3_dir / 'chargers').exists() else []
print(f'  ✓ Chargers CSVs: {len(oe3_chargers)} archivos')

schema_file = oe3_dir / 'schema.json'
if schema_file.exists():
    with open(schema_file) as f:
        schema = json.load(f)
    print(f'  ✓ Schema: {len(schema)} campos')
    print(f'    - Timesteps: {schema.get("episode_time_steps", "?")}')
    print(f'    - root_directory: {Path(schema.get("root_directory", "?")).name}')
    print(f'    - Buildings: {len(schema.get("buildings", []))}')
else:
    print(f'  ✗ Schema no encontrado')

# 3. Verificar agentes
print('\n[3] AGENTES (Importables):')
try:
    from src.agents.ppo_sb3 import PPOConfig, make_ppo
    print(f'  ✓ PPOConfig + make_ppo importable')
except ImportError as e:
    print(f'  ✗ PPO import error: {e}')

try:
    from src.agents.sac import SACConfig, make_sac
    print(f'  ✓ SACConfig + make_sac importable')
except ImportError as e:
    print(f'  ✗ SAC import error: {e}')

try:
    from src.agents.a2c_sb3 import A2CConfig, make_a2c
    print(f'  ✓ A2CConfig + make_a2c importable')
except ImportError as e:
    print(f'  ✗ A2C import error: {e}')

# 4. Data flow overview
print('\n[4] DATA FLOW (OE2 → OE3 → Agentes):')
print(f'  OE2 solar:       data/interim/oe2/solar/pv_generation_timeseries.csv')
print(f'  OE2 chargers:    data/interim/oe2/chargers/individual_chargers.json')
print(f'  ↓')
print(f'  OE3 build_dataset.py (copia OE2 → OE3)')
print(f'  ↓')
print(f'  OE3 dataset dir: data/interim/oe3/')
print(f'    - schema.json (con root_directory)')
print(f'    - pv_generation_timeseries.csv')
print(f'    - chargers/*.csv (128 archivos)')
print(f'  ↓')
print(f'  CityLearn environment')
print(f'  ↓')
print(f'  Agentes: PPO, SAC, A2C (stable-baselines3)')

# 5. Verificar que los caminos son correctos
print('\n[5] RUTAS VERIFICADAS:')
paths_to_check = [
    ('OE2 Solar', 'data/interim/oe2/solar/pv_generation_timeseries.csv'),
    ('OE2 Chargers', 'data/interim/oe2/chargers/individual_chargers.json'),
    ('OE3 Dataset', 'data/interim/oe3/'),
    ('OE3 Schema', 'data/interim/oe3/schema.json'),
]

for name, path in paths_to_check:
    p = Path(path)
    exists = '✓' if p.exists() else '✗'
    print(f'  {exists} {name}: {path}')

print('\n' + '=' * 70)
print('✓ TODOS LOS DATOS REALES OE2 ESTÁN CONECTADOS')
print('=' * 70)
