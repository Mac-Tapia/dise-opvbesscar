"""OE2 Data Loader v5.5 - Backward Compatibility Wrapper.

NOTA: Este archivo re-exporta desde dataset_builder.py para compatibilidad.
      TODO el código de OE2 está unificado en dataset_builder.py.

Uso recomendado:
    from src.citylearnv2.dataset_builder.dataset_builder import load_solar_data, ...
"""
from __future__ import annotations

# Re-export from dataset_builder for backward compatibility
from src.citylearnv2.dataset_builder.dataset_builder import (
    OE2ValidationError,
    SolarData,
    BESSData,
    ChargerData,
    DEFAULT_SOLAR_PATH,
    DEFAULT_BESS_PATH,
    DEFAULT_CHARGERS_PATH,
    DEFAULT_MALL_DEMAND_PATH,
    DEFAULT_SCENARIOS_DIR,
    SCENARIOS_SELECTION_PE_FC_PATH,
    SCENARIOS_TABLA_DETALLADOS_PATH,
    SCENARIOS_TABLA_ESTADISTICAS_PATH,
    SCENARIOS_TABLA_RECOMENDADO_PATH,
    SCENARIOS_TABLA13_PATH,
    INTERIM_SOLAR_PATHS,
    INTERIM_BESS_PATH,
    INTERIM_CHARGERS_PATHS,
    INTERIM_DEMAND_PATH,
    resolve_data_path,
    load_solar_data,
    load_bess_data,
    load_chargers_data,
    load_mall_demand_data,
    load_scenarios_metadata,
    validate_oe2_complete,
    rebuild_oe2_datasets_complete,
)

__all__ = [
    "OE2ValidationError", "SolarData", "BESSData", "ChargerData",
    "DEFAULT_SOLAR_PATH", "DEFAULT_BESS_PATH", "DEFAULT_CHARGERS_PATH",
    "DEFAULT_MALL_DEMAND_PATH", "DEFAULT_SCENARIOS_DIR",
    "SCENARIOS_SELECTION_PE_FC_PATH", "SCENARIOS_TABLA_DETALLADOS_PATH",
    "SCENARIOS_TABLA_ESTADISTICAS_PATH", "SCENARIOS_TABLA_RECOMENDADO_PATH",
    "SCENARIOS_TABLA13_PATH", "INTERIM_SOLAR_PATHS", "INTERIM_BESS_PATH",
    "INTERIM_CHARGERS_PATHS", "INTERIM_DEMAND_PATH", "resolve_data_path",
    "load_solar_data", "load_bess_data", "load_chargers_data",
    "load_mall_demand_data", "load_scenarios_metadata",
    "validate_oe2_complete", "rebuild_oe2_datasets_complete",
]
