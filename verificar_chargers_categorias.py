#!/usr/bin/env python3
"""Verificar categorización motos/mototaxis en chargers_real_hourly_2024.csv"""

import pandas as pd
from pathlib import Path

print("\n" + "="*80)
print("📊 VERIFICAR CATEGORIZACIÓN MOTOS/MOTOTAXIS")
print("="*80 + "\n")

csv_file = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")

if not csv_file.exists():
    print(f"❌ Archivo no encontrado: {csv_file}")
    exit(1)

# Cargar archivo
df = pd.read_csv(csv_file)

print(f"📁 Archivo: {csv_file.name}")
print(f"📊 Dimensiones: {df.shape[0]} filas × {df.shape[1]} columnas\n")

print("📋 Columnas:")
print("-" * 80)
for i, col in enumerate(df.columns):
    print(f"  [{i}] {col}")

print("\n" + "-" * 80)
print("🔍 ANÁLISIS DE ESTRUCTURA:")
print("-" * 80)

# Detectar motos vs mototaxis
n_cols = len(df.columns)
n_sockets = n_cols - 1  # Restar timestamp/índice si existe

print(f"\n  Total de columnas: {n_cols}")
print(f"  Esperadas para 128 sockets: 128 (sin timestamp)")
print(f"  O 129 (con timestamp/índice)\n")

# Motos: 28 × 4 = 112 sockets (índices 0-111)
# Mototaxis: 4 × 4 = 16 sockets (índices 112-127)

print("  ARQUITECTURA IQUITOS:")
print("    • 28 chargers MOTOS × 4 sockets = 112 sockets (índices 0-111)")
print("    • 4 chargers MOTOTAXIS × 4 sockets = 16 sockets (índices 112-127)")
print("    • Total: 128 sockets\n")

# Verificar si tiene estructura moto/mototaxi
has_moto_label = any('moto' in str(col).lower() for col in df.columns if 'moto' in str(col).lower() and 'taxi' not in str(col).lower())
has_mototaxi_label = any('mototaxi' in str(col).lower() for col in df.columns)
has_socket_label = any('socket' in str(col).lower() for col in df.columns)

print("  ETIQUETAS DETECTADAS:")
if has_moto_label:
    print("    ✅ Columnas con etiqueta 'moto'")
else:
    print("    ❌ NO hay columnas con etiqueta 'moto'")

if has_mototaxi_label:
    print("    ✅ Columnas con etiqueta 'mototaxi'")
else:
    print("    ❌ NO hay columnas con etiqueta 'mototaxi'")

if has_socket_label:
    print("    ✅ Columnas con etiqueta 'socket'")
else:
    print("    ❌ NO hay columnas con etiqueta 'socket'")

print("\n" + "-" * 80)
print("📊 PRIMERAS 5 FILAS:")
print("-" * 80)
print(df.head().to_string())

print("\n" + "-" * 80)
print("📈 ESTADÍSTICAS:")
print("-" * 80)
print(df.describe().to_string())

print("\n" + "="*80)
if n_sockets == 128 or n_cols == 128:
    print("✅ CORRECTO: 128 sockets confirmados")
else:
    print(f"⚠️  ADVERTENCIA: Se esperan 128 sockets, encontrados {n_sockets if n_sockets > 0 else n_cols}")
print("="*80 + "\n")
