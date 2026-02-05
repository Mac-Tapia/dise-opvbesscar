#!/usr/bin/env python3
"""
Script de información del entorno instalado
Muestra detalles de la configuración actual
"""

import sys
import platform
from pathlib import Path

print("\n" + "="*80)
print("INFORMACIÓN DEL ENTORNO INSTALADO")
print("="*80 + "\n")

# Información del Sistema
print("🖥️  SISTEMA OPERATIVO")
print("-" * 80)
print(f"  Sistema: {platform.system()} {platform.release()}")
print(f"  Máquina: {platform.machine()}")
print(f"  Procesador: {platform.processor()}")
print()

# Información de Python
print("🐍 PYTHON")
print("-" * 80)
print(f"  Versión: {sys.version}")
print(f"  Ejecutable: {sys.executable}")
print(f"  Ruta del sitio: {sys.prefix}")
print()

# Información de PyTorch
print("🔥 PYTORCH")
print("-" * 80)
try:
    import torch
    print(f"  Versión: {torch.__version__}")
    print(f"  CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  Versión CUDA: {torch.version.cuda}")
        print(f"  Versión cuDNN: {torch.backends.cudnn.version()}")
        print(f"  Memoria GPU: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print(f"  Modo: CPU (sin aceleración GPU)")
except ImportError:
    print("  ❌ PyTorch no disponible")
print()

# Información de Stable Baselines 3
print("🤖 STABLE BASELINES 3")
print("-" * 80)
try:
    import stable_baselines3
    print(f"  Versión: {stable_baselines3.__version__}")
    print(f"  Agentes disponibles:")
    print(f"    - SAC (Soft Actor-Critic)")
    print(f"    - PPO (Proximal Policy Optimization)")
    print(f"    - A2C (Advantage Actor-Critic)")
except ImportError:
    print("  ❌ Stable Baselines 3 no disponible")
print()

# Información de CityLearn
print("🏢 CITYLEARN")
print("-" * 80)
try:
    import citylearn
    print(f"  Versión: {citylearn.__version__}")
    print(f"  Esquema disponible: v2.5.0")
except ImportError:
    print("  ❌ CityLearn no disponible")
print()

# Información de Gymnasium
print("🎮 GYMNASIUM")
print("-" * 80)
try:
    import gymnasium
    print(f"  Versión: {gymnasium.__version__}")
    print(f"  Compatible con CityLearn: v0.28.1")
except ImportError:
    print("  ❌ Gymnasium no disponible")
print()

# Información de paquetes de datos
print("📊 PAQUETES DE DATOS")
print("-" * 80)
try:
    import numpy as np
    import pandas as pd
    import scipy
    print(f"  NumPy: {np.__version__}")
    print(f"  Pandas: {pd.__version__}")
    print(f"  SciPy: {scipy.__version__}")
except ImportError:
    print("  ❌ Algunos paquetes de datos no disponibles")
print()

# Información de visualización
print("📈 VISUALIZACIÓN")
print("-" * 80)
try:
    import matplotlib
    import seaborn
    import PIL
    print(f"  Matplotlib: {matplotlib.__version__}")
    print(f"  Seaborn: {seaborn.__version__}")
    print(f"  Pillow: {PIL.__version__}")
except ImportError:
    print("  ❌ Algunos paquetes de visualización no disponibles")
print()

# Información de Solar
print("☀️  SOLAR & ENERGÍA")
print("-" * 80)
try:
    import pvlib
    print(f"  pvlib: {pvlib.__version__}")
    print(f"  Funcionalidad: Modelado solar fotovoltaico")
except ImportError:
    print("  ❌ pvlib no disponible")
print()

# Información del proyecto
print("📂 PROYECTO DISEÑOPVBESSCAR")
print("-" * 80)

project_root = Path(__file__).parent
print(f"  Ruta raíz: {project_root}")

dirs_to_check = [
    "src",
    "configs",
    "data",
    "docs",
    "outputs",
    "checkpoints",
]

print(f"  Estructura del proyecto:")
for dir_name in dirs_to_check:
    dir_path = project_root / dir_name
    if dir_path.exists():
        print(f"    ✓ {dir_name}")
    else:
        print(f"    - {dir_name} (crear)")

print()

# Configuración recomendada
print("⚙️  CONFIGURACIÓN RECOMENDADA")
print("-" * 80)
print("  Para entrenamientos óptimos:")
print()
print("  SAC (Soft Actor-Critic):")
print("    - learning_rate: 5e-5")
print("    - batch_size: 256")
print("    - buffer_size: 200,000")
print("    - Duración: 5-10 episodios (43,800-87,600 pasos)")
print()
print("  PPO (Proximal Policy Optimization):")
print("    - learning_rate: 1e-4")
print("    - n_steps: 2,048")
print("    - batch_size: 256")
print("    - Duración: 500,000+ pasos")
print()
print("  A2C (Advantage Actor-Critic):")
print("    - learning_rate: 1e-4")
print("    - n_steps: 2,048")
print("    - Duración: 500,000+ pasos")
print()

# Recomendaciones finales
print("=" * 80)
print("✅ CONFIGURACIÓN LISTA PARA DESARROLLO")
print("=" * 80 + "\n")

print("Para comenzar:")
print("  1. python verify_installation.py  # Verificar todas las dependencias")
print("  2. python -m scripts.run_oe3_simulate --help  # Ver opciones disponibles")
print("  3. python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac")
print("\n")
