"""
PRESENTACION DE DATASETS DE ENTRADA A BESS.PY
Muestra información detallada de los 3 datasets que carga bess.py
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

root = Path(__file__).parent
oe2_dir = root / "data" / "oe2"

# Rutas de datos (EXACTAS como las usa bess.py)
pv_path = oe2_dir / "Generacionsolar" / "pv_generation_citylearn2024.csv"
ev_path = oe2_dir / "chargers" / "chargers_ev_ano_2024_v3.csv"
mall_path = oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv"

print("\n" + "="*100)
print("DATASETS DE ENTRADA A BESS.PY - VERIFICACION")
print("="*100)

# ============================================================================
# DATASET 1: PV GENERATION
# ============================================================================
print("\n[1] GENERACION SOLAR (PV) - PV_GENERATION_CITYLEARN2024.CSV")
print("-"*100)
print(f"Ruta: {pv_path}")
print(f"Existe: {pv_path.exists()}")

if pv_path.exists():
    df_pv = pd.read_csv(pv_path)
    print(f"\n  ESTRUCTURA:")
    print(f"    Filas: {len(df_pv):,}")
    print(f"    Columnas: {len(df_pv.columns)}")
    print(f"    Tamaño archivo: {pv_path.stat().st_size / 1024:.1f} KB")
    
    print(f"\n  COLUMNAS:")
    for i, col in enumerate(df_pv.columns, 1):
        dtype = str(df_pv[col].dtype)
        non_null = df_pv[col].notna().sum()
        print(f"    {i}. {col:.<40} ({dtype:>10}, {non_null:>5} no-nulos)")
    
    print(f"\n  DATOS (Primeras 3 filas):")
    print(df_pv.head(3).to_string())
    
    print(f"\n  ESTADISTICAS:")
    # Buscar columna numérica de generación PV
    numeric_cols = df_pv.select_dtypes(include=['number']).columns.tolist()
    for col in numeric_cols:
        print(f"    {col}:")
        print(f"      Min:     {df_pv[col].min():>15,.2f}")
        print(f"      Max:     {df_pv[col].max():>15,.2f}")
        print(f"      Promedio:{df_pv[col].mean():>15,.2f}")
        print(f"      Total:   {df_pv[col].sum():>15,.0f}")
else:
    print(f"  ❌ ARCHIVO NO ENCONTRADO")

# ============================================================================
# DATASET 2: EV DEMAND
# ============================================================================
print("\n[2] DEMANDA EV (MOTOS/MOTOTAXIS) - CHARGERS_EV_ANO_2024_V3.CSV")
print("-"*100)
print(f"Ruta: {ev_path}")
print(f"Existe: {ev_path.exists()}")

if ev_path.exists():
    df_ev = pd.read_csv(ev_path)
    print(f"\n  ESTRUCTURA:")
    print(f"    Filas: {len(df_ev):,}")
    print(f"    Columnas: {len(df_ev.columns)}")
    print(f"    Tamaño archivo: {ev_path.stat().st_size / 1024:.1f} KB")
    
    print(f"\n  COLUMNAS:")
    for i, col in enumerate(df_ev.columns[:15], 1):  # Mostrar primeras 15
        dtype = str(df_ev[col].dtype)
        non_null = df_ev[col].notna().sum()
        print(f"    {i}. {col:.<40} ({dtype:>10}, {non_null:>5} no-nulos)")
    
    if len(df_ev.columns) > 15:
        print(f"    ... ({len(df_ev.columns) - 15} columnas más)")
    
    print(f"\n  DATOS (Primeras 3 filas):")
    print(df_ev.iloc[:3, :8].to_string())
    
    print(f"\n  ESTADISTICAS (si contiene energía):")
    numeric_cols = df_ev.select_dtypes(include=['number']).columns.tolist()
    if 'ev_energia_total_kwh' in df_ev.columns:
        col = 'ev_energia_total_kwh'
        print(f"    {col}:")
        print(f"      Min:     {df_ev[col].min():>15,.2f} kWh")
        print(f"      Max:     {df_ev[col].max():>15,.2f} kWh")
        print(f"      Promedio:{df_ev[col].mean():>15,.2f} kWh")
        print(f"      Total:   {df_ev[col].sum():>15,.0f} kWh/año")
    else:
        print(f"    Columnas numéricas: {numeric_cols[:5]}")
else:
    print(f"  ❌ ARCHIVO NO ENCONTRADO")

# ============================================================================
# DATASET 3: MALL DEMAND
# ============================================================================
print("\n[3] DEMANDA MALL (CENTRO COMERCIAL) - DEMANDAMALLHORAKWH.CSV")
print("-"*100)
print(f"Ruta: {mall_path}")
print(f"Existe: {mall_path.exists()}")

if mall_path.exists():
    df_mall = pd.read_csv(mall_path)
    print(f"\n  ESTRUCTURA:")
    print(f"    Filas: {len(df_mall):,}")
    print(f"    Columnas: {len(df_mall.columns)}")
    print(f"    Tamaño archivo: {mall_path.stat().st_size / 1024:.1f} KB")
    
    print(f"\n  COLUMNAS:")
    for i, col in enumerate(df_mall.columns, 1):
        dtype = str(df_mall[col].dtype)
        non_null = df_mall[col].notna().sum()
        print(f"    {i}. {col:.<40} ({dtype:>10}, {non_null:>5} no-nulos)")
    
    print(f"\n  DATOS (Primeras 3 filas):")
    print(df_mall.head(3).to_string())
    
    print(f"\n  ESTADISTICAS:")
    numeric_cols = df_mall.select_dtypes(include=['number']).columns.tolist()
    for col in numeric_cols:
        print(f"    {col}:")
        print(f"      Min:     {df_mall[col].min():>15,.2f}")
        print(f"      Max:     {df_mall[col].max():>15,.2f}")
        print(f"      Promedio:{df_mall[col].mean():>15,.2f}")
        print(f"      Total:   {df_mall[col].sum():>15,.0f} kWh/año")
else:
    print(f"  ❌ ARCHIVO NO ENCONTRADO")

# ============================================================================
# RESUMEN CONSOLIDADO
# ============================================================================
print("\n" + "="*100)
print("RESUMEN CONSOLIDADO")
print("="*100)

if pv_path.exists() and ev_path.exists() and mall_path.exists():
    df_pv = pd.read_csv(pv_path)
    df_ev = pd.read_csv(ev_path)
    df_mall = pd.read_csv(mall_path)
    
    # Buscar columna numérica de PV
    pv_col = None
    for col in ['pv_kwh', 'energia_kwh', 'ac_energy_kwh', 'potencia_kw']:
        if col in df_pv.columns:
            pv_col = col
            break
    if pv_col is None:
        pv_col = df_pv.select_dtypes(include=['number']).columns[0]
    
    # Buscar columna de EV
    ev_col = None
    for col in ['ev_energia_total_kwh', 'totalenergy_kwh', 'ev_kwh']:
        if col in df_ev.columns:
            ev_col = col
            break
    if ev_col is None:
        ev_col = df_ev.select_dtypes(include=['number']).columns[0]
    
    # Buscar columna de MALL
    mall_col = None
    for col in ['mall_kwh', 'mall_demand_kwh', 'demanda_mall_kwh']:
        if col in df_mall.columns:
            mall_col = col
            break
    if mall_col is None:
        mall_col = df_mall.select_dtypes(include=['number']).columns[0]
    
    pv_total = df_pv[pv_col].sum()
    ev_total = df_ev[ev_col].sum() if ev_col else 0
    mall_total = df_mall[mall_col].sum() if mall_col else 0
    
    print(f"\n  COMPATIBILIDAD:")
    print(f"    PV filas:   {len(df_pv):>5} (8,760 requerido para año completo: {'✅' if len(df_pv) == 8760 else '❌'})")
    print(f"    EV filas:   {len(df_ev):>5} (8,760 requerido para año completo: {'✅' if len(df_ev) == 8760 else '❌'})")
    print(f"    MALL filas: {len(df_mall):>5} (8,760 requerido para año completo: {'✅' if len(df_mall) == 8760 else '❌'})")
    
    print(f"\n  ENERGIAS ANUALES:")
    print(f"    PV:   {pv_total:>15,.0f} kWh/año (columna: {pv_col})")
    print(f"    EV:   {ev_total:>15,.0f} kWh/año (columna: {ev_col})")
    print(f"    MALL: {mall_total:>15,.0f} kWh/año (columna: {mall_col})")
    print(f"    TOTAL:{pv_total + ev_total + mall_total:>15,.0f} kWh/año")
    
    print(f"\n  PROPORCION:")
    total = pv_total + ev_total + mall_total
    print(f"    PV:   {pv_total/total*100:>6.1f}% (fuente renovable)")
    print(f"    EV:   {ev_total/total*100:>6.1f}% (demanda motos/mototaxis)")
    print(f"    MALL: {mall_total/total*100:>6.1f}% (demanda centro comercial)")

print("\n" + "="*100)
print("FIN DE PRESENTACION")
print("="*100 + "\n")
