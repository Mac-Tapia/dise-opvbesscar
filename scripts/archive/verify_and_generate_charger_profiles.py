"""
Script para generar y verificar perfiles individuales de chargers para CityLearn OE3.

CONTEXTO:
- CityLearn necesita 128 archivos CSV individuales (charger_simulation_001.csv ... 128.csv)
- Cada archivo: 8,760 filas × 1 columna (demand_kw)
- Fuente: chargers_hourly_profiles_annual.csv (8,760 × 128)

EJECUCIÓN:
    python -m scripts.verify_and_generate_charger_profiles

OUTPUT:
- data/processed/citylearn/.../buildings/Building_1/charger_simulation_XXX.csv (128 archivos)
- Reporte de validación con estadísticas por charger
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def verify_and_generate_charger_profiles(
    chargers_annual_csv: Path,
    output_building_dir: Path,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Generar 128 archivos CSV individuales para CityLearn desde perfiles anuales.

    Args:
        chargers_annual_csv: chargers_hourly_profiles_annual.csv (8,760 × 128)
        output_building_dir: buildings/Building_1/ directory
        overwrite: Sobrescribir archivos existentes

    Returns:
        Dict con estadísticas de generación
    """
    logger.info("[+] Verificando y generando perfiles individuales de chargers...")
    logger.info(f"    Input: {chargers_annual_csv}")
    logger.info(f"    Output dir: {output_building_dir}")

    if not chargers_annual_csv.exists():
        raise FileNotFoundError(
            f"Archivo de perfiles anuales no existe: {chargers_annual_csv}\n"
            f"Ejecutar primero: python -m src.iquitos_citylearn.oe2.convert_toma_profiles_to_hourly"
        )

    # Leer perfiles anuales
    df_annual = pd.read_csv(chargers_annual_csv)

    # Validaciones
    if df_annual.shape[0] != 8760:
        raise ValueError(
            f"Perfiles anuales deben tener 8,760 filas (horario anual), "
            f"encontradas {df_annual.shape[0]}"
        )

    if df_annual.shape[1] != 128:
        raise ValueError(
            f"Perfiles anuales deben tener 128 columnas (chargers), "
            f"encontradas {df_annual.shape[1]}"
        )

    logger.info(f"    ✓ Validación: {df_annual.shape[0]} filas × {df_annual.shape[1]} columnas")

    # Crear directorio de salida
    output_building_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    stats = {
        'total_chargers': 128,
        'motos_chargers': 112,
        'mototaxis_chargers': 16,
        'files_generated': 0,
        'files_skipped': 0,
        'total_annual_demand_kwh': df_annual.sum().sum(),
        'mean_hourly_demand_kw': df_annual.sum(axis=1).mean(),
        'peak_hourly_demand_kw': df_annual.sum(axis=1).max(),
        'chargers': {},
    }

    # Generar 128 archivos individuales
    for charger_idx in range(128):
        charger_col = df_annual.columns[charger_idx]
        csv_filename = f"charger_simulation_{charger_idx + 1:03d}.csv"
        csv_path = output_building_dir / csv_filename

        # Skip si existe y no overwrite
        if csv_path.exists() and not overwrite:
            stats['files_skipped'] += 1
            continue

        # Extraer perfil de este charger
        charger_demand = df_annual[charger_col]

        # Crear DataFrame con columna demand_kw
        df_charger = pd.DataFrame({
            'demand_kw': charger_demand.values
        })

        # Guardar CSV
        df_charger.to_csv(csv_path, index=False)
        generated_files.append(csv_path)
        stats['files_generated'] += 1

        # Estadísticas por charger
        stats['chargers'][charger_col] = {
            'file': csv_filename,
            'annual_kwh': float(charger_demand.sum()),
            'mean_kw': float(charger_demand.mean()),
            'max_kw': float(charger_demand.max()),
            'min_kw': float(charger_demand.min()),
            'utilization': float((charger_demand > 0).sum() / 8760),  # % de horas activas
        }

        if (charger_idx + 1) % 20 == 0:
            logger.info(f"    Generados {charger_idx + 1}/128 archivos...")

    logger.info(f"[OK] Generados {stats['files_generated']} archivos")
    logger.info(f"     Skipped: {stats['files_skipped']}")
    logger.info(f"     Total demand: {stats['total_annual_demand_kwh']:.1f} kWh/año")
    logger.info(f"     Mean hourly: {stats['mean_hourly_demand_kw']:.2f} kW")
    logger.info(f"     Peak hourly: {stats['peak_hourly_demand_kw']:.2f} kW")

    # Análisis por tipo de charger
    motos_demand = sum(
        v['annual_kwh'] for k, v in stats['chargers'].items()
        if 'MOTO_CH_' in k
    )
    mototaxis_demand = sum(
        v['annual_kwh'] for k, v in stats['chargers'].items()
        if 'MOTO_TAXI_CH_' in k
    )

    logger.info(f"\n[ANÁLISIS POR TIPO]")
    logger.info(f"  Motos (112 chargers): {motos_demand:.1f} kWh/año ({motos_demand/stats['total_annual_demand_kwh']*100:.1f}%)")
    logger.info(f"  Mototaxis (16 chargers): {mototaxis_demand:.1f} kWh/año ({mototaxis_demand/stats['total_annual_demand_kwh']*100:.1f}%)")

    # Top 5 chargers con mayor demanda
    top_chargers = sorted(
        stats['chargers'].items(),
        key=lambda x: x[1]['annual_kwh'],
        reverse=True
    )[:5]

    logger.info(f"\n[TOP 5 CHARGERS - MAYOR DEMANDA]")
    for charger_name, charger_stats in top_chargers:
        logger.info(
            f"  {charger_name}: {charger_stats['annual_kwh']:.1f} kWh/año "
            f"(utilization {charger_stats['utilization']*100:.1f}%)"
        )

    return stats


def main():
    """Entry point."""
    import sys
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    # Rutas por defecto
    project_root = Path(__file__).resolve().parents[1]
    chargers_annual = project_root / "data" / "interim" / "oe2" / "chargers" / "chargers_hourly_profiles_annual.csv"

    # Buscar dataset de CityLearn más reciente
    citylearn_datasets_dir = project_root / "data" / "processed" / "citylearn"
    if not citylearn_datasets_dir.exists():
        logger.error(f"Directorio CityLearn no existe: {citylearn_datasets_dir}")
        logger.error("Ejecutar primero: python -m scripts.run_oe3_build_dataset")
        return 1

    # Buscar carpeta más reciente con Building_1
    dataset_dirs = list(citylearn_datasets_dir.glob("*/buildings/Building_1"))
    if not dataset_dirs:
        logger.error("No se encontró ningún dataset con buildings/Building_1")
        logger.error("Ejecutar primero: python -m scripts.run_oe3_build_dataset")
        return 1

    # Usar el más reciente
    output_building_dir = sorted(dataset_dirs, key=lambda p: p.stat().st_mtime)[-1]
    logger.info(f"[DATASET DETECTADO]: {output_building_dir.parent.parent.name}")

    # Permitir override por argumentos
    if len(sys.argv) > 1:
        chargers_annual = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_building_dir = Path(sys.argv[2])

    try:
        stats = verify_and_generate_charger_profiles(
            chargers_annual_csv=chargers_annual,
            output_building_dir=output_building_dir,
            overwrite=True,
        )

        # Guardar reporte JSON
        report_path = output_building_dir / "chargers_generation_report.json"
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"[OK] Reporte guardado: {report_path}")

        return 0
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
