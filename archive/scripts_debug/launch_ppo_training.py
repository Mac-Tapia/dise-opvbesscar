#!/usr/bin/env python3
"""Lanzador simple de entrenamiento PPO"""
import subprocess
import time
import sys
from pathlib import Path

print('='*80)
print('LANZADOR DE ENTRENAMIENTO PPO')
print('='*80)
print()

script_path = Path('scripts/train/train_ppo_multiobjetivo.py')
log_file = Path('outputs/ppo_training/ppo_training.log')

print(f'Script: {script_path}')
print(f'Log: {log_file}')
print()

if not script_path.exists():
    print(f'ERROR: {script_path} no encontrado')
    sys.exit(1)

print('Iniciando entrenamiento...')
print()

# Lanzar en background
try:
    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
        cwd=Path.cwd()
    )
    print(f'PID: {proc.pid}')
    print(f'Status: Entrenamiento lanzado')
    print()
    
    # Esperar a que genere logs
    print('Esperando inicialización (15 segundos)...')
    time.sleep(15)
    
    # Mostrar primeros logs
    if log_file.exists():
        with open(log_file) as f:
            lines = f.readlines()
        print()
        print('Primeras líneas del log:')
        print('-'*80)
        for line in lines[:30]:
            print(line.rstrip())
        print('-'*80)
        print()
        print(f'Log actualizado: {len(lines)} líneas')
    else:
        print('Log aun no creado')
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
