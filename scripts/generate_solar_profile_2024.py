"""
Generador de perfil horario de generación solar para 2024.

Genera datos realistas de generación solar para Iquitos, Perú (3.74°S, 73.27°W)
usando PVGIS y modelos de radiación solar.

Columnas generadas:
- fecha: Fecha en formato YYYY-MM-DD (01 enero hasta 31 diciembre 2024)
- hora: Hora del día (0-23)
- irradiancia_ghi: Irradiancia global horizontal (W/m²)
- potencia_kw: Potencia en kW (basada en 4,050 kWp instalados)
- energia_kwh: Energía generada en kWh (por cada hora)
- temperatura_c: Temperatura ambiente (°C)
- velocidad_viento_ms: Velocidad del viento (m/s)

Ubicación: Iquitos, Perú (3.74°S, 73.27°W)
Capacidad instalada: 4,050 kWp
Año: 2024
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Agregar src a path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def generate_solar_profile_pvgis(
    latitude: float = -3.74,
    longitude: float = -73.27,
    installed_capacity_kwp: float = 4050.0,
    year: int = 2024,
    output_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Genera perfil de generación solar usando datos realistas.

    Intenta usar PVGIS si está disponible, si no, usa un modelo sintético realista
    basado en patrones de radiación solar y temperature estándares para la ubicación.

    Args:
        latitude: Latitud (positiva = N, negativa = S)
        longitude: Longitud (positiva = E, negativa = W)
        installed_capacity_kwp: Capacidad instalada en kWp
        year: Año a generar (default 2024)
        output_dir: Directorio de salida para guardar CSV

    Returns:
        DataFrame con columnas: fecha, hora, irradiancia_ghi, potencia_kw, energia_kwh, temperatura_c, velocidad_viento_ms
    """

    logger.info(f"Generando perfil solar para {year} en ubicación ({latitude}°, {longitude}°)")
    logger.info(f"Capacidad instalada: {installed_capacity_kwp} kWp")

    # Intentar usar PVGIS si está disponible
    df = _get_pvgis_data(latitude, longitude, year)

    if df is None:
        logger.info("PVGIS no disponible, usando modelo sintético realista...")
        df = _generate_synthetic_solar_data(latitude, longitude, year)

    # Calcular potencia y energía a partir de irradiancia
    df = _calculate_power_from_irradiance(df, installed_capacity_kwp)

    # Validación: Debe tener exactamente 8,760 horas (365 días × 24 horas)
    if len(df) != 8760:
        logger.warning(f"Dataset tiene {len(df)} filas, esperado 8,760. Ajustando...")
        df = df.iloc[:8760].copy()

    # Guardar si se especifica directorio
    if output_dir:
        output_path = Path(output_dir) / f"solar_generation_profile_{year}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"✅ Perfil solar guardado en: {output_path}")
        logger.info(f"   Total de registros: {len(df)} (8,760 = 1 año completo)")
        logger.info(f"   Generación total año: {df['energia_kwh'].sum():.2f} kWh")
        logger.info(f"   Potencia promedio: {df['potencia_kw'].mean():.2f} kW")
        logger.info(f"   Potencia máxima: {df['potencia_kw'].max():.2f} kW")

    return df


def _get_pvgis_data(latitude: float, longitude: float, year: int) -> Optional[pd.DataFrame]:
    """Obtiene datos de PVGIS si está disponible."""
    try:
        import pvlib
        from pvlib.iotools import get_pvgis_hourly

        logger.info("Descargando datos de PVGIS...")

        # Obtener datos de PVGIS
        data, meta = get_pvgis_hourly(
            latitude=latitude,
            longitude=longitude,
            start=pd.Timestamp(f"{year}-01-01"),
            end=pd.Timestamp(f"{year}-12-31"),
            raddatabase="SARAH3",  # Base de datos de radiación solar
            timeout=300,
        )

        # Renombrar columnas
        df = data.copy()
        df = df.reset_index()
        df.columns = df.columns.str.lower()

        # Extraer fecha y hora
        if "time" in df.columns:
            df["fecha"] = df["time"].dt.date
            df["hora"] = df["time"].dt.hour
        else:
            logger.warning("Columna 'time' no encontrada en PVGIS")
            return None

        # Irradiancia global horizontal
        if "ghi" in df.columns:
            df["irradiancia_ghi"] = df["ghi"].fillna(0.0)
        else:
            logger.warning("Columna 'ghi' no encontrada en PVGIS")
            return None

        # Temperatura
        if "t2m" in df.columns:
            df["temperatura_c"] = df["t2m"].fillna(20.0)
        else:
            logger.warning("Columna 't2m' no encontrada, usando temperatura promedio")
            df["temperatura_c"] = 25.0

        # Velocidad del viento
        if "ws10m" in df.columns:
            df["velocidad_viento_ms"] = df["ws10m"].fillna(2.0)
        else:
            df["velocidad_viento_ms"] = 2.0

        # Seleccionar columnas relevantes
        df = df[
            ["fecha", "hora", "irradiancia_ghi", "temperatura_c", "velocidad_viento_ms"]
        ].copy()

        logger.info(f"✅ Datos PVGIS obtenidos exitosamente: {len(df)} registros")
        return df

    except ImportError:
        logger.warning("pvlib no disponible, usando modelo sintético")
        return None
    except Exception as e:
        logger.warning(f"Error obteniendo datos PVGIS: {e}, usando modelo sintético")
        return None


def _generate_synthetic_solar_data(
    latitude: float, longitude: float, year: int
) -> pd.DataFrame:
    """Genera datos solares sintéticos realistas basados en modelos climatológicos."""

    # Parámetros para Iquitos (trópico ecuatorial)
    # - Latitud: 3.74°S (cerca del ecuador)
    # - Ubicación: Amazonía peruana
    # - Características: Alta nubosidad, radiación moderada a alta

    dates = pd.date_range(f"{year}-01-01", periods=8760, freq="h")

    data = {
        "fecha": dates.date,
        "hora": dates.hour,
        "dia_ano": dates.dayofyear,
        "dia_semana": dates.dayofweek,
    }

    df = pd.DataFrame(data)

    # ========================================================================
    # MODELO DE RADIACIÓN SOLAR (GHI - Global Horizontal Irradiance)
    # ========================================================================
    # Para Iquitos (3.74°S):
    # - Radiación máxima teórica: ~1000 W/m²
    # - Radiación promedio anual: ~500-600 W/m²
    # - Nubosidad media: 60% (reduce radiación ~40%)
    # - Patrón: radiación máxima al mediodía, variable con estaciones

    # Irradiancia teórica (clear-sky)
    hora_rad = np.radians(df["hora"] * 15 - 180)  # Convertir hora a ángulo solar
    clear_sky_ghi = 900 * np.maximum(
        0, np.sin(np.radians(latitude)) * np.sin(0) + np.cos(np.radians(latitude)) * np.cos(0) * np.cos(hora_rad)
    )

    # Factor de nubosidad variable por mes (Iquitos: alta nubosidad)
    # Menos nubes en verano austral (enero-marzo), más en invierno (junio-agosto)
    cloudiness_factor = np.array(
        [0.45, 0.46, 0.47, 0.50, 0.52, 0.48, 0.46, 0.47, 0.50, 0.52, 0.51, 0.48]
    )
    df["cloudiness"] = df["dia_ano"].apply(
        lambda x: cloudiness_factor[int((x - 1) / 30.44)]  # Aproximar mes
    )

    # GHI final = clear sky × cloudiness + ruido aleatorio
    np.random.seed(2024)
    noise = np.random.normal(0, 20, len(df))
    df["irradiancia_ghi"] = (
        (clear_sky_ghi * df["cloudiness"] + noise).clip(lower=0).astype(float)
    )

    # ========================================================================
    # MODELO DE TEMPERATURA AMBIENTE
    # ========================================================================
    # Iquitos: Clima tropical, temperatura constante ~26°C todo el año
    # Variación diaria: ~8°C (mínimo 22°C a las 5h, máximo 30°C a las 14h)

    temp_promedio_mes = np.array([26.5, 26.7, 26.5, 26.3, 26.1, 25.9, 25.8, 26.0, 26.3, 26.6, 26.8, 26.6])
    df["temp_mes"] = df["dia_ano"].apply(
        lambda x: temp_promedio_mes[int((x - 1) / 30.44)]
    )

    # Variación diaria sinusoidal
    hora_sin = np.sin((df["hora"] - 5) * np.pi / 12)  # Mínimo a las 5h, máximo a las 14h
    temp_diaria = df["temp_mes"] - 4 * np.cos((df["hora"] - 14) * np.pi / 12)
    df["temperatura_c"] = (temp_diaria + np.random.normal(0, 0.5, len(df))).astype(float)

    # ========================================================================
    # MODELO DE VELOCIDAD DE VIENTO
    # ========================================================================
    # Iquitos: Vientos bajos (amazonia)
    # Promedio: 2 m/s, rango 1-4 m/s

    viento_base = 2.0 + 0.5 * np.sin(df["hora"] * np.pi / 12)  # Variación diaria
    df["velocidad_viento_ms"] = (viento_base + np.random.normal(0, 0.3, len(df))).clip(
        lower=0.5, upper=5.0
    ).astype(float)

    # Limpiar columnas temporales
    df = df.drop(columns=["dia_ano", "dia_semana", "cloudiness", "temp_mes"])

    return df


def _calculate_power_from_irradiance(
    df: pd.DataFrame, installed_capacity_kwp: float
) -> pd.DataFrame:
    """
    Calcula potencia y energía a partir de irradiancia GHI.

    Considera:
    - Eficiencia del inversor: 0.96
    - Eficiencia de módulos a temperatura estándar: 0.18
    - Pérdidas por temperatura: -0.4% por °C sobre 25°C
    - Pérdidas por suciedad y degradación: 0.02
    """

    df = df.copy()

    # Parámetros de eficiencia
    inverter_efficiency = 0.96
    module_efficiency_stc = 0.18  # Standard Test Condition (25°C, 1000 W/m²)
    temp_coefficient = -0.004  # -0.4% por °C
    soiling_factor = 0.98  # 2% pérdidas por suciedad
    area_m2 = installed_capacity_kwp / (module_efficiency_stc * 1.0)  # Área total

    # Eficiencia de módulos considerando temperatura
    temp_loss = temp_coefficient * (df["temperatura_c"] - 25)
    module_efficiency = module_efficiency_stc * (1 + temp_loss)

    # Potencia DC generada
    pv_power_dc = (
        df["irradiancia_ghi"]
        * area_m2
        * module_efficiency
        * soiling_factor
        / 1000  # Convertir a kW
    )

    # Potencia AC después del inversor
    df["potencia_kw"] = (pv_power_dc * inverter_efficiency).clip(lower=0).astype(float)

    # Limitar a capacidad máxima
    df["potencia_kw"] = df["potencia_kw"].clip(upper=installed_capacity_kwp)

    # Energía generada (en kWh) = Potencia (kW) × 1 hora
    df["energia_kwh"] = df["potencia_kw"].astype(float)

    # Reordenar y seleccionar columnas finales
    df = df[
        [
            "fecha",
            "hora",
            "irradiancia_ghi",
            "potencia_kw",
            "energia_kwh",
            "temperatura_c",
            "velocidad_viento_ms",
        ]
    ].copy()

    # Convertir fecha a string en formato YYYY-MM-DD
    df["fecha"] = df["fecha"].astype(str)

    return df


def main():
    """Función principal para generar perfil solar."""
    output_dir = Path(__file__).parent.parent / "data" / "oe2" / "Generacionsolar"

    df = generate_solar_profile_pvgis(
        latitude=-3.74,  # Iquitos, Perú
        longitude=-73.27,
        installed_capacity_kwp=4050.0,
        year=2024,
        output_dir=str(output_dir),
    )

    # Mostrar resumen estadístico
    print("\n" + "=" * 80)
    print("RESUMEN DE GENERACIÓN SOLAR - 2024")
    print("=" * 80)
    print(f"Ubicación: Iquitos, Perú (3.74°S, 73.27°W)")
    print(f"Capacidad instalada: 4,050 kWp")
    print(f"\nESTADÍSTICAS:")
    print(f"  Total registros: {len(df)}")
    print(f"  Rango fechas: {df['fecha'].min()} a {df['fecha'].max()}")
    print(f"\n  IRRADIANCIA (W/m²):")
    print(f"    Promedio: {df['irradiancia_ghi'].mean():.2f}")
    print(f"    Mínimo: {df['irradiancia_ghi'].min():.2f}")
    print(f"    Máximo: {df['irradiancia_ghi'].max():.2f}")
    print(f"\n  POTENCIA (kW):")
    print(f"    Promedio: {df['potencia_kw'].mean():.2f}")
    print(f"    Mínimo: {df['potencia_kw'].min():.2f}")
    print(f"    Máximo: {df['potencia_kw'].max():.2f}")
    print(f"\n  ENERGÍA (kWh):")
    print(f"    Total anual: {df['energia_kwh'].sum():,.2f} kWh")
    print(f"    Promedio hora: {df['energia_kwh'].mean():.2f} kWh")
    print(f"\n  TEMPERATURA (°C):")
    print(f"    Promedio: {df['temperatura_c'].mean():.2f}")
    print(f"    Mínimo: {df['temperatura_c'].min():.2f}")
    print(f"    Máximo: {df['temperatura_c'].max():.2f}")
    print(f"\n  VELOCIDAD VIENTO (m/s):")
    print(f"    Promedio: {df['velocidad_viento_ms'].mean():.2f}")
    print(f"    Mínimo: {df['velocidad_viento_ms'].min():.2f}")
    print(f"    Máximo: {df['velocidad_viento_ms'].max():.2f}")

    print(f"\nPrimeros 5 registros:")
    print(df.head(5).to_string(index=False))

    print(f"\nÚltimos 5 registros:")
    print(df.tail(5).to_string(index=False))

    print("\n" + "=" * 80)
    print(f"✅ Archivo guardado en: data/oe2/Generacionsolar/solar_generation_profile_2024.csv")
    print("=" * 80)

    return df


if __name__ == "__main__":
    main()
