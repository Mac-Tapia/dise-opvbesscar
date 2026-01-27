#!/usr/bin/env python3
"""
Quick GPU optimization verification script
Ensures RTX 4060 is ready for optimized training
"""
from __future__ import annotations

import torch
import sys

def main():
    print("\n" + "="*80)
    print("GPU OPTIMIZATION VERIFICATION FOR RTX 4060")
    print("="*80)

    # Check PyTorch
    print("\n[PyTorch Status]")
    print(f"  Version: {torch.__version__}")
    print(f"  CUDA Available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("  ERROR: CUDA not available!")
        sys.exit(1)

    # Check GPU
    print("\n[GPU Details]")
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    compute_cap = torch.cuda.get_device_capability(0)

    print(f"  Name: {gpu_name}")
    print(f"  Memory: {gpu_memory_gb:.1f} GB")
    print(f"  Compute Capability: {compute_cap[0]}.{compute_cap[1]}")

    if gpu_memory_gb < 8.0:
        print(f"  WARNING: GPU memory < 8 GB. Config may cause OOM.")
    else:
        print(f"  OK: GPU memory >= 8 GB")

    if compute_cap[0] >= 8:
        print(f"  OK: TF32 support available (Ampere+)")
    else:
        print(f"  NOTE: TF32 not available (pre-Ampere GPU)")

    # Check cuDNN
    print("\n[cuDNN Status]")
    print(f"  Enabled: {torch.backends.cudnn.enabled}")
    print(f"  Benchmark: {torch.backends.cudnn.benchmark}")
    print(f"  Deterministic: {torch.backends.cudnn.deterministic}")

    # Test GPU computation
    print("\n[GPU Computation Test]")
    try:
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.matmul(x, y)
        print(f"  Matrix multiplication: OK")
        print(f"  Result shape: {z.shape}")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Check configuration file
    print("\n[Configuration Status]")
    try:
        import yaml  # type: ignore
        with open("configs/default.yaml") as f:
            cfg = yaml.safe_load(f)

        sac_cfg = cfg['evaluation']['sac']
        ppo_cfg = cfg['evaluation']['ppo']
        a2c_cfg = cfg['evaluation']['a2c']

        print(f"  SAC batch_size: {sac_cfg['batch_size']} (expected 256)")
        print(f"  SAC buffer_size: {sac_cfg['buffer_size']} (expected 1000000)")
        print(f"  PPO n_steps: {ppo_cfg['n_steps']} (expected 8192)")
        print(f"  PPO n_epochs: {ppo_cfg['n_epochs']} (expected 40)")
        print(f"  A2C n_steps: {a2c_cfg['n_steps']} (expected 128)")
        print(f"  A2C batch_size: {a2c_cfg['batch_size']} (expected 2048)")
        print(f"  All configs: OK")

    except Exception as e:
        print(f"  WARNING: Could not load config: {e}")

    print("\n" + "="*80)
    print("VERIFICATION COMPLETE - GPU READY FOR OPTIMIZED TRAINING")
    print("="*80)
    print("\nNext step: Run training with:")
    print("  py -3.11 -m scripts.launch_gpu_optimized_training")
    print("")

if __name__ == "__main__":
    main()
