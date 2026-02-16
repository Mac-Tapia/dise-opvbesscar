from __future__ import annotations

from typing import Any, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class NoControlAgent:
    """Agente baseline sin control inteligente.

    Todas las acciones son cero (no intervencion).
    Util como baseline para comparar con agentes inteligentes.

    Soporta dos modos:
    1. Acciones zero en todos los actuadores (modo neutro puro)
    2. EVs siempre al maximo, otros actuadores zero (modo uncontrolled EV charging)
    """

    def __init__(self, env: Any, ev_charge_max: bool = False):
        """
        Args:
            env: CityLearn environment
            ev_charge_max: Si True, EV chargers = maximo, otros = zero (UncontrolledCharging mode)
                          Si False, todos = zero (NoControl mode)
        """
        self.env = env
        self.ev_charge_max = ev_charge_max
        self._setup_action_space()

    def _setup_action_space(self):
        """Configura espacios de accion."""
        self.action_space = getattr(self.env, "action_space", None)
        self.action_names = getattr(self.env, "action_names", None)

        if self.action_space is None:
            # Intentar obtener de CityLearn Agent base
            try:
                if hasattr(self.env, 'action_dimension'):
                    self.action_dimension = self.env.action_dimension
                else:
                    self.action_dimension = [(1,)]
            except ImportError:
                self.action_dimension = [(1,)]
        else:
            if isinstance(self.action_space, list):
                self.action_dimension = [sp.shape for sp in self.action_space]
            else:
                self.action_dimension = [self.action_space.shape]

        # Identificar indices de acciones relacionadas con EV si es modo uncontrolled
        self._ev_indices: List[List[int]] = []
        if self.ev_charge_max and self.action_names is not None:
            action_names_list = list(self.action_names) if isinstance(self.action_names, (list, tuple)) else [self.action_names]
            action_names_list = [list(n) if isinstance(n, (list, tuple)) else [n] for n in action_names_list]

            for names in action_names_list:
                idx = [i for i, name in enumerate(names) if "electric_vehicle" in str(name).lower()]
                self._ev_indices.append(idx)
        else:
            if isinstance(self.action_space, list):
                self._ev_indices = [[] for _ in self.action_space]
            else:
                self._ev_indices = [[]]

    def predict(self, observations: Any = None, deterministic: bool = True) -> List[List[float]]:
        """Devuelve acciones basadas en modo configurado."""
        actions: List[List[float]] = []

        if isinstance(self.action_space, list):
            for i, sp in enumerate(self.action_space):
                action = np.zeros(sp.shape[0], dtype=np.float32)

                # Si modo ev_charge_max, setear EVs al maximo
                if self.ev_charge_max and i < len(self._ev_indices):
                    high = getattr(sp, "high", np.ones(sp.shape[0]))
                    for ev_idx in self._ev_indices[i]:
                        try:
                            action[ev_idx] = float(high[ev_idx])
                        except (IndexError, TypeError):
                            action[ev_idx] = 1.0

                action = np.clip(action, getattr(sp, "low", 0.0), getattr(sp, "high", 1.0))
                actions.append(action.tolist())
        elif self.action_space is not None:
            action = np.zeros(self.action_space.shape[0], dtype=np.float32)

            if self.ev_charge_max and len(self._ev_indices) > 0:
                high = getattr(self.action_space, "high", np.ones(self.action_space.shape[0]))
                for ev_idx in self._ev_indices[0]:
                    try:
                        action[ev_idx] = float(high[ev_idx])
                    except (IndexError, TypeError):
                        action[ev_idx] = 1.0

            action = np.clip(action, getattr(self.action_space, "low", 0.0),
                           getattr(self.action_space, "high", 1.0))
            actions.append(action.tolist())
        else:
            # Fallback
            for dim in self.action_dimension:
                action = np.zeros(dim[0] if isinstance(dim, tuple) else dim, dtype=np.float32)
                actions.append(action.tolist())

        return actions

    def act(self, observations: Any = None) -> List[List[float]]:
        """Alias para predict."""
        return self.predict(observations)

    def learn(self, episodes: int = 0):
        """Baseline no requiere entrenamiento."""
        mode = "Uncontrolled EV charging" if self.ev_charge_max else "No Control (all zero)"
        logger.info(f"Baseline ({mode}) - no requiere entrenamiento")


# Alias para compatibilidad backward (DEPRECATED - usar NoControlAgent directamente)
UncontrolledChargingAgent = NoControlAgent


def make_no_control(env: Any, ev_charge_max: bool = False) -> NoControlAgent:
    """Factory function para crear agente NoControl/Uncontrolled.

    Args:
        env: CityLearn environment
        ev_charge_max: Si True = UncontrolledCharging, Si False = NoControl puro
    """
    return NoControlAgent(env, ev_charge_max=ev_charge_max)


def make_uncontrolled(env: Any) -> NoControlAgent:
    """Factory function para crear agente UncontrolledCharging (EV siempre al maximo)."""
    return NoControlAgent(env, ev_charge_max=True)
