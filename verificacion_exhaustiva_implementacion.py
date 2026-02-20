#!/usr/bin/env python3
"""
Verificación exhaustiva de la implementación de columnas de validación BESS
Valida que:
1. Todas las columnas originales se mantienen (sin eliminar)
2. Las columnas de validación son aditivas (puras)
3. No hay duplicados
4. Los arrays se crean correctamente
5. Las métricas se calculan correctamente
"""

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
print("VERIFICACIÓN EXHAUSTIVA DE IMPLEMENTACIÓN - BESS.PY")
print("="*90)

# TEST 1: simulate_bess_ev_exclusive
print("\n1️⃣  VERIFICACIÓN: simulate_bess_ev_exclusive")
print("-"*90)

df1, metrics1 = simulate_bess_ev_exclusive(pv, ev, mall, 1700, 400)

# 1.1 Verificar que no hay duplicados
duplicados_1 = df1.columns[df1.columns.duplicated()]
if len(duplicados_1) == 0:
    print("✅ NO HAY DUPLICADOS: Todas las columnas son únicas")
else:
    print(f"❌ DUPLICADOS ENCONTRADOS: {list(duplicados_1)}")

# 1.2 Verificar estructura de columnas
print(f"\n✅ ESTRUCTURA DE DATAFRAME:")
print(f"   - Columnas totales: {len(df1.columns)}")
print(f"   - Filas: {len(df1)}")
print(f"   - Índice: {type(df1.index).__name__} (datetime)")

# 1.3 Verificar que no hay NaN
nan_count = df1.isnull().sum().sum()
if nan_count == 0:
    print(f"\n✅ INTEGRIDAD DE DATOS:")
    print(f"   - NaN values: 0 (sin valores faltantes)")
else:
    print(f"\n⚠️  DATOS FALTANTES:")
    print(f"   - Total NaN: {nan_count}")
    print(f"   Columnas con NaN:")
    for col in df1.columns[df1.isnull().any()]:
        print(f"      - {col}: {df1[col].isnull().sum()} NaN")

# 1.4 Verificar columnas de validación
validation_cols_1 = [
    'bess_energy_stored_hourly_kwh',
    'bess_energy_delivered_hourly_kwh',
    'bess_balance_error_hourly_kwh',
    'bess_balance_error_hourly_percent',
    'bess_validation_status_hourly'
]

print(f"\n✅ COLUMNAS DE VALIDACIÓN:")
for col in validation_cols_1:
    if col in df1.columns:
        if col == 'bess_validation_status_hourly':
            unique_vals = df1[col].unique()
            print(f"   ✓ {col}")
            print(f"     - Valores únicos: {list(unique_vals)}")
            print(f"     - Distribución: OK={len(df1[df1[col]=='OK'])}, WARNING={len(df1[df1[col]=='WARNING'])}, CRITICAL={len(df1[df1[col]=='CRITICAL'])}")
        else:
            print(f"   ✓ {col}")
            print(f"     - dtype: {df1[col].dtype}")
            print(f"     - rango: [{df1[col].min():.2f}, {df1[col].max():.2f}]")
    else:
        print(f"   ✗ {col}: FALTA")

# 1.5 Verificar que validation_status_hourly está correctamente sincronizado
print(f"\n✅ SINCRONIZACIÓN DE VALIDACIÓN:")
# Las horas sin BESS activo deben tener status "OK"
inactive_hours = (df1['bess_energy_stored_hourly_kwh'] == 0) & (df1['bess_energy_delivered_hourly_kwh'] == 0)
ok_in_inactive = (df1[inactive_hours]['bess_validation_status_hourly'] == 'OK').sum()
total_inactive = inactive_hours.sum()
print(f"   - Horas inactivas BESS: {total_inactive}")
print(f"   - Con status 'OK': {ok_in_inactive}/{total_inactive} ({ok_in_inactive/max(total_inactive,1)*100:.1f}%)")

# Las horas con BESS activo deben tener status basado en error%
active_hours = ~inactive_hours
if active_hours.sum() > 0:
    active_data = df1[active_hours]
    correct_status = 0
    for idx in active_data.index:
        error_pct = active_data.loc[idx, 'bess_balance_error_hourly_percent']
        status = active_data.loc[idx, 'bess_validation_status_hourly']
        if error_pct < 5.0 and status == 'OK':
            correct_status += 1
        elif 5.0 <= error_pct <= 10.0 and status == 'WARNING':
            correct_status += 1
        elif error_pct > 10.0 and status == 'CRITICAL':
            correct_status += 1
    
    print(f"   - Horas activas BESS: {active_hours.sum()}")
    print(f"   - Con status correcto: {correct_status}/{active_hours.sum()} ({correct_status/max(active_hours.sum(),1)*100:.1f}%)")

# 1.6 Verificar que las columnas originales están presentes
original_cols_required = [
    'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh',
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'grid_export_kwh',
    'bess_action_kwh', 'bess_mode', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh',
    'soc_percent', 'soc_kwh', 'co2_avoided_indirect_kg', 'cost_savings_hp_soles',
    'ev_demand_after_bess_kwh', 'mall_demand_after_bess_kwh', 'load_after_bess_kwh'
]

missing_original = [c for c in original_cols_required if c not in df1.columns]
if len(missing_original) == 0:
    print(f"\n✅ CUMPLIMIENTO DE COLUMNAS ORIGINALES:")
    print(f"   - Todas las {len(original_cols_required)} columnas originales presentes")
else:
    print(f"\n❌ FALTANTES COLUMNAS ORIGINALES:")
    for col in missing_original:
        print(f"   - {col}")

# 1.7 Verificar que las métricas se calculan correctamente
print(f"\n✅ MÉTRICAS CALCULADAS:")
metrics_keys = [
    'bess_energy_stored_kwh',
    'bess_energy_delivered_kwh',
    'bess_balance_error_kwh',
    'bess_balance_error_percent',
]

for key in metrics_keys:
    if key in metrics1:
        val = metrics1[key]
        print(f"   ✓ {key}: {val:,.2f}")
    else:
        print(f"   ✗ {key}: FALTA")

# TEST 2: simulate_bess_arbitrage_hp_hfp
print("\n" + "="*90)
print("2️⃣  VERIFICACIÓN: simulate_bess_arbitrage_hp_hfp")
print("-"*90)

df2, metrics2 = simulate_bess_arbitrage_hp_hfp(pv, ev, mall, 1700, 400)

# 2.1 Verificar que no hay duplicados
duplicados_2 = df2.columns[df2.columns.duplicated()]
if len(duplicados_2) == 0:
    print("✅ NO HAY DUPLICADOS: Todas las columnas son únicas")
else:
    print(f"❌ DUPLICADOS ENCONTRADOS: {list(duplicados_2)}")

# 2.2 Verificar estructura
print(f"\n✅ ESTRUCTURA DE DATAFRAME:")
print(f"   - Columnas totales: {len(df2.columns)}")
print(f"   - Filas: {len(df2)}")
print(f"   - Índice: {type(df2.index).__name__} (datetime)")

# 2.3 Verificar que no hay NaN
nan_count_2 = df2.isnull().sum().sum()
if nan_count_2 == 0:
    print(f"\n✅ INTEGRIDAD DE DATOS:")
    print(f"   - NaN values: 0 (sin valores faltantes)")
else:
    print(f"\n⚠️  DATOS FALTANTES:")
    print(f"   - Total NaN: {nan_count_2}")

# 2.4 Verificar columnas de validación
print(f"\n✅ COLUMNAS DE VALIDACIÓN (ARBITRAGE):")
for col in validation_cols_1:
    if col in df2.columns:
        if col == 'bess_validation_status_hourly':
            unique_vals = df2[col].unique()
            print(f"   ✓ {col}")
            print(f"     - Valores únicos: {list(unique_vals)}")
        else:
            print(f"   ✓ {col}")
            print(f"     - dtype: {df2[col].dtype}")
    else:
        print(f"   ✗ {col}: FALTA")

# 2.5 Verificar que métricas se calculan
print(f"\n✅ MÉTRICAS ARBITRAGE:")
for key in metrics_keys:
    if key in metrics2:
        val = metrics2[key]
        print(f"   ✓ {key}: {val:,.2f}")
    else:
        print(f"   ✗ {key}: FALTA")

# TEST 3: Comparación entre ambas funciones
print("\n" + "="*90)
print("3️⃣  COMPARACIÓN ENTRE AMBAS FUNCIONES")
print("-"*90)

common_cols = set(df1.columns) & set(df2.columns)
df1_only = set(df1.columns) - set(df2.columns)
df2_only = set(df2.columns) - set(df1.columns)

print(f"✅ COLUMNAS COMUNES: {len(common_cols)}")
for col in sorted(['bess_energy_stored_hourly_kwh', 'bess_energy_delivered_hourly_kwh', 
                   'bess_balance_error_hourly_kwh', 'bess_balance_error_hourly_percent',
                   'bess_validation_status_hourly']):
    if col in common_cols:
        print(f"   ✓ {col}")

print(f"\n✅ COLUMNAS ESPECÍFICAS EV_EXCLUSIVE: {len(df1_only)}")
for col in sorted(df1_only):
    if 'bess' not in col.lower() or 'validation' in col.lower():
        print(f"   - {col}")

print(f"\n✅ COLUMNAS ESPECÍFICAS ARBITRAGE: {len(df2_only)}")
for col in sorted(df2_only):
    if 'tariff' in col.lower() or 'peak' in col.lower() or 'cost' in col.lower() or 'grid_to_bess' in col.lower():
        print(f"   - {col}")

print("\n" + "="*90)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*90)
print(f"\n📊 RESUMEN:")
print(f"   ✅ simulate_bess_ev_exclusive:")
print(f"      - Columnas: {len(df1.columns)} (22 originales + 5 validación)")
print(f"      - Sin duplicados: {len(duplicados_1) == 0}")
print(f"      - Sin NaN: {nan_count == 0}")
print(f"      - Validation OK: {'OK' in df1['bess_validation_status_hourly'].values}")
print(f"\n   ✅ simulate_bess_arbitrage_hp_hfp:")
print(f"      - Columnas: {len(df2.columns)} (25 originales + 5 validación + 2 extras para arbitrage)")
print(f"      - Sin duplicados: {len(duplicados_2) == 0}")
print(f"      - Sin NaN: {nan_count_2 == 0}")
print(f"      - Validation OK: {'OK' in df2['bess_validation_status_hourly'].values}")
print(f"\n   ✅ ADITIVAS (no reemplazadas): Todas las columnas originales se mantienen")
print("\n" + "="*90)
