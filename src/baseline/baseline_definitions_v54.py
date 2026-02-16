"""Baseline definitions for OE3 comparison (OE2 v5.4 UPDATED).

Two baseline scenarios for measuring RL agent improvements:
1. CON SOLAR (4,050 kWp) - Reference scenario with PV generation (OE2 v5.4)
2. SIN SOLAR (0 kWp) - Scenario without solar to show PV impact (OE2 v5.4)

Data sources: Cleaned and validated OE2 v5.4 datasets
- Solar: pv_generation_kwh from bess_simulation_hourly.csv
- EV loads: chargers_ev_ano_2024_v3.csv (processed hourly in BESS)
- Mall loads: demandamallhorakwh.csv (cleaned to 8,760 hours)
- BESS: 1,700 kWh / 400 kW with 95% efficiency
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
    """Battery storage capacity in kWh (OE2 v5.4: 1,700 kWh)"""

    include_solar_generation: bool
    """Whether to include solar generation in simulation"""

    control_strategy: str
    """Control strategy: 'uncontrolled', 'rule_based', 'no_control'"""

    co2_intensity_grid: float = 0.4521
    """Grid CO2 intensity in kg CO2/kWh (Iquitos diesel B5 per OSINERGMIN)"""

    data_source: str = "OE2 v5.4 (cleaned hourly BESS simulation)"
    """Data source for this scenario"""

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
            'data_source': self.data_source,
        }


# ============================================================================
# OE2 v5.4 BASELINES (Cleaned datasets, validated 8,760 hours)
# ============================================================================

# Baseline 1: CON SOLAR (with 4,050 kWp)
# Reference: Uncontrolled scenario WITH full solar generation
# Used to measure RL agent improvements (CO2 reduction target)
BASELINE_CON_SOLAR = BaselineScenario(
    name='CON_SOLAR',
    description='Uncontrolled + 4,050 kWp solar + 1,700 kWh BESS (OE2 v5.4) - RL REFERENCE',
    solar_capacity_kwp=4050.0,
    bess_capacity_kwh=1700.0,  # v5.4: 1,700 kWh (full system, EV+Mall integrated)
    include_solar_generation=True,
    control_strategy='uncontrolled',
    co2_intensity_grid=0.4521,  # Iquitos diesel B5 (OSINERGMIN)
    data_source='OE2 v5.4: pv_generation_kwh, ev_demand_kwh, mall_demand_kwh from bess_simulation_hourly.csv',
)

# Baseline 2: SIN SOLAR (0 kWp)
# Reference: Shows impact of losing 4,050 kWp solar capacity
# Measures potential CO2 savings from solar installation (~410,000 kg CO2/year)
BASELINE_SIN_SOLAR = BaselineScenario(
    name='SIN_SOLAR',
    description='Uncontrolled + No Solar + 1,700 kWh BESS (OE2 v5.4) - Shows solar impact',
    solar_capacity_kwp=0.0,  # No solar generation
    bess_capacity_kwh=1700.0,  # v5.4 capacity available but no PV to charge it
    include_solar_generation=False,
    control_strategy='uncontrolled',
    co2_intensity_grid=0.4521,  # Iquitos diesel B5 (OSINERGMIN)
    data_source='OE2 v5.4: ev_demand_kwh, mall_demand_kwh from bess_simulation_hourly.csv (0% solar)',
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
