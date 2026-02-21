#!/usr/bin/env python3
"""
PRESENTACIÓN DE DATASETS DE ENTRADA - BALANCE.PY v5.7
======================================================

balance.py es un módulo de VISUALIZACIÓN que recibe datos precalculados.
Este script muestra TODOS los datasets de entrada que usa.

Datos precalculados provienen de: bess.py (dimensionamiento OE2)
Visualización generada por: balance.py (16 gráficas)

Flujo de Datos:
  bess.py
    ├─ Carga: PV, EV, MALL (3 datasets primarios)
    ├─ Simula: BESS con 6 fases
    └─ Genera: bess_ano_2024.csv (dataset completo con lógica simulada)
    
  balance.py
    ├─ Carga: bess_ano_2024.csv (UNICO dataset precalculado)
    ├─ Procesa: Columnas para visualización
    └─ Genera: 16 gráficas de balance energético
"""

from pathlib import Path
import pandas as pd
import json
from datetime import datetime

def main():
    print("\n" + "="*90)
    print("DATASETS DE ENTRADA - BALANCE.PY v5.7")
    print("="*90)
    
    project_root = Path(__file__).parent
    
    # ========================================================================
    # DATASET INMEDIATO (usado por balance.py)
    # ========================================================================
    print("\n[1] DATASET INMEDIATO - Cargado por balance.py")
    print("-"*90)
    
    bess_csv_path = project_root / "data/oe2/bess/bess_ano_2024.csv"
    
    print(f"\n📊 BESS Balance Energético (Principal)")
    print(f"   Archivo: {bess_csv_path.name}")
    print(f"   Ruta: {bess_csv_path.relative_to(project_root)}")
    
    if bess_csv_path.exists():
        df_bess = pd.read_csv(bess_csv_path)
        file_size_mb = bess_csv_path.stat().st_size / (1024*1024)
        
        print(f"   Estado: ✅ EXISTE")
        print(f"   Tamaño: {file_size_mb:.2f} MB")
        print(f"   Registros: {len(df_bess):,} (1 año horario = 8,760 horas)")
        print(f"   Columnas: {df_bess.shape[1]}")
        
        print(f"\n   DIMENSIONES ENERGÉTICAS (desde archivo):")
        
        if 'pv_kwh' in df_bess.columns:
            pv_total = df_bess['pv_kwh'].sum()
            print(f"     • PV Generación: {pv_total:,.0f} kWh/año ({pv_total/1e6:.2f} GWh/año)")
        
        if 'ev_kwh' in df_bess.columns:
            ev_total = df_bess['ev_kwh'].sum()
            print(f"     • EV Demanda: {ev_total:,.0f} kWh/año ({ev_total/1e3:.1f} MWh/año)")
        
        if 'mall_kwh' in df_bess.columns:
            mall_total = df_bess['mall_kwh'].sum()
            mall_max = df_bess['mall_kwh'].max()
            print(f"     • MALL Demanda: {mall_total:,.0f} kWh/año ({mall_total/1e6:.2f} GWh/año)")
            print(f"       ├─ Pico máximo: {mall_max:,.1f} kW")
            print(f"       ├─ Promedio: {df_bess['mall_kwh'].mean():,.1f} kW")
            print(f"       └─ Mínimo: {df_bess['mall_kwh'].min():,.1f} kW")
        
        if 'bess_to_ev_kwh' in df_bess.columns:
            bess_ev = df_bess['bess_to_ev_kwh'].sum()
            print(f"     • BESS → EV: {bess_ev:,.0f} kWh/año")
        
        if 'bess_to_mall_kwh' in df_bess.columns:
            bess_mall = df_bess['bess_to_mall_kwh'].sum()
            print(f"     • BESS → MALL (Peak Shaving): {bess_mall:,.0f} kWh/año")
        
        if 'grid_import_kwh' in df_bess.columns:
            grid_import = df_bess['grid_import_kwh'].sum()
            print(f"     • Grid Importación: {grid_import:,.0f} kWh/año ({grid_import/1e6:.2f} GWh/año)")
        
        if 'grid_export_kwh' in df_bess.columns:
            grid_export = df_bess['grid_export_kwh'].sum()
            print(f"     • Grid Exportación: {grid_export:,.0f} kWh/año ({grid_export/1e6:.2f} GWh/año)")
        
        if 'soc_percent' in df_bess.columns:
            soc_mean = df_bess['soc_percent'].mean()
            print(f"     • BESS SOC Promedio: {soc_mean:.1f}%")
        
        print(f"\n   COLUMNAS PRINCIPALES ({df_bess.shape[1]} totales):")
        
        # Columnas de entrada
        entrada_cols = [col for col in df_bess.columns if 'pv' in col.lower() or 'ev' in col.lower() or 'mall' in col.lower()]
        if entrada_cols:
            print(f"     [ENTRADA - Datos Medidos/Supuestos]")
            for col in sorted(entrada_cols)[:5]:
                print(f"       • {col}")
        
        # Columnas de flujos
        flujo_cols = [col for col in df_bess.columns if 'to_' in col.lower() or 'pv_to' in col.lower()]
        if flujo_cols:
            print(f"     [FLUJOS - Distribución de Energía]")
            for col in sorted(flujo_cols)[:8]:
                print(f"       • {col}")
        
        # Columnas de estado
        estado_cols = [col for col in df_bess.columns if 'soc' in col.lower() or 'mode' in col.lower()]
        if estado_cols:
            print(f"     [ESTADO - BESS y Sistema]")
            for col in sorted(estado_cols):
                print(f"       • {col}")
        
        # Columnas de beneficios
        beneficio_cols = [col for col in df_bess.columns if 'co2' in col.lower() or 'cost' in col.lower() or 'avoided' in col.lower()]
        if beneficio_cols:
            print(f"     [BENEFICIOS - CO₂ y Ahorros]")
            for col in sorted(beneficio_cols)[:5]:
                print(f"       • {col}")
    else:
        print(f"   Estado: ❌ NO EXISTE")
        print(f"   → Ejecuta primero: python -m src.dimensionamiento.oe2.disenobess.bess")
    
    # ========================================================================
    # DATASETS FUENTE (usados por bess.py para CREAR el dataset anterior)
    # ========================================================================
    print("\n\n[2] DATASETS FUENTE - Usados por bess.py (que alimentan balance.py)")
    print("-"*90)
    
    # PV
    pv_csv_path = project_root / "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv"
    print(f"\n☀️  PV GENERATION (Solar)")
    print(f"   Archivo: {pv_csv_path.name}")
    print(f"   Ruta: {pv_csv_path.relative_to(project_root)}")
    print(f"   Propósito: Generación horaria de PV (4,050 kWp)")
    print(f"   Período: 1 año natural (2024) - 8,760 horas")
    
    if pv_csv_path.exists():
        df_pv = pd.read_csv(pv_csv_path)
        print(f"   Estado: ✅ EXISTE")
        print(f"   Registros: {len(df_pv):,} horas")
        print(f"   Columnas: {', '.join(df_pv.columns[:5].tolist())}...")
        if 'energia_kwh' in df_pv.columns:
            pv_total = df_pv['energia_kwh'].sum()
            print(f"   Energía: {pv_total:,.0f} kWh/año ({pv_total/1e6:.2f} GWh/año)")
    else:
        print(f"   Estado: ❌ NO EXISTE")
    
    # EV
    ev_csv_path = project_root / "data/oe2/chargers/chargers_ev_ano_2024_v3.csv"
    print(f"\n🔋 EV DEMAND (Motos + Mototaxis)")
    print(f"   Archivo: {ev_csv_path.name}")
    print(f"   Ruta: {ev_csv_path.relative_to(project_root)}")
    print(f"   Propósito: Demanda horaria de 38 sockets de carga")
    print(f"   Composición: 30 sockets motos + 8 sockets mototaxis")
    print(f"   Período: 1 año natural (2024) - 8,760 horas")
    print(f"   Tecnología: Modo 3 @ 7.4 kW por socket (230V, 32A monofásico)")
    
    if ev_csv_path.exists():
        df_ev = pd.read_csv(ev_csv_path)
        print(f"   Estado: ✅ EXISTE")
        print(f"   Registros: {len(df_ev):,} horas")
        print(f"   Columnas: {df_ev.shape[1]} (38 sockets × múltiples parámetros)")
        if 'ev_energia_total_kwh' in df_ev.columns:
            ev_total = df_ev['ev_energia_total_kwh'].sum()
            print(f"   Energía Total: {ev_total:,.0f} kWh/año ({ev_total/1e3:.1f} MWh/año)")
    else:
        print(f"   Estado: ❌ NO EXISTE")
    
    # MALL
    mall_csv_path = project_root / "data/oe2/demandamallkwh/demandamallhorakwh.csv"
    print(f"\n🏬 MALL DEMAND (Centro Comercial)")
    print(f"   Archivo: {mall_csv_path.name}")
    print(f"   Ruta: {mall_csv_path.relative_to(project_root)}")
    print(f"   Propósito: Demanda horaria del centro comercial (Iquitos)")
    print(f"   Período: 1 año natural (2024) - 8,760 horas")
    print(f"   Descripción: Perfil de carga real del complejo comercial")
    
    if mall_csv_path.exists():
        df_mall = pd.read_csv(mall_csv_path)
        print(f"   Estado: ✅ EXISTE")
        print(f"   Registros: {len(df_mall):,} horas")
        print(f"   Columnas: {', '.join(df_mall.columns[:5].tolist())}...")
        
        if 'datetime' in df_mall.columns:
            df_mall['datetime'] = pd.to_datetime(df_mall['datetime'])
            df_mall_2024 = df_mall[df_mall['datetime'].dt.year == 2024]
            print(f"   Registros (2024): {len(df_mall_2024):,} horas")
        
        if 'mall_demand_kwh' in df_mall.columns:
            mall_total = df_mall['mall_demand_kwh'].sum()
            mall_max = df_mall['mall_demand_kwh'].max()
            mall_min = df_mall['mall_demand_kwh'].min()
            mall_mean = df_mall['mall_demand_kwh'].mean()
            print(f"   Energía Total: {mall_total:,.0f} kWh/año ({mall_total/1e6:.2f} GWh/año)")
            print(f"   Pico Máximo: {mall_max:,.1f} kW")
            print(f"   Mínimo: {mall_min:,.1f} kW")
            print(f"   Promedio: {mall_mean:,.1f} kW")
    else:
        print(f"   Estado: ❌ NO EXISTE")
    
    # ========================================================================
    # ARQUITECTURA DE DATOS
    # ========================================================================
    print("\n\n[3] ARQUITECTURA DE DATOS - Cómo los datos fluyen")
    print("-"*90)
    
    flujo = """
    DATASETS FUENTE (3)
    ├─ PV Solar (pv_generation_citylearn2024.csv)
    │   └─ 8,292,514 kWh/año
    ├─ EV Demand (chargers_ev_ano_2024_v3.csv)
    │   └─ 408,282 kWh/año (38 sockets)
    └─ MALL Demand (demandamallhorakwh.csv)
        └─ 12,368,653 kWh/año
    
    ↓ (bess.py: Dimensionamiento OE2)
    
    PROCESAMIENTO - 6 FASES BESS
    ├─ FASE 1 (6h-9h): BESS carga primero, EV no opera
    ├─ FASE 2 (9h+, SOC<99%): EV máxima prioridad + BESS en paralelo
    ├─ FASE 3 (9h+, SOC≥99%): HOLDING - BESS mantiene 100%
    ├─ FASE 4 (PV<MALL, >1900kW): Peak shaving descarga
    ├─ FASE 5 (EV_deficit>0): EV prioridad descarga
    └─ FASE 6 (22h-6h): IDLE/Reposo a 20% SOC
    
    ↓ (genera bess_ano_2024.csv)
    
    DATASET INTEGRADO (1)
    └─ bess_ano_2024.csv: 8,760 horas × 33 columnas
       ├─ Generación y Demanda (entrada)
       ├─ Flujos Energéticos (PV→EV, PV→BESS, BESS→MALL, etc)
       ├─ Estado BESS (SOC, carga, descarga)
       ├─ Grid (import/export)
       └─ Beneficios (CO₂ evitado, ahorros)
    
    ↓ (balance.py: Visualización)
    
    GRÁFICAS DE BALANCE (16 total)
    ├─ 00_BALANCE_INTEGRADO_COMPLETO.png
    ├─ 00.1_EXPORTACION_Y_PEAK_SHAVING.png
    ├─ 01_balance_5dias.png
    ├─ 02_balance_diario.png
    ├─ 03_distribucion_fuentes.png
    ├─ 04_cascada_energetica.png
    ├─ 05_bess_soc.png
    ├─ 06_emisiones_co2.png
    ├─ 07_utilizacion_pv.png
    └─ ... (más gráficas)
    """
    
    print(flujo)
    
    # ========================================================================
    # CONFIGURACIÓN FIJA DE DATASETS (desde datasets_config.py)
    # ========================================================================
    print("\n[4] VERIFICACIÓN - Rutas FIJAS de datasets (datasets_config.py)")
    print("-"*90)
    
    try:
        from src.config.datasets_config import (
            PV_GENERATION_DATA_PATH,
            EV_DEMAND_DATA_PATH,
            MALL_DEMAND_DATA_PATH,
            validate_dataset_paths,
            detect_dataset_changes
        )
        
        print("\n✅ Configuración FIJAS detectada (src/config/datasets_config.py)")
        
        validation = validate_dataset_paths()
        changes = detect_dataset_changes()
        
        print(f"\n   PV Path:")
        print(f"     Ruta: {PV_GENERATION_DATA_PATH}")
        print(f"     Existe: {'✅' if PV_GENERATION_DATA_PATH.exists() else '❌'}")
        print(f"     Cambios: {'⚠️ ACTUALIZADO' if changes['pv_changed'] else '✅ Sin cambios'}")
        
        print(f"\n   EV Path:")
        print(f"     Ruta: {EV_DEMAND_DATA_PATH}")
        print(f"     Existe: {'✅' if EV_DEMAND_DATA_PATH.exists() else '❌'}")
        print(f"     Cambios: {'⚠️ ACTUALIZADO' if changes['ev_changed'] else '✅ Sin cambios'}")
        
        print(f"\n   MALL Path:")
        print(f"     Ruta: {MALL_DEMAND_DATA_PATH}")
        print(f"     Existe: {'✅' if MALL_DEMAND_DATA_PATH.exists() else '❌'}")
        print(f"     Cambios: {'⚠️ ACTUALIZADO' if changes['mall_changed'] else '✅ Sin cambios'}")
        
    except ImportError:
        print("\n⚠️  datasets_config.py no encontrado (configure_python_environment primero)")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("\n\n" + "="*90)
    print("RESUMEN - Datasets para balance.py")
    print("="*90)
    
    print("""
    DATASET INMEDIATO (usado por balance.py):
      ✓ bess_ano_2024.csv
        └─ Contiene TODA la lógica simulada de BESS (6 fases)
        └─ Alimentado por: bess.py

    DATASETS FUENTE (usados por bess.py para CREAR el anterior):
      ✓ pv_generation_citylearn2024.csv (8,292,514 kWh/año)
      ✓ chargers_ev_ano_2024_v3.csv (408,282 kWh/año, 38 sockets)
      ✓ demandamallhorakwh.csv (12,368,653 kWh/año)

    FLUJO:
      [3 Datasets Fuente]
            ↓
        bess.py (Dimensionamiento BESS 6 fases)
            ↓
      [1 Dataset Integrado: bess_ano_2024.csv]
            ↓
      balance.py (Visualización 16 gráficas)
            ↓
      [GRÁFICAS]

    NOTA: balance.py está optimizado para recibir datos precalculados.
          NO regenera la lógica BESS, solo visualiza dataset existente.
    """)
    
    print("="*90)
    print()

if __name__ == '__main__':
    main()
