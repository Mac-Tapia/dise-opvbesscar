#!/usr/bin/env python
"""Generar archivo de demanda horaria del mall para 8760 timesteps"""

import pandas as pd
from pathlib import Path
import numpy as np

# Patrón horario típico de mall (varía por hora del día)
hourly_pattern = {
    0: 95,    # Madrugada
    1: 85,
    2: 80,
    3: 78,
    4: 75,
    5: 80,
    6: 95,    # Amanecer
    7: 110,
    8: 130,   # Mañana
    9: 160,
    10: 180,
    11: 190,
    12: 200,  # Mediodía (pico)
    13: 190,
    14: 180,
    15: 170,
    16: 175,  # Tarde
    17: 185,
    18: 195,  # Atardecer (pico)
    19: 190,
    20: 170,  # Noche
    21: 150,
    22: 120,
    23: 100,
}

# Variación mensual (% adicional)
monthly_factor = {
    1: 1.05,   # Enero: 5% más
    2: 1.03,
    3: 1.00,
    4: 0.98,
    5: 0.95,   # Mayo-Junio: menos uso AC (invierno)
    6: 0.92,
    7: 0.93,
    8: 0.95,
    9: 0.98,
    10: 1.02,
    11: 1.05,  # Noviembre-Diciembre: más uso
    12: 1.08,
}

# Generar datos para 365 días × 24 horas
records = []
for day in range(365):
    # Determinar mes y fecha
    date = pd.Timestamp('2024-01-01') + pd.Timedelta(days=day)
    month = date.month
    month_factor = monthly_factor.get(month, 1.0)

    # Aplicar variación por día de semana (fines de semana más bajos)
    day_of_week = date.dayofweek  # 0=Monday, 6=Sunday
    weekday_factor = 0.90 if day_of_week >= 5 else 1.0  # -10% fin de semana

    for hour in range(24):
        base_demand = hourly_pattern[hour]

        # Aplicar variaciones
        demand = base_demand * month_factor * weekday_factor

        # Agregar ruido pequeño (~5%)
        noise = np.random.normal(1.0, 0.02)
        demand = max(70, demand * noise)  # Mínimo 70 kW

        records.append({
            'fecha': date.strftime('%Y-%m-%d'),
            'hora': hour,
            'demanda_kw': round(demand, 2)
        })

# Crear DataFrame
df = pd.DataFrame(records)

# Verificar
print(f'Generando demanda del mall:')
print(f'  Total de filas: {len(df)} (¿= 8760? {len(df) == 8760})')
print(f'  Rango de demanda: {df["demanda_kw"].min():.1f} - {df["demanda_kw"].max():.1f} kW')
print(f'  Promedio: {df["demanda_kw"].mean():.1f} kW')

# Guardar
output_path = Path('data/interim/oe2/mall_demand_hourly.csv')
df.to_csv(output_path, index=False)
print(f'\n✓ Archivo guardado: {output_path}')
print(f'  Columnas: {list(df.columns)}')
print(f'  Primeras 5 filas:')
print(df.head())
print(f'\n  Últimas 5 filas:')
print(df.tail())
