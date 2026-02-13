"""Initialize baseline module."""

from __future__ import annotations

from .baseline_definitions import (
    BaselineScenario,
    BASELINE_CON_SOLAR,
    BASELINE_SIN_SOLAR,
    ALL_BASELINES,
    get_baseline,
)
from .baseline_calculator import BaselineCalculator

__all__ = [
    'BaselineScenario',
    'BASELINE_CON_SOLAR',
    'BASELINE_SIN_SOLAR',
    'ALL_BASELINES',
    'get_baseline',
    'BaselineCalculator',
]
