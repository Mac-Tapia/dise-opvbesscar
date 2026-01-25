"""Verificar perfiles de generación y carga para validar gráfica."""
import pandas as pd
import numpy as np

print("="*80)
print("VERIFICACIÓN DE PERFILES REALES")
print("="*80)

# 1. Perfil Solar
print("\n1. PERFIL DE GENERACIÓN SOLAR:")
print("-" * 40)
df_pv = pd.read_csv('data/oe2/pv_profile_24h.csv')
print(df_pv[['hour', 'pv_kwh']])
print(f"\nTotal generación: {df_pv['pv_kwh'].sum():.1f} kWh/día")
print(f"Horas con generación: {df_pv[df_pv['pv_kwh'] > 0]['hour'].min()}-{df_pv[df_pv['pv_kwh'] > 0]['hour'].max()}h")

# 2. Perfil EV (convertido a horario)
print("\n2. PERFIL DE CARGA EV (MOTOS/MOTOTAXIS):")
print("-" * 40)
df_ev = pd.read_csv('data/oe2/perfil_horario_carga.csv')

# Si es de 15 min, convertir a horario
if len(df_ev) == 96 or len(df_ev) == 35040:
    print(f"Detectado perfil de 15 min ({len(df_ev)} intervalos)")
    if len(df_ev) == 96:
        # Expandir a año
        df_ev_year = pd.concat([df_ev] * 365, ignore_index=True)
    else:
        df_ev_year = df_ev.copy()

    # Convertir a horario
    df_ev_year['hour'] = df_ev_year['interval'] // 4
    df_ev_hourly = df_ev_year.groupby('hour')['energy_kwh'].mean().reset_index()
    df_ev_hourly.columns = ['hour', 'ev_kwh']
else:
    df_ev_hourly = df_ev.copy()
    df_ev_hourly.columns = ['hour', 'ev_kwh']

print(df_ev_hourly[['hour', 'ev_kwh']])
print(f"\nTotal demanda EV: {df_ev_hourly['ev_kwh'].sum():.1f} kWh/día")
print(f"Horas con demanda: {df_ev_hourly[df_ev_hourly['ev_kwh'] > 0]['hour'].min()}-{df_ev_hourly[df_ev_hourly['ev_kwh'] > 0]['hour'].max()}h")

# 3. Déficit EV en horario nocturno (18-22h)
print("\n3. ANÁLISIS DÉFICIT EV (18h-22h):")
print("-" * 40)
deficit_hours = range(18, 23)
ev_deficit = df_ev_hourly[df_ev_hourly['hour'].isin(deficit_hours)]['ev_kwh'].sum()
pv_deficit = df_pv[df_pv['hour'].isin(deficit_hours)]['pv_kwh'].sum()
print(f"Demanda EV 18h-22h: {ev_deficit:.1f} kWh/día")
print(f"Generación PV 18h-22h: {pv_deficit:.1f} kWh/día")
print(f"Déficit neto: {ev_deficit - pv_deficit:.1f} kWh/día")

print("\n" + "="*80)
