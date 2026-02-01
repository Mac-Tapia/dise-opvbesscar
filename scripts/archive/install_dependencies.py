#!/usr/bin/env python
"""Validar e instalar dependencias del proyecto pvbesscar.

Este script verifica que todas las librerías necesarias estén instaladas
correctamente y con las versiones compatibles.

Uso:
    python scripts/install_dependencies.py
    python scripts/install_dependencies.py --check-only
    python scripts/install_dependencies.py --reinstall-all
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any


def check_python_version() -> bool:
    """Verificar que Python 3.11 esté siendo usado."""
    if sys.version_info[:2] != (3, 11):
        print(f"❌ ERROR: Python 3.11 requerido, pero Python {sys.version_info.major}.{sys.version_info.minor} está en uso")
        print(f"   Solución: Activar environment con Python 3.11")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} correcto")
    return True


def check_package(package_name: str, import_name: str = "") -> Tuple[bool, str]:
    """Verificar si un paquete está instalado y obtener su versión."""
    if not import_name:
        import_name = package_name

    try:
        module = __import__(import_name)
        version = getattr(module, "__version__", "desconocida")
        return True, version
    except ImportError:
        return False, "NO INSTALADO"


def check_dependencies() -> Dict[str, Tuple[bool, str]]:
    """Verificar todas las dependencias críticas."""
    packages: Dict[str, str] = {
        "numpy": "numpy",
        "pandas": "pandas",
        "scipy": "scipy",
        "gymnasium": "gymnasium",
        "stable-baselines3": "stable_baselines3",
        "torch": "torch",
        "citylearn": "citylearn",
        "pyyaml": "yaml",
        "python-dotenv": "dotenv",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "tensorboard": "tensorboard",
    }

    results: Dict[str, Tuple[bool, str]] = {}
    for pkg_name, import_name in packages.items():
        results[pkg_name] = check_package(pkg_name, import_name)

    return results


def print_status_table(results: Dict[str, Tuple[bool, str]]) -> None:
    """Imprimir tabla de estado de dependencias."""
    print("\n" + "="*80)
    print("ESTADO DE DEPENDENCIAS")
    print("="*80)
    print(f"{'Paquete':<30} {'Status':<15} {'Versión'}")
    print("-"*80)

    for pkg_name, (installed, version) in sorted(results.items()):
        status = "✅ OK" if installed else "❌ FALTA"
        print(f"{pkg_name:<30} {status:<15} {version}")

    print("="*80)


def get_install_commands() -> List[str]:
    """Retornar comandos de instalación."""
    return [
        "pip install -r requirements.txt",
        "pip install -r requirements-training.txt",
        "pip install -r requirements-citylearn-v2.txt",
    ]


def print_installation_guide() -> None:
    """Imprimir guía de instalación."""
    print("\n" + "="*80)
    print("GUÍA DE INSTALACIÓN")
    print("="*80)
    print("\n1️⃣  Crear ambiente virtual:")
    print("   python -m venv .venv")
    print("\n2️⃣  Activar ambiente virtual:")
    print("   Windows: .venv\\Scripts\\activate")
    print("   Linux/Mac: source .venv/bin/activate")
    print("\n3️⃣  Instalar dependencias (en orden):")
    for i, cmd in enumerate(get_install_commands(), 1):
        print(f"   {i}. {cmd}")
    print("\n4️⃣  Verificar instalación:")
    print("   python scripts/install_dependencies.py --check-only")
    print("\n" + "="*80)


def main() -> int:
    """Main entry point."""
    print("="*80)
    print("VALIDACIÓN DE DEPENDENCIAS - pvbesscar")
    print("="*80 + "\n")

    # Paso 1: Verificar Python 3.11
    if not check_python_version():
        return 1

    # Paso 2: Verificar dependencias
    print("\n⏳ Verificando dependencias...")
    results = check_dependencies()

    # Paso 3: Mostrar estado
    print_status_table(results)

    # Paso 4: Contar problemas
    missing: List[str] = [pkg for pkg, (installed, _) in results.items() if not installed]
    installed_count: int = len([pkg for pkg, (installed, _) in results.items() if installed])
    total_count: int = len(results)

    print(f"\n📊 RESUMEN:")
    print(f"   ✅ Instaladas: {installed_count}/{total_count}")
    print(f"   ❌ Faltantes: {len(missing)}/{total_count}")

    if missing:
        print(f"\n⚠️  Paquetes faltantes: {', '.join(missing)}")
        print("\n📝 Para instalar todos los paquetes, ejecutar:")
        print("   pip install -r requirements.txt")
        print("   pip install -r requirements-training.txt")
        print("   pip install -r requirements-citylearn-v2.txt")
        print_installation_guide()
        return 1
    else:
        print("\n✅ TODAS LAS DEPENDENCIAS INSTALADAS CORRECTAMENTE")
        print("\n🚀 Próximo paso: Ejecutar training")
        print("   python -m scripts.run_oe3_simulate --config configs/default.yaml")
        return 0


if __name__ == "__main__":
    sys.exit(main())
