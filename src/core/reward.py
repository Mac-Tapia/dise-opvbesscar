"""src.core.reward — Universal multi-objective reward for PVBESS-EV RL agents.

Implements the CO2_DUAL_FOCUS reward model (v8.1 universal) derived from:
  - PVBESSCAR OE3 validated results (Kruskal-Wallis H=81.65, p=1.86e-18)
  - Wali et al. (2025) STET: voltage-based performance metric
  - Nikolay et al. (2025) Nat. Commun. Eng.: user satisfaction formulation

Reward decomposition (all components ∈ [-1, +1]):

    R(t) = Σ_k w_k · r_k(t)    with Σ_k w_k = 1

Components:
    r_co2(t)     CO₂ reduction (indirect: grid displacement)
    r_direct(t)  CO₂ reduction (direct: EV electrification)
    r_ev(t)      EV service satisfaction (charging completeness)
    r_solar(t)   PV self-consumption fraction
    r_grid(t)    Grid stability / ramp smoothing

All weights are configurable per deployment — different sites have different
regulatory priorities (e.g., isolated grids prioritize CO₂ more).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from src.core.energy_balance import PowerFlows


@dataclass
class RewardWeights:
    """Configurable reward weights. Must sum to 1.0.

    Validated weight sets (v8.1 OE3 — siete componentes equilibrados):
        CO2_DUAL_FOCUS v8.1 (Iquitos isolated thermal grid):
            w_direct=0.20 (OE3-1: CO2 directa ICE→EV)
            w_co2=0.30    (OE3-2: CO2 indirecta grid import)
            w_ev=0.35     (OE3-3: satisfaccion/cantidad carga EV)
            w_solar=0.04  (autoconsumo PV)
            w_grid=0.11   (bess_solar_timing=0.07 + grid_stability=0.02 + cost=0.02)
        GRID_CONNECTED (urban, tariff-driven):
            w_direct=0.10, w_co2=0.20, w_ev=0.30, w_solar=0.10, w_grid=0.30
        EV_PRIORITY (dense urban parking):
            w_direct=0.20, w_co2=0.15, w_ev=0.50, w_solar=0.10, w_grid=0.05
    """
    w_direct_co2: float = 0.15   # OE3-1: CO2 directa (EV electrification vs ICE)
    w_co2: float = 0.40          # OE3-2: CO2 indirecta (grid displacement by PV/BESS)
    w_ev: float = 0.25           # OE3-3: EV service satisfaction / quantity charged
    w_solar: float = 0.04        # PV self-consumption
    w_grid: float = 0.15         # grid stability + BESS solar timing + tariff cost
    clip: float = 5.0            # symmetric reward clip per component

    def __post_init__(self) -> None:
        total = self.w_direct_co2 + self.w_co2 + self.w_ev + self.w_solar + self.w_grid
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(
                f"RewardWeights must sum to 1.0, got {total:.6f}. "
                "Adjust weights before instantiating."
            )

    @classmethod
    def co2_dual_focus(cls) -> "RewardWeights":
        """v8.1 OE3: Iquitos isolated thermal grid — direct_co2=0.20, ev_complete=0.35, indirect=0.30."""
        return cls(w_direct_co2=0.20, w_co2=0.30, w_ev=0.35, w_solar=0.04, w_grid=0.11)

    @classmethod
    def grid_connected(cls) -> "RewardWeights":
        """Optimal for urban, tariff-driven deployments with grid stability priority."""
        return cls(w_direct_co2=0.10, w_co2=0.20, w_ev=0.30, w_solar=0.10, w_grid=0.30)

    @classmethod
    def ev_priority(cls) -> "RewardWeights":
        """Optimal for high-density EV parking where service level is paramount."""
        return cls(w_direct_co2=0.20, w_co2=0.15, w_ev=0.50, w_solar=0.10, w_grid=0.05)


class UniversalReward:
    """Computes R(t) = Σ_k w_k · r_k(t) for any site configuration.

    Normalization strategy:
        Each component is normalized to [-1, +1] relative to a per-episode
        baseline derived from the no-control (F₀) scenario.  This ensures reward
        scale is consistent across deployments regardless of fleet size or PV area.

    Usage::
        reward_fn = UniversalReward(weights=RewardWeights.co2_dual_focus(),
                                    ev_demand_baseline_kwh_per_h=50.0,
                                    pv_capacity_kwh_per_h=300.0,
                                    co2_baseline_kg_per_h=22.6)
        r = reward_fn.compute(flows_t, flows_prev)
    """

    def __init__(
        self,
        weights: RewardWeights,
        ev_demand_baseline_kwh_per_h: float,
        pv_capacity_kwh_per_h: float,
        co2_baseline_kg_per_h: float,
        grid_ramp_baseline_kwh: float = 1.0,
        reward_scale: float = 1.0,
    ) -> None:
        self.w = weights
        self._ev_base = max(ev_demand_baseline_kwh_per_h, 1e-9)
        self._pv_cap = max(pv_capacity_kwh_per_h, 1e-9)
        self._co2_base = max(co2_baseline_kg_per_h, 1e-9)
        self._ramp_base = max(grid_ramp_baseline_kwh, 1e-9)
        self.scale = reward_scale

    # ─────────────────────────────────────────────────────────────────────────
    # Component calculators
    # ─────────────────────────────────────────────────────────────────────────

    def _r_direct_co2(self, flows: PowerFlows) -> float:
        """r_direct ∈ [-1, +1]: fraction of maximum direct CO₂ avoided.

        r_direct(t) = CO2_direct_avoided(t) / CO2_baseline(t)
        """
        return min(1.0, flows.co2_avoided_direct_kg / self._co2_base)

    def _r_co2(self, flows: PowerFlows) -> float:
        """r_co2 ∈ [-1, +1]: indirect CO₂ avoided by PV displacing grid.

        r_co2(t) = (CO2_avoided_indirect(t) - CO2_grid(t)) / CO2_baseline(t)
        """
        net = flows.co2_avoided_indirect_kg - flows.co2_grid_kg
        return float(max(-1.0, min(1.0, net / self._co2_base)))

    def _r_ev(self, flows: PowerFlows) -> float:
        """r_ev ∈ [-1, +1]: EV service satisfaction.

        r_ev(t) = EV_served(t) / EV_demand(t) - 1  when demand > 0
               = 0  when no EV demand
        """
        if flows.ev_demand_kwh <= 0:
            return 0.0
        return flows.ev_served_kwh / flows.ev_demand_kwh - 1.0  # ranges [−1, 0]

    def _r_solar(self, flows: PowerFlows) -> float:
        """r_solar ∈ [0, +1]: fraction of PV self-consumed (not curtailed/exported)."""
        return flows.pv_self_consumption_frac

    def _r_grid(self, flows: PowerFlows, prev_grid_import: float) -> float:
        """r_grid ∈ [-1, +1]: penalises large grid ramps (stability).

        r_grid(t) = -|ΔP_grid(t)| / ramp_baseline
        """
        ramp = abs(flows.grid_import_kwh - prev_grid_import)
        return -min(1.0, ramp / self._ramp_base)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def compute(
        self,
        flows: PowerFlows,
        prev_flows: Optional[PowerFlows] = None,
    ) -> float:
        """Compute composite reward for one timestep.

        Args:
            flows:      PowerFlows for timestep t
            prev_flows: PowerFlows for timestep t-1 (for ramp penalty; None → 0 ramp)

        Returns:
            Scalar reward R(t) ∈ [-1, +1] (before scale).
        """
        prev_grid = prev_flows.grid_import_kwh if prev_flows else flows.grid_import_kwh

        r_d   = self._r_direct_co2(flows)
        r_c   = self._r_co2(flows)
        r_e   = self._r_ev(flows)
        r_s   = self._r_solar(flows)
        r_g   = self._r_grid(flows, prev_grid)

        composite = (
            self.w.w_direct_co2 * r_d
            + self.w.w_co2      * r_c
            + self.w.w_ev       * r_e
            + self.w.w_solar    * r_s
            + self.w.w_grid     * r_g
        )
        return float(max(-self.w.clip, min(self.w.clip, composite * self.scale)))

    def component_dict(
        self,
        flows: PowerFlows,
        prev_flows: Optional[PowerFlows] = None,
    ) -> dict:
        """Return all reward components for logging."""
        prev_grid = prev_flows.grid_import_kwh if prev_flows else flows.grid_import_kwh
        return {
            "r_direct_co2": self._r_direct_co2(flows),
            "r_co2":        self._r_co2(flows),
            "r_ev":         self._r_ev(flows),
            "r_solar":      self._r_solar(flows),
            "r_grid":       self._r_grid(flows, prev_grid),
            "R_total":      self.compute(flows, prev_flows),
        }
