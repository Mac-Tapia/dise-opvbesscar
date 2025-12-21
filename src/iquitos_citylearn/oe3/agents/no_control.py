from __future__ import annotations
import numpy as np
from citylearn.agents.base import Agent

class NoControlAgent(Agent):
    """Acciones cero para todos los actuadores (baseline sin control inteligente)."""
    def predict(self, observations, deterministic=None):
        a = np.zeros(self.action_dimension[0], dtype=np.float32)
        return [a.tolist()]
