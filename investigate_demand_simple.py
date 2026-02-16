import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("INVESTIGACIÓN: ¿CUÁNTOS VEHÍCULOS REALMENTE LLEGAN AL SIMULADOR?")
print("="*80)
print()

try:
    # Cargar con parámetros robustos
    df = pd.read_csv(
        "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
        on_bad_lines='skip',  # Ignorar líneas malformadas
        engine='python'
    )
    
    print("[1] DATASET CARGADO EXITOSAMENTE")
    print(f"    Shape: {df.shape[0]} registros × {df.shape[1]} columnas")
    print(f"    Columnas: {list(df.columns)}")
    print()
    
    print("[2] ANÁLISIS DE DEMANDA:")
    print(f"    Total registros (demanda): {len(df)}")
    print(f"    Año tiene: 365 días")
    print(f"    Promedio vehículos/día: {len(df)/365:.1f}")
    print()
    
    # Buscar columna de tipo vehículo
    vehicle_type_col = None
    for col in df.columns:
        if 'type' in col.lower() or 'tipo' in col.lower() or 'vehicle' in col.lower():
            vehicle_type_col = col
            break
    
    if vehicle_type_col:
        print(f"[3] TIPOS DE VEHÍCULOS (columna: {vehicle_type_col}):")
        print(df[vehicle_type_col].value_counts())
        print()
    
    # Buscar columna de fecha
    date_col = None
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower() or 'timestamp' in col.lower():
            date_col = col
            break
    
    if date_col:
        print(f"[4] DISTRIBUCIÓN POR DÍA (primer mes):")
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        daily = df.groupby(df[date_col].dt.date).size()
        print(f"    Min: {daily.min()}, Max: {daily.max()}, Promedio: {daily.mean():.1f}")
        print()
        print("    Enero 2024 (primeros 10 días):")
        for i, (date, count) in enumerate(daily.head(10).items()):
            print(f"      {date}: {count} vehículos")
        print()
    
    print("[5] CONCLUSIÓN:")
    print(f"    Especificación: 270 motos + 39 mototaxis = 309 vehículos/día")
    print(f"    Dataset real: {len(df)/365:.1f} vehículos/día en promedio")
    
    if len(df)/365 < 100:
        print(f"    ❌ DATASET MUY PEQUEÑO - Solo {len(df)/365:.1f} disponibles vs 309 esperados")
        print(f"       Ratio: {(len(df)/365)/309*100:.1f}% de la demanda esperada")
    elif len(df)/365 < 309:
        print(f"    ⚠️  Dataset limitado - {len(df)/365:.1f} vs 309 esperados")
    else:
        print(f"    ✓ Dataset completo - Tiene suficientes vehículos")
    print()
    
except Exception as e:
    print(f"ERROR al procesar CSV: {e}")
    print()
    print("Intentando carregar con sep automático...")
    
    # Detectar separador
    with open("data/oe2/chargers/chargers_ev_ano_2024_v3.csv", 'r', encoding='utf-8', errors='ignore') as f:
        first_line = f.readline()
        if ',' in first_line:
            sep = ','
        elif ';' in first_line:
            sep = ';'
        elif '\t' in first_line:
            sep = '\t'
        else:
            sep = ','
    
    print(f"Separador detectado: '{sep}'")
    
    df = pd.read_csv(
        "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
        sep=sep,
        on_bad_lines='skip',
        engine='python'
    )
    
    print(f"Dataset cargado: {df.shape[0]} registros")
    print(f"Promedio/día: {len(df)/365:.1f} vehículos")
    print()

print("="*80)
