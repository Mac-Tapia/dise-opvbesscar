#!/usr/bin/env python3
"""
SCRIPT DE DEMOSTRACIÓN: Balance.py v5.8 con 4 Datasets y Auto-Actualización
============================================================================

Este script muestra:
1. Las 4 rutas de datasets que SIEMPRE se cargan
2. Cómo funciona la auto-detección de cambios
3. Cuándo se regeneran las gráficas

EJECUCIÓN:
    python demonstracion_4datasets_balance.py
"""

from pathlib import Path
import json
from datetime import datetime

def mostrar_rutas_datasets():
    """Mostrar las 4 rutas FIJAS de datasets que usa balance.py"""
    
    print("\n" + "="*80)
    print("BALANCE.PY v5.8: 4 DATASETS CON AUTO-ACTUALIZACIÓN")
    print("="*80)
    
    print("\n📂 RUTAS FIJAS (inmutables con Final[Path]):\n")
    
    datasets = {
        "1. PV GENERATION": {
            "ruta": "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv",
            "columna_key": "energia_kwh",
            "proposito": "Generación solar horaria (kWh)",
            "cantidad_anual": "8,292,514 kWh/año",
        },
        "2. EV DEMAND": {
            "ruta": "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
            "columna_key": "ev_energia_total_kwh",
            "proposito": "Demanda EV motos/mototaxis (38 sockets)",
            "cantidad_anual": "408,282 kWh/año",
        },
        "3. MALL DEMAND": {
            "ruta": "data/oe2/demandamallkwh/demandamallhorakwh.csv",
            "columna_key": "mall_demand_kwh",
            "proposito": "Demanda centro comercial",
            "cantidad_anual": "12,368,653 kWh/año",
        },
        "4. BESS OUTPUT": {
            "ruta": "data/oe2/bess/bess_ano_2024.csv",
            "columna_key": "grid_export_kwh",
            "proposito": "Salida simulación BESS (bess.py)",
            "cantidad_anual": "1,484,110 kWh exportados/año",
        },
    }
    
    for dataset_name, info in datasets.items():
        print(f"  {dataset_name}")
        print(f"    Ruta: {info['ruta']}")
        print(f"    Columna: {info['columna_key']}")
        print(f"    Propósito: {info['proposito']}")
        print(f"    Cantidad: {info['cantidad_anual']}")
        print()


def mostrar_auto_deteccion():
    """Mostrar cómo funciona la auto-detección de cambios"""
    
    print("="*80)
    print("🔄 SISTEMA DE AUTO-DETECCIÓN DE CAMBIOS")
    print("="*80)
    
    print("\nAlgoritmo: Hash MD5 + Metadata Tracking\n")
    
    print("1️⃣  AL INICIAR balance.py:")
    print("    detect_dataset_changes()")
    print("    ├─ Calcula hash MD5 de cada archivo actual")
    print("    ├─ Compara con hash guardado en data/.datasets_metadata.json")
    print("    └─ Determina: {'pv_changed': bool, 'ev_changed': bool, ...}\n")
    
    print("2️⃣  SI ALGÚN DATASET CAMBIÓ:")
    print("    ├─ Mensaje: ⚠️ CAMBIOS DETECTADOS EN DATASETS")
    print("    ├─ Lista qué cambió (PV, EV, MALL, o BESS)")
    print("    └─ AUTO-ACTION: Regenera gráficas automáticamente\n")
    
    print("3️⃣  SI NO HAY CAMBIOS:")
    print("    ├─ Mensaje: ✅ Datasets sin cambios")
    print("    └─ Usa datos cacheados (eficiencia)\n")
    
    print("4️⃣  METADATA GUARDADA EN:")
    print("    data/.datasets_metadata.json (archivo oculto)")
    print("    Contiene: {file_name, file_size, hash_md5, modified_timestamp}\n")


def mostrar_validaciones():
    """Mostrar validaciones críticas de balance.py"""
    
    print("="*80)
    print("✅ VALIDACIONES CRÍTICAS")
    print("="*80 + "\n")
    
    validaciones = [
        {
            "num": "1",
            "dataset": "PV GENERATION",
            "validacion": "Archivo existe en data/oe2/Generacionsolar/",
            "columna": "energia_kwh",
            "error_si_falla": "FileNotFoundError: pv_generation_citylearn2024.csv",
        },
        {
            "num": "2",
            "dataset": "EV DEMAND",
            "validacion": "Archivo existe en data/oe2/chargers/",
            "columna": "ev_energia_total_kwh",
            "error_si_falla": "FileNotFoundError: chargers_ev_ano_2024_v3.csv",
        },
        {
            "num": "3",
            "dataset": "MALL DEMAND",
            "validacion": "Archivo existe en data/oe2/demandamallkwh/",
            "columna": "mall_demand_kwh",
            "error_si_falla": "FileNotFoundError: demandamallhorakwh.csv",
        },
        {
            "num": "4",
            "dataset": "BESS OUTPUT",
            "validacion": "Archivo existe en data/oe2/bess/",
            "columna": "grid_export_kwh",
            "error_si_falla": "FileNotFoundError: bess_ano_2024.csv (requiere bess.py)",
        },
    ]
    
    for v in validaciones:
        print(f"[{v['num']}] {v['dataset']}")
        print(f"    ✓ Existencia: {v['validacion']}")
        print(f"    ✓ Columna: {v['columna']}")
        print(f"    ❌ Si falla: {v['error_si_falla']}")
        print()


def mostrar_cuando_se_regeneran():
    """Mostrar cuándo se regeneran las gráficas"""
    
    print("="*80)
    print("📊 CUÁNDO SE REGENERAN LAS GRÁFICAS")
    print("="*80 + "\n")
    
    print("ESCENARIO 1: Primera ejecución de balance.py")
    print("  └─ Estado: Todos los cambios detectados (metadata vacía)")
    print("  └─ Resultado: Genera 16 gráficas\n")
    
    print("ESCENARIO 2: Segunda ejecución sin cambios")
    print("  └─ Estado: ✅ Datasets sin cambios")
    print("  └─ Resultado: Usa gráficas previas (no regenera)\n")
    
    print("ESCENARIO 3: Reemplazo PV CSV con mismo nombre")
    print("  └─ Estado: ⚠️ PV GENERATION cambió (hash diferente)")
    print("  └─ Resultado: Regenera TODAS las 16 gráficas\n")
    
    print("ESCENARIO 4: Reemplazo EV CSV con mismo nombre")
    print("  └─ Estado: ⚠️ EV DEMAND cambió")
    print("  └─ Resultado: Regenera TODAS las 16 gráficas\n")
    
    print("ESCENARIO 5: Modifico demandamallhorakwh.csv")
    print("  └─ Estado: ⚠️ MALL DEMAND cambió")
    print("  └─ Resultado: Regenera TODAS las 16 gráficas\n")
    
    print("ESCENARIO 6: Ejecuto bess.py (genera nuevo bess_ano_2024.csv)")
    print("  └─ Estado: ⚠️ BESS OUTPUT cambió")
    print("  └─ Resultado: balance.py detecta y regenera gráficas\n")


def mostrar_comando_ejecucion():
    """Mostrar comandos de ejecución"""
    
    print("="*80)
    print("🚀 CÓMO EJECUTAR")
    print("="*80 + "\n")
    
    print("1. PRIMERO: Ejecutar bess.py para generar bess_ano_2024.csv")
    print("   $ python -m src.dimensionamiento.oe2.disenobess.bess\n")
    
    print("2. LUEGO: Ejecutar balance.py con 4 datasets")
    print("   $ python -c \"from src.dimensionamiento.oe2.balance_energetico.balance import main; main()\"\n")
    
    print("3. RESULTADO:")
    print("   ├─ Detecta cambios automáticamente")
    print("   ├─ Carga 4 datasets")
    print("   └─ Genera 16 gráficas en outputs/balance_energetico/\n")


def mostrar_flujo_completo():
    """Mostrar flujo completo de datos"""
    
    print("="*80)
    print("📈 FLUJO COMPLETO DE DATOS (v5.8)")
    print("="*80 + "\n")
    
    print("""
    ENTRADA DATOS FUENTE (3 archivos)
    ├─ pv_generation_citylearn2024.csv (8,292,514 kWh/año)
    ├─ chargers_ev_ano_2024_v3.csv (408,282 kWh/año)
    └─ demandamallhorakwh.csv (12,368,653 kWh/año)
             │
             ▼
    PROCESAMIENTO: BESS.PY
    ├─ Fase 1: BESS carga primero (6-9h)
    ├─ Fase 2: EV máxima prioridad (9h+)
    ├─ Fase 3: HOLDING (SOC≥99%)
    ├─ Fase 4: Peak shaving (PV<MALL>1900kW)
    ├─ Fase 5: EV prioridad descarga
    └─ Fase 6: IDLE (22h-6h)
             │
             ▼
    OUTPUT: bess_ano_2024.csv (8,760 horas × 35 columnas)
    ├─ Flujos: pv_to_ev, pv_to_bess, pv_to_mall, etc.
    ├─ BESS: soc_percent, carga, descarga, grid_export
    └─ Resultados: CO2 evitado, autoconsumo, peak shaving
             │
             ▼
    VISUALIZACIÓN: BALANCE.PY v5.8
    ├─ Carga 4 DATASETS (PV, EV, MALL, BESS)
    ├─ AUTO-DETECCIÓN: ¿Cambios en alguno?
    ├─ Si cambios → Regenera gráficas
    └─ Genera 16 PNG (energía, balance, CO2, etc.)
             │
             ▼
    OUTPUT FINAL: outputs/balance_energetico/
    ├─ 00_BALANCE_INTEGRADO_COMPLETO.png
    ├─ 00_INTEGRAL_todas_curvas.png - 6 FASES visualizadas
    ├─ 05_bess_soc.png - Estado BESS por hora
    ├─ 06_emisiones_co2.png - CO2 evitado
    ├─ 07_utilizacion_pv.png - Distribución solar
    └─ ... 10 gráficas más
    """)


def main():
    """Ejecutar demostración completa"""
    
    mostrar_rutas_datasets()
    mostrar_auto_deteccion()
    mostrar_validaciones()
    mostrar_cuando_se_regeneran()
    mostrar_comando_ejecucion()
    mostrar_flujo_completo()
    
    print("="*80)
    print("✅ CONCLUSIÓN: Balance.py v5.8 OPERA CON 4 DATASETS + AUTO-UPDATE")
    print("="*80)
    print("\nLas 4 rutas:")
    print("  1. ✅ PV GENERATION: pv_generation_citylearn2024.csv")
    print("  2. ✅ EV DEMAND: chargers_ev_ano_2024_v3.csv")
    print("  3. ✅ MALL DEMAND: demandamallhorakwh.csv")
    print("  4. ✅ BESS OUTPUT: bess_ano_2024.csv (generado por bess.py)")
    print("\nGarantías:")
    print("  ✓ Rutas FIJAS (Final[Path])")
    print("  ✓ Auto-detección de cambios (MD5 hash)")
    print("  ✓ Regeneración automática de gráficas")
    print("  ✓ Metadata tracking en data/.datasets_metadata.json")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
