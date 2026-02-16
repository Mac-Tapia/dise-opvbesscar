"""
Dataset Builder for CityLearn v2 - Unified OE2 Integration Module (v6.0)

NUEVO BUILDER MODULAR (14 Feb 2026):
Este modulo centraliza la construccion de datasets
para CityLearn v2 desde OE2 (Solar, Chargers, BESS).

Estructura (NEW):
+-- data_loader.py              - Cargador unificado de OE2 (CANONICAL)
+-- rewards.py                  - Funcion multiobjetivo (CANONICAL)
+-- catalog_datasets.py         - Catalogo centralizado de datasets
+-- main_build_citylearn.py     - Orquestador principal
+-- enrich_chargers.py          - Enriquecimiento de chargers
+-- integrate_datasets.py       - Integracion de 3 datasets
+-- analyze_datasets.py         - Analisis estadistico

CAMBIOS EN v6.0:
[OK] Eliminado dataset_builder.py monolitico (2,701 LOC)
[OK] Separado data_loader (validacion OE2)
[OK] Separado rewards (multiobjetivo)
[OK] Modularizado en 7 modulos enfocados
[OK] Consolidacion: viejo builder -> wrapper re-export

USO RECOMENDADO:
    from src.dataset_builder_citylearn import load_solar_data
    from src.dataset_builder_citylearn import MultiObjectiveReward
    from src.dataset_builder_citylearn import get_dataset
"""

from __future__ import annotations

# Primary exports: Data loader (canonical)
from .data_loader import (
    OE2ValidationError,
    SolarData,
    BESSData,
    ChargerData,
    DemandData,
    resolve_data_path,
    load_solar_data,
    load_bess_data,
    load_chargers_data,
    load_mall_demand_data,
    load_scenarios_metadata,
    validate_oe2_complete,
    rebuild_oe2_datasets_complete,
    # Constants
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

# Rewards (canonical)
from .rewards import (
    MultiObjectiveWeights,
    IquitosContext,
    MultiObjectiveReward,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

# Catalog
from .catalog_datasets import (
    DATASETS_CATALOG,
    get_dataset,
    list_datasets,
    validate_datasets,
    display_catalog,
)

# Observations (NEW - v6.0 SSOT)
from .observations import (
    ObservationBuilder,
    validate_observation,
    get_observation_stats,
    SOLAR_MAX_KW,
    MALL_MAX_KW,
    BESS_MAX_KWH,
    BESS_MAX_POWER_KW,
    CHARGER_MAX_KW,
    NUM_CHARGERS,
    HOURS_PER_YEAR,
    CO2_FACTOR_IQUITOS,
)

# Complete Dataset Builder (v7.0 - Load ALL columns before training)
from .complete_dataset_builder import (
    CompleteDatasetBuilder,
    build_complete_datasets_for_training,
)

__version__ = "6.0"
__author__ = "pvbesscar project"
__date__ = "2026-02-14"

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__date__",
    
    # ===== DATA LOADER (canonical source of truth) =====
    "OE2ValidationError",
    "SolarData",
    "BESSData",
    "ChargerData",
    "DemandData",
    "resolve_data_path",
    "load_solar_data",
    "load_bess_data",
    "load_chargers_data",
    "load_mall_demand_data",
    "load_scenarios_metadata",
    "validate_oe2_complete",
    "rebuild_oe2_datasets_complete",
    
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
    
    # ===== REWARDS (multiobjetivo) =====
    "MultiObjectiveWeights",
    "IquitosContext",
    "MultiObjectiveReward",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
    
    # ===== CATALOG =====
    "DATASETS_CATALOG",
    "get_dataset",
    "list_datasets",
    "validate_datasets",
    "display_catalog",
    
    # ===== OBSERVATIONS (NEW v6.0 - SSOT) =====
    "ObservationBuilder",
    "validate_observation",
    "get_observation_stats",
    "SOLAR_MAX_KW",
    "MALL_MAX_KW",
    "BESS_MAX_KWH",
    "BESS_MAX_POWER_KW",
    "CHARGER_MAX_KW",
    "NUM_CHARGERS",
    "HOURS_PER_YEAR",
    "CO2_FACTOR_IQUITOS",
    
    # ===== COMPLETE DATASET BUILDER (v7.0 - Load ALL columns) =====
    "CompleteDatasetBuilder",
    "build_complete_datasets_for_training",
]
