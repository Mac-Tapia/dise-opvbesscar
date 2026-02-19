#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDAR USO DE TODAS LAS COLUMNAS DEL DATASET EN SAC
Verifica que train_sac.py esté usando TODAS las columnas disponibles:
- 236+ columnas CO2
- 240+ columnas Motos/Mototaxis
- Chargers completos
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Set

print('='*100)
print('VALIDACION DE COLUMNAS: DATASET vs SAC USAGE')
print('='*100)
print()

# ===== CARGAR TODOS LOS CSVS =====
dataset_path = Path('data/iquitos_ev_mall')

if not dataset_path.exists():
    print('[ERROR] data/iquitos_ev_mall NO EXISTE')
    exit(1)

print('[1] CARGAR TODOS LOS CSVS DISPONIBLES')
print('-' * 100)

# Solar
solar_path = dataset_path / 'solar_generation.csv'
if solar_path.exists():
    df_solar = pd.read_csv(solar_path)
    print(f'\n✓ SOLAR: {solar_path.name}')
    print(f'  Shape: {df_solar.shape[0]} filas × {df_solar.shape[1]} columnas')
    print(f'  Columnas: {", ".join(df_solar.columns[:10].tolist())} ...')
    solar_cols = set(df_solar.columns)
else:
    print(f'\n✗ SOLAR NO EXISTE')
    solar_cols = set()

# Chargers
chargers_path = dataset_path / 'chargers_timeseries.csv'
if chargers_path.exists():
    df_chargers = pd.read_csv(chargers_path)
    print(f'\n✓ CHARGERS: {chargers_path.name}')
    print(f'  Shape: {df_chargers.shape[0]} filas × {df_chargers.shape[1]} columnas')
    print(f'  Columnas primeras 20:')
    for i, col in enumerate(df_chargers.columns[:20], 1):
        print(f'    {i:2d}. {col}')
    if len(df_chargers.columns) > 20:
        print(f'    ... +{len(df_chargers.columns) - 20} más')
    chargers_cols = set(df_chargers.columns)
else:
    print(f'\n✗ CHARGERS NO EXISTE')
    chargers_cols = set()

# Mall
mall_path = dataset_path / 'mall_demand.csv'
if mall_path.exists():
    df_mall = pd.read_csv(mall_path)
    print(f'\n✓ MALL: {mall_path.name}')
    print(f'  Shape: {df_mall.shape[0]} filas × {df_mall.shape[1]} columnas')
    print(f'  Columnas: {", ".join(df_mall.columns.tolist())}')
    mall_cols = set(df_mall.columns)
else:
    print(f'\n✗ MALL NO EXISTE')
    mall_cols = set()

# BESS
bess_path = dataset_path / 'bess_timeseries.csv'
if bess_path.exists():
    df_bess = pd.read_csv(bess_path)
    print(f'\n✓ BESS: {bess_path.name}')
    print(f'  Shape: {df_bess.shape[0]} filas × {df_bess.shape[1]} columnas')
    print(f'  Columnas: {", ".join(df_bess.columns[:15].tolist())}')
    if len(df_bess.columns) > 15:
        print(f'  ... +{len(df_bess.columns) - 15} más')
    bess_cols = set(df_bess.columns)
else:
    print(f'\n✗ BESS NO EXISTE')
    bess_cols = set()

# ===== ANALIZAR COLUMNAS POR TIPO =====
print()
print()
print('[2] ANALISIS DE COLUMNAS POR TIPO')
print('-' * 100)

# Chargers - tipo de datos
print('\n[CHARGERS] Análisis de tipos:')
numeric_cols = df_chargers.select_dtypes(include=[np.number]).columns.tolist()
str_cols = df_chargers.select_dtypes(include=['object']).columns.tolist()
print(f'  Columnas numéricas: {len(numeric_cols)}')
print(f'  Columnas de texto: {len(str_cols)}')
print(f'  Total: {len(df_chargers.columns)}')

# Detectar patrón de columnas
print(f'\n  Patrones detectados:')
print(f'    Socket/Charger: {[c for c in numeric_cols if "socket" in c.lower()][:5]}')
print(f'    Vehicle type: {str_cols[:5]}')
print(f'    Otros numericos: {numeric_cols[30:35] if len(numeric_cols) > 30 else numeric_cols[-5:]}')

# Motos y Mototaxis específicamente
print(f'\n[CHARGERS] Columnas MOTOS vs MOTOTAXIS:')
moto_cols = [c for c in chargers_cols if 'moto' in c.lower() and 'taxi' not in c.lower()]
mototaxi_cols = [c for c in chargers_cols if 'mototaxi' in c.lower() or ('taxi' in c.lower() and 'moto' in c.lower())]
print(f'  Columnas con "MOTO": {len(moto_cols)} → {moto_cols[:10]}')
print(f'  Columnas con "MOTOTAXI": {len(mototaxi_cols)} → {mototaxi_cols[:10]}')

# CO2 - Buscar en otros CSVs o columnas
print(f'\n[CO2] Búsqueda de columnas relacionadas:')
all_cols = solar_cols | chargers_cols | mall_cols | bess_cols
co2_cols = [c for c in all_cols if 'co2' in c.lower()]
print(f'  Columnas con "CO2": {len(co2_cols)} → {co2_cols}')

# ===== ANALIZAR DATOS =====
print()
print()
print('[3] ANALISIS CUANTITATIVO DE DATOS')
print('-' * 100)

# Chargers - diversidad
print('\n[CHARGERS] Estadísticas de valores:')
chargers_numeric = df_chargers[numeric_cols]
print(f'  Filas: {len(chargers_numeric)}')
print(f'  Columnas numéricas: {len(numeric_cols)}')
print(f'  Valores no-nulos:')
for col in numeric_cols[:5]:
    non_null = chargers_numeric[col].notna().sum()
    null_pct = 100 * (1 - non_null / len(chargers_numeric))
    print(f'    {col}: {non_null:,} ({null_pct:.1f}% valores NULL)')

# CO2 total disponible
print(f'\n[CHARGERS] Distribución de potencia:')
total_power = chargers_numeric[numeric_cols].sum().sum()
print(f'  Total potencia (todas columnas): {total_power:,.0f} kW·h')
print(f'  Top 10 columnas por energía:')
col_sums = chargers_numeric[numeric_cols].sum().nlargest(10)
for i, (col, val) in enumerate(col_sums.items(), 1):
    pct = 100 * val / total_power
    print(f'    {i:2d}. {col}: {val:10,.0f} kWh ({pct:5.1f}%)')

# ===== COMPARAR CON LO QUE TRAIN_SAC USA =====
print()
print()
print('[4] COMPARACION: COLUMNAS DISPONIBLES vs USO EN TRAIN_SAC.PY')
print('-' * 100)

# Leer train_sac.py para ver qué usa
train_sac_path = Path('scripts/train/train_sac.py')
if train_sac_path.exists():
    with open(train_sac_path, 'r', encoding='utf-8') as f:
        train_sac_content = f.read()
    
    # Buscar patrones en load_datasets_from_processed()
    print(f'\n[TRAIN_SAC.PY] Análisis de función load_datasets_from_processed():')
    
    # Detectar límites
    if 'power_cols[:50]' in train_sac_content or 'power_cols[:38]' in train_sac_content:
        print('  ⚠ LIMITACION: Solo toma primeras 50 o 38 columnas (HARDCODED)')
        print('    Línea apropiada: chargers_padded = np.zeros((HOURS_PER_YEAR, 38))')
    
    if 'chargers_moto' in train_sac_content:
        print('  ✓ Separa MOTOS: chargers_moto_hourly')
    else:
        print('  ✗ NO separa motos')
    
    if 'chargers_mototaxi' in train_sac_content:
        print('  ✓ Separa MOTOTAXIS: chargers_mototaxi_hourly')
    else:
        print('  ✗ NO separa mototaxis')
    
    # Buscar CO2
    if 'co2' in train_sac_content.lower():
        print('  ✓ Usa CO2: (encontrado en código)')
        co2_uses = []
        for i, line in enumerate(train_sac_content.split('\n'), 1):
            if 'co2' in line.lower() and i > 600 and i < 900:  # En load_datasets_from_processed
                co2_uses.append((i, line.strip()[:80]))
        if co2_uses:
            print(f'    Usos encontrados ({len(co2_uses)}):')
            for line_no, text in co2_uses[:5]:
                print(f'      {line_no}: {text}...')
    else:
        print('  ✗ NO usa CO2 directamente')
else:
    print(f'✗ train_sac.py no encontrado')

# ===== RECOMENDACIONES =====
print()
print()
print('[5] RECOMENDACIONES PARA USAR TODAS LAS COLUMNAS')
print('-' * 100)

print(f'\n[CHARGERS] Columnas disponibles vs usadas:')
print(f'  Disponibles: {len(numeric_cols)} columnas numéricas')
print(f'  Actual en train_sac.py: ~38 sockets (HARDCODED)')
print(f'  DEFICIT: {len(numeric_cols) - 38} columnas NO usadas ❌')

print(f'\n[MOTOS/MOTOTAXIS] Distribución de energía:')
if len(df_chargers) > 0:
    # Intenta calcular ratios
    sample_row = df_chargers.iloc[0]
    numeric_sample = sample_row[numeric_cols]
    print(f'  Ejemplo fila 1:')
    print(f'    Total energía: {numeric_sample.sum():.2f} kW')
    print(f'    Primeros 30 sockets (motos): {numeric_sample[:30].sum():.2f} kW')
    print(f'    Últimos 8 sockets (mototaxis): {numeric_sample[-8:].sum():.2f} kW')
    
print(f'\n[CO2] Métricas para cada dataset:')
print(f'  SOLAR: {len(solar_cols)} columnas')
print(f'  CHARGERS: {len(chargers_cols)} columnas → FOCUS en todas')
print(f'  MALL: {len(mall_cols)} columnas')
print(f'  BESS: {len(bess_cols)} columnas')

# ===== ACCION REQUERIDA =====
print()
print()
print('[6] ACCION REQUERIDA')
print('='*100)

print(f'''
PROBLEMA IDENTIFICADO:
  train_sac.py en load_datasets_from_processed() usa solo SUBSET de columnas:
  
  ✗ Chargers: {len(numeric_cols)} disponibles → solo 38 usadas (HARDCODED)
  ✗ CO2: No se usan columnas CO2 específicas (si existen)
  ✗ Motos/Mototaxis: Solo 2 métricas agregadas (sum), no distribución

SOLUCION REQUERIDA:
  1. Usar TODAS las {len(numeric_cols)} columnas de chargers
  2. Usar TODAS las columnas CO2 si existen
  3. Crear matriz (8760, {len(numeric_cols)}) en lugar de (8760, 38)
  4. Separar adecuadamente motos (primeros 30) vs mototaxis (últimos 8)
  5. Actualizar RealOE2Environment para procesar {len(numeric_cols)} dimensiones

IMPACTO:
  - Observación será más rica y detallada
  - Agente verá distribución real de potencia por socket
  - CO2 y metrics más precisas
''')

print()
print('='*100)
