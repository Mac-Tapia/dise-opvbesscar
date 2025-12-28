from __future__ import annotations

from typing import Any, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class NoControlAgent:
    """Agente baseline sin control inteligente.
    
    Todas las acciones son cero (no intervención).
    Útil como baseline para comparar con agentes inteligentes.
    """
    
    def __init__(self, env: Any):
        self.env = env
        self._setup_action_space()
    
    def _setup_action_space(self):
        """Configura espacios de acción."""
        self.action_space = getattr(self.env, "action_space", None)
        
        if self.action_space is None:
            # Intentar obtener de CityLearn Agent base
            try:
                from citylearn.agents.base import Agent
                _ = Agent  # Referencia para evitar warning de import no usado
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
    
    def predict(self, observations: Any = None, deterministic: bool = True) -> List[List[float]]:
        """Devuelve acciones cero para todos los actuadores."""
        actions: List[List[float]] = []
        
        if isinstance(self.action_space, list):
            for sp in self.action_space:
                action = np.zeros(sp.shape[0], dtype=np.float32)
                actions.append(action.tolist())
        elif self.action_space is not None:
            action = np.zeros(self.action_space.shape[0], dtype=np.float32)
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
        """NoControl no requiere entrenamiento."""
        logger.info("NoControl no requiere entrenamiento (baseline)")


def make_no_control(env: Any) -> NoControlAgent:
    """Factory function para crear agente NoControl."""
    return NoControlAgent(env)
