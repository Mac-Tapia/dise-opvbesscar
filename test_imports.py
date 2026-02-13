#!/usr/bin/env python
"""Test de importación de todos los módulos clave."""

import sys

modules_to_test = [
    "src.citylearnv2.progress.transition_manager",
    "src.citylearnv2.progress.metrics_extractor",
    "src.agents.sac",
    "src.agents.ppo_sb3",
    "src.agents.a2c_sb3",
    "src.agents.rbc",
    "src.agents.no_control",
    "src.utils.agent_utils",
    "src.utils.logging",
    "src.dimensionamiento.oe2.data_loader",
    "src.dimensionamiento.oe2.chargers",
    "src.rewards.rewards",
]

failed = []
passed = 0

for module_name in modules_to_test:
    try:
        __import__(module_name)
        passed += 1
        print(f"✅ {module_name}")
    except Exception as e:
        failed.append((module_name, str(e)[:50]))
        print(f"❌ {module_name}: {str(e)[:80]}")

print(f"\n📊 Resultados: {passed}/{len(modules_to_test)} módulos importados exitosamente")

if failed:
    print(f"\n❌ Fallos:")
    for mod, err in failed:
        print(f"  {mod}: {err}...")
    sys.exit(1)
else:
    print("\n✅ TODOS LOS MÓDULOS IMPORTARON CORRECTAMENTE")
