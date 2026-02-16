#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico de datos SAC en result_sac.json"""
import json
from pathlib import Path

print('='*80)
print('DIAGNÓSTICO - DATOS SAC EN RESULT_SAC.JSON')
print('='*80)
print()

sac_file = Path('outputs/sac_training/result_sac.json')

print(f'[1] Verificando archivo: {sac_file}')
print()

if sac_file.exists():
    print('  ✓ Archivo encontrado')
    print(f'    Tamaño: {sac_file.stat().st_size / 1024:.2f} KB')
    print()
    
    try:
        with open(sac_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print('[2] Estructura de datos:')
        print()
        print(f'  Claves principales: {list(data.keys())}')
        print()
        
        # Revisar cada sección
        for key in data.keys():
            value = data[key]
            print(f'  [{key}]')
            if isinstance(value, dict):
                print(f'    Claves: {list(value.keys())}')
                for subkey in list(value.keys())[:5]:
                    print(f'      - {subkey}: {type(value[subkey]).__name__}')
                if len(value.keys()) > 5:
                    print(f'      ... ({len(value.keys())-5} más)')
            elif isinstance(value, list):
                print(f'    Lista con {len(value)} elementos')
                if len(value) > 0:
                    print(f'    Primer elemento: {value[0]}')
            else:
                print(f'    Valor: {value}')
            print()
        
        # Búsqueda específica de CO2
        print('[3] Búsqueda de métricas CO2:')
        print()
        
        def find_co2(obj, path=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if 'co2' in key.lower():
                        print(f'  {path}.{key} = {value}')
                    find_co2(value, f'{path}.{key}')
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:3]):  # Solo primeros 3 elementos
                    find_co2(item, f'{path}[{i}]')
        
        find_co2(data)
        
        # Resumen de datos
        print()
        print('[4] Datos disponibles para SAC:')
        print()
        
        training = data.get('training', {})
        evolution = data.get('training_evolution', {})
        summary = data.get('summary_metrics', {})
        
        print(f'  training.total_timesteps: {training.get("total_timesteps", "N/A")}')
        print(f'  training.episodes_completed: {training.get("episodes_completed", "N/A")}')
        print(f'  training_evolution claves: {list(evolution.keys())[:5]}')
        print(f'  summary_metrics claves: {list(summary.keys())[:5]}')
        
        # Comprobar si hay datos de CO2
        print()
        print('[5] Verificación de CO2:')
        total_co2 = summary.get('total_co2_avoided_kg', 0)
        print(f'  total_co2_avoided_kg: {total_co2}')
        
        if total_co2 == 0:
            print('  ⚠️ CO2 evitado es CERO')
            print()
            print('  Posibles causas:')
            print('    1. El entrenamiento de SAC no completó')
            print('    2. Los datos no se guardaron correctamente')
            print('    3. Las métricas no se calcularon')
            print()
            print('  Revisar: ¿Completó SAC el entrenamiento?')
        
    except json.JSONDecodeError as e:
        print(f'  ✗ Error al decodificar JSON: {e}')
    except Exception as e:
        print(f'  ✗ Error: {e}')
else:
    print(f'  ✗ Archivo NO encontrado: {sac_file}')
    print()
    print('  Verificando si existen entrenamientos de SAC...')
    
    sac_output = Path('outputs/sac_training')
    if sac_output.exists():
        print(f'  ✓ Directorio existe: {sac_output}')
        files = list(sac_output.glob('*'))
        print(f'    Archivos encontrados: {len(files)}')
        for f in files:
            print(f'      - {f.name}')
    else:
        print(f'  ✗ Directorio NO existe: {sac_output}')

print()
print('='*80)
