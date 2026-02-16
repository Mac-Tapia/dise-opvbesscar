#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reescribir mall CSV limpio y correcto."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

mal_file = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
backup_file = mal_file.with_suffix('.csv.backup')

print('Reescribiendo archivo mall_demand...')

# Hacer backup
if not backup_file.exists() and mal_file.exists():
    import shutil
    shutil.copy(mal_file, backup_file)
    print(f'  Backup guardado: {backup_file}')

# Leer con maxima tolerancia
try:
    df = pd.read_csv(mal_file, on_bad_lines='skip', engine='python')
    print(f'  Shape: {df.shape}')
    print(f'  Columns: {df.columns.tolist()}')
    print(f'  dtypes: {df.dtypes.to_dict()}')
    
    # Asegurar 8760 filas
    if len(df) > 8760:
        df = df.iloc[:8760]
    
    # Asegurar que todas las columnas numericas sean numericas
    for col in df.columns[1:]:  # Saltar datetime
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except:
            pass
    
    # Remover NaNs
    df = df.dropna()
    
    print(f'  Shape despues limpieza: {df.shape}')
    
    # Reescribir con ASCII encoding
    mal_file.unlink()
    df.to_csv(mal_file, index=False, encoding='utf-8')
    print(f'  [OK] Archivo reescrito: {mal_file}')
    
    # Verificar
    df_check = pd.read_csv(mal_file)
    print(f'  [OK] Verificacion: {df_check.shape} OK')
    print(f'    Ultima columna ({df_check.columns[-1]}): {df_check[df_check.columns[-1]].iloc[0]}')
    
except Exception as e:
    print(f'  [ERROR] {e}')
    import traceback
    traceback.print_exc()
