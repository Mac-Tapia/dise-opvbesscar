#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validar que todos los datasets OE2 estén listos para entrenamiento SAC."""

import pandas as pd
import numpy as np
from pathlib import Path

print('='*80)
print('VALIDACION DE DATOS OE2 REALES - TODAS LAS COLUMNAS')
print('='*80)
print()

datasets_ok = True

# 1. SOLAR
print('1. SOLAR (4,050 kWp - PVGIS + PVLib)')
print('-'*80)
solar_path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
if solar_path.exists():
    df_solar = pd.read_csv(solar_path)
    print(f'  ✓ Archivo: {solar_path.name}')
    print(f'  ✓ Filas: {len(df_solar)} (8,760 esperados)')
    print(f'  ✓ Columnas ({len(df_solar.columns)}): {list(df_solar.columns[:8])}...')
    if 'ac_power_kw' in df_solar.columns:
        energia = df_solar['ac_power_kw'].sum()
        print(f'  ✓ AC Power total: {energia:.0f} kWh/año')
        print(f'  ✓ Average: {df_solar["ac_power_kw"].mean():.2f} kW/h')
        if len(df_solar) == 8760:
            print('  ✓ VALIDACIÓN: CORRECTA')
        else:
            print(f'  ✗ ERROR: {len(df_solar)} filas != 8760')
            datasets_ok = False
    else:
        print('  ✗ Columna ac_power_kw not found')
        datasets_ok = False
else:
    print(f'  ✗ NO ENCONTRADO: {solar_path}')
    datasets_ok = False
print()

# 2. CHARGERS
print('2. CHARGERS (38 sockets = 30 motos + 8 mototaxis)')
print('-'*80)
charger_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
if charger_path.exists():
    df_chargers = pd.read_csv(charger_path)
    socket_cols = [c for c in df_chargers.columns if '_charger_power_kw' in c]
    print(f'  ✓ Archivo: {charger_path.name}')
    print(f'  ✓ Filas: {len(df_chargers)} (8,760 esperados)')
    print(f'  ✓ Sockets (columnas _charger_power_kw): {len(socket_cols)} (38 esperados)')
    
    if len(socket_cols) == 38:
        energy_total = df_chargers[socket_cols].sum().sum()
        print(f'  ✓ Energía total EVs: {energy_total:.0f} kWh/año')
        print(f'  ✓ Average por hora: {energy_total / len(df_chargers):.2f} kW')
        print(f'  ✓ Primeros 3 sockets: {socket_cols[:3]}')
        print(f'  ✓ Últimos 3 sockets: {socket_cols[-3:]}')
        
        # Separar motos vs mototaxis
        motos = df_chargers[[c for c in socket_cols if int(c.split('_')[1]) < 30]].sum().sum()
        mototaxis = df_chargers[[c for c in socket_cols if int(c.split('_')[1]) >= 30]].sum().sum()
        print(f'  ✓ Motos (0-29): {motos:.0f} kWh/año')
        print(f'  ✓ Mototaxis (30-37): {mototaxis:.0f} kWh/año')
        
        if len(df_chargers) == 8760 and len(socket_cols) == 38:
            print('  ✓ VALIDACIÓN: CORRECTA')
        else:
            datasets_ok = False
    else:
        print(f'  ✗ ERROR: {len(socket_cols)} sockets != 38')
        datasets_ok = False
else:
    print(f'  ✗ NO ENCONTRADO: {charger_path}')
    datasets_ok = False
print()

# 3. MALL
print('3. MALL (100 kW nominal - Shopping Mall)')
print('-'*80)
mall_path = Path('data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv')
if mall_path.exists():
    # Intentar con diferentes delimitadores
    try:
        df_mall = pd.read_csv(mall_path, sep=';')
    except:
        df_mall = pd.read_csv(mall_path)
    
    print(f'  ✓ Archivo: {mall_path.name}')
    print(f'  ✓ Filas: {len(df_mall)} (8,760 esperados)')
    print(f'  ✓ Columnas: {list(df_mall.columns)}')
    
    # Detectar columna de demanda (puede ser diferente formato)
    demand_col = None
    if 'kWh' in df_mall.columns[0]:
        # Dividir si vienen juntos
        parts = df_mall.columns[0].split(';')
        if len(parts) > 1:
            df_mall = pd.read_csv(mall_path, sep=';')
            demand_col = df_mall.columns[-1]
        else:
            demand_col = df_mall.columns[-1]
    else:
        demand_col = 'demand_kwh' if 'demand_kwh' in df_mall.columns else df_mall.columns[-1]
    
    # Convertir a numérica si es string
    df_mall[demand_col] = pd.to_numeric(df_mall[demand_col], errors='coerce')
    demanda = df_mall[demand_col].sum()
    print(f'  ✓ Energía total: {demanda:.0f} kWh/año')
    print(f'  ✓ Average: {df_mall[demand_col].mean():.2f} kW/h')
    print(f'  ✓ Min/Max: {df_mall[demand_col].min():.2f} / {df_mall[demand_col].max():.2f} kW')
    
    if len(df_mall) == 8760:
        print('  ✓ VALIDACIÓN: CORRECTA')
    else:
        print(f'  ✗ ERROR: {len(df_mall)} filas != 8760')
        datasets_ok = False
else:
    print(f'  ✗ NO ENCONTRADO: {mall_path}')
    datasets_ok = False
print()

# 4. BESS
print('4. BESS (940 kWh EV + 400 kW potencia máxima)')
print('-'*80)
bess_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv')
if bess_path.exists():
    df_bess = pd.read_csv(bess_path)
    print(f'  ✓ Archivo: {bess_path.name}')
    print(f'  ✓ Filas: {len(df_bess)} (8,760 esperados)')
    print(f'  ✓ Columnas ({len(df_bess.columns)}): {list(df_bess.columns)}')
    
    if 'soc_percent' in df_bess.columns or 'bess_soc_percent' in df_bess.columns:
        soc_col = 'soc_percent' if 'soc_percent' in df_bess.columns else 'bess_soc_percent'
        print(f'  ✓ SOC Average: {df_bess[soc_col].mean():.1f}%')
        print(f'  ✓ SOC Min/Max: {df_bess[soc_col].min():.1f}% / {df_bess[soc_col].max():.1f}%')
    
    if len(df_bess) == 8760:
        print('  ✓ VALIDACIÓN: CORRECTA')
    else:
        print(f'  ✗ ERROR: {len(df_bess)} filas != 8760')
        datasets_ok = False
else:
    print(f'  ✗ NO ENCONTRADO: {bess_path}')
    datasets_ok = False
print()

# RESUMEN FINAL
print('='*80)
if datasets_ok:
    print('✅ VALIDACION EXITOSA - Todos los datos OE2 están listos')
    print('   Próximo paso: Lanzar entrenamiento SAC con scripts/train/train_sac_multiobjetivo.py')
else:
    print('❌ ERROR DE VALIDACION - Faltan o están dañados algunos datasets')
    print('   Asegúrate de que todos los archivos existan y tengan 8,760 filas')
print('='*80)
