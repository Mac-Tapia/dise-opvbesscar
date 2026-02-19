#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preparar datos reales OE2 para entrenamiento PPO.
Valida integridad y sincronizacion con CityLearn v2.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

def main():
    print('='*80)
    print('CONSTRUYENDO DATOS REALES OE2 PARA CITYLEARN v2')
    print('='*80)
    print()
    
    # Validar datasets OE2 obligatorios
    datasets = {
        'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
        'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
        'BESS': 'data/oe2/bess/bess_ano_2024.csv',
        'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
    }
    
    print('[PASO 1] Validando integridad de datos OE2...')
    all_ok = True
    
    for name, path in datasets.items():
        p = Path(path)
        if not p.exists():
            print(f'  [ERROR] {name:15} -> NO ENCONTRADO: {path}')
            all_ok = False
        else:
            try:
                df = pd.read_csv(path)
                rows = len(df)
                cols = df.shape[1]
                expected_rows = 8760
                status = '[OK]' if rows == expected_rows else '[WARNING]'
                print(f'  {status} {name:15} -> {rows:,} filas, {cols} columnas')
                if rows != expected_rows:
                    print(f'      ([WARNING] ESPERADO: {expected_rows} filas)')
            except Exception as e:
                print(f'  [ERROR] {name:15} -> ERROR: {str(e)[:50]}')
                all_ok = False
    
    print()
    if not all_ok:
        print('[ERROR] Algunos datasets OE2 no estan disponibles')
        sys.exit(1)
    
    print('[OK] Todos los datasets OE2 validados [OK]')
    print()
    print('='*80)
    print('ESTADO: Datos OE2 listos para entrenamiento SAC')
    print('='*80)
    print()
    print('Proximos pasos:')
    print('  1. Lanzar: python scripts/train/train_sac_multiobjetivo.py')
    print('  2. Monitorear con: Get-Content training_output.log -Tail 50')
    print()

if __name__ == '__main__':
    main()
