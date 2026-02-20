#!/usr/bin/env python3
"""Test de validación de columnas horarias de BESS"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Import las funciones
from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive, simulate_bess_arbitrage_hp_hfp

# Crear datos de prueba
np.random.seed(42)
pv_test = np.random.uniform(0, 100, 8760)
pv_test[0:6] = 0  # Noche
pv_test[18:24] = 0  # Noche
ev_test = np.random.uniform(20, 100, 8760)
mall_test = np.random.uniform(80, 150, 8760)

# Columnas requeridas
required_cols = [
    'bess_energy_stored_hourly_kwh',
    'bess_energy_delivered_hourly_kwh', 
    'bess_balance_error_hourly_kwh',
    'bess_balance_error_hourly_percent',
    'bess_validation_status_hourly'
]

print("="*70)
print("TEST 1: simulate_bess_ev_exclusive")
print("="*70)

try:
    df1, metrics1 = simulate_bess_ev_exclusive(pv_test, ev_test, mall_test, capacity_kwh=1700, power_kw=400)
    print(f"✅ Ejecución exitosa")
    print(f"   Filas generadas: {len(df1)}")
    print(f"   Columnas de validación:")
    
    all_present = True
    for col in required_cols:
        if col in df1.columns:
            if col == 'bess_validation_status_hourly':
                unique_vals = list(df1[col].unique())
                print(f"      ✓ {col}: {unique_vals}")
            else:
                n_unique = df1[col].nunique()
                print(f"      ✓ {col}: {n_unique} valores únicos")
        else:
            print(f"      ✗ {col}: NOT FOUND")
            all_present = False
    
    if all_present:
        print(f"\n   Status distribution:")
        for status in ['OK', 'WARNING', 'CRITICAL']:
            count = (df1['bess_validation_status_hourly'] == status).sum()
            pct = count / len(df1) * 100
            print(f"      - {status}: {count} horas ({pct:.1f}%)")
        
        print(f"\n   Rango balance error: {df1['bess_balance_error_hourly_kwh'].min():.2f} a {df1['bess_balance_error_hourly_kwh'].max():.2f} kWh")
        print(f"   Rango balance %: {df1['bess_balance_error_hourly_percent'].min():.2f} a {df1['bess_balance_error_hourly_percent'].max():.2f}%")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST 2: simulate_bess_arbitrage_hp_hfp")
print("="*70)

try:
    df2, metrics2 = simulate_bess_arbitrage_hp_hfp(pv_test, ev_test, mall_test, capacity_kwh=1700, power_kw=400)
    print(f"✅ Ejecución exitosa")
    print(f"   Filas generadas: {len(df2)}")
    print(f"   Columnas de validación:")
    
    all_present = True
    for col in required_cols:
        if col in df2.columns:
            if col == 'bess_validation_status_hourly':
                unique_vals = list(df2[col].unique())
                print(f"      ✓ {col}: {unique_vals}")
            else:
                n_unique = df2[col].nunique()
                print(f"      ✓ {col}: {n_unique} valores únicos")
        else:
            print(f"      ✗ {col}: NOT FOUND")
            all_present = False
    
    if all_present:
        print(f"\n   Status distribution:")
        for status in ['OK', 'WARNING', 'CRITICAL']:
            count = (df2['bess_validation_status_hourly'] == status).sum()
            pct = count / len(df2) * 100
            print(f"      - {status}: {count} horas ({pct:.1f}%)")
        
        print(f"\n   Rango balance error: {df2['bess_balance_error_hourly_kwh'].min():.2f} a {df2['bess_balance_error_hourly_kwh'].max():.2f} kWh")
        print(f"   Rango balance %: {df2['bess_balance_error_hourly_percent'].min():.2f} a {df2['bess_balance_error_hourly_percent'].max():.2f}%")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✅ VALIDACIÓN COMPLETA")
print("="*70)
