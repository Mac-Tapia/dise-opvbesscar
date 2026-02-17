#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIMPIEZA SEGURA DE CHECKPOINTS - SOLO SAC
PROTEGE: PPO, A2C siempre
VALIDA: Solo files que pertenecen a SAC antes de eliminar
ROBUSTO: Reporta antes/despues con validacion completa
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from datetime import datetime

def safe_clean_sac_checkpoints() -> bool:
    """
    Limpia SOLO checkpoints de SAC con validacion estricta.
    
    Returns:
        bool: True si limpieza fue exitosa, False si error
    """
    checkpoint_dir = Path('checkpoints')
    sac_dir = checkpoint_dir / 'SAC'
    ppo_dir = checkpoint_dir / 'PPO'
    a2c_dir = checkpoint_dir / 'A2C'
    
    print()
    print('=' * 90)
    print('LIMPIEZA SEGURA DE CHECKPOINTS SAC (PYTHON ROBUSTO)')
    print('=' * 90)
    print()
    print(f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # ============================================================================
    # PASO 1: LISTAR ESTADO INICIAL - ANTES DE LIMPIAR
    # ============================================================================
    print('[PASO 1] ESTADO INICIAL - Checkpoints detectados')
    print('-' * 90)
    
    checkpoints_before = {
        'SAC': [],
        'PPO': [],
        'A2C': []
    }
    
    for agent_name, agent_dir in [('SAC', sac_dir), ('PPO', ppo_dir), ('A2C', a2c_dir)]:
        if agent_dir.exists():
            files = list(agent_dir.rglob('*'))
            files = [f for f in files if f.is_file()]
            checkpoints_before[agent_name] = files
            print(f'  [{agent_name}] {len(files)} archivos')
            for f in sorted(files)[:5]:  # Mostrar primeros 5
                print(f'         {f.relative_to(checkpoint_dir)}')
            if len(files) > 5:
                print(f'         ... y {len(files) - 5} más')
        else:
            print(f'  [{agent_name}] (no existe)')
    
    print()
    
    # ============================================================================
    # PASO 2: VALIDACION - CONFIRMAR QUE PODEMOS LIMPIAR SOLO SAC
    # ============================================================================
    print('[PASO 2] VALIDACION - Solo se eliminará SAC')
    print('-' * 90)
    
    if sac_dir.exists():
        n_sac_files = len(list(sac_dir.rglob('*')))
        print(f'  ✓ SAC existe: {n_sac_files} archivos serán eliminados')
    else:
        print(f'  ℹ SAC no existe (nada que limpiar)')
    
    if ppo_dir.exists():
        n_ppo_files = len(list(ppo_dir.rglob('*')))
        print(f'  ✓ PPO PROTEGIDO: {n_ppo_files} archivos serán preservados')
    else:
        print(f'  ℹ PPO no existe')
    
    if a2c_dir.exists():
        n_a2c_files = len(list(a2c_dir.rglob('*')))
        print(f'  ✓ A2C PROTEGIDO: {n_a2c_files} archivos serán preservados')
    else:
        print(f'  ℹ A2C no existe')
    
    print()
    
    # ============================================================================
    # PASO 3: LIMPIEZA - ELIMINAR SOLO SAC
    # ============================================================================
    print('[PASO 3] LIMPIEZA SEGURA - Eliminando SAC...')
    print('-' * 90)
    
    if sac_dir.exists():
        try:
            # Contar archivos antes de eliminar
            files_to_delete = list(sac_dir.rglob('*'))
            files_to_delete = [f for f in files_to_delete if f.is_file()]
            
            # Eliminar directorio completo de SAC
            shutil.rmtree(sac_dir)
            print(f'  ✓ Eliminados {len(files_to_delete)} archivos de SAC')
            try:
                sac_rel = sac_dir.relative_to(Path.cwd())
            except (ValueError, TypeError):
                sac_rel = sac_dir
            print(f'  ✓ Directorio eliminado: {sac_rel}')
            
        except Exception as e:
            print(f'  ✗ ERROR al eliminar SAC: {e}')
            return False
    else:
        print(f'  ℹ SAC no existe (nada que eliminar)')
    
    # Recrear directorio vacío para SAC
    try:
        sac_dir.mkdir(parents=True, exist_ok=True)
        print(f'  ✓ Directorio SAC recreado (vacío)')
    except Exception as e:
        print(f'  ✗ ERROR al recrear SAC: {e}')
        return False
    
    print()
    
    # ============================================================================
    # PASO 4: VALIDACION FINAL - CONFIRMAR LIMPIEZA Y PROTECCION
    # ============================================================================
    print('[PASO 4] VALIDACION FINAL - Estado después de limpieza')
    print('-' * 90)
    
    checkpoints_after = {
        'SAC': [],
        'PPO': [],
        'A2C': []
    }
    
    for agent_name, agent_dir in [('SAC', sac_dir), ('PPO', ppo_dir), ('A2C', a2c_dir)]:
        if agent_dir.exists():
            files = list(agent_dir.rglob('*'))
            files = [f for f in files if f.is_file()]
            checkpoints_after[agent_name] = files
            print(f'  [{agent_name}] {len(files)} archivos')
            for f in sorted(files)[:5]:
                print(f'         {f.relative_to(checkpoint_dir)}')
            if len(files) > 5:
                print(f'         ... y {len(files) - 5} más')
        else:
            print(f'  [{agent_name}] (no existe)')
    
    print()
    
    # ============================================================================
    # PASO 5: RESUMEN Y CONFIRMACION
    # ============================================================================
    print('[PASO 5] RESUMEN Y CONFIRMACION')
    print('-' * 90)
    
    sac_cleaned = len(checkpoints_before['SAC']) > len(checkpoints_after['SAC']) or len(checkpoints_after['SAC']) == 0
    ppo_protected = checkpoints_before['PPO'] == checkpoints_after['PPO']
    a2c_protected = checkpoints_before['A2C'] == checkpoints_after['A2C']
    
    print(f'  SAC LIMPIADO:    {sac_cleaned} ✓')
    print(f'  PPO PROTEGIDO:   {ppo_protected} ✓')
    print(f'  A2C PROTEGIDO:   {a2c_protected} ✓')
    
    success = (sac_cleaned and ppo_protected and a2c_protected)
    
    if success and ppo_protected and a2c_protected:
        print()
        print('✓ LIMPIEZA COMPLETADA CON EXITO')
        print('  - SAC: Listo para nuevo entrenamiento')
        print('  - PPO: Protegido y listo para recuperacion')
        print('  - A2C: Protegido y listo para recuperacion')
        print()
        return True
    else:
        print()
        print('✗ LIMPIEZA CON ADVERTENCIAS')
        if not ppo_protected:
            print('  ⚠ PPO fue modificado (ERROR)')
        if not a2c_protected:
            print('  ⚠ A2C fue modificado (ERROR)')
        print()
        return False


def main():
    """Ejecutar limpieza segura de SAC."""
    try:
        success = safe_clean_sac_checkpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print()
        print(f'✗ ERROR FATAL: {e}')
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
