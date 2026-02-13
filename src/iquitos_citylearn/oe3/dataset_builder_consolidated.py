"""Dataset Builder Consolidado - Construye ambiente CityLearn para OE3.

Integra OE2 (dimensionamiento) con CityLearn v2 (simulación).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


def build_iquitos_env(
    config: dict[str, Any],
    solar_csv_path: Optional[str] = None,
    chargers_json_path: Optional[str] = None,
    dataset_dir: Optional[str] = None
) -> dict[str, Any]:
    """Construye ambiente CityLearn para Iquitos con datos OE2.

    Args:
        config: Configuración (de YAML)
        solar_csv_path: Path a solar timeseries CSV (8760 filas)
        chargers_json_path: Path a chargers.json
        dataset_dir: Directorio del dataset (contiene schema.json)

    Returns:
        Diccionario con:
        - env: CityLearn environment (si disponible)
        - schema: Schema dictionary
        - solar_data: Solar timeseries
        - chargers: Charger specifications
        - is_valid: Boolean indicando éxito

    Raises:
        ValueError: Si dataset no se carga correctamente
    """
    result: dict[str, Any] = {
        "env": None,
        "schema": None,
        "solar_data": None,
        "chargers": None,
        "is_valid": False,
        "errors": []
    }

    try:
        from src.dimensionamiento.oe2.data_loader import (
            load_solar_data,
            load_chargers_data,
            OE2ValidationError
        )
        from src.dimensionamiento.oe2.chargers import create_iquitos_chargers
    except ImportError as e:
        result["errors"].append(f"Cannot import OE2 modules: {e}")
        return result

    # 1. Cargar solar
    if solar_csv_path:
        try:
            solar_data = load_solar_data(solar_csv_path)
            result["solar_data"] = solar_data
            logger.info(f"✓ Solar data loaded: {solar_data.capacity_kwp} kWp")
        except OE2ValidationError as e:
            result["errors"].append(f"Solar loading failed: {e}")
            return result
    else:
        logger.warning("No solar_csv_path provided, using defaults")
        try:
            solar_data = load_solar_data("data/interim/oe2/solar/pv_generation_timeseries.csv")
            result["solar_data"] = solar_data
        except OE2ValidationError:
            logger.warning("Default solar path not available")

    # 2. Cargar chargers
    if chargers_json_path:
        try:
            chargers_list = load_chargers_data(chargers_json_path)
            result["chargers"] = chargers_list
            logger.info(f"✓ Chargers loaded: {len(chargers_list)} units")
        except OE2ValidationError as e:
            result["errors"].append(f"Chargers loading failed: {e}")
            # Fallback a defaults
            chargers_list = create_iquitos_chargers()
            result["chargers"] = list(chargers_list)
            logger.info(f"Using default chargers: {len(chargers_list)} units")
    else:
        chargers_list = create_iquitos_chargers()
        result["chargers"] = list(chargers_list)
        logger.info(f"Using default chargers: {len(chargers_list)} units")

    # 3. Cargar o crear schema
    if dataset_dir:
        schema_path = Path(dataset_dir) / "schema.json"
        if schema_path.exists():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    result["schema"] = json.load(f)
                logger.info(f"✓ Schema loaded from {schema_path}")
            except Exception as e:
                logger.warning(f"Error loading schema: {e}")

    if result["schema"] is None:
        # Crear schema por defecto
        result["schema"] = _create_default_schema(config)
        logger.info("Using default schema")

    # 4. Intentar crear CityLearn environment
    try:
        from citylearn.citylearn import CityLearnEnv
    except ImportError:
        logger.warning("CityLearn not available, skipping environment creation")
        result["is_valid"] = len(result["errors"]) == 0
        return result

    try:
        if dataset_dir and result["schema"]:
            # CityLearn requiere el schema como dict, no como path
            env = CityLearnEnv(result["schema"])
        else:
            logger.warning("No dataset_dir or schema provided, cannot create CityLearn env")
            result["is_valid"] = len(result["errors"]) == 0
            return result

        result["env"] = env
        logger.info("✓ CityLearn environment created successfully")
    except Exception as e:
        logger.error(f"Error creating CityLearn env: {e}")
        result["errors"].append(f"CityLearn env creation failed: {e}")

    # Mark as valid if no critical errors
    result["is_valid"] = len(result["errors"]) == 0

    return result


def _create_default_schema(config: dict[str, Any]) -> dict[str, Any]:
    """Crea schema CityLearn por defecto.

    Returns:
        Diccionario con schema compatible CityLearn v2
    """
    return {
        "version": "2.5.0",
        "buildings": [
            {
                "name": "Iquitos_EV_Charging_Hub",
                "latitude": -3.7525,
                "longitude": -73.2451,
                "weather_file": "data/weather/iquitos_weather.epw",
                "carbon_intensity_file": "data/carbon_intensity/iquitos_ci.csv",
                "energy_simulation_period": [1, 1, 365, 31, 23, 59],
                "physics": True,
                "random_seed": 42,
                "roof_area": 5000.0,
                "ground_floor_area": 10000.0,
                "solar_generation": {
                    "power_output_timeseries": "data/interim/oe2/solar/pv_generation_timeseries.csv"
                },
                "electrical_storage": {
                    "capacity": config.get("bess_capacity_kwh", 4520.0),
                    "power": config.get("bess_power_kw", 2712.0)
                },
                "dhw_heating": False,
                "cooling": False,
                "heating": False,
                "ev_charging": {
                    "charger_count": 128,
                    "max_power_kw": config.get("ev_max_power_kw", 272.0)
                }
            }
        ],
        "episode_time_steps": 8760,
        "schema_path": "schema.json"
    }


def validate_dataset(dataset_dir: str | Path) -> dict[str, Any]:
    """Valida completitud del dataset OE3.

    Verifica:
    - schema.json existe
    - Charger CSV files (128)
    - Solar timeseries

    Args:
        dataset_dir: Directorio con datos OE3

    Returns:
        Diccionario con resultados de validación
    """
    dataset_dir = Path(dataset_dir)
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "files_found": {
            "schema": False,
            "charger_csvs": 0,
            "solar_timeseries": False
        }
    }

    # Verificar schema
    schema_path = dataset_dir / "schema.json"
    if schema_path.exists():
        result["files_found"]["schema"] = True
    else:
        result["warnings"].append(f"schema.json not found at {schema_path}")

    # Verificar charger CSVs
    charger_dir = dataset_dir / "charger_0" if (dataset_dir / "charger_0").exists() else dataset_dir
    charger_csvs = list(charger_dir.glob("charger_*.csv"))
    result["files_found"]["charger_csvs"] = len(charger_csvs)

    if len(charger_csvs) < 128:
        result["warnings"].append(
            f"Expected 128 charger CSVs, found {len(charger_csvs)}"
        )

    # Verificar solar
    solar_path = dataset_dir / "solar_generation.csv"
    if not solar_path.exists():
        solar_path = dataset_dir / "pv_generation_timeseries.csv"

    if solar_path.exists():
        result["files_found"]["solar_timeseries"] = True
    else:
        result["errors"].append("Solar timeseries file not found")
        result["is_valid"] = False

    return result
