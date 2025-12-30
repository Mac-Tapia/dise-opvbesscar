#!/usr/bin/env python3
"""
Script para regenerar todas las gráficas de OE2 y OE3.

Este script ejecuta el pipeline completo y genera todas las visualizaciones.
Requiere Python 3.11 y dependencias instaladas.

Uso:
    python scripts/regenerate_all_graphics.py --config configs/default.yaml
    
    # O solo OE2:
    python scripts/regenerate_all_graphics.py --config configs/default.yaml --oe2-only
    
    # O solo OE3:
    python scripts/regenerate_all_graphics.py --config configs/default.yaml --oe3-only
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Ejecuta un comando y reporta el resultado."""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    print(f"Comando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"✓ {description} - COMPLETADO")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - ERROR (código {e.returncode})")
        return False
    except FileNotFoundError:
        print(f"✗ {description} - COMANDO NO ENCONTRADO")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Regenerar todas las gráficas de OE2 y OE3'
    )
    parser.add_argument(
        '--config', type=str, default='configs/default.yaml',
        help='Archivo de configuración YAML'
    )
    parser.add_argument(
        '--oe2-only', action='store_true',
        help='Solo regenerar gráficas de OE2'
    )
    parser.add_argument(
        '--oe3-only', action='store_true',
        help='Solo regenerar gráficas de OE3'
    )
    parser.add_argument(
        '--skip-simulation', action='store_true',
        help='Saltar simulación (solo gráficas de datos existentes)'
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    config_path = project_root / args.config
    
    if not config_path.exists():
        print(f"❌ Error: Archivo de configuración no encontrado: {config_path}")
        sys.exit(1)
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║  REGENERACIÓN DE GRÁFICAS OE2 Y OE3                          ║
║  Proyecto: Infraestructura de Carga EV - Mall de Iquitos    ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    success_count = 0
    total_count = 0
    
    # Determinar qué ejecutar
    run_oe2 = not args.oe3_only
    run_oe3 = not args.oe2_only
    
    # ========================================
    # OE2 - Dimensionamiento
    # ========================================
    if run_oe2:
        print("\n" + "="*60)
        print("FASE 1: OE2 - DIMENSIONAMIENTO")
        print("="*60)
        
        if not args.skip_simulation:
            # 1.1 Solar
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe2_solar", "--config", str(config_path)],
                "OE2 - Dimensionamiento Solar (PV)"
            ):
                success_count += 1
            
            # 1.2 Chargers
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe2_chargers", "--config", str(config_path)],
                "OE2 - Dimensionamiento Cargadores EV"
            ):
                success_count += 1
            
            # 1.3 BESS
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe2_bess", "--config", str(config_path)],
                "OE2 - Dimensionamiento BESS"
            ):
                success_count += 1
        
        # 1.4 Gráficas Solar
        total_count += 1
        if run_command(
            [sys.executable, "-m", "scripts.run_oe2_solar_plots", "--config", str(config_path)],
            "OE2 - Gráficas Solar"
        ):
            success_count += 1
        
        # 1.5 Reporte completo con gráficas
        total_count += 1
        if run_command(
            [sys.executable, "-m", "scripts.generate_oe2_report"],
            "OE2 - Reporte completo con visualizaciones"
        ):
            success_count += 1
    
    # ========================================
    # OE3 - Simulación y Agentes
    # ========================================
    if run_oe3:
        print("\n" + "="*60)
        print("FASE 2: OE3 - SIMULACIÓN Y AGENTES")
        print("="*60)
        
        if not args.skip_simulation:
            # 2.1 Build dataset
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe3_build_dataset", "--config", str(config_path)],
                "OE3 - Construcción dataset CityLearn"
            ):
                success_count += 1
            
            # 2.2 Simulate
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe3_simulate", "--config", str(config_path)],
                "OE3 - Simulación y entrenamiento agentes"
            ):
                success_count += 1
            
            # 2.3 CO2 table
            total_count += 1
            if run_command(
                [sys.executable, "-m", "scripts.run_oe3_co2_table", "--config", str(config_path)],
                "OE3 - Tabla comparativa CO₂"
            ):
                success_count += 1
        
        # 2.4 Gráficas entrenamiento
        total_count += 1
        if run_command(
            [sys.executable, "-m", "scripts.plot_oe3_training", "--config", str(config_path)],
            "OE3 - Gráficas de entrenamiento"
        ):
            success_count += 1
    
    # ========================================
    # Resumen
    # ========================================
    print("\n" + "="*60)
    print("RESUMEN DE EJECUCIÓN")
    print("="*60)
    print(f"Tareas completadas: {success_count}/{total_count}")
    print(f"Tasa de éxito: {100*success_count/total_count:.1f}%")
    
    if success_count == total_count:
        print("\n✓ TODAS LAS GRÁFICAS REGENERADAS EXITOSAMENTE")
        print("\nGráficas generadas en:")
        if run_oe2:
            print("  - reports/oe2/")
            print("  - reports/oe2/solar_plots/")
        if run_oe3:
            print("  - analyses/oe3/training/")
            print("  - reports/oe3/")
        return 0
    else:
        print("\n⚠ ALGUNAS TAREAS FALLARON")
        print(f"Revisa los mensajes de error arriba")
        return 1


if __name__ == "__main__":
    sys.exit(main())
