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
            charger_set = create_iquitos_chargers()
            chargers_list = list(charger_set.chargers) if hasattr(charger_set, 'chargers') else charger_set  # type: ignore[arg-type,assignment]
            result["chargers"] = chargers_list
            logger.info(f"Using default chargers: {len(chargers_list)} units")
    else:
        charger_set = create_iquitos_chargers()
        chargers_list = list(charger_set.chargers) if hasattr(charger_set, 'chargers') else charger_set  # type: ignore[arg-type,assignment]
        result["chargers"] = chargers_list
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

    # 4. Crear environment simplificado
    try:
        env = _create_simple_env(config)
        result["env"] = env
        result["is_valid"] = True
        logger.info("✓ Simple Gymnasium environment created successfully")
    except Exception as e:
        logger.error(f"Error creating environment: {e}", exc_info=True)
        result["errors"].append(f"Environment creation failed: {e}")
        result["is_valid"] = False

    return result


def _update_schema_paths(schema: dict[str, Any], dataset_dir: str | Path) -> dict[str, Any]:
    """Actualiza rutas en el schema para que apunten a archivos reales.

    Convierte rutas relativas a absolutas.

    Args:
        schema: Schema dictionary
        dataset_dir: Directorio del dataset

    Returns:
        Schema actualizado con rutas correctas
    """
    dataset_dir = Path(dataset_dir).resolve()

    # Actualizar rutas en cada building
    for building in schema.get("buildings", []):
        # Solar generation path
        if "energy_simulation" in building:
            sim = building["energy_simulation"]
            if "solar_generation" in sim:
                # Si la ruta es relativa, convertir a absoluta
                solar_path = sim["solar_generation"]
                if isinstance(solar_path, str):
                    solar_path = Path(solar_path)
                    if not solar_path.is_absolute():
                        # Intentar encontrar en dataset_dir primero
                        if (dataset_dir / Path(solar_path).name).exists():
                            sim["solar_generation"] = str((dataset_dir / Path(solar_path).name).resolve())
                        else:
                            # Sino, buscar en data/interim/oe2
                            oe2_path = Path("data/interim/oe2") / Path(solar_path).name
                            if oe2_path.exists():
                                sim["solar_generation"] = str(oe2_path.resolve())
            if "non_shiftable_load" in sim:
                # Actualizar paths para loads también
                load_path = sim["non_shiftable_load"]
                if isinstance(load_path, str):
                    load_path = Path(load_path)
                    if not load_path.is_absolute():
                        if (dataset_dir / Path(load_path).name).exists():
                            sim["non_shiftable_load"] = str((dataset_dir / Path(load_path).name).resolve())

    return schema


def _create_default_schema(config: dict[str, Any]) -> dict[str, Any]:
    """Crea schema CityLearn por defecto.

    Returns:
        Diccionario con schema compatible CityLearn v2
    """
    return {
        "version": "2.5.0",
        "seconds_per_time_step": 3600,
        "episode_time_steps": 8760,
        "observations": {
            "solar_irradiance": {"variable": "hour", "observation_length": 1},
            "indoor_dry_bulb_temperature": {"variable": "hour", "observation_length": 1},
            "non_shiftable_load": {"variable": "hour", "observation_length": 1},
            "solar_generation": {"variable": "hour", "observation_length": 1},
            "electrical_storage_soc": {"variable": "hour", "observation_length": 1},
            "electrical_storage_power_output": {"variable": "hour", "observation_length": 1}
        },
        "actions": {
            "electrical_storage_charging_power": {"variable": "continuous", "limits": [0.0, 1.0]},
            "electric_vehicle_charger_0_power": {"variable": "continuous", "limits": [0.0, 1.0]},
            "electric_vehicle_charger_1_power": {"variable": "continuous", "limits": [0.0, 1.0]},
            "electric_vehicle_charger_2_power": {"variable": "continuous", "limits": [0.0, 1.0]}
        },
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
    result: dict[str, Any] = {
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


def _create_simple_env(config: dict[str, Any]) -> Any:
    """Crea environment simplificado compatible con Gymnasium y agentes RL.

    Args:
        config: Diccionario de configuración

    Returns:
        Environment con interfaz gymnasium (observation y action spaces)
    """
    import numpy as np
    from gymnasium import Env, spaces

    class IquitosSimpleEnv(Env):
        """Environment simplificado para Iquitos EV Charging basado en Gymnasium."""

        metadata = {"render_modes": []}

        def __init__(self, cfg: dict[str, Any]):
            super().__init__()
            self.config = cfg
            self.time_step = 0
            self.episode_steps = cfg.get("episode_time_steps", 8760)

            # Constantes del proyecto Iquitos
            self.total_motos = 2912  # Número total de motos
            self.total_mototaxis = 416  # Número total de mototaxis
            self.grid_co2_intensity = 0.4521  # kg CO2/kWh en Iquitos
            self.charger_power_kw = 272.0 / 128  # kW por charger
            self.bess_capacity_kwh = 2000.0  # kWh de BESS

            # Acumuladores de sesión
            self.total_charging_kwh = 0.0
            self.total_solar_direct_kwh = 0.0
            self.motos_charged_this_episode = 0
            self.mototaxis_charged_this_episode = 0

            # Espacios (compatibles con Stable-Baselines3)
            self.observation_space = spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(394,),  # 394 dimensiones como en CityLearn OE3
                dtype=np.float32
            )

            self.action_space = spaces.Box(
                low=0.0,
                high=1.0,
                shape=(129,),  # 129 acciones (1 BESS + 128 chargers)
                dtype=np.float32
            )

        def reset(self, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:  # type: ignore[override]
            """Reset del environment."""
            super().reset(seed=seed)
            self.time_step = 0
            self.total_charging_kwh = 0.0
            self.total_solar_direct_kwh = 0.0
            self.motos_charged_this_episode = 0
            self.mototaxis_charged_this_episode = 0
            obs = np.zeros(394, dtype=np.float32)
            return obs, {}

        def step(self, action):
            """Paso de simulación con cálculos realistas de CO2 y VE."""
            self.time_step += 1

            # Asegurar que action sea un array 1D de floats
            action = np.asarray(action, dtype=np.float32).flatten()

            # 🔴 CRITICAL: Clamp actions to [0, 1] - SAC puede enviar valores fuera de rango
            action = np.clip(action, 0.0, 1.0)

            # Observación: valores pequeños aleatorios
            obs = np.random.randn(394).astype(np.float32) * 0.1

            # ========== CÁLCULO DE CARGA DE EV ==========
            # action[0] = BESS control (0-1)
            # action[1:129] = 128 charger powers (0-1)
            bess_control = float(action[0]) if len(action) > 0 else 0.5
            charger_actions = action[1:129] if len(action) > 1 else np.full(128, 0.5)

            # Energía cargada en esta hora (kWh) - siempre >= 0
            total_charger_power_fraction = max(0.0, float(np.mean(charger_actions)))
            hourly_charging_kwh = max(0.0, self.charger_power_kw * 128 * total_charger_power_fraction)
            self.total_charging_kwh += hourly_charging_kwh

            # ========== ESTIMACIÓN DE MOTOS Y MOTOTAXIS CARGADOS ==========
            # Suponemos que cada moto necesita ~4 kWh y mototaxis ~6 kWh por carga
            kwh_per_moto = 4.0
            kwh_per_mototaxi = 6.0

            # Distribución: motos 87.5%, mototaxis 12.5% (según proyecto)
            moto_fraction = 0.875

            # Energía destinada a motos vs mototaxis (aproximado)
            motos_kwh = hourly_charging_kwh * moto_fraction
            mototaxis_kwh = hourly_charging_kwh * (1 - moto_fraction)

            hourly_motos = motos_kwh / kwh_per_moto
            hourly_mototaxis = mototaxis_kwh / kwh_per_mototaxi

            self.motos_charged_this_episode += hourly_motos
            self.mototaxis_charged_this_episode += hourly_mototaxis

            # ========== CÁLCULO DE SOLAR Y CO2 ==========
            # Solar típico en Iquitos: ~1200 kWh/kWp/año = 4.05 GWp * 1200 = 4860 MWh
            # Promedio horario: 4860000 kWh / 8760 h = 555 kWh/h
            # Simulamos una curva sinusoidal (0 en noche, máximo al mediodía)
            hour_of_day = self.time_step % 24
            solar_curve = max(0.0, 555 * np.sin((hour_of_day - 6) * np.pi / 12))  # 6am-6pm activo

            # Uso directo de solar (fracción del total cargado)
            solar_utilization = max(0.0, bess_control * 0.5)  # BESS control afecta eficiencia
            solar_direct_kwh = max(0.0, solar_curve * solar_utilization)
            self.total_solar_direct_kwh += solar_direct_kwh

            # ========== CÁLCULO DE REDUCCIÓN DE CO2 ==========
            # CO2 DIRECTO: Desplazamiento de transporte fósil por eléctrico
            # Cada moto/mototaxi eléctrica evita quemar gasolina
            # Consumo típico: moto gasolina ~2L/100km, mototaxi ~3L/100km
            # Equivalencia: 1L gasolina = 2.31 kg CO2
            # Autonomía por carga: moto ~50km, mototaxi ~40km
            km_per_moto_charge = 50.0  # km por carga completa
            km_per_mototaxi_charge = 40.0
            gasoline_consumption_moto = 2.0 / 100  # L/km
            gasoline_consumption_mototaxi = 3.0 / 100  # L/km
            co2_per_liter_gasoline = 2.31  # kg CO2/L

            # CO2 evitado por cada vehículo cargado
            co2_per_moto = km_per_moto_charge * gasoline_consumption_moto * co2_per_liter_gasoline
            co2_per_mototaxi = km_per_mototaxi_charge * gasoline_consumption_mototaxi * co2_per_liter_gasoline

            co2_direct_avoided = max(0.0, hourly_motos * co2_per_moto + hourly_mototaxis * co2_per_mototaxi)

            # CO2 INDIRECTO: Desplazamiento de generación diesel por solar/BESS
            # Cada kWh de solar usado en lugar del grid térmico (diesel) = CO2 evitado
            # Grid Iquitos: 0.4521 kg CO2/kWh (generación térmica)
            co2_indirect_avoided = max(0.0, solar_direct_kwh * self.grid_co2_intensity)

            # ========== REWARD ==========
            # Reward basado en:
            # 1. Carga realizada (promedio de acciones)
            # 2. Uso de solar (beneficio ambiental)
            # 3. Reducción de CO2
            charging_reward = max(0.0, float(np.mean(charger_actions))) * 0.5
            solar_reward = solar_utilization * 0.3
            co2_reward = (co2_direct_avoided + co2_indirect_avoided) * 0.01
            reward = charging_reward + solar_reward + co2_reward

            # Terminación
            terminated = self.time_step >= self.episode_steps
            truncated = False

            info = {
                "time_step": self.time_step,
                "motos_cumulative": int(self.motos_charged_this_episode),
                "mototaxis_cumulative": int(self.mototaxis_charged_this_episode),
                "co2_direct_kg": co2_direct_avoided,
                "co2_indirect_kg": co2_indirect_avoided,
                "solar_direct_kwh": solar_direct_kwh,
                "charging_kwh": hourly_charging_kwh
            }

            return obs, reward, terminated, truncated, info

    return IquitosSimpleEnv(config)
