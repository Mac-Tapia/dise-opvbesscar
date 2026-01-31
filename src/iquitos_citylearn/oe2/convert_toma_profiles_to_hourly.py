"""
Convertir perfiles de tomas individuales de 30min a 1h para OE3.

PROBLEMA IDENTIFICADO:
- Los perfiles en data/interim/oe2/chargers/toma_profiles/ tienen 17,520 filas (30min)
- OE3 necesita 8,760 filas (1h horario)
- dataset_builder.py espera chargers_hourly_profiles_annual.csv (8,760 × 128)

SOLUCIÓN:
- Leer los 128 archivos toma_XXX_30min.csv
- Resamplear de 30min → 1h (agregación por suma de energía kWh)
- Generar chargers_hourly_profiles_annual.csv (8,760 × 128)
- Usar columnas power_kw (demanda instantánea) para cada toma

SALIDA:
- data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv
- Formato: 8,760 filas × 128 columnas (MOTO_CH_001 ... MOTO_TAXI_CH_128)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


def convert_toma_profiles_30min_to_hourly(
    toma_profiles_dir: Path,
    output_path: Path,
    n_tomas: int = 128,
) -> pd.DataFrame:
    """
    Convertir perfiles individuales de tomas de 30min a 1h.

    Args:
        toma_profiles_dir: Directorio con toma_XXX_moto_30min.csv y toma_XXX_mototaxi_30min.csv
        output_path: Ruta de salida para chargers_hourly_profiles_annual.csv
        n_tomas: Número total de tomas (default 128)

    Returns:
        DataFrame con shape (8760, 128)
    """
    logger.info("[+] Convirtiendo perfiles de tomas 30min → 1h...")
    logger.info(f"    Input dir: {toma_profiles_dir}")
    logger.info(f"    Output: {output_path}")

    if not toma_profiles_dir.exists():
        raise FileNotFoundError(f"Directorio de perfiles no existe: {toma_profiles_dir}")

    hourly_profiles: Dict[str, pd.Series] = {}

    for toma_id in range(n_tomas):
        # Detectar tipo de toma (motos: 0-111, mototaxis: 112-127)
        if toma_id < 112:
            toma_type = "moto"
            charger_name = f"MOTO_CH_{toma_id + 1:03d}"
        else:
            toma_type = "mototaxi"
            # Ajustar índice para mototaxis (112 → 001)
            mototaxi_index = toma_id - 112 + 1
            charger_name = f"MOTO_TAXI_CH_{mototaxi_index:03d}"

        # Leer archivo de toma
        toma_file = toma_profiles_dir / f"toma_{toma_id:03d}_{toma_type}_30min.csv"

        if not toma_file.exists():
            logger.warning(f"    [SKIP] {toma_file.name} no existe")
            # Crear perfil de ceros si no existe
            hourly_profiles[charger_name] = pd.Series([0.0] * 8760, name=charger_name)
            continue

        # Leer CSV
        try:
            df_30min = pd.read_csv(toma_file)
        except Exception as e:
            logger.error(f"    [ERROR] No se pudo leer {toma_file.name}: {e}")
            hourly_profiles[charger_name] = pd.Series([0.0] * 8760, name=charger_name)
            continue

        # Validar columnas requeridas
        if 'power_kw' not in df_30min.columns:
            logger.error(f"    [ERROR] {toma_file.name} no tiene columna 'power_kw'")
            hourly_profiles[charger_name] = pd.Series([0.0] * 8760, name=charger_name)
            continue

        # Validar longitud (debe ser 17,520 para un año a 30min)
        if len(df_30min) != 17520:
            logger.warning(
                f"    [WARN] {toma_file.name} tiene {len(df_30min)} filas "
                f"(esperado 17,520 para 30min anual)"
            )

        # Crear índice temporal si no existe
        if 'date' not in df_30min.columns or 'hour_of_day' not in df_30min.columns:
            # Generar índice temporal simple
            df_30min['timestamp'] = pd.date_range(
                start='2024-01-01',
                periods=len(df_30min),
                freq='30min'
            )
        else:
            # Construir timestamp desde date + hour_of_day + minute_of_hour
            try:
                df_30min['timestamp'] = pd.to_datetime(df_30min['date']) + \
                    pd.to_timedelta(df_30min['hour_of_day'], unit='h') + \
                    pd.to_timedelta(df_30min.get('minute_of_hour', 0), unit='m')
            except Exception:
                # Fallback: usar índice secuencial
                df_30min['timestamp'] = pd.date_range(
                    start='2024-01-01',
                    periods=len(df_30min),
                    freq='30min'
                )

        # Resamplear a 1h (usar mean para power_kw instantánea)
        df_30min.set_index('timestamp', inplace=True)
        hourly_power = df_30min['power_kw'].resample('h').mean()

        # Asegurar que tiene exactamente 8,760 filas
        if len(hourly_power) != 8760:
            logger.warning(
                f"    [WARN] {charger_name} tiene {len(hourly_power)} horas después de resample "
                f"(esperado 8,760)"
            )
            # Truncar o rellenar
            if len(hourly_power) > 8760:
                hourly_power = hourly_power[:8760]
            else:
                # Rellenar con ceros
                missing = 8760 - len(hourly_power)
                hourly_power = pd.concat([
                    hourly_power,
                    pd.Series([0.0] * missing, name='power_kw')
                ])

        hourly_profiles[charger_name] = hourly_power.reset_index(drop=True)
        hourly_profiles[charger_name].name = charger_name

        if (toma_id + 1) % 20 == 0:
            logger.info(f"    Procesadas {toma_id + 1}/{n_tomas} tomas...")

    # Construir DataFrame final (8,760 × 128)
    df_hourly_annual = pd.DataFrame(hourly_profiles)

    # Reordenar columnas para mantener orden lógico
    # MOTO_CH_001 ... MOTO_CH_112, MOTO_TAXI_CH_001 ... MOTO_TAXI_CH_016
    column_order = []
    for i in range(112):
        column_order.append(f"MOTO_CH_{i + 1:03d}")
    for i in range(16):
        column_order.append(f"MOTO_TAXI_CH_{i + 1:03d}")

    # Reordenar si todas las columnas existen
    missing_cols = set(column_order) - set(df_hourly_annual.columns)
    if missing_cols:
        logger.warning(f"    [WARN] Faltan {len(missing_cols)} columnas en output")
        # Crear columnas faltantes con ceros
        for col in missing_cols:
            df_hourly_annual[col] = 0.0

    df_hourly_annual = df_hourly_annual[column_order]

    # Guardar CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_hourly_annual.to_csv(output_path, index=False)

    logger.info(f"[OK] Generado {output_path.name}: {df_hourly_annual.shape}")
    logger.info(f"     Total demand: {df_hourly_annual.sum().sum():.1f} kWh/año")
    logger.info(f"     Mean hourly: {df_hourly_annual.sum(axis=1).mean():.2f} kW")
    logger.info(f"     Peak hourly: {df_hourly_annual.sum(axis=1).max():.2f} kW")

    return df_hourly_annual


def main():
    """Entry point para conversión standalone."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    # Rutas por defecto
    project_root = Path(__file__).resolve().parents[3]
    toma_profiles_dir = project_root / "data" / "interim" / "oe2" / "chargers" / "toma_profiles"
    output_path = project_root / "data" / "interim" / "oe2" / "chargers" / "chargers_hourly_profiles_annual.csv"

    # Permitir override por argumentos
    if len(sys.argv) > 1:
        toma_profiles_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])

    try:
        df_result = convert_toma_profiles_30min_to_hourly(
            toma_profiles_dir=toma_profiles_dir,
            output_path=output_path,
        )
        logger.info(f"✓ Conversión exitosa: {df_result.shape[0]} filas × {df_result.shape[1]} columnas")
        return 0
    except Exception as e:
        logger.error(f"✗ Error en conversión: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
