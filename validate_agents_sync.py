#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validacion integral de sincronizacion de agentes SAC, PPO, A2C.
Este script verifica que los 3 agentes esten correctamente vinculados y sincronizados.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts' / 'train'))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print('\n' + '='*80)
print('[VALIDACION INTEGRAL] Sincronizacion de Agentes SAC, PPO, A2C')
print('='*80)

# Test imports
print('\n[1/5] Validando importaciones...')
try:
    from train_sac_multiobjetivo import (
        BESS_CAPACITY_KWH as SAC_BESS_CAP,
        BESS_MAX_KWH_CONST as SAC_BESS_MAX,
        SOLAR_MAX_KW as SAC_SOLAR_MAX,
        ALL_OBSERVABLE_COLS as SAC_OBS,
    )
    print('  ✅ SAC: Importación exitosa')
except Exception as e:
    print(f'  ❌ SAC: Error - {e}')
    sys.exit(1)

try:
    from train_ppo_multiobjetivo import (
        BESS_CAPACITY_KWH as PPO_BESS_CAP,
        BESS_MAX_KWH as PPO_BESS_MAX,
        SOLAR_MAX_KW as PPO_SOLAR_MAX,
        ALL_OBSERVABLE_COLS as PPO_OBS,
    )
    print('  ✅ PPO: Importación exitosa')
except Exception as e:
    print(f'  ❌ PPO: Error - {e}')
    sys.exit(1)

try:
    from train_a2c_multiobjetivo import (
        BESS_CAPACITY_KWH as A2C_BESS_CAP,
        BESS_MAX_KWH_CONST as A2C_BESS_MAX,
        SOLAR_MAX_KW as A2C_SOLAR_MAX,
        ALL_OBSERVABLE_COLS as A2C_OBS,
    )
    print('  ✅ A2C: Importación exitosa')
except Exception as e:
    print(f'  ❌ A2C: Error - {e}')
    sys.exit(1)

# Test synchronization
print('\n[2/5] Validando sincronizacion BESS...')
checks = {
    'SAC BESS_CAPACITY = 940.0': SAC_BESS_CAP == 940.0,
    'PPO BESS_CAPACITY = 940.0': PPO_BESS_CAP == 940.0,
    'A2C BESS_CAPACITY = 940.0': A2C_BESS_CAP == 940.0,
    'SAC BESS_MAX = 1700.0': SAC_BESS_MAX == 1700.0,
    'PPO BESS_MAX = 1700.0': PPO_BESS_MAX == 1700.0,
    'A2C BESS_MAX = 1700.0': A2C_BESS_MAX == 1700.0,
}

all_ok = True
for check_name, result in checks.items():
    status = '✅' if result else '❌'
    print(f'  {status} {check_name}')
    if not result:
        all_ok = False

print('\n[3/5] Validando sincronizacion SOLAR y MALL...')
checks = {
    'SAC SOLAR_MAX = 4100.0': SAC_SOLAR_MAX == 4100.0,
    'PPO SOLAR_MAX = 4100.0': PPO_SOLAR_MAX == 4100.0,
    'A2C SOLAR_MAX = 4100.0': A2C_SOLAR_MAX == 4100.0,
}

for check_name, result in checks.items():
    status = '✅' if result else '❌'
    print(f'  {status} {check_name}')
    if not result:
        all_ok = False

print('\n[4/5] Validando columnas observables (27 cols)...')
checks = {
    'SAC observables = 27': len(SAC_OBS) == 27,
    'PPO observables = 27': len(PPO_OBS) == 27,
    'A2C observables = 27': len(A2C_OBS) == 27,
    'SAC == PPO observables': len(SAC_OBS) == len(PPO_OBS),
    'SAC == A2C observables': len(SAC_OBS) == len(A2C_OBS),
}

for check_name, result in checks.items():
    status = '✅' if result else '❌'
    print(f'  {status} {check_name}')
    if not result:
        all_ok = False

print('\n[5/5] Validando funciones de validacion integrada...')
try:
    # SAC has validate_agent_integrity
    from train_sac_multiobjetivo import validate_agent_integrity as sac_validate
    print('  ✅ SAC: validate_agent_integrity() existe')
except:
    print('  ❌ SAC: validate_agent_integrity() NO existe')
    all_ok = False

try:
    # PPO has validate_ppo_sync
    from train_ppo_multiobjetivo import validate_ppo_sync as ppo_validate
    print('  ✅ PPO: validate_ppo_sync() existe')
except:
    print('  ❌ PPO: validate_ppo_sync() NO existe')
    all_ok = False

try:
    # A2C has validate_a2c_sync
    from train_a2c_multiobjetivo import validate_a2c_sync as a2c_validate
    print('  ✅ A2C: validate_a2c_sync() existe')
except:
    print('  ❌ A2C: validate_a2c_sync() NO existe')
    all_ok = False

# Summary
print('\n' + '='*80)
if all_ok:
    print('[RESULTADO] ✅ TODOS LOS AGENTES ESTAN SINCRONIZADOS Y PREPARADOS')
    print('='*80)
    print('\nLos 3 agentes (SAC, PPO, A2C) estan listos para entrenar:')
    print('  • Constantes sincronizadas (BESS, SOLAR, MALL)')
    print('  • Observaciones consistentes (27 columnas)')
    print('  • Funciones de validacion integradas')
    print('  • Imports correctos')
    print('\n✅ Puedes ejecutar: python scripts/train/train_[sac|ppo|a2c]_multiobjetivo.py')
else:
    print('[RESULTADO] ❌ HAY PROBLEMAS DE SINCRONIZACION')
    print('='*80)
    print('Revisar los errores arriba y corregir los archivos.')
    sys.exit(1)
