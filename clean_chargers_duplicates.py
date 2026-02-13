#!/usr/bin/env python3
"""
LIMPIEZA DE DUPLICADOS: Chargers Dataset v5.2
==============================================

Script para eliminar filas completamente duplicadas del dataset.
Mantiene el dataset íntegro (8,760 horas = 365 días × 24 horas)
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

# Rutas
ORIGINAL_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
BACKUP_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.BACKUP_ANTES_LIMPIEZA.csv")
CLEANED_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")  # Sobrescribir

print("\n" + "="*90)
print("🧹 LIMPIEZA DE DUPLICADOS: Chargers Dataset v5.2")
print("="*90)

# Cargar dataset original
print(f"\n📂 Cargando dataset: {ORIGINAL_PATH}")
df = pd.read_csv(ORIGINAL_PATH, index_col=0, parse_dates=[0])
print(f"✓ Dimensiones originales: {df.shape[0]:,} filas × {df.shape[1]:,} columnas")

# Hacer backup DEL ORIGINAL (con filas duplicadas)
print(f"\n💾 Creando backup del dataset original...")
shutil.copy(ORIGINAL_PATH, BACKUP_PATH)
print(f"✓ Backup: {BACKUP_PATH}")

# Detectar duplicados
print(f"\n🔍 Analizando duplicados...")
dup_mask = df.duplicated(keep=False)  # Marca TODAS las duplicadas (no solo las segundas)
dup_count_total = dup_mask.sum()
dup_unique = df.duplicated().sum()  # Solo las segundas y posteriores

print(f"✓ Total filas que son duplicadas: {dup_count_total}")
print(f"✓ Total filas a eliminar: {dup_unique}")

if dup_count_total > 0:
    # Mostrar ejemplo
    dup_df = df[dup_mask].head(3)
    print(f"\n📋 Ejemplo de filas duplicadas:")
    print(dup_df.iloc[:, :5].to_string())

# Eliminar duplicados (mantiene la primera ocurrencia)
print(f"\n🧹 Eliminando duplicados...")
df_cleaned = df.drop_duplicates(keep='first')
print(f"✓ Dimensiones después de limpieza: {df_cleaned.shape[0]:,} filas × {df_cleaned.shape[1]:,} columnas")

# Verificar integridad después de limpieza
print(f"\n✅ Verificación post-limpieza:")
print(f"   Filas: {df_cleaned.shape[0]:,}")
print(f"   Columnas: {df_cleaned.shape[1]:,}")
print(f"   Período: {df_cleaned.index.min()} → {df_cleaned.index.max()}")
print(f"   Año: {df_cleaned.index.year.unique()}")
print(f"   Duplicados restantes: {df_cleaned.duplicated().sum()}")

# Validar que no falta energía
energy_original = df["ev_energia_total_kwh"].sum()
energy_cleaned = df_cleaned["ev_energia_total_kwh"].sum()
print(f"\n   Energía original:  {energy_original:>12,.0f} kWh")
print(f"   Energía limpia:    {energy_cleaned:>12,.0f} kWh")
print(f"   Pérdida: {((energy_original - energy_cleaned) / energy_original * 100):.4f}%")

# Guardar dataset limpio (sobrescribir el original)
print(f"\n💾 Guardando dataset limpio...")
df_cleaned.to_csv(CLEANED_PATH)
print(f"✓ Guardado: {CLEANED_PATH}")

# Resumen
print(f"\n" + "="*90)
print("✅ LIMPIEZA COMPLETADA")
print("="*90)
print(f"\nResumen:")
print(f"   ❌ Duplicados eliminados: {dup_unique:,} filas")
print(f"   ✅ Dataset limpio: {df_cleaned.shape[0]:,} filas")
print(f"   ✅ Columnas intactas: {df_cleaned.shape[1]:,}")
print(f"   ✅ Backup guardado: {BACKUP_PATH}")
print(f"   ✅ Dataset limpio actualizado: {CLEANED_PATH}")

print(f"\n💡 Si necesitas revertir, copia de {BACKUP_PATH} de vuelta al original")
print("="*90 + "\n")
