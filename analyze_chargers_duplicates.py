#!/usr/bin/env python3
"""
ANÁLISIS DE DUPLICADOS: ¿Son válidos o artefactos?
====================================================
"""

import pandas as pd
from pathlib import Path

# Cargar backup (original con duplicados)
df = pd.read_csv(
    "data/oe2/chargers/chargers_ev_ano_2024_v3.BACKUP_ANTES_LIMPIEZA.csv",
    index_col=0,
    parse_dates=[0]
)

print("\n" + "="*90)
print("🔬 ANÁLISIS DE DUPLICADOS EN CHARGERS DATASET")
print("="*90)

# Obtener filas duplicadas
dup_mask = df.duplicated(keep=False)
dup_df = df[dup_mask]

print(f"\n📊 Estadísticas:")
print(f"   Total filas: {len(df):,}")
print(f"   Filas duplicadas: {dup_mask.sum():,}")
print(f"   Fechas únicas duplicadas: {dup_df.index.nunique():,}")

# Analizar por fecha
print(f"\n🕐 Análisis temporal de duplicados:")
dup_dates = dup_df.index.unique()
print(f"   Rango: {dup_dates.min()} → {dup_dates.max()}")

# ¿Dónde se concentran los duplicados?
date_counts = dup_df.index.value_counts().sort_index()
print(f"\n📈 Fechas con duplicados (frecuencia):")
for date in date_counts.head(10).index:
    count = date_counts[date]
    print(f"   {date}: {count} filas idénticas")

# Examinar un ejemplo duplicado
print(f"\n💡 Ejemplo de filas duplicadas (misma hora):")
sample_dup_date = date_counts.index[0]
sample_rows = df.loc[[sample_dup_date]]
print(f"   Hora: {sample_dup_date}")
print(f"   Cantidad de filas con esa timestamp: {len(sample_rows)}")

# Mostrar primeras columnas
print(f"\n📋 Primeras columnas de filas duplicadas:")
print(sample_rows.iloc[:, :8].to_string())

# ¿Son valores cero los duplicados?
print(f"\n🔍 Análisis de valores en duplicados:")
sample_row = sample_rows.iloc[0]

# Columnas de potencia
power_cols = [col for col in df.columns if '_charging_power_kw' in col]
power_vals = sample_row[power_cols]
power_nonzero = (power_vals > 0).sum()
print(f"   Socket charging power (non-zero): {power_nonzero}/{len(power_cols)}")

# Columnas activas
active_cols = [col for col in df.columns if '_active' in col]
active_vals = sample_row[active_cols]
active_nonzero = (active_vals > 0).sum()
print(f"   Socket active (active): {active_nonzero}/{len(active_cols)}")

# Energía
energy = sample_row.get("ev_energia_total_kwh", 0)
print(f"   Total energy: {energy:.2f} kWh")

# Conclusión
print(f"\n" + "="*90)
print("📝 CONCLUSIÓN:")
print("="*90)

print(f"\nLos {dup_mask.sum()} duplicados son:")
if power_nonzero == 0:
    print("   ✓ VÁLIDOS: Son horas con CERO CARGA (sin vehículos)")
    print("   ✓ Esperado: En horas nocturnas o cerradas del mall")
    print("   ✓ RECOMENDACIÓN: Eliminar (no aportan información a agentes RL)")
else:
    print("   ❌ INVÁLIDOS: Son duplicados de datos reales")
    print("   ❌ RECOMENDACIÓN: Investigar causa en chargers.py")

print("\n" + "="*90 + "\n")
