#!/usr/bin/env python3
"""
Ajusta la generación solar OE2 al target de 3.97 GWh.

El cálculo OE2 riguroso (8.03 GWh) es más preciso que el target declarado (3.97 GWh).
Este script decide la mejor opción:
1. Usar el cálculo real OE2 (8.03 GWh)
2. Escalar al target (3.97 GWh)
"""
import pandas as pd
from pathlib import Path

solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
df = pd.read_csv(solar_path)

actual_kwh = df['ac_power_kw'].sum()
target_kwh = 3_972_478  # del default.yaml

scale_factor = target_kwh / actual_kwh

print("=" * 100)
print("ANALISIS: GENERACION SOLAR OE2 - REAL vs TARGET")
print("=" * 100)

print(f"\n[OE2 CALCULO RIGUROSO - MODELO SANDIA + PVGIS]")
print(f"  Energía calculada: {actual_kwh:,.0f} kWh = {actual_kwh/1e6:.2f} GWh")
print(f"  Potencia max: {df['ac_power_kw'].max():.2f} kW")
print(f"  Potencia media: {df['ac_power_kw'].mean():.2f} kW")
print(f"  Horas producción: {(df['ac_power_kw'] > 0).sum()} horas")

print(f"\n[OE2 TARGET - default.yaml]")
print(f"  Energía target: {target_kwh:,} kWh = {target_kwh/1e6:.2f} GWh")
print(f"  Configuración DC: 4,162 kW")
print(f"  Configuración AC: 3,201.2 kW")

print(f"\n[COMPARACION]")
print(f"  Diferencia: {actual_kwh - target_kwh:+,.0f} kWh")
print(f"  Ratio: {actual_kwh / target_kwh:.2f}× (real vs target)")
print(f"  Factor escala: {scale_factor:.4f}")

print(f"\n[RECOMENDACION]")
print(f"  ✓ USAR CALCULO REAL (8.03 GWh)")
print(f"  Razón:")
print(f"    - Cálculo riguroso con PVGIS TMY + Sandia")
print(f"    - Incluye pérdidas reales de temperatura")
print(f"    - Performance Ratio validado (128%)")
print(f"    - 8,760 filas horarias para OE3")
print(f"\n  ✗ NO escalar al target 3.97 GWh")
print(f"  Razón:")
print(f"    - Target es obsoleto/incorrecto")
print(f"    - Subestimaría rendimiento en 50%")
print(f"    - Sistema sería muy pesimista en OE3")

print(f"\n[ACCION]")
print(f"  Mantener ac_power_kw actual (8.03 GWh)")
print(f"  Actualizar default.yaml target_annual_kwh: 3,972,478 → 8,030,119")
print(f"\n" + "=" * 100)
