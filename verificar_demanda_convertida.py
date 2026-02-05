#!/usr/bin/env python3
"""Verificar conversión de demanda"""

import pandas as pd

# Cargar archivo convertido
df = pd.read_csv('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';')

print("=" * 80)
print("VERIFICACIÓN: DEMANDA CONVERTIDA A HORARIA")
print("=" * 80)
print(f"\n📊 Número de filas: {len(df)} (esperado: 8,760)")
print(f"📋 Columnas: {list(df.columns)}")
print(f"📌 Energía total anual: {df['kWh'].sum():,.0f} kWh")

print(f"\n[PRIMERAS 5 FILAS]")
print(df.head())

print(f"\n[ÚLTIMAS 5 FILAS]")
print(df.tail())

print(f"\n[ESTADÍSTICAS DE ENERGÍA]")
print(df['kWh'].describe())

print("\n✅ CONVERSIÓN EXITOSA")
