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

from typing import Any, NoReturn


def _raise_missing_citylearn(exc: ModuleNotFoundError) -> NoReturn:
    raise ModuleNotFoundError(
        "CityLearn is optional and is not installed in the base environment. "
        "Use a separate CityLearn environment or install citylearn==2.5.0 "
        "--no-deps if you explicitly need src.citylearnv2."
    ) from exc


def create_iquitos_env(*args: Any, **kwargs: Any) -> Any:
    try:
        from .env_factory import create_iquitos_env as _create_iquitos_env
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("citylearn"):
            _raise_missing_citylearn(exc)
        raise

    return _create_iquitos_env(*args, **kwargs)


def create_iquitos_env_for_sb3(*args: Any, **kwargs: Any) -> Any:
    try:
        from .env_factory import create_iquitos_env_for_sb3 as _create_iquitos_env_for_sb3
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("citylearn"):
            _raise_missing_citylearn(exc)
        raise

    return _create_iquitos_env_for_sb3(*args, **kwargs)


def __getattr__(name: str) -> Any:
    if name == "IquitosEVChargingWrapper":
        from .ev_charging_wrapper import IquitosEVChargingWrapper

        return IquitosEVChargingWrapper

    if name == "IquitosCO2Reward":
        try:
            from .reward_co2 import IquitosCO2Reward
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.startswith("citylearn"):
                _raise_missing_citylearn(exc)
            raise

        return IquitosCO2Reward

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_iquitos_env",
    "create_iquitos_env_for_sb3",
    "IquitosEVChargingWrapper",
    "IquitosCO2Reward",
]
