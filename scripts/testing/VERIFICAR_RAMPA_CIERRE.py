"""
Verificar rampa descendente en hora 21 y cierre en hora 22
"""
import pandas as pd

df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print('=' * 70)
print('ÚLTIMA HORA ANTES DEL CIERRE (21h) - RAMPA DESCENDENTE:')
print('=' * 70)
hora_21 = df[df['hour'] == 21][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']]
print(hora_21.to_string(index=False))

print('\n' + '=' * 70)
print('HORA DE CIERRE (22h) - DEBE SER CERO:')
print('=' * 70)
hora_22 = df[df['hour'] == 22][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']]
print(hora_22.to_string(index=False))

print('\n' + '=' * 70)
print('RESUMEN:')
print('=' * 70)
print(f'Total energía día: {df["energy_kwh"].sum():.2f} kWh')
print(f'Energía a las 21h: {df[df["hour"] == 21]["energy_kwh"].sum():.2f} kWh')
print(f'Energía a las 22h: {df[df["hour"] == 22]["energy_kwh"].sum():.2f} kWh')
print(f'Potencia máxima 21h: {df[df["hour"] == 21]["power_kw"].max():.2f} kW')
print(f'Potencia mínima 21h: {df[df["hour"] == 21]["power_kw"].min():.2f} kW')

if df[df["hour"] == 22]["energy_kwh"].sum() == 0:
    print('\n✅ CORRECTO: Energía a las 22h es CERO (mall cerrado)')
else:
    print('\n❌ ERROR: Energía a las 22h NO es cero')

if df[df["hour"] == 21]["power_kw"].is_monotonic_decreasing:
    print('✅ CORRECTO: Rampa descendente en hora 21')
else:
    print('⚠️  VERIFICAR: Rampa en hora 21 puede no ser monotónica')
