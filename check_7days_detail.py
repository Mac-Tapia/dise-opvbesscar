"""
Verificar los primeros 7 días de carga BESS por hora específica
"""

import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

# Primeros 7 días = 7 * 24 = 168 horas
df_7days = df.iloc[:168].copy()

print("\n" + "="*100)
print("DETALLE: Primeros 7 días - Carga BESS por hora")
print("="*100)
print(f"{'Hora Global':<15} {'Día':<6} {'Hora/Día':<12} {'PV Gen':<12} {'BESS Carga':<15} {'BESS Desc':<15} {'Status':<20}")
print("─" * 100)

problemas = []
for idx in range(len(df_7days)):
    hour_global = idx
    day = idx // 24 + 1
    hour_day = idx % 24
    
    pv = df_7days.iloc[idx]['pv_generation_kw']
    charge = df_7days.iloc[idx]['bess_charge_kw']
    discharge = df_7days.iloc[idx]['bess_discharge_kw']
    
    # Detectar problema
    status = "OK"
    if hour_day >= 15 and charge > 10:
        status = "❌ CARGA TARDE!"
        problemas.append((day, hour_day, charge))
    elif 6 <= hour_day < 15 and charge > 10:
        status = "✅ OK (mañana)"
    elif hour_day < 6 or hour_day >= 22:
        if charge > 0.1:
            status = "⚠️ FUERA HORARIO"
    
    if charge > 0.1 or discharge > 0.1:  # Solo mostrar si hay actividad BESS
        print(f"{hour_global:<15} {day:<6} {hour_day:02d}h-{hour_day+1:02d}h      {pv:>10,.0f}kW {charge:>13,.1f}kW {discharge:>13,.1f}kW {status:<20}")

print("\n" + "="*100)
if problemas:
    print(f"❌ PROBLEMAS ENCONTRADOS: {len(problemas)} horas con carga en la tarde")
    print("─" * 100)
    for day, hour, charge in problemas:
        print(f"   Día {day}, Hora {hour:02d}h: {charge:.1f} kW")
else:
    print("✅ SIN PROBLEMAS: No hay carga de BESS después de las 15h")

print("="*100)
