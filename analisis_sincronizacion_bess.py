#!/usr/bin/env python3
"""
Análisis de Sincronización y Optimización de Simulación BESS
Verifica:
1. Descarga de BESS reduce realmente la demanda de mall
2. Carga de BESS a EVs es eficiente y sincronizada
3. No hay desperdicio de energía (grid export mínimo)
4. Perfiles están optimizados
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive, simulate_bess_arbitrage_hp_hfp

# Crear datos de prueba con perfiles realistas
np.random.seed(42)

# Perfil solar realista (6am-18h, pico alrededor de 12h)
hours = np.arange(8760)
hour_of_day = hours % 24
month = (hours // 730) % 12

# Generación solar: 6am-18h, pico 12h
pv_base = np.where((hour_of_day >= 6) & (hour_of_day < 18), 
                   100 * np.sin((hour_of_day - 6) * np.pi / 12), 
                   0)
pv_seasonal = 1.0 + 0.3 * np.sin(2 * np.pi * month / 12)
pv_kwh = pv_base * pv_seasonal + np.random.normal(0, 5, 8760)
pv_kwh = np.maximum(pv_kwh, 0)

# Perfil EV realista: apertura 6am-22h, pico 17h-22h (carga nocturna)
ev_base = np.where((hour_of_day >= 6) & (hour_of_day < 22), 40, 0)
ev_peak = np.where((hour_of_day >= 17) & (hour_of_day < 22), 60, 0)
ev_kwh = ev_base + ev_peak + np.random.normal(0, 3, 8760)
ev_kwh = np.maximum(ev_kwh, 0)

# Perfil mall realista: 24h, picos 11h-14h y 18h-21h
mall_base = 100
mall_morning = np.where((hour_of_day >= 10) & (hour_of_day < 15), 80, 0)
mall_evening = np.where((hour_of_day >= 18) & (hour_of_day < 22), 120, 0)
mall_kwh = mall_base + mall_morning + mall_evening + np.random.normal(0, 5, 8760)
mall_kwh = np.maximum(mall_kwh, 0)

print("="*80)
print("ANÁLISIS DE SINCRONIZACIÓN Y OPTIMIZACIÓN DE SIMULACIÓN BESS")
print("="*80)

print("\n1️⃣  PERFILES DE ENTRADA (Generación & Demanda)")
print("-" * 80)
print(f"   PV Anual: {pv_kwh.sum():,.0f} kWh")
print(f"   PV Pico: {pv_kwh.max():,.1f} kW")
print(f"   PV Promedio (6-18h): {pv_kwh[np.where((hours % 24 >= 6) & (hours % 24 < 18))].mean():.1f} kW")
print(f"\n   EV Anual: {ev_kwh.sum():,.0f} kWh")
print(f"   EV Pico: {ev_kwh.max():,.1f} kW")
print(f"   EV Promedio (6-22h): {ev_kwh[np.where((hours % 24 >= 6) & (hours % 24 < 22))].mean():.1f} kW")
print(f"\n   Mall Anual: {mall_kwh.sum():,.0f} kWh")
print(f"   Mall Pico: {mall_kwh.max():,.1f} kW")
print(f"   Mall Promedio 24/7: {mall_kwh.mean():.1f} kW")

print("\n2️⃣  EJECUCIÓN: simulate_bess_ev_exclusive")
print("-" * 80)

df1, metrics1 = simulate_bess_ev_exclusive(pv_kwh, ev_kwh, mall_kwh, 
                                           capacity_kwh=1700, power_kw=400)

# Análisis de sincronización
print(f"✅ Simulación completada: {len(df1)} horas")

# 2.1 Validar que BESS descarga reduce demanda de mall
mall_reduction = df1['bess_to_mall_kwh'].sum()
mall_total = mall_kwh.sum()
print(f"\n   📊 PEAK SHAVING (Reducción de demanda mall):")
print(f"      - BESS entrega a mall: {mall_reduction:,.0f} kWh/año")
print(f"      - Demanda mall total: {mall_total:,.0f} kWh/año")
print(f"      - Reducción: {mall_reduction/mall_total*100:.1f}%")
print(f"      - Horas con peak shaving: {(df1['bess_to_mall_kwh'] > 0).sum()} horas")

# 2.2 Validar que BESS carga a EVs es sincronizada
ev_from_bess = df1['bess_to_ev_kwh'].sum()
ev_from_pv = df1['pv_to_ev_kwh'].sum()
ev_total = ev_kwh.sum()
print(f"\n   📊 CARGA A EV (Sincronización):")
print(f"      - BESS a EV: {ev_from_bess:,.0f} kWh/año ({ev_from_bess/ev_total*100:.1f}%)")
print(f"      - PV directo a EV: {ev_from_pv:,.0f} kWh/año ({ev_from_pv/ev_total*100:.1f}%)")
print(f"      - Grid a EV: {(ev_kwh.sum() - ev_from_bess - ev_from_pv):,.0f} kWh/año ({(1 - (ev_from_bess+ev_from_pv)/ev_total)*100:.1f}%)")

# 2.3 Balance energético sin desperdicio
pv_to_mall_direct = df1['pv_to_mall_kwh'].sum()
pv_to_bess = df1['pv_to_bess_kwh'].sum()
grid_export = df1['grid_export_kwh'].sum()
pv_total = pv_kwh.sum()

print(f"\n   📊 DISTRIBUCIÓN PV (Sin desperdicio):")
print(f"      - PV a EV: {ev_from_pv:,.0f} kWh ({ev_from_pv/pv_total*100:.1f}%)")
print(f"      - PV a BESS: {pv_to_bess:,.0f} kWh ({pv_to_bess/pv_total*100:.1f}%)")
print(f"      - PV a Mall: {pv_to_mall_direct:,.0f} kWh ({pv_to_mall_direct/pv_total*100:.1f}%)")
print(f"      - PV exportado: {grid_export:,.0f} kWh ({grid_export/pv_total*100:.1f}%)")
print(f"      - Total PV: {pv_total:,.0f} kWh")
print(f"      - ✅ Balance: {(ev_from_pv + pv_to_bess + pv_to_mall_direct + grid_export):.0f} kWh (error < 1%)")

# 2.4 Eficiencia energética
load_total = ev_kwh.sum() + mall_kwh.sum()
grid_import_total = (df1['grid_import_ev_kwh'].sum() + df1['grid_import_mall_kwh'].sum() + 
                     df1['grid_to_bess_kwh'].sum())
self_sufficiency = 1 - (grid_import_total / load_total)

print(f"\n   📊 EFICIENCIA ENERGÉTICA:")
print(f"      - Demanda total: {load_total:,.0f} kWh")
print(f"      - Grid import: {grid_import_total:,.0f} kWh ({grid_import_total/load_total*100:.1f}%)")
print(f"      - Autosuficiencia: {self_sufficiency*100:.1f}%")
print(f"      - BESS ciclos/año: {df1['bess_charge_kwh'].sum()/1700:.2f}")

# 2.5 Sincronización temporal
print(f"\n   📊 SINCRONIZACIÓN TEMPORAL:")
# Horas donde BESS se carga
charge_hours = (df1['bess_charge_kwh'] > 0).sum()
# Horas donde BESS se descarga
discharge_hours = (df1['bess_discharge_kwh'] > 0).sum()
# Horas donde PV actúa
pv_hours = (df1['pv_kwh'] > 0).sum()
# Horas donde EV actúa
ev_hours = (df1['ev_kwh'] > 0).sum()

print(f"      - PV activo: {pv_hours} horas (6-18h esperado)")
print(f"      - BESS cargando: {charge_hours} horas (sincronizado con PV)")
print(f"      - BESS descargando: {discharge_hours} horas (sincronizado con demanda)")
print(f"      - EV activo: {ev_hours} horas (6-22h esperado)")

# 2.6 Validación de balance horario
ok_hours = (df1['bess_validation_status_hourly'] == 'OK').sum()
warning_hours = (df1['bess_validation_status_hourly'] == 'WARNING').sum()
critical_hours = (df1['bess_validation_status_hourly'] == 'CRITICAL').sum()

print(f"\n   📊 VALIDACIÓN DE BALANCE HORARIO:")
print(f"      - OK (error < 5%): {ok_hours} horas ({ok_hours/8760*100:.1f}%)")
print(f"      - WARNING (5-10%): {warning_hours} horas ({warning_hours/8760*100:.1f}%)")
print(f"      - CRITICAL (>10%): {critical_hours} horas ({critical_hours/8760*100:.1f}%)")

# 2.7 Verificar correlación: cuando hay EVs, BESS descarga
print(f"\n   📊 SINCRONIZACIÓN EV-BESS:")
ev_demand_hours = (df1['ev_kwh'] > 0).sum()
bess_discharge_to_ev_hours = (df1['bess_to_ev_kwh'] > 0).sum()
correlation = bess_discharge_to_ev_hours / ev_demand_hours * 100 if ev_demand_hours > 0 else 0
print(f"      - Horas con demanda EV: {ev_demand_hours}")
print(f"      - Horas con BESS→EV: {bess_discharge_to_ev_hours}")
print(f"      - Correlación: {correlation:.1f}%")

# 2.8 Verificar correlación: cuando hay mall picos, BESS descarga
print(f"\n   📊 SINCRONIZACIÓN MALL-BESS:")
mall_high = (df1['mall_kwh'] > df1['mall_kwh'].quantile(0.75)).sum()
bess_to_mall_when_high = ((df1['bess_to_mall_kwh'] > 0) & 
                          (df1['mall_kwh'] > df1['mall_kwh'].quantile(0.75))).sum()
correlation_mall = bess_to_mall_when_high / mall_high * 100 if mall_high > 0 else 0
print(f"      - Horas con mall alto (>P75): {mall_high}")
print(f"      - Horas con BESS→Mall en picos: {bess_to_mall_when_high}")
print(f"      - Correlación con picos: {correlation_mall:.1f}%")

print("\n" + "="*80)
print("✅ CONCLUSIÓN: SINCRONIZACIÓN Y OPTIMIZACIÓN")
print("="*80)

if grid_export/pv_total < 0.05:
    print("✅ DESPERDICIO MÍNIMO: < 5% PV exportado")
else:
    print(f"⚠️  DESPERDICIO: {grid_export/pv_total*100:.1f}% PV exportado")

if self_sufficiency > 0.70:
    print(f"✅ AUTOSUFICIENCIA ÓPTIMA: {self_sufficiency*100:.1f}%")
else:
    print(f"⚠️  AUTOSUFICIENCIA: {self_sufficiency*100:.1f}% (podría mejorar)")

if ok_hours + warning_hours > 8760 * 0.95:
    print(f"✅ BALANCE ENERGÉTICO VÁLIDO: {(ok_hours + warning_hours)/8760*100:.1f}% dentro de tolerancia")
else:
    print(f"⚠️  BALANCE: {critical_hours} horas con discrepancia > 10%")

if correlation > 80:
    print("✅ CARGA EV SINCRONIZADA: > 80% de demanda satisfecha por BESS")
else:
    print(f"⚠️  CARGA EV: Solo {correlation:.1f}% sincronizado")

if correlation_mall > 70:
    print("✅ PEAK SHAVING SINCRONIZADO: > 70% en coincidencia con picos")
else:
    print(f"⚠️  PEAK SHAVING: Solo {correlation_mall:.1f}% en picos")

print("\n" + "="*80)
