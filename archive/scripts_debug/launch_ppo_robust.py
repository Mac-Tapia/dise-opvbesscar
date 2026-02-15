#!/usr/bin/env python3
"""Lanzador robusto de entrenamiento PPO"""
import subprocess
import sys
from pathlib import Path

print('='*80)
print('LANZADOR ROBUSTO PPO')
print('='*80)
print()

# Asegurar que estamos en el directorio correcto
project_root = Path.cwd()
print(f'Directorio de proyecto: {project_root}')
print(f'PYTHONPATH: {sys.path[0]}')

# Crear environment limpio para el subprocess
import os
env = os.environ.copy()
env['PYTHONPATH'] = str(project_root) + ':' + env.get('PYTHONPATH', '')

log_file = project_root / 'outputs/ppo_training/ppo_training.log'

print(f'Log: {log_file}')
print()

print('Iniciando entrenamiento PPO...')

cmd = [
    sys.executable, 
    'scripts/train/train_ppo_multiobjetivo.py'
]

with open(log_file, 'w') as f:
    proc = subprocess.Popen(
        cmd,
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=str(project_root),
        env=env
    )

print(f'✓ Entrenamiento lanzado (PID {proc.pid})')
print(f'✓ Log: {log_file}')
print()
print('Monitorear con:')
print(f'  Get-Content "{log_file}" -Tail 50 -Wait')
