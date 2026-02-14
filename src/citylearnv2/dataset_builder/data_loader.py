"""OE2 Data Loader v5.6 - Backward Compatibility Namespace.

⚠️ CONSOLIDATED BUILDER (14 Feb 2026):
This module is now a pure re-export namespace for backward compatibility.
All actual implementation moved to:
  → src.dataset_builder_citylearn.data_loader (unified/modular)
  → src.dataset_builder_citylearn.rewards (multiobjetivo)

This is the OLD location that scripts may still import from. All imports
are transparently redirected to the new modular builder for maintainability.

Migration guide:
  OLD: from src.citylearnv2.dataset_builder.data_loader import load_solar_data
  NEW: from src.dataset_builder_citylearn.data_loader import load_solar_data
  (both work, but new is canonical)

The old monolithic src.citylearnv2.dataset_builder/dataset_builder.py is
DEPRECATED and will be removed after agent revalidation.
"""
from __future__ import annotations

# Re-export from new unified builder (canonical location)
from src.dataset_builder_citylearn.data_loader import (
    OE2ValidationError,
    SolarData,
    BESSData,
    ChargerData,
    DemandData,
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
    PROCESSED_CITYLEARN_DIR,
    BESS_CAPACITY_KWH,
    BESS_MAX_POWER_KW,
    EV_DEMAND_KW,
    N_CHARGERS,
    TOTAL_SOCKETS,
    MALL_DEMAND_KW,
    SOLAR_PV_KWP,
    CO2_FACTOR_GRID_KG_PER_KWH,
    CO2_FACTOR_EV_KG_PER_KWH,
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
    # Exceptions
    "OE2ValidationError",
    # Data classes
    "SolarData", "BESSData", "ChargerData", "DemandData",
    # Paths (primary)
    "DEFAULT_SOLAR_PATH", "DEFAULT_BESS_PATH", "DEFAULT_CHARGERS_PATH",
    "DEFAULT_MALL_DEMAND_PATH", "DEFAULT_SCENARIOS_DIR",
    "SCENARIOS_SELECTION_PE_FC_PATH", "SCENARIOS_TABLA_DETALLADOS_PATH",
    "SCENARIOS_TABLA_ESTADISTICAS_PATH", "SCENARIOS_TABLA_RECOMENDADO_PATH",
    "SCENARIOS_TABLA13_PATH",
    # Paths (interim)
    "INTERIM_SOLAR_PATHS", "INTERIM_BESS_PATH", "INTERIM_CHARGERS_PATHS",
    "INTERIM_DEMAND_PATH", "PROCESSED_CITYLEARN_DIR",
    # Constants
    "BESS_CAPACITY_KWH", "BESS_MAX_POWER_KW", "EV_DEMAND_KW",
    "N_CHARGERS", "TOTAL_SOCKETS", "MALL_DEMAND_KW", "SOLAR_PV_KWP",
    "CO2_FACTOR_GRID_KG_PER_KWH", "CO2_FACTOR_EV_KG_PER_KWH",
    # Functions
    "resolve_data_path", "load_solar_data", "load_bess_data",
    "load_chargers_data", "load_mall_demand_data", "load_scenarios_metadata",
    "validate_oe2_complete", "rebuild_oe2_datasets_complete",
]
