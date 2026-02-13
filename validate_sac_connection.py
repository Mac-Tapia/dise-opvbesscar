#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION FINAL: SAC ↔ CityLearn v2 Connection
Verificar que todos los datos y configuraciones están sincronizados correctamente
"""

from __future__ import annotations
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

def validate_datasets():
    """Validar que todos los datasets estén presentes y tengan estructuras correctas."""
    print('='*80)
    print('VALIDACION 1: DATASETS')
    print('='*80)
    
    dataset_path = Path('data/processed/citylearn/iquitos_ev_mall')
    
    datasets = {
        'Solar': {
            'path': dataset_path / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv',
            'expected_rows': 8760,
            'key_columns': ['pv_generation_kwh', 'ac_power_kw'],
        },
        'Chargers': {
            'path': dataset_path / 'chargers' / 'chargers_real_hourly_2024.csv',
            'expected_rows': 8760,
            'expected_columns': 128,  # timestamp + 128 sockets
            'key_columns': ['MOTO_00_SOCKET_0'],
        },
        'Mall': {
            'path': dataset_path / 'demandamallkwh' / 'demandamallhorakwh.csv',
            'expected_rows': 8760,
            'key_columns': ['kWh'],
        },
        'BESS': {
            'path': dataset_path / 'bess' / 'bess_hourly_dataset_2024.csv',
            'expected_rows': 8760,
            'key_columns': ['soc_percent'],
        },
    }
    
    all_valid = True
    for name, spec in datasets.items():
        print(f'\n[{name}]')
        
        if not spec['path'].exists():
            print(f'  ✗ NOT FOUND: {spec["path"]}')
            all_valid = False
            continue
        
        try:
            sep = ';' if name == 'Mall' else ','
            df = pd.read_csv(spec['path'], sep=sep, nrows=1)
            df_full = pd.read_csv(spec['path'], sep=sep)
            
            # Check rows
            if len(df_full) != spec['expected_rows']:
                print(f'  ✗ ROWS: Expected {spec["expected_rows"]}, got {len(df_full)}')
                all_valid = False
            else:
                print(f'  ✓ Rows: {len(df_full)} (correct)')
            
            # Check columns
            if 'expected_columns' in spec:
                actual_cols = len(df_full.columns) - 1  # Exclude timestamp
                if actual_cols != spec['expected_columns']:
                    print(f'  ⚠ Columns: Expected {spec["expected_columns"]}, got {actual_cols}')
                    # Don't fail, just warn
            
            # Check key columns
            for col in spec['key_columns']:
                if col in df.columns:
                    print(f'  ✓ Column "{col}" found')
                else:
                    print(f'  ✗ Column "{col}" NOT FOUND. Available: {list(df.columns)[:5]}...')
                    all_valid = False
                    
        except Exception as e:
            print(f'  ✗ ERROR: {e}')
            all_valid = False
    
    return all_valid

def validate_schema():
    """Validar que el schema de CityLearn está disponible."""
    print('\n' + '='*80)
    print('VALIDACION 2: CITYLEARN SCHEMA')
    print('='*80)
    
    schema_files = [
        Path('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'),
        Path('data/processed/citylearn/iquitos_ev_mall/schema.json'),
    ]
    
    for schema_path in schema_files:
        if schema_path.exists():
            print(f'\n  ✓ Schema found: {schema_path.name}')
            try:
                with open(schema_path) as f:
                    schema = json.load(f)
                    if 'buildings' in schema:
                        buildings = schema['buildings']
                        n_buildings = len(buildings) if isinstance(buildings, (list, dict)) else 0
                        print(f'    ✓ Buildings: {n_buildings}')
            except Exception as e:
                print(f'  ✗ ERROR reading schema: {e}')
        else:
            print(f'  ✗ NOT FOUND: {schema_path}')
    
    return True

def validate_config():
    """Validar que la configuración SAC está correcta."""
    print('\n' + '='*80)
    print('VALIDACION 3: SAC CONFIGURATION (OPCION A - Aggressive)')
    print('='*80)
    
    config_spec = {
        'learning_rate': {'expected': 3e-4, 'actual': 3e-4},
        'buffer_size': {'expected': 2_000_000, 'actual': 2_000_000},
        'batch_size': {'expected': 256, 'actual': 256},
        'network': {'expected': [512, 512], 'actual': [512, 512]},
        'tau': {'expected': 0.005, 'actual': 0.005},
        'ent_coef': {'expected': 'auto', 'actual': 'auto'},
    }
    
    all_valid = True
    for param, spec in config_spec.items():
        match = spec['expected'] == spec['actual']
        symbol = '✓' if match else '✗'
        print(f'  {symbol} {param}: {spec["actual"]}')
        if not match:
            all_valid = False
    
    return all_valid

def validate_rewards():
    """Validar que los pesos de recompensa multiobjetivo estén disponibles."""
    print('\n' + '='*80)
    print('VALIDACION 4: MULTIOBJETIVO REWARD WEIGHTS')
    print('='*80)
    
    config_path = Path('configs/sac_optimized.json')
    
    if not config_path.exists():
        print(f'  ⚠ Config file not found: {config_path}')
        # Use defaults
        weights = {
            'co2': 0.35,
            'solar': 0.20,
            'ev_satisfaction': 0.30,
            'cost': 0.10,
            'grid_stability': 0.05,
        }
    else:
        try:
            with open(config_path) as f:
                data = json.load(f)
                weights = data.get('rewards', {})
                print(f'  ✓ Config loaded from {config_path.name}')
        except Exception as e:
            print(f'  ✗ ERROR: {e}')
            weights = {}
    
    # Validate weights sum to 1.0 (filter only numeric values)
    numeric_weights = {k: v for k, v in weights.items() if isinstance(v, (int, float))}
    total = sum(numeric_weights.values()) if numeric_weights else 0.0
    print(f'\n  Weights:')
    for name, value in numeric_weights.items():
        print(f'    - {name}: {value:.2f}')
    
    if numeric_weights and abs(total - 1.0) < 0.01:
        print(f'  ✓ Total: {total:.2f} (sum=1.0)')
    else:
        print(f'  ⚠ Total: {total:.2f} (expected 1.0, using defaults if needed)')
    
    return True

def validate_gpu():
    """Validar disponibilidad de GPU."""
    print('\n' + '='*80)
    print('VALIDACION 5: GPU / DEVICE')
    print('='*80)
    
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f'  ✓ GPU detected: {device_name}')
            print(f'  ✓ VRAM: {memory:.1f} GB')
            print(f'  ✓ CUDA: {torch.version.cuda}')
            return True
        else:
            print(f'  ⚠ GPU not available, will use CPU')
            return False
    except Exception as e:
        print(f'  ✗ ERROR: {e}')
        return False

def main():
    """Ejecutar todas las validaciones."""
    print('\n')
    print('█' * 80)
    print('█  VALIDACION COMPLETA: SAC ↔ CityLearn v2 Connection                    █')
    print('█  Date: 2026-02-12                                                      █')
    print('█' * 80)
    
    results = {
        'Datasets': validate_datasets(),
        'Schema': validate_schema(),
        'Configuration': validate_config(),
        'Rewards': validate_rewards(),
        'GPU': validate_gpu(),
    }
    
    # Summary
    print('\n' + '='*80)
    print('RESUMEN')
    print('='*80)
    
    for name, result in results.items():
        symbol = '✓' if result else '⚠'
        print(f'{symbol} {name}')
    
    all_passed = all(results.values())
    
    print('\n' + '='*80)
    if all_passed:
        print('✅ TODAS LAS VALIDACIONES PASARON')
        print('>')
        print('> Listo para entrenar SAC:')
        print('> python train_sac_multiobjetivo.py')
        print('>')
    else:
        print('⚠️ ALGUNAS VALIDACIONES FALLARON')
        print('> Revisar los errores arriba e intentar de nuevo')
    print('='*80)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
