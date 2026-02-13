#!/usr/bin/env python3
"""Verificación de integridad de datos guardados en CSV"""

import pandas as pd
from pathlib import Path
import json

print("\n" + "="*70)
print("VERIFICACIÓN DE DATOS GUARDADOS EN CSV")
print("="*70)

# Verificar datos de cargadores
charger_dir = Path('data/interim/oe3/chargers')
charger_files = list(charger_dir.glob('charger_*.csv'))
print(f"\n✅ Se encontraron {len(charger_files)} archivos CSV de cargadores")

# Leer un archivo de ejemplo
if charger_files:
    df_charger = pd.read_csv(charger_files[0])
    print(f"\n📊 Estructura del archivo charger_000.csv:")
    print(f"   - Filas (timesteps): {len(df_charger)}")
    print(f"   - Columnas: {list(df_charger.columns)}")
    print(f"   - Tamaño: {charger_files[0].stat().st_size / (1024) :.2f} KB")

    print(f"\n📋 Primeras 3 filas:")
    print(df_charger.head(3).to_string())

    print(f"\n📊 Últimas 3 filas:")
    print(df_charger.tail(3).to_string())

    # Verificar integridad de datos
    print(f"\n✓ Verificación de datos faltantes (NaN):")
    null_counts = df_charger.isnull().sum()
    if null_counts.sum() == 0:
        print("   ✅ No hay datos faltantes")
    else:
        print(null_counts)

    # Estadísticas de SOC
    print(f"\n⚡ Estadísticas de Estado de Carga (SOC):")
    print(f"   - SOC mínimo: {df_charger['current_soc'].min():.4f}")
    print(f"   - SOC máximo: {df_charger['current_soc'].max():.4f}")
    print(f"   - SOC promedio: {df_charger['current_soc'].mean():.4f}")

    # Validar cantidad de registros (8760 = 1 año de horas)
    if len(df_charger) == 8760:
        print(f"   ✅ Cantidad de registros correcta (8760 horas = 1 año)")
    else:
        print(f"   ⚠️  ADVERTENCIA: Se esperaban 8760 registros, se encontraron {len(df_charger)}")

# Verificar schema.json
schema_file = Path('data/interim/oe3/schema.json')
if schema_file.exists():
    print(f"\n✅ Schema archivo: {schema_file.name} ({schema_file.stat().st_size} bytes)")
    with open(schema_file) as f:
        schema = json.load(f)
    print(f"   - Timesteps en episodio: {schema.get('episode_time_steps', 'N/A')}")
    print(f"   - Minutos por timestep: {schema.get('time_step_minutes', 'N/A')}")
    print(f"   - Cantidad de edificios: {len(schema.get('buildings', []))}")

    # Verificar cargadores en schema
    building = schema.get('buildings', [{}])[0]
    chargers = building.get('controllable_charging', [])
    print(f"   - Cantidad de cargadores en schema: {len(chargers)}")

# Contar archivos totales
total_charger_files = len(list(charger_dir.glob('charger_*.csv')))
print(f"\n✅ RESUMEN FINAL:")
print(f"   - Archivos CSV de cargadores: {total_charger_files}")
print(f"   - Archivo de schema: 1")
print(f"   - Total de archivos generados: {total_charger_files + 1}")

print(f"\n📁 Ubicación de datos: data/interim/oe3/")
print("\n" + "="*70)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*70)
