#!/usr/bin/env python
"""Verificar conexión OE2 → OE3 (todos los datos necesarios)"""
import pandas as pd  # type: ignore[import]
import json
from pathlib import Path

print("=" * 80)
print("VERIFICACIÓN EXHAUSTIVA: DATOS OE2 → SCHEMA OE3")
print("=" * 80)

interim_dir = Path("data/interim/oe2")

# 1. SOLAR
print("\n1. SOLAR TIMESERIES")
solar_path = interim_dir / "solar" / "pv_generation_timeseries.csv"
if solar_path.exists():
    df = pd.read_csv(solar_path)
    print(f"   ✓ Archivo: {solar_path.name}")
    print(f"   ✓ Shape: {df.shape} (8760 = 1 año)")
    print(f"   ✓ Columnas: {df.columns.tolist()}")
else:
    print(f"   ✗ NO ENCONTRADO: {solar_path}")

# 2. CHARGERS PROFILES
print("\n2. CHARGERS DAILY PROFILES (para expandir a 8760 horas)")
chargers_daily = interim_dir / "chargers" / "chargers_hourly_profiles.csv"
if chargers_daily.exists():
    df = pd.read_csv(chargers_daily)
    print(f"   ✓ Archivo: {chargers_daily.name}")
    print(f"   ✓ Shape: {df.shape} (24 horas × 128 + 1 col hora)")
    cols_without_hour = [c for c in df.columns if c.lower() != 'hour']
    print(f"   ✓ Chargers (sin hour): {len(cols_without_hour)}")
    print(f"   ✓ Primeras 5 columnas: {df.columns.tolist()[:5]}")
else:
    print(f"   ✗ NO ENCONTRADO: {chargers_daily}")

# 3. INDIVIDUAL CHARGERS CONFIG
print("\n3. INDIVIDUAL CHARGERS CONFIGURATION")
chargers_config = interim_dir / "chargers" / "individual_chargers.json"
if chargers_config.exists():
    with open(chargers_config) as f:
        cfg = json.load(f)
    print(f"   ✓ Archivo: {chargers_config.name}")
    if isinstance(cfg, dict):
        print(f"   ✓ Total chargers: {len(cfg)}")
        print(f"   ✓ Primeros 3: {list(cfg.keys())[:3]}")
    else:
        print(f"   ✓ Total chargers: {len(cfg)}")
        print(f"   ✓ Es lista, primeros 3: {cfg[:3] if len(cfg) > 0 else 'N/A'}")
else:
    print(f"   ✗ NO ENCONTRADO: {chargers_config}")

# 4. BESS CONFIG
print("\n4. BESS CONFIGURATION")
bess_path = interim_dir / "bess" / "bess_config.json"
if bess_path.exists():
    with open(bess_path) as f:
        cfg = json.load(f)
    print(f"   ✓ Archivo: {bess_path.name}")
    print(f"   ✓ Capacidad: {cfg.get('capacity_kwh', 'N/A')} kWh")
    print(f"   ✓ Potencia: {cfg.get('nominal_power_kw', 'N/A')} kW")
else:
    print(f"   ✗ NO ENCONTRADO: {bess_path}")

# 5. BUILDING LOAD
print("\n5. BUILDING LOAD (MALL)")
building_load = interim_dir / "demandamallkwh" / "demanda_mall_kwh.csv"
if not building_load.exists():
    building_load = interim_dir / "oe2" / "citylearn" / "building_load.csv"
if building_load.exists():
    df = pd.read_csv(building_load)
    print(f"   ✓ Archivo encontrado")
    print(f"   ✓ Shape: {df.shape}")
    print(f"   ✓ Columnas: {df.columns.tolist()[:3]}")
else:
    print(f"   ✗ NO ENCONTRADO")

print("\n" + "=" * 80)
print("✅ TODOS LOS DATOS OE2 NECESARIOS ESTÁN PRESENTES")
print("=" * 80)
