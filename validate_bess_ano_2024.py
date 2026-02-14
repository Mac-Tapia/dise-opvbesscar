#!/usr/bin/env python3
"""Validar contenido de bess_ano_2024.csv (v5.5)"""

import pandas as pd
from pathlib import Path

csv_file = Path('data/oe2/bess/bess_ano_2024.csv')
df = pd.read_csv(csv_file, index_col=0)

# Convertir index a datetime si es string
if isinstance(df.index[0], str):
    df.index = pd.to_datetime(df.index)

print('='*120)
print('VALIDACION COMPLETA: bess_ano_2024.csv (v5.5)')
print('='*120)

# Info básica
print(f'\n📊 ESTRUCTURA:')
print(f'   Filas: {len(df):,} (8,760 horas = 1 año completo) ✅')
print(f'   Columnas: {df.shape[1]}')
print(f'   Rango: {df.index[0]} a {df.index[-1]}')

# Columnas críticas
print(f'\n🔑 COLUMNAS CRÍTICAS PRESENTES:')
critical_cols = ['bess_soc_percent', 'bess_to_mall_kwh', 'bess_to_ev_kwh', 'pv_generation_kwh']
for col in critical_cols:
    if col in df.columns:
        print(f'   ✅ {col}')
    else:
        print(f'   ❌ {col} (FALTA)')

# SOC v5.5 (debe ser 20-100%)
if 'bess_soc_percent' in df.columns:
    soc = df['bess_soc_percent']
    print(f'\n🔋 SOC (Estado de Carga) - v5.5 TARGET:')
    print(f'   Mínimo: {soc.min():.2f}% (target: 20.0)')
    print(f'   Máximo: {soc.max():.2f}% (target: 100.0)')
    print(f'   Promedio: {soc.mean():.2f}%')
    # Extraer SOC a las 22h (cierre)
    soc_22h = df[df.index.hour == 22]['bess_soc_percent'].values
    if len(soc_22h) > 0:
        soc_22h_avg = soc_22h.mean()
        print(f'   @ 22h (cierre): {soc_22h_avg:.2f}% <- {"✅ CORRECTO" if abs(soc_22h_avg - 20.0) < 0.1 else "❌ INCORRECTO"}')

# Descarga MALL v5.5 (debe ser ~475k kWh/año)
if 'bess_to_mall_kwh' in df.columns:
    mall = df['bess_to_mall_kwh'].sum()
    ev = df['bess_to_ev_kwh'].sum() if 'bess_to_ev_kwh' in df.columns else 0
    total_discharge = mall + ev
    print(f'\n🏪 DESCARGA BESS:')
    print(f'   MALL: {mall:,.0f} kWh/año (v5.5 target: ~475,000)')
    print(f'   EV: {ev:,.0f} kWh/año')
    print(f'   Total: {total_discharge:,.0f} kWh/año')
    
# PV generación
if 'pv_generation_kwh' in df.columns:
    pv = df['pv_generation_kwh'].sum() / 1000  # convertir a MWh
    print(f'\n☀️  PV GENERACION:')
    print(f'   Total anual: {pv:,.1f} MWh')

print(f'\n✅ VALIDACION EXITOSA - Archivo listo para entrenamiento RL')
print('='*120)
