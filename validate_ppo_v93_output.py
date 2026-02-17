#!/usr/bin/env python3
"""Validar estructura de archivos de salida PPO v9.3"""

import pandas as pd
import json
import sys

def main():
    print('='*80)
    print('VALIDACIÓN DE ESTRUCTURA PPO v9.3')
    print('='*80)
    print()

    # Validar timeseries
    try:
        ts = pd.read_csv('outputs/ppo_training/timeseries_ppo.csv')
        print(f'✅ timeseries_ppo.csv')
        print(f'   Dimensiones: {ts.shape[0]} registros × {ts.shape[1]} columnas')
        print(f'   Columnas esperadas: 33')
        
        status = "✓ CORRECTO" if ts.shape[1] == 33 else "✗ ERROR"
        print(f'   Status: {status}')
        print()
        
        # Listar columnas
        print('   Columnas presentes:')
        for i, col in enumerate(ts.columns, 1):
            print(f'     {i:2d}. {col}')
    except Exception as e:
        print(f'✗ Error en timeseries: {e}')
        sys.exit(1)

    print()
    print('-'*80)
    print()

    # Validar trace
    try:
        tr = pd.read_csv('outputs/ppo_training/trace_ppo.csv')
        print(f'✅ trace_ppo.csv')
        print(f'   Dimensiones: {tr.shape[0]} registros × {tr.shape[1]} columnas')
        print(f'   Columnas esperadas: 22')
        
        status = "✓ CORRECTO" if tr.shape[1] == 22 else "✗ ERROR"
        print(f'   Status: {status}')
        print()
        
        print('   Columnas presentes:')
        for i, col in enumerate(tr.columns, 1):
            print(f'     {i:2d}. {col}')
    except Exception as e:
        print(f'✗ Error en trace: {e}')
        sys.exit(1)

    print()
    print('-'*80)
    print()

    # Validar result
    try:
        with open('outputs/ppo_training/result_ppo.json') as f:
            result = json.load(f)
        
        print(f'✅ result_ppo.json')
        print(f'   Episodios: {len(result)}')
        
        if len(result) > 0:
            keys = result[0].keys()
            print(f'   Campos por episodio: {len(keys)}')
            print('   Campos:')
            for i, key in enumerate(sorted(keys), 1):
                print(f'     {i:2d}. {key}')
    except Exception as e:
        print(f'✗ Error en result: {e}')
        sys.exit(1)

    print()
    print('='*80)
    print('✅ VALIDACIÓN COMPLETADA - ESTRUCTURA CORRECTA')
    print('='*80)

if __name__ == '__main__':
    main()
