#!/usr/bin/env python3
"""VER DATOS REALES QUE CARGA dataset_builder."""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path("src")))

print("\n" + "="*80)
print("📊 DATOS REALES QUE CARGA dataset_builder")
print("="*80 + "\n")

# 1. Mostrar archivos reales
print("[1] ARCHIVOS REALES OE2:")
print("-" * 80)

chargers_file = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")
solar_file = Path("data/oe2/solar/pv_generation_timeseries.csv")
bess_file = Path("data/oe2/bess/bess_config.json")

print(f"\n📁 CARGADORES:")
if chargers_file.exists():
    df_chargers = pd.read_csv(chargers_file)
    print(f"   ✅ Archivo: {chargers_file}")
    print(f"   📊 Filas: {len(df_chargers)}")
    print(f"   📋 Columnas: {len(df_chargers.columns)}")
    print(f"   📄 Tamaño: {chargers_file.stat().st_size / 1024:.1f} KB")
    print(f"\n   Columnas:")
    for col in df_chargers.columns:
        print(f"      • {col}")
    print(f"\n   Primeras filas:")
    print(df_chargers.head(3).to_string())
else:
    print(f"   ❌ NO ENCONTRADO: {chargers_file}")

print(f"\n📁 SOLAR:")
if solar_file.exists():
    df_solar = pd.read_csv(solar_file)
    print(f"   ✅ Archivo: {solar_file}")
    print(f"   📊 Filas: {len(df_solar)}")
    print(f"   📋 Columnas: {len(df_solar.columns)}")
    print(f"   📄 Tamaño: {solar_file.stat().st_size / 1024:.1f} KB")
    print(f"\n   Columnas:")
    for col in df_solar.columns:
        print(f"      • {col}")
    print(f"\n   Primeras filas:")
    print(df_solar.head(3).to_string())
else:
    print(f"   ⚠️  NO ENCONTRADO: {solar_file}")

print(f"\n📁 BESS (Batería):")
if bess_file.exists():
    import json
    with open(bess_file) as f:
        bess_config = json.load(f)
    print(f"   ✅ Archivo: {bess_file}")
    print(f"   📋 Configuración:")
    for key, val in bess_config.items():
        print(f"      • {key}: {val}")
else:
    print(f"   ⚠️  NO ENCONTRADO: {bess_file}")

# 2. Llamar dataset_builder
print("\n" + "="*80)
print("[2] CONSTRUYENDO DATASET CON ESTOS DATOS REALES...")
print("="*80 + "\n")

try:
    from citylearnv2.dataset_builder.dataset_builder import (
        _load_oe2_artifacts,
        build_citylearn_dataset
    )
    
    # Cargar artefactos OE2
    print("Cargando artefactos OE2...")
    artifacts = _load_oe2_artifacts(Path("data/interim"))
    
    print(f"\n✅ Artefactos cargados:")
    for key, val in artifacts.items():
        if hasattr(val, 'shape'):
            print(f"   • {key:30s} shape={val.shape}")
        elif isinstance(val, dict):
            print(f"   • {key:30s} {len(val)} items")
        elif isinstance(val, list):
            print(f"   • {key:30s} {len(val)} items")
        else:
            print(f"   • {key:30s} {type(val).__name__}")
    
    # Construir dataset
    print("\nConstruyendo dataset CityLearn v2...")
    dataset = build_citylearn_dataset()
    
    print(f"\n✅ Dataset construido:")
    for key in sorted(dataset.keys()):
        val = dataset[key]
        if hasattr(val, 'shape'):
            print(f"   • {key:40s} shape={val.shape}")
        elif isinstance(val, dict):
            print(f"   • {key:40s} {len(val)} items")
        elif isinstance(val, list):
            print(f"   • {key:40s} {len(val)} items")
        else:
            print(f"   • {key:40s} {type(val).__name__}")
    
    print("\n" + "="*80)
    print("✅ CONSTRUCCIÓN CON DATOS REALES COMPLETADA")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
