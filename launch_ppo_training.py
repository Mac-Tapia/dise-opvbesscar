#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper para lanzar entrenamiento PPO con PYTHONPATH configurado correctamente
"""
import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Asegurar que src está disponible
src_path = project_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Configurar variable de entorno
os.environ['PYTHONPATH'] = f"{str(project_root)};{os.environ.get('PYTHONPATH', '')}"

print(f"[OK] PYTHONPATH configurado: {sys.path[:3]}")
print(f"[OK] Working directory: {os.getcwd()}")
print()

# Ahora importar y ejecutar el entrenamiento
from scripts.train.train_ppo_multiobjetivo import main

if __name__ == '__main__':
    main()
