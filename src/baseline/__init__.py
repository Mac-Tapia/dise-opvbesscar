"""Initialize baseline module."""

from __future__ import annotations

from .baseline_definitions_v54 import (
    BaselineScenario,
    BASELINE_CON_SOLAR,
    BASELINE_SIN_SOLAR,
    ALL_BASELINES,
    get_baseline,
)
from .baseline_calculator_v2 import BaselineCalculator

__all__ = [
    'BaselineScenario',
    'BASELINE_CON_SOLAR',
    'BASELINE_SIN_SOLAR',
    'ALL_BASELINES',
    'get_baseline',
    'BaselineCalculator',
]
