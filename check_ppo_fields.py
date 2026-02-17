#!/usr/bin/env python3
import json
from pathlib import Path

result_file = Path('outputs/ppo_training/result_ppo.json')
if result_file.exists():
    with open(result_file, 'r') as f:
        result = json.load(f)
    
    print('CAMPOS PRINCIPALES EN result_ppo.json:')
    print('=' * 80)
    for key in result:
        print(f'  - {key}')
    
    print()
    print('CAMPOS EN training_evolution:')
    print('=' * 80)
    if 'training_evolution' in result:
        for key in result['training_evolution']:
            vals = result['training_evolution'][key]
            if isinstance(vals, list):
                print(f'  - {key} ({len(vals)} valores)')
            else:
                print(f'  - {key}')
    
    print()
    print('CAMPOS EN validation:')
    print('=' * 80)
    if 'validation' in result:
        for key in result['validation']:
            val = result['validation'][key]
            print(f'  - {key}: {val}')
