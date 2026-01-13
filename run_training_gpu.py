#!/usr/bin/env python3
"""Verificar disponibilidad GPU y lanzar entrenamiento RL con máximo rendimiento."""

import torch
import os

print("=" * 60)
print("CONFIGURACIÓN GPU")
print("=" * 60)

cuda_available = torch.cuda.is_available()
print(f"✓ CUDA Disponible: {cuda_available}")

if cuda_available:
    device_count = torch.cuda.device_count()
    print(f"✓ Número de GPUs: {device_count}")
    
    for i in range(device_count):
        props = torch.cuda.get_device_properties(i)
        print(f"  GPU {i}: {props.name}")
        print(f"    - Memoria Total: {props.total_memory / 1e9:.2f} GB")
        print(f"    - Compute Capability: {props.major}.{props.minor}")
    
    print(f"✓ GPU Actual: {torch.cuda.current_device()}")
    print(f"✓ Memoria Disponible: {torch.cuda.get_device_properties(torch.cuda.current_device()).total_memory / 1e9:.2f} GB")
    
    # Configurar variables ambientales para máximo rendimiento
    os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Async GPU operations (más rápido)
    os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    os.environ['OMP_NUM_THREADS'] = '4'
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    
    print("\n✓ Configuración GPU optimizada:")
    print("  - CUDA_LAUNCH_BLOCKING=0 (async operations)")
    print("  - OMP_NUM_THREADS=4")
    print("  - CUDA_VISIBLE_DEVICES=0 (GPU 0)")
else:
    print("✗ CUDA NO disponible - usando CPU")
    device = 'cpu'

print("\n" + "=" * 60)
print("INICIANDO ENTRENAMIENTO RL CON GPU")
print("=" * 60 + "\n")

# Lanzar entrenamiento
import subprocess
import sys

cmd = [
    sys.executable, 
    "-m", 
    "scripts.run_oe3_simulate",
    "--config", 
    "configs/default.yaml"
]

print(f"Comando: {' '.join(cmd)}\n")
result = subprocess.run(cmd, cwd="d:\\diseñopvbesscar")
sys.exit(result.returncode)
