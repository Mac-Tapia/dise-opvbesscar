"""Objetivo Específico 3 (OE.3): CityLearn v2 con carga EV.

Este paquete contiene:
- Construcción de dataset CityLearn (schema + series temporales) a partir de los resultados del OE.2.
- Simulación y evaluación de agentes (sin control, RBC, RL/SAC).
- Cálculo de emisiones CO₂ y tabla comparativa anual y a 20 años.

SINCRONIZACIÓN CENTRALIZADA (2026-02-01):
Todos los módulos principales están vinculados para evitar duplicación.
Importa todo desde este __init__.py para máxima compatibilidad.
"""

from __future__ import annotations

# =====================================================================
# AGENTS - Factory functions y clases para agentes RL
# =====================================================================
from .agents import (
    A2CAgent,
    A2CConfig,
    BasicRBCAgent,
    NoControlAgent,
    PPOAgent,
    PPOConfig,
    RBCConfig,
    SACAgent,
    SACConfig,
    UncontrolledChargingAgent,
    detect_device,
    make_a2c,
    make_basic_ev_rbc,
    make_no_control,
    make_ppo,
    make_sac,
    make_uncontrolled,
)

# =====================================================================
# REWARDS - Multi-objetivo y contexto Iquitos
# =====================================================================
from .rewards import (
    CityLearnMultiObjectiveWrapper,
    IquitosContext,
    MultiObjectiveReward,
    MultiObjectiveWeights,
    calculate_co2_reduction_bess_discharge,
    calculate_co2_reduction_direct,
    calculate_co2_reduction_indirect,
    calculate_solar_dispatch,
    create_iquitos_reward_weights,
)

# =====================================================================
# EMISSIONS - Constantes y cálculos centralizados
# =====================================================================
from .emissions_constants import (
    EMISSIONS,
    EmissionsConstants,
    calculate_ev_co2_avoided,
    calculate_solar_co2_avoided,
    validate_config_consistency,
)

# =====================================================================
# CO₂ ANALYSIS - Tablas y comparación de emisiones
# =====================================================================
from .co2_table import (
    CityBaseline,
    EmissionsFactors,
)

# =====================================================================
# DATA LOADING - Carga de datos OE2
# =====================================================================
from .data_loader import (
    BESSData,
    ChargerData,
    MallData,
    OE2DataLoader,
    SolarData,
)

# =====================================================================
# DATASET CONSTRUCTION - Build CityLearn schema y series
# =====================================================================
from .dataset_builder import (
    BuiltDataset,
    build_citylearn_dataset,
)

# =====================================================================
# BASELINE SIMULATION - Simulación sin control inteligente
# =====================================================================
from .baseline_simulator import (
    BaselineResults,
    BaselineSimulator,
)

# =====================================================================
# VALIDATION - Validadores de schema y dataset
# =====================================================================
from .schema_validator import (
    CityLearnSchemaValidator,
    SchemaValidationError,
)

from .validate_citylearn_build import (
    CityLearnDataValidator,
    validate_citylearn_dataset,
)

# =====================================================================
# SIMULATION - Motor principal de simulación RL
# =====================================================================
from .simulate import (
    SimulationResult,
    simulate,
)

# =====================================================================
# MONITORING - Progress tracking y visualización
# =====================================================================
from .progress import (
    append_progress_row,
    render_progress_plot,
)

# =====================================================================
# ENERGY DISPATCH - Despacho inteligente de energía
# =====================================================================
from .dispatcher import (
    DispatchDecision,
    DispatchRule,
    EnergyBalance,
    EnergyDispatcher,
    EVChargeState,
)

# =====================================================================
# OBSERVABLE ENRICHMENT - Enriquecimiento de observables
# =====================================================================
from .enriched_observables import (
    EnrichedObservableWrapper,
    OperationalConstraints,
)

# =====================================================================
# CHARGER MONITORING - Monitoreo en tiempo real
# =====================================================================
from .charger_monitor import (
    ChargerMonitor,
)

# =====================================================================
# CHARGE PREDICTION - Predicción de tiempo de carga
# =====================================================================
from .charge_predictor import (
    BatteryProfile,
    ChargeScheduler,
    ChargeTimePredictor,
    ChargeTimingEstimate,
)

# =====================================================================
# DEMAND CURVE - Modelado de curva demanda
# =====================================================================
from .demand_curve import (
    DemandCurveAnalyzer,
)

# =====================================================================
# DATASET CONSTRUCTION (Advanced) - Constructor auxiliar
# =====================================================================
try:
    from .dataset_constructor import (
        DatasetBuilder,
        DatasetConfig,
        DatasetMetadata,
    )
except ImportError:
    # Fallback si el módulo no está disponible
    pass

# =====================================================================
# EXPORTS - Todas las clases y funciones públicas
# =====================================================================
__all__ = [
    # Agents
    "NoControlAgent",
    "UncontrolledChargingAgent",
    "SACAgent",
    "SACConfig",
    "PPOAgent",
    "PPOConfig",
    "A2CAgent",
    "A2CConfig",
    "BasicRBCAgent",
    "RBCConfig",
    "make_sac",
    "make_ppo",
    "make_a2c",
    "make_no_control",
    "make_uncontrolled",
    "make_basic_ev_rbc",
    "detect_device",
    # Rewards
    "MultiObjectiveWeights",
    "IquitosContext",
    "MultiObjectiveReward",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
    "calculate_co2_reduction_indirect",
    "calculate_co2_reduction_bess_discharge",
    "calculate_co2_reduction_direct",
    "calculate_solar_dispatch",
    # Emissions
    "EmissionsConstants",
    "EMISSIONS",
    "calculate_ev_co2_avoided",
    "calculate_solar_co2_avoided",
    "validate_config_consistency",
    # CO₂ Analysis
    "EmissionsFactors",
    "CityBaseline",
    # Data Loading
    "SolarData",
    "ChargerData",
    "BESSData",
    "MallData",
    "OE2DataLoader",
    # Dataset
    "BuiltDataset",
    "build_citylearn_dataset",
    "CityLearnDatasetConstructor",  # May not exist
    # Baseline
    "BaselineResults",
    "BaselineSimulator",
    # Validation
    "SchemaValidationError",
    "CityLearnSchemaValidator",
    "CityLearnDataValidator",
    "validate_citylearn_dataset",
    # Simulation
    "SimulationResult",
    "simulate",
    # Progress
    "append_progress_row",
    "render_progress_plot",
    # Dispatch
    "EVChargeState",
    "EnergyBalance",
    "DispatchRule",
    "DispatchDecision",
    "EnergyDispatcher",
    # Observables
    "OperationalConstraints",
    "EnrichedObservableWrapper",
    # Charger
    "ChargerMonitor",
    # Charge Prediction
    "BatteryProfile",
    "ChargeTimingEstimate",
    "ChargeTimePredictor",
    "ChargeScheduler",
    # Demand
    "DemandCurveAnalyzer",
    # Dataset Constructor
    "DatasetConfig",
    "DatasetMetadata",
    "DatasetBuilder",
]
