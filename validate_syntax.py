#!/usr/bin/env python3
"""
Verifica que los archivos principales compilen sin errores de sintaxis
"""
from pathlib import Path
import py_compile
import sys

files_to_check = [
    "src/iquitos_citylearn/oe2/bess.py",
    "src/iquitos_citylearn/oe2/solar_pvlib.py",
    "src/iquitos_citylearn/oe3/simulate.py",
    "src/iquitos_citylearn/oe3/agents/sac.py",
    "src/iquitos_citylearn/oe3/agents/a2c_sb3.py",
    "src/iquitos_citylearn/oe3/agents/ppo_sb3.py",
    "scripts/train_agents_real.py",
]

root = Path(__file__).parent
errors = []

print("=" * 70)
print("VALIDACION DE SINTAXIS - ARCHIVOS PRINCIPALES")
print("=" * 70)

for file_path in files_to_check:
    full_path = root / file_path
    try:
        py_compile.compile(str(full_path), doraise=True)
        print(f"✅ {file_path}")
    except py_compile.PyCompileError as e:
        print(f"❌ {file_path}")
        print(f"   Error: {e}")
        errors.append((file_path, str(e)))

print("\n" + "=" * 70)
if errors:
    print(f"❌ {len(errors)} archivos con errores")
    for file_path, error in errors:
        print(f"  - {file_path}")
    sys.exit(1)
else:
    print(f"✅ TODOS LOS {len(files_to_check)} ARCHIVOS VALIDOS")
    print("\n Pipeline listo para ejecutarse!")
    sys.exit(0)
