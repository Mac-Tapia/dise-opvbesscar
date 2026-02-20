#!/usr/bin/env python3
"""
VALIDACIÓN INTEGRAL: Dataset BESS para CityLearn v2
Verifica sincronización, optimización y ausencia de desperdicios
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive, simulate_bess_arbitrage_hp_hfp

# Crear datos de prueba realistas
np.random.seed(2024)
n_hours = 8760

# Perfil PV realista (generación solar 6-18h)
pv_test = np.zeros(n_hours)
for h in range(n_hours):
    hour_of_day = h % 24
    if 6 <= hour_of_day <= 18:
        # Parábola para generar curva realista de generación
        t_norm = (hour_of_day - 6) / 12
        pv_test[h] = 80 * np.sin(np.pi * t_norm) ** 2
    
    # Variabilidad diaria (invierno/verano)
    day_of_year = h // 24
    seasonal_factor = 0.7 + 0.3 * np.sin(2 * np.pi * day_of_year / 365)
    pv_test[h] *= seasonal_factor

# Perfil EV realista (motos/mototaxis - pico 0-6h, 14-22h)
ev_test = np.zeros(n_hours)
for h in range(n_hours):
    hour_of_day = h % 24
    if 0 <= hour_of_day < 6:  # Madrugada: carga inicial
        ev_test[h] = 60 + 20 * np.random.uniform(0.8, 1.2)
    elif 6 <= hour_of_day < 14:  # Día: operación, carga lenta
        ev_test[h] = 30 + 10 * np.random.uniform(0.8, 1.2)
    elif 14 <= hour_of_day < 22:  # Tarde/noche: carga rápida
        ev_test[h] = 80 + 20 * np.random.uniform(0.8, 1.2)
    else:  # Noche: carga final
        ev_test[h] = 70 + 15 * np.random.uniform(0.8, 1.2)

# Perfil MALL realista (comercio - picos mediodía y tarde)
mall_test = np.zeros(n_hours)
for h in range(n_hours):
    hour_of_day = h % 24
    if 8 <= hour_of_day <= 21:  # Operación comercial
        if 11 <= hour_of_day <= 13 or 17 <= hour_of_day <= 20:  # Picos
            mall_test[h] = 150 + 50 * np.random.uniform(0.8, 1.2)
        else:
            mall_test[h] = 80 + 30 * np.random.uniform(0.8, 1.2)
    else:  # Cerrado
        mall_test[h] = 20 + 10 * np.random.uniform(0.8, 1.2)

print("\n" + "="*80)
print("VALIDACIÓN INTEGRAL: Dataset BESS para CityLearn v2")
print("="*80)

# ============================================================================
# TEST 1: simulate_bess_ev_exclusive
# ============================================================================
print("\n┌─ TEST 1: EV EXCLUSIVE (Motos + Mototaxis)")
print("├─ Carga desde: Generación PV + BESS")
print("├─ Descarga BESS hacia: EV (prioridad) + MALL (peak shaving)")
print("└─ Objetivo: Autosuficiencia EV, reducción CO2")

df_ev, metrics_ev = simulate_bess_ev_exclusive(
    pv_test, ev_test, mall_test, 
    capacity_kwh=1700, 
    power_kw=400
)

print(f"\n✅ Datos generados:")
print(f"   Filas: {len(df_ev)} (8,760 horas = 1 año)")
print(f"   Columnas: {len(df_ev.columns)}")

# Verificar columnas críticas para CityLearn v2
critical_cols = [
    'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh',
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'grid_export_kwh',
    'bess_charge_kwh', 'bess_discharge_kwh', 'bess_mode',
    'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh',
    'soc_percent', 'soc_kwh',
    'ev_demand_after_bess_kwh', 'mall_demand_after_bess_kwh', 'load_after_bess_kwh',
    'bess_energy_stored_hourly_kwh', 'bess_energy_delivered_hourly_kwh',
    'bess_balance_error_hourly_kwh', 'bess_balance_error_hourly_percent',
    'bess_validation_status_hourly'
]

print(f"\n✅ Columnas críticas para CityLearn v2:")
all_present = True
for col in critical_cols:
    if col in df_ev.columns:
        print(f"   ✓ {col}")
    else:
        print(f"   ✗ FALTA: {col}")
        all_present = False

if all_present:
    print(f"\n   ✅ TODAS LAS COLUMNAS PRESENTES")
else:
    print(f"\n   ❌ FALTAN COLUMNAS")

# ============================================================================
# ANÁLISIS DE SINCRONIZACIÓN Y OPTIMIZACIÓN
# ============================================================================
print(f"\n" + "─"*80)
print("SINCRONIZACIÓN CON PERFILES")
print("─"*80)

# 1. Validar que PV fluye correctamente
pv_total = df_ev['pv_kwh'].sum()
pv_to_ev_total = df_ev['pv_to_ev_kwh'].sum()
pv_to_bess_total = df_ev['pv_to_bess_kwh'].sum()
pv_to_mall_total = df_ev['pv_to_mall_kwh'].sum()
pv_export_total = df_ev['grid_export_kwh'].sum()
pv_accounted = pv_to_ev_total + pv_to_bess_total + pv_to_mall_total + pv_export_total

print(f"\n📊 Flujo PV (Generación → Distribución):")
print(f"   PV Generado:         {pv_total:>12,.0f} kWh")
print(f"   ├─ PV → EV:          {pv_to_ev_total:>12,.0f} kWh ({pv_to_ev_total/pv_total*100:>5.1f}%)")
print(f"   ├─ PV → BESS:        {pv_to_bess_total:>12,.0f} kWh ({pv_to_bess_total/pv_total*100:>5.1f}%)")
print(f"   ├─ PV → MALL:        {pv_to_mall_total:>12,.0f} kWh ({pv_to_mall_total/pv_total*100:>5.1f}%)")
print(f"   └─ PV → Exportado:   {pv_export_total:>12,.0f} kWh ({pv_export_total/pv_total*100:>5.1f}%)")
print(f"   Total contabilizado: {pv_accounted:>12,.0f} kWh")
balance_pv = abs(pv_accounted - pv_total)
print(f"   Discrepancia PV:     {balance_pv:>12,.0f} kWh ({balance_pv/pv_total*100:.2f}%)")
if balance_pv / pv_total * 100 < 0.1:
    print(f"   ✅ SIN DESPERDICIOS (error < 0.1%)")
elif balance_pv / pv_total * 100 < 1.0:
    print(f"   ✓ Bajo desperdicio (error < 1%)")
else:
    print(f"   ⚠️ Verificar contabilización")

# 2. Validar BESS carga/descarga sincronización
bess_charge_total = df_ev['bess_charge_kwh'].sum()
bess_discharge_total = df_ev['bess_discharge_kwh'].sum()
bess_to_ev_total = df_ev['bess_to_ev_kwh'].sum()
bess_to_mall_total = df_ev['bess_to_mall_kwh'].sum()
bess_discharge_accounted = bess_to_ev_total + bess_to_mall_total

print(f"\n📊 Ciclo BESS (Carga → Descarga → Distribución):")
print(f"   BESS Cargado:        {bess_charge_total:>12,.0f} kWh")
print(f"   BESS Descargado:     {bess_discharge_total:>12,.0f} kWh")
print(f"   Descarga contab.:    {bess_discharge_accounted:>12,.0f} kWh")
print(f"   ├─ BESS → EV:        {bess_to_ev_total:>12,.0f} kWh ({bess_to_ev_total/max(bess_discharge_total,1)*100:>5.1f}%)")
print(f"   └─ BESS → MALL:      {bess_to_mall_total:>12,.0f} kWh ({bess_to_mall_total/max(bess_discharge_total,1)*100:>5.1f}%)")
balance_bess = abs(bess_discharge_accounted - bess_discharge_total)
print(f"   Discrepancia DESC:   {balance_bess:>12,.0f} kWh ({balance_bess/max(bess_discharge_total,1)*100:.2f}%)")
if balance_bess / max(bess_discharge_total, 1) * 100 < 0.1:
    print(f"   ✅ BESS 100% DISTRIBUIDO (error < 0.1%)")
elif balance_bess / max(bess_discharge_total, 1) * 100 < 1.0:
    print(f"   ✓ BESS casi perfecto (error < 1%)")
else:
    print(f"   ⚠️ Verificar distribución BESS")

# 3. Validar demanda original = demanda cortada + BESS aporte
ev_original_total = df_ev['ev_kwh'].sum()
ev_after_bess_total = df_ev['ev_demand_after_bess_kwh'].sum()
ev_bess_aporte = ev_original_total - ev_after_bess_total
ev_expected_bess = df_ev['bess_to_ev_kwh'].sum()

print(f"\n📊 Balance EV (Demanda Original = Cortada + BESS Aporte):")
print(f"   EV Demanda Original: {ev_original_total:>12,.0f} kWh")
print(f"   EV Demanda Cortada:  {ev_after_bess_total:>12,.0f} kWh")
print(f"   EV BESS Aporte:      {ev_bess_aporte:>12,.0f} kWh")
print(f"   EV BESS Esperado:    {ev_expected_bess:>12,.0f} kWh")
balance_ev = abs(ev_bess_aporte - ev_expected_bess)
print(f"   Discrepancia:        {balance_ev:>12,.0f} kWh ({balance_ev/ev_original_total*100:.2f}%)")
if balance_ev / ev_original_total * 100 < 0.1:
    print(f"   ✅ BALANCE PERFECTO (error < 0.1%)")
else:
    print(f"   ⚠️ Revisar balance EV")

# 4. Validar demanda MALL
mall_original_total = df_ev['mall_kwh'].sum()
mall_after_bess_total = df_ev['mall_demand_after_bess_kwh'].sum()
mall_bess_aporte = mall_original_total - mall_after_bess_total
mall_expected_bess = df_ev['bess_to_mall_kwh'].sum()

print(f"\n📊 Balance MALL (Demanda Original = Cortada + Peak Shaving):")
print(f"   MALL Demanda Orig.:  {mall_original_total:>12,.0f} kWh")
print(f"   MALL Demanda Cortad.:{mall_after_bess_total:>12,.0f} kWh")
print(f"   MALL Peak Shaving:   {mall_bess_aporte:>12,.0f} kWh")
print(f"   MALL Esperado BESS:  {mall_expected_bess:>12,.0f} kWh")
balance_mall = abs(mall_bess_aporte - mall_expected_bess)
print(f"   Discrepancia:        {balance_mall:>12,.0f} kWh ({balance_mall/mall_original_total*100:.2f}%)")
if balance_mall / mall_original_total * 100 < 0.1:
    print(f"   ✅ BALANCE PERFECTO (error < 0.1%)")
else:
    print(f"   ⚠️ Revisar balance MALL")

# ============================================================================
# VALIDACIÓN DE PERFILES HORARIOS
# ============================================================================
print(f"\n" + "─"*80)
print("VALIDACIÓN DE SINCRONIZACIÓN HORARIA")
print("─"*80)

# Encontrar horas con máxima actividad
max_pv_hour = df_ev['pv_kwh'].idxmax()
max_pv_val = df_ev.loc[max_pv_hour, 'pv_kwh']
max_ev_hour = df_ev['ev_kwh'].idxmax()
max_ev_val = df_ev.loc[max_ev_hour, 'ev_kwh']
max_mall_hour = df_ev['mall_kwh'].idxmax()
max_mall_val = df_ev.loc[max_mall_hour, 'mall_kwh']
max_bess_charge_hour = df_ev['bess_charge_kwh'].idxmax()
max_bess_charge_val = df_ev.loc[max_bess_charge_hour, 'bess_charge_kwh']
max_bess_discharge_hour = df_ev['bess_discharge_kwh'].idxmax()
max_bess_discharge_val = df_ev.loc[max_bess_discharge_hour, 'bess_discharge_kwh']

print(f"\n🔍 Horas de máxima actividad:")
print(f"   Max PV:              {max_pv_hour.strftime('%H:%M')} → {max_pv_val:.1f} kWh")
print(f"   Max EV:              {max_ev_hour.strftime('%H:%M')} → {max_ev_val:.1f} kWh")
print(f"   Max MALL:            {max_mall_hour.strftime('%H:%M')} → {max_mall_val:.1f} kWh")
print(f"   Max BESS Carga:      {max_bess_charge_hour.strftime('%H:%M')} → {max_bess_charge_val:.1f} kWh")
print(f"   Max BESS Descarga:   {max_bess_discharge_hour.strftime('%H:%M')} → {max_bess_discharge_val:.1f} kWh")

# Validar sincronización lógica
print(f"\n✅ Validaciones de sincronización:")

# BESS carga debe ser en horario de PV (6-18h)
bess_charge_hours = df_ev[df_ev['bess_charge_kwh'] > 0].index.hour.unique()
bess_charge_during_pv = df_ev[(df_ev['bess_charge_kwh'] > 0) & ((df_ev.index.hour >= 6) & (df_ev.index.hour <= 18))].shape[0] / max(len(df_ev[df_ev['bess_charge_kwh'] > 0]), 1) * 100
print(f"   BESS carga durante PV (6-18h): {bess_charge_during_pv:.1f}%")
if bess_charge_during_pv > 90:
    print(f"      ✓ Correctamente sincronizado con generación PV")

# BESS descarga debe ser en horario de demanda (6-22h)
bess_discharge_hours = df_ev[df_ev['bess_discharge_kwh'] > 0].index.hour.unique()
bess_discharge_during_demand = df_ev[(df_ev['bess_discharge_kwh'] > 0) & ((df_ev.index.hour >= 6) & (df_ev.index.hour <= 22))].shape[0] / max(len(df_ev[df_ev['bess_discharge_kwh'] > 0]), 1) * 100
print(f"   BESS descarga durante demanda (6-22h): {bess_discharge_during_demand:.1f}%")
if bess_discharge_during_demand > 90:
    print(f"      ✓ Correctamente sincronizado con demanda")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print(f"\n" + "="*80)
print("RESUMEN Y ESTADO FINAL")
print("="*80)

checks = [
    ("Todas columnas presentes", all_present),
    ("PV sin desperdicios (< 0.1%)", balance_pv / pv_total * 100 < 0.1),
    ("BESS 100% distribuido (< 0.1%)", balance_bess / max(bess_discharge_total, 1) * 100 < 0.1),
    ("EV balance perfecto (< 0.1%)", balance_ev / ev_original_total * 100 < 0.1),
    ("MALL balance perfecto (< 0.1%)", balance_mall / mall_original_total * 100 < 0.1),
    ("BESS carga sincronizado con PV (> 90%)", bess_charge_during_pv > 90),
    ("BESS descarga sincronizado con demanda (> 90%)", bess_discharge_during_demand > 90),
]

print(f"\n✅ Validaciones completadas:\n")
for check_name, check_result in checks:
    status = "✓" if check_result else "✗"
    print(f"   {status} {check_name}")

all_pass = all(result for _, result in checks)
print(f"\n{'='*80}")
if all_pass:
    print(f"✅ DATASET BESS VALIDADO - LISTO PARA CITYLEARN V2")
    print(f"   - Sincronización: ÓPTIMA")
    print(f"   - Desperdicios: CERO (< 0.1%)")
    print(f"   - Perfiles: SINCRONIZADOS")
    print(f"   - Columnas: TODAS PRESENTES + NUEVAS VALIDACIONES ADITIVAS")
else:
    print(f"⚠️ REVISAR VALIDACIONES")

print("="*80 + "\n")
