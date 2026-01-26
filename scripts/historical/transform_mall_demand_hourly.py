#!/usr/bin/env python3
"""
Transformar demanda de mall de 15 minutos a resolución horaria (8,760 horas/año).

Entrada: data/interim/oe2/demandamallkwh/demandamallkwh.csv (15 minutos)
Salida: data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv (1 hora × 365 días)

Integración: Los datos horarios se usan en dataset_constructor.py para observable #4
"""

import logging
from pathlib import Path

import pandas as pd

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Rutas
PROJECT_ROOT = Path(__file__).parent.parent
MALL_DATA_DIR = PROJECT_ROOT / 'data' / 'interim' / 'oe2' / 'demandamallkwh'
MALL_15MIN_FILE = MALL_DATA_DIR / 'demandamallkwh.csv'
MALL_HOURLY_FILE = MALL_DATA_DIR / 'demanda_mall_horaria_anual.csv'


def load_mall_15min_data() -> pd.DataFrame:
    """Cargar datos de 15 minutos del mall."""
    logger.info(f"Cargando datos 15-min desde: {MALL_15MIN_FILE}")

    try:
        # Cargar con separador punto y coma
        df = pd.read_csv(MALL_15MIN_FILE, sep=';')
        logger.info(f"✓ Cargados {len(df)} registros de 15 minutos")

        # Renombrar columnas
        df.columns = ['datetime_str', 'kwh']

        # Convertir a datetime
        df['datetime'] = pd.to_datetime(df['datetime_str'], format='%d/%m/%Y %H:%M')

        logger.info(f"Rango de fechas: {df['datetime'].min()} a {df['datetime'].max()}")
        logger.info(f"Resolución: {(df['datetime'].iloc[1] - df['datetime'].iloc[0]).total_seconds() / 60:.0f} minutos")

        return df
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        raise


def aggregate_to_hourly(df_15min: pd.DataFrame) -> pd.DataFrame:
    """Agregar datos de 15 minutos a resolución horaria (promedio)."""
    logger.info("Agregando a resolución horaria...")

    # Set datetime como index
    df_15min = df_15min.set_index('datetime')

    # Resample a 1 hora (promedio de los 4 datos de 15 minutos)
    df_hourly = df_15min['kwh'].resample('h').mean()

    # Convertir a DataFrame
    df_hourly = df_hourly.reset_index()
    df_hourly.columns = ['datetime', 'kwh']

    logger.info(f"✓ Agregados a {len(df_hourly)} registros horarios")
    logger.info(f"  Energía promedio horaria: {df_hourly['kwh'].mean():.2f} kWh")
    logger.info(f"  Energía mín/máx: {df_hourly['kwh'].min():.2f} / {df_hourly['kwh'].max():.2f} kWh")

    return df_hourly


def expand_to_full_year(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Expandir datos a 1 año completo (365 días × 24 horas = 8,760 registros).

    Si los datos originales no cubre 1 año, repetir el patrón disponible.
    Si cubre más, tomar solo 1 año.
    """
    logger.info("Expandiendo a 1 año completo (8,760 horas)...")

    # Crear timeline de 1 año
    start_date = pd.Timestamp('2024-01-01')
    end_date = start_date + pd.DateOffset(days=365)

    datetime_full_year = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]  # Excluir final

    logger.info(f"Timeline de 1 año: {start_date} a {start_date + pd.DateOffset(days=364)}")
    logger.info(f"Registros esperados: {len(datetime_full_year)}")

    # Datos disponibles
    n_available = len(df_hourly)
    n_required = len(datetime_full_year)

    if n_available >= n_required:
        # Tomar solo 1 año
        logger.info(f"Datos disponibles: {n_available} (>= {n_required})")
        logger.info("Tomando solo 1 año de los datos disponibles")
        df_year = df_hourly.iloc[:n_required].copy()
        df_year['datetime'] = datetime_full_year.values
    else:
        # Repetir patrón
        logger.warning(f"Datos disponibles: {n_available} (< {n_required})")
        logger.warning(f"Falta: {n_required - n_available} registros")
        logger.warning("Repitiendo patrón de datos disponibles")

        # Repetir el patrón
        n_repeats = (n_required // n_available) + 1
        df_expanded = pd.concat([df_hourly] * n_repeats, ignore_index=True)
        df_year = df_expanded.iloc[:n_required].copy()
        df_year['datetime'] = datetime_full_year.values
        df_year.reset_index(drop=True, inplace=True)

    logger.info(f"✓ Expandido a {len(df_year)} registros (8,760 horas)")
    logger.info(f"  Energía anual total: {df_year['kwh'].sum():.0f} kWh")
    logger.info(f"  Energía diaria promedio: {df_year['kwh'].sum() / 365:.2f} kWh")

    return df_year


def save_hourly_data(df_hourly: pd.DataFrame):
    """Guardar datos horarios anuales."""
    logger.info(f"Guardando en: {MALL_HOURLY_FILE}")

    # Formato: YYYY-MM-DD HH:00 | kwh
    df_hourly['datetime_str'] = df_hourly['datetime'].dt.strftime('%Y-%m-%d %H:00')

    output_df = df_hourly[['datetime_str', 'kwh']].copy()
    output_df.columns = ['datetime', 'kwh']

    output_df.to_csv(MALL_HOURLY_FILE, sep=',', index=False)

    logger.info(f"✓ Guardados {len(output_df)} registros horarios")


def validate_output():
    """Validar que el archivo de salida está correcto."""
    logger.info("Validando salida...")

    df = pd.read_csv(MALL_HOURLY_FILE)

    # Verificaciones
    checks = {
        'Registros == 8760': len(df) == 8760,
        'Sin NaN': df['kwh'].notna().all(),
        'kwh >= 0': (df['kwh'] >= 0).all(),
        'Tipo datetime correcto': len(df['datetime'].iloc[0].split(' ')) == 2,
    }

    all_ok = all(checks.values())

    for check, result in checks.items():
        symbol = '✓' if result else '❌'
        logger.info(f"  {symbol} {check}: {result}")

    if all_ok:
        logger.info("✅ Validación exitosa")

        # Mostrar estadísticas
        logger.info("\nEstadísticas:")
        logger.info(f"  Energía anual: {df['kwh'].sum():.0f} kWh")
        logger.info(f"  Energía diaria promedio: {df['kwh'].sum() / 365:.2f} kWh")
        logger.info(f"  Energía horaria mín/máx: {df['kwh'].min():.2f} / {df['kwh'].max():.2f} kWh")
        logger.info(f"  Primeros registros:")
        for i in range(min(3, len(df))):
            logger.info(f"    {df['datetime'].iloc[i]}: {df['kwh'].iloc[i]:.2f} kWh")
        logger.info(f"  ...últimos registros:")
        for i in range(max(0, len(df)-3), len(df)):
            logger.info(f"    {df['datetime'].iloc[i]}: {df['kwh'].iloc[i]:.2f} kWh")
    else:
        logger.error("❌ Validación fallida")
        return False

    return True


def main():
    """Función principal."""
    logger.info("="*70)
    logger.info("TRANSFORMAR DEMANDA MALL: 15 MIN → 1 HORA × 1 AÑO")
    logger.info("="*70)
    logger.info("")

    try:
        # Cargar datos 15-min
        df_15min = load_mall_15min_data()

        # Agregar a horario
        df_hourly = aggregate_to_hourly(df_15min)

        # Expandir a 1 año
        df_year = expand_to_full_year(df_hourly)

        # Guardar
        save_hourly_data(df_year)

        # Validar
        valid = validate_output()

        logger.info("")
        logger.info("="*70)
        if valid:
            logger.info("✅ TRANSFORMACIÓN COMPLETADA")
            logger.info(f"Salida: {MALL_HOURLY_FILE}")
        else:
            logger.info("❌ TRANSFORMACIÓN INCOMPLETA")
            return 1
        logger.info("="*70)

        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
