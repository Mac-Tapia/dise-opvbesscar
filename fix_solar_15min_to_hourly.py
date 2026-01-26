#!/usr/bin/env python3
"""
Convertir datos solares de 15 minutos a 1 hora.
El archivo pv_generation_timeseries.csv viene en 15-min (data subhoraria)
pero CityLearn requiere exactamente 8,760 filas horarias (1 por hora del año).
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd  # type: ignore[import-not-found]
import numpy as np  # type: ignore[import-not-found]

solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")

print("=" * 80)
print("CONVERTIR DATOS SOLARES DE 15-MIN A HORARIO")
print("=" * 80)

# Leer datos en 15-min
df = pd.read_csv(solar_path)  # type: ignore[attr-defined]
print(f"\n✓ Archivo original cargado: {len(df)} filas")
print(f"  Primeras filas:\n{df.head()}")
print(f"  Columnas: {df.columns.tolist()}")

# Validar que es 15-min (cada 4 datos = 1 hora)
if len(df) % 4 == 0:
    print(f"\n✓ Confirmado: {len(df)} filas ÷ 4 = {len(df)//4} horas")
else:
    print(f"\n⚠ ADVERTENCIA: {len(df)} no es divisible por 4")

# Convertir timestamp a datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])  # type: ignore[attr-defined,index]
df = df.set_index('timestamp')  # type: ignore[attr-defined]

print(f"\nRango de datos: {df.index.min()} a {df.index.max()}")

# Resamplear a horario - usar la suma de 4 datos de 15-min por hora
df_hourly = df.resample('h').agg({  # type: ignore[attr-defined]
    'ghi_wm2': 'mean',      # Irradiancia: promedio
    'dni_wm2': 'mean',      # DNI: promedio
    'dhi_wm2': 'mean',      # DHI: promedio
    'temp_air_c': 'mean',   # Temperatura: promedio
    'wind_speed_ms': 'mean', # Viento: promedio
    'dc_power_kw': 'sum',   # Potencia DC: suma (4 intervalos de 15-min = 1 hora)
    'ac_power_kw': 'sum',   # Potencia AC: suma
    'dc_energy_kwh': 'sum', # Energía DC: suma
    'ac_energy_kwh': 'sum', # Energía AC: suma
    'pv_kwh': 'sum',        # PV energía: suma
    'pv_kw': 'sum',         # PV potencia: suma
})

print(f"\n✓ Datos resampled a horario: {len(df_hourly)} filas")
print(f"  Primeras filas:\n{df_hourly.head()}")
print(f"  Ultimas filas:\n{df_hourly.tail()}")

# Validar que tenemos exactamente 8,760 horas (365 días × 24 horas)
if len(df_hourly) != 8760:
    print(f"\n⚠ ADVERTENCIA: Se esperaban 8,760 filas, pero se obtuvieron {len(df_hourly)}")
    print(f"  Ajustando a exactamente 8,760 filas...")
    if len(df_hourly) > 8760:
        df_hourly = df_hourly.iloc[:8760]
    else:
        # Rellenar con ceros si falta
        missing = 8760 - len(df_hourly)
        print(f"  Faltan {missing} filas, rellenando con ceros")
        df_hourly = df_hourly.reindex(pd.date_range(df_hourly.index[0], periods=8760, freq='h'), fill_value=0.0)  # type: ignore[attr-defined]

print(f"\n✓ FINAL: {len(df_hourly)} filas horarias (correctas: {len(df_hourly) == 8760})")

# Resetear índice para escribir CSV
df_hourly_reset = df_hourly.reset_index()
df_hourly_reset.rename(columns={'timestamp': 'timestamp'}, inplace=True)

# Escribir archivo resampled
print(f"\n💾 Escribiendo archivo resampled...")
df_hourly_reset.to_csv(solar_path, index=False)

print(f"✓ Archivo guardado: {solar_path}")
print(f"\nEstadísticas de potencia AC (ac_power_kw):")
print(f"  Min: {df_hourly_reset['ac_power_kw'].min():.2f} kW")
print(f"  Max: {df_hourly_reset['ac_power_kw'].max():.2f} kW")
print(f"  Mean: {df_hourly_reset['ac_power_kw'].mean():.2f} kW")
print(f"  Sum: {df_hourly_reset['ac_power_kw'].sum():.1f} kWh (año)")

print(f"\nEstadísticas de PV energía (pv_kwh):")
print(f"  Min: {df_hourly_reset['pv_kwh'].min():.2f} kWh")
print(f"  Max: {df_hourly_reset['pv_kwh'].max():.2f} kWh")
print(f"  Mean: {df_hourly_reset['pv_kwh'].mean():.2f} kWh")
print(f"  Sum: {df_hourly_reset['pv_kwh'].sum():.1f} kWh (año)")

print(f"\n{'='*80}")
print("✅ CONVERSIÓN COMPLETADA")
print(f"{'='*80}")
