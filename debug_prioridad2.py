#!/usr/bin/env python
"""Debug: Analizar por qué PRIORIDAD 2 no funciona"""
import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

print("\n" + "="*100)
print("DEBUG: PRIORIDAD 2 - ¿Por qué NO descarga a MALL después de EV?")
print("="*100)

# Día 1 específicamente
data_day1 = df[df['day'] == 1].copy()

print("\n[DÍA 1 - DESGLOSE HORA A HORA (18h-22h)]")
print("-"*100)
print("HORA | SOC_% | EV_kW | MALL_kW | BESS_CH | BESS_DS | EV_from_BESS | MALL_from_BESS | total_to_MALL")
print("-"*100)

for h in range(18, 23):
    row = data_day1[data_day1['hour'] == h]
    if len(row) == 0:
        continue
    row = row.iloc[0]
    
    soc = row['bess_soc_percent']
    ev = row['ev_demand_kwh']
    mall = row['mall_demand_kwh']
    bess_ch = row['bess_charge_kwh']
    bess_ds = row['bess_discharge_kwh']
    ev_from_bess = row['bess_to_ev_kwh'] if 'bess_to_ev_kwh' in row.index else 0
    mall_from_bess = row['bess_to_mall_kwh'] if 'bess_to_mall_kwh' in row.index else 0
    
    print(f" {h:02d}h | {soc:5.1f} | {ev:5.0f} | {mall:7.0f} | {bess_ch:7.0f} | {bess_ds:7.0f} | {ev_from_bess:12.0f} | {mall_from_bess:14.0f} | {ev_from_bess + mall_from_bess:13.0f}")

print("\n[ANÁLISIS DE PATRÓN]")
print("-"*100)

# Ver si hay algún día donde sí hay descarga a MALL
days_with_mall_discharge = df.groupby('day')['bess_to_mall_kwh'].sum()
days_with_mall = days_with_mall_discharge[days_with_mall_discharge > 100]

print(f"Días con >100 kWh descarga a MALL: {len(days_with_mall)} de 365")
if len(days_with_mall) > 0:
    sample_day = days_with_mall.index[0]
    print(f"\nAnalizando día {sample_day} (que tiene descarga a MALL):")
    
    data_sample = df[df['day'] == sample_day]
    for h in range(18, 23):
        row = data_sample[data_sample['hour'] == h]
        if len(row) == 0:
            continue
        row = row.iloc[0]
        
        soc = row['bess_soc_percent']
        ev = row['ev_demand_kwh']
        mall = row['mall_demand_kwh']
        bess_ds = row['bess_discharge_kwh']
        ev_from_bess = row['bess_to_ev_kwh'] if 'bess_to_ev_kwh' in row.index else 0
        mall_from_bess = row['bess_to_mall_kwh'] if 'bess_to_mall_kwh' in row.index else 0
        
        print(f"  {h:02d}h: SOC={soc:5.1f}% | Descarga={bess_ds:6.0f} | EV_BESS={ev_from_bess:6.0f} | MALL_BESS={mall_from_bess:6.0f}")

print("\n[DIAGNÓSTICO FINAL]")
print("-"*100)

# Calcular cuánto va a MALL durante 18h-22h
total_discharge_18_22 = df[(df['hour'] >= 18) & (df['hour'] <= 22)]['bess_discharge_kwh'].sum()
total_to_ev_18_22 = df[(df['hour'] >= 18) & (df['hour'] <= 22)]['bess_to_ev_kwh'].sum()
total_to_mall_18_22 = df[(df['hour'] >= 18) & (df['hour'] <= 22)]['bess_to_mall_kwh'].sum()

print(f"\nTOTAL 18h-22h:")
print(f"  - BESS DESCARGA TOTAL: {total_discharge_18_22:>10,.0f} kWh")
print(f"  - Que va a EV:        {total_to_ev_18_22:>10,.0f} kWh")
print(f"  - Que va a MALL:      {total_to_mall_18_22:>10,.0f} kWh")
print(f"  - Diferencia (log):   {total_discharge_18_22 - (total_to_ev_18_22 + total_to_mall_18_22):>10,.0f} kWh")

if total_to_mall_18_22 < 10:
    print(f"\n  ✗ CRÍTICO: BESS casi NO descarga a MALL (solo {total_to_mall_18_22:.0f} kWh en 5h)")
    print(f"    → PRIORIDAD 2 se está ignorando o NO se ejecuta")
    print(f"    → Posibles causas:")
    print(f"       1. Función calculate_max_discharge_to_mall() devuelve 0")
    print(f"       2. Condición if(...max_discharge_power_kw...) NO se cumple")
    print(f"       3. remaining_discharge_power está a 0 después de PRIORIDAD 1")

print("\n" + "="*100)
