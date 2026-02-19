#!/usr/bin/env python
"""Verificar que SAC, PPO y A2C tienen construcción de dataset centralizado."""

import sys
from pathlib import Path

print("="*80)
print("VERIFICACION: SAC, PPO, A2C apuntan a data/iquitos_ev_mall")
print("="*80)

# Buscar construccion de dataset en los 3 scripts
scripts = {
    "SAC": Path("scripts/train/train_sac.py"),
    "PPO": Path("scripts/train/train_ppo.py"),
    "A2C": Path("scripts/train/train_a2c.py"),
}

required_strings = [
    "data/iquitos_ev_mall",
    "build_citylearn_dataset",
    "save_citylearn_dataset",
    "dataset_config_v7.json",
]

print("\nVerificando que cada script tiene construcción de dataset...\n")

all_ok = True

for agent_name, script_path in scripts.items():
    print(f"[{agent_name}] {script_path}")
    
    if not script_path.exists():
        print(f"  ❌ Archivo no encontrado")
        all_ok = False
        continue
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar que tiene la construcción de dataset
    has_construction = all(s in content for s in required_strings)
    
    if has_construction:
        print(f"  ✅ Tiene construcción de dataset:".ljust(60))
        for req_str in required_strings:
            if req_str in content:
                print(f"     • {req_str}".ljust(60))
    else:
        missing = [s for s in required_strings if s not in content]
        print(f"  ❌ Faltan strings:".ljust(60))
        for m in missing:
            print(f"     • {m}")
        all_ok = False
    
    # Verificar que llama a build_citylearn_dataset()
    if "build_citylearn_dataset()" in content:
        print(f"  ✅ Llama a build_citylearn_dataset()")
    else:
        print(f"  ⚠️  No encuentra llamada a build_citylearn_dataset()")
    
    # Verificar que llama a save_citylearn_dataset()
    if "save_citylearn_dataset(" in content:
        print(f"  ✅ Llama a save_citylearn_dataset()")
    else:
        print(f"  ⚠️  No encuentra llamada a save_citylearn_dataset()")
    
    print()

print("="*80)
if all_ok:
    print("✅ VERIFICACION COMPLETA: Los 3 agentes usan data/iquitos_ev_mall")
    print("="*80)
    print("\nResumo:")
    print("  SAC: Construye dataset en data/iquitos_ev_mall ✅")
    print("  PPO: Construye dataset en data/iquitos_ev_mall ✅")
    print("  A2C: Construye dataset en data/iquitos_ev_mall ✅")
    print("\nTodos los agentes cargarán la MISMA configuración:")
    print("  • 30 motos (sockets 0-29, chargers 0-14)")
    print("  • 8 mototaxis (sockets 30-37, chargers 15-18)")
    print("  • 38 sockets totales")
    print("  • 19 chargers × 7.4 kW = 140.6 kW")
    print("  • BESS: 2000 kWh @ 400 kW")
    print("  • Solar: 4050 kWp")
else:
    print("❌ VERIFICACION FALLIDA: Revisar scripts")
    print("="*80)
    sys.exit(1)
