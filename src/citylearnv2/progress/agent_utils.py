"""Utilidades compartidas para agentes RL.

Proporciona:
- Validación de entornos y espacios
- Wrapping de observaciones/acciones
- Utilitarios de checkpoint
- Normalización y escalado
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple
import logging
import numpy as np

# Type alias for Python 3.11+
Dict = dict

logger = logging.getLogger(__name__)


def validate_env_spaces(env: Any) -> dict[str, Any]:
    """Valida que el entorno tenga espacios de observación y acción válidos.

    Args:
        env: CityLearnEnv o similar

    Returns:
        Dict con dimensiones y tipos de espacios

    Raises:
        ValueError: Si espacios no están configurados correctamente
    """
    obs_space = getattr(env, "observation_space", None)
    action_space = getattr(env, "action_space", None)

    if obs_space is None or action_space is None:
        raise ValueError("Environment must have observation_space and action_space attributes")

    # Determinar dimensiones
    if isinstance(obs_space, list):
        obs_dims = [getattr(s, "shape", (1,))[0] if hasattr(s, "shape") else 1 for s in obs_space]
        obs_dim = sum(obs_dims)
    else:
        obs_dims = [obs_space.shape[0] if hasattr(obs_space, "shape") else 1]
        obs_dim = obs_dims[0]

    if isinstance(action_space, list):
        action_dims = [getattr(s, "shape", (1,))[0] if hasattr(s, "shape") else 1 for s in action_space]
        action_dim = sum(action_dims)
    else:
        action_dims = [action_space.shape[0] if hasattr(action_space, "shape") else 1]
        action_dim = action_dims[0]

    result = {
        "obs_dim": obs_dim,
        "obs_dims": obs_dims,
        "action_dim": action_dim,
        "action_dims": action_dims,
        "obs_space": obs_space,
        "action_space": action_space,
    }

    logger.info("Environment validated: obs_dim=%s, action_dim=%s", obs_dim, action_dim)
    return result


def ensure_checkpoint_dir(checkpoint_dir: Optional[str]) -> Path:
    """Crea y valida directorio de checkpoints.

    Args:
        checkpoint_dir: Ruta al directorio (crear si no existe)

    Returns:
        Path: Ruta al directorio validado
    """
    if checkpoint_dir is None:
        checkpoint_dir = "./checkpoints"

    path = Path(checkpoint_dir)
    path.mkdir(parents=True, exist_ok=True)
    logger.info("Checkpoint directory: %s", path.absolute())
    return path


class ListToArrayWrapper:
    """Wrapper que convierte observaciones lista a numpy arrays.

    CityLearn devuelve observaciones como listas; este wrapper las convierte
    a arrays para compatibilidad con stable-baselines3.
    """

    def __init__(self, env: Any):
        self.env = env
        self.observation_space = getattr(env, "observation_space", None)
        self.action_space = getattr(env, "action_space", None)

    def reset(self, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset con conversión de lista a array."""
        obs, info = self.env.reset(**kwargs)
        return self._convert_obs(obs), info

    def step(self, action: Any) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Step con conversión de lista a array."""
        obs, reward, terminated, truncated, info = self.env.step(action)
        return self._convert_obs(obs), reward, terminated, truncated, info

    def _convert_obs(self, obs: Any) -> np.ndarray:
        """Convierte observación a array."""
        if isinstance(obs, list):
            try:
                return np.array(obs, dtype=np.float32).flatten()
            except (ValueError, TypeError):
                logger.warning("Error converting obs, returning as numpy array")
                return np.array(obs, dtype=np.float32).flatten()
        if isinstance(obs, np.ndarray):
            return obs.astype(np.float32).flatten()
        return np.array([obs], dtype=np.float32).flatten()

    def __getattr__(self, name: str) -> Any:
        """Delega atributos al entorno envuelto."""
        return getattr(self.env, name)


def flatten_action(action: Any) -> np.ndarray:
    """Aplana acción (si es lista de arrays)."""
    if isinstance(action, list):
        try:
            return np.concatenate([np.array(a, dtype=np.float32).flatten() for a in action])
        except (ValueError, TypeError):
            return np.array(action, dtype=np.float32).flatten()
    return np.array(action, dtype=np.float32).flatten()


def unflatten_action(flat_action: np.ndarray, action_dims: list) -> list:
    """Desaplana acción según dimensiones esperadas."""
    actions = []
    idx = 0
    for dim in action_dims:
        actions.append(flat_action[idx:idx+dim].tolist())
        idx += dim
    return actions


def validate_checkpoint(checkpoint_path: str) -> bool:
    """Valida que un checkpoint exista y sea accesible.

    Args:
        checkpoint_path: Ruta al checkpoint

    Returns:
        bool: True si válido
    """
    path = Path(checkpoint_path)
    if not path.exists():
        logger.warning("Checkpoint not found: %s", checkpoint_path)
        return False
    logger.info("Checkpoint validated: %s", checkpoint_path)
    return True


def clip_observations(obs: np.ndarray, clip_value: float = 10.0) -> np.ndarray:
    """Clipea observaciones normalizadas.

    Evita valores extremos que puedan causar inestabilidad.
    """
    return np.clip(obs, -clip_value, clip_value)


def normalize_observations(obs: np.ndarray, mean: Optional[np.ndarray] = None,
                          std: Optional[np.ndarray] = None) -> np.ndarray:
    """Normaliza observaciones a media=0, std=1.

    Si mean/std no se proporcionan, normaliza en esta llamada.
    """
    if mean is None:
        mean = obs.mean(axis=0)
    if std is None:
        std = obs.std(axis=0) + 1e-8

    result: np.ndarray = (obs - mean) / std
    return result


def denormalize_observations(obs: np.ndarray, mean: np.ndarray,
                            std: np.ndarray) -> np.ndarray:
    """Desnormaliza observaciones."""
    result: np.ndarray = obs * std + mean
    return result


def scale_reward(reward: float, scale: float = 0.01) -> float:
    """Escala recompensa para estabilidad."""
    return reward * scale
