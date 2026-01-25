"""
Generador de perfil solar simplificado para Iquitos
Basado en patrón típico de radiación solar ecuatorial
"""
import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 80)
print("GENERACIÓN DE PERFIL SOLAR SIMPLIFICADO")
print("=" * 80)

# Parámetros
print("\n⚙️ Parámetros:")
print("   Ubicación: Iquitos, Loreto, Perú (3.7°S)")
print("   Energía diaria objetivo: 22,036 kWh")
print("   Horario generación: 5h - 17h (12 horas)")
print("   Patrón: Curva gaussiana centrada al mediodía")

# Crear perfil horario (24 horas)
hours = np.arange(24)

# Parámetros de la curva gaussiana
peak_hour = 12  # Mediodía solar
width = 3.5  # Ancho de la curva
peak_power = 1812.5  # Potencia pico al mediodía

# Generar curva gaussiana
gaussian = np.exp(-((hours - peak_hour) ** 2) / (2 * width ** 2))

# Aplicar límites (solo 5h-17h)
pv_kwh = np.zeros(24)
for h in range(24):
    if 5 <= h <= 17:
        pv_kwh[h] = peak_power * gaussian[h]
    else:
        pv_kwh[h] = 0.0

# Normalizar para alcanzar objetivo diario
current_total = pv_kwh.sum()
target_total = 22036  # kWh/día
scaling_factor = target_total / current_total
pv_kwh = pv_kwh * scaling_factor

# Crear DataFrame
df = pd.DataFrame({
    'hour': hours,
    'pv_kwh': pv_kwh
})

# Guardar
output_path = Path("data/oe2/pv_profile_24h.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

print(f"\n📊 Perfil generado:")
print(f"   Total diario: {pv_kwh.sum():.2f} kWh")
print(f"   Potencia pico: {pv_kwh.max():.2f} kW (hora {pv_kwh.argmax()})")
print(f"   Horas de generación: {np.sum(pv_kwh > 0)} horas")

# Mostrar distribución horaria
print(f"\n📈 Distribución horaria:")
print(f"{'Hora':<6} {'Generación (kWh)':<20} {'Gráfica':<40}")
print("-" * 70)
for h, kwh in enumerate(pv_kwh):
    if kwh > 0:
        bar_length = int((kwh / pv_kwh.max()) * 40)
        bar = "█" * bar_length
        print(f"{h:>4}h  {kwh:>17.2f}  {bar}")

print(f"\n✅ Perfil guardado en: {output_path.resolve()}")

# Generar también serie temporal anual (opcional)
print(f"\n📅 Generando serie temporal anual...")

# Repetir patrón diario 365 veces con variación estacional
days = 365
df_annual = pd.DataFrame()

for day in range(days):
    # Factor estacional (máximo en verano, mínimo en invierno)
    # En el ecuador la variación es menor (~10%)
    day_of_year = day + 1
    seasonal_factor = 1.0 + 0.05 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Repetir perfil diario con factor estacional
    day_data = pd.DataFrame({
        'datetime': pd.date_range(start=f'2024-01-01 00:00', periods=24, freq='h') + pd.Timedelta(days=day),
        'pv_kwh': pv_kwh * seasonal_factor
    })

    df_annual = pd.concat([df_annual, day_data], ignore_index=True)

# Guardar serie temporal
timeseries_path = Path("data/oe2/pv_generation_timeseries.csv")
df_annual.to_csv(timeseries_path, index=False)

print(f"   Serie anual: {len(df_annual)} puntos (8,760 horas)")
print(f"   Total anual: {df_annual['pv_kwh'].sum():.0f} kWh")
print(f"   Promedio diario: {df_annual['pv_kwh'].sum() / 365:.0f} kWh")
print(f"   ✅ Guardado en: {timeseries_path.resolve()}")

print("\n" + "=" * 80)
print("✅ GENERACIÓN COMPLETADA")
print("=" * 80)
print("\nAhora puedes ejecutar:")
print("   python PROBAR_BESS_15MIN.py")
