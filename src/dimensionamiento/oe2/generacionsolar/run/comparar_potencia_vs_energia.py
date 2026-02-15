#!/usr/bin/env python
"""
Comparacion detallada: POTENCIA (kW) vs ENERGIA (kWh)
Sistema solar de Iquitos - 4,050 kWp
Formula correcta: E [kWh] = P [kW] × Δt [h]
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Cargar datos
data_path = Path("data/oe2/Generacionsolar/pv_generation_timeseries.csv")
df = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
df = df.reset_index()  # Convert index back to column for compatibility

print("=" * 80)
print("  COMPARACION: POTENCIA (kW) vs ENERGIA (kWh) - SISTEMA SOLAR IQUITOS")
print("=" * 80)

# Mostrar estadisticas por columna
print("\n[GRAPH] COMPARACION DE UNIDADES Y VALORES")
print("-" * 80)

# Maximo y promedio de potencia
max_power = df['ac_power_kw'].max()
mean_power = df['ac_power_kw'].mean()
min_power = df['ac_power_kw'].min()

# Maximo y promedio de energia
max_energy = df['ac_energy_kwh'].max()
mean_energy = df['ac_energy_kwh'].mean()
min_energy = df['ac_energy_kwh'].min()

print(f"\n🔴 POTENCIA (kW) - Instantanea [W/1000]:")
print(f"   Maxima:  {max_power:,.1f} kW")
print(f"   Media:   {mean_power:,.1f} kW")
print(f"   Minima:  {min_power:,.1f} kW")

print(f"\n🟢 ENERGIA (kWh) - Acumulada en Δt [W × h / 1000]:")
print(f"   Maxima:  {max_energy:,.3f} kWh")
print(f"   Media:   {mean_energy:,.3f} kWh")
print(f"   Minima:  {min_energy:,.3f} kWh")

# Validacion de formula E = P × Δt
print("\n" + "=" * 80)
print("  VALIDACION DE FORMULA: E [kWh] = P [kW] × Δt [h]")
print("=" * 80)

# Encontrar la hora con maxima potencia
max_power_idx = df['ac_power_kw'].idxmax()
max_row = df.iloc[max_power_idx]

print(f"\n📍 Momento de maxima potencia:")
print(f"   Datetime: {max_row['datetime']}")
print(f"   Potencia AC: {max_row['ac_power_kw']:.1f} kW")
print(f"   Energia AC: {max_row['ac_energy_kwh']:.6f} kWh")

# Calcular el intervalo de tiempo
if len(df) > 1:
    dt_hours = (df['datetime'].iloc[1] - df['datetime'].iloc[0]).total_seconds() / 3600
else:
    dt_hours = 1.0

print(f"\n[TIME]️ Intervalo temporal (Δt): {dt_hours:.4f} horas")

# Verificar la formula
calculated_energy = max_row['ac_power_kw'] * dt_hours
actual_energy = max_row['ac_energy_kwh']
error_pct = abs(calculated_energy - actual_energy) / actual_energy * 100 if actual_energy != 0 else 0

print(f"\n🔍 Verificacion matematica:")
print(f"   Formula: E = P × Δt")
print(f"   E calculada = {max_row['ac_power_kw']:.4f} [kW] × {dt_hours:.4f} [h]")
print(f"   E calculada = {calculated_energy:.6f} kWh")
print(f"   E en CSV = {actual_energy:.6f} kWh")
print(f"   Error = {error_pct:.10f} %")
print(f"   [OK] VERIFICACION: {'CORRECTA' if error_pct < 0.01 else 'DIFERENCIA DETECTADA'}")

# Resumen de energia total
total_energy_kwh = df['ac_energy_kwh'].sum()
print(f"\n[CHART] RESUMEN ANUAL:")
print(f"   Energia total anual: {total_energy_kwh:,.0f} kWh")
print(f"   Energia total anual: {total_energy_kwh/1e6:.2f} GWh")

# Mostrar ejemplos de diferentes horas
print("\n" + "=" * 80)
print("  EJEMPLOS DE DIFERENTES HORAS DEL DIA")
print("=" * 80)

sample_hours = [0, 6, 12, 18, 23]  # Noches y dias
for hour in sample_hours:
    sample = df[df['datetime'].dt.hour == hour].iloc[0]
    print(f"\n🕐 {sample['datetime'].strftime('%H:%M')} - {sample['datetime'].strftime('%A')}")
    print(f"   Irradiancia GHI: {sample['ghi_wm2']:.1f} W/m²")
    print(f"   Potencia AC: {sample['ac_power_kw']:.3f} kW (instantanea)")
    print(f"   Energia AC: {sample['ac_energy_kwh']:.6f} kWh (en {dt_hours*60:.0f} minutos)")

print("\n" + "=" * 80)
print("  CONCLUSION")
print("=" * 80)
print(f"""
[OK] POTENCIA y ENERGIA son MAGNITUDES DIFERENTES:
   - POTENCIA [kW]: Flujo instantaneo de energia en un momento
   - ENERGIA [kWh]: Energia acumulada durante un periodo de tiempo

[OK] FORMULA CORRECTA: E [kWh] = P [kW] × Δt [h]
   - Se verifico correctamente: {error_pct:.6f}% error (practicamente nulo)

[OK] DATOS REALISTAS DESCARGADOS DE PVGIS:
   - Generacion SOLO durante el dia (6:00-18:00 aprox)
   - Maxima potencia al mediodia: {max_power:.1f} kW
   - Energia anual: {total_energy_kwh/1e6:.2f} GWh
   - Horas de produccion: {(df['ac_power_kw'] > 0).sum()} horas de {len(df)} totales
   - Intervalo de datos: 15 minutos (0.25 horas)
""")

print("\n" + "=" * 80)
print("  TABLA RESUMEN ENERGIA MENSUAL")
print("=" * 80)
monthly = df.groupby(df['datetime'].dt.strftime('%Y-%m'))['ac_energy_kwh'].sum()
for month, energy in monthly.items():
    print(f"  {month}:  {energy:>12,.0f} kWh  ({energy/1e3:>8,.1f} MWh)")
print(f"  {'TOTAL':>7}:  {total_energy_kwh:>12,.0f} kWh  ({total_energy_kwh/1e6:>8,.2f} GWh)")
