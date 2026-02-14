"""Re-export TransitionManager from citylearnv2.dataset_builder for backward compatibility."""

from __future__ import annotations

from ..citylearnv2.dataset_builder.transition_manager import TransitionManager, TransitionState, create_transition_manager

__all__ = ["TransitionManager", "TransitionState", "create_transition_manager"]
