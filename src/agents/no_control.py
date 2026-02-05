"""Uncontrolled/No-Control baseline agents for benchmarking."""

from __future__ import annotations

from typing import Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class NoControlAgent:
    """Baseline agent that does nothing (zero control)."""

    def __init__(self, env: Any, config: Optional[dict[str, Any]] = None):
        """Initialize no-control agent.

        Args:
            env: CityLearn environment
            config: Configuration (unused)
        """
        self.env = env
        self.config = config or {}
        self._trained = False
        self.training_history: list[dict[str, float]] = []

    def learn(self, episodes: Optional[int] = None, **kwargs: Any) -> None:
        """No-op learning (doesn't actually train)."""
        logger.info("[NoControl] No training performed (baseline agent)")
        self._trained = True

    def predict(self, observations: Any, deterministic: bool = True) -> list:
        """Predict zero control (no action taken)."""
        # Return zero actions for all controllable elements
        if isinstance(self.env.action_space, list):
            return [[0.0] * sp.shape[0] for sp in self.env.action_space]
        return [[0.0] * self.env.action_space.shape[0]]

    def save(self, path: str) -> None:
        """Save baseline (no-op)."""
        logger.info("[NoControl] Save requested but nothing to save (baseline)")

    def load(self, path: str) -> None:
        """Load baseline (no-op)."""
        logger.info("[NoControl] Load requested but nothing to load (baseline)")


class UncontrolledChargingAgent(NoControlAgent):
    """Uncontrolled charging baseline - charges at constant power."""

    def predict(self, observations: Any, deterministic: bool = True) -> list:
        """Predict constant charging (1.0 = max power)."""
        # Return max power for all chargers
        if isinstance(self.env.action_space, list):
            return [[1.0] * sp.shape[0] for sp in self.env.action_space]
        return [[1.0] * self.env.action_space.shape[0]]


def make_no_control(env: Any, config: Optional[dict[str, Any]] = None) -> NoControlAgent:
    """Factory function for no-control baseline agent."""
    return NoControlAgent(env, config)


def make_uncontrolled(env: Any, config: Optional[dict[str, Any]] = None) -> UncontrolledChargingAgent:
    """Factory function for uncontrolled charging baseline agent."""
    return UncontrolledChargingAgent(env, config)
