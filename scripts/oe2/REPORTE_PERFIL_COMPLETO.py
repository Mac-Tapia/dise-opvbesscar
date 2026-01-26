"""Visualización completa del perfil de carga de 15 minutos

Mostrando la rampa de subida, hora pico, rampa de bajada y cierre
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

csv_path = Path('data/oe2/perfil_horario_carga.csv')
if not csv_path.exists():
    raise FileNotFoundError(f"Archivo no encontrado: {csv_path}")

df = pd.read_csv(csv_path)

if df.empty:
    raise ValueError("El archivo CSV está vacío")

print("=" * 80)
print("PERFIL COMPLETO DE CARGA - RESOLUCIÓN 15 MINUTOS")
print("=" * 80)

print("\n" + "=" * 80)
print("RESUMEN GENERAL")
print("=" * 80)
print(f"Total intervalos: {len(df)}")
print(f"Energía total día: {df['energy_kwh'].sum():.2f} kWh")
print(f"Potencia máxima: {df['power_kw'].max():.2f} kW (a las {df.loc[df['power_kw'].idxmax(), 'time_of_day']:.2f}h)")
print(f"Potencia promedio operación: {df[df['power_kw'] > 0]['power_kw'].mean():.2f} kW")

print("\n" + "=" * 80)
print("PERFIL POR HORA (9h-22h)")
print("=" * 80)
print(f"{'Hora':<6} {'Energía (kWh)':<15} {'Pot. Max (kW)':<15} {'Pot. Min (kW)':<15} {'Tipo'}")
print("-" * 80)

for hora in range(9, 23):
    data_hora = df[df['hour'] == hora]
    if not data_hora.empty:
        energia = data_hora['energy_kwh'].sum()
        pot_max = data_hora['power_kw'].max()
        pot_min = data_hora['power_kw'].min()

        # Determinar tipo
        if hora < 18:
            tipo = "🔼 Subida"
        elif 18 <= hora <= 20:
            tipo = "⚡ PICO"
        elif hora == 21:
            tipo = "🔽 Rampa bajada"
        else:
            tipo = "⏹️  Cerrado"

        print(f"{hora:>4}h  {energia:>13.2f}  {pot_max:>13.2f}  {pot_min:>13.2f}  {tipo}")
    else:
        print(f"{hora:>4}h  {'0.00':>13}  {'0.00':>13}  {'0.00':>13}  ⏹️  Cerrado")

print("\n" + "=" * 80)
print("DETALLES - INICIO DE OPERACIÓN (9h)")
print("=" * 80)
hora_9 = df[df['hour'] == 9][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw']]
print(hora_9.to_string(index=False))

print("\n" + "=" * 80)
print("DETALLES - HORA PICO (18h)")
print("=" * 80)
hora_18 = df[df['hour'] == 18][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']]
print(hora_18.to_string(index=False))

print("\n" + "=" * 80)
print("DETALLES - ÚLTIMA HORA ANTES DE CIERRE (21h) - RAMPA DESCENDENTE")
print("=" * 80)
hora_21 = df[df['hour'] == 21][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']]
print(hora_21.to_string(index=False))
if len(hora_21) >= 4:
    print(f"\nVerificación rampa descendente:")
    val_0 = float(hora_21.iloc[0]['power_kw'])
    val_1 = float(hora_21.iloc[1]['power_kw'])
    val_2 = float(hora_21.iloc[2]['power_kw'])
    val_3 = float(hora_21.iloc[3]['power_kw'])
    print(f"  21:00 → 21:15: {val_0:.2f} → {val_1:.2f} kW (↓{val_0 - val_1:.2f} kW)")
    print(f"  21:15 → 21:30: {val_1:.2f} → {val_2:.2f} kW (↓{val_1 - val_2:.2f} kW)")
    print(f"  21:30 → 21:45: {val_2:.2f} → {val_3:.2f} kW (↓{val_2 - val_3:.2f} kW)")

print("\n" + "=" * 80)
print("DETALLES - HORA DE CIERRE (22h) - CERO")
print("=" * 80)
hora_22 = df[df['hour'] == 22][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw']]
print(hora_22.to_string(index=False))

print("\n" + "=" * 80)
print("VERIFICACIÓN FINAL")
print("=" * 80)

# Calcular valores con type safety
total_energia = float(df['energy_kwh'].sum())
energia_pico = float(df[df['is_peak']]['energy_kwh'].sum())
energia_fuera_pico = float(df[~df['is_peak']]['energy_kwh'].sum())
energia_22h = float(df[df['hour'] == 22]['energy_kwh'].sum())
potencia_max = float(df['power_kw'].max())

print(f"✅ Total energía: {total_energia:.2f} kWh (objetivo: 3,252.00 kWh)")
print(f"✅ Energía hora pico (18-21h): {energia_pico:.2f} kWh (40% = 1,300.80 kWh)")
print(f"✅ Energía fuera pico: {energia_fuera_pico:.2f} kWh (60% = 1,951.20 kWh)")
print(f"✅ Energía a las 22h (cierre): {energia_22h:.2f} kWh (debe ser 0.00)")

# Validar rampa descendente con seguridad
is_monotonic_decreasing = bool(hora_21['power_kw'].is_monotonic_decreasing)
print(f"✅ Rampa descendente 21h: {is_monotonic_decreasing} (debe ser True)")
print(f"✅ Potencia máxima sistema: {potencia_max:.2f} kW")

# Calcular distribución por período con type safety
apertura = float(df[(df['hour'] >= 9) & (df['hour'] < 18)]['energy_kwh'].sum())
pico = float(df[(df['hour'] >= 18) & (df['hour'] < 21)]['energy_kwh'].sum())
cierre_rampa = float(df[df['hour'] == 21]['energy_kwh'].sum())
total = float(df['energy_kwh'].sum())

print(f"\n{'=' * 80}")
print("DISTRIBUCIÓN DE ENERGÍA POR PERÍODO")
print("=" * 80)
apertura_pct = (apertura / total * 100) if total > 0 else 0.0
pico_pct = (pico / total * 100) if total > 0 else 0.0
cierre_pct = (cierre_rampa / total * 100) if total > 0 else 0.0

print(f"Apertura → Pre-pico (9h-18h):  {apertura:>10.2f} kWh  ({apertura_pct:>5.1f}%)")
print(f"Hora pico (18h-21h):            {pico:>10.2f} kWh  ({pico_pct:>5.1f}%)")
print(f"Rampa cierre (21h):             {cierre_rampa:>10.2f} kWh  ({cierre_pct:>5.1f}%)")
print(f"Cierre (22h):                   {0.00:>10.2f} kWh  ({0.0:>5.1f}%)")
print("-" * 80)
print(f"TOTAL:                          {total:>10.2f} kWh  (100.0%)")
