#!/usr/bin/env python
"""
Script para instalar PyTorch con soporte CUDA de forma correcta
"""
import subprocess
import sys

# Primero desinstalar la versión CPU
print("Desinstalando PyTorch CPU...")
subprocess.run([sys.executable, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "-y"],
               capture_output=True)

# Instalar versión con CUDA desde PyTorch oficial
print("\nInstalando PyTorch 2.5.1 con CUDA 12.1...")
result = subprocess.run([
    sys.executable, "-m", "pip", "install", "--default-timeout=1000",
    "torch", "torchvision", "torchaudio",
    "--index-url", "https://download.pytorch.org/whl/cu121"
], text=True)

if result.returncode == 0:
    print("\n✅ PyTorch CUDA instalado exitosamente")
    # Verificar
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("\n❌ Error durante la instalación")
    print("Intentando con espejo alternativo...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--default-timeout=1000",
        "torch", "torchvision", "torchaudio", "-U"
    ])
