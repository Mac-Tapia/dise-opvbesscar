"""
env_factory.py — Factory de entornos CityLearn v2 para Iquitos.

Provee:
  create_iquitos_env()        → IquitosEVChargingWrapper(CityLearnEnv)
                                obs_dim=18, action_dim=3
                                [bess, ev_motos_frac, ev_mototaxis_frac]
  create_iquitos_env_for_sb3() → Monitor-wrapped gymnasium.Env compatible con SB3

ESPACIO DE ACCIÓN (3D — después del wrapper):
  action[0]  bess_action      ∈ [-1, +1]   BESS dispatch
  action[1]  ev_motos_frac    ∈ [0, 1]     fracción carga motos (carg 00-14)
  action[2]  ev_mototaxis_frac ∈ [0, 1]    fracción carga mototaxis (carg 15-18)

Pipeline:
  CityLearnEnv(mall only, BESS, PV)
      ↓
  IquitosEVChargingWrapper   ← añade control EV + reward CO2_DUAL_FOCUS v8.1
      ↓ (para SB3)
  Monitor(SB3)               ← registra métricas episodio, compatible con PPO/A2C/SAC
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Asegurar project root en sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from citylearn.citylearn import CityLearnEnv


from .schema_builder import (
    _OUTPUT_DIR as _DEFAULT_DATA_DIR,
    build_citylearn_schema,
)
from .reward_co2 import IquitosCO2Reward
from .ev_charging_wrapper import IquitosEVChargingWrapper

logger = logging.getLogger(__name__)

_SCHEMA_PATH = _DEFAULT_DATA_DIR / "schema_iquitos.json"


def _ensure_schema() -> Path:
    """Genera los datos y schema si no existen todavía."""
    if not _SCHEMA_PATH.exists():
        logger.info("Schema no encontrado — generando desde datos OE2...")
        build_citylearn_schema()
    return _SCHEMA_PATH


def create_iquitos_env(
    schema_path: Path | None = None,
    rebuild: bool = False,
) -> IquitosEVChargingWrapper:
    """Crea el entorno completo Iquitos PV-BESS-EV con control de cargadores.

    Devuelve IquitosEVChargingWrapper(CityLearnEnv), que extiende el entorno
    base CityLearn con:
    - Acción 3D: [bess, ev_motos_frac, ev_mototaxis_frac]
    - Obs 18D: CityLearn(11) + EV state(5) + tarifa(2)
    - Reward CO2_DUAL_FOCUS v8.1 (pesos en ev_charging_wrapper.py)

    Apto para entrenamiento con SB3 SAC/PPO/A2C (via create_iquitos_env_for_sb3)
    o directamente en bucle de episodios manuales.

    Parameters
    ----------
    schema_path : Path, optional
        Ruta al schema JSON. Generado automáticamente si no existe.
    rebuild : bool
        Si True, regenera CSVs y schema aunque ya existan.

    Returns
    -------
    IquitosEVChargingWrapper
        Entorno con obs_dim=18, action_dim=3.
    """
    if rebuild:
        build_citylearn_schema()

    spath = Path(schema_path) if schema_path else _ensure_schema()
    logger.info("Creando CityLearnEnv base desde schema: %s", spath)

    # CityLearn base: solo BESS + PV + mall (no EVs)
    # La IquitosCO2Reward del schema es interna a CityLearn, pero
    # IquitosEVChargingWrapper sobreescribe la reward con la versión completa
    base_env = CityLearnEnv(
        schema=str(spath),
        reward_function=IquitosCO2Reward,
        central_agent=True,
    )

    n_obs_base = base_env.observation_space[0].shape[0]
    n_act_base = base_env.action_space[0].shape[0]
    logger.info(
        "CityLearnEnv base: obs_dim=%d, action_dim=%d (solo BESS)",
        n_obs_base, n_act_base,
    )

    # Wrapper EV: añade control de 19 cargadores Modo 3 (38 sockets simultáneos)
    ev_csv = _DEFAULT_DATA_DIR / "ev_demand.csv"
    env = IquitosEVChargingWrapper(base_env, ev_demand_csv=ev_csv)

    logger.info(
        "Entorno Iquitos EV listo: obs_dim=%d, action_dim=%d [bess, motos_frac, mototaxis_frac]",
        env.observation_space.shape[0],
        env.action_space.shape[0],
    )
    return env


def create_iquitos_env_for_sb3(
    schema_path: Path | None = None,
    rebuild: bool = False,
) -> Any:
    """Crea el entorno Iquitos EV con Monitor wrapper para stable-baselines3.

    Pipeline:
        CityLearnEnv(mall+BESS+PV)
            → IquitosEVChargingWrapper (3D action, 16D obs, reward CO2 dual)
            → Monitor (SB3)  ← registra retornos de episodio sin modificar obs/act

    Apto para SB3 PPO, A2C, SAC. La acción 3D se pasa como array numpy.

    Parameters
    ----------
    schema_path : Path, optional
        Ruta al schema JSON. Generado automáticamente si no existe.
    rebuild : bool
        Si True, regenera los datos y schema.

    Returns
    -------
    gymnasium.Env (Monitor-wrapped)
        obs_space=Box(18,), action_space=Box(3,) — listo para SB3.
    """
    ev_env = create_iquitos_env(schema_path=schema_path, rebuild=rebuild)
    # IquitosEVChargingWrapper ya cumple la API gymnasium estándar:
    # obs_space=Box(18,), action_space=Box(3,), step/reset → gymnasium API
    # SB3 acepta directamente cualquier gymnasium.Env sin wrapper extra
    # Solo envolvemos con Monitor para que SB3 registre métricas de episodio
    try:
        from stable_baselines3.common.monitor import Monitor
        env: Any = Monitor(ev_env)
    except ImportError:
        env = ev_env

    logger.info(
        "SB3 env listo: obs_space=%s, action_space=%s",
        env.observation_space,
        env.action_space,
    )
    return env
