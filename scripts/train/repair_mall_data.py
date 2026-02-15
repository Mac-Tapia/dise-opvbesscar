#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reparar archivo mall_demand con formato incorrecto."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

mall_file = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')

print('Reparando archivo mall_demand...')
print(f'Leyendo: {mall_file}')

# Leer con skiprows para saltar lineas problematicas
try:
    # Intenta leer directamente
    df = pd.read_csv(mall_file)
    print(f'  Shape original: {df.shape}')
    print(f'  Columns: {df.columns.tolist()}')
    
    # Si tiene problemas, relimpiar
    if len(df) > 8760 or df.shape[1] != 6:
        print('  [INFO] Limpiando datos...')
        # Leer con manejo de problemas
        df = pd.read_csv(mall_file, on_bad_lines='skip')
        print(f'  Shape limpio: {df.shape}')
        
        # Asegurarse de que tenemos 8760 filas
        if len(df) > 8760:
            df = df.iloc[:8760]
        
        # Guardar limpio
        df.to_csv(mall_file, index=False)
        print(f'  [OK] Guardado: {mall_file}')
    else:
        print('  [OK] Formato correcto')
        
except Exception as e:
    print(f'  [ERROR] {e}')
    import traceback
    traceback.print_exc()
