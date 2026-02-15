#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion simplificada de dataset names"""
from pathlib import Path
import pandas as pd

print("\n" + "="*100)
print("VERIFICACION DE NOMBRES DE DATASETS - LISTADO SIMPLIFICADO")
print("="*100 + "\n")

datasets = {
    'SOLAR': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'CHARGERS': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
    'MALL_DEMAND': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

for name, path in datasets.items():
    p = Path(path)
    if p.exists():
        print(f"[OK] {name:20} | {path}")
        df = pd.read_csv(path, nrows=0)  # Solo columnas
        sep = ',' 
        print(f"   📋 Columnas ({len(df.columns)}): {list(df.columns)}\n")
    else:
        print(f"[X] {name:20} | NO EXISTE: {path}\n")

print("="*100)
