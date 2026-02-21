#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnosticar inconsistencias en Día 7 y Día 8"""
import pandas as pd
import numpy as np

# Cargar datos
bess_data = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')

# Día 7 = horas 144-167 (6 días × 24 + 0 = 144, hasta 167)
# Día 8 = horas 168-191

print("=" * 80)
print("DIAGNÓSTICO: Día 7 y Día 8 - Inconsistencia Carga/Descarga")
print("=" * 80)

for day_num, day_name, start_hour, end_hour in [
    (7, "DÍA 7", 144, 167),
    (8, "DÍA 8", 168, 191),
]:
    print(f"\n{'=' * 80}")
    print(f"{day_name} (horas {start_hour}-{end_hour})")
    print(f"{'=' * 80}")
    
    day_data = bess_data.iloc[start_hour:end_hour+1].copy()
    day_data['local_hour'] = (day_data.index % 24).values
    
    print(f"\nCOLUMNAS: {list(day_data.columns)}")
    print(f"\nDatos por hora:")
    print(day_data[['local_hour', 'bess_action_kwh', 'bess_mode', 'pv_to_bess_kwh', 
                     'bess_to_ev_kwh', 'bess_to_mall_kwh']].to_string())
    
    # Análisis
    print(f"\n{'─' * 80}")
    print("ANÁLISIS DE INCONSISTENCIAS:")
    print(f"{'─' * 80}")
    
    # Identificar horas donde hay carga Y descarga simultáneamente
    has_charge = day_data['pv_to_bess_kwh'] > 0.1
    has_discharge = (day_data['bess_to_ev_kwh'] + day_data['bess_to_mall_kwh']) > 0.1
    simultaneous = has_charge & has_discharge
    
    if simultaneous.any():
        print(f"\n❌ PROBLEMA ENCONTRADO: {simultaneous.sum()} horas con carga Y descarga simultánea:")
        problem_hours = day_data[simultaneous][['local_hour', 'pv_to_bess_kwh', 
                                                  'bess_to_ev_kwh', 'bess_to_mall_kwh', 'bess_mode']]
        print(problem_hours.to_string())
    else:
        print(f"\n✓ NO hay horas con carga Y descarga simultánea")
    
    # Contar horas por fase
    charge_hours = (day_data['pv_to_bess_kwh'] > 0.1).sum()
    discharge_hours = ((day_data['bess_to_ev_kwh'] + day_data['bess_to_mall_kwh']) > 0.1).sum()
    idle_hours = 24 - max(charge_hours, discharge_hours)  # Aproximado
    
    print(f"\nRESUMEN POR FASE:")
    print(f"  Horas CARGANDO (pv_to_bess > 0.1 kW):    {charge_hours}")
    print(f"  Horas DESCARGANDO (bess_to_* > 0.1 kW): {discharge_hours}")
    print(f"  Horas REPOSO/HOLDING:                     {24 - max(charge_hours, discharge_hours)}")
    
    # Verificar totales de carga/descarga
    total_charge = day_data['pv_to_bess_kwh'].sum()
    total_discharge = (day_data['bess_to_ev_kwh'] + day_data['bess_to_mall_kwh']).sum()
    soc_change = day_data['bess_soc_percent'].iloc[-1] - day_data['bess_soc_percent'].iloc[0]
    
    print(f"\nENERGÍA DEL DÍA:")
    print(f"  Total CARGADO (pv_to_bess):              {total_charge:8.1f} kWh")
    print(f"  Total DESCARGADO (bess_to_ev+mall):     {total_discharge:8.1f} kWh")
    print(f"  Variación SOC (inicio→fin):              {soc_change:8.1f}%")
    print(f"  Balance esperado:                        {total_charge - total_discharge:8.1f} kWh")
    
    # Detalle por modo
    print(f"\nDETALLE POR MODO:")
    for mode in day_data['bess_mode'].unique():
        mode_data = day_data[day_data['bess_mode'] == mode]
        print(f"  {mode:15s}: {len(mode_data):2d} horas | Carga: {mode_data['pv_to_bess_kwh'].sum():7.1f} | "
              f"Descarga: {(mode_data['bess_to_ev_kwh'] + mode_data['bess_to_mall_kwh']).sum():7.1f} kWh")

print("\n" + "=" * 80)
print("FIN DIAGNÓSTICO")
print("=" * 80)
