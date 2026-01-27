#!/usr/bin/env python3
"""
Lanzador de Entrenamiento A2C - Sin dependencias de .venv en shell
Ejecuta directamente desde Python el pipeline OE3 completo
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n[*] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"[ERROR] {description} fallo")
            return False
        print(f"[OK] {description}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    print("\n" + "="*60)
    print("   LANZADOR DE ENTRENAMIENTO A2C")
    print("="*60)

    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Verificar Python
    print(f"\n[1/3] Python version: {sys.version.split()[0]}")
    print(f"      Location: {sys.executable}")

    # Verificar paquetes
    print(f"\n[2/3] Verificando paquetes...")
    try:
        import torch
        import numpy
        import pandas
        import stable_baselines3
        import citylearn
        print("[OK] Todos los paquetes disponibles")
    except ImportError as e:
        print(f"[ERROR] Falta paquete: {e}")
        return 1

    # Lanzar entrenamiento
    print(f"\n[3/3] Lanzando pipeline OE3...")
    print("      Dataset → Baseline → SAC → PPO → A2C")
    print("")

    cmd = f'"{sys.executable}" -m scripts.run_oe3_simulate --config configs/default.yaml'

    try:
        result = subprocess.run(cmd, shell=True, cwd=project_root)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n[INFO] Entrenamiento interrumpido por usuario")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
