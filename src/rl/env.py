"""src.rl.env — UniversalPVBESSEnv: site-agnostic Gymnasium environment.

This environment can be instantiated for ANY site worldwide by passing a
SiteConfig and pre-loaded timeseries DataFrames.  No Iquitos-specific logic.

Observation space:
    Box(obs_dim,) where obs_dim = 15 + N_vehicle_types * 3
    (scales automatically with fleet composition)

Action space:
    Box(1 + N_vehicle_types,) — [bess_action, ev_frac_type_0, …, ev_frac_type_N]
    bess_action ∈ [-1, +1]:  -1=max discharge, +1=max charge
    ev_frac_i   ∈ [0, 1]:   fraction of type-i demand to serve this hour

Mathematical model:
    Energy balance:  EnergyBalance.step() — Wali et al. (2025) Eq. 2-11
    Reward:          UniversalReward.compute() — CO2_DUAL_FOCUS v8.0
    Observation:     ObsBuilder.build() — EV-GNN feature encoding (2025)

References:
    [1] Wali et al. (2025) STET — xEV hybrid microgrid energy management
    [2] Nikolay et al. (2025) Nature Commun. Eng. — EV-GNN scalable RL
    [3] Vazquez-Canteli et al. (2021) CityLearn — MARL building energy
    [4] PVBESSCAR OE3 validated results (SAC, 50 eps, Iquitos 2024)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    _GYM_AVAILABLE = True
except ImportError:
    try:
        import gym  # type: ignore
        from gym import spaces  # type: ignore
        _GYM_AVAILABLE = True
    except ImportError:
        _GYM_AVAILABLE = False
        gym = None  # type: ignore
        spaces = None  # type: ignore

from src.core.site import BuildingConfig, SiteConfig
from src.core.energy_balance import EnergyBalance, PowerFlows
from src.core.reward import RewardWeights, UniversalReward
from src.rl.obs_builder import ObsBuilder


class UniversalPVBESSEnv:
    """Gymnasium-compatible environment for any PVBESS-EV site.

    Can wrap a single building or aggregate multiple buildings from one SiteConfig.

    Usage::
        cfg = load_site_config("configs/sites/iquitos_bess_mall.yaml")
        env = UniversalPVBESSEnv.from_site_config(cfg, solar_df, ev_df, mall_df)
        obs, info = env.reset()
        obs, reward, terminated, truncated, info = env.step(action)

    DataFrames must have 8760 rows (hourly, one year):
        solar_df:  columns [potencia_kw, irradiancia_ghi, temperatura_c, velocidad_viento_ms]
        ev_df:     one column per vehicle type name matching EVVehicleTypeConfig.name
                   e.g. {"moto": Series(8760), "mototaxi": Series(8760)}
        mall_df:   columns [mall_demand_kwh]  (fixed load)
    """

    def __init__(
        self,
        building: BuildingConfig,
        pv_timeseries: np.ndarray,          # shape (8760,) — PV kW per hour
        irr_timeseries: np.ndarray,         # shape (8760,) — GHI W/m²
        temp_timeseries: np.ndarray,        # shape (8760,) — °C
        wind_timeseries: np.ndarray,        # shape (8760,) — m/s
        ev_demand_timeseries: np.ndarray,   # shape (8760, N_types) — kWh/h per type
        fixed_load_timeseries: np.ndarray,  # shape (8760,) — kWh/h
        reward_weights: Optional[RewardWeights] = None,
        site_config: Optional[SiteConfig] = None,
        max_episode_steps: int = 8760,
        seed: int = 42,
    ) -> None:
        self.building = building
        self.cfg = site_config
        self.n_hours = 8760
        self.max_steps = min(max_episode_steps, self.n_hours)

        # ── Timeseries ──────────────────────────────────────────────────────
        self._pv = np.asarray(pv_timeseries, dtype=np.float32)
        self._irr = np.asarray(irr_timeseries, dtype=np.float32)
        self._temp = np.asarray(temp_timeseries, dtype=np.float32)
        self._wind = np.asarray(wind_timeseries, dtype=np.float32)
        self._ev = np.asarray(ev_demand_timeseries, dtype=np.float32)
        if self._ev.ndim == 1:
            self._ev = self._ev[:, np.newaxis]
        self._fixed = np.asarray(fixed_load_timeseries, dtype=np.float32)

        self.n_types = self._ev.shape[1]
        self.fleet = building.ev_fleet

        # ── Physics ─────────────────────────────────────────────────────────
        co2_avoided = (
            [vt.co2_avoided_kg_per_kwh for vt in self.fleet.vehicle_types]
            if self.fleet else [0.0] * self.n_types
        )
        tariff_grid = site_config.grid if site_config else None
        co2_intensity = tariff_grid.co2_intensity_kg_per_kwh if tariff_grid else 0.4521
        max_tariff = (
            tariff_grid.tariff.peak_rate_local_per_kwh if tariff_grid else 0.45
        )

        self.balance = EnergyBalance(
            bess_capacity_kwh=building.bess_capacity_kwh,
            bess_power_kw=building.bess_power_kw,
            bess_efficiency_roundtrip=building.bess_efficiency_roundtrip,
            bess_soc_min=building.bess_soc_min,
            bess_soc_max=building.bess_soc_max,
            co2_intensity_kg_per_kwh=co2_intensity,
            co2_avoided_per_type=co2_avoided,
        )

        # ── Reward ──────────────────────────────────────────────────────────
        w = reward_weights or RewardWeights.co2_dual_focus()
        ev_base = float(self._ev.sum(axis=1).mean()) if self._ev.size > 0 else 1.0
        pv_max = float(self._pv.max()) if self._pv.size > 0 else 1.0
        co2_base = ev_base * co2_intensity
        self.reward_fn = UniversalReward(
            weights=w,
            ev_demand_baseline_kwh_per_h=ev_base,
            pv_capacity_kwh_per_h=pv_max,
            co2_baseline_kg_per_h=co2_base,
        )

        # ── Observation builder ──────────────────────────────────────────────
        self.obs_builder = ObsBuilder(
            fleet=self.fleet,
            bess_capacity_kwh=building.bess_capacity_kwh,
            pv_max_kw=pv_max,
            co2_intensity=co2_intensity,
            tariff_max=max_tariff,
        )
        self.obs_dim = self.obs_builder.obs_dim
        self.action_dim = 1 + self.n_types

        # ── Gym spaces ───────────────────────────────────────────────────────
        if _GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=-5.0, high=5.0, shape=(self.obs_dim,), dtype=np.float32
            )
            action_low = np.array([-1.0] + [0.0] * self.n_types, dtype=np.float32)
            action_high = np.array([1.0] + [1.0] * self.n_types, dtype=np.float32)
            self.action_space = spaces.Box(low=action_low, high=action_high, dtype=np.float32)

        # ── State ────────────────────────────────────────────────────────────
        self._rng = np.random.default_rng(seed)
        self._t: int = 0
        self._soc: float = building.bess_initial_soc
        self._ev_debt: List[float] = [0.0] * self.n_types
        self._ev_served_total: List[float] = [0.0] * self.n_types
        self._ev_demand_total: List[float] = [0.0] * self.n_types
        self._prev_flows: Optional[PowerFlows] = None
        self._year = site_config.year if site_config else 2024

    # ─────────────────────────────────────────────────────────────────────────

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._t = 0
        self._soc = self.building.bess_initial_soc
        self._ev_debt = [0.0] * self.n_types
        self._ev_served_total = [0.0] * self.n_types
        self._ev_demand_total = [0.0] * self.n_types
        self._prev_flows = None
        return self._obs(), {}

    def step(
        self, action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        t = self._t
        action = np.asarray(action, dtype=np.float32)
        bess_action = float(np.clip(action[0], -1.0, 1.0))
        ev_fracs = [float(np.clip(action[1 + i], 0.0, 1.0)) for i in range(self.n_types)]

        pv = float(self._pv[t])
        irr = float(self._irr[t])
        temp = float(self._temp[t])
        wind = float(self._wind[t])
        ev_demand = [float(self._ev[t, i]) for i in range(self.n_types)]
        fixed = float(self._fixed[t])

        tariff_obj = self.cfg.grid.tariff if (self.cfg and self.cfg.grid) else None
        hour = t % 24
        is_peak = bool(tariff_obj and hour in tariff_obj.peak_hours)
        tariff_now = float(tariff_obj.rate_at(hour) if tariff_obj else 0.28)

        flows = self.balance.step(
            pv_kwh=pv,
            ev_demand_per_type=ev_demand,
            fixed_load_kwh=fixed,
            bess_soc_prev=self._soc,
            bess_action=bess_action,
            ev_fracs=ev_fracs,
            is_peak_hour=is_peak,
        )

        reward = self.reward_fn.compute(flows, self._prev_flows)
        self._soc = flows.bess_soc_frac

        for i in range(self.n_types):
            d = ev_demand[i] if i < len(ev_demand) else 0.0
            s = flows.ev_served_per_type[i] if i < len(flows.ev_served_per_type) else 0.0
            self._ev_demand_total[i] += d
            self._ev_served_total[i] += s
            self._ev_debt[i] = max(0.0, self._ev_debt[i] + d - s)

        self._prev_flows = flows
        self._t += 1
        terminated = self._t >= self.max_steps
        truncated = False

        ev_sat = [
            (self._ev_served_total[i] / max(self._ev_demand_total[i], 1e-9))
            for i in range(self.n_types)
        ]

        info: Dict[str, Any] = {
            "t": t,
            "pv_kwh": flows.pv_kwh,
            "bess_soc": self._soc,
            "grid_import_kwh": flows.grid_import_kwh,
            "ev_satisfaction": ev_sat,
            "co2_avoided_kg": flows.co2_avoided_direct_kg + flows.co2_avoided_indirect_kg,
            "reward_components": self.reward_fn.component_dict(flows, self._prev_flows),
        }
        return self._obs(), reward, terminated, truncated, info

    def _obs(self) -> np.ndarray:
        t = min(self._t, self.n_hours - 1)
        tariff_obj = self.cfg.grid.tariff if (self.cfg and self.cfg.grid) else None
        hour = t % 24
        tariff_now = float(tariff_obj.rate_at(hour) if tariff_obj else 0.28)
        ev_demand = [float(self._ev[t, i]) for i in range(self.n_types)]
        ev_sat = [
            float(self._ev_served_total[i] / max(self._ev_demand_total[i], 1e-9))
            for i in range(self.n_types)
        ]
        return self.obs_builder.build(
            timestep=t,
            year=self._year,
            pv_kw=float(self._pv[t]),
            irr_ghi=float(self._irr[t]),
            temp_c=float(self._temp[t]),
            wind_ms=float(self._wind[t]),
            bess_soc=self._soc,
            grid_import_kw=self._prev_flows.grid_import_kwh if self._prev_flows else 0.0,
            tariff_now=tariff_now,
            ev_demand_per_type=ev_demand,
            ev_debt_per_type=self._ev_debt,
            ev_satisfaction_per_type=ev_sat,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Factory: build from SiteConfig + DataFrames
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def from_dataframes(
        cls,
        site: SiteConfig,
        building_idx: int,
        solar_df,
        ev_dfs: Dict[str, Any],
        fixed_load_df,
        reward_weights: Optional[RewardWeights] = None,
        **kwargs,
    ) -> "UniversalPVBESSEnv":
        """Construct environment from a SiteConfig and pre-loaded DataFrames.

        Args:
            site:          validated SiteConfig
            building_idx:  index into site.buildings
            solar_df:      DataFrame with [potencia_kw, irradiancia_ghi, temperatura_c, velocidad_viento_ms]
            ev_dfs:        dict {vehicle_type_name: Series(8760)} — demand per type
            fixed_load_df: DataFrame or Series with [mall_demand_kwh]
            reward_weights: optional, defaults to CO2_DUAL_FOCUS

        Returns:
            Ready-to-use UniversalPVBESSEnv instance.
        """
        import pandas as pd

        building = site.buildings[building_idx]
        fleet = building.ev_fleet

        pv = solar_df["potencia_kw"].to_numpy(dtype=np.float32)
        irr = solar_df["irradiancia_ghi"].to_numpy(dtype=np.float32)
        temp = solar_df["temperatura_c"].to_numpy(dtype=np.float32)
        wind = solar_df["velocidad_viento_ms"].to_numpy(dtype=np.float32)

        n_types = fleet.n_vehicle_types if fleet else 0
        if n_types > 0:
            ev_cols = [ev_dfs[vt.name].to_numpy(dtype=np.float32) for vt in fleet.vehicle_types]
            ev_arr = np.column_stack(ev_cols)
        else:
            ev_arr = np.zeros((8760, 1), dtype=np.float32)

        if isinstance(fixed_load_df, pd.DataFrame):
            fixed = fixed_load_df["mall_demand_kwh"].to_numpy(dtype=np.float32)
        else:
            fixed = np.asarray(fixed_load_df, dtype=np.float32)

        return cls(
            building=building,
            pv_timeseries=pv,
            irr_timeseries=irr,
            temp_timeseries=temp,
            wind_timeseries=wind,
            ev_demand_timeseries=ev_arr,
            fixed_load_timeseries=fixed,
            reward_weights=reward_weights,
            site_config=site,
            **kwargs,
        )
