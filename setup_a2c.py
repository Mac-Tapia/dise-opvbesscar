#!/usr/bin/env python3
"""
SETUP - VERIFICAR E INSTALAR EN PYTHON 3.11 EXACTAMENTE
========================================================

Este script asegura que:
1. Python 3.11 EXACTAMENTE está siendo usado
2. NO se use Python 3.12, 3.13, etc
3. Virtual environment está activado
4. Dependencias correctas instaladas
5. Todo listo para entrenar A2C

⚠️  REQUERIMIENTO: Python 3.11 EXACTAMENTE
"""

import sys
import subprocess
from pathlib import Path

print("\n" + "="*80)
print("🔧 SETUP A2C - VERIFICAR PYTHON 3.11 EXACTAMENTE")
print("="*80)

# ========== VALIDAR PYTHON 3.11 EXACTAMENTE ==========
print(f"\n[1/4] Verificando versión de Python...")
print(f"      Versión actual: {sys.version_info.major}.{sys.version_info.minor}")
print(f"      Requerida: 3.11 EXACTAMENTE (no 3.12, no 3.13)")

if sys.version_info[:2] != (3, 11):
    print(f"\n❌ ERROR: Se requiere EXACTAMENTE Python 3.11")
    print(f"   Tienes: Python {sys.version_info.major}.{sys.version_info.minor}")
    print(f"\n❌ NO se soportan: Python 3.12, 3.13, etc")
    print("\nPara usar Python 3.11 EXACTAMENTE:")
    print("  1. Descarga Python 3.11 EXACTAMENTE desde python.org")
    print("  2. Desinstala Python 3.12, 3.13, etc")
    print("  3. Crea venv con Python 3.11:")
    print("     python3.11 -m venv .venv")
    print("     .venv\\Scripts\\activate  (Windows)")
    print("     pip install -r requirements-training.txt")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      ✓ Python 3.11 detectado")

# ========== VERIFICAR VIRTUAL ENVIRONMENT ==========
print(f"\n[2/4] Verificando virtual environment...")
in_venv = sys.prefix != sys.base_prefix
print(f"      En venv: {'SÍ' if in_venv else 'NO'}")

if not in_venv:
    print("\n⚠️  No estás en un virtual environment")
    print("   Ejecuta primero:")
    print("   .venv\\Scripts\\activate  (Windows)")
    print("   source .venv/bin/activate  (Linux/Mac)")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

print("      ✓ Virtual environment activo")

# ========== VERIFICAR PAQUETES ==========
print(f"\n[3/4] Verificando paquetes requeridos...")

required_packages = {
    'gymnasium': 'gymnasium',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'stable_baselines3': 'stable_baselines3',
    'torch': 'torch',
}

missing = []
for name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"      ✓ {name}")
    except ImportError:
        print(f"      ✗ {name} (faltante)")
        missing.append(name)

if missing:
    print(f"\n❌ Paquetes faltantes: {', '.join(missing)}")
    print("\nInstala con:")
    print("   pip install -r requirements-training.txt")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

# ========== VERIFICAR DATOS ==========
print(f"\n[4/4] Verificando datos locales...")

data_files = [
    'data/processed/citylearn/iquitos_ev_mall/weather.csv',
    'data/processed/citylearn/iquitos_ev_mall/Building_1.csv',
    'data/processed/citylearn/iquitos_ev_mall/charger_simulation_001.csv',
]

missing_data = []
for filepath in data_files:
    if Path(filepath).exists():
        print(f"      ✓ {filepath}")
    else:
        print(f"      ✗ {filepath} (faltante)")
        missing_data.append(filepath)

if missing_data:
    print(f"\n❌ Datos faltantes. Ejecuta primero:")
    print("   python scripts/run_oe3_build_dataset.py --config configs/default.yaml")
    print("\n" + "="*80 + "\n")
    sys.exit(1)

# ========== TODO OK ==========
print("\n" + "="*80)
print("✅ SETUP COMPLETADO - LISTO PARA ENTRENAR")
print("="*80)
print("\nEjecuta ahora:")
print("   python train_a2c_local_data_only.py")
print("="*80 + "\n")
