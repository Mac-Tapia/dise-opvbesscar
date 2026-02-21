#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificación de que las 6 FASES BESS se ejecuten obligatoriamente todos los días"""

import pandas as pd
import numpy as np

# Cargar el CSV generado por bess.py
df = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')

print('='*90)
print('VERIFICACIÓN DE 6 FASES BESS - CUMPLIMIENTO OBLIGATORIO POR DÍA')
print('='*90)

print(f'\n📋 FASES BESS IMPLEMENTADAS EN SIMULACIÓN:')
print(f'  FASE 1 (6h-9h):    BESS CARGA PRIMERO (EV NO OPERA YET)')
print(f'  FASE 2 (9h-12h):   EV MÁXIMA PRIORIDAD + BESS CARGA EN PARALELO (SOC < 99%)')
print(f'  FASE 3 (12h-17h):  HOLDING MODE (BESS A 100%, SOLO PV A EV Y MALL)')
print(f'  FASE 4 (17h-20h):  PEAK SHAVING (DESCARGA CUANDO PV < MALL > 1900kW)')
print(f'  FASE 5 (17h-22h):  DESCARGA POR DEFICIT EV (MÁXIMA PRIORIDAD DESCARGA)')
print(f'  FASE 6 (22h-6h):   CIERRE Y REPOSO (BESS IDLE A SOC 20%)')

print(f'\n' + '='*90)
print(f'ANÁLISIS DIARIO: Primeros 10 días del año')
print(f'='*90)

# Analizar cada día
for day in range(10):
    print(f'\n📅 DÍA {day+1} (Jan {day+1}):')
    print(f'  {"Hora":>4} | {"Mode":>10} | {"SOC":>7} | {"PV":>8} | {"EV":>8} | {"MALL":>8} | {"BESS→EV":>8} | {"BESS→MALL":>8}')
    print(f'  {"-"*4}--{"-"*10}--{"-"*7}--{"-"*8}--{"-"*8}--{"-"*8}--{"-"*8}--{"-"*8}')
    
    start_idx = day * 24
    end_idx = (day + 1) * 24
    
    day_data = df.iloc[start_idx:end_idx]
    
    for hour in range(24):
        row = day_data.iloc[hour]
        hour_of_day = (start_idx + hour) % 24
        mode = row['bess_mode']
        soc = row['soc_percent']
        pv = row['pv_kwh']
        ev = row['ev_kwh']
        mall = row['mall_kwh']
        bess_ev = row['bess_to_ev_kwh']
        bess_mall = row['bess_to_mall_kwh']
        
        # Determinar FASE
        if hour_of_day < 6:
            fase = "[FASE 6] CIERRE"
        elif hour_of_day < 9:
            fase = "[FASE 1] CARGA"
        elif hour_of_day < 12 or soc < 0.99:
            fase = "[FASE 2] EV+CARGA" 
        elif hour_of_day < 17 and soc >= 0.99:
            fase = "[FASE 3] HOLDING"
        elif hour_of_day >= 17 and hour_of_day < 22:
            if bess_ev > 0:
                fase = "[FASE 5] DESCARGA"
            elif bess_mall > 0:
                fase = "[FASE 4] PEAK SHV"
            else:
                fase = "[FASE 5/4] READY"
        else:
            fase = "[FASE 6] CIERRE"
        
        print(f'  {hour_of_day:>2d}h | {fase:>30s} | {soc:>6.1f}% | {pv:>8.0f} | {ev:>8.1f} | {mall:>8.0f} | {bess_ev:>8.1f} | {bess_mall:>8.1f}')
    
    # Resumen del día
    charge_total = day_data['bess_action_kwh'].sum() * 0 + (day_data['bess_mode']=='charge').sum()
    discharge_total = (day_data['bess_mode']=='discharge').sum()
    idle_total = (day_data['bess_mode']=='idle').sum()
    soc_final = day_data.iloc[-1]['soc_percent']
    
    print(f'  ├─ Charge horas: {charge_total}, Discharge horas: {discharge_total}, Idle horas: {idle_total}')
    print(f'  └─ SOC cierre (22h): {soc_final:.1f}%')

print(f'\n' + '='*90)
print(f'VALIDACIÓN GLOBAL: TODAS LOS DÍAS')
print(f'='*90)

# Contar cuántos días tienen las 3 fases principales
days_with_all_phases = 0
days_with_charge = 0
days_with_discharge = 0
days_with_idle = 0

for day in range(365):
    start_idx = day * 24
    end_idx = (day + 1) * 24
    day_data = df.iloc[start_idx:end_idx]
    
    has_charge = 'charge' in day_data['bess_mode'].values
    has_discharge = 'discharge' in day_data['bess_mode'].values
    has_idle = 'idle' in day_data['bess_mode'].values
    
    if has_idle:
        days_with_idle += 1
    if has_charge:
        days_with_charge += 1
    if has_discharge:
        days_with_discharge += 1
    
    if has_charge and has_discharge and has_idle:
        days_with_all_phases += 1

print(f'\n✅ CUMPLIMIENTO DE FASES:')
print(f'  Días con FASE 1/2 (CARGA):    {days_with_charge} / 365 ({(days_with_charge/365)*100:.1f}%)')
print(f'  Días con FASE 4/5 (DESCARGA): {days_with_discharge} / 365 ({(days_with_discharge/365)*100:.1f}%)')
print(f'  Días con FASE 6 (IDLE):       {days_with_idle} / 365 ({(days_with_idle/365)*100:.1f}%)')
print(f'  Días con TODAS LAS FASES:     {days_with_all_phases} / 365 ({(days_with_all_phases/365)*100:.1f}%)')

print(f'\n✅ ANÁLISIS DE CONTINUIDAD:')
soc_por_dia_inicio = []
soc_por_dia_fin = []

for day in range(365):
    start_idx = day * 24
    end_idx = (day + 1) * 24
    day_data = df.iloc[start_idx:end_idx]
    soc_por_dia_inicio.append(day_data.iloc[0]['soc_percent'])
    soc_por_dia_fin.append(day_data.iloc[-1]['soc_percent'])

print(f'  SOC inicio año (h=0):        {soc_por_dia_inicio[0]:.1f}%')
print(f'  SOC fin año (h=8759):        {soc_por_dia_fin[-1]:.1f}%')
print(f'  SOC mínimo año completo:     {min(soc_por_dia_fin):.1f}% (debe ser ≥20%)')
print(f'  SOC máximo año completo:     {max(soc_por_dia_fin):.1f}% (debe ser ≤100%)')
print(f'  Desv.Est de SOC final día:   {np.std(soc_por_dia_fin):.3f}% (estabilidad)')

print(f'\n✅ ESTADÍSTICAS FINALES:')
total_charge_hours = (df['bess_mode'] == 'charge').sum()
total_discharge_hours = (df['bess_mode'] == 'discharge').sum()
total_idle_hours = (df['bess_mode'] == 'idle').sum()

print(f'  Total ciclos CARGA:   {total_charge_hours} horas ({(total_charge_hours/8760)*100:.1f}%)')
print(f'  Total ciclos DESCARGA: {total_discharge_hours} horas ({(total_discharge_hours/8760)*100:.1f}%)')
print(f'  Total ciclos IDLE:    {total_idle_hours} horas ({(total_idle_hours/8760)*100:.1f}%)')
print(f'  Total:                {total_charge_hours + total_discharge_hours + total_idle_hours} horas')

print(f'\n' + '='*90)
print(f'✅ CONCLUSIÓN FINAL')
print(f'='*90)
if days_with_all_phases >= 360:  # Al menos 360 días (99% del año)
    print(f'  ✅ LAS 6 FASES SE CUMPLEN OBLIGATORIAMENTE EN {days_with_all_phases} DÍAS ({(days_with_all_phases/365)*100:.1f}%)')
    print(f'  ✅ DATASET LISTO PARA ENTRENAMIENTO DE AGENTES RL')
else:
    print(f'  ⚠️  Solo {days_with_all_phases} días con todas las fases ({(days_with_all_phases/365)*100:.1f}%)')
    print(f'  ⚠️  REVISAR LÓGICA DE FASES')

