#!/usr/bin/env python3
"""
Verificación: Schema conectado con datasets OE2 y OE3
Verifica que toda la data local está lista para entrenamiento A2C
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Imports que se requieren en runtime dentro del venv
try:
    import pandas as pd  # type: ignore  # noqa
except ImportError:
    pd = None

print("=" * 80)
print("VERIFICACION: SCHEMA + DATASETS CONECTADOS")
print("=" * 80)
print()

errors = []
warnings = []
success_count = 0

# ==================== VERIFICACIONES ====================

# 1. Python 3.11
print("[1/7] Verificando Python 3.11...")
if sys.version_info[:2] != (3, 11):
    errors.append(f"Python {sys.version_info[0]}.{sys.version_info[1]} (requiere 3.11)")
    print(f"  X ERROR: Python {sys.version_info[0]}.{sys.version_info[1]} (requiere 3.11)")
else:
    print(f"  OK: Python 3.11 detectado")
    success_count += 1

# 2. Schema archivo
print("\n[2/7] Verificando schema archivo...")
schema_path = Path("outputs/schema_building.json")
if not schema_path.exists():
    errors.append(f"Schema no existe: {schema_path}")
    print(f"  ✗ {schema_path} NO EXISTE")
else:
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        # Extraer info
        buildings = schema.get("buildings", [])
        start_time = schema.get("simulation_start_time_step")
        end_time = schema.get("simulation_end_time_step")
        timesteps = (end_time - start_time + 1) if end_time is not None and start_time is not None else None

        print(f"  ✓ Schema cargado: {schema_path}")
        print(f"    - Edificios/Objetos: {len(buildings)}")
        print(f"    - Timesteps: {timesteps} (8,760 esperados = 1 año x 24 horas)")

        if timesteps != 8760:
            warnings.append(f"Timesteps inesperado: {timesteps} (esperado 8,760)")
            print(f"    ⚠ Advertencia: Timesteps no estándar")
        else:
            success_count += 1
    except Exception as e:
        errors.append(f"Error leyendo schema: {e}")
        print(f"  ✗ Error: {e}")

# 3. Datos OE2 - Solar
print("\n[3/7] Verificando solar timeseries OE2...")
solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
if not solar_path.exists():
    errors.append(f"Solar CSV no existe: {solar_path}")
    print(f"  ✗ {solar_path} NO EXISTE")
else:
    try:
        import pandas as pd  # type: ignore  # noqa
        df_solar = pd.read_csv(solar_path)

        print(f"  ✓ Solar timeseries cargada: {solar_path}")
        print(f"    - Filas: {len(df_solar)} (8,760 esperadas)")
        print(f"    - Columnas: {list(df_solar.columns)[:3]}...")

        if len(df_solar) != 8760:
            warnings.append(f"Solar CSV tiene {len(df_solar)} filas, esperadas 8,760")
            print(f"    ⚠ Advertencia: Longitud inesperada")
        else:
            success_count += 1
    except Exception as e:
        errors.append(f"Error leyendo solar CSV: {e}")
        print(f"  ✗ Error: {e}")

# 4. Datos OE2 - Chargers
print("\n[4/7] Verificando chargers OE2...")
chargers_path = Path("data/interim/oe2/chargers/individual_chargers.json")
if not chargers_path.exists():
    errors.append(f"Chargers JSON no existe: {chargers_path}")
    print(f"  ✗ {chargers_path} NO EXISTE")
else:
    try:
        with open(chargers_path) as f:
            chargers = json.load(f)

        num_chargers = len(chargers)
        num_sockets = num_chargers * 4  # 4 sockets por charger

        print(f"  ✓ Chargers config cargada: {chargers_path}")
        print(f"    - Chargers: {num_chargers} (32 esperados)")
        print(f"    - Sockets totales: {num_sockets} (128 esperados)")

        if num_chargers == 32 and num_sockets == 128:
            success_count += 1
        else:
            warnings.append(f"Chargers: {num_chargers} (esperado 32), Sockets: {num_sockets} (esperado 128)")
            print(f"    ⚠ Advertencia: Números inesperados")
    except Exception as e:
        errors.append(f"Error leyendo chargers JSON: {e}")
        print(f"  ✗ Error: {e}")

# 5. Datos OE2 - BESS
print("\n[5/7] Verificando BESS config OE2...")
bess_path = Path("data/interim/oe2/bess/bess_config.json")
if not bess_path.exists():
    errors.append(f"BESS config no existe: {bess_path}")
    print(f"  ✗ {bess_path} NO EXISTE")
else:
    try:
        with open(bess_path) as f:
            bess = json.load(f)

        capacity_kwh = bess.get("capacity_kwh", "N/A")
        power_kw = bess.get("power_kw", "N/A")

        print(f"  ✓ BESS config cargada: {bess_path}")
        print(f"    - Capacidad: {capacity_kwh} kWh")
        print(f"    - Potencia: {power_kw} kW")
        success_count += 1
    except Exception as e:
        errors.append(f"Error leyendo BESS config: {e}")
        print(f"  ✗ Error: {e}")

# 6. Perfil horario chargers
print("\n[6/7] Verificando perfil horario chargers...")
profile_path = Path("data/interim/oe2/chargers/perfil_horario_carga.csv")
if not profile_path.exists():
    errors.append(f"Perfil horario no existe: {profile_path}")
    print(f"  ✗ {profile_path} NO EXISTE")
else:
    try:
        if pd is not None:
            df_profile = pd.read_csv(profile_path)
        else:
            raise ImportError("pandas no disponible")

        print(f"  ✓ Perfil horario cargado: {profile_path}")
        print(f"    - Horas: {len(df_profile)} (24 esperadas)")

        if len(df_profile) == 24:
            success_count += 1
        else:
            warnings.append(f"Perfil horario: {len(df_profile)} horas (esperado 24)")
            print(f"    ⚠ Advertencia: Horas inesperadas")
    except Exception as e:
        errors.append(f"Error leyendo perfil horario: {e}")
        print(f"  ✗ Error: {e}")

# 7. Config default.yaml
print("\n[7/7] Verificando configuración default.yaml...")
config_path = Path("configs/default.yaml")
if not config_path.exists():
    errors.append(f"Config default.yaml no existe: {config_path}")
    print(f"  ✗ {config_path} NO EXISTE")
else:
    print(f"  ✓ Configuración cargada: {config_path}")
    success_count += 1

# ==================== RESUMEN ====================
print()
print("=" * 80)
print("RESUMEN")
print("=" * 80)

if errors:
    print(f"\n❌ ERRORES ENCONTRADOS: {len(errors)}")
    for i, err in enumerate(errors, 1):
        print(f"  {i}. {err}")

if warnings:
    print(f"\n⚠️  ADVERTENCIAS: {len(warnings)}")
    for i, warn in enumerate(warnings, 1):
        print(f"  {i}. {warn}")

print(f"\n✓ VERIFICACIONES EXITOSAS: {success_count}/7")

if not errors:
    print("\n" + "=" * 80)
    print("✓ SCHEMA Y DATASETS TOTALMENTE CONECTADOS Y LISTOS")
    print("=" * 80)
    print("\nProximo paso - Ejecuta A2C con:")
    print("  python -m scripts.run_a2c_only --config configs/default.yaml")
    sys.exit(0)
else:
    print("\n" + "=" * 80)
    print("❌ PROBLEMAS DETECTADOS - RESOLVER ANTES DE ENTRENAR")
    print("=" * 80)
    sys.exit(1)
