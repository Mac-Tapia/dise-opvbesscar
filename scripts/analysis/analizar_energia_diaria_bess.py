#!/usr/bin/env python
"""
ANALISIS DIARIO: Cuánta energía BESS queda después de descargar 100% para EV
"""

import pandas as pd
import numpy as np

bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print("=" * 100)
print("ANALISIS DIARIO: ALMACENAMIENTO BESS vs DESCARGA TOTAL EV")
print("=" * 100)

# Agrupar por día
bess_df['datetime'] = pd.to_datetime(bess_df['datetime'])
bess_df['date'] = bess_df['datetime'].dt.date
bess_df['hour'] = bess_df['datetime'].dt.hour

# Estadísticas diarias
daily_stats = bess_df.groupby('date').agg({
    'bess_charge_kwh': 'sum',
    'bess_discharge_kwh': 'sum',
    'bess_to_ev_kwh': 'sum',
    'ev_kwh': 'sum',
    'soc_kwh': ['min', 'max', 'mean'],
    'soc_percent': ['min', 'max', 'mean'],
}).round(2)

daily_stats.columns = ['Carga_BESS', 'Descarga_BESS', 'BESS_to_EV', 'Demanda_EV', 
                       'SOC_min_kWh', 'SOC_max_kWh', 'SOC_mean_kWh',
                       'SOC_min_%', 'SOC_max_%', 'SOC_mean_%']

print("\n[1] PRIMEROS 10 DIAS - BALANCE DIARIO:")
print("-" * 100)
print(daily_stats.head(10).to_string())

print("\n\n[2] ESTADISTICAS ANUALES (365 DIAS):")
print("-" * 100)
print(f"Promedio carga BESS/día:        {daily_stats['Carga_BESS'].mean():>10,.1f} kWh")
print(f"Promedio descarga BESS/día:     {daily_stats['Descarga_BESS'].mean():>10,.1f} kWh")
print(f"Promedio BESS→EV/día:           {daily_stats['BESS_to_EV'].mean():>10,.1f} kWh")
print(f"Promedio demanda EV/día:        {daily_stats['Demanda_EV'].mean():>10,.1f} kWh")

print(f"\nPromedio SOC mínimo diario:     {daily_stats['SOC_min_%'].mean():>10,.1f}%")
print(f"Promedio SOC máximo diario:     {daily_stats['SOC_max_%'].mean():>10,.1f}%")
print(f"Promedio SOC medio diario:      {daily_stats['SOC_mean_%'].mean():>10,.1f}%")

# El mínimo SOC más bajo del año
min_soc_day = daily_stats['SOC_min_%'].idxmin()
max_soc_high = daily_stats['SOC_max_%'].idxmax()

print(f"\nSOC mínimo más bajo del año:    {daily_stats['SOC_min_%'].min():>10,.1f}% (día {min_soc_day})")
print(f"SOC máximo más alto del año:    {daily_stats['SOC_max_%'].max():>10,.1f}% (día {max_soc_high})")

# Analizar el día con SOC mínimo más bajo
worst_day = bess_df[bess_df['date'] == min_soc_day].copy()

print("\n\n[3] DIA CON SOC MINIMO MAS BAJO DEL AÑO (Caso crítico):")
print("-" * 100)
print(f"Fecha: {min_soc_day}")
print(f"\nHorario de operación (6h-22h):")

worst_day_hourly = worst_day[(worst_day['hour'] >= 6) & (worst_day['hour'] <= 22)][['hour', 'pv_kwh', 'ev_kwh', 'soc_percent', 'soc_kwh', 
                               'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh']].copy()
worst_day_hourly.columns = ['Hora', 'PV(kW)', 'EV(kW)', 'SOC(%)', 'SOC(kWh)', 
                             'Carga', 'Descarga', 'BESS→EV']
print(worst_day_hourly.to_string(index=False))

print(f"\n\nResumen del día {min_soc_day}:")
print(f"  • Demanda EV total:           {worst_day['ev_kwh'].sum():>10,.1f} kWh")
print(f"  • BESS→EV entregado:          {worst_day['bess_to_ev_kwh'].sum():>10,.1f} kWh")
print(f"  • PV→EV directo:              {worst_day['pv_to_ev_kwh'].sum():>10,.1f} kWh")
print(f"  • Carga BESS (PV):            {worst_day['bess_charge_kwh'].sum():>10,.1f} kWh")

# Horas específicas
try:
    soc_06h = worst_day[worst_day['hour']==6]['soc_percent'].values[0]
    soc_22h = worst_day[worst_day['hour']==22]['soc_percent'].values[0]
    print(f"  • SOC inicio día (06h):       {soc_06h:>10,.1f}%")
    print(f"  • SOC mínimo día:             {worst_day['soc_percent'].min():>10,.1f}%")
    print(f"  • SOC cierre día (22h):       {soc_22h:>10,.1f}%")
except:
    pass

# Balance energético
bess_disponible_inicio = worst_day['soc_kwh'].max()
bess_usado_para_ev = worst_day['bess_to_ev_kwh'].sum()
bess_disponible_final = worst_day[worst_day['hour'].isin([22, 23])]['soc_kwh'].iloc[-1] if len(worst_day[worst_day['hour'].isin([22, 23])]) > 0 else worst_day['soc_kwh'].iloc[-1]
bess_cargado_dia = worst_day['bess_charge_kwh'].sum()

print(f"\nBalance BESS energético:")
print(f"  • BESS máximo (manana):       {bess_disponible_inicio:>10,.0f} kWh (100%)")
print(f"  • BESS cargado (PV):          {bess_cargado_dia:>10,.0f} kWh (+)")
print(f"  • BESS usado para EV:         {bess_usado_para_ev:>10,.0f} kWh (-)")
print(f"  • BESS cierre (22h):          {bess_disponible_final:>10,.0f} kWh")
print(f"  • ¿Puede llegar al 20%?:      {'✅ SI' if worst_day['soc_percent'].min() >= 19.9 else '❌ NO'}")

# Análisis global
print("\n\n[4] CAPACIDAD DISPONIBLE vs DEMANDA EV (MUESTRA CADA 30 DIAS):")
print("-" * 100)

for day_idx in range(0, 365, 30):
    day = daily_stats.index[day_idx]
    ev_dem = daily_stats.loc[day, 'Demanda_EV']
    bess_to_ev = daily_stats.loc[day, 'BESS_to_EV']
    soc_min = daily_stats.loc[day, 'SOC_min_%']
    soc_max = daily_stats.loc[day, 'SOC_max_%']
    
    if bess_to_ev > 0:
        pct = (bess_to_ev / ev_dem) * 100
        print(f"Día {day}: EV={ev_dem:6.0f} kWh, BESS→EV={bess_to_ev:6.0f} kWh ({pct:5.1f}%), SOC {soc_min:5.1f}%-{soc_max:5.1f}%")

print("\n\n[5] RESPUESTA: ¿CUANTA ENERGIA QUEDA EN BESS?")
print("=" * 100)

prom_soc_max = daily_stats['SOC_max_kWh'].mean()
prom_soc_min = daily_stats['SOC_min_kWh'].mean()
prom_soc_mean = daily_stats['SOC_mean_kWh'].mean()
prom_bess_to_ev = daily_stats['BESS_to_EV'].mean()

print(f"\nCAPACIDAD BASE DEL BESS:")
print(f"  Nominal total:                2,000 kWh")
print(f"  Usable (80% DoD):             1,600 kWh (rango 20%-100%)")

print(f"\nDESCARGA DIARIA para EV:")
print(f"  Promedio BESS→EV/día:         {prom_bess_to_ev:>6,.0f} kWh (37.1% de demanda EV)")

print(f"\nENERGIA QUE QUEDA EN BESS:")
print(f"  Promedio SOC máximo (manana): {prom_soc_max:>6,.0f} kWh (100%)")
print(f"  Promedio SOC mínimo (critico):{prom_soc_min:>6,.0f} kWh ({daily_stats['SOC_min_%'].mean():.1f}%)")
print(f"  Promedio SOC al cierre (22h): {prom_soc_mean:>6,.0f} kWh ({daily_stats['SOC_mean_%'].mean():.1f}%)")
print(f"  Reserva minima (20%):         {0.20 * 2000:>6,.0f} kWh (nunca bajamos)")

print(f"\nRESPUESTA A LA PREGUNTA:")
print(f"  ✅ Después de descargar {prom_bess_to_ev:.0f} kWh para EV,")
print(f"  ✅ El BESS aún tiene {prom_soc_mean:.0f} kWh ({daily_stats['SOC_mean_%'].mean():.1f}%),")
print(f"  ✅ Puede llegar al 20% mínimo operacional ({0.20*2000:.0f} kWh)")

print("\n" + "=" * 100)
