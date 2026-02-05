#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DIAGNOSTICO_GPU_CUDA_LOCAL.py
===============================

Verifica GPU/CUDA disponible y proporciona configuración optimizada.

Ejecución:
  python DIAGNOSTICO_GPU_CUDA_LOCAL.py

Detecta:
  1. PyTorch y versión
  2. CUDA disponible y versión
  3. GPU/CUDA detectado
  4. Device recomendado (cuda:0 o cpu)
  5. Propiedades del GPU (si existe)
  6. Configuración recomendada para entrenamiento
"""

import sys
import json
from pathlib import Path
from typing import Any

def diagnose_gpu_cuda() -> tuple[dict[str, Any], int]:
    """Diagnosticar GPU/CUDA y retornar configuración."""

    print("\n" + "="*80)
    print("DIAGNÓSTICO GPU/CUDA LOCAL")
    print("="*80 + "\n")

    config: dict[str, Any] = {
        "timestamp": str(Path.cwd()),
        "pytorch": {},
        "cuda": {},
        "gpu": {},
        "device_recommendation": None,
        "issues": [],
        "warnings": []
    }

    # PASO 1: Verificar PyTorch
    print("[PASO 1] Verificar PyTorch")
    print("-" * 80)

    try:
        import torch
        print(f"  ✓ PyTorch instalado: {torch.__version__}")
        config["pytorch"]["version"] = torch.__version__
        config["pytorch"]["installed"] = True
    except ImportError as e:
        print(f"  ❌ PyTorch NO instalado: {e}")
        config["pytorch"]["installed"] = False
        config["issues"].append(f"PyTorch not installed: {e}")
        return config, 1

    # PASO 2: Verificar CUDA en PyTorch
    print("\n[PASO 2] Verificar CUDA en PyTorch")
    print("-" * 80)

    cuda_available = torch.cuda.is_available()
    print(f"  CUDA available: {cuda_available}")
    config["cuda"]["available"] = cuda_available

    if cuda_available:
        print(f"  ✓ CUDA DISPONIBLE")

        cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
        cudnn_version = torch.backends.cudnn.version()
        print(f"    - CUDA version (PyTorch): {cuda_version}")
        print(f"    - cuDNN version: {cudnn_version}")

        config["cuda"]["version"] = cuda_version
        config["cuda"]["cudnn_version"] = cudnn_version

        # PASO 3: Propiedades del GPU
        print("\n[PASO 3] Propiedades del GPU")
        print("-" * 80)

        num_gpus = torch.cuda.device_count()
        print(f"  GPUs detectados: {num_gpus}")
        config["gpu"]["count"] = num_gpus

        if num_gpus > 0:
            for i in range(num_gpus):
                device_name = torch.cuda.get_device_name(i)
                print(f"    GPU {i}: {device_name}")

                # Propiedades del GPU
                device_props = torch.cuda.get_device_properties(i)
                print(f"      - Memoria total: {device_props.total_memory / 1e9:.2f} GB")
                print(f"      - Capability: {device_props.major}.{device_props.minor}")

                config["gpu"][f"gpu_{i}"] = {
                    "name": device_name,
                    "total_memory_gb": device_props.total_memory / 1e9,
                    "capability": f"{device_props.major}.{device_props.minor}"
                }

        # PASO 4: Verificar cuDNN enabled
        print("\n[PASO 4] Verificar cuDNN")
        print("-" * 80)

        cudnn_enabled = torch.backends.cudnn.enabled
        print(f"  cuDNN enabled: {cudnn_enabled}")
        config["cuda"]["cudnn_enabled"] = cudnn_enabled

        if not cudnn_enabled:
            config["warnings"].append("cuDNN is disabled - enabling...")
            torch.backends.cudnn.enabled = True
            print(f"  → Habilitando cuDNN...")

        # PASO 5: Verificar memoria disponible
        print("\n[PASO 5] Verificar memoria GPU disponible")
        print("-" * 80)

        torch.cuda.empty_cache()
        memory_allocated = torch.cuda.memory_allocated(0) / 1e9
        memory_reserved = torch.cuda.memory_reserved(0) / 1e9

        print(f"  Memoria asignada: {memory_allocated:.2f} GB")
        print(f"  Memoria reservada: {memory_reserved:.2f} GB")

        config["gpu"]["memory_allocated_gb"] = memory_allocated
        config["gpu"]["memory_reserved_gb"] = memory_reserved

    else:
        print(f"  ⚠️  CUDA NO DISPONIBLE - Usando CPU")
        config["cuda"]["available"] = False
        config["warnings"].append("CUDA not available - will use CPU")

    # PASO 6: Recomendación de device
    print("\n[PASO 6] Recomendación de Device")
    print("-" * 80)

    if cuda_available and torch.cuda.device_count() > 0:
        device = "cuda:0"
        print(f"  ✓ Device recomendado: {device}")
        config["device_recommendation"] = device
    else:
        device = "cpu"
        print(f"  → Device: {device} (CPU mode)")
        config["device_recommendation"] = device

    # PASO 7: Configuración recomendada para entrenamiento
    print("\n[PASO 7] Configuración recomendada para entrenamiento")
    print("-" * 80)

    if cuda_available and torch.cuda.device_count() > 0:
        config["recommended_config"] = {
            "device": "cuda:0",
            "learning_rate": 3e-4,
            "batch_size": 128,
            "buffer_size": 1000000,
            "network_arch": [256, 256],
            "mixed_precision": True,
            "num_workers": 4,
            "pin_memory": True,
            "notes": "GPU mode - faster training (5-10h per agent)"
        }
        print(f"  MODO GPU:")
        print(f"    - Device: cuda:0")
        print(f"    - Batch size: 128 (puede aumentarse)")
        print(f"    - Learning rate: 3e-4")
        print(f"    - Mixed precision: True (más rápido)")
        print(f"    - Num workers: 4")
        print(f"    - Tiempo esperado: 5-10 horas por agente")
    else:
        config["recommended_config"] = {
            "device": "cpu",
            "learning_rate": 3e-4,
            "batch_size": 64,
            "buffer_size": 1000000,
            "network_arch": [256, 256],
            "mixed_precision": False,
            "num_workers": 0,
            "pin_memory": False,
            "notes": "CPU mode - slower training (10-15h per agent)"
        }
        print(f"  MODO CPU:")
        print(f"    - Device: cpu")
        print(f"    - Batch size: 64 (CPU optimized)")
        print(f"    - Learning rate: 3e-4")
        print(f"    - Mixed precision: False (CPU no lo soporta)")
        print(f"    - Num workers: 0")
        print(f"    - Tiempo esperado: 10-15 horas por agente")

    # PASO 8: Verificación de importancias
    print("\n[PASO 8] Verificación de dependencias críticas")
    print("-" * 80)

    deps = {
        "torch": False,
        "gymnasium": False,
        "stable-baselines3": False,
        "pandas": False,
        "numpy": False,
    }

    try:
        import torch
        deps["torch"] = True
    except:
        pass

    try:
        import gymnasium
        deps["gymnasium"] = True
    except:
        pass

    try:
        import stable_baselines3
        deps["stable-baselines3"] = True
    except:
        pass

    try:
        import pandas
        deps["pandas"] = True
    except:
        pass

    try:
        import numpy
        deps["numpy"] = True
    except:
        pass

    for dep, installed in deps.items():
        status = "✓" if installed else "❌"
        print(f"  {status} {dep}")
        if not installed:
            config["issues"].append(f"{dep} not installed")

    return config, 0


def main():
    """Ejecutar diagnóstico y generar reporte."""

    config, code = diagnose_gpu_cuda()

    # PASO 9: Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80 + "\n")

    if config["cuda"]["available"]:
        print("✅ GPU/CUDA DISPONIBLE")
        print(f"   Device: {config['device_recommendation']}")
        print(f"   GPU(s): {config['gpu']['count']}")

        if config["gpu"]["count"] > 0:
            for i in range(config["gpu"]["count"]):
                gpu_info = config["gpu"].get(f"gpu_{i}", {})
                if gpu_info:
                    print(f"   - {gpu_info.get('name', 'Unknown')}")
                    print(f"     Memoria: {gpu_info.get('total_memory_gb', 0):.1f} GB")
    else:
        print("⚠️  GPU/CUDA NO DISPONIBLE")
        print(f"   Device: CPU")
        print("   El entrenamiento será LENTO (10-15h por agente)")

    # Mostrar issues
    if config["issues"]:
        print(f"\n❌ PROBLEMAS ({len(config['issues'])}):")
        for issue in config["issues"]:
            print(f"   - {issue}")

    # Mostrar warnings
    if config["warnings"]:
        print(f"\n⚠️  ADVERTENCIAS ({len(config['warnings'])}):")
        for warning in config["warnings"]:
            print(f"   - {warning}")

    # Guardar config a JSON
    config_file = Path("gpu_cuda_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Configuración guardada: {config_file}")

    print("\n" + "=" * 80)
    print("PRÓXIMOS PASOS")
    print("=" * 80 + "\n")

    if config["cuda"]["available"]:
        print("1. Los scripts de entrenamiento usarán GPU automáticamente")
        print("2. Ejecutar:")
        print("   python train_sac_multiobjetivo.py  # ~5h GPU (vs 10h CPU)")
        print("3. El entrenamiento será 2x más rápido")
        return 0
    else:
        print("1. GPU/CUDA no disponible - se usará CPU")
        print("2. Ejecutar:")
        print("   python train_sac_multiobjetivo.py  # ~10-15h CPU")
        print("3. Considerar:")
        print("   - Instalar NVIDIA driver (si hay GPU)")
        print("   - Instalar CUDA Toolkit 11.8+")
        print("   - pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        return 1


if __name__ == "__main__":
    sys.exit(main())
