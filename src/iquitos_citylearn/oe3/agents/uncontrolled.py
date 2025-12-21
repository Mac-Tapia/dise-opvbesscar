from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

import numpy as np


@dataclass
class UncontrolledChargingAgent:
    """Baseline (sin control inteligente).

    - Cargadores EV: siempre intentan cargar al máximo permitido (acción = máximo).
    - Otros recursos controlables (p. ej., BESS): acción = 0 (no carga/descarga deliberada).

    Está diseñado para funcionar con CityLearn en modo centralizado o descentralizado.
    """

    env: Any
    ev_action_keywords: Tuple[str, ...] = ("electric_vehicle",)

    def __post_init__(self) -> None:
        self.action_names = getattr(self.env, "action_names", None)
        self.action_space = getattr(self.env, "action_space", None)

        if self.action_names is None or self.action_space is None:
            raise ValueError("env must expose action_names and action_space attributes (CityLearnEnv).")

        # CityLearn typically provides list[Box] and list[list[str]]; normalize.
        self._subspaces = list(self.action_space) if isinstance(self.action_space, (list, tuple)) else [self.action_space]
        self._subnames = list(self.action_names) if isinstance(self.action_names, (list, tuple)) else [self.action_names]
        self._subnames = [list(n) for n in self._subnames]

        self._low = [np.array(getattr(sp, "low", -1.0), dtype=float) for sp in self._subspaces]
        self._high = [np.array(getattr(sp, "high", 1.0), dtype=float) for sp in self._subspaces]

        # Indices of EV-related actions per subspace.
        self._ev_indices: List[List[int]] = []
        for names in self._subnames:
            idx = [i for i, n in enumerate(names) if any(k in str(n) for k in self.ev_action_keywords)]
            self._ev_indices.append(idx)

    def predict(self, observations: Any = None, deterministic: bool = True):
        actions: List[List[float]] = []
        for low, high, idxs in zip(self._low, self._high, self._ev_indices):
            a = np.zeros_like(high, dtype=float)

            # Set EV actions to maximum (charge at max power/normalized limit).
            for i in idxs:
                try:
                    a[i] = float(high[i])
                except Exception:
                    a[i] = 1.0

            a = np.clip(a, low, high)
            actions.append(a.tolist())

        return actions

    # Alias used by some wrappers
    def act(self, observations: Any = None):
        return self.predict(observations, deterministic=True)
