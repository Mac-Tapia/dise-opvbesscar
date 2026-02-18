#!/usr/bin/env python3
"""
Eliminar archivos no-usados del dataset_builder_citylearn
"""
from pathlib import Path

workspace = Path(__file__).parent.parent
builder_dir = workspace / "src" / "dataset_builder_citylearn"

# Archivos a eliminar
files_to_delete = [
    "analyze_datasets.py",
    "catalog_datasets.py",
    "complete_dataset_builder.py",
    "enrich_chargers.py",
    "integrate_datasets.py",
    "main_build_citylearn.py",
    "metadata_builder.py",
    "observations.py",
    "reward_normalizer.py",
    "scenario_builder.py"
]

# Archivos críticos que NO deben eliminarse
critical_files = [
    "__init__.py",
    "rewards.py",
    "data_loader.py"
]

print("=" * 80)
print("🗑️  ELIMINANDO ARCHIVOS NO-USADOS")
print("=" * 80)
print()

deleted_count = 0
for filename in files_to_delete:
    filepath = builder_dir / filename
    if filepath.exists():
        filepath.unlink()
        print(f"✓ Eliminado: {filename}")
        deleted_count += 1
    else:
        print(f"⚠️  No encontrado: {filename}")

print()
print(f"✅ TOTAL ELIMINADOS: {deleted_count}/10")
print()

# Verificar archivos críticos
print("Verificando archivos CRÍTICOS:")
all_critical_exist = True
for filename in critical_files:
    filepath = builder_dir / filename
    if filepath.exists():
        print(f"  ✓ {filename}")
    else:
        print(f"  ✗ FALTA: {filename}")
        all_critical_exist = False

print()
if all_critical_exist:
    print("✅ Todos los archivos críticos existen")
    print("   Estructura final: __init__.py, rewards.py, data_loader.py")
else:
    print("❌ Error: Faltan archivos críticos!")

# Listar archivos restantes
print()
print("Archivos actuales en dataset_builder_citylearn:")
for f in sorted(builder_dir.glob("*.py")):
    if f.name != "__pycache__":
        print(f"  • {f.name}")
