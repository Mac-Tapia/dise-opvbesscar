#!/usr/bin/env python3
"""Test script to verify A2C callback attributes are fixed."""
from __future__ import annotations
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.train.train_a2c import DetailedLoggingCallback

print('='*80)
print('VERIFICACION DE CORRECCIONES A2C - ATRIBUTOS DE CALLBACK')
print('='*80)

# Crear callback
callback = DetailedLoggingCallback(output_dir=Path('outputs/a2c_training'))

# Verificar atributos
print('\n✓ Atributos de callback:')
attrs = [
    'episode_co2_avoided_indirect',
    'episode_co2_avoided_direct',
    'episode_motos_charged',
    'episode_mototaxis_charged',
    'episode_grid_stability',
    'episode_cost_usd',
    'episode_bess_discharge_kwh',
    'episode_bess_charge_kwh',
]

all_ok = True
for attr in attrs:
    has_attr = hasattr(callback, attr)
    status = '✓' if has_attr else '✗'
    print(f'  {status} {attr}: {has_attr}')
    if not has_attr:
        all_ok = False

print('\n✓ Valores iniciales (deben estar vacíos):')
print(f'  - episode_motos_charged: {len(callback.episode_motos_charged)} elementos')
print(f'  - episode_mototaxis_charged: {len(callback.episode_mototaxis_charged)} elementos')
print(f'  - episode_co2_avoided_indirect: {len(callback.episode_co2_avoided_indirect)} elementos')
print(f'  - episode_co2_avoided_direct: {len(callback.episode_co2_avoided_direct)} elementos')

print('\n✓ Objetivos de diseño DIARIOS (Iquitos):')
print(f'  - Motos: 270 unidades/día')
print(f'  - Mototaxis: 39 unidades/día')
print(f'  - TOTAL ANUAL: {(270+39)*365} vehículos/año')

print('\n' + '='*80)
if all_ok:
    print('RESULTADO: [OK] Todos los atributos están presentes y correctos')
    print('='*80)
    sys.exit(0)
else:
    print('RESULTADO: [ERROR] Faltan algunos atributos')
    print('='*80)
    sys.exit(1)
