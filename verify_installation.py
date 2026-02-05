#!/usr/bin/env python3
"""
Script de verificación de instalación de dependencias
Python 3.11 - diseñopvbesscar Project
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

print("\n" + "="*80)
print("VERIFICACIÓN DE INSTALACIÓN - PYTHON 3.11")
print("diseñopvbesscar Project")
print("="*80 + "\n")

# Lista de paquetes a verificar
packages_core = [
    ("numpy", "NumPy"),
    ("pandas", "Pandas"),
    ("scipy", "SciPy"),
]

packages_rl = [
    ("gymnasium", "Gymnasium"),
]

packages_ml = [
    ("torch", "PyTorch"),
    ("torchvision", "TorchVision"),
]

packages_sb3 = [
    ("stable_baselines3", "Stable Baselines 3"),
]

packages_utils = [
    ("yaml", "PyYAML"),
    ("pydantic", "Pydantic"),
    ("dotenv", "python-dotenv"),
]

packages_viz = [
    ("matplotlib", "Matplotlib"),
    ("seaborn", "Seaborn"),
    ("PIL", "Pillow"),
]

packages_energy = [
    ("pvlib", "pvlib"),
]

packages_testing = [
    ("pytest", "pytest"),
]

def check_package(module_name, display_name):
    """Verifica si un paquete está instalado"""
    try:
        __import__(module_name)
        return True, None
    except ImportError as e:
        return False, str(e)

def print_section(title):
    """Imprime un encabezado de sección"""
    print(f"\n{title}")
    print("-" * 80 + "\n")

def verify_packages(packages, section_name):
    """Verifica una lista de paquetes"""
    print_section(section_name)

    failed = 0
    for module, display_name in packages:
        success, error = check_package(module, display_name)
        if success:
            print(f"✓ {display_name:40} - INSTALADO")
        else:
            print(f"✗ {display_name:40} - NO ENCONTRADO")
            failed += 1

    return failed

# Ejecutar verificaciones
total_failed = 0

total_failed += verify_packages(packages_core, "CORE DATA PROCESSING")
total_failed += verify_packages(packages_rl, "REINFORCEMENT LEARNING")
total_failed += verify_packages(packages_ml, "DEEP LEARNING")
total_failed += verify_packages(packages_sb3, "STABLE BASELINES 3 (RL Framework)")
total_failed += verify_packages(packages_utils, "UTILITIES & CONFIG")
total_failed += verify_packages(packages_viz, "VISUALIZATION & ANALYSIS")
total_failed += verify_packages(packages_energy, "SOLAR & ENERGY")
total_failed += verify_packages(packages_testing, "TESTING")

# Resumen final
print("\n" + "="*80)
print("RESUMEN DE VERIFICACIÓN")
print("="*80 + "\n")

if total_failed == 0:
    print("✅ TODAS LAS DEPENDENCIAS INSTALADAS CORRECTAMENTE\n")
    print("El entorno está listo para:")
    print("  • Entrenamiento de agentes RL (SAC, PPO, A2C)")
    print("  • Simulación de CityLearn v2.5.0")
    print("  • Análisis de datos con pandas/numpy")
    print("  • Visualización con matplotlib")
    print("\n")

    # Información adicional
    try:
        import torch
        print(f"✓ PyTorch CUDA disponible: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  Memoria CUDA: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    except Exception as e:
        print(f"⚠️  Error verificando CUDA: {e}")

    print("\n")
else:
    print(f"⚠️  ADVERTENCIA: {total_failed} paquete(s) no encontrado(s)\n")
    print("Por favor ejecuta nuevamente:")
    print("  .\\install_requirements.bat")
    print("\n")

# Guardar log
log_file = Path("installation_verification.txt")
with open(log_file, "w") as f:
    f.write(f"Verificación de Instalación - {datetime.now().isoformat()}\n")
    f.write(f"Python Version: {sys.version}\n")
    f.write(f"Paquetes fallidos: {total_failed}\n\n")

    # Ejecutar pip list
    result = subprocess.run(["pip", "list"], capture_output=True, text=True)
    f.write("Paquetes instalados:\n")
    f.write(result.stdout)

print(f"Log de verificación guardado en: {log_file}")
print("\n" + "="*80 + "\n")
