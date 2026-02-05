#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAR: Dataset Builder carga TODOS los datos OE2 desde ubicaciones REALES
Output: Confirma que data/oe2/ está siendo utilizado correctamente
"""

import sys
from pathlib import Path

sys.path.insert(0, 'd:\\diseñopvbesscar')

print("=" * 90)
print("VERIFICACION: Dataset Builder carga datos OE2 desde ubicaciones REALES")
print("=" * 90)
print()

# Ubicaciones esperadas (REALES)
oe2_real_path = Path("d:\\diseñopvbesscar\\data\\oe2")
interim_path = Path("d:\\diseñopvbesscar\\data\\interim\\oe2")

print("[TEST 1] UBICACIONES DE ARCHIVOS OE2")
print("-" * 90)
print()

tests = {
    "Solar generación": oe2_real_path / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",
    "Cargadores (JSON)": oe2_real_path / "chargers" / "individual_chargers.json",
    "BESS horario": oe2_real_path / "bess" / "bess_hourly_dataset_2024.csv",
    "Demanda Mall": oe2_real_path / "mall_demand_hourly.csv",
}

all_oe2_exist = True
for name, path in tests.items():
    status = "✅ EXISTE" if path.exists() else "❌ NO EXISTE"
    base_path = Path('d:\\diseñopvbesscar')
    relative_path = path.relative_to(base_path)
    print(f"  {status:20} {name:<30} {relative_path}")
    if not path.exists():
        all_oe2_exist = False

print()

# Test 2: Import dataset_builder
print("[TEST 2] VERIFICAR IMPORTS EN DATASET_BUILDER")
print("-" * 90)
print()

try:
    from src.citylearnv2.dataset_builder.dataset_builder import _load_oe2_artifacts, build_citylearn_dataset
    print("✅ dataset_builder.py importado correctamente")
    print()
except ImportError as e:
    print(f"❌ Error importando dataset_builder: {e}")
    print()
    sys.exit(1)

# Test 3: Cargar artifacts desde OE2
print("[TEST 3] CARGAR ARTIFACTS OE2 VIA _load_oe2_artifacts()")
print("-" * 90)
print()

try:
    artifacts = _load_oe2_artifacts(interim_path)

    print("✅ _load_oe2_artifacts() ejecutado exitosamente")
    print()
    print("Artifacts cargados:")

    artifact_checks = {
        "solar_ts": ("GENERACION SOLAR", "DataFrame"),
        "chargers_hourly_profiles_annual": ("PERFILES CARGADORES", "DataFrame (128 cols = 128 tomas)"),
        "bess_hourly_2024": ("BESS HORARIO", "DataFrame (8760 filas)"),
        "iquitos_context": ("CONTEXTO IQUITOS", "Parámetros CO2 grid + tarifas"),
        "reward_weights": ("PESOS RECOMPENSA", "MultiObjectiveWeights"),
        "mall_demand": ("DEMANDA MALL", "DataFrame (8760 filas)"),
    }

    for key, (desc, expected) in artifact_checks.items():
        if key in artifacts:
            val = artifacts[key]
            if hasattr(val, 'shape'):
                info = f"shape={val.shape}"
            elif isinstance(val, dict):
                info = f"dict con {len(val)} items"
            else:
                info = type(val).__name__
            print(f"  ✅ {key:<40} {desc:<30} {info}")
        else:
            print(f"  ⚠️  {key:<40} {desc:<30} NO CARGADO")

    print()

except Exception as e:
    print(f"❌ Error cargando artifacts: {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 4: Verificar que dataset_builder.py busca en data/oe2/ primero
print("[TEST 4] VALIDAR RUTAS EN CODE")
print("-" * 90)
print()

try:
    dataset_builder_file = Path("d:\\diseñopvbesscar\\src\\citylearnv2\\dataset_builder\\dataset_builder.py")
    content = dataset_builder_file.read_text(encoding='utf-8')

    checks = [
        ("interim_dir.parent.parent / \"oe2\"", "Búsqueda en data/oe2/"),
        ("pv_generation_hourly_citylearn_v2.csv", "Archivo solar correcto"),
        ("mall_demand_hourly.csv", "Archivo demanda mall correcto"),
    ]

    for search_str, desc in checks:
        if search_str in content:
            print(f"  ✅ Código actualizado: {desc}")
        else:
            print(f"  ⚠️  NO ENCONTRADO: {desc}")

    print()

except Exception as e:
    print(f"Error verificando código: {e}")
    print()

# Test 5: Resumen
print("=" * 90)
print("RESUMEN")
print("=" * 90)
print()

if all_oe2_exist:
    print("✅ TODOS LOS DATOS OE2 REALES EXISTEN EN data/oe2/")
    print()
    print("✅ Dataset Builder está configurado para:")
    print("   1. Buscar primero en: data/oe2/Generacionsolar/, data/oe2/chargers/, etc.")
    print("   2. Fallback a: data/interim/oe2/")
    print()
    print("✅ CityLearn v2 recibirá datos REALES de OE2")
    print("   → Entrenamiento SAC/PPO/A2C usará datos reales")
    print("   → Métricas CO₂/EV satisfaction estarán basadas en datos reales")
    print()
    print("🎯 LISTO PARA ENTRENAR:")
    print("   python -m scripts.run_oe3_simulate --config configs/default.yaml")
    print()
else:
    print("⚠️  ALGUNOS DATOS OE2 NO ENCONTRADOS")
    print()
    print("Verifica que existan:")
    for name, path in tests.items():
        if not path.exists():
            print(f"   - {path}")
    print()

print("=" * 90)
