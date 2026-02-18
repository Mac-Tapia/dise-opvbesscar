"""
Dataset Builder for CityLearn v2 - Unified OE2 Integration Module (v7.0)

ARQUITECTURA FINAL (2026-02-18):
Módulo consolidado únicamente con archivos usados en training:

Estructura ACTUAL (LIMPIA):
+-- data_loader.py              - Cargador unificado de OE2 (CANONICAL)
+-- rewards.py                  - Función multiobjetivo (CANONICAL)
+-- __init__.py                 - Re-export de lo anterior

AUDITORÍA COMPLETADA (2026-02-18):
✓ rewards.py - Conecta los 3 agentes (SAC, PPO, A2C)
✓ data_loader.py - Carga datos OE2  
✓ __init__.py - Re-exporta funciones de rewards + data_loader

ARCHIVOS ELIMINADOS (10 - no usados):
[REMOVED] analyze_datasets.py - No usado en training
[REMOVED] catalog_datasets.py - No usado en training  
[REMOVED] complete_dataset_builder.py - No usado en training
[REMOVED] enrich_chargers.py - No usado en training
[REMOVED] integrate_datasets.py - No usado en training
[REMOVED] main_build_citylearn.py - No usado en training
[REMOVED] metadata_builder.py - No usado en training
[REMOVED] observations.py - No usado en training
[REMOVED] reward_normalizer.py - No usado en training
[REMOVED] scenario_builder.py - No usado en training

USO RECOMENDADO (v7.0):
    # Para rewards (usado por SAC/PPO/A2C)
    from src.dataset_builder_citylearn.rewards import (
        IquitosContext,
        MultiObjectiveReward,
        create_iquitos_reward_weights,
    )
    
    # Para datos OE2
    from src.dataset_builder_citylearn.data_loader import (
        load_solar_data,
        load_bess_data,
        load_chargers_data,
        load_mall_demand_data,
    )
"""

from __future__ import annotations

# Primary exports: Data loader (CANONICAL source of truth)
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
    # CityLearn v2 builders
    build_citylearn_dataset,
    save_citylearn_dataset,
    load_citylearn_dataset,
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

# Rewards (CANONICAL multiobjetivo - conecta SAC/PPO/A2C)
from .rewards import (
    MultiObjectiveWeights,
    IquitosContext,
    MultiObjectiveReward,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

__version__ = "7.0"
__author__ = "pvbesscar project"
__date__ = "2026-02-18"

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
    
    # ===== CITYLEARN V2 BUILDERS =====
    "build_citylearn_dataset",
    "save_citylearn_dataset",
    "load_citylearn_dataset",
    
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
    
    # ===== REWARDS (multiobjetivo - conecta SAC/PPO/A2C) =====
    "MultiObjectiveWeights",
    "IquitosContext",
    "MultiObjectiveReward",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
]
