#!/usr/bin/env python3
"""Verificar PyTorch + CUDA availability"""

import torch

print("=" * 60)
print("  PyTorch + CUDA Availability Check")
print("=" * 60)
print()

print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
print()

if torch.cuda.is_available():
    print("✅ GPU DETECTED:")
    print(f"   GPU Name: {torch.cuda.get_device_name(0)}")
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"   GPU Memory: {gpu_mem:.1f} GB")
    print()
    print("✅ PyTorch has CUDA support - GPU READY FOR TRAINING!")
else:
    print("❌ GPU NOT AVAILABLE:")
    print("   PyTorch does NOT have CUDA support")
    print()
    print("To enable GPU, reinstall PyTorch:")
    print("   py -3.11 -m pip install torch --index-url https://download.pytorch.org/whl/cu118")

print()
print("=" * 60)
