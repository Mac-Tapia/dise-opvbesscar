import sys
sys.path.insert(0, 'src')
from iquitos_citylearn.oe2.chargers import build_hourly_profile

# Generar perfil de 15 minutos
profile = build_hourly_profile(
    energy_day_kwh=3252.0,
    opening_hour=9,
    closing_hour=22,
    peak_hours=[18, 19, 20, 21],
    peak_share_day=0.4
)

print(f"\n{'='*70}")
print("VERIFICACIÓN PERFIL DE 15 MINUTOS")
print(f"{'='*70}\n")

print(f"Intervalos generados: {len(profile)} (esperado: 96 para 24h × 4)")
print(f"Resolución temporal: 15 minutos\n")

print(f"Primeros 12 intervalos (primeras 3 horas):")
print(profile.head(12)[['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']])

print(f"\nIntervalos de hora pico (18h-19h = intervalos 72-75):")
peak_start = 18 * 4
peak_end = 19 * 4
print(profile.iloc[peak_start:peak_end][['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']])

print(f"\nÚltimos 12 intervalos (últimas 3 horas):")
print(profile.tail(12)[['interval', 'time_of_day', 'hour', 'minute', 'energy_kwh', 'power_kw', 'is_peak']])

print(f"\nRESUMEN:")
print(f"  Total energía: {profile['energy_kwh'].sum():.2f} kWh (esperado: 3252.00 kWh)")
print(f"  Energía pico: {profile[profile['is_peak']]['energy_kwh'].sum():.2f} kWh")
print(f"  Energía fuera pico: {profile[~profile['is_peak']]['energy_kwh'].sum():.2f} kWh")
print(f"  Potencia máxima: {profile['power_kw'].max():.2f} kW")
print(f"  Potencia promedio: {profile['power_kw'].mean():.2f} kW")

print(f"\n{'='*70}\n")
