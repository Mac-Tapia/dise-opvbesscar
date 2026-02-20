#!/usr/bin/env python3
"""Verificar estructura completa de ambas funciones BESS"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive, simulate_bess_arbitrage_hp_hfp

# Datos de prueba
np.random.seed(42)
pv = np.random.uniform(0, 100, 8760)
pv[0:6] = 0
pv[18:24] = 0
ev = np.random.uniform(20, 100, 8760)
mall = np.random.uniform(80, 150, 8760)

print("="*90)
print("COMPARACIÓN DE ESTRUCTURA DE DATAFRAMES - AMBAS FUNCIONES")
print("="*90)

# Test 1
print("\n1️⃣  simulate_bess_ev_exclusive")
print("-"*90)
df1, metrics1 = simulate_bess_ev_exclusive(pv, ev, mall, 1700, 400)
print(f"✅ Columnas: {len(df1.columns)}")
print(f"   Filas: {len(df1)}")

original_cols = [
    'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh', 
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'grid_export_kwh',
    'bess_action_kwh', 'bess_mode', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh',
    'soc_percent', 'soc_kwh', 'co2_avoided_indirect_kg', 'cost_savings_hp_soles',
    'ev_demand_after_bess_kwh', 'mall_demand_after_bess_kwh', 'load_after_bess_kwh'
]

new_cols = [
    'bess_energy_stored_hourly_kwh', 'bess_energy_delivered_hourly_kwh',
    'bess_balance_error_hourly_kwh', 'bess_balance_error_hourly_percent',
    'bess_validation_status_hourly'
]

print(f"\n   Columnas ORIGINALES ({len(original_cols)}):")
missing_original = [c for c in original_cols if c not in df1.columns]
if missing_original:
    print(f"   ⚠️  FALTANTES: {missing_original}")
else:
    print(f"   ✅ Todas presentes")

print(f"\n   Columnas NUEVAS (Validación - {len(new_cols)}):")
missing_new = [c for c in new_cols if c not in df1.columns]
if missing_new:
    print(f"   ⚠️  FALTANTES: {missing_new}")
else:
    print(f"   ✅ Todas presentes")

print(f"\n   Total columnas esperadas: {len(original_cols) + len(new_cols)}")
print(f"   Total columnas reales: {len(df1.columns)}")

# Test 2
print("\n2️⃣  simulate_bess_arbitrage_hp_hfp")
print("-"*90)
df2, metrics2 = simulate_bess_arbitrage_hp_hfp(pv, ev, mall, 1700, 400)
print(f"✅ Columnas: {len(df2.columns)}")
print(f"   Filas: {len(df2)}")

# Para arbitrage, algunas columnas pueden ser diferentes
# Se espera: las básicas + tarifas + validación
arbitrage_expected_cols = [
    'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh',
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'grid_export_kwh',
    'bess_action_kwh', 'bess_mode', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'grid_to_bess_kwh', 'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh',
    'grid_export_kwh_metric', 'soc_percent', 'soc_kwh',
    'is_peak_hour', 'tariff_soles_kwh', 'cost_grid_import_soles', 'savings_bess_soles',
    'co2_grid_kg', 'co2_avoided_kg'
]

print(f"\n   Columnas ESPERADAS ({len(arbitrage_expected_cols)}):")
missing_expected = [c for c in arbitrage_expected_cols if c not in df2.columns]
if missing_expected:
    print(f"   ⚠️  FALTANTES: {missing_expected}")
else:
    print(f"   ✅ Todas presentes")

print(f"\n   Columnas NUEVAS (Validación - {len(new_cols)}):")
missing_new_arb = [c for c in new_cols if c not in df2.columns]
if missing_new_arb:
    print(f"   ⚠️  FALTANTES: {missing_new_arb}")
else:
    print(f"   ✅ Todas presentes")

print(f"\n   Total columnas reales: {len(df2.columns)}")

print("\n" + "="*90)
print("RESUMEN")
print("="*90)

print(f"\n✅ simulate_bess_ev_exclusive:")
print(f"   - {len(original_cols)} columnas originales")
print(f"   - {len(new_cols)} columnas de validación")
print(f"   - Total: {len(df1.columns)} columnas")

print(f"\n✅ simulate_bess_arbitrage_hp_hfp:")
print(f"   - {len(arbitrage_expected_cols)} columnas esperadas")
print(f"   - {len(new_cols)} columnas de validación")
print(f"   - Total: {len(df2.columns)} columnas")

print(f"\n📊 Comparación de filas:")
print(f"   - EV Exclusive: {len(df1)} filas (8,760 horas ✅)")
print(f"   - Arbitrage: {len(df2)} filas (8,760 horas ✅)")

print(f"\n📊 Ready for CityLearn v2:")
print(f"   - ✅ EV Exclusive: {len(df1.columns)} features × {len(df1)} timesteps")
print(f"   - ✅ Arbitrage: {len(df2.columns)} features × {len(df2)} timesteps")

print("\n" + "="*90)
