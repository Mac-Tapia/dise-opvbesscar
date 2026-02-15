#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher para entrenamiento PPO - resuelve issues de PYTHONPATH"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Solución de PYTHONPATH - agregar directorio del proyecto al path
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / 'src'))

print(f'[LAUNCHER] Working dir: {os.getcwd()}')
print(f'[LAUNCHER] Python path incluye:')
for p in sys.path[:3]:
    print(f'  - {p}')
print()

# Ahora importar y ejecutar el entrenamiento
try:
    from scripts.train.train_ppo_multiobjetivo import main
    print('[LAUNCHER] ✓ Módulos importados correctamente')
    print('[LAUNCHER] Iniciando entrenamiento PPO...')
    print('-' * 80)
    print()
    main()
except Exception as e:
    print(f'[ERROR] {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
