#!/usr/bin/env python3
"""
AUDITORÍA Y LIMPIEZA: Identificar archivos innecesarios y reorganizar para producción
===================================================================================

Escanea la raíz del proyecto para identificar:
1. Archivos .py sueltos que son solo debugging/testing
2. Archivos .md documentación temporal
3. Logs y archivos temporales
4. Lo que DEBE mantenerse para producción
"""

from pathlib import Path
from collections import defaultdict
import sys

def audit_project():
    """Auditoría del estado del proyecto"""
    
    print('\n' + '='*100)
    print('🔍 AUDITORÍA: Archivos en la raíz que pueden ser limpiados')
    print('='*100 + '\n')
    
    root = Path('.')
    
    # Categorías de archivos
    categories = {
        'TESTING/DEBUG SCRIPTS': [],
        'TEMPORAL DOCUMENTATION': [],
        'TEMP LOGS': [],
        'ESSENTIAL KEEP': [],
        'PRODUCTION DATA': [],
        'CONFIGS': []
    }
    
    # Patrones a eliminar
    debug_patterns = [
        'analisis_', 'check_', 'cleanup_', 'compare_', 'create_unified_',
        'final_cleanup_', 'launch_ppo_', 'regenerate_', 'run_a2c_',
        'test_', 'validate_', 'verify_', 'visualize_', '_build_',
        'cargar_27_', 'monitorear_'
    ]
    
    temp_doc_patterns = [
        'AJUSTE_', 'CAMBIOS_', 'CHECKLIST_', 'CONSOLIDACION_',
        'DESGLOSE_', 'ENTREGA_', 'ESTADO_', 'ENTRENAMIENTO_PPO_',
        'FIX_', 'FLUJO_', 'INDICE_', 'INICIO_', 'LIMPIEZA_',
        'LISTA_', 'MAPA_', 'PEAK_', 'PROGRESO_', 'REAL_',
        'REPORTE_', 'RESPUESTA_', 'RESUMEN_', 'SISTEMA_',
        'VERIFICACION_'
    ]
    
    keep_files = [
        'README.md', 'pyproject.toml', 'setup.py', 'requirements.txt',
        'requirements-training.txt', 'requirements-citylearn-v2.txt',
        'pyrightconfig.json', 'py.typed', '.gitignore',
        'Dockerfile', 'Dockerfile.fastapi', 'docker-compose.yml',
        'docker-compose.dev.yml', 'docker-compose.fastapi.yml',
        'docker-compose.gpu.yml', 'docker-entrypoint.sh',
        '.github', '.vscode', '.venv', '.pytest_cache', '.mypy_cache',
        'activate_env_auto.ps1'
    ]
    
    # Escanear archivos
    print('📋 ARCHIVOS ENCONTRADOS:\n')
    
    for file in sorted(root.glob('*')):
        if file.is_dir():
            continue
        
        name = file.name
        size_kb = file.stat().st_size / 1024
        
        # Categorizar
        if name.endswith('.py'):
            is_debug = any(name.startswith(p) for p in debug_patterns)
            if is_debug:
                categories['TESTING/DEBUG SCRIPTS'].append((name, size_kb))
            elif name in keep_files:
                categories['ESSENTIAL KEEP'].append((name, size_kb))
            else:
                categories['TESTING/DEBUG SCRIPTS'].append((name, size_kb))
        
        elif name.endswith('.md'):
            is_temp = any(name.startswith(p) for p in temp_doc_patterns)
            if is_temp:
                categories['TEMPORAL DOCUMENTATION'].append((name, size_kb))
            elif name == 'README.md':
                categories['ESSENTIAL KEEP'].append((name, size_kb))
            else:
                categories['TEMPORAL DOCUMENTATION'].append((name, size_kb))
        
        elif name.endswith('.log') or name.endswith('.txt'):
            if 'train_ppo' in name or 'train_' in name:
                categories['TEMP LOGS'].append((name, size_kb))
            else:
                categories['PRODUCTION DATA'].append((name, size_kb))
        
        elif name in keep_files or name.startswith('.'):
            categories['ESSENTIAL KEEP'].append((name, size_kb))
        
        elif name.endswith('.yml') or name.endswith('.yaml'):
            categories['CONFIGS'].append((name, size_kb))
        
        elif name.startswith('docker') or name.endswith('.sh'):
            categories['ESSENTIAL KEEP'].append((name, size_kb))
        
        else:
            categories['PRODUCTION DATA'].append((name, size_kb))
    
    # Mostrar resultados
    total_cleanup_kb = 0
    
    for category, files in categories.items():
        if not files:
            continue
        
        print(f'\n{category}:')
        print('-' * 100)
        
        category_size = 0
        for name, size_kb in files:
            print(f'  • {name:50s} {size_kb:10.2f} KB')
            category_size += size_kb
            if 'TESTING' in category or 'TEMPORAL' in category or 'TEMP' in category:
                total_cleanup_kb += size_kb
        
        print(f'  {"SUBTOTAL":50s} {category_size:10.2f} KB')
    
    # Recomendaciones
    print('\n' + '='*100)
    print('💡 RECOMENDACIONES PARA PRODUCCIÓN')
    print('='*100 + '\n')
    
    print('🗑️  ELIMINAR (total ahorro: {:.1f} KB):'.format(total_cleanup_kb))
    print('-' * 100)
    
    if categories['TESTING/DEBUG SCRIPTS']:
        print('\n  Debugging scripts (.py):')
        for name, _ in categories['TESTING/DEBUG SCRIPTS']:
            print(f'    - rm {name}')
    
    if categories['TEMPORAL DOCUMENTATION']:
        print('\n  Temporary docs (.md):')
        for name, _ in categories['TEMPORAL DOCUMENTATION'][:5]:
            print(f'    - rm {name}')
        if len(categories['TEMPORAL DOCUMENTATION']) > 5:
            print(f'    ... y {len(categories["TEMPORAL DOCUMENTATION"])-5} más')
    
    if categories['TEMP LOGS']:
        print('\n  Training logs (archivados, no necesarios):')
        for name, _ in categories['TEMP LOGS'][:3]:
            print(f'    - rm {name}')
        if len(categories['TEMP LOGS']) > 3:
            print(f'    ... y {len(categories["TEMP LOGS"])-3} más')
    
    print('\n\n✅ MANTENER PARA PRODUCCIÓN:')
    print('-' * 100)
    print(f'\n  Estructura mínima viable:')
    print(f'    📁 src/                      - Código fuente (OE2, OE3, modelos)')
    print(f'    📁 scripts/                  - Scripts de entrenamiento (train_*.py)')
    print(f'    📁 configs/                  - Configuración (default.yaml, etc)')
    print(f'    📁 data/                     - Datos (OE2, OE3, interim, processed)')
    print(f'    📁 outputs/                  - Resultados de entrenamientos')
    print(f'    📁 checkpoints/              - Modelos guardados')
    print(f'    📄 pyproject.toml            - Configuración pip/poetry')
    print(f'    📄 requirements*.txt         - Dependencias')
    print(f'    📄 README.md                 - Documentación principal')
    print(f'    🐳 Dockerfile*               - Containerización')
    
    print('\n\n🎯 ESTRUCTURA PRODUCCIÓN LIMPIA:')
    print('-' * 100)
    print('''
    diseñopvbesscar/
    ├── src/                          ← Código principal (OE2, OE3, rewards, etc)
    ├── scripts/
    │   ├── train/                    ← Solo train_ppo.py, train_sac.py, train_a2c.py
    │   ├── verify_oe2_data.py        ← Validación (una sola)
    │   └── benchmark_ppo.py          ← Benchmark (una sola)
    ├── configs/
    │   └── default.yaml
    ├── data/
    │   ├── oe2/                      ← Datos reales OE2
    │   ├── processed/
    │   └── interim/
    ├── outputs/                      ← Resultados
    ├── checkpoints/                  ← Modelos
    ├── pyproject.toml
    ├── requirements.txt
    └── README.md
    
    Total archivos raíz: ~15 (vs ~100 con todos los .py y .md sueltos)
    ''')
    
    print('\n' + '='*100 + '\n')

if __name__ == '__main__':
    audit_project()
