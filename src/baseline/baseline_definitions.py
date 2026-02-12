"""Baseline definitions for OE3 comparison.

Two baseline scenarios for measuring RL agent improvements:
1. CON SOLAR (4,050 kWp) - Reference scenario with PV generation
2. SIN SOLAR (0 kWp) - Scenario without solar to show solar impact
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class BaselineScenario:
    """Definition of a baseline scenario for comparison."""

    name: str
    """Scenario name (e.g., 'CON_SOLAR', 'SIN_SOLAR')"""

    description: str
    """Human-readable description"""

    solar_capacity_kwp: float
    """Solar PV capacity in kWp"""

    bess_capacity_kwh: float
    """Battery storage capacity in kWh"""

    include_solar_generation: bool
    """Whether to include solar generation in simulation"""

    control_strategy: str
    """Control strategy: 'uncontrolled', 'rule_based', 'no_control'"""

    co2_intensity_grid: float = 0.4521
    """Grid CO2 intensity in kg CO2/kWh (Iquitos thermal grid)"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'solar_capacity_kwp': self.solar_capacity_kwp,
            'bess_capacity_kwh': self.bess_capacity_kwh,
            'include_solar_generation': self.include_solar_generation,
            'control_strategy': self.control_strategy,
            'co2_intensity_grid': self.co2_intensity_grid,
        }


# Baseline 1: CON SOLAR (with 4,050 kWp)
BASELINE_CON_SOLAR = BaselineScenario(
    name='CON_SOLAR',
    description='Baseline with 4,050 kWp solar generation (reference for RL agents)',
    solar_capacity_kwp=4050.0,
    bess_capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
    include_solar_generation=True,
    control_strategy='uncontrolled',
    co2_intensity_grid=0.4521,
)

# Baseline 2: SIN SOLAR (0 kWp)
BASELINE_SIN_SOLAR = BaselineScenario(
    name='SIN_SOLAR',
    description='Baseline without solar (0 kWp) - shows impact of PV installation',
    solar_capacity_kwp=0.0,
    bess_capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
    include_solar_generation=False,
    control_strategy='uncontrolled',
    co2_intensity_grid=0.4521,
)

# All baselines for iteration
ALL_BASELINES = [BASELINE_CON_SOLAR, BASELINE_SIN_SOLAR]


def get_baseline(name: str) -> BaselineScenario | None:
    """Get baseline scenario by name.

    Args:
        name: Baseline name ('CON_SOLAR', 'SIN_SOLAR')

    Returns:
        BaselineScenario or None if not found
    """
    for baseline in ALL_BASELINES:
        if baseline.name.upper() == name.upper():
            return baseline
    return None
