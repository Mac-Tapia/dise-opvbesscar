#!/usr/bin/env python
"""Verificar estado de CUDA en PyTorch"""

import torch

print("=" * 70)
print("🔍 ESTADO DE CUDA EN PYTORCH")
print("=" * 70)
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device count: {torch.cuda.device_count()}")

if torch.cuda.is_available():
    print(f"Current CUDA device: {torch.cuda.current_device()}")
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
    print(f"CUDA capability: {torch.cuda.get_device_capability(0)}")
    
    # Prueba simple de tensor
    x = torch.randn(3, 3, device='cuda')
    print(f"\n✅ Tensor test on GPU: SUCCESS")
    print(f"Tensor device: {x.device}")
else:
    print("\n❌ CUDA NOT AVAILABLE")
    print("PyTorch was installed without CUDA support")
