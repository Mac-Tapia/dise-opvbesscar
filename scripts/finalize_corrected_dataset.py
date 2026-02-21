"""
Agregar columna datetime al dataset corregido y reemplazar el original
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data' / 'oe2' / 'bess'

print("=" * 100)
print("Agregar columna datetime al dataset corregido")
print("=" * 100)

# Cargar el dataset generado (sin datetime)
df = pd.read_csv(DATA_DIR / 'bess_ano_2024_CORREGIDO.csv')

# Crear columna datetime
datetime_index = pd.date_range(
    start='2024-01-01 00:00:00',
    periods=len(df),
    freq='h'
)

# Insertar datetime como primera columna
df.insert(0, 'datetime', datetime_index)

# Guardar
output_file = DATA_DIR / 'bess_ano_2024.csv'
df.to_csv(output_file, index=False)

print(f"\n✓ Dataset actualizado:")
print(f"  - Columnas: {len(df.columns)}")
print(f"  - Filas: {len(df)}")
print(f"  - Rango temporal: {df['datetime'].min()} → {df['datetime'].max()}")
print(f"  - Guardado: {output_file}")

# Validación rápida
conflicts = ((df['bess_energy_stored_hourly_kwh'] > 0) & (df['bess_energy_delivered_hourly_kwh'] > 0)).sum()
print(f"\n✅ Validación:")
print(f"  - Conflictos carga/descarga: {conflicts} / {len(df)}")
print(f"  - BESS cargado anual: {df['bess_energy_stored_hourly_kwh'].sum():,.0f} kWh")
print(f"  - BESS descargado anual: {df['bess_energy_delivered_hourly_kwh'].sum():,.0f} kWh")
print(f"  - Grid importado anual: {df['grid_import_kwh'].sum():,.0f} kWh")

print("\n" + "=" * 100)
