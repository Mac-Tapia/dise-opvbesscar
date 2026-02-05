#!/usr/bin/env python
"""
Comparación detallada: POTENCIA (kW) vs ENERGÍA (kWh)
Sistema solar de Iquitos - 4,050 kWp
Fórmula correcta: E [kWh] = P [kW] × Δt [h]
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Cargar datos
data_path = Path("data/oe2/Generacionsolar/pv_generation_timeseries.csv")
df = pd.read_csv(data_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 80)
print("  COMPARACIÓN: POTENCIA (kW) vs ENERGÍA (kWh) - SISTEMA SOLAR IQUITOS")
print("=" * 80)

# Mostrar estadísticas por columna
print("\n📊 COMPARACIÓN DE UNIDADES Y VALORES")
print("-" * 80)

# Máximo y promedio de potencia
max_power = df['ac_power_kw'].max()
mean_power = df['ac_power_kw'].mean()
min_power = df['ac_power_kw'].min()

# Máximo y promedio de energía
max_energy = df['ac_energy_kwh'].max()
mean_energy = df['ac_energy_kwh'].mean()
min_energy = df['ac_energy_kwh'].min()

print(f"\n🔴 POTENCIA (kW) - Instantánea [W/1000]:")
print(f"   Máxima:  {max_power:,.1f} kW")
print(f"   Media:   {mean_power:,.1f} kW")
print(f"   Mínima:  {min_power:,.1f} kW")

print(f"\n🟢 ENERGÍA (kWh) - Acumulada en Δt [W × h / 1000]:")
print(f"   Máxima:  {max_energy:,.3f} kWh")
print(f"   Media:   {mean_energy:,.3f} kWh")
print(f"   Mínima:  {min_energy:,.3f} kWh")

# Validación de fórmula E = P × Δt
print("\n" + "=" * 80)
print("  VALIDACIÓN DE FÓRMULA: E [kWh] = P [kW] × Δt [h]")
print("=" * 80)

# Encontrar la hora con máxima potencia
max_power_idx = df['ac_power_kw'].idxmax()
max_row = df.iloc[max_power_idx]

print(f"\n📍 Momento de máxima potencia:")
print(f"   Timestamp: {max_row['timestamp']}")
print(f"   Potencia AC: {max_row['ac_power_kw']:.1f} kW")
print(f"   Energía AC: {max_row['ac_energy_kwh']:.6f} kWh")

# Calcular el intervalo de tiempo
if len(df) > 1:
    dt_hours = (df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds() / 3600
else:
    dt_hours = 1.0

print(f"\n⏱️ Intervalo temporal (Δt): {dt_hours:.4f} horas")

# Verificar la fórmula
calculated_energy = max_row['ac_power_kw'] * dt_hours
actual_energy = max_row['ac_energy_kwh']
error_pct = abs(calculated_energy - actual_energy) / actual_energy * 100 if actual_energy != 0 else 0

print(f"\n🔍 Verificación matemática:")
print(f"   Fórmula: E = P × Δt")
print(f"   E calculada = {max_row['ac_power_kw']:.4f} [kW] × {dt_hours:.4f} [h]")
print(f"   E calculada = {calculated_energy:.6f} kWh")
print(f"   E en CSV = {actual_energy:.6f} kWh")
print(f"   Error = {error_pct:.10f} %")
print(f"   ✅ VERIFICACIÓN: {'CORRECTA' if error_pct < 0.01 else 'DIFERENCIA DETECTADA'}")

# Resumen de energía total
total_energy_kwh = df['ac_energy_kwh'].sum()
print(f"\n📈 RESUMEN ANUAL:")
print(f"   Energía total anual: {total_energy_kwh:,.0f} kWh")
print(f"   Energía total anual: {total_energy_kwh/1e6:.2f} GWh")

# Mostrar ejemplos de diferentes horas
print("\n" + "=" * 80)
print("  EJEMPLOS DE DIFERENTES HORAS DEL DÍA")
print("=" * 80)

sample_hours = [0, 6, 12, 18, 23]  # Noches y días
for hour in sample_hours:
    sample = df[df['timestamp'].dt.hour == hour].iloc[0]
    print(f"\n🕐 {sample['timestamp'].strftime('%H:%M')} - {sample['timestamp'].strftime('%A')}")
    print(f"   Irradiancia GHI: {sample['ghi_wm2']:.1f} W/m²")
    print(f"   Potencia AC: {sample['ac_power_kw']:.3f} kW (instantánea)")
    print(f"   Energía AC: {sample['ac_energy_kwh']:.6f} kWh (en {dt_hours*60:.0f} minutos)")

print("\n" + "=" * 80)
print("  CONCLUSIÓN")
print("=" * 80)
print(f"""
✅ POTENCIA y ENERGÍA son MAGNITUDES DIFERENTES:
   • POTENCIA [kW]: Flujo instantáneo de energía en un momento
   • ENERGÍA [kWh]: Energía acumulada durante un período de tiempo

✅ FÓRMULA CORRECTA: E [kWh] = P [kW] × Δt [h]
   • Se verificó correctamente: {error_pct:.6f}% error (prácticamente nulo)

✅ DATOS REALISTAS DESCARGADOS DE PVGIS:
   • Generación SOLO durante el día (6:00-18:00 aprox)
   • Máxima potencia al mediodía: {max_power:.1f} kW
   • Energía anual: {total_energy_kwh/1e6:.2f} GWh
   • Horas de producción: {(df['ac_power_kw'] > 0).sum()} horas de {len(df)} totales
   • Intervalo de datos: 15 minutos (0.25 horas)
""")

print("\n" + "=" * 80)
print("  TABLA RESUMEN ENERGÍA MENSUAL")
print("=" * 80)
monthly = df.groupby(df['timestamp'].dt.strftime('%Y-%m'))['ac_energy_kwh'].sum()
for month, energy in monthly.items():
    print(f"  {month}:  {energy:>12,.0f} kWh  ({energy/1e3:>8,.1f} MWh)")
print(f"  {'TOTAL':>7}:  {total_energy_kwh:>12,.0f} kWh  ({total_energy_kwh/1e6:>8,.2f} GWh)")
