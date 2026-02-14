#!/usr/bin/env python3
"""
Análisis de Peak Shaving del BESS - PPO v5.3
=============================================
Analiza cuánta demanda pico del mall (>2000 kW) corta el BESS.

Métricas:
- Por hora: Picos cortados en hora punta (18:00-22:00)
- Por día: Energía total de picos cortados
- Por mes: Agregación mensual
- Por año: Total anual
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
PEAK_THRESHOLD_KW = 2000  # Umbral de pico (kW)
PEAK_HOURS = list(range(18, 23))  # Horas punta: 18:00-22:00
BESS_MAX_DISCHARGE_KW = 342  # Máxima descarga BESS (kW)

# ==============================================================================
# CARGAR DATOS
# ==============================================================================
print("=" * 70)
print("ANÁLISIS DE PEAK SHAVING DEL BESS - PPO v5.3")
print("=" * 70)

# 1. Cargar demanda del mall
mall_path = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
mall_df = pd.read_csv(mall_path, sep=';', names=['datetime', 'demand_kwh'], skiprows=1)
mall_df['datetime'] = pd.to_datetime(mall_df['datetime'], format='%d/%m/%Y %H:%M')
mall_df['demand_kw'] = mall_df['demand_kwh']  # Ya está en kW (potencia promedio hora)

print(f"\n[1] DEMANDA MALL:")
print(f"    Registros: {len(mall_df):,}")
print(f"    Rango: {mall_df['datetime'].min()} a {mall_df['datetime'].max()}")
print(f"    Demanda: min={mall_df['demand_kw'].min():.0f} kW, max={mall_df['demand_kw'].max():.0f} kW, mean={mall_df['demand_kw'].mean():.0f} kW")

# 2. Cargar timeseries PPO (último episodio COMPLETO)
ts_path = Path("outputs/ppo_training/timeseries_ppo.csv")
ts_df = pd.read_csv(ts_path)
# Filtrar último episodio COMPLETO (8760 horas)
episode_sizes = ts_df.groupby('episode').size()
complete_episodes = episode_sizes[episode_sizes >= 8760].index.tolist()
last_complete = max(complete_episodes) if complete_episodes else ts_df['episode'].max()
ts_df = ts_df[ts_df['episode'] == last_complete].copy()
ts_df = ts_df.reset_index(drop=True)

print(f"\n[2] TIMESERIES PPO (Episodio {last_complete} - completo):")
print(f"    Registros: {len(ts_df):,}")
print(f"    BESS power: min={ts_df['bess_power_kw'].min():.1f} kW, max={ts_df['bess_power_kw'].max():.1f} kW")

# ==============================================================================
# MERGE Y CALCULAR PICOS
# ==============================================================================
# Crear índice temporal para merge
ts_df['hour_index'] = ts_df['hour_of_year']
mall_df['hour_index'] = range(len(mall_df))

# Merge
df = mall_df.merge(ts_df[['hour_index', 'bess_power_kw', 'bess_soc', 'hour_of_day']], 
                   on='hour_index', how='left')

# Extraer campos temporales
df['month'] = df['datetime'].dt.month
df['day_of_year'] = df['datetime'].dt.dayofyear
df['hour'] = df['datetime'].dt.hour
df['date'] = df['datetime'].dt.date

# Identificar picos
df['is_peak'] = df['demand_kw'] > PEAK_THRESHOLD_KW
df['peak_excess_kw'] = np.maximum(0, df['demand_kw'] - PEAK_THRESHOLD_KW)

# Calcular energía cortada por BESS (solo cuando descarga = bess_power_kw > 0)
# El BESS solo puede cortar lo que excede el umbral
df['bess_discharge_kw'] = np.maximum(0, df['bess_power_kw'].fillna(0))
df['peak_shaved_kw'] = np.minimum(df['peak_excess_kw'], df['bess_discharge_kw'])
df['peak_shaved_kwh'] = df['peak_shaved_kw']  # 1 hora = kW = kWh

# Hora punta
df['is_peak_hour'] = df['hour'].isin(PEAK_HOURS)

# ==============================================================================
# ANÁLISIS DE HORAS CON PICOS
# ==============================================================================
print("\n" + "=" * 70)
print("PICOS DE DEMANDA (> 2000 kW)")
print("=" * 70)

peak_hours_df = df[df['is_peak']].copy()
print(f"\n[3] HORAS CON PICOS:")
print(f"    Total horas con demanda > {PEAK_THRESHOLD_KW} kW: {len(peak_hours_df):,} de {len(df):,} ({100*len(peak_hours_df)/len(df):.1f}%)")
print(f"    Energía total en exceso: {df['peak_excess_kw'].sum():,.0f} kWh")
print(f"    Energía cortada por BESS: {df['peak_shaved_kwh'].sum():,.0f} kWh")
print(f"    % Picos cortados: {100*df['peak_shaved_kwh'].sum()/max(1, df['peak_excess_kw'].sum()):.1f}%")

# ==============================================================================
# ANÁLISIS POR HORA PUNTA (18:00-22:00)
# ==============================================================================
print("\n" + "-" * 70)
print(f"HORA PUNTA ({PEAK_HOURS[0]}:00 - {PEAK_HOURS[-1]+1}:00)")
print("-" * 70)

peak_hour_df = df[df['is_peak_hour']].copy()
print(f"\n    Horas en hora punta: {len(peak_hour_df):,}")
print(f"    Horas con pico en hora punta: {len(peak_hour_df[peak_hour_df['is_peak']]):,}")
print(f"    Energía exceso en hora punta: {peak_hour_df['peak_excess_kw'].sum():,.0f} kWh")
print(f"    Energía cortada en hora punta: {peak_hour_df['peak_shaved_kwh'].sum():,.0f} kWh")

# Distribución por hora
print(f"\n    Por hora del día:")
hourly_stats = df.groupby('hour').agg({
    'demand_kw': 'mean',
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_discharge_kw': 'mean'
}).round(1)

for h in PEAK_HOURS:
    row = hourly_stats.loc[h]
    print(f"      {h:02d}:00 - Demanda media: {row['demand_kw']:,.0f} kW | "
          f"Exceso: {row['peak_excess_kw']:,.0f} kWh | "
          f"Cortado: {row['peak_shaved_kwh']:,.0f} kWh | "
          f"BESS desc.: {row['bess_discharge_kw']:.1f} kW")

# ==============================================================================
# ANÁLISIS POR DÍA
# ==============================================================================
print("\n" + "=" * 70)
print("PEAK SHAVING POR DÍA")
print("=" * 70)

daily_stats = df.groupby('date').agg({
    'demand_kw': ['max', 'mean'],
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_discharge_kw': 'sum',
    'is_peak': 'sum'
}).round(1)
daily_stats.columns = ['demand_max', 'demand_mean', 'excess_kwh', 'shaved_kwh', 'bess_discharge', 'peak_hours']

# Top 10 días con más picos
top_peak_days = daily_stats.nlargest(10, 'excess_kwh')
print(f"\nTop 10 días con mayores picos:")
print(f"{'Fecha':<12} {'Dem.Max':<10} {'Exceso':<12} {'Cortado':<12} {'%Cortado':<10} {'Horas Pico':<10}")
print("-" * 70)
for date, row in top_peak_days.iterrows():
    pct = 100 * row['shaved_kwh'] / max(1, row['excess_kwh'])
    print(f"{str(date):<12} {row['demand_max']:>8,.0f} kW {row['excess_kwh']:>10,.0f} kWh {row['shaved_kwh']:>10,.0f} kWh {pct:>8.1f}% {int(row['peak_hours']):>8}")

# Resumen diario
days_with_peaks = (daily_stats['peak_hours'] > 0).sum()
print(f"\nResumen diario:")
print(f"    Días con picos (>2000 kW): {days_with_peaks} de 365 ({100*days_with_peaks/365:.1f}%)")
print(f"    Promedio exceso/día (con pico): {daily_stats[daily_stats['peak_hours']>0]['excess_kwh'].mean():,.0f} kWh")
print(f"    Promedio cortado/día (con pico): {daily_stats[daily_stats['peak_hours']>0]['shaved_kwh'].mean():,.0f} kWh")

# ==============================================================================
# ANÁLISIS POR MES
# ==============================================================================
print("\n" + "=" * 70)
print("PEAK SHAVING POR MES")
print("=" * 70)

monthly_stats = df.groupby('month').agg({
    'demand_kw': ['max', 'mean'],
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_discharge_kw': 'sum',
    'is_peak': 'sum'
}).round(1)
monthly_stats.columns = ['demand_max', 'demand_mean', 'excess_kwh', 'shaved_kwh', 'bess_discharge', 'peak_hours']

MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
print(f"\n{'Mes':<6} {'Dem.Max':<10} {'Exceso':<14} {'Cortado':<14} {'%Cortado':<10} {'Horas Pico':<10}")
print("-" * 70)

for month in range(1, 13):
    row = monthly_stats.loc[month]
    pct = 100 * row['shaved_kwh'] / max(1, row['excess_kwh'])
    print(f"{MESES[month-1]:<6} {row['demand_max']:>8,.0f} kW {row['excess_kwh']:>12,.0f} kWh {row['shaved_kwh']:>12,.0f} kWh {pct:>8.1f}% {int(row['peak_hours']):>8}")

# ==============================================================================
# RESUMEN ANUAL
# ==============================================================================
print("\n" + "=" * 70)
print("RESUMEN ANUAL DE PEAK SHAVING")
print("=" * 70)

annual_excess = df['peak_excess_kw'].sum()
annual_shaved = df['peak_shaved_kwh'].sum()
annual_pct = 100 * annual_shaved / max(1, annual_excess)

print(f"""
    DEMANDA MALL:
    ├─ Máxima:                    {df['demand_kw'].max():>12,.0f} kW
    ├─ Media:                     {df['demand_kw'].mean():>12,.0f} kW
    └─ Total anual:               {df['demand_kw'].sum():>12,.0f} kWh

    PICOS (>{PEAK_THRESHOLD_KW} kW):
    ├─ Horas con pico:            {len(peak_hours_df):>12,} horas ({100*len(peak_hours_df)/8760:.1f}%)
    ├─ Energía exceso anual:      {annual_excess:>12,.0f} kWh
    └─ Pico máximo sobre umbral:  {df['peak_excess_kw'].max():>12,.0f} kW

    BESS PEAK SHAVING:
    ├─ Energía cortada anual:     {annual_shaved:>12,.0f} kWh
    ├─ % de picos cortados:       {annual_pct:>12.1f}%
    └─ Ahorro estimado CO2:       {annual_shaved * 0.4521:>12,.0f} kg

    HORA PUNTA ({PEAK_HOURS[0]}:00-{PEAK_HOURS[-1]+1}:00):
    ├─ Energía exceso:            {peak_hour_df['peak_excess_kw'].sum():>12,.0f} kWh
    └─ Energía cortada:           {peak_hour_df['peak_shaved_kwh'].sum():>12,.0f} kWh
""")

# ==============================================================================
# GUARDAR RESULTADOS
# ==============================================================================
output_dir = Path("outputs/ppo_training")
output_dir.mkdir(parents=True, exist_ok=True)

# CSV diario
daily_output = daily_stats.reset_index()
daily_output.to_csv(output_dir / "peak_shaving_daily.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_daily.csv'}")

# CSV mensual
monthly_output = monthly_stats.reset_index()
monthly_output.to_csv(output_dir / "peak_shaving_monthly.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_monthly.csv'}")

# CSV horario completo
hourly_output = df[['datetime', 'demand_kw', 'bess_power_kw', 'bess_soc', 
                    'peak_excess_kw', 'peak_shaved_kwh', 'is_peak', 'is_peak_hour']].copy()
hourly_output.to_csv(output_dir / "peak_shaving_hourly.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_hourly.csv'}")

print("\n" + "=" * 70)
print("ANÁLISIS COMPLETADO")
print("=" * 70)
