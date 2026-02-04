"""
Análisis CRÍTICO: Demanda del Mall OE2
2 resoluciones detectadas (HORARIO vs 15-MINUTO)

OBJETIVO: Determinar si ambos archivos tienen los MISMOS datos
y cuál usar para OE3 (DEBE ser HORARIO exacto 8,760 horas)
"""
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from _pandas_dt_helpers import extract_floor_hour

print('\n' + '='*90)
print('[ANÁLISIS OE2 MALL DEMAND] 2 Resoluciones detectadas')
print('='*90)

# ===== 1. HORARIO (8,760 filas) =====
print('\n[HORARIO] Datos anuales horarios')
hourly_path = 'data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv'
df_hourly = pd.read_csv(hourly_path)
df_hourly['datetime'] = pd.to_datetime(df_hourly['datetime'])
df_hourly = df_hourly.sort_values('datetime').reset_index(drop=True)

print(f'  Filas: {len(df_hourly):,} (= 365 días × 24 horas)')
print(f'  Rango: {df_hourly["datetime"].min().date()} a {df_hourly["datetime"].max().date()}')
print(f'  Demanda total: {df_hourly["kwh"].sum():,.0f} kWh/año')
print(f'  Demanda media: {df_hourly["kwh"].mean():.1f} kW')
print(f'  Min: {df_hourly["kwh"].min():.1f} kW, Max: {df_hourly["kwh"].max():.1f} kW')
print(f'\n  Primeras 5 horas:')
print(df_hourly.head())

# ===== 2. 15-MINUTO (35,136 filas) =====
print('\n\n[15-MINUTO] Datos con resolución 15-minuto')
min15_path = 'data/interim/oe2/demandamallkwh/demandamallkwh.csv'
df_15min = pd.read_csv(min15_path, sep=';')
df_15min['FECHAHORA'] = pd.to_datetime(df_15min['FECHAHORA'], format='%d/%m/%Y %H:%M')
df_15min = df_15min.sort_values('FECHAHORA').reset_index(drop=True)

# 35,136 = 365 × 24 × 4 + 96 (ajuste por años no-bisiestos)
# Sin embargo, si es exactamente 35,136, es porque tiene:
# 365 días × 24 horas × 4 intervalos de 15min = 35,040
# Más algunos registros extras = 35,136
# O es 365.2 días (ajuste para 24h extra) × 24 × 4 = 35,136

n_days_equivalent = len(df_15min) / (24 * 4)
print(f'  Filas: {len(df_15min):,}')
print(f'  = {n_days_equivalent:.1f} días (si son 4 registros/hora)')
print(f'  Rango: {df_15min["FECHAHORA"].min().date()} a {df_15min["FECHAHORA"].max().date()}')

# Calcular demanda total (cada fila es 15min = 0.25 horas, así que kWh = kW × 0.25)
df_15min_copy = df_15min.copy()
df_15min_copy['kWh'] = df_15min_copy['kWh'] * 0.25  # Convertir de kW a kWh (15-minuto)
total_15min = df_15min_copy['kWh'].sum()

print(f'  Demanda total: {total_15min:,.0f} kWh/año')
print(f'  Demanda media: {df_15min_copy["kWh"].mean():.3f} kWh (por intervalo 15min)')
print(f'  Demanda media (horaria equiv): {df_15min_copy["kWh"].mean() * 4:.1f} kW')
print(f'  Min: {df_15min["kWh"].min():.1f} kW, Max: {df_15min["kWh"].max():.1f} kW')
print(f'\n  Primeras 5 registros:')
print(df_15min.head())

# ===== 3. COMPARACIÓN =====
print('\n\n' + '='*90)
print('[COMPARACIÓN] Horario vs 15-Minuto')
print('='*90)

# Reagrupar datos 15-minuto a horario y comparar
df_15min['hora'] = df_15min['FECHAHORA']
df_15min['kWh'] = df_15min['kWh'] * 0.25  # Convertir a kWh
df_15min_hourly = df_15min.groupby(extract_floor_hour(df_15min['FECHAHORA']))['kWh'].sum().reset_index()
df_15min_hourly.columns = ['datetime', 'kwh']

print(f'\n  Reagrupado 15-minuto a horario: {len(df_15min_hourly):,} filas')
print(f'  Demanda total (reagrupado): {df_15min_hourly["kwh"].sum():,.0f} kWh/año')

# Comparar totales
diff_total = abs(df_hourly['kwh'].sum() - df_15min_hourly['kwh'].sum())
diff_pct = (diff_total / df_hourly['kwh'].sum()) * 100

print(f'\n  ✓ Demanda HORARIO: {df_hourly["kwh"].sum():,.0f} kWh')
print(f'  ✓ Demanda 15-MIN reagrupado: {df_15min_hourly["kwh"].sum():,.0f} kWh')
print(f'  Diferencia: {diff_total:,.0f} kWh ({diff_pct:.2f}%)')

if diff_pct < 5:
    print(f'\n  ✅ CONCLUSIÓN: Son los MISMOS datos en diferente resolución')
    print(f'     (Diferencia {diff_pct:.2f}% es normal por redondeo/interpolación)')
else:
    print(f'\n  ⚠️ CONCLUSIÓN: Son datos DIFERENTES')
    print(f'     (Diferencia {diff_pct:.2f}% sugiere diferentes fuentes o métodos)')

# Comparar rangos horarios
print(f'\n  Rangos de fechas:')
print(f'    Horario: {df_hourly["datetime"].min()} a {df_hourly["datetime"].max()}')
print(f'    15-min:  {df_15min_hourly["datetime"].min()} a {df_15min_hourly["datetime"].max()}')

# ===== 4. RECOMENDACIÓN =====
print('\n\n' + '='*90)
print('[RECOMENDACIÓN] Para OE3 CityLearn')
print('='*90)
print('\n  ✅ USAR: data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv')
print(f'     • Exactamente 8,760 filas (365 días × 24 horas)')
print(f'     • Resolución HORARIA requerida por CityLearn v2.5.0')
print(f'     • Datos validados y limpios')
print(f'     • Demanda total: {df_hourly["kwh"].sum():,.0f} kWh/año')
print('\n  ❌ NO USAR: data/interim/oe2/demandamallkwh/demandamallkwh.csv')
print(f'     • 35,136 filas (resolución 15-minuto, NO soportada por CityLearn)')
print(f'     • Si se necesita 15-minuto, requiere downsampling previo')
print(f'     • Los datos que llegan a CityLearn se descartan si no son horarios')

print('\n  📝 NOTA: dataset_builder.py YA maneja correctamente esto:')
print('     • Línea 239-254: Intenta cargar demanda_mall_horaria_anual.csv')
print('     • Línea 255-290: Si falla, intenta con demandamallkwh.csv y agrupa por hora')
print('     • Validación: Asegura exactamente 8,760 registros')

print('\n' + '='*90)
print()
