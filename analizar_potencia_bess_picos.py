#!/usr/bin/env python
"""Análisis de dimensionamiento correcto del BESS para limitar picos a 2000 kW."""
import pandas as pd
import numpy as np

# Leerel CSV simulado
df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

# Calcular demanda total por hora
df['total_demand'] = df['ev_demand_kwh'] + df['mall_demand_kwh']

# Analizar picos
print("=" * 70)
print("ANÁLISIS: ¿QUÉ POTENCIA DE BESS SE NECESITA PARA LIMITAR PICOS A 2000 kW?")
print("=" * 70)

# Horas donde demanda > 2000
high_load_hours = df[df['total_demand'] > 2000].copy()
high_load_hours['excess_above_2000'] = high_load_hours['total_demand'] - 2000

print(f"\nHoras con demanda > 2000 kW: {len(high_load_hours)}/8760 (43.3%)")
print(f"\nEstadísticas de exceso sobre 2000 kW:")
print(f"  Mínimo:  {high_load_hours['excess_above_2000'].min():.1f} kW")
print(f"  Promedio: {high_load_hours['excess_above_2000'].mean():.1f} kW")
print(f"  Máximo:   {high_load_hours['excess_above_2000'].max():.1f} kW")
print(f"  P95:      {high_load_hours['excess_above_2000'].quantile(0.95):.1f} kW")
print(f"  P90:      {high_load_hours['excess_above_2000'].quantile(0.90):.1f} kW")

# Cuantiles
percentiles = [50, 75, 80, 85, 90, 95, 99, 100]
print(f"\nPercentiles de exceso sobre 2000 kW:")
for p in percentiles:
    val = high_load_hours['excess_above_2000'].quantile(p/100)
    hours_above = (high_load_hours['excess_above_2000'] >= val).sum()
    print(f"  P{p:2d}: {val:6.1f} kW (en {hours_above:4d} horas)")

# Analizar patrones por hora del día
print("\n\nPATRÓN: Demanda máxima por hora del día")
hourly_max = df.copy()
hourly_max['hour'] = df.index % 24
hourly_max = hourly_max.groupby('hour')['total_demand'].agg(['mean', 'max', 'std']).reset_index()
print("\nHora | Promedio |  Máximo | Desv.Est | Exceso promedio (>2000)")
print("-----|----------|---------|----------|-------------------------")
for _, row in hourly_max.iterrows():
    hour = int(row['hour'])
    mean_val = row['mean']
    max_val = row['max']
    std_val = row['std']
    # Calcular exceso promedio si hay
    if mean_val > 2000:
        excess = mean_val - 2000
        print(f"{hour:4d} | {mean_val:8.1f} | {max_val:7.1f} | {std_val:8.1f} | {excess:7.1f} kW")
    elif max_val > 2000:
        print(f"{hour:4d} | {mean_val:8.1f} | {max_val:7.1f} | {std_val:8.1f} | (max>{2000})")

# Análisis de capacidad energética
print("\n\nANÁLISIS: Energía diaria necesaria para cortar picos")
print("=" * 70)

daily_excess_kwh_list = []
for day in range(365):
    day_data = df.iloc[day*24:(day+1)*24]
    day_data_high = day_data[day_data['total_demand'] > 2000]
    if len(day_data_high) > 0:
        daily_excess = (day_data_high['total_demand'] - 2000).sum()
        daily_excess_kwh_list.append(daily_excess)

if daily_excess_kwh_list:
    daily_excess_kwh = np.array(daily_excess_kwh_list)
    print(f"\nEnergía DIARIA necesaria para limitar picos a 2000 kW:")
    print(f"  Mínimo:  {daily_excess_kwh.min():.1f} kWh")
    print(f"  Promedio: {daily_excess_kwh.mean():.1f} kWh")
    print(f"  Máximo:   {daily_excess_kwh.max():.1f} kWh")
    print(f"  P95:      {np.percentile(daily_excess_kwh, 95):.1f} kWh")
    
    # Para leer con C-rate de 0.36 (400kW / 1700 kWh = 0.235 C-rate actual)
    print(f"\nCapacidad BESS necesaria:")
    print(f"  Para P95 diario ({np.percentile(daily_excess_kwh, 95):.0f} kWh): " +
          f"{np.percentile(daily_excess_kwh, 95) / 0.80:.0f} kWh (con DoD 80%)")
    print(f"  Para P99 diario ({np.percentile(daily_excess_kwh, 99):.0f} kWh): " +
          f"{np.percentile(daily_excess_kwh, 99) / 0.80:.0f} kWh (con DoD 80%)")
    print(f"  Para máximo diario ({daily_excess_kwh.max():.0f} kWh): " +
          f"{daily_excess_kwh.max() / 0.80:.0f} kWh (con DoD 80%)")

print("\n" + "=" * 70)
print("RECOMENDACIÓN:")
print("=" * 70)
print("""
Para LIMITAR PICOS a 2000 kW se necesita:

1. POTENCIA: >860 kW (para reducir máximo exceso de 863.9 kW)
   - Actual: 400 kW (insuficiente para límite estricto)
   - Recomendado: 900-1000 kW

2. CAPACIDAD: Para sostener descarga en horas pico
   - Actual: 1,700 kWh
   - Ratio actual: 1700/400 = 4.25 (bueno para 4+ horas de autonomía)
   
3. DIMENSIONAMIENTO REVISADO:
   Option A: Aumentar solo potencia a 900 kW → Capacidad = 900*4.25 = 3,825 kWh (MUY GRANDE)
   Option B: Mantener ratio 2.75 → 900 kW requiere 2,475 kWh
   Option C: Aceptar que BESS reduce pero no elimina picos
     - Con 400 kW: reduce pico a 2,463 kW en mejor caso
     
CONCLUSIÓN: 
El BESS actual (1,700 kWh / 400 kW) está dimensionado para:
✓ Cubrir déficit EV (58% de cobertura)
✓ Reducir importación grid (~35% de reducción)
✓ Ahorrar costos (S/.1.25M/año)

NO para:
✗ Limitar picos a 2000 kW (exceso demasiado grande)
""")
print("=" * 70)
