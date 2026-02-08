#!/usr/bin/env python
"""Limpiar checkpoints y outputs sin confirmación interactiva."""
from pathlib import Path
import shutil

# Rutas a limpiar
CHECKPOINTS_DIR = Path('checkpoints')
OUTPUTS_DIR = Path('outputs')

def clean_directory(dir_path: Path, dir_name: str) -> int:
    """Elimina directorio completo y recuenta."""
    if not dir_path.exists():
        print(f'  ✓ {dir_name}: No existe (OK)')
        return 0
    
    try:
        count = sum(1 for _ in dir_path.rglob('*'))
        shutil.rmtree(dir_path)
        print(f'  ✓ {dir_name}: Eliminados {count} archivos')
        return count
    except Exception as e:
        print(f'  ✗ {dir_name}: Error - {e}')
        return 0

print('\n╔════════════════════════════════════════════════════════════╗')
print('║    LIMPIEZA AUTOMÁTICA - Checkpoints + Outputs           ║')
print('╚════════════════════════════════════════════════════════════╝\n')

print('Eliminando...')
total = 0
total += clean_directory(CHECKPOINTS_DIR, 'checkpoints/')
total += clean_directory(OUTPUTS_DIR, 'outputs/')

print(f'\n✅ Limpieza completada: {total} items eliminados\n')

# Recrear directorios vacíos
CHECKPOINTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
print('✅ Directorios preparados para nuevos checkpoint/outputs\n')
