#!/usr/bin/env python3
"""Análisis detallado de datos REALES del MALL desde demandamallhorakwh.csv"""

import pandas as pd
from pathlib import Path
import numpy as np

print("="*80)
print("ANÁLISIS COMPLETO - DATOS REALES DEL MALL (data/oe2/demandamallkwh/demandamallhorakwh.csv)")
print("="*80)
print()

# Leer el archivo MALL con separador correcto
mall_file = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
df_mall = pd.read_csv(mall_file, sep=';', encoding='utf-8')

print("1. INFORMACIÓN DEL ARCHIVO:")
print(f"   Filas: {len(df_mall)}")
print(f"   Columnas: {list(df_mall.columns)}")
print(f"   Tipo de dato: {df_mall['kWh'].dtype}")
print()

# Análisis de demanda
mall_demand = df_mall['kWh'].values.astype(np.float32)

print("2. ESTADÍSTICAS DE DEMANDA DEL MALL:")
print(f"   Mínimo:  {mall_demand.min():.1f} kWh/hora")
print(f"   Máximo:  {mall_demand.max():.1f} kWh/hora")
print(f"   Promedio: {mall_demand.mean():.1f} kWh/hora")
print(f"   Mediana: {np.median(mall_demand):.1f} kWh/hora")
print(f"   Desv Est: {mall_demand.std():.1f} kWh/hora")
print()

# Crear columna datetime y hora para análisis posterior
df_mall['datetime'] = pd.to_datetime(df_mall['FECHAHORA'], format='%d/%m/%Y %H:%M')
df_mall['hora'] = df_mall['datetime'].dt.hour

# Consumo total anual
annual_demand_kwh = mall_demand.sum()
annual_demand_mwh = annual_demand_kwh / 1000
annual_demand_gwh = annual_demand_mwh / 1000

print("3. CONSUMO ANUAL DEL MALL:")
print(f"   Total: {annual_demand_kwh:,.0f} kWh")
print(f"   Total: {annual_demand_mwh:,.1f} MWh")
print(f"   Total: {annual_demand_gwh:.2f} GWh")
print()

# Perfil horario
print("4. PERFIL HORARIO DEL MALL:")
print(f"   Horas de operación: {(mall_demand > 0).sum()} / 8,760")
print(f"   Horas OFF: {(mall_demand == 0).sum()} / 8,760")

# Percentiles
percentiles = [10, 25, 50, 75, 90, 95, 99]
print()
print("   Percentiles de demanda (kWh/h):")
for p in percentiles:
    val = np.percentile(mall_demand, p)
    print(f"      P{p:2d}: {val:.1f}")
print()

# Horarios pico/normal
morning_peak = df_mall[df_mall['hora'].isin([7,8,9,10,11])]['kWh'].mean()
afternoon_peak = df_mall[df_mall['hora'].isin([13,14,15,16,17])]['kWh'].mean()
night_peak = df_mall[df_mall['hora'].isin([19,20,21])]['kWh'].mean()

print("5. VARIACIÓN POR HORA DEL DÍA:")
# Ya creamos datetime y hora arriba
hourly_avg = df_mall.groupby('hora')['kWh'].agg(['mean', 'min', 'max'])
print("   Hora | Promedio | Mín   | Máx   |")
print("   -----|----------|-------|-------|")
for h in range(24):
    if h in hourly_avg.index:
        row = hourly_avg.loc[h]
        print(f"   {h:02d}h | {row['mean']:8.1f} | {row['min']:5.1f} | {row['max']:5.1f} |")
print()

print("6. HORARIOS PICO:")
print(f"   Mañana (7-11h): {morning_peak:.1f} kWh/h")
print(f"   Tarde (13-17h): {afternoon_peak:.1f} kWh/h")
print(f"   Noche (19-21h): {night_peak:.1f} kWh/h")
print()

# Comparación de lo que se asume con realidad
print("7. COMPARACIÓN: ASUMIDO vs. REAL:")
print()
print("   DOCUMENTADO/ASUMIDO:")
print("      - Baseline: ~100 kW")
print("      - Consumo anual estimado: 100 kW × 24h × 365d = 876 MWh")
print()
print("   REAL (DEL DATASET):")
print(f"      - Promedio: {mall_demand.mean():.1f} kW/hora")
print(f"      - Consumo anual real: {annual_demand_gwh:.2f} GWh = {annual_demand_mwh:,.0f} MWh")
print(f"      - Diferencia: {annual_demand_mwh - 876:.0f} MWh/año ({((annual_demand_mwh / 876) - 1) * 100:.1f}% mayor)")
print()

# Impacto en balance energético
print("8. IMPACTO EN BALANCE ENERGÉTICO DEL SISTEMA:")

# Cargar solar y EV para comparación
solar_file = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
if solar_file.exists():
    df_solar = pd.read_csv(solar_file)
    if 'pv_generation_kwh' in df_solar.columns:
        col = 'pv_generation_kwh'
    elif 'ac_power_kw' in df_solar.columns:
        col = 'ac_power_kw'
    else:
        col = df_solar.columns[-1]
    solar_annual = df_solar[col].sum()
    print(f"   Solar PV anual: {solar_annual:,.0f} kWh ({solar_annual/1000:.2f} GWh)")

charger_file = Path('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')
if charger_file.exists():
    df_chargers = pd.read_csv(charger_file)
    data_cols = [c for c in df_chargers.columns if 'timestamp' not in c.lower() and 'time' not in c.lower()]
    chargers_annual = df_chargers[data_cols].sum().sum()
    print(f"   EVs (38 sockets) anual: {chargers_annual:,.0f} kWh ({chargers_annual/1000:.2f} GWh)")

print(f"   MALL anual: {annual_demand_kwh:,.0f} kWh ({annual_demand_gwh:.2f} GWh)")
total_load = annual_demand_kwh
if charger_file.exists():
    total_load += chargers_annual
print(f"   TOTAL (MALL + EV): {total_load:,.0f} kWh ({total_load/1000/1000:.2f} GWh)")
print()

# Cálculo de cobertura solar
if solar_file.exists():
    solar_coverage = (solar_annual / total_load) * 100
    grid_supply = ((total_load - solar_annual) / total_load) * 100
    print(f"   Cobertura solar: {solar_coverage:.1f}%")
    print(f"   Suministro grid: {grid_supply:.1f}%")
print()

print("="*80)
print("CONCLUSIÓN CRÍTICA:")
print("="*80)
print()
print(f"⚠️  El MALL NO consume 100 kW baseline")
print(f"✓   El MALL consume EN PROMEDIO: {mall_demand.mean():.0f} kW/hora")
print(f"✓   El MALL consume ANUALMENTE: {annual_demand_gwh:.2f} GWh (NO 0.876 GWh estimado)")
print()
print("IMPACTO EN train_sac_multiobjetivo.py:")
print("Los datos cargados en mall_hourly DEBEN ser los valores REALES del archivo CSV")
print(f"NO sustitutos por 100 kW baseline")
print()
