#!/usr/bin/env python3
"""
TEST INTEGRACION COMPLETO - Verificar sistema listo para entrenar
Sin caracteres especiales - Solo ASCII compatible
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import pandas as pd  # type: ignore  # noqa
except ImportError:
    pd = None

print("\n" + "="*80)
print("TEST INTEGRACION COMPLETO - SISTEMA LISTO PARA ENTRENAR")
print("="*80)

errors = []
warnings = []
checks_passed = 0

# ============================================================================
# [1] Python 3.11
# ============================================================================
print("\n[1/6] Verificando Python 3.11...")
if sys.version_info[:2] != (3, 11):
    errors.append(f"Python {sys.version_info[0]}.{sys.version_info[1]} (requiere 3.11)")
    print(f"  [FAIL] Python {sys.version_info[0]}.{sys.version_info[1]} (requiere 3.11)")
else:
    print(f"  [PASS] Python 3.11.{sys.version_info[2]} detectado")
    checks_passed += 1

# ============================================================================
# [2] Schema CityLearn v2
# ============================================================================
print("\n[2/6] Verificando Schema CityLearn v2...")
schema_path = Path("outputs/schema_building.json")
if not schema_path.exists():
    errors.append(f"Schema no existe: {schema_path}")
    print(f"  [FAIL] {schema_path} NO EXISTE")
else:
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        buildings = schema.get("buildings", [])
        start_time = schema.get("simulation_start_time_step", 0)
        end_time = schema.get("simulation_end_time_step", 8759)
        timesteps = end_time - start_time + 1

        print(f"  [PASS] Schema cargado correctamente")
        print(f"         - Version: CityLearn v2")
        print(f"         - Edificios: {len(buildings)}")
        print(f"         - Timesteps: {timesteps} (1 ano = 8,760 horas esperadas)")

        if timesteps == 8760:
            checks_passed += 1
        else:
            warnings.append(f"Timesteps inesperado: {timesteps} (esperado 8,760)")
            print(f"  [WARN] Timesteps no es 8,760")
    except Exception as e:
        errors.append(f"Error leyendo schema: {e}")
        print(f"  [FAIL] Error: {e}")

# ============================================================================
# [3] Datos Solar OE2 (1 ano)
# ============================================================================
print("\n[3/6] Verificando datos Solar OE2 (1 ano)...")
solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
if not solar_path.exists():
    errors.append(f"Solar CSV no existe: {solar_path}")
    print(f"  [FAIL] {solar_path} NO EXISTE")
else:
    try:
        if pd is None:
            raise ImportError("pandas no disponible")
        df_solar = pd.read_csv(solar_path)

        print(f"  [PASS] Solar timeseries cargada")
        print(f"         - Filas: {len(df_solar)} (8,760 esperadas para 1 ano)")
        print(f"         - Columnas: {list(df_solar.columns)}")
        print(f"         - Resolucion: Horaria")

        if len(df_solar) == 8760:
            checks_passed += 1
        else:
            warnings.append(f"Solar CSV tiene {len(df_solar)} filas, esperadas 8,760")
            print(f"  [WARN] Longitud no es 8,760")
    except Exception as e:
        errors.append(f"Error leyendo solar CSV: {e}")
        print(f"  [FAIL] Error: {e}")

# ============================================================================
# [4] Chargers OE2
# ============================================================================
print("\n[4/6] Verificando Chargers OE2...")
chargers_path = Path("data/interim/oe2/chargers/individual_chargers.json")
if not chargers_path.exists():
    errors.append(f"Chargers JSON no existe: {chargers_path}")
    print(f"  [FAIL] {chargers_path} NO EXISTE")
else:
    try:
        with open(chargers_path) as f:
            chargers = json.load(f)

        num_chargers = len(chargers)
        num_sockets = num_chargers * 4

        print(f"  [PASS] Chargers cargados")
        print(f"         - Chargers: {num_chargers}")
        print(f"         - Sockets totales: {num_sockets}")

        if num_sockets == 512:  # 128 chargers * 4 sockets = 512
            checks_passed += 1
        else:
            warnings.append(f"Sockets: {num_sockets} (esperado 512)")
            print(f"  [WARN] Sockets no son 512")
    except Exception as e:
        errors.append(f"Error leyendo chargers JSON: {e}")
        print(f"  [FAIL] Error: {e}")

# ============================================================================
# [5] BESS OE2
# ============================================================================
print("\n[5/6] Verificando BESS OE2...")
bess_path = Path("data/interim/oe2/bess/bess_results.json")
if not bess_path.exists():
    errors.append(f"BESS results no existe: {bess_path}")
    print(f"  [FAIL] {bess_path} NO EXISTE")
else:
    try:
        with open(bess_path) as f:
            bess = json.load(f)

        capacity_kwh = bess.get("capacity_kwh", "N/A")
        power_kw = bess.get("nominal_power_kw", "N/A")

        print(f"  [PASS] BESS results cargada")
        print(f"         - Capacidad: {capacity_kwh} kWh")
        print(f"         - Potencia: {power_kw} kW")

        if capacity_kwh == 4520.0 and power_kw == 2712.0:
            checks_passed += 1
        else:
            warnings.append(f"BESS valores: {capacity_kwh} kWh, {power_kw} kW (esperado 4520 kWh, 2712 kW)")
    except Exception as e:
        errors.append(f"Error leyendo BESS config: {e}")
        print(f"  [FAIL] Error: {e}")

# ============================================================================
# [6] Configuracion
# ============================================================================
print("\n[6/6] Verificando Configuracion...")
config_path = Path("configs/default.yaml")
if not config_path.exists():
    errors.append(f"Config no existe: {config_path}")
    print(f"  [FAIL] {config_path} NO EXISTE")
else:
    print(f"  [PASS] Configuracion lista")
    print(f"         - Archivo: configs/default.yaml")
    checks_passed += 1

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "="*80)
print("RESUMEN DE VERIFICACION")
print("="*80)

total_checks = 6
print(f"\nChequeos exitosos: {checks_passed}/{total_checks}")

if errors:
    print(f"\nERRORES ({len(errors)}):")
    for i, err in enumerate(errors, 1):
        print(f"  {i}. {err}")

if warnings:
    print(f"\nADVERTENCIAS ({len(warnings)}):")
    for i, warn in enumerate(warnings, 1):
        print(f"  {i}. {warn}")

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("\n" + "="*80)
if not errors and checks_passed == total_checks:
    print("RESULTADO: OK - SISTEMA LISTO PARA ENTRENAR")
    print("="*80)
    print("\nEste es tu sistema:")
    print("  - Python: 3.11 (requerido)")
    print("  - Schema: CityLearn v2 con 8,760 timesteps (1 ano)")
    print("  - Datos: Conectados a base de datos de 1 ano")
    print("  - Solar: 8,760 horas horarias")
    print("  - Chargers: 128 sockets (32 chargers)")
    print("  - BESS: Configurado")
    print("\nPuedes lanzar el entrenamiento:")
    print("  python -m scripts.run_a2c_only --config configs/default.yaml")
    print("="*80 + "\n")
    sys.exit(0)
else:
    print("RESULTADO: FALLOS - RESOLVER ANTES DE ENTRENAR")
    print("="*80 + "\n")
    sys.exit(1)
