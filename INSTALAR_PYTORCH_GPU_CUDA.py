#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
INSTALAR_PYTORCH_GPU_CUDA.py
=============================

Instala PyTorch con soporte CUDA 12.1 para NVIDIA RTX 4060 Laptop

Pasos:
  1. Actualizar pip
  2. Desinstalar PyTorch CPU-only
  3. Instalar PyTorch + CUDA 12.1
  4. Validar instalación
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: str, description: str) -> int:
    """Ejecutar comando y capturar resultado."""
    print(f"\n{description}...")
    print("-" * 80)
    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode

def main():
    print("\n" + "="*80)
    print("INSTALADOR: PyTorch con CUDA 12.1 para RTX 4060")
    print("="*80)

    # PASO 1: Actualizar pip
    print("\n[PASO 1] Actualizar pip")
    run_command(
        "python -m pip install --upgrade pip",
        "Upgrading pip"
    )

    # PASO 2: Desinstalar PyTorch CPU-only
    print("\n[PASO 2] Desinstalar PyTorch CPU-only")
    run_command(
        "pip uninstall torch torchvision torchaudio -y",
        "Uninstalling CPU-only PyTorch"
    )

    # PASO 3: Instalar PyTorch con CUDA 12.1
    print("\n[PASO 3] Instalar PyTorch + CUDA 12.1")
    print("-" * 80)
    print("Esto descargará ~2GB y tomará algunos minutos...")
    print("GPU detectada: NVIDIA RTX 4060 Laptop")
    print()

    code = run_command(
        "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
        "Installing PyTorch with CUDA 12.1 support"
    )

    if code != 0:
        print("\n❌ Error during installation")
        return 1

    # PASO 4: Validar instalación
    print("\n[PASO 4] Validar instalación")
    print("-" * 80)

    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")

        cuda_available = torch.cuda.is_available()
        print(f"  CUDA available: {cuda_available}")

        if cuda_available:
            print(f"  ✓ CUDA HABILITADO")
            cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
            print(f"    - CUDA version: {cuda_version}")
            print(f"    - GPUs detected: {torch.cuda.device_count()}")

            for i in range(torch.cuda.device_count()):
                device_name = torch.cuda.get_device_name(i)
                print(f"    - GPU {i}: {device_name}")

                # Probar memoria
                props = torch.cuda.get_device_properties(i)
                print(f"      Memory: {props.total_memory / 1e9:.1f} GB")
        else:
            print(f"  ❌ CUDA still not available")
            print(f"     Posible issue: NVIDIA driver no instalado")
            return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    print("\n" + "="*80)
    print("✅ INSTALACIÓN EXITOSA")
    print("="*80)
    print("\nAhora ejecutar:")
    print("  python DIAGNOSTICO_GPU_CUDA_LOCAL.py")
    print("\nY luego:")
    print("  python train_sac_multiobjetivo.py")

    return 0

if __name__ == "__main__":
    sys.exit(main())
