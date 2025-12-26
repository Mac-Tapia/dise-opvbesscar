from .uncontrolled import UncontrolledChargingAgent
from .rbc import make_basic_ev_rbc, BasicRBCAgent, RBCConfig
from .sac import make_sac, SACAgent, SACConfig, detect_device as _detect_sac
from .no_control import NoControlAgent, make_no_control
from .ppo_sb3 import make_ppo, PPOAgent, PPOConfig
from .a2c_sb3 import make_a2c, A2CAgent, A2CConfig
from ..rewards import (
    MultiObjectiveReward,
    MultiObjectiveWeights,
    IquitosContext,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

# Re-export device detection
detect_device = _detect_sac

__all__ = [
    # Agentes
    "UncontrolledChargingAgent",
    "NoControlAgent",
    "BasicRBCAgent",
    "SACAgent",
    "PPOAgent",
    "A2CAgent",
    # Factory functions
    "make_basic_ev_rbc",
    "make_sac",
    "make_no_control",
    "make_ppo",
    "make_a2c",
    # Configuraciones
    "RBCConfig",
    "SACConfig",
    "PPOConfig",
    "A2CConfig",
    # Utilidades GPU
    "detect_device",
    # Multiobjetivo / Multicriterio
    "MultiObjectiveReward",
    "MultiObjectiveWeights",
    "IquitosContext",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
]
