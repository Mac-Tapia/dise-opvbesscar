"""
Analiza el PERÍODO REAL de demanda EV del dataset (sin suposiciones)
"""
import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("ANALIZANDO PERÍODO REAL DE DEMANDA EV DEL DATASET")
print("="*80)

# Cargar el dataset - solo el mes de enero para análisis rápido
data_path = Path('d:/diseñopvbesscar/data/iquitos_ev_mall/chargers_timeseries.csv')

print(f"\n1. Leyendo archivo: {data_path.name}")
print(f"   Tamaño total: {data_path.stat().st_size / 1_000_000:.1f} MB\n")

# Leer solo el mes de enero (744 horas: 31 días × 24 horas)
try:
    df = pd.read_csv(data_path, nrows=744)  # Enero 2024
    print(f"✓ Leído exito: {len(df)} filas (enero 2024)\n")
except Exception as e:
    print(f"✗ Error: {e}\n")
    exit(1)

# Convertir datetime
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour_of_day'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

# Buscar la columna de EV
print("2. COLUMNAS DISPONIBLES PARA EV:")
ev_cols = [c for c in df.columns if 'ev' in c.lower()]
for col in ev_cols:
    print(f"   - {col}")

# Usar la columna de demanda total EV
if 'ev_energia_total_kwh' in df.columns:
    ev_col = 'ev_energia_total_kwh'
elif 'ev_demand_kwh' in df.columns:
    ev_col = 'ev_demand_kwh'
else:
    ev_col = ev_cols[0] if ev_cols else None

print(f"\n✓ Usando columna: {ev_col}\n")

# Analizar período de demanda EV
print("3. ANÁLISIS DEL PERÍODO DE DEMANDA EV:\n")

# Estadísticas por hora del día
hourly_stats = df.groupby('hour_of_day')[ev_col].agg(['sum', 'mean', 'max', 'min', 'count'])
hourly_stats['non_zero'] = df.groupby('hour_of_day')[ev_col].apply(lambda x: (x > 0).sum())

print(hourly_stats.to_string())

# Identificar horas con demanda
print("\n\n4. HORAS CON DEMANDA > 0:\n")
with_demand = hourly_stats[hourly_stats['sum'] > 0].index.tolist()
print(f"   Horas: {with_demand if with_demand else 'NINGUNA'}")

if with_demand:
    print(f"   Período: {min(with_demand):02d}:00 - {max(with_demand)+1:02d}:00")
    print(f"   Duración: {len(with_demand)} horas/día")
    print(f"   Total demanda/hora: {hourly_stats.loc[with_demand, 'sum'].sum() / len(hourly_stats.loc[with_demand]) :.1f} kWh/hora (promedio)")
else:
    print("   ⚠ NO hay demanda EV en enero")

# Estadísticas generales
print(f"\n5. RESUMEN GENERAL (ENERO 2024):\n")
total_ev = df[ev_col].sum()
print(f"   Total EV enero: {total_ev:,.1f} kWh")
print(f"   Promedio/hora: {df[ev_col].mean():.1f} kWh/hora")
print(f"   Max horaria: {df[ev_col].max():.1f} kWh/hora (en hora {df[ev_col].idxmax()} = {df.iloc[df[ev_col].idxmax()]['hour_of_day']}:00)")
print(f"   Min horaria: {df[ev_col].min():.1f} kWh/hora")
print(f"   Horas con demanda: {(df[ev_col] > 0).sum()} de {len(df)}")
print(f"   Porcentaje hrs con demanda: {(df[ev_col] > 0).sum() / len(df) * 100:.1f}%")

# Mostrar un día completo (ejemplo: día 5)
print(f"\n6. EJEMPLO: DISTRIBUCIÓN HORARIA (DÍA 5 de enero):\n")
day5 = df[df['day'] == 5].copy()
day5 = day5.sort_values('hour_of_day')
print("   Hora | Demanda EV (kWh)")
print("   ----|-----------------")
for _, row in day5.iterrows():
    hour = int(row['hour_of_day'])
    demand = row[ev_col]
    marker = "●" if demand > 0 else "○"
    print(f"   {hour:02d}:00 | {demand:7.1f} kWh {marker}")

# Estadísticas por hora del día con formato visual
print(f"\n7. VISUALIZACIÓN PERÍODO DE DEMANDA:\n")
print("   Hora | Demanda Total | Conteo")
print("   ----|---------------|---------")
for hour in range(24):
    row = hourly_stats.loc[hour]
    percent = (row['non_zero'] / row['count'] * 100) if row['count'] > 0 else 0
    bar = "█" * int(min(row['sum'] / 5, 20)) if row['sum'] > 0 else ""
    print(f"   {hour:02d}:00 | {row['sum']:11.1f}  | {int(row['non_zero']):2d}/{int(row['count']):2d} {bar}")

print("\n" + "="*80)
print("CONCLUSIÓN: Período REAL de demanda EV según dataset")
print("="*80)

if with_demand:
    start_h = min(with_demand)
    end_h = max(with_demand) + 1
    print(f"\n✓ EV OPERA DE: {start_h:02d}:00 A {end_h:02d}:00")
    print(f"  Duración: {len(with_demand)} horas/día")
    print(f"  Status: VALIDADO CON DATOS REALES")
else:
    print("\n✗ No hay demanda EV detectada en enero")
    
print("\n")
