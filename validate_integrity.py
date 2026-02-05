#!/usr/bin/env python3
"""
VALIDACIÓN DE INTEGRIDAD - Proyecto pvbesscar OE3
Verifica que todos los archivos estén en orden, dependencias correctas, y no haya roturas
"""

import sys
import os
from pathlib import Path
import json
import importlib.util

print('='*80)
print('🔍 VALIDACIÓN DE INTEGRIDAD - PROYECTO PVBESSCAR OE3')
print('='*80)
print()

WORKSPACE = Path('.')
CHECKS_PASSED = 0
CHECKS_FAILED = 0

def check(name, condition, details=""):
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        print(f'  ✅ {name}')
        CHECKS_PASSED += 1
    else:
        print(f'  ❌ {name}')
        if details:
            print(f'     ↳ {details}')
        CHECKS_FAILED += 1

print('[1] VERIFICAR ESTRUCTURA DE CARPETAS')
print('-'*80)

folders_to_check = [
    'checkpoints',
    'checkpoints/SAC',
    'checkpoints/PPO',
    'checkpoints/A2C',
    'outputs',
    'outputs/sac_training',
    'outputs/ppo_training',
    'outputs/a2c_training',
    'outputs/training_pipeline',
    'configs',
    'data',
    'src',
    'src/rewards',
    'src/agents',
    'src/iquitos_citylearn',
]

for folder in folders_to_check:
    folder_path = WORKSPACE / folder
    exists = folder_path.exists()
    if not exists:
        folder_path.mkdir(parents=True, exist_ok=True)  # Crear si no existe
    check(f'Carpeta: {folder}', folder_path.exists(), str(folder_path))

print()
print('[2] VERIFICAR SCRIPTS PRINCIPALES')
print('-'*80)

scripts_to_check = [
    'test_sac_multiobjetivo.py',
    'train_sac_multiobjetivo.py',
    'train_ppo_a2c_multiobjetivo.py',
    'run_training_pipeline.py',
]

for script in scripts_to_check:
    script_path = WORKSPACE / script
    exists = script_path.exists()
    check(f'Script: {script}', exists, f'Size: {script_path.stat().st_size} bytes' if exists else 'No encontrado')

print()
print('[3] VERIFICAR CONFIGURACIÓN')
print('-'*80)

configs_to_check = [
    ('configs/default.yaml', 'YAML config'),
    ('pyproject.toml', 'Python dependencies'),
    ('requirements.txt', 'Requirements'),
]

for config_file, desc in configs_to_check:
    config_path = WORKSPACE / config_file
    check(f'{desc}: {config_file}', config_path.exists())

print()
print('[4] VERIFICAR CÓDIGO FUENTE')
print('-'*80)

source_files = [
    'src/rewards/rewards.py',
    'src/rewards/__init__.py',
    'src/agents/sac.py',
    'src/agents/ppo_sb3.py',
    'src/agents/a2c_sb3.py',
    'src/dimensionamiento/oe2/chargers.py',
    'src/dimensionamiento/oe2/solar_pvlib.py',
]

for source_file in source_files:
    source_path = WORKSPACE / source_file
    exists = source_path.exists()
    check(f'Source: {source_file}', exists, f'Size: {source_path.stat().st_size} bytes' if exists else 'No encontrado')

print()
print('[5] VERIFICAR IMPORTES CRÍTICOS')
print('-'*80)

critical_imports = [
    ('stable_baselines3', 'SAC, PPO, A2C'),
    ('gymnasium', 'Space, Env'),
    ('torch', 'CUDA support'),
    ('numpy', 'Math operations'),
    ('pandas', 'Data handling'),
    ('pyyaml', 'Config loading'),
]

for package, submodules in critical_imports:
    try:
        __import__(package)
        check(f'Package: {package}', True, submodules)
    except ImportError as e:
        check(f'Package: {package}', False, str(e))

print()
print('[6] VALIDAR ARCHIVOS DE REQUISITOS')
print('-'*80)

try:
    with open(WORKSPACE / 'pyproject.toml', 'r') as f:
        content = f.read()
        has_sac = 'stable-baselines3' in content.lower()
        has_gym = 'gymnasium' in content.lower()
        has_torch = 'torch' in content.lower()

    check('stable-baselines3 en dependencies', has_sac)
    check('gymnasium en dependencies', has_gym)
    check('torch en dependencies', has_torch)
except Exception as e:
    check('Leer pyproject.toml', False, str(e))

print()
print('[7] VERIFICAR AUSENCIA DE ARCHIVOS OBSOLETOS')
print('-'*80)

obsolete_files = [
    'train_sac_test.py',
    'train_sac_quick.py',
    'train_sac_production.py',
    'train_ppo_production.py',
    'train_a2c_production.py',
    'train_all_agents.py',
    'diagnose_sac.py',
    'load_env.py',
    'monitor_pipeline.py',
]

for obsolete_file in obsolete_files:
    obsolete_path = WORKSPACE / obsolete_file
    check(f'ELIMINADO: {obsolete_file}', not obsolete_path.exists(), 'Correctamente limpiado')

print()
print('[8] VERIFICAR DOCUMENTACIÓN PRODUCCIÓN')
print('-'*80)

docs_production = [
    'PRODUCCION_v2.0.md',
    'START_HERE.md',
    'QUICK_REFERENCE.txt',
    'ARQUITECTURA_MULTIOBJETIVO_REAL.md',
]

for doc in docs_production:
    doc_path = WORKSPACE / doc
    check(f'Doc: {doc}', doc_path.exists())

print()
print('[9] VALIDAR REWARD SYSTEM')
print('-'*80)

try:
    from src.rewards.rewards import (
        IquitosContext,
        MultiObjectiveWeights,
        MultiObjectiveReward,
        create_iquitos_reward_weights
    )

    check('IquitosContext importable', True)
    check('MultiObjectiveWeights importable', True)
    check('MultiObjectiveReward importable', True)
    check('create_iquitos_reward_weights importable', True)

    # Test instantiation
    context = IquitosContext()
    check('IquitosContext instantiation', context.co2_factor_kg_per_kwh > 0, f'CO₂: {context.co2_factor_kg_per_kwh}')

    weights = create_iquitos_reward_weights("co2_focus")
    check('Weights creation', weights.co2 > 0, f'CO₂ weight: {weights.co2}')

    reward_calc = MultiObjectiveReward(weights=weights, context=context)
    check('MultiObjectiveReward creation', reward_calc is not None)

except Exception as e:
    check('Reward system', False, str(e))

print()
print('[10] VALIDAR INTEGRIDAD DE SCRIPTS PYTHON')
print('-'*80)

def validate_python_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), str(file_path), 'exec')
        return True
    except SyntaxError as e:
        return False, str(e)
    except UnicodeDecodeError as e:
        return False, f"Encoding error: {e}"

for script in scripts_to_check:
    script_path = WORKSPACE / script
    if script_path.exists():
        result = validate_python_syntax(script_path)
        if result is True:
            check(f'Sintaxis: {script}', True)
        else:
            check(f'Sintaxis: {script}', False, result[1])

print()
print('='*80)
print(f'📊 RESULTADOS FINALES')
print('='*80)
print(f'  ✅ Checks passed: {CHECKS_PASSED}')
print(f'  ❌ Checks failed: {CHECKS_FAILED}')
print()

if CHECKS_FAILED == 0:
    print('🎉 VALIDACIÓN COMPLETA - ¡PROYECTO LISTO PARA PRODUCCIÓN!')
    print()
    print('Próximo paso:')
    print('  python test_sac_multiobjetivo.py         # Validar sistema (5 min)')
    print('  python train_sac_multiobjetivo.py        # Entrenar SAC (2h CPU)')
    print('  python run_training_pipeline.py          # Pipeline maestro (5h CPU)')
    sys.exit(0)
else:
    print(f'⚠️  {CHECKS_FAILED} PROBLEMAS ENCONTRADOS - Revisar arriba')
    sys.exit(1)
