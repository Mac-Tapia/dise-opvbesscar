"""Metrics extraction utilities - consolidated from old citylearnv2.dataset_builder.

This module provides backward compatibility and metric extraction utilities for agent training.
"""

from __future__ import annotations

from .utils_metrics import EpisodeMetricsAccumulator, extract_step_metrics
from dataset_builder_citylearn import CO2_FACTOR_GRID_KG_PER_KWH, CO2_FACTOR_EV_KG_PER_KWH

# Re-export for backward compatibility
__all__ = [
    "extract_step_metrics",
    "calculate_co2_metrics",
    "EpisodeMetricsAccumulator",
    "get_unwrapped_env",
    "CO2_GRID_FACTOR_KG_PER_KWH",
    "CO2_EV_FACTOR_KG_PER_KWH",
]

# Alias for naming convention compatibility
CO2_GRID_FACTOR_KG_PER_KWH = CO2_FACTOR_GRID_KG_PER_KWH
CO2_EV_FACTOR_KG_PER_KWH = CO2_FACTOR_EV_KG_PER_KWH


def calculate_co2_metrics(
    grid_import_kwh: float,
    ev_energy_kwh: float,
) -> dict[str, float]:
    """Calculate CO2 metrics from energy consumption.
    
    Args:
        grid_import_kwh: Energy imported from grid (kWh)
        ev_energy_kwh: Energy to EVs (kWh)
    
    Returns:
        Dict with CO2 calculations
    """
    return {
        "co2_grid_kg": grid_import_kwh * CO2_GRID_FACTOR_KG_PER_KWH,
        "co2_ev_equivalent_kg": ev_energy_kwh * CO2_EV_FACTOR_KG_PER_KWH,
    }


def get_unwrapped_env(env):
    """Get unwrapped environment instance.
    
    Args:
        env: Wrapped environment (possibly with wrappers)
    
    Returns:
        Base unwrapped environment
    """
    while hasattr(env, 'env'):
        env = env.env
    return env
