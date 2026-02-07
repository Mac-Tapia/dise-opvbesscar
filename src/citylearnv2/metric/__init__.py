"""
Métricas y utilidades para CityLearn v2 - OE3.

Este módulo proporciona utilidades para:
- Monitoreo de chargers
- Análisis de curva de demanda
- Despacho de energía
- Validación de schema
- Cálculo de EV demand

Los módulos principales (agents, rewards, dataset_builder) se importan
directamente desde sus ubicaciones originales.
"""

from __future__ import annotations

# Imports desde archivos que existen en este directorio
from .charger_monitor import ChargerMonitor
from .demand_curve import DemandCurveAnalyzer
from .dispatcher import (
    DispatchDecision,
    DispatchRule,
    EnergyBalance,
    EnergyDispatcher,
    EVChargeState,
)
from .ev_demand_calculator import (
    EVDemandCalculator,
)
from .schema_validator import (
    CityLearnSchemaValidator,
    SchemaValidationError,
)

# Re-export desde ubicaciones correctas para compatibilidad
# Dataset builder (desde el módulo correcto)
try:
    from src.citylearnv2.dataset_builder import (
        build_citylearn_dataset,
        BuiltDataset,
        CityLearnDataValidator,
    )
except ImportError:
    build_citylearn_dataset = None  # type: ignore
    BuiltDataset = None  # type: ignore
    CityLearnDataValidator = None  # type: ignore

# Rewards (desde módulo raíz)
try:
    from src.rewards.rewards import (
        IquitosContext,
        MultiObjectiveReward,
        MultiObjectiveWeights,
        create_iquitos_reward_weights,
    )
except ImportError:
    IquitosContext = None  # type: ignore
    MultiObjectiveReward = None  # type: ignore
    MultiObjectiveWeights = None  # type: ignore
    create_iquitos_reward_weights = None  # type: ignore

__all__ = [
    # Local modules
    "ChargerMonitor",
    "DemandCurveAnalyzer",
    "DispatchDecision",
    "DispatchRule",
    "EnergyBalance",
    "EnergyDispatcher",
    "EVChargeState",
    "EVDemandCalculator",
    "CityLearnSchemaValidator",
    "SchemaValidationError",
    # Re-exported from dataset_builder
    "build_citylearn_dataset",
    "BuiltDataset",
    "CityLearnDataValidator",
    # Re-exported from rewards
    "IquitosContext",
    "MultiObjectiveReward",
    "MultiObjectiveWeights",
    "create_iquitos_reward_weights",
]
