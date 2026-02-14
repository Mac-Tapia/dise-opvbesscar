"""CONSOLIDATED DATASET BUILDER (14 Feb 2026).

⚠️ REFACTORED & MODULARIZED:

This namespace is now a BACKWARD COMPATIBILITY LAYER for the new modular builder
located at src.dataset_builder_citylearn/.

OLD STRUCTURE (DEPRECATED):
├── dataset_builder.py (2,701 LOC monolithic) ❌ REMOVED
├── data_loader.py (re-export wrapper) → uses new src.dataset_builder_citylearn
├── rewards.py (1,022 LOC) → copied to src.dataset_builder_citylearn
├── progress.py (deprecated) ❌ REMOVED
├── transition_manager.py (deprecated) → moved to src.agents/
├── metrics_extractor.py (deprecated) → moved to src.agents/
└── fixed_schedule.py (deprecated) → moved to src.agents/

NEW STRUCTURE (CANONICAL):
src/dataset_builder_citylearn/
├── data_loader.py (unified OE2 loader with validation)
├── rewards.py (multiobjetivo reward function)
├── catalog_datasets.py (dataset metadata catalog)
├── main_build_citylearn.py (environment builder)
├── enrich_chargers.py (data enrichment)
├── integrate_datasets.py (dataset integration)
└── analyze_datasets.py (analysis tools)

MIGRATION GUIDE:
From: from src.citylearnv2.dataset_builder import load_solar_data
To:   from src.dataset_builder_citylearn import load_solar_data

Both work during transition period, but new location is canonical.

Version: 2026-02-14 (v6.0 - Consolidated)
"""

from __future__ import annotations

# Re-export from new modular builder
from src.dataset_builder_citylearn.data_loader import (
    # Exceptions
    OE2ValidationError,
    # Data classes
    SolarData,
    BESSData,
    ChargerData,
    DemandData,
    # Functions
    resolve_data_path,
    load_solar_data,
    load_bess_data,
    load_chargers_data,
    load_mall_demand_data,
    load_scenarios_metadata,
    validate_oe2_complete,
    rebuild_oe2_datasets_complete,
    # Path constants
    DEFAULT_SOLAR_PATH,
    DEFAULT_BESS_PATH,
    DEFAULT_CHARGERS_PATH,
    DEFAULT_MALL_DEMAND_PATH,
    DEFAULT_SCENARIOS_DIR,
    INTERIM_SOLAR_PATHS,
    INTERIM_BESS_PATH,
    INTERIM_CHARGERS_PATHS,
    INTERIM_DEMAND_PATH,
    # OE2 constants
    BESS_CAPACITY_KWH,
    BESS_MAX_POWER_KW,
    EV_DEMAND_KW,
    N_CHARGERS,
    TOTAL_SOCKETS,
    MALL_DEMAND_KW,
    SOLAR_PV_KWP,
    CO2_FACTOR_GRID_KG_PER_KWH,
    CO2_FACTOR_EV_KG_PER_KWH,
)

from src.dataset_builder_citylearn.rewards import (
    MultiObjectiveWeights,
    IquitosContext,
    MultiObjectiveReward,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

__all__ = [
    # ===== EXCEPTIONS =====
    "OE2ValidationError",
    
    # ===== DATA CLASSES =====
    "SolarData",
    "BESSData",
    "ChargerData",
    "DemandData",
    
    # ===== FUNCTIONS: DATA LOADING =====
    "resolve_data_path",
    "load_solar_data",
    "load_bess_data",
    "load_chargers_data",
    "load_mall_demand_data",
    "load_scenarios_metadata",
    "validate_oe2_complete",
    "rebuild_oe2_datasets_complete",
    
    # ===== PATH CONSTANTS =====
    "DEFAULT_SOLAR_PATH",
    "DEFAULT_BESS_PATH",
    "DEFAULT_CHARGERS_PATH",
    "DEFAULT_MALL_DEMAND_PATH",
    "DEFAULT_SCENARIOS_DIR",
    "INTERIM_SOLAR_PATHS",
    "INTERIM_BESS_PATH",
    "INTERIM_CHARGERS_PATHS",
    "INTERIM_DEMAND_PATH",
    
    # ===== OE2 CONSTANTS =====
    "BESS_CAPACITY_KWH",
    "BESS_MAX_POWER_KW",
    "EV_DEMAND_KW",
    "N_CHARGERS",
    "TOTAL_SOCKETS",
    "MALL_DEMAND_KW",
    "SOLAR_PV_KWP",
    "CO2_FACTOR_GRID_KG_PER_KWH",
    "CO2_FACTOR_EV_KG_PER_KWH",
    
    # ===== REWARD FUNCTIONS =====
    "MultiObjectiveWeights",
    "IquitosContext",
    "MultiObjectiveReward",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
]
