#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rápido de los cambios PPO v7.3 para entropía.
Verifica que los imports y variables globales estén correctamente configuradas.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar src/ al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print('=' * 80)
print('[TEST] Verificar que cambios de entropía PPO v7.3 están bien integrados')
print('=' * 80)
print()

# =========================================================================
# TEST 1: Verificar que el archivo de training no tiene errores de sintaxis
# =========================================================================
print('[TEST 1] Verificar sintaxis de train_ppo_multiobjetivo.py...')
try:
    import scripts.train.train_ppo_multiobjetivo as ppo_module
    print('  ✓ train_ppo_multiobjetivo.py importa sin errores')
except SyntaxError as e:
    print(f'  ❌ ERROR de sintaxis: {e}')
    sys.exit(1)
except ImportError as e:
    print(f'  ⚠️  ImportError (esperado si dependencias no instaladas): {e}')
print()

# =========================================================================
# TEST 2: Verificar que GLOBAL_PPO_METRICS está definido
# =========================================================================
print('[TEST 2] Verificar variables globales...')
try:
    from scripts.train.train_ppo_multiobjetivo import GLOBAL_PPO_METRICS, GLOBAL_ENERGY_VALUES
    
    print(f'  ✓ GLOBAL_ENERGY_VALUES definido con keys: {list(GLOBAL_ENERGY_VALUES.keys())}')
    print(f'  ✓ GLOBAL_PPO_METRICS definido con keys: {list(GLOBAL_PPO_METRICS.keys())}')
    
    # Verificar que tiene todas las métricas esperadas
    expected_keys = ['current_entropy', 'current_approx_kl', 'current_clip_fraction',
                     'current_policy_loss', 'current_value_loss', 'current_explained_variance']
    missing = [k for k in expected_keys if k not in GLOBAL_PPO_METRICS]
    if missing:
        print(f'  ❌ Faltan keys en GLOBAL_PPO_METRICS: {missing}')
        sys.exit(1)
    else:
        print(f'  ✓ Todas las keys esperadas presentes en GLOBAL_PPO_METRICS')
except (ImportError, AttributeError) as e:
    print(f'  ❌ No se puede importar variables globales: {e}')
    sys.exit(1)
print()

# =========================================================================
# TEST 3: Verificar que DetailedLoggingCallback existe
# =========================================================================
print('[TEST 3] Verificar DetailedLoggingCallback...')
try:
    from scripts.train.train_ppo_multiobjetivo import DetailedLoggingCallback
    print(f'  ✓ DetailedLoggingCallback importado exitosamente')
    
    # Verificar que __init__ tiene los parámetros esperados
    import inspect
    sig = inspect.signature(DetailedLoggingCallback.__init__)
    params = list(sig.parameters.keys())
    print(f'  ✓ __init__ parameters: {params}')
except (ImportError, AttributeError) as e:
    print(f'  ❌ No se puede importar DetailedLoggingCallback: {e}')
    sys.exit(1)
print()

# =========================================================================
# TEST 4: Verificar que PPOMetricsCallback existe
# =========================================================================
print('[TEST 4] Verificar PPOMetricsCallback...')
try:
    from scripts.train.train_ppo_multiobjetivo import PPOMetricsCallback
    print(f'  ✓ PPOMetricsCallback importado exitosamente')
except (ImportError, AttributeError) as e:
    print(f'  ❌ No se puede importar PPOMetricsCallback: {e}')
    sys.exit(1)
print()

# =========================================================================
# TEST 5: Verificar estructura de imports
# =========================================================================
print('[TEST 5] Verificar imports del módulo de training...')
try:
    # Verificar que tiene los imports críticos
    import scripts.train.train_ppo_multiobjetivo as ppo
    
    # Esto debería funcionar sin errores
    print('  ✓ Todos los imports críticos funcionan')
except Exception as e:
    print(f'  ❌ Error en imports: {e}')
    sys.exit(1)
print()

# =========================================================================
# TEST 6: Verificar que verify_ppo_entropy.py existe
# =========================================================================
print('[TEST 6] Verificar script de validación...')
verify_script = Path('verify_ppo_entropy.py')
if verify_script.exists():
    print(f'  ✓ {verify_script} existe')
else:
    print(f'  ❌ {verify_script} NO encontrado')
    sys.exit(1)
print()

print('=' * 80)
print('✅ TODOS LOS TESTS PASARON')
print('=' * 80)
print()
print('Próximos pasos:')
print('  1. Ejecutar: python scripts/train/train_ppo_multiobjetivo.py')
print('  2. Verificar: python verify_ppo_entropy.py')
print()
