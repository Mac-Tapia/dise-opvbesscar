"""
src/citylearnv2 — Módulo de integración CityLearn v2 para Iquitos PV-BESS-EV.

Provee:
- schema_builder.py       : genera CSVs y schema JSON para CityLearnEnv
- reward_co2.py           : IquitosCO2Reward(RewardFunction) — multi-objetivo CO₂
- ev_charging_wrapper.py  : IquitosEVChargingWrapper — control 3D (BESS+motos+mototaxis)
- env_factory.py          : create_iquitos_env() / create_iquitos_env_for_sb3()

Espacio de acción del entorno completo:
  action[0]  bess_action       ∈ [-1, +1]
  action[1]  ev_motos_frac     ∈ [0, 1]  (15 cargadores × 2 sockets = 30 sockets)
  action[2]  ev_mototaxis_frac ∈ [0, 1]  (4 cargadores × 2 sockets = 8 sockets)
"""
from __future__ import annotations

from .env_factory import create_iquitos_env, create_iquitos_env_for_sb3
from .ev_charging_wrapper import IquitosEVChargingWrapper
from .reward_co2 import IquitosCO2Reward

__all__ = [
    "create_iquitos_env",
    "create_iquitos_env_for_sb3",
    "IquitosEVChargingWrapper",
    "IquitosCO2Reward",
]
