#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAR DATASETS CONSTRUIDOS - VALIDAR COLUMNAS Y COMPLETITUD
Revisa si todos los datasets para A2C, PPO, SAC fueron construidos correctamente.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

print('='*80)
print('VERIFICACION DE DATASETS - COLUMNAS Y COMPLETITUD')
print('='*80)
print()

# Rutas esperadas
workspace_root = Path(__file__).parent
datasets_base = workspace_root / 'data' / 'datasets'

# Agentes esperados
agents = ['A2C', 'PPO', 'SAC']
expected_files = {
    'train': 'training_dataset.csv',
    'val': 'validation_dataset.csv',
    'test': 'test_dataset.csv',
}

print('[*] Buscando datasets en:', datasets_base)
print()

# Diccionario para guardar resultados
results = {}

for agent in agents:
    agent_dir = datasets_base / agent
    print(f'\n{"="*80}')
    print(f'AGENTE: {agent}')
    print(f'{"="*80}')
    
    if not agent_dir.exists():
        print(f'❌ ERROR: Carpeta {agent_dir} NO EXISTE')
        results[agent] = {'status': 'MISSING', 'files': {}}
        continue
    
    print(f'✓ Carpeta encontrada: {agent_dir}')
    print()
    
    agent_results = {'status': 'OK', 'files': {}}
    all_loaded = True
    
    for split_name, filename in expected_files.items():
        filepath = agent_dir / filename
        print(f'\n[{split_name.upper()}] {filename}')
        print('-' * 60)
        
        if not filepath.exists():
            print(f'  ❌ ARCHIVO NO ENCONTRADO: {filepath}')
            agent_results['files'][split_name] = {
                'exists': False,
                'rows': 0,
                'columns': [],
            }
            all_loaded = False
            continue
        
        try:
            # Cargar dataset
            df = pd.read_csv(filepath)
            
            file_info = {
                'exists': True,
                'rows': len(df),
                'columns': list(df.columns),
                'dtypes': {col: str(df[col].dtype) for col in df.columns[:10]},  # Primeras 10
                'null_count': int(df.isnull().sum().sum()),
            }
            
            agent_results['files'][split_name] = file_info
            
            # Mostrar info
            print(f'  ✓ Archivo cargado correctamente')
            print(f'    Filas: {len(df):,}')
            print(f'    Columnas: {len(df.columns)}')
            print(f'    Nulos totales: {file_info["null_count"]}')
            print(f'\n    Primeras 10 columnas:')
            for i, col in enumerate(df.columns[:10], 1):
                print(f'      {i:2d}. {col:<40s} ({df[col].dtype})')
            
            if len(df.columns) > 10:
                print(f'      ... y {len(df.columns) - 10} más')
            
        except Exception as e:
            print(f'  ❌ ERROR al cargar: {e}')
            agent_results['files'][split_name] = {
                'exists': True,
                'error': str(e),
                'rows': 0,
                'columns': [],
            }
            all_loaded = False
    
    # Resumen agente
    agent_results['all_files_loaded'] = all_loaded
    results[agent] = agent_results
    
    if all_loaded:
        print(f'\n✅ {agent}: TODOS LOS DATASETS CARGADOS CORRECTAMENTE')
    else:
        print(f'\n⚠️  {agent}: FALTAN ARCHIVOS O ERRORES')

# ===== RESUMEN GENERAL =====
print('\n\n' + '='*80)
print('RESUMEN FINAL')
print('='*80)
print()

all_ready = True
for agent in agents:
    status = results[agent].get('status', 'UNKNOWN')
    all_files = results[agent].get('all_files_loaded', False)
    
    if status == 'MISSING':
        symbol = '❌'
        all_ready = False
    elif all_files:
        symbol = '✅'
    else:
        symbol = '⚠️'
        all_ready = False
    
    print(f'{symbol} {agent:5s} - {status}')

print()
if all_ready:
    print('🎉 TODOS LOS DATASETS ESTÁN LISTOS PARA ENTRENAR')
else:
    print('⚠️  REVISAR ERRORES ANTES DE ENTRENAR')

print()
print('='*80)
