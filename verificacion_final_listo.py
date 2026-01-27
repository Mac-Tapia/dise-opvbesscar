#!/usr/bin/env python3
"""
PASO FINAL: Verificar todo está listo para A2C
Ejecuta DESPUÉS de activar Python 3.11 venv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

print("=" * 80)
print("VERIFICACION FINAL - SCHEMA + DATASETS + PYTHON 3.11")
print("=" * 80)
print()

# 1. Python 3.11
print("[1/3] Python 3.11...")
if sys.version_info[:2] != (3, 11):
    print(f"  BLOQUEADO: Python {sys.version_info[0]}.{sys.version_info[1]}")
    print("  ERROR: Necesitas Python 3.11 EXACTAMENTE")
    sys.exit(1)
else:
    print(f"  OK: Python 3.11 detectado")

# 2. Schema
print("\n[2/3] Schema + Datasets...")
try:
    with open("outputs/schema_building.json") as f:
        schema = json.load(f)

    import pandas as pd
    df_solar = pd.read_csv("data/interim/oe2/solar/pv_generation_timeseries.csv")

    with open("data/interim/oe2/chargers/individual_chargers.json") as f:
        chargers = json.load(f)

    with open("data/interim/oe2/bess/bess_config.json") as f:
        bess = json.load(f)

    # Verificar valores
    timesteps = schema.get("simulation_end_time_step", 0) + 1
    num_chargers = len(chargers)

    if timesteps == 8760 and num_chargers == 32 and len(df_solar) == 8760:
        print(f"  OK: Schema conectado correctamente")
        print(f"     - Timesteps: {timesteps} (8,760 = 1 año)")
        print(f"     - Chargers: {num_chargers} (32 = 128 sockets)")
        print(f"     - Solar: {len(df_solar)} filas (horarias)")
    else:
        print(f"  ERROR: Valores inesperados")
        sys.exit(1)
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# 3. Dependencias criticas
print("\n[3/3] Dependencias criticas...")
try:
    import citylearn
    import stable_baselines3
    print(f"  OK: CityLearn detectado")
    print(f"  OK: Stable-Baselines3 detectado")
except ImportError as e:
    print(f"  ERROR: Falta dependencia: {e}")
    sys.exit(1)

# EXITO
print()
print("=" * 80)
print("TODOS LOS SISTEMAS LISTOS")
print("=" * 80)
print()
print("Ejecuta A2C ahora:")
print("  python -m scripts.run_a2c_only --config configs/default.yaml")
print()

sys.exit(0)
