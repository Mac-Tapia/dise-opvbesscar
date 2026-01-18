#!/usr/bin/env python
"""Verificar si demanda del mall se carga en OE2 BESS."""

from pathlib import Path
from iquitos_citylearn.oe2.bess import load_mall_demand_real
import pandas as pd

# Cargar demanda del mall
demand_path = Path('data/interim/oe2/demandamallkwh/demandamallkwh.csv')
print('='*80)
print('VERIFICACIÓN: DEMANDA DEL MALL EN OE2 BESS')
print('='*80)
print()

if demand_path.exists():
    print(f'✅ ARCHIVO ENCONTRADO: {demand_path}')
    print(f'   Tamaño: {demand_path.stat().st_size / 1024:.1f} KB')
    print()
    
    # Cargar usando función de OE2
    df = load_mall_demand_real(demand_path, year=2024)
    print(f'✅ DATOS CARGADOS POR run_oe2_bess.py')
    print(f'   Total registros: {len(df)}')
    print(f'   Período: {df.index[0]} a {df.index[-1]}')
    print()
    
    print('DEMANDA HORARIA (primeras 24 horas):')
    print()
    print('Hora | Demanda (kWh/h)')
    print('─────┼──────────────────')
    for i, (idx, row) in enumerate(df.head(24).iterrows()):
        hora = idx.hour
        demanda = row['mall_kwh']
        print(f' {hora:2d}  | {demanda:8.1f}')
    print()
    
    print('ESTADÍSTICAS:')
    print(f'  Mínimo:   {df["mall_kwh"].min():.1f} kWh')
    print(f'  Máximo:   {df["mall_kwh"].max():.1f} kWh')
    print(f'  Promedio: {df["mall_kwh"].mean():.1f} kWh')
    print(f'  Total anual: {df["mall_kwh"].sum():,.0f} kWh')
    print()
    
else:
    print(f'❌ NO ENCONTRADO: {demand_path}')
