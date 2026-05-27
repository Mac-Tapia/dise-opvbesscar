"""src.core.site — Universal site, building, and fleet configuration.

All configuration is site-agnostic and validated at instantiation.
Supports any location (lat/lon/tz), any number of buildings, any EV fleet
composition (N vehicle types with different battery sizes and CO₂ factors).

Mathematical references:
  - Energy balance:  P_gen(t) + P_grid(t) = Σ_i P_load_i(t) + P_bess(t)
    (Wali et al., STET 2025, Eq. 2-5)
  - PV model:        P_pv(t) = η_inv × G(t) × A_pv × η_panel
    (IEC 61724-1)
  - BESS model:      SoC(t+1) = SoC(t) + P_bess(t)·η_bess / E_cap
    (Wali et al., STET 2025, Eq. 7)
  - Fleet demand:    P_ev(t) = Σ_{j=1}^{N} P_evj(t)
    (Bottieau et al., 2025, Eq. 1; EV-GNN, Nat. Commun. Eng. 2025)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# TARIFF SCHEDULE
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TariffSchedule:
    """Electricity tariff with peak / off-peak differentiation.

    Any grid worldwide can be represented with two time-of-use periods.
    More complex tariffs (e.g., 3-period) can be encoded by splitting blocks.
    """
    peak_rate_local_per_kwh: float       # tariff during peak hours (local currency/kWh)
    offpeak_rate_local_per_kwh: float    # tariff off-peak
    peak_hours_start: int = 18           # inclusive, 0-23
    peak_hours_end: int = 22             # inclusive, 0-23
    currency: str = "PEN"                # ISO 4217 (PEN, USD, EUR, …)
    exchange_rate_to_usd: float = 1.0    # local_currency / USD

    def __post_init__(self) -> None:
        if not (0 <= self.peak_hours_start <= 23):
            raise ValueError(f"peak_hours_start must be 0-23, got {self.peak_hours_start}")
        if not (0 <= self.peak_hours_end <= 23):
            raise ValueError(f"peak_hours_end must be 0-23, got {self.peak_hours_end}")
        if self.peak_rate_local_per_kwh <= 0:
            raise ValueError("peak_rate must be positive")
        if self.offpeak_rate_local_per_kwh <= 0:
            raise ValueError("offpeak_rate must be positive")

    @property
    def peak_hours(self) -> List[int]:
        return list(range(self.peak_hours_start, self.peak_hours_end + 1))

    def rate_at(self, hour: int) -> float:
        return self.peak_rate_local_per_kwh if hour in self.peak_hours else self.offpeak_rate_local_per_kwh

    def rate_usd_at(self, hour: int) -> float:
        return self.rate_at(hour) / self.exchange_rate_to_usd


# ──────────────────────────────────────────────────────────────────────────────
# GRID CONFIG
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class GridConfig:
    """Electrical grid connection parameters for any deployment location.

    co2_intensity_kg_per_kwh varies by country/region:
      - Iquitos (isolated thermal, diesel): 0.4521
      - Perú SIN (hydro mix):               0.2300
      - Chile:                               0.3100
      - Spain:                               0.1600
      - Coal-heavy grid (India):             0.7500
    """
    co2_intensity_kg_per_kwh: float      # kg CO₂ / kWh imported from grid
    tariff: TariffSchedule
    max_import_kw: Optional[float] = None   # grid capacity limit (None = unlimited)
    max_export_kw: Optional[float] = None   # export limit (None = no export)
    grid_type: str = "connected"             # "connected" | "isolated" | "microgrid"

    def __post_init__(self) -> None:
        if self.co2_intensity_kg_per_kwh < 0:
            raise ValueError("co2_intensity cannot be negative")


# ──────────────────────────────────────────────────────────────────────────────
# EV VEHICLE TYPE
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EVVehicleTypeConfig:
    """Specification for ONE vehicle type in the fleet.

    Supports heterogeneous fleets: motorcycles, cars, buses, trucks, …
    Each type has its own battery size, charger power, and CO₂ avoidance factor.

    CO₂ avoidance factor κ (kg CO₂/kWh) represents the net CO₂ avoided per kWh
    of electricity delivered to this vehicle type, compared to its fossil fuel
    equivalent:
        κ = (km_per_liter × co2_per_liter) / (km_per_kwh × 1000)
    (IPCC 2021; MINEM Perú emission factors)

    Reference fleets used for validation:
      - Iquitos motos:      κ = 0.87, battery = 1.5 kWh, charger = 7.4 kW
      - Iquitos mototaxis:  κ = 0.54, battery = 3.0 kWh, charger = 7.4 kW
      - Lima car:           κ = 0.32, battery = 40 kWh,  charger = 22 kW
    """
    name: str                              # e.g. "moto", "car", "bus"
    vehicle_count: int                     # total vehicles of this type in fleet
    battery_kwh: float                     # usable battery capacity per vehicle
    charger_power_kw: float                # rated charger power (AC)
    co2_avoided_kg_per_kwh: float          # κ_j: CO₂ avoidance factor
    sockets_per_charger: int = 2           # number of EVs per physical charger
    avg_daily_sessions: float = 1.0        # average charging sessions per vehicle/day
    session_energy_kwh: Optional[float] = None  # avg kWh per session (None → battery_kwh × 0.5)
    peak_hours_share: float = 0.5          # fraction of sessions during peak hours
    utilization_factor: float = 0.85       # fraction of fleet active on a given day

    def __post_init__(self) -> None:
        if self.vehicle_count <= 0:
            raise ValueError(f"vehicle_count must be > 0 for type '{self.name}'")
        if self.battery_kwh <= 0:
            raise ValueError(f"battery_kwh must be > 0 for type '{self.name}'")
        if not (0 < self.utilization_factor <= 1):
            raise ValueError(f"utilization_factor must be in (0,1] for type '{self.name}'")
        if not (0 <= self.peak_hours_share <= 1):
            raise ValueError("peak_hours_share must be in [0,1]")
        if self.session_energy_kwh is None:
            object.__setattr__(self, "session_energy_kwh", self.battery_kwh * 0.5)

    @property
    def n_chargers(self) -> int:
        return math.ceil(self.vehicle_count / self.sockets_per_charger)

    @property
    def peak_demand_kw(self) -> float:
        return self.n_chargers * self.charger_power_kw


# ──────────────────────────────────────────────────────────────────────────────
# EV FLEET CONFIG
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EVFleetConfig:
    """Heterogeneous EV fleet: any number of vehicle types, any total size.

    The fleet is the controlled load — the RL agent allocates charging fractions
    independently per vehicle type: a_ev_i ∈ [0, 1].

    No hard limit on fleet size. Action space dimension scales with len(vehicle_types).
    """
    vehicle_types: List[EVVehicleTypeConfig]
    opening_hour: int = 8
    closing_hour: int = 22

    def __post_init__(self) -> None:
        if not self.vehicle_types:
            raise ValueError("EVFleetConfig must have at least one vehicle type")
        names = [v.name for v in self.vehicle_types]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate vehicle type names: {names}")

    @property
    def total_vehicles(self) -> int:
        return sum(v.vehicle_count for v in self.vehicle_types)

    @property
    def total_chargers(self) -> int:
        return sum(v.n_chargers for v in self.vehicle_types)

    @property
    def total_sockets(self) -> int:
        return sum(v.n_chargers * v.sockets_per_charger for v in self.vehicle_types)

    @property
    def peak_demand_kw(self) -> float:
        return sum(v.peak_demand_kw for v in self.vehicle_types)

    @property
    def n_vehicle_types(self) -> int:
        return len(self.vehicle_types)


# ──────────────────────────────────────────────────────────────────────────────
# BUILDING CONFIG
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BuildingConfig:
    """One building / parking site with PV, BESS, EV fleet, and fixed load.

    Mathematical energy balance at each timestep t (hourly):

        P_pv(t) + P_grid(t) = P_bess_net(t) + P_ev(t) + P_fixed(t)

        P_bess_net(t) = P_bess_discharge(t) - P_bess_charge(t)

        SoC(t+1) = SoC(t) + [P_bess_charge(t)·η_c - P_bess_discharge(t)/η_d] / E_cap
                   s.t.  SoC_min ≤ SoC(t) ≤ SoC_max

    All physical quantities can be configured per building.
    Multiple BuildingConfig instances → multi-building / multi-site deployment.
    """
    name: str

    # ── PV system ──────────────────────────────────────────────────────────
    pv_area_m2: float                  # available rooftop area
    pv_panel_efficiency: float = 0.20  # η_panel (typical mono-Si: 0.18–0.22)
    pv_surface_tilt_deg: float = 10.0  # tilt from horizontal (°)
    pv_surface_azimuth_deg: float = 0.0  # 0=South, 90=West (pvlib convention)
    pv_coverage_fraction: float = 0.65   # fraction of roof usable for panels
    pv_inverter_efficiency: float = 0.97
    pv_system_losses: float = 0.14       # soiling, wiring, mismatch (IEC 61724)

    # ── BESS ────────────────────────────────────────────────────────────────
    bess_capacity_kwh: float = 0.0     # 0 = no BESS
    bess_power_kw: float = 0.0
    bess_dod: float = 0.80             # depth of discharge
    bess_efficiency_roundtrip: float = 0.95
    bess_soc_min: float = 0.20
    bess_soc_max: float = 1.00
    bess_initial_soc: float = 0.50

    # ── EV fleet ────────────────────────────────────────────────────────────
    ev_fleet: Optional[EVFleetConfig] = None  # None = no EV charging

    # ── Fixed loads ─────────────────────────────────────────────────────────
    fixed_load_kw: float = 0.0        # constant background load (mall, offices…)
    fixed_load_profile_csv: Optional[str] = None  # path to 8760-row CSV (overrides fixed_load_kw)

    def __post_init__(self) -> None:
        if self.pv_area_m2 < 0:
            raise ValueError(f"[{self.name}] pv_area_m2 must be ≥ 0")
        if not (0 < self.pv_panel_efficiency < 1):
            raise ValueError(f"[{self.name}] pv_panel_efficiency must be in (0,1)")
        if self.bess_capacity_kwh < 0:
            raise ValueError(f"[{self.name}] bess_capacity_kwh must be ≥ 0")
        if self.bess_soc_min >= self.bess_soc_max:
            raise ValueError(f"[{self.name}] bess_soc_min ({self.bess_soc_min}) must be < bess_soc_max ({self.bess_soc_max})")

    @property
    def pv_installed_kwp(self) -> float:
        usable_area = self.pv_area_m2 * self.pv_coverage_fraction
        return usable_area * self.pv_panel_efficiency * (1.0 - self.pv_system_losses)

    @property
    def bess_usable_kwh(self) -> float:
        return self.bess_capacity_kwh * self.bess_dod

    @property
    def has_bess(self) -> bool:
        return self.bess_capacity_kwh > 0 and self.bess_power_kw > 0

    @property
    def has_ev(self) -> bool:
        return self.ev_fleet is not None


# ──────────────────────────────────────────────────────────────────────────────
# SITE CONFIG (top-level)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SiteConfig:
    """Complete site specification — the single source of truth for any deployment.

    A "site" is a geographic location with one or more buildings, a shared grid
    connection, and a shared climate (solar irradiance, temperature).

    Examples:
      - Single building (Iquitos BESS Mall): 1 building, 1 fleet, isolated grid
      - Multi-building campus: N buildings, shared PV/BESS, shared grid
      - Urban deployment: K sites in a city, each self-contained
    """
    site_id: str                        # unique identifier (slug, e.g. "iquitos_mall_2024")
    name: str                           # human-readable name
    description: str = ""

    # ── Location ────────────────────────────────────────────────────────────
    latitude: float = 0.0              # decimal degrees (−90 to +90)
    longitude: float = 0.0             # decimal degrees (−180 to +180)
    altitude_m: float = 0.0
    timezone: str = "UTC"              # IANA timezone (e.g. "America/Lima")
    year: int = 2024

    # ── Grid ────────────────────────────────────────────────────────────────
    grid: Optional[GridConfig] = None

    # ── Buildings ───────────────────────────────────────────────────────────
    buildings: List[BuildingConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.site_id:
            raise ValueError("site_id must not be empty")
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")
        if not self.buildings:
            raise ValueError(f"Site '{self.site_id}' must have at least one building")

    @property
    def n_buildings(self) -> int:
        return len(self.buildings)

    @property
    def total_pv_kwp(self) -> float:
        return sum(b.pv_installed_kwp for b in self.buildings)

    @property
    def total_bess_kwh(self) -> float:
        return sum(b.bess_capacity_kwh for b in self.buildings)

    @property
    def total_ev_vehicles(self) -> int:
        return sum(b.ev_fleet.total_vehicles for b in self.buildings if b.has_ev)

    @property
    def all_vehicle_types(self) -> List[str]:
        types: List[str] = []
        for b in self.buildings:
            if b.has_ev:
                for vt in b.ev_fleet.vehicle_types:
                    if vt.name not in types:
                        types.append(vt.name)
        return types


# ──────────────────────────────────────────────────────────────────────────────
# YAML LOADER — parse any site config file
# ──────────────────────────────────────────────────────────────────────────────

def _parse_tariff(d: Dict[str, Any]) -> TariffSchedule:
    return TariffSchedule(
        peak_rate_local_per_kwh=float(d["peak_rate_local_per_kwh"]),
        offpeak_rate_local_per_kwh=float(d["offpeak_rate_local_per_kwh"]),
        peak_hours_start=int(d.get("peak_hours_start", 18)),
        peak_hours_end=int(d.get("peak_hours_end", 22)),
        currency=str(d.get("currency", "PEN")),
        exchange_rate_to_usd=float(d.get("exchange_rate_to_usd", 1.0)),
    )


def _parse_grid(d: Dict[str, Any]) -> GridConfig:
    return GridConfig(
        co2_intensity_kg_per_kwh=float(d["co2_intensity_kg_per_kwh"]),
        tariff=_parse_tariff(d["tariff"]),
        max_import_kw=d.get("max_import_kw"),
        max_export_kw=d.get("max_export_kw"),
        grid_type=str(d.get("grid_type", "connected")),
    )


def _parse_vehicle_type(d: Dict[str, Any]) -> EVVehicleTypeConfig:
    return EVVehicleTypeConfig(
        name=str(d["name"]),
        vehicle_count=int(d["vehicle_count"]),
        battery_kwh=float(d["battery_kwh"]),
        charger_power_kw=float(d["charger_power_kw"]),
        co2_avoided_kg_per_kwh=float(d["co2_avoided_kg_per_kwh"]),
        sockets_per_charger=int(d.get("sockets_per_charger", 2)),
        avg_daily_sessions=float(d.get("avg_daily_sessions", 1.0)),
        session_energy_kwh=d.get("session_energy_kwh"),
        peak_hours_share=float(d.get("peak_hours_share", 0.5)),
        utilization_factor=float(d.get("utilization_factor", 0.85)),
    )


def _parse_ev_fleet(d: Dict[str, Any]) -> EVFleetConfig:
    return EVFleetConfig(
        vehicle_types=[_parse_vehicle_type(vt) for vt in d["vehicle_types"]],
        opening_hour=int(d.get("opening_hour", 8)),
        closing_hour=int(d.get("closing_hour", 22)),
    )


def _parse_building(d: Dict[str, Any]) -> BuildingConfig:
    return BuildingConfig(
        name=str(d["name"]),
        pv_area_m2=float(d["pv_area_m2"]),
        pv_panel_efficiency=float(d.get("pv_panel_efficiency", 0.20)),
        pv_surface_tilt_deg=float(d.get("pv_surface_tilt_deg", 10.0)),
        pv_surface_azimuth_deg=float(d.get("pv_surface_azimuth_deg", 0.0)),
        pv_coverage_fraction=float(d.get("pv_coverage_fraction", 0.65)),
        pv_inverter_efficiency=float(d.get("pv_inverter_efficiency", 0.97)),
        pv_system_losses=float(d.get("pv_system_losses", 0.14)),
        bess_capacity_kwh=float(d.get("bess_capacity_kwh", 0.0)),
        bess_power_kw=float(d.get("bess_power_kw", 0.0)),
        bess_dod=float(d.get("bess_dod", 0.80)),
        bess_efficiency_roundtrip=float(d.get("bess_efficiency_roundtrip", 0.95)),
        bess_soc_min=float(d.get("bess_soc_min", 0.20)),
        bess_soc_max=float(d.get("bess_soc_max", 1.00)),
        bess_initial_soc=float(d.get("bess_initial_soc", 0.50)),
        ev_fleet=_parse_ev_fleet(d["ev_fleet"]) if "ev_fleet" in d else None,
        fixed_load_kw=float(d.get("fixed_load_kw", 0.0)),
        fixed_load_profile_csv=d.get("fixed_load_profile_csv"),
    )


def load_site_config(path: str | Path) -> SiteConfig:
    """Load and validate a SiteConfig from a YAML file.

    Args:
        path: Path to site YAML file (configs/sites/*.yaml)

    Returns:
        Validated SiteConfig ready for use in OE2 generators and OE3 environment.

    Raises:
        ValueError:  if required fields missing or invalid
        FileNotFoundError: if file not found
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Site config not found: {path}")
    with open(path, encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f)

    return SiteConfig(
        site_id=str(raw["site_id"]),
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        latitude=float(raw["latitude"]),
        longitude=float(raw["longitude"]),
        altitude_m=float(raw.get("altitude_m", 0.0)),
        timezone=str(raw.get("timezone", "UTC")),
        year=int(raw.get("year", 2024)),
        grid=_parse_grid(raw["grid"]) if "grid" in raw else None,
        buildings=[_parse_building(b) for b in raw.get("buildings", [])],
    )
