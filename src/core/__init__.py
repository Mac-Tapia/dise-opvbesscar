"""src.core — Universal PVBESS-EV abstractions.

This package is site-agnostic and location-agnostic.  It defines the mathematical
models and configuration primitives that can be instantiated for any site on Earth:

  SiteConfig        → full site specification (location, buildings, grid)
  BuildingConfig    → one building: roof area, PV, BESS, EV fleet
  EVFleetConfig     → heterogeneous vehicle types (motos, cars, buses, …)
  GridConfig        → grid connection: tariff schedule, CO₂ intensity, capacity

  SolarModel        → PV generation timeseries from location + area + pvlib
  BESSModel         → BESS state machine (charge / discharge / SoC)
  EVFleetModel      → stochastic EV arrival + demand aggregation
  EnergyBalance     → pure power-balance equations (no site coupling)
  UniversalReward   → configurable CO₂/cost/satisfaction reward
"""
from src.core.site import (
    SiteConfig,
    BuildingConfig,
    EVFleetConfig,
    EVVehicleTypeConfig,
    GridConfig,
    TariffSchedule,
    load_site_config,
)
from src.core.energy_balance import EnergyBalance, PowerFlows
from src.core.reward import UniversalReward, RewardWeights

__all__ = [
    "SiteConfig",
    "BuildingConfig",
    "EVFleetConfig",
    "EVVehicleTypeConfig",
    "GridConfig",
    "TariffSchedule",
    "load_site_config",
    "EnergyBalance",
    "PowerFlows",
    "UniversalReward",
    "RewardWeights",
]
