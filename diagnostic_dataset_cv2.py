#!/usr/bin/env python3
"""Diagnóstico del dataset en CityLearn v2"""

import pandas as pd
import json
from pathlib import Path

print('╔════════════════════════════════════════════════════════════╗')
print('║        DIAGNÓSTICO DATASET CITYLEARN v2                    ║')
print('╚════════════════════════════════════════════════════════════╝')
print()

# 1. Verificar datos solares
solar_path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
print(f'[1] DATOS SOLARES: {solar_path}')
if solar_path.exists():
    solar_df = pd.read_csv(solar_path)
    print(f'    ✓ Archivo encontrado')
    print(f'    • Filas: {len(solar_df)} (debe ser 8,760)')
    print(f'    • Columnas: {list(solar_df.columns)}')
    numeric_cols = solar_df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        first_num = numeric_cols[0]
        print(f'    • Rango valores: [{solar_df[first_num].min():.2f}, {solar_df[first_num].max():.2f}]')
    if len(solar_df) == 8760:
        print(f'    ✅ VÁLIDO: Datos horarios anuales')
    else:
        print(f'    ❌ ERROR: Se requieren exactamente 8,760 filas')
else:
    print(f'    ❌ ARCHIVO NO ENCONTRADO')
print()

# 2. Verificar datos de cargadores
charger_path = Path('data/interim/oe2/chargers/individual_chargers.json')
print(f'[2] DATOS DE CARGADORES: {charger_path}')
if charger_path.exists():
    with open(charger_path) as f:
        chargers = json.load(f)
    print(f'    ✓ Archivo encontrado')
    print(f'    • Tipo: {type(chargers).__name__}')
    print(f'    • Cantidad: {len(chargers)}')
    if isinstance(chargers, list):
        sockets = len(chargers) * 4
        print(f'    • Sockets esperados: {sockets} (32 × 4 = 128)')
        if len(chargers) == 32:
            print(f'    ✅ VÁLIDO: 32 cargadores para 128 sockets')
        else:
            print(f'    ⚠️  ADVERTENCIA: Se esperan 32 cargadores, hay {len(chargers)}')
else:
    print(f'    ❌ ARCHIVO NO ENCONTRADO')
print()

# 3. Verificar demanda del mall
mall_path = Path('data/interim/oe2/mall_demand_hourly.csv')
print(f'[3] DEMANDA DEL MALL: {mall_path}')
if mall_path.exists():
    mall_df = pd.read_csv(mall_path)
    print(f'    ✓ Archivo encontrado')
    print(f'    • Filas: {len(mall_df)}')
    print(f'    • Columnas: {list(mall_df.columns)}')
else:
    print(f'    ❌ ARCHIVO NO ENCONTRADO')
print()

print('╔════════════════════════════════════════════════════════════╗')
print('║                   FIN DIAGNÓSTICO                           ║')
print('╚════════════════════════════════════════════════════════════╝')
