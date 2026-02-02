"""Agents module for RL-based energy management.

Provides three main RL agents (SAC, PPO, A2C) plus baselines (NoControl, UncontrolledCharging).
All agents compatible with CityLearn v2 and multi-objective reward optimization.
"""

# CONSOLIDADO EN no_control.py - mantener alias para backward compatibility
# from .uncontrolled import UncontrolledChargingAgent  (DEPRECATED)
from .rbc import make_basic_ev_rbc, BasicRBCAgent, RBCConfig
from .sac import make_sac, SACAgent, SACConfig, detect_device as _detect_sac
from .no_control import NoControlAgent, make_no_control, make_uncontrolled, UncontrolledChargingAgent
from .ppo_sb3 import make_ppo, PPOAgent, PPOConfig, detect_device as _detect_ppo
from .a2c_sb3 import make_a2c, A2CAgent, A2CConfig, detect_device as _detect_a2c
from .transition_manager import TransitionManager, TransitionState, create_transition_manager
from ..rewards import (
    MultiObjectiveReward,
    MultiObjectiveWeights,
    IquitosContext,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)

# Re-export device detection (unified)
def detect_device() -> str:
    """Unified device detection across all agents.

    Fallback priority: SAC → PPO → A2C → CPU
    """
    try:
        return _detect_sac()
    except (ImportError, AttributeError, RuntimeError):
        pass

    try:
        return _detect_ppo()
    except (ImportError, AttributeError, RuntimeError):
        pass

    try:
        return _detect_a2c()
    except (ImportError, AttributeError, RuntimeError):
        pass

    return "cpu"

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
    # Transition Manager
    "TransitionManager",
    "TransitionState",
    "create_transition_manager",
    # Multiobjetivo / Multicriterio
    "MultiObjectiveReward",
    "MultiObjectiveWeights",
    "IquitosContext",
    "CityLearnMultiObjectiveWrapper",
    "create_iquitos_reward_weights",
]
