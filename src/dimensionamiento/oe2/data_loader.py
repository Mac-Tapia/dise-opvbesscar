"""OE2 Data Loader - Carga y valida datos de dimensionamiento.

Proporciona:
- Carga de datos OE2 (solar, chargers, BESS)
- Validación de integridad
- Conversión de formatos
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import json
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class OE2ValidationError(Exception):
    """Excepción para errores de validación OE2."""
    pass


@dataclass(frozen=True)
class SolarData:
    """Datos inmutables de generación solar."""

    timeseries: np.ndarray  # 8760 valores horarios (W/m²)
    capacity_kwp: float     # Capacidad instalada (kWp)
    location: str           # Ubicación (ej: "Iquitos, Peru")

    def __post_init__(self):
        if len(self.timeseries) != 8760:
            raise OE2ValidationError(
                f"Solar timeseries must have exactly 8760 hourly values, got {len(self.timeseries)}"
            )
        if self.capacity_kwp <= 0:
            raise OE2ValidationError(f"Capacity must be positive, got {self.capacity_kwp}")


@dataclass(frozen=True)
class BESSData:
    """Datos inmutables de almacenamiento (BESS)."""

    capacity_kwh: float    # Capacidad energética (kWh)
    power_kw: float        # Potencia max (kW)
    efficiency: float      # Eficiencia (0-1)

    def __post_init__(self):
        if self.capacity_kwh <= 0:
            raise OE2ValidationError(f"BESS capacity must be positive, got {self.capacity_kwh}")
        if self.power_kw <= 0:
            raise OE2ValidationError(f"BESS power must be positive, got {self.power_kw}")
        if not (0 < self.efficiency <= 1):
            raise OE2ValidationError(f"BESS efficiency must be in (0, 1], got {self.efficiency}")


@dataclass(frozen=True)
class ChargerData:
    """Datos inmutables de cargador individual."""

    charger_id: int        # ID único
    max_power_kw: float    # Potencia máxima (kW)
    vehicle_type: str      # "moto" o "mototaxi"
    sockets: int           # Número de sockets (típicamente 4)


def load_solar_data(csv_path: Path | str) -> SolarData:
    """Carga datos de generación solar desde CSV.

    El CSV debe tener:
    - Exactamente 8760 filas (1 año horario)
    - Una columna numérica (W/m² o similar)

    Args:
        csv_path: Ruta a CSV de solar

    Returns:
        SolarData con serie de 8760 valores

    Raises:
        OE2ValidationError: Si formato o longitud inválidos
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise OE2ValidationError(f"Solar CSV not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise OE2ValidationError(f"Error reading solar CSV: {e}")

    # Buscar primera columna numérica
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        raise OE2ValidationError("No numeric columns found in solar CSV")

    values = df[numeric_cols[0]].astype(float).values

    if len(values) != 8760:
        raise OE2ValidationError(
            f"Solar data must have 8760 hourly rows, got {len(values)}"
        )

    # Validar que no todos sean cero
    if np.all(values == 0):
        raise OE2ValidationError("Solar values are all zero - invalid data")

    return SolarData(
        timeseries=values,
        capacity_kwp=4050.0,  # Valor OE2 standard
        location="Iquitos, Peru"
    )


def load_bess_data(config: Dict[str, Any]) -> BESSData:
    """Carga datos de BESS desde configuración.

    Args:
        config: Diccionario con claves:
            - bess_capacity_kwh
            - bess_power_kw
            - bess_efficiency (opcional, default 0.95)

    Returns:
        BESSData con especificaciones del storage
    """
    try:
        capacity = float(config.get("bess_capacity_kwh", 4520.0))
        power = float(config.get("bess_power_kw", 2712.0))
        efficiency = float(config.get("bess_efficiency", 0.95))
    except (ValueError, TypeError) as e:
        raise OE2ValidationError(f"Invalid BESS config: {e}")

    return BESSData(
        capacity_kwh=capacity,
        power_kw=power,
        efficiency=efficiency
    )


def load_chargers_data(json_path: Path | str) -> List[ChargerData]:
    """Carga datos de cargadores desde JSON.

    El JSON debe ser:
    ```json
    [
      {
        "charger_id": 0,
        "max_power_kw": 2.125,
        "vehicle_type": "moto",
        "sockets": 4
      },
      ...
    ]
    ```

    Args:
        json_path: Ruta a JSON de chargers

    Returns:
        Lista de 32+ ChargerData (típicamente 128 total con multiplicador de sockets)

    Raises:
        OE2ValidationError: Si formato inválido
    """
    json_path = Path(json_path)

    if not json_path.exists():
        logger.warning(f"Chargers JSON not found: {json_path}, creating defaults")
        return _create_default_chargers()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise OE2ValidationError(f"Error reading chargers JSON: {e}")

    if not isinstance(data, list):
        raise OE2ValidationError("Chargers JSON must be a list")

    chargers = []
    for item in data:
        try:
            charger = ChargerData(
                charger_id=int(item["charger_id"]),
                max_power_kw=float(item["max_power_kw"]),
                vehicle_type=str(item.get("vehicle_type", "moto")).lower(),
                sockets=int(item.get("sockets", 4))
            )
            chargers.append(charger)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid charger entry: {e}")

    if not chargers:
        logger.warning("No valid chargers loaded, using defaults")
        return _create_default_chargers()

    return chargers


def _create_default_chargers() -> List[ChargerData]:
    """Crea 32 cargadores default (128 sockets totales × 4 c/u).

    Distribución:
    - 28 para motos
    - 4 para mototaxis

    Returns:
        Lista de 32 ChargerData
    """
    chargers = []

    # 28 cargadores para motos
    for i in range(28):
        chargers.append(ChargerData(
            charger_id=i,
            max_power_kw=2.125,
            vehicle_type="moto",
            sockets=4
        ))

    # 4 cargadores para mototaxis
    for i in range(28, 32):
        chargers.append(ChargerData(
            charger_id=i,
            max_power_kw=2.125,
            vehicle_type="mototaxi",
            sockets=4
        ))

    return chargers


def validate_oe2_complete(
    solar_path: Path | str,
    bess_config: Dict[str, Any],
    chargers_path: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Validación completa de todos los datos OE2.

    Verifica:
    - Solar: 8760 valores horarios, no todos cero
    - BESS: Capacidad > 0, potencia > 0
    - Chargers: Mínimo 32, máximo 128 acciones

    Args:
        solar_path: Ruta a CSV de solar
        bess_config: Diccionario de config BESS
        chargers_path: Ruta a JSON de chargers (opcional)

    Returns:
        Diccionario con resultados de validación

    Raises:
        OE2ValidationError: Si alguna validación falla
    """
    results = {
        "solar": None,
        "bess": None,
        "chargers": None,
        "is_valid": False,
        "errors": []
    }

    try:
        # Validar solar
        solar = load_solar_data(solar_path)
        results["solar"] = {
            "capacity_kwp": solar.capacity_kwp,
            "timesteps": len(solar.timeseries),
            "location": solar.location
        }
    except OE2ValidationError as e:
        results["errors"].append(f"Solar validation failed: {str(e)}")

    try:
        # Validar BESS
        bess = load_bess_data(bess_config)
        results["bess"] = {
            "capacity_kwh": bess.capacity_kwh,
            "power_kw": bess.power_kw,
            "efficiency": bess.efficiency
        }
    except OE2ValidationError as e:
        results["errors"].append(f"BESS validation failed: {str(e)}")

    try:
        # Validar chargers
        chargers = load_chargers_data(chargers_path or "")
        total_sockets = sum(c.sockets for c in chargers)
        motos = sum(1 for c in chargers if c.vehicle_type == "moto")
        mototaxis = sum(1 for c in chargers if c.vehicle_type == "mototaxi")

        results["chargers"] = {
            "total_units": len(chargers),
            "total_sockets": total_sockets,
            "motos": motos,
            "mototaxis": mototaxis
        }

        if total_sockets < 32 or total_sockets > 256:
            results["errors"].append(
                f"Total charger actions {total_sockets} outside valid range [32, 256]"
            )
    except OE2ValidationError as e:
        results["errors"].append(f"Chargers validation failed: {str(e)}")

    # Mark as valid if no errors
    results["is_valid"] = len(results["errors"]) == 0

    if not results["is_valid"]:
        logger.error(f"OE2 Validation failed with {len(results['errors'])} error(s)")
    else:
        logger.info("✓ OE2 Validation passed")

    return results
