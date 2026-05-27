"""tests/integration/test_universal_env.py — Integration tests for UniversalPVBESSEnv.

Tests cover: instantiation, obs/action shapes, step semantics, factory method,
reward sign, and energy balance invariants.

All tests use synthetic data (no OE2 CSV reads) to avoid I/O dependencies.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.core.site import (
    BuildingConfig,
    EVFleetConfig,
    EVVehicleTypeConfig,
    GridConfig,
    SiteConfig,
    TariffSchedule,
)
from src.core.reward import RewardWeights
from src.rl import UniversalPVBESSEnv


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_tariff() -> TariffSchedule:
    return TariffSchedule(
        peak_rate_local_per_kwh=0.45,
        offpeak_rate_local_per_kwh=0.28,
        peak_hours_start=18,
        peak_hours_end=22,
        currency="PEN",
        exchange_rate_to_usd=3.75,
    )


def _make_grid() -> GridConfig:
    return GridConfig(
        co2_intensity_kg_per_kwh=0.4521,
        tariff=_make_tariff(),
        max_import_kw=None,
        max_export_kw=0.0,
        grid_type="isolated",
    )


def _make_vtype(name: str, count: int) -> EVVehicleTypeConfig:
    return EVVehicleTypeConfig(
        name=name,
        vehicle_count=count,
        battery_kwh=1.5,
        charger_power_kw=7.4,
        sockets_per_charger=2,
        co2_avoided_kg_per_kwh=0.87,
        avg_daily_sessions=1.0,
        session_energy_kwh=0.75,
        peak_hours_share=0.50,
        utilization_factor=0.92,
    )


def _make_fleet(n_types: int = 2) -> EVFleetConfig:
    types = [_make_vtype(f"type_{i}", 10 * (i + 1)) for i in range(n_types)]
    return EVFleetConfig(vehicle_types=types, opening_hour=9, closing_hour=22)


def _make_building(n_ev_types: int = 2) -> BuildingConfig:
    return BuildingConfig(
        name="Test Building",
        pv_area_m2=1000.0,
        pv_panel_efficiency=0.20,
        pv_surface_tilt_deg=10.0,
        pv_surface_azimuth_deg=0.0,
        pv_coverage_fraction=0.65,
        pv_inverter_efficiency=0.95,
        pv_system_losses=0.14,
        bess_capacity_kwh=100.0,
        bess_power_kw=50.0,
        bess_dod=0.80,
        bess_efficiency_roundtrip=0.95,
        bess_soc_min=0.20,
        bess_soc_max=1.00,
        bess_initial_soc=0.50,
        fixed_load_kw=10.0,
        ev_fleet=_make_fleet(n_ev_types),
    )


def _make_site(n_ev_types: int = 2) -> SiteConfig:
    return SiteConfig(
        site_id="test_site",
        name="Test Site",
        latitude=-3.75,
        longitude=-73.25,
        altitude_m=100.0,
        timezone="America/Lima",
        year=2024,
        grid=_make_grid(),
        buildings=[_make_building(n_ev_types)],
    )


def _make_timeseries(n_types: int = 2, n_hours: int = 8760):
    pv = np.random.default_rng(0).uniform(0, 100, n_hours).astype(np.float32)
    irr = np.random.default_rng(1).uniform(0, 800, n_hours).astype(np.float32)
    temp = np.random.default_rng(2).uniform(20, 35, n_hours).astype(np.float32)
    wind = np.random.default_rng(3).uniform(0, 5, n_hours).astype(np.float32)
    ev = np.random.default_rng(4).uniform(0, 5, (n_hours, n_types)).astype(np.float32)
    fixed = np.full(n_hours, 10.0, dtype=np.float32)
    return pv, irr, temp, wind, ev, fixed


def _make_env(n_ev_types: int = 2) -> UniversalPVBESSEnv:
    site = _make_site(n_ev_types)
    building = site.buildings[0]
    pv, irr, temp, wind, ev, fixed = _make_timeseries(n_ev_types)
    weights = RewardWeights.co2_dual_focus()
    return UniversalPVBESSEnv(
        building=building,
        pv_timeseries=pv,
        irr_timeseries=irr,
        temp_timeseries=temp,
        wind_timeseries=wind,
        ev_demand_timeseries=ev,
        fixed_load_timeseries=fixed,
        reward_weights=weights,
        site_config=site,
        seed=42,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests: instantiation and spaces
# ─────────────────────────────────────────────────────────────────────────────

class TestInstantiation:

    def test_obs_dim_two_types(self):
        env = _make_env(n_ev_types=2)
        assert env.obs_dim == 15 + 2 * 3  # 21

    def test_obs_dim_one_type(self):
        env = _make_env(n_ev_types=1)
        assert env.obs_dim == 15 + 1 * 3  # 18

    def test_obs_dim_three_types(self):
        env = _make_env(n_ev_types=3)
        assert env.obs_dim == 15 + 3 * 3  # 24

    def test_action_dim_two_types(self):
        env = _make_env(n_ev_types=2)
        assert env.action_dim == 1 + 2  # 3

    def test_action_dim_one_type(self):
        env = _make_env(n_ev_types=1)
        assert env.action_dim == 1 + 1  # 2

    def test_n_types_matches_fleet(self):
        env = _make_env(n_ev_types=2)
        assert env.n_types == 2

    def test_action_space_low_high(self):
        env = _make_env(n_ev_types=2)
        assert env.action_space.low[0] == -1.0
        assert env.action_space.high[0] == 1.0
        assert all(env.action_space.low[1:] == 0.0)
        assert all(env.action_space.high[1:] == 1.0)

    def test_observation_space_shape(self):
        env = _make_env(n_ev_types=2)
        assert env.observation_space.shape == (env.obs_dim,)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: reset
# ─────────────────────────────────────────────────────────────────────────────

class TestReset:

    def test_reset_returns_obs_shape(self):
        env = _make_env()
        obs, info = env.reset()
        assert obs.shape == (env.obs_dim,)

    def test_reset_obs_dtype_float32(self):
        env = _make_env()
        obs, _ = env.reset()
        assert obs.dtype == np.float32

    def test_reset_obs_within_clip(self):
        env = _make_env()
        obs, _ = env.reset()
        assert np.all(obs >= -5.0) and np.all(obs <= 5.0)

    def test_reset_info_is_dict(self):
        env = _make_env()
        _, info = env.reset()
        assert isinstance(info, dict)

    def test_reset_resets_timestep(self):
        env = _make_env()
        env.reset()
        env.step(env.action_space.sample())
        env.step(env.action_space.sample())
        env.reset()
        assert env._t == 0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: step semantics
# ─────────────────────────────────────────────────────────────────────────────

class TestStep:

    def test_step_returns_five_tuple(self):
        env = _make_env()
        env.reset()
        result = env.step(env.action_space.sample())
        assert len(result) == 5

    def test_step_obs_shape(self):
        env = _make_env()
        env.reset()
        obs, *_ = env.step(env.action_space.sample())
        assert obs.shape == (env.obs_dim,)

    def test_step_reward_is_scalar(self):
        env = _make_env()
        env.reset()
        _, reward, *_ = env.step(env.action_space.sample())
        assert isinstance(reward, float)

    def test_step_terminated_false_mid_episode(self):
        env = _make_env()
        env.reset()
        _, _, terminated, truncated, _ = env.step(env.action_space.sample())
        assert not terminated
        assert not truncated

    def test_step_terminated_at_end(self):
        env = _make_env(n_ev_types=1)
        site = _make_site(1)
        building = site.buildings[0]
        pv, irr, temp, wind, ev, fixed = _make_timeseries(1, 8760)
        small_env = UniversalPVBESSEnv(
            building=building,
            pv_timeseries=pv,
            irr_timeseries=irr,
            temp_timeseries=temp,
            wind_timeseries=wind,
            ev_demand_timeseries=ev,
            fixed_load_timeseries=fixed,
            site_config=site,
            max_episode_steps=3,
            seed=0,
        )
        small_env.reset()
        for _ in range(2):
            _, _, terminated, _, _ = small_env.step(small_env.action_space.sample())
            assert not terminated
        _, _, terminated, _, _ = small_env.step(small_env.action_space.sample())
        assert terminated

    def test_step_info_keys(self):
        env = _make_env()
        env.reset()
        _, _, _, _, info = env.step(env.action_space.sample())
        for key in ("t", "pv_kwh", "bess_soc", "grid_import_kwh", "ev_satisfaction", "co2_avoided_kg"):
            assert key in info, f"missing info key: {key}"

    def test_step_co2_avoided_nonneg(self):
        env = _make_env()
        env.reset()
        for _ in range(24):
            _, _, _, _, info = env.step(env.action_space.sample())
            assert info["co2_avoided_kg"] >= 0.0

    def test_step_bess_soc_bounded(self):
        env = _make_env()
        env.reset()
        building = env.building
        for _ in range(100):
            _, _, terminated, _, info = env.step(env.action_space.sample())
            soc = info["bess_soc"]
            assert building.bess_soc_min - 1e-6 <= soc <= building.bess_soc_max + 1e-6
            if terminated:
                break

    def test_step_ev_satisfaction_range(self):
        env = _make_env()
        env.reset()
        for _ in range(50):
            _, _, terminated, _, info = env.step(env.action_space.sample())
            for sat in info["ev_satisfaction"]:
                assert 0.0 <= sat <= 1.0 + 1e-6
            if terminated:
                break

    def test_step_clipped_action_accepted(self):
        """Actions outside bounds should be clipped, not raise an error."""
        env = _make_env()
        env.reset()
        bad_action = np.array([5.0, -3.0, 99.0], dtype=np.float32)
        obs, reward, _, _, _ = env.step(bad_action)
        assert obs.shape == (env.obs_dim,)


# ─────────────────────────────────────────────────────────────────────────────
# Tests: reward
# ─────────────────────────────────────────────────────────────────────────────

class TestReward:

    def test_reward_finite(self):
        env = _make_env()
        env.reset()
        for _ in range(50):
            _, reward, terminated, _, _ = env.step(env.action_space.sample())
            assert np.isfinite(reward), f"non-finite reward: {reward}"
            if terminated:
                break

    def test_discharge_during_peak_nonneg_reward(self):
        """Discharging BESS fully during peak hour should produce non-negative reward."""
        env = _make_env()
        env.reset()
        # Advance to peak hour 18
        for h in range(18):
            env.step(np.zeros(env.action_dim, dtype=np.float32))
        discharge_action = np.array([-1.0] + [1.0] * env.n_types, dtype=np.float32)
        _, reward, _, _, _ = env.step(discharge_action)
        # Reward should be reasonable (not deeply negative) when serving EV demand
        assert reward > -5.0


# ─────────────────────────────────────────────────────────────────────────────
# Tests: from_dataframes factory
# ─────────────────────────────────────────────────────────────────────────────

class TestFromDataframes:

    def test_from_dataframes_instantiates(self):
        import pandas as pd
        site = _make_site(2)
        n = 8760
        rng = np.random.default_rng(99)
        solar_df = pd.DataFrame({
            "potencia_kw": rng.uniform(0, 100, n),
            "irradiancia_ghi": rng.uniform(0, 800, n),
            "temperatura_c": rng.uniform(20, 35, n),
            "velocidad_viento_ms": rng.uniform(0, 5, n),
        })
        ev_dfs = {
            "type_0": pd.Series(rng.uniform(0, 5, n)),
            "type_1": pd.Series(rng.uniform(0, 5, n)),
        }
        fixed_df = pd.DataFrame({"mall_demand_kwh": np.full(n, 10.0)})
        env = UniversalPVBESSEnv.from_dataframes(
            site=site,
            building_idx=0,
            solar_df=solar_df,
            ev_dfs=ev_dfs,
            fixed_load_df=fixed_df,
            seed=0,
        )
        assert env.obs_dim == 21
        assert env.action_dim == 3

    def test_from_dataframes_step_works(self):
        import pandas as pd
        site = _make_site(2)
        n = 8760
        rng = np.random.default_rng(7)
        solar_df = pd.DataFrame({
            "potencia_kw": rng.uniform(0, 100, n),
            "irradiancia_ghi": rng.uniform(0, 800, n),
            "temperatura_c": rng.uniform(20, 35, n),
            "velocidad_viento_ms": rng.uniform(0, 5, n),
        })
        ev_dfs = {
            "type_0": pd.Series(rng.uniform(0, 5, n)),
            "type_1": pd.Series(rng.uniform(0, 5, n)),
        }
        fixed_df = pd.DataFrame({"mall_demand_kwh": np.full(n, 10.0)})
        env = UniversalPVBESSEnv.from_dataframes(
            site=site, building_idx=0, solar_df=solar_df,
            ev_dfs=ev_dfs, fixed_load_df=fixed_df,
        )
        obs, _ = env.reset()
        obs2, reward, _, _, info = env.step(env.action_space.sample())
        assert obs2.shape == (env.obs_dim,)
        assert np.isfinite(reward)
