#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

print('\n' + '='*80)
print('✓ VERIFICACION DE DATOS OE2 REALES')
print('='*80)

datasets = {
    'Solar PV': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'Chargers EV': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS SOC': 'data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv',
    'Mall Demand': 'data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv',
}

all_ok = True
for name, path in datasets.items():
    p = Path(path)
    if p.exists():
        try:
            df = pd.read_csv(p)
            rows = len(df)
            cols = len(df.columns)
            status = '✓' if rows == 8760 else '⚠'
            print(f'{status} {name:20} | {rows:,} filas | {cols} cols')
        except Exception as e:
            print(f'✗ {name:20} | Error: {str(e)[:30]}')
            all_ok = False
    else:
        print(f'✗ {name:20} | NO ENCONTRADO')
        all_ok = False

print('='*80)
if all_ok:
    print('✅ TODOS LOS DATOS OE2 CARGADOS Y LISTOS\n')
else:
    print('❌ FALTAN DATOS\n')
