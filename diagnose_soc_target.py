#!/usr/bin/env python
"""Diagnóstico: Verificar por qué SOC no llega a 20% exacto en cierre (22h)"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

print("\n" + "="*90)
print("DIAGNÓSTICO: SOC Final a las 22h (Target: 20.0%, Actual: 27.8%)")
print("="*90)

# Análisis de 3 días representativos
test_days = [1, 100, 250]  # Primero, mitad, final

for day in test_days:
    data_day = df[df['day'] == day]
    if len(data_day) == 0:
        continue
    
    print(f"\n[ANÁLISIS DÍA {day:3d}]")
    print("-"*90)
    
    # Mostrar evolución de SOC cada hora
    for h in range(6, 24):
        data_h = data_day[data_day['hour'] == h]
        if len(data_h) == 0:
            continue
        
        row = data_h.iloc[0]
        soc = row['bess_soc_percent']
        pv = row['pv_generation_kwh']
        ev = row['ev_demand_kwh']
        mall = row['mall_demand_kwh']
        ch = row['bess_charge_kwh']
        dsch = row['bess_discharge_kwh']
        to_mall = row['bess_to_mall_kwh'] if 'bess_to_mall_kwh' in row.index else 0
        mode = row['bess_mode'] if 'bess_mode' in row.index else '?'
        
        print(f"  {h:02d}h: SOC={soc:>5.1f}% | PV={pv:>6.0f}kW | EV={ev:>5.0f}kW | MALL={mall:>6.0f}kW | " +
              f"Ch={ch:>4.0f} Ds={dsch:>4.0f} ToMall={to_mall:>4.0f} | {mode:>8s}")
    
    # SOC a las 22h
    soc_22h = data_day[data_day['hour'] == 22]['bess_soc_percent'].values
    if len(soc_22h) > 0:
        print(f"\n  → SOC a las 22h: {soc_22h[0]:.1f}% (Target: 20.0%, Delta: {soc_22h[0]-20.0:+.1f}%)")

print("\n" + "="*90)
print("ANÁLISIS AGREGADO (TODO EL AÑO)")
print("="*90)

# Comprobar si calculate_max_discharge_to_mall realmente estállamándose
print(f"\nESTADÍSTICAS CLAVE:")
print(f"  - SOC mínimo en cierre (22h): {df[df['hour']==22]['bess_soc_percent'].min():.1f}%")
print(f"  - SOC máximo en cierre (22h): {df[df['hour']==22]['bess_soc_percent'].max():.1f}%")
print(f"  - SOC promedio en cierre (22h): {df[df['hour']==22]['bess_soc_percent'].mean():.1f}%")

# Analizar descarga a MALL
print(f"\nDESCARGA A MALL (debería ser mucho mayor si v5.5 funciona):")
for h in range(6, 24):
    total_mall_h = df[df['hour']==h]['bess_to_mall_kwh'].sum() if 'bess_to_mall_kwh' in df.columns else 0
    avg_mall_h = total_mall_h / 365
    print(f"  {h:02d}h: {avg_mall_h:>6.0f} kWh/día (total anual: {total_mall_h:>10,.0f} kWh)")

total_to_mall = df['bess_to_mall_kwh'].sum() if 'bess_to_mall_kwh' in df.columns else 0
print(f"  TOTAL ANUAL: {total_to_mall:,.0f} kWh (v5.4 esperaba 265k, v5.5 debería >400k)")

# Analizar si hay cambios de descarga después de las 17h
print(f"\nANÁLISIS '17h-22h' (Ventana descarga propuesta):")
discharge_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['bess_discharge_kwh'].sum()
print(f"  Total descarga 17h-22h: {discharge_17_22:,.0f} kWh/año")

# DIAGNÓSTICO: ¿Se está llamando calculate_max_discharge_to_mall()?
print(f"\nDIAGNÓSTICO: Verificar si PRIORIDAD 2 se ejecuta...")
print(f"  Si SOC final promedio = 27.8% (sin cambio v5.4), entonces:")
print(f"    ✗ calculate_max_discharge_to_mall() NO se está ejecutando")
print(f"    ✗ O se ejecuta pero devuelve valores incorrectos (unidades/cálculo)")
print(f"    ✗ O hay un problema de indentación/flujo en el código")

print("\n" + "="*90)
