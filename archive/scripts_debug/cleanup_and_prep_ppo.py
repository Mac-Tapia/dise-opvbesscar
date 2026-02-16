#!/usr/bin/env python3
"""Limpieza de checkpoints y preparación para PPO"""
from pathlib import Path

print('='*80)
print('LIMPIEZA Y PREPARACION PARA PPO')
print('='*80)
print()

# 1. Limpiar SAC Checkpoints
sac_dir = Path('checkpoints/SAC')
if sac_dir.exists():
    files = list(sac_dir.glob('*'))
    for f in files:
        if f.is_file():
            f.unlink()
    print(f'[OK] Checkpoints SAC limpiados ({len(files)} archivos eliminados)')
else:
    print('[OK] Directorio SAC no existe (limpio)')

# 2. Limpiar outputs SAC  
sac_out = Path('outputs/sac_training')
if sac_out.exists():
    files = list(sac_out.glob('*'))
    for f in files:
        if f.is_file():
            f.unlink()
    print(f'[OK] Outputs SAC limpiados ({len(files)} archivos eliminados)')
else:
    print('[OK] Outputs SAC no existe (limpio)')

# 3. Crear estructura PPO limpia
ppo_dir = Path('checkpoints/PPO')
ppo_out = Path('outputs/ppo_training')
ppo_dir.mkdir(parents=True, exist_ok=True)
ppo_out.mkdir(parents=True, exist_ok=True)
print(f'[OK] Estructura PPO creada')

print()
print('Estado actual:')
print(f'  ✓ Checkpoints SAC: {len(list(sac_dir.glob("*")))} archivos')
print(f'  ✓ Checkpoints PPO: {len(list(ppo_dir.glob("*")))} archivos (LIMPIO)')
print(f'  ✓ Outputs SAC: {len(list(sac_out.glob("*")))} archivos')
print(f'  ✓ Outputs PPO: {len(list(ppo_out.glob("*")))} archivos (LIMPIO)')

print()
print('='*80)
print('Limpieza completada - Listo para entrenamiento PPO')
print('='*80)
