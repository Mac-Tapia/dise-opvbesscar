#!/usr/bin/env python3
"""Fix charger profiles: add missing MOTO_CH_001 column"""
import pandas as pd
from pathlib import Path

charger_file = Path("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv")
df = pd.read_csv(charger_file, index_col=0, encoding='utf-8')

print(f"Shape antes: {df.shape}")
print(f"Primeras columnas: {df.columns[:3].tolist()}")

# Crear nueva columna MOTO_CH_001 con valores de MOTO_CH_002
moto_ch_001_values = df['MOTO_CH_002'].copy()

# Insertar al principio
df.insert(0, 'MOTO_CH_001', moto_ch_001_values)

print(f"Shape después: {df.shape}")
print(f"Primeras columnas: {df.columns[:3].tolist()}")
print(f"Últimas columnas: {df.columns[-3:].tolist()}")

# Guardar
df.to_csv(charger_file, encoding='utf-8')
print(f"\n✅ Archivo actualizado: {charger_file}")
print(f"   {df.shape[0]} filas × {df.shape[1]} columnas (esperado: 8760 × 128)")
