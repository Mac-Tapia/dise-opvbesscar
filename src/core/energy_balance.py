"""src.core.energy_balance — Universal power-balance equations.

Mathematical model derived from:
  Wali et al. (2025) — STET: P_gen + P_grid = P_load + P_bess   [Eq. 2-5]
  IEC 61724-1 — PV system performance monitoring
  EV-GNN (Nat. Commun. Eng. 2025) — fleet demand aggregation

All functions are pure (no state, no I/O) so they can be called in any
environment, tested deterministically, and composed freely.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class PowerFlows:
    """Snapshot of power flows at a single timestep (kWh/h = kW for hourly).

    All values in kWh per 1-hour timestep (= average kW).
    Positive convention:
        pv_kwh          > 0  → generation (always ≥ 0)
        grid_import_kwh > 0  → buying from grid
        grid_export_kwh > 0  → selling to grid
        bess_charge_kwh > 0  → battery absorbing power
        bess_discharge_kwh > 0  → battery delivering power
        ev_demand_kwh   > 0  → EV load (always ≥ 0)
        fixed_load_kwh  > 0  → fixed non-shiftable load (always ≥ 0)
    """
    pv_kwh: float = 0.0
    grid_import_kwh: float = 0.0
    grid_export_kwh: float = 0.0
    bess_charge_kwh: float = 0.0
    bess_discharge_kwh: float = 0.0
    bess_soc_frac: float = 0.5
    ev_demand_kwh: float = 0.0
    ev_served_kwh: float = 0.0         # kWh actually delivered to EVs
    fixed_load_kwh: float = 0.0
    curtailed_kwh: float = 0.0         # PV generation curtailed (spilled)
    co2_grid_kg: float = 0.0           # CO₂ from grid imports
    co2_avoided_direct_kg: float = 0.0  # CO₂ avoided by EV electrification
    co2_avoided_indirect_kg: float = 0.0  # CO₂ avoided by displacing grid

    # Per-vehicle-type breakdowns (aligned with EVFleetConfig.vehicle_types order)
    ev_demand_per_type: List[float] = field(default_factory=list)
    ev_served_per_type: List[float] = field(default_factory=list)

    @property
    def bess_net_kwh(self) -> float:
        """Net BESS flow: positive = discharging (delivering to loads)."""
        return self.bess_discharge_kwh - self.bess_charge_kwh

    @property
    def total_load_kwh(self) -> float:
        return self.ev_served_kwh + self.fixed_load_kwh

    @property
    def balance_error_kwh(self) -> float:
        """Residual of power balance equation (should be ≈ 0)."""
        lhs = self.pv_kwh + self.grid_import_kwh + self.bess_discharge_kwh
        rhs = self.total_load_kwh + self.grid_export_kwh + self.bess_charge_kwh + self.curtailed_kwh
        return lhs - rhs

    @property
    def pv_self_consumption_frac(self) -> float:
        if self.pv_kwh <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.curtailed_kwh / self.pv_kwh))

    @property
    def ev_satisfaction_frac(self) -> float:
        if self.ev_demand_kwh <= 0:
            return 1.0
        return max(0.0, min(1.0, self.ev_served_kwh / self.ev_demand_kwh))


class EnergyBalance:
    """Pure power-balance calculator for a single building / timestep.

    Implements the dispatch priority stack (configurable):
        P1: PV → EV  (maximize direct solar self-consumption)
        P2: PV → BESS  (store surplus for later)
        P3: BESS → EV  (discharge BESS to cover EV demand)
        P4: BESS → Fixed load  (peak shaving during HP)
        P5: Grid → loads  (import only if deficit)
        P6: PV → Grid  (export surplus if allowed)

    The RL agent controls:
        bess_action  ∈ [-1, +1]   (-1=max discharge, +1=max charge)
        ev_frac_i    ∈ [0, 1]     per vehicle type i

    Reference:
        Wali et al. (2025) Eq. 2–11; PVBESSCAR OE2 dispatch rules v5.5
    """

    def __init__(
        self,
        bess_capacity_kwh: float,
        bess_power_kw: float,
        bess_efficiency_roundtrip: float,
        bess_soc_min: float,
        bess_soc_max: float,
        co2_intensity_kg_per_kwh: float,
        co2_avoided_per_type: List[float],
        max_export_kw: Optional[float] = None,
        dt_hours: float = 1.0,
    ) -> None:
        self.e_cap = bess_capacity_kwh
        self.p_max = bess_power_kw
        self.eta = math.sqrt(bess_efficiency_roundtrip)   # split into η_c = η_d = √η_rt
        self.eta_c = self.eta
        self.eta_d = self.eta
        self.soc_min = bess_soc_min
        self.soc_max = bess_soc_max
        self.alpha = co2_intensity_kg_per_kwh
        self.kappa = list(co2_avoided_per_type)          # κ_j per vehicle type
        self.max_export_kw = max_export_kw
        self.dt = dt_hours

    def step(
        self,
        pv_kwh: float,
        ev_demand_per_type: List[float],
        fixed_load_kwh: float,
        bess_soc_prev: float,
        bess_action: float,           # ∈ [-1, +1]
        ev_fracs: List[float],        # ∈ [0, 1] per type
        is_peak_hour: bool = False,
    ) -> PowerFlows:
        """Compute one timestep of energy balance.

        Args:
            pv_kwh:             PV generation this hour (kWh)
            ev_demand_per_type: raw EV demand by vehicle type [kWh] before agent control
            fixed_load_kwh:     non-shiftable load (mall, offices…)
            bess_soc_prev:      BESS SoC at start of timestep [0, 1]
            bess_action:        agent BESS action ∈ [-1, +1]
            ev_fracs:           agent EV allocation fractions per type ∈ [0, 1]
            is_peak_hour:       True if current hour is peak tariff hour

        Returns:
            PowerFlows snapshot for this timestep.
        """
        n = len(ev_demand_per_type)
        if len(ev_fracs) != n:
            raise ValueError(f"ev_fracs length {len(ev_fracs)} ≠ n_types {n}")

        # ── 1. EV load after agent fraction control ────────────────────────
        ev_served_per_type = [
            max(0.0, d * max(0.0, min(1.0, f)))
            for d, f in zip(ev_demand_per_type, ev_fracs)
        ]
        ev_total = sum(ev_served_per_type)
        total_load = ev_total + fixed_load_kwh

        # ── 2. BESS action → requested charge/discharge power ─────────────
        #   bess_action > 0 → charge;  bess_action < 0 → discharge
        requested_bess_kw = float(np.clip(bess_action, -1.0, 1.0)) * self.p_max

        # ── 3. BESS SoC limits ────────────────────────────────────────────
        e_available_discharge = max(0.0, (bess_soc_prev - self.soc_min) * self.e_cap)
        e_available_charge    = max(0.0, (self.soc_max - bess_soc_prev) * self.e_cap)

        if requested_bess_kw >= 0:  # charging
            bess_charge_kwh = min(
                requested_bess_kw * self.dt,
                e_available_charge / self.eta_c,
            )
            bess_discharge_kwh = 0.0
        else:  # discharging
            bess_discharge_kwh = min(
                -requested_bess_kw * self.dt,
                e_available_discharge * self.eta_d,
            )
            bess_charge_kwh = 0.0

        # ── 4. Power balance: PV + BESS_discharge → loads → BESS_charge → grid
        supply = pv_kwh + bess_discharge_kwh
        deficit = max(0.0, total_load + bess_charge_kwh - supply)
        surplus = max(0.0, supply - total_load - bess_charge_kwh)

        grid_import_kwh = deficit
        grid_export_kwh = min(surplus, (self.max_export_kw or math.inf) * self.dt)
        curtailed_kwh   = max(0.0, surplus - grid_export_kwh)

        # ── 5. SoC update ─────────────────────────────────────────────────
        #   ΔE_bess = P_charge × η_c - P_discharge / η_d   (energy INTO battery)
        delta_soc = (bess_charge_kwh * self.eta_c - bess_discharge_kwh / self.eta_d) / max(self.e_cap, 1e-9)
        bess_soc_new = float(np.clip(bess_soc_prev + delta_soc, self.soc_min, self.soc_max))

        # ── 6. CO₂ accounting ─────────────────────────────────────────────
        co2_grid_kg = grid_import_kwh * self.alpha

        # Indirect avoided: every kWh of PV self-consumed → avoids grid CO₂
        pv_self_consumed = pv_kwh - curtailed_kwh - grid_export_kwh
        co2_avoided_indirect_kg = max(0.0, pv_self_consumed * self.alpha)

        # Direct avoided: kWh charged to each EV type × κ_j
        co2_avoided_direct_kg = sum(
            served * kappa
            for served, kappa in zip(ev_served_per_type, self.kappa)
        )

        return PowerFlows(
            pv_kwh=pv_kwh,
            grid_import_kwh=grid_import_kwh,
            grid_export_kwh=grid_export_kwh,
            bess_charge_kwh=bess_charge_kwh,
            bess_discharge_kwh=bess_discharge_kwh,
            bess_soc_frac=bess_soc_new,
            ev_demand_kwh=sum(ev_demand_per_type),
            ev_served_kwh=ev_total,
            fixed_load_kwh=fixed_load_kwh,
            curtailed_kwh=curtailed_kwh,
            co2_grid_kg=co2_grid_kg,
            co2_avoided_direct_kg=co2_avoided_direct_kg,
            co2_avoided_indirect_kg=co2_avoided_indirect_kg,
            ev_demand_per_type=list(ev_demand_per_type),
            ev_served_per_type=ev_served_per_type,
        )
