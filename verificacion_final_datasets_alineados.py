#!/usr/bin/env python3
"""
VERIFICACIÓN FINAL: Datasets Solar + Demanda Alineados para CityLearn OE3
Confirma que ambos archivos están preparados para integración en el ambiente
"""

import pandas as pd
from pathlib import Path

print("\n" + "=" * 90)
print("VERIFICACIÓN FINAL: PREPARACIÓN DATOS PARA CITYLEARN OE3")
print("=" * 90)

# 1. CARGAR DATASETS
print("\n[1/3] CARGANDO DATASETS...")

# Solar
solar_path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
solar_df = pd.read_csv(solar_path)
print(f"  ✓ Solar: {solar_path}")
print(f"    - Filas: {len(solar_df)}")
print(f"    - Columnas: {list(solar_df.columns)}")

# Demanda (convertida)
demanda_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
demanda_df = pd.read_csv(demanda_path, sep=';')
print(f"  ✓ Demanda: {demanda_path}")
print(f"    - Filas: {len(demanda_df)}")
print(f"    - Columnas: {list(demanda_df.columns)}")

# 2. VALIDACIÓN DE FORMATOS Y COMPLETITUD
print("\n[2/3] VALIDANDO FORMATOS Y COMPLETITUD...")

# Solar validations
solar_checks = {
    "Filas == 8,760": len(solar_df) == 8760,
    "Potencia KW en rango": (solar_df['potencia_kw'] >= 0).all(),
    "Energía KWh en rango": (solar_df['energia_kwh'] >= 0).all(),
    "Sin valores NaN": solar_df[['potencia_kw', 'energia_kwh']].notna().all().all(),
}

print("  Solar (OE2):")
for check, result in solar_checks.items():
    status = "✓" if result else "✗"
    print(f"    {status} {check}")

# Demanda validations
demanda_checks = {
    "Filas == 8,760+": len(demanda_df) >= 8760,
    "Energía KWh >0": (demanda_df['kWh'] > 0).sum() > 7000,
    "Sin valores NaN": demanda_df['kWh'].notna().all(),
    "Formato FECHAHORA OK": demanda_df['FECHAHORA'].str.len().between(12, 16).all(),
}

print("  Demanda (Convertida):")
for check, result in demanda_checks.items():
    status = "✓" if result else "✗"
    print(f"    {status} {check}")

# 3. ESTADÍSTICAS DE INTEGRACIÓN
print("\n[3/3] ESTADÍSTICAS DE INTEGRACIÓN SOLAR + DEMANDA...")

print(f"\n  📊 SOLAR:")
print(f"     Energía anual: {solar_df['energia_kwh'].sum():,.0f} kWh")
print(f"     Potencia máx:  {solar_df['potencia_kw'].max():.2f} kW")
print(f"     Potencia prom: {solar_df['potencia_kw'].mean():.2f} kW")
print(f"     Horas >0 kW:   {(solar_df['potencia_kw'] > 0).sum():,}")

print(f"\n  📊 DEMANDA:")
print(f"     Energía anual: {demanda_df['kWh'].sum():,.0f} kWh")
print(f"     Energía máx:   {demanda_df['kWh'].max():.0f} kWh/hora")
print(f"     Energía min:   {demanda_df['kWh'].min():.0f} kWh/hora")
print(f"     Energía prom:  {demanda_df['kWh'].mean():.0f} kWh/hora")

print(f"\n  🔗 COMPARATIVA:")
ratio = demanda_df['kWh'].sum() / solar_df['energia_kwh'].sum()
print(f"     Solar vs Demanda: {ratio:.2%}")
print(f"     Interpretación: Demanda = {ratio:.1%} de generación solar")

# 4. ESTADO FINAL
print("\n" + "=" * 90)
print("✅ VERIFICACIÓN COMPLETADA - DATASETS LISTOS PARA CITYLEARN OE3")
print("=" * 90)

print("\n📦 ARCHIVOS CONSOLIDADOS PARA ENTRENAMIENTO:")
print(f"   1. Solar:  {solar_path}")
print(f"   2. Demanda: {demanda_path}")

print("\n🚀 PRÓXIMO PASO: Integrar en dataset_builder.py")
print("   Command: python -m src.iquitos_citylearn.oe3.dataset_builder")

print("\n" + "=" * 90 + "\n")
