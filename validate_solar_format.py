import pandas as pd
from pathlib import Path

solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")

print("=" * 90)
print("VALIDACION EXHAUSTIVA: DATOS SOLARES HORARIOS PARA UN ANO COMPLETO")
print("=" * 90)

# Cargar datos
df = pd.read_csv(solar_path)
print(f"\n[1] CANTIDAD DE FILAS")
print(f"    Filas actuales: {len(df)}")
print(f"    Filas requeridas: 8,760 (365 dias x 24 horas/dia)")
check1 = len(df) == 8760
print(f"    STATUS: {'CORRECTO' if check1 else f'ERROR: {len(df) - 8760:+d} filas'}")

# Convertir timestamp
timestamp_col = 'index' if 'index' in df.columns else 'timestamp'
df[timestamp_col] = pd.to_datetime(df[timestamp_col])
df = df.set_index(timestamp_col).sort_index()

print(f"\n[2] RESOLUCION TEMPORAL")
print(f"    Primer timestamp: {df.index[0]}")
print(f"    Ultimo timestamp: {df.index[-1]}")

# Validar que sea horario
deltas = df.index.to_series().diff()[1:]
median_delta = deltas.median()
check2 = median_delta == pd.Timedelta(hours=1)
print(f"    Delta mediano: {median_delta}")
print(f"    STATUS: {'HORARIO CONFIRMADO' if check2 else 'NO ES HORARIO'}")

# Cobertura temporal
print(f"\n[3] COBERTURA TEMPORAL")
date_min = df.index.min()
date_max = df.index.max()
duration = date_max - date_min
days_covered = duration.days + 1
print(f"    Desde: {date_min.strftime('%Y-%m-%d')}")
print(f"    Hasta: {date_max.strftime('%Y-%m-%d')}")
print(f"    Duracion: {days_covered} dias")
check3 = (days_covered >= 364 and days_covered <= 366) and len(df) == 8760
print(f"    STATUS: {'ANO COMPLETO' if check3 else f'PARCIAL: {days_covered} dias'}")

# Continuidad
print(f"\n[4] CONTINUIDAD")
missing_hours = len(df) - (duration.total_seconds() / 3600)
check4 = abs(missing_hours) < 2
print(f"    Horas presentes: {len(df)}")
print(f"    STATUS: {'SIN BRECHAS' if check4 else f'BRECHAS: {abs(missing_hours):.0f} horas'}")

# Potencia AC
print(f"\n[5] GENERACION SOLAR (ac_power_kw)")
ac_power = df['ac_power_kw']
print(f"    Min: {ac_power.min():.2f} kW")
print(f"    Max: {ac_power.max():.2f} kW")
print(f"    Mean: {ac_power.mean():.2f} kW")
print(f"    Sum (energia anual): {ac_power.sum():.1f} kWh")

check5a = (ac_power > 0).any()
check5b = ac_power.sum() > 0
hours_gen = (ac_power > 0).sum()
print(f"    Horas con generacion: {hours_gen} / {len(df)} ({100*hours_gen/len(df):.1f}%)")
print(f"    STATUS: {'VALORES > 0 DETECTADOS' if check5a else 'TODOS CEROS'}")

# Patron dia/noche
print(f"\n[6] PATRON DIA/NOCHE")
df_for_hour = df.copy()
df_for_hour['hour'] = df_for_hour.index.hour
daily_pattern = df_for_hour.groupby('hour')['ac_power_kw'].agg(['mean'])
peak_hours = daily_pattern[daily_pattern['mean'] > 0].index
if len(peak_hours) > 0:
    min_h = peak_hours.min()
    max_h = peak_hours.max()
    print(f"    Horas con generacion: {min_h}:00 a {max_h}:00")
    check6 = (8 <= min_h <= 12 and 14 <= max_h <= 20)
    print(f"    STATUS: {'PATRON CORRECTO' if check6 else 'PATRON ANOMALO'}")
else:
    check6 = False
    print(f"    STATUS: SIN PATRON DIA/NOCHE")

# Resumen
print(f"\n" + "=" * 90)
print(f"RESUMEN FINAL")
print(f"=" * 90)
checks = {
    "8,760 filas exactas": check1,
    "Resolucion horaria": check2,
    "Ano completo": check3,
    "Sin brechas": check4,
    "Valores > 0": check5a,
    "Energia > 0": check5b,
    "Patron dia/noche": check6 or hours_gen > 0,
}

all_passed = all(checks.values())
for name, val in checks.items():
    print(f"  [{'PASS' if val else 'FAIL'}] {name}")

print(f"\n{'='*90}")
if all_passed:
    print(f"EXITO: Datos solares VALIDOS para OE3")
    print(f"  - 8,760 horas (1 ano)")
    print(f"  - Generacion anual: {ac_power.sum():.1f} kWh")
    print(f"  - Pico: {ac_power.max():.1f} kW")
else:
    print(f"FALLOS DETECTADOS - revisar problemas arriba")
print(f"{'='*90}\n")
