"""src.rl.obs_builder — Universal observation vector builder.

Observation space scales automatically with fleet composition:

    obs_dim = 5 (time) + 5 (solar) + 2 (BESS) + 3 (grid) + N_types * 3 (EV per type)

    [0:5]    time features: [month_norm, hour_norm, day_type_norm, hour_sin, hour_cos]
    [5:10]   solar:         [irr_ghi_norm, temp_norm, wind_norm, pv_kw_norm, pv_frac]
    [10:12]  BESS:          [soc_frac, soc_kwh_norm]
    [12:15]  grid:          [grid_import_norm, tariff_norm, co2_intensity_norm]
    [15:15+N_types*3] EV per type i:
               [ev_demand_norm_i, ev_debt_norm_i, ev_satisfaction_i]

This formulation follows EV-GNN (Nat. Commun. Eng. 2025): state encodes per-node
features including energy transferred, elapsed time, and satisfaction.
"""
from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from src.core.site import EVFleetConfig


class ObsBuilder:
    """Builds and normalizes the observation vector for a given fleet config.

    All values clipped to [-obs_clip, +obs_clip] for training stability.
    Normalization uses known physical bounds (not running statistics) to avoid
    distribution shift during deployment at new sites.
    """

    OBS_DIM_BASE = 15  # time(5) + solar(5) + bess(2) + grid(3)
    OBS_DIM_PER_TYPE = 3  # demand_norm, debt_norm, satisfaction

    def __init__(
        self,
        fleet: Optional[EVFleetConfig],
        bess_capacity_kwh: float,
        pv_max_kw: float,
        co2_intensity: float,
        tariff_max: float,
        obs_clip: float = 5.0,
    ) -> None:
        self.fleet = fleet
        self.n_types = fleet.n_vehicle_types if fleet else 0
        self.bess_cap = max(bess_capacity_kwh, 1.0)
        self.pv_max = max(pv_max_kw, 1.0)
        self.co2_ref = max(co2_intensity, 1e-6)
        self.tariff_ref = max(tariff_max, 1e-6)
        self.clip = obs_clip
        self.obs_dim = self.OBS_DIM_BASE + self.n_types * self.OBS_DIM_PER_TYPE

        # Max demand per type for normalization (peak_demand_kw)
        self._ev_max_per_type: List[float] = []
        if fleet:
            for vt in fleet.vehicle_types:
                self._ev_max_per_type.append(max(vt.peak_demand_kw, 1.0))

    def build(
        self,
        timestep: int,
        year: int,
        pv_kw: float,
        irr_ghi: float,
        temp_c: float,
        wind_ms: float,
        bess_soc: float,
        grid_import_kw: float,
        tariff_now: float,
        ev_demand_per_type: List[float],
        ev_debt_per_type: List[float],
        ev_satisfaction_per_type: List[float],
    ) -> np.ndarray:
        """Build normalized observation vector.

        Args:
            timestep: hour index [0, 8759]
            year:     calendar year for date derivation
            pv_kw:    PV generation (kW)
            irr_ghi:  global horizontal irradiance (W/m²)
            temp_c:   ambient temperature (°C)
            wind_ms:  wind speed (m/s)
            bess_soc: BESS state of charge [0, 1]
            grid_import_kw: current grid import (kW)
            tariff_now: current tariff (local currency/kWh)
            ev_demand_per_type: EV demand [kW] per type (N_types)
            ev_debt_per_type:   cumulative unfulfilled demand [kWh] per type
            ev_satisfaction_per_type: satisfaction fraction [0,1] per type

        Returns:
            np.ndarray of shape (obs_dim,)
        """
        import datetime
        base_date = datetime.datetime(year, 1, 1) + datetime.timedelta(hours=timestep)
        month = base_date.month
        hour = base_date.hour
        day_of_week = base_date.weekday()  # 0=Monday, 6=Sunday

        hour_rad = 2 * math.pi * hour / 24
        obs: List[float] = [
            # ── Time features [0:5] ─────────────────────────────────────────
            month / 12.0,
            hour / 23.0,
            day_of_week / 6.0,
            math.sin(hour_rad),
            math.cos(hour_rad),
            # ── Solar features [5:10] ────────────────────────────────────────
            min(irr_ghi / 1200.0, 1.0),       # GHI: max ~1200 W/m²
            min(max(temp_c, -20) + 20, 80) / 80,  # temp: normalize to [0,1]
            min(wind_ms / 20.0, 1.0),          # wind: max 20 m/s
            min(pv_kw / self.pv_max, 1.0),
            min(pv_kw / (self.pv_max + 1e-9), 1.0),  # PV fraction of capacity
            # ── BESS features [10:12] ────────────────────────────────────────
            float(np.clip(bess_soc, 0.0, 1.0)),
            float(np.clip(bess_soc * self.bess_cap / self.bess_cap, 0.0, 1.0)),
            # ── Grid features [12:15] ────────────────────────────────────────
            min(grid_import_kw / (self.pv_max + 1.0), 2.0),
            tariff_now / self.tariff_ref,
            self.co2_ref / self.co2_ref,       # normalized intensity (1.0 at reference)
        ]

        # ── EV features per type [15 : 15+N_types*3] ─────────────────────
        for i in range(self.n_types):
            d_max = self._ev_max_per_type[i]
            obs.append(min(ev_demand_per_type[i] / d_max, 2.0) if i < len(ev_demand_per_type) else 0.0)
            obs.append(min(ev_debt_per_type[i] / d_max, 2.0) if i < len(ev_debt_per_type) else 0.0)
            obs.append(float(np.clip(ev_satisfaction_per_type[i], 0.0, 1.0)) if i < len(ev_satisfaction_per_type) else 1.0)

        arr = np.array(obs, dtype=np.float32)
        return np.clip(arr, -self.clip, self.clip)
