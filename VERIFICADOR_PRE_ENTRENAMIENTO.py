#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR PRE-ENTRENAMIENTO
Comprobación rápida que TODOS los agentes están listos para entrenamiento COMPLETO.
Ejecutar antes de: python scripts/train/train_sac_multiobjetivo.py (etc)
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Add workspace to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

def check_agents_compiled() -> bool:
    """Verificar que los 3 scripts compilen sin errores."""
    print('\n[1] VERIFICAR COMPILACION DE AGENTES')
    print('-' * 80)
    
    files_to_check = [
        'scripts/train/train_sac_multiobjetivo.py',
        'scripts/train/train_ppo_multiobjetivo.py',
        'scripts/train/train_a2c_multiobjetivo.py',
    ]
    
    all_ok = True
    for filepath in files_to_check:
        full_path = workspace_root / filepath
        if not full_path.exists():
            print(f'  ❌ No existe: {filepath}')
            all_ok = False
            continue
        
        try:
            compile(open(full_path, encoding='utf-8').read(), str(full_path), 'exec')
            print(f'  ✅ {filepath} compila correctamente')
        except SyntaxError as e:
            print(f'  ❌ Error syntax en {filepath}: {e}')
            all_ok = False
    
    return all_ok


def check_validation_module() -> bool:
    """Verificar que training_validation.py existe e importa correctamente."""
    print('\n[2] VERIFICAR MÓDULO CENTRALIZADO')
    print('-' * 80)
    
    validation_path = workspace_root / 'src' / 'agents' / 'training_validation.py'
    
    if not validation_path.exists():
        print(f'  ❌ No existe: src/agents/training_validation.py')
        return False
    
    print(f'  ✅ src/agents/training_validation.py existe')
    
    try:
        from src.agents.training_validation import validate_agent_config
        print(f'  ✅ Puede importar validate_agent_config()')
    except ImportError as e:
        print(f'  ❌ Error importando: {e}')
        return False
    
    return True


def check_oe2_datasets() -> bool:
    """Verificar que los 5 archivos OE2 existen."""
    print('\n[3] VERIFICAR DATASETS OE2')
    print('-' * 80)
    
    required_files = {
        'Solar': 'data/interim/oe2/solar/pv_generation_citylearn2024.csv',
        'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
        'BESS': 'data/oe2/bess/bess_ano_2024.csv',
        'Mall': 'data/oe2/mall/demandamallhorakwh.csv',
    }
    
    all_ok = True
    for name, filepath in required_files.items():
        full_path = workspace_root / filepath
        if full_path.exists():
            # Check row count if CSV
            if filepath.endswith('.csv'):
                try:
                    import pandas as pd
                    df = pd.read_csv(full_path)
                    rows = len(df)
                    print(f'  ✅ {name:12} ({filepath}) - {rows} horas')
                    
                    # Validate 8,760 hours requirement
                    if rows == 8760:
                        print(f'     → ✅ Exactamente 8,760 horas (correcto para 1 año)')
                    else:
                        print(f'     → ⚠️  {rows} horas (NO 8,760 - problema de escala)')
                        all_ok = False
                except Exception as e:
                    print(f'  ❌ Error leyendo {filepath}: {e}')
                    all_ok = False
            else:
                print(f'  ✅ {name:12} ({filepath}) existe')
        else:
            print(f'  ❌ No existe: {filepath}')
            all_ok = False
    
    return all_ok


def check_agent_constants() -> bool:
    """Verificar que constantes de agentes están sincronizadas."""
    print('\n[4] VERIFICAR CONSTANTES SINCRONIZADAS')
    print('-' * 80)
    
    try:
        # SAC
        sys.path.insert(0, str(workspace_root / 'scripts' / 'train'))
        from train_sac_multiobjetivo import (
            CO2_FACTOR_IQUITOS as SAC_CO2,
            BESS_CAPACITY_KWH as SAC_BESS_CAP,
            BESS_MAX_KWH_CONST as SAC_BESS_MAX,
            HOURS_PER_YEAR as SAC_HOURS,
        )
        from train_ppo_multiobjetivo import (
            CO2_FACTOR_IQUITOS as PPO_CO2,
            BESS_CAPACITY_KWH as PPO_BESS_CAP,
            BESS_MAX_KWH_CONST as PPO_BESS_MAX,
            HOURS_PER_YEAR as PPO_HOURS,
        )
        from train_a2c_multiobjetivo import (
            CO2_FACTOR_IQUITOS as A2C_CO2,
            BESS_CAPACITY_KWH as A2C_BESS_CAP,
            BESS_MAX_KWH_CONST as A2C_BESS_MAX,
            HOURS_PER_YEAR as A2C_HOURS,
        )
        
        # Check CO2
        if SAC_CO2 == PPO_CO2 == A2C_CO2 == 0.4521:
            print(f'  ✅ CO2 Factor Iquitos: {SAC_CO2} kg/kWh (SAC=PPO=A2C)')
        else:
            print(f'  ❌ CO2 Factor desincronizado: SAC={SAC_CO2}, PPO={PPO_CO2}, A2C={A2C_CO2}')
            return False
        
        # Check BESS capacity
        if SAC_BESS_CAP == PPO_BESS_CAP == A2C_BESS_CAP == 940.0:
            print(f'  ✅ BESS Capacity EV: {SAC_BESS_CAP} kWh (SAC=PPO=A2C)')
        else:
            print(f'  ❌ BESS Capacity desincronizado: SAC={SAC_BESS_CAP}, PPO={PPO_BESS_CAP}, A2C={A2C_BESS_CAP}')
            return False
        
        # Check BESS max (normalización)
        if SAC_BESS_MAX == PPO_BESS_MAX == A2C_BESS_MAX == 1700.0:
            print(f'  ✅ BESS Max (normalización): {SAC_BESS_MAX} kWh (SAC=PPO=A2C)')
        else:
            print(f'  ❌ BESS Max desincronizado: SAC={SAC_BESS_MAX}, PPO={PPO_BESS_MAX}, A2C={A2C_BESS_MAX}')
            return False
        
        # Check hours per year
        if SAC_HOURS == PPO_HOURS == A2C_HOURS == 8760:
            print(f'  ✅ Hours/Year: {SAC_HOURS} (SAC=PPO=A2C)')
        else:
            print(f'  ❌ Hours/Year desincronizado: SAC={SAC_HOURS}, PPO={PPO_HOURS}, A2C={A2C_HOURS}')
            return False
        
        return True
        
    except ImportError as e:
        print(f'  ❌ Error importando constantes: {e}')
        return False


def check_training_spec() -> bool:
    """Verificar que la especificación de entrenamiento está documentada."""
    print('\n[5] VERIFICAR ESPECIFICACION ENTRENAMIENTO')
    print('-' * 80)
    
    spec_file = workspace_root / 'ENTRENAMIENTO_COMPLETO_SPEC.py'
    
    if spec_file.exists():
        print(f'  ✅ ENTRENAMIENTO_COMPLETO_SPEC.py existe')
    else:
        print(f'  ❌ No existe: ENTRENAMIENTO_COMPLETO_SPEC.py')
        return False
    
    # Check key requirements
    try:
        spec_content = spec_file.read_text(encoding='utf-8')
        
        checks = {
            'episodios': 10,
            'TOTAL_TIMESTEPS: int = 87_600': True,
            'obs_dim': '246|156',
            'action_dim': 39,
        }
        
        for check_str, expected in checks.items():
            if isinstance(expected, bool):
                if check_str in spec_content:
                    print(f'  ✅ {check_str} definido')
                else:
                    print(f'  ⚠️  No encontrado: {check_str}')
            else:
                if str(expected) in spec_content:
                    print(f'  ✅ {check_str}: {expected}')
        
        return True
    except Exception as e:
        print(f'  ❌ Error leyendo spec: {e}')
        return False


def main():
    """Ejecutar todas las verificaciones."""
    print('=' * 80)
    print('VERIFICADOR PRE-ENTRENAMIENTO - GARANTÍA DE ENTRENAMIENTO COMPLETO')
    print('=' * 80)
    print('Este script verifica que TODOS los agentes están listos para entrenamiento')
    print('con 10 episodios completos (87,600 timesteps cada uno) usando TODOS los')
    print('datos OE2 y TODAS las columnas observables.')
    print()
    
    results = {
        'Compilación': check_agents_compiled(),
        'Validación centralizada': check_validation_module(),
        'Datasets OE2': check_oe2_datasets(),
        'Constantes sincronizadas': check_agent_constants(),
        'Especificación documentada': check_training_spec(),
    }
    
    print('\n' + '=' * 80)
    print('RESUMEN')
    print('=' * 80)
    
    for check_name, result in results.items():
        status = '✅' if result else '❌'
        print(f'{status} {check_name}')
    
    all_ok = all(results.values())
    
    print()
    if all_ok:
        print('🚀 ¡TODOS LOS AGENTES ESTÁN LISTOS PARA ENTRENAMIENTO!')
        print()
        print('Próximos pasos:')
        print('  1. python scripts/train/train_sac_multiobjetivo.py  (4-6h GPU)')
        print('  2. python scripts/train/train_ppo_multiobjetivo.py  (3-5h GPU)')
        print('  3. python scripts/train/train_a2c_multiobjetivo.py  (2-3h GPU)')
        print()
        print('O en paralelo si tienes múltiples GPUs:')
        print('  nohup python scripts/train/train_sac_multiobjetivo.py &')
        print('  nohup python scripts/train/train_ppo_multiobjetivo.py &')
        print('  nohup python scripts/train/train_a2c_multiobjetivo.py &')
        print()
        return 0
    else:
        print('⚠️  Algunos requisitos no se cumplen.')
        print('   Revisa los ❌ arriba y corrige antes de entrenar.')
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
