"""
Dataset Builder for CityLearn v2 - Unified OE2 Integration Module (v6.0)

NUEVO BUILDER MODULAR (14 Feb 2026):
Este módulo centraliza la construcción de datasets
para CityLearn v2 desde OE2 (Solar, Chargers, BESS).

Estructura (NEW):
├── data_loader.py              - Cargador unificado de OE2 (CANONICAL)
├── rewards.py                  - Función multiobjetivo (CANONICAL)
├── catalog_datasets.py         - Catálogo centralizado de datasets
├── main_build_citylearn.py     - Orquestador principal
├── enrich_chargers.py          - Enriquecimiento de chargers
├── integrate_datasets.py       - Integración de 3 datasets
└── analyze_datasets.py         - Análisis estadístico

CAMBIOS EN v6.0:
✅ Eliminado dataset_builder.py monolítico (2,701 LOC)
✅ Separado data_loader (validación OE2)
✅ Separado rewards (multiobjetivo)
✅ Modularizado en 7 módulos enfocados
✅ Consolidación: viejo builder → wrapper re-export

USO RECOMENDADO:
    from src.dataset_builder_citylearn import load_solar_data
    from src.dataset_builder_citylearn import MultiObjectiveReward
    from src.dataset_builder_citylearn import get_dataset

BACKWARD COMPATIBILITY:
    from src.citylearnv2.dataset_builder import load_solar_data
    (still works, pero apunta al nuevo builder)
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
]
