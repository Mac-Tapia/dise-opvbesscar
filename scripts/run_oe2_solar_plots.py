#!/usr/bin/env python
"""
Script para generar gráficas avanzadas del sistema fotovoltaico.

Ejecutar después de run_oe2_solar.py para generar todas las visualizaciones.

Uso:
    python scripts/run_oe2_solar_plots.py --config configs/default.yaml
"""

import argparse
from pathlib import Path
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iquitos_citylearn.oe2.solar_plots import generate_all_solar_plots


def main():
    parser = argparse.ArgumentParser(
        description='Generar gráficas avanzadas del sistema FV'
    )
    parser.add_argument(
        '--config', type=str, default='configs/default.yaml',
        help='Archivo de configuración YAML'
    )
    parser.add_argument(
        '--data-dir', type=str, default=None,
        help='Directorio con datos de entrada (override config)'
    )
    parser.add_argument(
        '--out-dir', type=str, default=None,
        help='Directorio de salida para gráficas (override config)'
    )
    
    args = parser.parse_args()
    
    # Directorio base del proyecto
    project_root = Path(__file__).parent.parent
    
    # Directorios por defecto
    data_dir = Path(args.data_dir) if args.data_dir else project_root / 'data' / 'interim' / 'oe2' / 'solar'
    out_dir = Path(args.out_dir) if args.out_dir else project_root / 'reports' / 'oe2' / 'solar_plots'
    
    # Verificar que existen los datos
    if not (data_dir / 'solar_results.json').exists():
        print(f"❌ Error: No se encontró solar_results.json en {data_dir}")
        print("   Ejecute primero: python scripts/run_oe2_solar.py --config configs/default.yaml")
        sys.exit(1)
    
    if not (data_dir / 'pv_generation_timeseries.csv').exists():
        print(f"❌ Error: No se encontró pv_generation_timeseries.csv en {data_dir}")
        sys.exit(1)
    
    # Generar gráficas
    generate_all_solar_plots(data_dir, out_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
