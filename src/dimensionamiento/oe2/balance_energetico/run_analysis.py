#!/usr/bin/env python3
"""
Script de ejecución simple para Balance Energético.

Uso:
    python run_balance_analysis.py                    # Análisis completo
    python run_balance_analysis.py --metrics-only     # Solo métricas
    python run_balance_analysis.py --help             # Ver opciones
"""

import sys
from pathlib import Path

# Agregar ruta del proyecto
project_root = Path(__file__).parent.parent.parent.parent.parent  # src/.../balance_energetico -> project root
sys.path.insert(0, str(project_root))

from src.dimensionamiento.oe2.balance_energetico import (
    BalanceEnergeticoSystem,
    BalanceEnergeticoConfig,
    main,
)


def show_help():
    """Muestra ayuda."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         Balance Energético - Sistema Eléctrico Iquitos         ║
╚════════════════════════════════════════════════════════════════╝

DESCRIPCIÓN:
  Analiza el balance energético integral considerando:
  - Generación solar PV (4,050 kWp)
  - Almacenamiento BESS (940 kWh / 342 kW - exclusivo EV)
  - Demanda Mall (~100 kW)
  - Demanda Vehículos Eléctricos (38 sockets, 1,129 kWh/día 9h-22h)
  - Importación de red eléctrica

USO:
  python run_balance_analysis.py [OPCIÓN]

OPCIONES:
  (sin argumentos)      Análisis completo (7 gráficas + métricas + CSV)
  --metrics-only        Solo calcular métricas (sin gráficas)
  --quick               Prueba rápida (valida datos + resumen)
  --custom              Configuración personalizada
  --help, -h            Mostrar esta ayuda

EJEMPLOS:
  # Análisis completo (recomendado)
  python run_balance_analysis.py

  # Solo ver las métricas (más rápido)
  python run_balance_analysis.py --metrics-only

  # Prueba rápida de validación
  python run_balance_analysis.py --quick

SALIDA:
  Los resultados se guardan en: reports/balance_energetico/
  
  Gráficas:
    - 01_balance_5dias.png           (variabilidad solar)
    - 02_balance_diario.png          (365 días)
    - 03_distribucion_fuentes.png    (pie chart fuentes)
    - 04_cascada_energetica.png      (flujos energéticos)
    - 05_bess_soc.png                (estado carga)
    - 06_emisiones_co2.png           (impacto ambiental)
    - 07_utilizacion_pv.png          (análisis mensual)
  
  Datos:
    - balance_energetico_horario.csv (8,760 horas)

REQUISITOS:
  - Python 3.11+
  - pandas, numpy, matplotlib
  - data/processed/citylearn/iquitos_ev_mall/ (datasets CityLearn)

TIEMPO ESTIMADO:
  - Con gráficas:  3-5 minutos
  - Sin gráficas:  10-20 segundos

PROBLEMAS COMUNES:
  Q: "FileNotFoundError: data/processed/citylearn/..."
  A: Verificar que el directorio de datos existe en la ruta correcta
  
  Q: "Las gráficas no se generan"
  A: Instalar matplotlib: pip install matplotlib
  
  Q: "KeyError: columna no encontrada"
  A: Archivos CSV tienen columnas no esperadas. Ver README.md

════════════════════════════════════════════════════════════════
    """)


def run_full_analysis():
    """Ejecuta análisis completo."""
    print("\n" + "="*70)
    print("  BALANCE ENERGÉTICO - ANÁLISIS COMPLETO")
    print("="*70)
    
    try:
        system = main(
            data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
            output_dir=Path("reports/balance_energetico"),
            generate_plots=True
        )
        
        print("\n" + "="*70)
        print("  ✓ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("="*70)
        print("\nResultados guardados en: reports/balance_energetico/")
        print("\n7 Gráficas generadas:")
        print("  1. balance_5dias.png          - Variabilidad solar")
        print("  2. balance_diario.png         - Evolución anual")
        print("  3. distribucion_fuentes.png   - Cobertura por fuente")
        print("  4. cascada_energetica.png     - Flujos integrados")
        print("  5. bess_soc.png               - Estado de carga")
        print("  6. emisiones_co2.png          - Impacto ambiental")
        print("  7. utilizacion_pv.png         - Análisis mensual")
        print("\nCSV: balance_energetico_horario.csv (8,760 filas)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_metrics_only():
    """Ejecuta solo cálculo de métricas (sin gráficas)."""
    print("\n" + "="*70)
    print("  BALANCE ENERGÉTICO - SOLO MÉTRICAS")
    print("="*70)
    
    try:
        config = BalanceEnergeticoConfig(
            data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
        )
        
        system = BalanceEnergeticoSystem(config)
        
        print("\nCargando datasets...")
        if not system.load_all_datasets():
            return False
        
        print("Calculando balance...")
        system.calculate_balance()
        
        print("\nImprimiendo métricas...")
        system.print_summary()
        
        print("\n✓ Análisis de métricas completado")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_quick_test():
    """Ejecuta prueba rápida de validación."""
    print("\n" + "="*70)
    print("  BALANCE ENERGÉTICO - PRUEBA RÁPIDA")
    print("="*70)
    
    data_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    
    print("\nValidando archivos requeridos...")
    
    required = {
        "Solar PV": data_dir / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",
        "Chargers EV": data_dir / "chargers" / "chargers_real_hourly_2024.csv",
        "Demanda Mall": data_dir / "demandamallkwh" / "demandamallhorakwh.csv",
        "BESS Simulation": data_dir / "electrical_storage_simulation.csv",
    }
    
    all_ok = True
    for name, path in required.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {name:20} ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ {name:20} NO ENCONTRADO")
            all_ok = False
    
    if not all_ok:
        print("\n✗ Algunos archivos falta. Verifique la ruta data/processed/citylearn/iquitos_ev_mall/")
        return False
    
    print("\n✓ Todos los archivos validados")
    print("\nPara análisis completo, ejecute: python run_balance_analysis.py")
    
    return True


def run_custom_config():
    """Ejecuta análisis con configuración personalizada."""
    print("\n" + "="*70)
    print("  BALANCE ENERGÉTICO - CONFIGURACIÓN PERSONALIZADA")
    print("="*70)
    
    try:
        # Ejemplo: Escenario con diferente DoD
        print("\nConfigurando sistema con parámetros personalizados...")
        
        config = BalanceEnergeticoConfig(
            data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
            pv_capacity_kwp=4050.0,
            bess_capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
            bess_power_kw=342.0,       # v5.2: 342 kW
            dod=0.80,  # Profundidad de descarga 80%
            efficiency_roundtrip=0.95,  # Eficiencia 95%
        )
        
        system = BalanceEnergeticoSystem(config)
        
        if not system.load_all_datasets():
            return False
        
        system.calculate_balance()
        system.print_summary()
        
        print("\nOpcionales:")
        print("  - Modificar config.dod para cambiar profundidad de descarga")
        print("  - Modificar config.pv_capacity_kwp para escenarios diferentes")
        print("  - Modificar config.co2_intensity_kg_per_kwh para distintas intensidades")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main_cli():
    """Punto de entrada principal - interfaz línea de comandos."""
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ("--help", "-h", "help"):
            show_help()
            return 0
        
        elif arg == "--metrics-only":
            success = run_metrics_only()
            return 0 if success else 1
        
        elif arg == "--quick":
            success = run_quick_test()
            return 0 if success else 1
        
        elif arg == "--custom":
            success = run_custom_config()
            return 0 if success else 1
        
        else:
            print(f"✗ Opción no reconocida: {arg}")
            print("Use: python run_balance_analysis.py --help")
            return 1
    
    else:
        # Análisis completo (default)
        success = run_full_analysis()
        return 0 if success else 1


if __name__ == "__main__":
    exit_code = main_cli()
    sys.exit(exit_code)
