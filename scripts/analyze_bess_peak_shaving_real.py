#!/usr/bin/env python3
"""
Analisis de Peak Shaving - BESS REAL vs PPO
============================================
Compara el baseline de BESS (dataset OE2) con el control PPO.
Analiza cuanta demanda pico del mall (>2000 kW) corta el BESS.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path

# ==============================================================================
# CONFIGURACION
# ==============================================================================
PEAK_THRESHOLD_KW = 2000  # Umbral de pico (kW)
PEAK_HOURS = list(range(18, 23))  # Horas punta: 18:00-22:00
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# ==============================================================================
# CARGAR DATOS REALES DE BESS (BASELINE OE2)
# ==============================================================================
print("=" * 70)
print("ANALISIS DE PEAK SHAVING - DATOS REALES BESS (OE2)")
print("=" * 70)

bess_path = Path("data/oe2/bess/bess_ano_2024.csv")
df = pd.read_csv(bess_path)
df['datetime'] = pd.to_datetime(df['datetime'])

print(f"\n[1] DATASET BESS REAL (OE2):")
print(f"    Registros: {len(df):,}")
print(f"    Rango: {df['datetime'].min()} a {df['datetime'].max()}")

# ==============================================================================
# FLUJOS REALES DE BESS
# ==============================================================================
print("\n" + "=" * 70)
print("FLUJOS REALES DE BESS (Simulacion OE2)")
print("=" * 70)

total_charge = df['bess_charge_kwh'].sum()
total_discharge = df['bess_discharge_kwh'].sum()
pv_to_bess = df['pv_to_bess_kwh'].sum()
grid_to_bess = df['grid_to_bess_kwh'].sum()
bess_to_ev = df['bess_to_ev_kwh'].sum()
bess_to_mall = df['bess_to_mall_kwh'].sum()

print(f"""
    CARGA BESS:
    +- Desde Solar (PV):          {pv_to_bess:>12,.0f} kWh
    +- Desde Grid:                {grid_to_bess:>12,.0f} kWh
    +- TOTAL CARGA:               {total_charge:>12,.0f} kWh

    DESCARGA BESS:
    +- Hacia EVs:                 {bess_to_ev:>12,.0f} kWh
    +- Hacia Mall:                {bess_to_mall:>12,.0f} kWh
    +- TOTAL DESCARGA:            {total_discharge:>12,.0f} kWh

    BALANCE:
    +- Ratio (Descarga/Carga):    {100*total_discharge/total_charge:>12.1f}%
    +- Perdidas (eficiencia):     {total_charge - total_discharge:>12,.0f} kWh
    +- Eficiencia round-trip:     {100*total_discharge/total_charge:>12.1f}%
    
    SOC BESS:
    +- SOC medio:                 {df['bess_soc_percent'].mean():>12.1f}%
    +- SOC minimo:                {df['bess_soc_percent'].min():>12.1f}%
    +- SOC maximo:                {df['bess_soc_percent'].max():>12.1f}%
""")

# ==============================================================================
# ANALISIS DE PEAK SHAVING DEL MALL
# ==============================================================================
print("\n" + "=" * 70)
print("PEAK SHAVING DEL MALL - DATOS REALES")
print("=" * 70)

# Extraer campos temporales
df['month'] = df['datetime'].dt.month
df['day_of_year'] = df['datetime'].dt.dayofyear
df['hour'] = df['datetime'].dt.hour
df['date'] = df['datetime'].dt.date

# Calcular picos
df['is_peak'] = df['mall_demand_kwh'] > PEAK_THRESHOLD_KW
df['peak_excess_kw'] = np.maximum(0, df['mall_demand_kwh'] - PEAK_THRESHOLD_KW)

# Energia cortada = descarga BESS hacia mall durante picos
df['peak_shaved_kwh'] = np.where(
    df['is_peak'], 
    np.minimum(df['peak_excess_kw'], df['bess_to_mall_kwh']),
    0
)

# Hora punta
df['is_peak_hour'] = df['hour'].isin(PEAK_HOURS)

# Resumen de picos
peak_hours_df = df[df['is_peak']].copy()
total_excess = df['peak_excess_kw'].sum()
total_shaved = df['peak_shaved_kwh'].sum()

print(f"""
    DEMANDA MALL:
    +- Maxima:                    {df['mall_demand_kwh'].max():>12,.0f} kW
    +- Media:                     {df['mall_demand_kwh'].mean():>12,.0f} kW
    +- Total anual:               {df['mall_demand_kwh'].sum():>12,.0f} kWh

    PICOS (>{PEAK_THRESHOLD_KW} kW):
    +- Horas con pico:            {len(peak_hours_df):>12,} horas ({100*len(peak_hours_df)/8760:.1f}%)
    +- Energia exceso anual:      {total_excess:>12,.0f} kWh
    +- Pico maximo sobre umbral:  {df['peak_excess_kw'].max():>12,.0f} kW

    BESS PEAK SHAVING:
    +- BESS -> Mall total:         {bess_to_mall:>12,.0f} kWh
    +- BESS -> Mall en picos:      {total_shaved:>12,.0f} kWh
    +- % de picos cortados:       {100*total_shaved/max(1,total_excess):>12.1f}%
    +- Ahorro CO₂:                {total_shaved * 0.4521:>12,.0f} kg
""")

# ==============================================================================
# ANALISIS POR HORA PUNTA
# ==============================================================================
print("\n" + "-" * 70)
print(f"HORA PUNTA ({PEAK_HOURS[0]}:00 - {PEAK_HOURS[-1]+1}:00)")
print("-" * 70)

peak_hour_df = df[df['is_peak_hour']].copy()
print(f"\n    Por hora del dia:")
hourly_stats = df.groupby('hour').agg({
    'mall_demand_kwh': 'mean',
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_to_mall_kwh': ['sum', 'mean'],
    'bess_discharge_kwh': 'mean'
})
hourly_stats.columns = ['demand_mean', 'excess_total', 'shaved_total', 'bess_mall_total', 'bess_mall_mean', 'bess_discharge_mean']

print(f"\n    {'Hora':<6} {'Demanda':<10} {'Exceso':<14} {'Cortado':<14} {'BESS->Mall':<12} {'%Cortado':<10}")
print("    " + "-" * 70)
for h in range(6, 24):  # 6am - 11pm
    row = hourly_stats.loc[h]
    pct = 100 * row['shaved_total'] / max(1, row['excess_total']) if row['excess_total'] > 0 else 0
    marker = "◄" if h in PEAK_HOURS else ""
    print(f"    {h:02d}:00  {row['demand_mean']:>8,.0f} kW  {row['excess_total']:>12,.0f} kWh  {row['shaved_total']:>12,.0f} kWh  {row['bess_mall_total']:>10,.0f} kWh  {pct:>8.1f}% {marker}")

# ==============================================================================
# ANALISIS POR MES
# ==============================================================================
print("\n" + "=" * 70)
print("PEAK SHAVING POR MES")
print("=" * 70)

monthly_stats = df.groupby('month').agg({
    'mall_demand_kwh': ['max', 'mean'],
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_to_mall_kwh': 'sum',
    'bess_discharge_kwh': 'sum',
    'is_peak': 'sum'
})
monthly_stats.columns = ['demand_max', 'demand_mean', 'excess_kwh', 'shaved_kwh', 'bess_mall', 'bess_discharge', 'peak_hours']

print(f"\n{'Mes':<6} {'Dem.Max':<10} {'Exceso':<14} {'BESS->Mall':<14} {'Cortado':<12} {'%Cortado':<10}")
print("-" * 70)

for month in range(1, 13):
    row = monthly_stats.loc[month]
    pct = 100 * row['shaved_kwh'] / max(1, row['excess_kwh'])
    print(f"{MESES[month-1]:<6} {row['demand_max']:>8,.0f} kW {row['excess_kwh']:>12,.0f} kWh {row['bess_mall']:>12,.0f} kWh {row['shaved_kwh']:>10,.0f} kWh {pct:>8.1f}%")

# ==============================================================================
# ANALISIS POR DIA (Top 10)
# ==============================================================================
print("\n" + "=" * 70)
print("TOP 10 DIAS CON MAYORES PICOS")
print("=" * 70)

daily_stats = df.groupby('date').agg({
    'mall_demand_kwh': 'max',
    'peak_excess_kw': 'sum',
    'peak_shaved_kwh': 'sum',
    'bess_to_mall_kwh': 'sum',
    'is_peak': 'sum'
})
daily_stats.columns = ['demand_max', 'excess_kwh', 'shaved_kwh', 'bess_mall', 'peak_hours']

top_peak_days = daily_stats.nlargest(10, 'excess_kwh')
print(f"\n{'Fecha':<12} {'Dem.Max':<10} {'Exceso':<12} {'BESS->Mall':<12} {'Cortado':<12} {'%Cortado':<10}")
print("-" * 70)
for date, row in top_peak_days.iterrows():
    pct = 100 * row['shaved_kwh'] / max(1, row['excess_kwh'])
    print(f"{str(date):<12} {row['demand_max']:>8,.0f} kW {row['excess_kwh']:>10,.0f} kWh {row['bess_mall']:>10,.0f} kWh {row['shaved_kwh']:>10,.0f} kWh {pct:>8.1f}%")

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
print("\n" + "=" * 70)
print("RESUMEN ANUAL - DATOS REALES OE2")
print("=" * 70)

peak_hour_excess = peak_hour_df['peak_excess_kw'].sum()
peak_hour_shaved = peak_hour_df['peak_shaved_kwh'].sum()

print(f"""
    ================================================================
    BESS - FLUJOS REALES (SIN RL)
    ================================================================
    Carga total:                  {total_charge:>12,.0f} kWh
    Descarga total:               {total_discharge:>12,.0f} kWh
    Eficiencia:                   {100*total_discharge/total_charge:>12.1f}%
    
    ================================================================
    PEAK SHAVING MALL (>2000 kW)
    ================================================================
    Energia exceso anual:         {total_excess:>12,.0f} kWh
    Energia cortada (BESS):       {total_shaved:>12,.0f} kWh
    % Picos cortados:             {100*total_shaved/max(1,total_excess):>12.1f}%
    
    En HORA PUNTA (18-22h):
    +- Exceso:                    {peak_hour_excess:>12,.0f} kWh
    +- Cortado:                   {peak_hour_shaved:>12,.0f} kWh
    +- % Cortado:                 {100*peak_hour_shaved/max(1,peak_hour_excess):>12.1f}%
    
    ================================================================
    CO₂ AHORRADO POR PEAK SHAVING
    ================================================================
    Por picos cortados:           {total_shaved * 0.4521:>12,.0f} kg
    Por toda descarga BESS:       {total_discharge * 0.4521:>12,.0f} kg
""")

# ==============================================================================
# GUARDAR RESULTADOS
# ==============================================================================
output_dir = Path("outputs/ppo_training")
output_dir.mkdir(parents=True, exist_ok=True)

# CSV diario
daily_output = daily_stats.reset_index()
daily_output.to_csv(output_dir / "peak_shaving_daily_real.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_daily_real.csv'}")

# CSV mensual
monthly_output = monthly_stats.reset_index()
monthly_output.to_csv(output_dir / "peak_shaving_monthly_real.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_monthly_real.csv'}")

# CSV horario completo
hourly_output = df[['datetime', 'mall_demand_kwh', 'bess_charge_kwh', 'bess_discharge_kwh',
                    'bess_to_mall_kwh', 'bess_soc_percent', 'peak_excess_kw', 'peak_shaved_kwh', 
                    'is_peak', 'is_peak_hour']].copy()
hourly_output.to_csv(output_dir / "peak_shaving_hourly_real.csv", index=False)
print(f"[OK] Guardado: {output_dir / 'peak_shaving_hourly_real.csv'}")

print("\n" + "=" * 70)
print("ANALISIS COMPLETADO - DATOS REALES BESS OE2")
print("=" * 70)
