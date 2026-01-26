#!/usr/bin/env python
"""Monitor: Verificar que 128 chargers se generan correctamente en dataset builder"""
import json
from pathlib import Path
import subprocess
import sys

print("=" * 80)
print("PASO 1: Reinstalar paquete con código corregido")
print("=" * 80)
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
    cwd=Path.cwd()
)
if result.returncode == 0:
    print("✓ Paquete reinstalado")
else:
    print("✗ Error en reinstalación")
    sys.exit(1)

print("\n" + "=" * 80)
print("PASO 2: Limpiar dataset anterior")
print("=" * 80)
dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
if dataset_dir.exists():
    import shutil
    shutil.rmtree(dataset_dir)
    print(f"✓ Limpiado: {dataset_dir}")

print("\n" + "=" * 80)
print("PASO 3: Construir dataset desde OE2")
print("=" * 80)
import os
result = subprocess.run(
    [sys.executable, "-m", "scripts.run_oe3_build_dataset", "--config", "configs/default.yaml"],
    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
)

print("\n" + "=" * 80)
print("PASO 4: Verificar schema.json y archivos de chargers")
print("=" * 80)

schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
if schema_path.exists():
    with open(schema_path) as f:
        schema = json.load(f)

    buildings = schema.get("buildings", {})
    print(f"✓ Schema encontrado")
    print(f"  Buildings: {list(buildings.keys())}")

    mall_building = buildings.get("Mall_Iquitos", {})
    chargers = mall_building.get("chargers", {})
    print(f"  Chargers en Mall_Iquitos: {len(chargers)}")

    if len(chargers) > 0:
        charger_names = list(chargers.keys())
        print(f"  Primeros 3 chargers: {charger_names[:3]}")

        # Verificar que apuntan a archivos correctos
        first_charger = chargers[charger_names[0]]
        charger_file = first_charger.get("charger_simulation", "")
        print(f"  Archivo del primer charger: {charger_file}")

        # Contar archivos reales
        building_dir = Path("data/processed/citylearn/iquitos_ev_mall/buildings/Mall_Iquitos")
        charger_csvs = list(building_dir.glob("charger_simulation_*.csv"))
        print(f"  Archivos CSV reales generados: {len(charger_csvs)}")

        if len(charger_csvs) > 0:
            print(f"  Primeros 3 archivos: {[f.name for f in sorted(charger_csvs)[:3]]}")

            if len(charger_csvs) == 128:
                print("\n✅ ÉXITO: 128 chargers generados correctamente")
            else:
                print(f"\n⚠️ ADVERTENCIA: Solo {len(charger_csvs)} chargers generados (se esperaban 128)")
        else:
            print(f"\n✗ ERROR: No hay archivos charger_simulation_*.csv")
    else:
        print("  ✗ No hay chargers en el schema")
else:
    print("✗ Schema no encontrado")

print("=" * 80)
