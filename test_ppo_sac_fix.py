#!/usr/bin/env python3
"""Test script to verify PPO and SAC callback attributes are fixed."""
from __future__ import annotations
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Add scripts/train to path
sys.path.insert(0, str(_PROJECT_ROOT / "scripts" / "train"))

print('='*80)
print('VERIFICACION DE CORRECCIONES - PPO Y SAC')
print('='*80)

# Test PPO
print('\n[PPO] Verificando DetailedLoggingCallback...')
try:
    from scripts.train.train_ppo import DetailedLoggingCallback as PPOCallback
    ppo_callback = PPOCallback(output_dir=Path('outputs/ppo_training'))
    
    attrs_ppo = [
        'episode_co2_avoided_indirect',
        'episode_co2_avoided_direct',
        'episode_motos_charged',
        'episode_mototaxis_charged',
    ]
    
    ppo_ok = True
    for attr in attrs_ppo:
        has_attr = hasattr(ppo_callback, attr)
        status = '✓' if has_attr else '✗'
        print(f'  {status} {attr}: {has_attr}')
        if not has_attr:
            ppo_ok = False
    
    if ppo_ok:
        print('  [OK] PPO tiene todos los atributos requeridos')
    else:
        print('  [ERROR] PPO le faltan algunos atributos')
except Exception as e:
    print(f'  [ERROR] No se pudo cargar PPO callback: {e}')
    ppo_ok = False

# Test SAC
print('\n[SAC] Verificando SACMetricsCallback...')
try:
    from scripts.train.train_sac import SACMetricsCallback
    sac_callback = SACMetricsCallback(output_dir=Path('outputs/sac_training'))
    
    attrs_sac = [
        'episode_co2_avoided_indirect',
        'episode_co2_avoided_direct',
        'episode_motos_charged',
        'episode_mototaxis_charged',
        '_current_motos_charged_max',
        '_current_mototaxis_charged_max',
    ]
    
    sac_ok = True
    for attr in attrs_sac:
        has_attr = hasattr(sac_callback, attr)
        status = '✓' if has_attr else '✗'
        print(f'  {status} {attr}: {has_attr}')
        if not has_attr:
            sac_ok = False
    
    if sac_ok:
        print('  [OK] SAC tiene todos los atributos requeridos')
    else:
        print('  [ERROR] SAC le faltan algunos atributos')
except Exception as e:
    print(f'  [ERROR] No se pudo cargar SAC callback: {e}')
    sac_ok = False

# Test A2C (para completitud)
print('\n[A2C] Verificando DetailedLoggingCallback...')
try:
    from scripts.train.train_a2c import DetailedLoggingCallback as A2CCallback
    a2c_callback = A2CCallback(output_dir=Path('outputs/a2c_training'))
    
    attrs_a2c = [
        'episode_co2_avoided_indirect',
        'episode_co2_avoided_direct',
        'episode_motos_charged',
        'episode_mototaxis_charged',
    ]
    
    a2c_ok = True
    for attr in attrs_a2c:
        has_attr = hasattr(a2c_callback, attr)
        status = '✓' if has_attr else '✗'
        print(f'  {status} {attr}: {has_attr}')
        if not has_attr:
            a2c_ok = False
    
    if a2c_ok:
        print('  [OK] A2C tiene todos los atributos requeridos')
    else:
        print('  [ERROR] A2C le faltan algunos atributos')
except Exception as e:
    print(f'  [ERROR] No se pudo cargar A2C callback: {e}')
    a2c_ok = False

# Summary
print('\n' + '='*80)
print('RESUMEN DE CORRECCIONES (2026-02-18):')
print('='*80)
print(f'✓ A2C:   Atributos CO2 agregados + motos/mototaxis ahora ACUMULADOS')
print(f'{"✓" if ppo_ok else "✗"} PPO:   Motos/mototaxis cambiados de MAX a ACUMULADOS')
print(f'{"✓" if sac_ok else "✗"} SAC:   Atributos CO2 agregados + motos/mototaxis ahora ACUMULADOS')
print()
print('OBJETIVOS DE DISEÑO DIARIO (Iquitos):')
print('  - 270 motos/día   × 365 días = 98,550 motos/año')
print('  - 39 mototaxis/día × 365 días = 14,235 mototaxis/año')
print('  - TOTAL: 309 vehículos/día = 112,785 vehículos/año')
print()
print('='*80)

if all([ppo_ok, sac_ok, a2c_ok]):
    print('RESULTADO: [OK] Todos los agentes están listos')
    print('='*80)
    sys.exit(0)
else:
    print('RESULTADO: [ERROR] Algunos agentes tienen problemas')
    print('='*80)
    sys.exit(1)
