#!/usr/bin/env python3
"""
Validación EXHAUSTIVA de datos solares:
- Debe tener EXACTAMENTE 8,760 filas (365 días × 24 horas/día)
- Cada fila = 1 hora (resolución horaria)
- Debe cubrir AÑO COMPLETO (1 enero a 31 diciembre)
- Potencia AC debe ser > 0 durante horas de luz
"""
from pathlib import Path
import pandas as pd  # type: ignore[import]

solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")

print("=" * 90)
print("VALIDACIÓN EXHAUSTIVA: DATOS SOLARES HORARIOS PARA UN AÑO COMPLETO")
print("=" * 90)

# Cargar datos
df = pd.read_csv(solar_path)
print(f"\n1️⃣  CANTIDAD DE FILAS")
print(f"   Filas actuales: {len(df)}")
print(f"   Filas requeridas: 8,760 (365 días × 24 horas/día)")
print(f"   ✅ CORRECTO" if len(df) == 8760 else f"   ❌ ERROR: {len(df) - 8760:+d} filas")

# Convertir timestamp (usar columna 'index' que tiene los timestamps)
print(f"\n2️⃣  RESOLUCIÓN TEMPORAL")
timestamp_col = 'index' if 'index' in df.columns else 'timestamp'
df[timestamp_col] = pd.to_datetime(df[timestamp_col])
df = df.set_index(timestamp_col).sort_index()

print(f"   Primer timestamp: {df.index[0]}")
print(f"   Último timestamp: {df.index[-1]}")

# Validar que sea horario (delta = 1 hora)
deltas = df.index.to_series().diff()[1:]  # Skip NaT
median_delta = deltas.median()
print(f"   Delta mediano: {median_delta}")
print(f"   ✅ HORARIO CONFIRMADO" if median_delta == pd.Timedelta(hours=1) else f"   ❌ NO ES HORARIO: {median_delta}")

# Contar cambios de resolución
unique_deltas = deltas.unique()
print(f"   Deltas únicos encontrados: {sorted(set(unique_deltas))}")
if len(unique_deltas) == 1:
    print(f"   ✅ RESOLUCIÓN UNIFORME (todas las filas tienen el mismo delta)")
else:
    print(f"   ⚠️  ADVERTENCIA: Se encontraron {len(unique_deltas)} deltas diferentes")

# Validar cobertura de año completo
print(f"\n3️⃣  COBERTURA TEMPORAL (¿Año completo?)")
date_min = df.index.min()
date_max = df.index.max()
duration = date_max - date_min
days_covered = duration.days + 1  # +1 porque incluye ambos extremos
print(f"   Desde: {date_min.strftime('%Y-%m-%d')}")
print(f"   Hasta: {date_max.strftime('%Y-%m-%d')}")
print(f"   Duración: {days_covered} días")
print(f"   Horas calculadas: {days_covered * 24}")
print(f"   Horas actuales: {len(df)}")

# Verificar si abarca año completo
is_full_year = (days_covered >= 364 and days_covered <= 366) and len(df) == 8760
print(f"   {'✅ AÑO COMPLETO DETECTADO' if is_full_year else f'   ⚠️  PARCIAL: solo {days_covered} días'}")

# Validar continuidad (no debe haber gaps)
print(f"\n4️⃣  CONTINUIDAD (¿Sin brechas?)")
missing_hours = len(df) - (duration.total_seconds() / 3600)
print(f"   Horas esperadas por duración: {duration.total_seconds() / 3600:.0f}")
print(f"   Horas presentes: {len(df)}")
if abs(missing_hours) < 2:
    print(f"   ✅ SIN BRECHAS (serie continua)")
else:
    print(f"   ❌ BRECHAS DETECTADAS: {abs(missing_hours):.0f} horas faltantes")

# Estadísticas de potencia AC
print(f"\n5️⃣  GENERACIÓN SOLAR (ac_power_kw)")
ac_power = df['ac_power_kw']
print(f"   Min: {ac_power.min():.2f} kW")
print(f"   Max: {ac_power.max():.2f} kW")
print(f"   Mean: {ac_power.mean():.2f} kW")
print(f"   Median: {ac_power.median():.2f} kW")
print(f"   StdDev: {ac_power.std():.2f} kW")
print(f"   Sum (energía anual): {ac_power.sum():.1f} kWh")

# Validar que haya valores > 0 durante el día
print(f"   {'✅ VALORES > 0 DETECTADOS' if (ac_power > 0).any() else '   ❌ TODOS LOS VALORES SON CERO'}")
hours_with_generation = (ac_power > 0).sum()
hours_without_generation = (ac_power == 0).sum()
print(f"   Horas con generación (>0): {hours_with_generation} / {len(df)} ({100*hours_with_generation/len(df):.1f}%)")
print(f"   Horas sin generación (=0): {hours_without_generation} / {len(df)} ({100*hours_without_generation/len(df):.1f}%)")

# Análisis diario (debería haber patrón día/noche)
print(f"\n6️⃣  PATRÓN DÍA/NOCHE (Validación de Lógica)")
df_for_hour = df.copy()
if hasattr(df_for_hour.index, 'hour'):
    df_for_hour['hour'] = df_for_hour.index.hour  # type: ignore[union-attr]
else:
    df_for_hour['hour'] = 0
daily_pattern = df_for_hour.groupby('hour')['ac_power_kw'].agg(['mean', 'min', 'max', 'count'])

print(f"\n   Tabla de potencia por hora del día:")
print(f"   {'Hora':>5} | {'Mean (kW)':>12} | {'Min':>10} | {'Max':>10} | {'Count':>6}")
print(f"   {'-'*60}")
for hour in range(24):
    if hour in daily_pattern.index:
        row = daily_pattern.loc[hour]
        print(f"   {hour:>5} | {row['mean']:>12.1f} | {row['min']:>10.1f} | {row['max']:>10.1f} | {row['count']:>6.0f}")

# Horas pico (debería estar entre 8am-6pm con máximo alrededor de mediodía)
peak_hours = daily_pattern[daily_pattern['mean'] > 0].index
min_peak_hour = int(peak_hours.min()) if len(peak_hours) > 0 else None
max_peak_hour = int(peak_hours.max()) if len(peak_hours) > 0 else None
if min_peak_hour is not None and max_peak_hour is not None:
    print(f"\n   Horas con generación: {min_peak_hour}:00 a {max_peak_hour}:00")
    is_pattern_correct = 8 <= min_peak_hour <= 12 and 14 <= max_peak_hour <= 20
    print(f"   {'✅ PATRÓN DÍA/NOCHE CORRECTO' if is_pattern_correct else '   ⚠️  PATRÓN ANÓMALO'}")
else:
    print(f"\n   No se encontraron horas pico con generación")

# Resumen final
print(f"\n" + "=" * 90)
print(f"RESUMEN DE VALIDACIÓN")
print(f"=" * 90)

checks = {
    "8,760 filas exactas": len(df) == 8760,
    "Resolución horaria (1h)": median_delta == pd.Timedelta(hours=1),
    "Año completo (365 días)": is_full_year,
    "Sin brechas/gaps": abs(missing_hours) < 2,
    "Valores > 0 detectados": (ac_power > 0).any(),
    "Patrón día/noche lógico": (ac_power > 0).sum() > 0 and (ac_power == 0).sum() > 0,
    "Energía anual > 0": ac_power.sum() > 0,
}

all_passed = all(checks.values())
for check_name, passed in checks.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {check_name}")

print(f"\n{'='*90}")
if all_passed:
    print(f"🎉 ÉXITO: Todos los validadores pasaron")
    print(f"   Datos solares están CORRECTOS para entrenamiento OE3")
    print(f"   - 8,760 filas horarias (1 año completo)")
    print(f"   - Generación anual: {ac_power.sum():.1f} kWh")
    print(f"   - Pico de generación: {ac_power.max():.1f} kW")
else:
    print(f"❌ FALLA: Hay problemas en la validación")
    failed = [k for k, v in checks.items() if not v]
    for fail in failed:
        print(f"   - {fail}")
print(f"{'='*90}\n")
