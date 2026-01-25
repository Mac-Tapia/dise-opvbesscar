"""
Visualización completa del perfil de carga de 15 minutos
Mostrando la rampa de subida, hora pico, rampa de bajada y cierre
"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

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
    if len(data_hora) > 0:
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
print(f"\nVerificación rampa descendente:")
print(f"  21:00 → 21:15: {hora_21.iloc[0]['power_kw']:.2f} → {hora_21.iloc[1]['power_kw']:.2f} kW (↓{hora_21.iloc[0]['power_kw'] - hora_21.iloc[1]['power_kw']:.2f} kW)")
print(f"  21:15 → 21:30: {hora_21.iloc[1]['power_kw']:.2f} → {hora_21.iloc[2]['power_kw']:.2f} kW (↓{hora_21.iloc[1]['power_kw'] - hora_21.iloc[2]['power_kw']:.2f} kW)")
print(f"  21:30 → 21:45: {hora_21.iloc[2]['power_kw']:.2f} → {hora_21.iloc[3]['power_kw']:.2f} kW (↓{hora_21.iloc[2]['power_kw'] - hora_21.iloc[3]['power_kw']:.2f} kW)")

print("\n" + "=" * 80)
print("DETALLES - HORA DE CIERRE (22h) - CERO")
print("=" * 80)
hora_22 = df[df['hour'] == 22][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw']]
print(hora_22.to_string(index=False))

print("\n" + "=" * 80)
print("VERIFICACIÓN FINAL")
print("=" * 80)
print(f"✅ Total energía: {df['energy_kwh'].sum():.2f} kWh (objetivo: 3,252.00 kWh)")
print(f"✅ Energía hora pico (18-21h): {df[df['is_peak']]['energy_kwh'].sum():.2f} kWh (40% = 1,300.80 kWh)")
print(f"✅ Energía fuera pico: {df[~df['is_peak']]['energy_kwh'].sum():.2f} kWh (60% = 1,951.20 kWh)")
print(f"✅ Energía a las 22h (cierre): {df[df['hour'] == 22]['energy_kwh'].sum():.2f} kWh (debe ser 0.00)")
print(f"✅ Rampa descendente 21h: {hora_21['power_kw'].is_monotonic_decreasing} (debe ser True)")
print(f"✅ Potencia máxima sistema: {df['power_kw'].max():.2f} kW")

# Calcular distribución por período
apertura = df[(df['hour'] >= 9) & (df['hour'] < 18)]['energy_kwh'].sum()
pico = df[(df['hour'] >= 18) & (df['hour'] < 21)]['energy_kwh'].sum()
cierre_rampa = df[df['hour'] == 21]['energy_kwh'].sum()

print(f"\n{'=' * 80}")
print("DISTRIBUCIÓN DE ENERGÍA POR PERÍODO")
print("=" * 80)
print(f"Apertura → Pre-pico (9h-18h):  {apertura:>10.2f} kWh  ({apertura/df['energy_kwh'].sum()*100:>5.1f}%)")
print(f"Hora pico (18h-21h):            {pico:>10.2f} kWh  ({pico/df['energy_kwh'].sum()*100:>5.1f}%)")
print(f"Rampa cierre (21h):             {cierre_rampa:>10.2f} kWh  ({cierre_rampa/df['energy_kwh'].sum()*100:>5.1f}%)")
print(f"Cierre (22h):                   {0.00:>10.2f} kWh  ({0.0:>5.1f}%)")
print("-" * 80)
print(f"TOTAL:                          {df['energy_kwh'].sum():>10.2f} kWh  (100.0%)")
