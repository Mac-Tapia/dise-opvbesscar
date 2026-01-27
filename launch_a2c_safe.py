#!/usr/bin/env python3
"""
Verificar Python 3.11 EXACTAMENTE y lanzar A2C si es correcto
"""

import sys

print("\n" + "="*80)
print("VERIFICAR PYTHON 3.11 EXACTAMENTE ANTES DE LANZAR A2C")
print("="*80)

print(f"\nVersión actual: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print(f"Requerida:      Python 3.11 EXACTAMENTE")

if sys.version_info[:2] != (3, 11):
    print("\n" + "!"*80)
    print("❌ ERROR: PYTHON 3.11 EXACTAMENTE REQUERIDO")
    print("!"*80)
    print(f"\nTienes: Python {sys.version_info.major}.{sys.version_info.minor}")
    print(f"NO se soportan: Python 3.10, 3.12, 3.13, etc")
    print("\nSOLUCION:")
    print("1. Descarga Python 3.11 desde https://www.python.org/downloads/")
    print("2. Desinstala Python 3.12, 3.13 si está instalado")
    print("3. Instala Python 3.11 EXACTAMENTE")
    print("4. O usa venv:")
    print("   python3.11 -m venv .venv")
    print("   .venv\\Scripts\\activate")
    print("\nMás info: Ve el archivo PYTHON_311_REQUIREMENTS.md")
    print("="*80 + "\n")
    sys.exit(1)

print("\n✓ Python 3.11 CORRECTO\n")

# Si llegamos aquí, Python 3.11 es correcto - ejecutar A2C
print("Iniciando A2C Training...")
print("="*80 + "\n")

import subprocess
result = subprocess.run(
    [sys.executable, "-m", "scripts.run_a2c_only", "--config", "configs/default.yaml"],
    cwd=__file__.replace("\\", "/").rsplit("/", 1)[0]
)
sys.exit(result.returncode)
