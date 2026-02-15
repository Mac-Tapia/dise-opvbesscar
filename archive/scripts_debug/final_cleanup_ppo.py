#!/usr/bin/env python3
"""Limpiar completamente PPO checkpoints y outputs"""
from pathlib import Path
import shutil

print('Limpiando estructura PPO completamente...')

dirs_to_clean = [
    Path('checkpoints/PPO'),
    Path('outputs/ppo_training')
]

for dir_path in dirs_to_clean:
    if dir_path.exists():
        # Eliminar todos los archivos
        for f in dir_path.glob('*'):
            if f.is_file():
                f.unlink()
        print(f'✓ Limpiado: {dir_path}')
    else:
        # Crear si no existe
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f'✓ Creado: {dir_path}')

print()
print('✓ Ambiente PPO limpio y listo para entrenar')
