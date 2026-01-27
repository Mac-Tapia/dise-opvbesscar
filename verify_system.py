#!/usr/bin/env python3
"""
VERIFICAR SISTEMA - Python 3.11 y Dependencias
================================================

Ejecutar ANTES de entrenar para asegurar:
- Python 3.11
- Virtual environment activo
- Todas dependencias instaladas
- Datos locales presentes
"""

import sys
from pathlib import Path

print("\n" + "="*80)
print("VERIFICACION DE SISTEMA - PYTHON 3.11")
print("="*80)

# 1. Python 3.11
print("\n[1/4] Verificando Python 3.11...")
print(f"      Versión: {sys.version_info.major}.{sys.version_info.minor}")

if sys.version_info[:2] != (3, 11):
    print("\n" + "!"*80)
    print("ERROR: Python 3.11 requerido")
    print("!"*80)
    print(f"Tienes Python {sys.version_info.major}.{sys.version_info.minor}")
    print("\nSolución:")
    print("  1. Descarga Python 3.11 desde https://www.python.org/downloads/")
    print("  2. Crea venv: python3.11 -m venv .venv")
    print("  3. Activa: .venv\\Scripts\\activate")
    print("  4. Instala: pip install -r requirements-training.txt")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      > OK - Python 3.11 detectado")

# 2. Virtual Environment
print("\n[2/4] Verificando virtual environment...")
in_venv = sys.prefix != sys.base_prefix
print(f"      En venv: {'SI' if in_venv else 'NO'}")

if not in_venv:
    print("\n" + "!"*80)
    print("ADVERTENCIA: No estás en virtual environment")
    print("!"*80)
    print("\nSolución:")
    print("  .venv\\Scripts\\activate  (Windows)")
    print("  source .venv/bin/activate  (Linux/Mac)")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      > OK - venv activo")

# 3. Paquetes
print("\n[3/4] Verificando paquetes...")

packages = [
    'numpy',
    'pandas',
    'gymnasium',
    'stable_baselines3',
    'torch',
]

missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f"      > {pkg}")
    except ImportError:
        print(f"      X {pkg} (FALTANTE)")
        missing.append(pkg)

if missing:
    print("\n" + "!"*80)
    print(f"FALTANTES: {', '.join(missing)}")
    print("!"*80)
    print("\nInstala con:")
    print("  pip install -r requirements-training.txt")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      > OK - todos los paquetes presentes")

# 4. Datos
print("\n[4/4] Verificando datos locales...")

data_files = [
    'data/processed/citylearn/iquitos_ev_mall/weather.csv',
    'data/processed/citylearn/iquitos_ev_mall/Building_1.csv',
    'data/processed/citylearn/iquitos_ev_mall/charger_simulation_001.csv',
]

missing_data = []
for f in data_files:
    if Path(f).exists():
        print(f"      > {f}")
    else:
        print(f"      X {f} (FALTANTE)")
        missing_data.append(f)

if missing_data:
    print("\n" + "!"*80)
    print("DATOS FALTANTES")
    print("!"*80)
    print("\nEjecuta primero:")
    print("  python scripts/run_oe3_build_dataset.py --config configs/default.yaml")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      > OK - datos presentes")

# OK
print("\n" + "="*80)
print("VERIFICACION COMPLETADA - LISTO PARA ENTRENAR")
print("="*80)
print("\nEjecuta ahora:")
print("  python train_a2c_local_data_only.py")
print("="*80 + "\n")
