#!/usr/bin/env python3
"""
DIAGNÓSTICO INTEGRAL DEL PIPELINE
Revisa toda la cadena: Dataset → Agents → Training
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import traceback
import importlib.util
import json

print('='*80)
print('DIAGNÓSTICO INTEGRAL DEL PROYECTO - pvbesscar')
print('='*80)
print()

# ============================================================================
# FASE 1: VERIFICAR ESTRUCTURA DE ARCHIVOS CRÍTICOS
# ============================================================================
print('FASE 1: ESTRUCTURA DE ARCHIVOS CRÍTICOS')
print('-'*80)

required_files = {
    'Dataset Builder': [
        'src/iquitos_citylearn/oe3/dataset_builder_consolidated.py',
        'src/dimensionamiento/oe2/data_loader.py',
        'src/dimensionamiento/oe2/chargers.py',
    ],
    'Agents': [
        'src/agents/sac.py',
        'src/agents/ppo_sb3.py',
        'src/agents/a2c_sb3.py',
    ],
    'Utils': [
        'src/utils/agent_utils.py',
        'src/progress.py',
    ],
    'Scripts': [
        'scripts/run_oe3_simulate.py',
    ],
    'Config': [
        'configs/default.yaml',
    ]
}

missing_files = []
found_files = []
file_sizes = {}

for category, files in required_files.items():
    print(f'\n{category}:')
    for filepath_item in files:
        path = Path(filepath_item)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            file_sizes[filepath_item] = size_kb
            print(f'  ✓ {filepath_item} ({size_kb:.1f} KB)')
            found_files.append(filepath_item)
        else:
            print(f'  ✗ MISSING: {filepath_item}')
            missing_files.append(filepath_item)

print(f'\n\nRESULTADO: {len(found_files)}/{len([f for files in required_files.values() for f in files])} archivos encontrados')
if missing_files:
    print(f'⚠️  ARCHIVOS CRÍTICOS FALTANTES ({len(missing_files)}):')
    for filename in missing_files:
        print(f'  - {filename}')
else:
    print('✅ Todos los archivos críticos presentes')

# ============================================================================
# FASE 2: VERIFICAR IMPORTS Y DEPENDENCIAS
# ============================================================================
print('\n' + '='*80)
print('FASE 2: VERIFICAR IMPORTS Y DEPENDENCIAS')
print('-'*80)

critical_imports = {
    'src/agents/sac.py': ['from src.progress import', 'from src.agents.metrics_extractor import'],
    'src/agents/ppo_sb3.py': ['from src.progress import', 'from src.agents.metrics_extractor import'],
    'src/agents/a2c_sb3.py': ['from src.progress import', 'from src.agents.metrics_extractor import'],
}

import_issues: List[tuple[str, str]] = []

for filepath, required_imports in critical_imports.items():
    if not Path(filepath).exists():
        print(f'\n✗ {filepath} NO EXISTE')
        continue

    print(f'\n{filepath}:')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Verificar cada import requerido
            for req_import in required_imports:
                if req_import not in content:
                    import_issues.append((filepath, req_import))
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
            # Verificar cada import requerido
            for req_import in required_imports:
                if req_import not in content:
                    import_issues.append((filepath, req_import))

if import_issues:
    print(f'\n⚠️  PROBLEMAS DE IMPORTS ({len(import_issues)})')
    for filepath, imp in import_issues:
        print(f'  - {filepath}: falta {imp}')
else:
    print('\n✅ Todos los imports críticos presentes')

# ============================================================================
# FASE 3: VERIFICAR ARCHIVOS DE CONFIGURACIÓN
# ============================================================================
print('\n' + '='*80)
print('FASE 3: VERIFICAR ARCHIVOS DE CONFIGURACIÓN')
print('-'*80)

config_files = [
    'configs/default.yaml',
    'pyproject.toml',
    '.env',
]

print('\nArchivos de configuración:')
for cf in config_files:
    if Path(cf).exists():
        size_kb = Path(cf).stat().st_size / 1024
        print(f'  ✓ {cf} ({size_kb:.1f} KB)')
    else:
        print(f'  - {cf} (NO EXISTE - OPCIONAL)')

# ============================================================================
# FASE 4: VERIFICAR DIRECTORIOS DE DATOS
# ============================================================================
print('\n' + '='*80)
print('FASE 4: VERIFICAR DIRECTORIOS DE DATOS')
print('-'*80)

data_dirs = {
    'OE2 Input': 'data/interim/oe2',
    'OE3 Output': 'data/interim/oe3',
    'Checkpoints': 'checkpoints',
    'Outputs': 'outputs',
    'Logs': 'logs',
}

print('\nDirectorios:')
for name, dirpath in data_dirs.items():
    if Path(dirpath).exists():
        is_dir = Path(dirpath).is_dir()
        if is_dir:
            num_files = len(list(Path(dirpath).glob('*')))
            print(f'  ✓ {dirpath} ({num_files} items)')
        else:
            print(f'  ✗ {dirpath} NO ES DIRECTORIO')
    else:
        print(f'  - {dirpath} (no existe)')

# ============================================================================
# FASE 5: VERIFICAR DATASET DE ENTRENAMIENTO
# ============================================================================
print('\n' + '='*80)
print('FASE 5: VERIFICAR DATASET DE ENTRENAMIENTO')
print('-'*80)

dataset_path = Path('data/interim/oe3')
if dataset_path.exists():
    schema_path = dataset_path / 'schema.json'
    charger_dir = dataset_path / 'chargers'

    print('\nDataset OE3:')
    if schema_path.exists():
        try:
            with open(schema_path, 'r', encoding='utf-8') as schema_file:
                schema = json.load(schema_file)
            print(f'  ✓ schema.json ({schema_path.stat().st_size / 1024:.1f} KB)')
            print(f'    - Version: {schema.get("version", "UNKNOWN")}')
            print(f'    - Buildings: {len(schema.get("buildings", []))} building(s)')
            print(f'    - Climate zones: {len(schema.get("climate_zones", {}))} zone(s)')
        except Exception as e:
            print(f'  ✗ schema.json CORRUPTO: {e}')
    else:
        print(f'  ✗ schema.json NO ENCONTRADO')

    if charger_dir.exists():
        charger_files = list(charger_dir.glob('*.csv'))
        print(f'  ✓ {len(charger_files)} charger CSV files')
        if len(charger_files) != 128:
            print(f'    ⚠️  ADVERTENCIA: Se esperaban 128, encontrados {len(charger_files)}')
    else:
        print(f'  - Charger directory no existe')
else:
    print(f'✗ Dataset directory ({dataset_path}) NO EXISTE')

# ============================================================================
# FASE 6: VERIFICAR REQUISITOS DE PYTHON
# ============================================================================
print('\n' + '='*80)
print('FASE 6: VERIFICAR REQUISITOS DE PYTHON')
print('-'*80)

required_packages = {
    'gymnasium': 'RL environment',
    'numpy': 'Numerical computing',
    'pandas': 'Data manipulation',
    'torch': 'Deep learning (optional)',
    'stable_baselines3': 'RL algorithms',
    'pyyaml': 'Config files',
}

print('\nPaquetes requeridos:')
missing_packages = []
for pkg, desc in required_packages.items():
    try:
        spec = importlib.util.find_spec(pkg)
        if spec is not None:
            print(f'  ✓ {pkg} ({desc})')
        else:
            print(f'  ✗ {pkg} NO ENCONTRADO')
            missing_packages.append(pkg)
    except ImportError:
        print(f'  ✗ {pkg} NO ENCONTRADO')
        missing_packages.append(pkg)

if missing_packages:
    print(f'\n⚠️  PAQUETES FALTANTES ({len(missing_packages)}):')
    for pkg in missing_packages:
        print(f'  - {pkg}')
else:
    print('\n✅ Todos los paquetes requeridos instalados')

# ============================================================================
# FASE 7: RESUMEN FINAL
# ============================================================================
print('\n' + '='*80)
print('RESUMEN FINAL')
print('-'*80)

issues_found = len(missing_files) + len(import_issues) + len(missing_packages)

if issues_found == 0:
    print('✅ DIAGNÓSTICO EXITOSO - Sistema listo para entrenamiento')
else:
    print(f'⚠️  PROBLEMAS ENCONTRADOS: {issues_found}')
    print(f'  - Archivos faltantes: {len(missing_files)}')
    print(f'  - Imports incompletos: {len(import_issues)}')
    print(f'  - Paquetes faltantes: {len(missing_packages)}')

print('\n' + '='*80)
print('FIN DEL DIAGNÓSTICO')
print('='*80)
