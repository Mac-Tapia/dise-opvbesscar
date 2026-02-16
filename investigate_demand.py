import pandas as pd
import json
from pathlib import Path

print("="*80)
print("INVESTIGACIÓN: ¿CUÁNTOS VEHÍCULOS REALMENTE LLEGAN AL SIMULADOR?")
print("="*80)
print()

# 1. Buscar dataset de demanda de vehículos
print("[1] BUSCANDO DATASETS DE DEMANDA...")
data_paths = [
    "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    "data/interim/oe2/chargers/individual_chargers.json",
    "data/interim/oe2/chargers/chargers_demand.csv",
]

for path in data_paths:
    p = Path(path)
    if p.exists():
        print(f"  ✓ {path} EXISTE")
    else:
        print(f"  ✗ {path} no existe")

print()

# 2. Cargar y analizar demanda de motos
print("[2] ANALIZANDO CSV DE DEMANDA...")
df = pd.read_csv("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
print(f"  Total de registros: {len(df)}")
print(f"  Columnas: {list(df.columns)}")
print()

# Asumir 1 episodio = 1 día
print("[3] DÍAS EN EL AÑO Y PROMEDIO...")
print(f"  Registros totales: {len(df)}")
print(f"  Dias en año: 365")
print(f"  Promedio registros/día: {len(df) / 365:.1f}")
print()

# 4. Ver primeras filas
print("[4] PRIMERAS 10 FILAS DEL DATASET:")
print(df.head(10).to_string())
print()

# 5. Distribución por hora (si existe columna hora)
if 'hour' in df.columns:
    print("[5] VEHÍCULOS LLEGANDO POR HORA:")
    hourly = df.groupby('hour').size()
    print(hourly)
    print()

# 6. Distribución por día de semana
if 'date' in df.columns or 'day_of_week' in df.columns:
    print("[6] VEHÍCULOS POR DÍA:")
    if 'date' in df.columns:
        daily = df.groupby(pd.to_datetime(df['date'])).size()
        print(f"  Min vehículos/día: {daily.min()}")
        print(f"  Max vehículos/día: {daily.max()}")
        print(f"  Promedio/día: {daily.mean():.1f}")
        print(f"  Std/día: {daily.std():.1f}")
        print()
        print("  Distribución por día (primeros 20):")
        print(daily.head(20))
    print()

# 7. Analizar si 270 motos al día es realista
print("[7] EXPECTATIVA vs REALIDAD:")
print(f"  Esperado en especificación: 270 motos + 39 mototaxis = 309 vehículos/día")
print(f"  Realidad en dataset: {len(df)/365:.1f} vehículos/día en promedio")
if len(df)/365 < 309:
    print(f"  ❌ DATASET INSUFICIENTE: Solo tiene {len(df)/365:.1f} vehículos/día, necesita 309")
else:
    print(f"  ✓ Dataset cumple con 309 vehículos/día")
print()

# 8. Analizar horarios de carga disponibles
print("[8] ANÁLISIS DE HORARIOS DE CARGA:")
if 'hour' in df.columns:
    min_hour = df['hour'].min()
    max_hour = df['hour'].max()
    print(f"  Horarios con demanda: {int(min_hour):02d}:00 a {int(max_hour):02d}:00")
    print(f"  Ventana de carga: {int(max_hour - min_hour)} horas")
else:
    print(f"  No hay columna 'hour' para analizar horarios")
print()

# 9. Información de chargers
print("[9] INFORMACIÓN DE CARGADORES:")
if 'charger_id' in df.columns:
    unique_chargers = df['charger_id'].nunique()
    print(f"  Cargadores únicos: {unique_chargers}")
    print(f"  Cargadores esperados: 19 (15 motos + 4 mototaxis)")
elif 'charger' in df.columns:
    unique_chargers = df['charger'].nunique()
    print(f"  Cargadores únicos: {unique_chargers}")
elif 'id_charger' in df.columns:
    unique_chargers = df['id_charger'].nunique()
    print(f"  Cargadores únicos: {unique_chargers}")
print()

print("[CONCLUSIÓN]")
print("Si 270+39 vehículos/día es el OBJETIVO pero el dataset solo tiene ~28/día,")
print("eso explica por qué los agentes cargan solo ~28 motos por episodio.")
print("="*80)
