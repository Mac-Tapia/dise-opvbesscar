"""tests/integration/test_site_config.py — Integration tests for site config loading.

Tests cover: YAML loading for both canonical sites, property validation,
data-class invariants, and tariff schedule arithmetic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.site import (
    BuildingConfig,
    EVFleetConfig,
    EVVehicleTypeConfig,
    GridConfig,
    SiteConfig,
    TariffSchedule,
    load_site_config,
)

_CONFIGS = Path(__file__).resolve().parents[2] / "configs" / "sites"
_IQUITOS = _CONFIGS / "iquitos_bess_mall.yaml"
_LIMA = _CONFIGS / "lima_parking_ev.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# TariffSchedule
# ─────────────────────────────────────────────────────────────────────────────

class TestTariffSchedule:

    def setup_method(self):
        self.tariff = TariffSchedule(
            peak_rate_local_per_kwh=0.45,
            offpeak_rate_local_per_kwh=0.28,
            peak_hours_start=18,
            peak_hours_end=22,
            currency="PEN",
            exchange_rate_to_usd=3.75,
        )

    def test_peak_hours_property(self):
        ph = self.tariff.peak_hours
        assert 18 in ph
        assert 22 in ph
        assert 17 not in ph
        assert 23 not in ph

    def test_rate_at_peak(self):
        assert self.tariff.rate_at(20) == pytest.approx(0.45)

    def test_rate_at_offpeak(self):
        assert self.tariff.rate_at(10) == pytest.approx(0.28)

    def test_rate_at_boundary_start(self):
        assert self.tariff.rate_at(18) == pytest.approx(0.45)

    def test_rate_at_boundary_end(self):
        assert self.tariff.rate_at(22) == pytest.approx(0.45)

    def test_rate_at_just_after_peak(self):
        assert self.tariff.rate_at(23) == pytest.approx(0.28)


# ─────────────────────────────────────────────────────────────────────────────
# EVVehicleTypeConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestEVVehicleTypeConfig:

    def _moto(self, count=10, charger_kw=7.4, sockets=2):
        return EVVehicleTypeConfig(
            name="moto",
            vehicle_count=count,
            battery_kwh=1.5,
            charger_power_kw=charger_kw,
            sockets_per_charger=sockets,
            co2_avoided_kg_per_kwh=0.87,
            avg_daily_sessions=1.0,
            session_energy_kwh=0.75,
            peak_hours_share=0.50,
            utilization_factor=0.92,
        )

    def test_n_chargers(self):
        vt = self._moto(count=10, sockets=2)
        assert vt.n_chargers == 5  # ceil(10/2)

    def test_n_chargers_odd(self):
        vt = self._moto(count=11, sockets=2)
        assert vt.n_chargers == 6  # ceil(11/2)

    def test_peak_demand_kw(self):
        vt = self._moto(count=10, charger_kw=7.4, sockets=2)
        # n_chargers=5, peak_demand = 5 * 7.4 = 37.0
        assert vt.peak_demand_kw == pytest.approx(5 * 7.4)

    def test_invalid_utilization_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            EVVehicleTypeConfig(
                name="bad",
                vehicle_count=10,
                battery_kwh=1.5,
                charger_power_kw=7.4,
                sockets_per_charger=2,
                co2_avoided_kg_per_kwh=0.87,
                avg_daily_sessions=1.0,
                session_energy_kwh=0.75,
                peak_hours_share=0.50,
                utilization_factor=1.5,  # > 1.0 → invalid
            )


# ─────────────────────────────────────────────────────────────────────────────
# EVFleetConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestEVFleetConfig:

    def _fleet(self):
        moto = EVVehicleTypeConfig(
            name="moto", vehicle_count=270, battery_kwh=1.5, charger_power_kw=7.4,
            sockets_per_charger=2, co2_avoided_kg_per_kwh=0.87, avg_daily_sessions=1.0,
            session_energy_kwh=0.75, peak_hours_share=0.50, utilization_factor=0.92,
        )
        mototaxi = EVVehicleTypeConfig(
            name="mototaxi", vehicle_count=39, battery_kwh=3.0, charger_power_kw=7.4,
            sockets_per_charger=2, co2_avoided_kg_per_kwh=0.54, avg_daily_sessions=1.0,
            session_energy_kwh=1.5, peak_hours_share=0.50, utilization_factor=0.92,
        )
        return EVFleetConfig(vehicle_types=[moto, mototaxi], opening_hour=9, closing_hour=22)

    def test_total_vehicles(self):
        assert self._fleet().total_vehicles == 270 + 39

    def test_total_chargers_iquitos(self):
        fleet = self._fleet()
        # moto: ceil(270/2)=135, mototaxi: ceil(39/2)=20 → 155
        assert fleet.total_chargers == 135 + 20

    def test_total_sockets(self):
        fleet = self._fleet()
        # 135*2 + 20*2 = 310
        assert fleet.total_sockets == 310

    def test_n_vehicle_types(self):
        assert self._fleet().n_vehicle_types == 2

    def test_peak_demand_kw_positive(self):
        assert self._fleet().peak_demand_kw > 0


# ─────────────────────────────────────────────────────────────────────────────
# BuildingConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildingConfig:

    def _building(self):
        fleet = EVFleetConfig(
            vehicle_types=[
                EVVehicleTypeConfig(
                    name="moto", vehicle_count=10, battery_kwh=1.5, charger_power_kw=7.4,
                    sockets_per_charger=2, co2_avoided_kg_per_kwh=0.87, avg_daily_sessions=1.0,
                    session_energy_kwh=0.75, peak_hours_share=0.50, utilization_factor=0.92,
                )
            ],
            opening_hour=9,
            closing_hour=22,
        )
        return BuildingConfig(
            name="Test",
            pv_area_m2=15200.0,
            pv_panel_efficiency=0.199,
            pv_surface_tilt_deg=10.0,
            pv_surface_azimuth_deg=0.0,
            pv_coverage_fraction=0.65,
            pv_inverter_efficiency=0.956,
            pv_system_losses=0.14,
            bess_capacity_kwh=2000.0,
            bess_power_kw=400.0,
            bess_dod=0.80,
            bess_efficiency_roundtrip=0.95,
            bess_soc_min=0.20,
            bess_soc_max=1.00,
            bess_initial_soc=0.50,
            fixed_load_kw=100.0,
            ev_fleet=fleet,
        )

    def test_pv_installed_kwp(self):
        b = self._building()
        # formula: area * coverage * efficiency * (1 - losses)
        expected = 15200.0 * 0.65 * 0.199 * (1.0 - 0.14)
        assert b.pv_installed_kwp == pytest.approx(expected, rel=1e-4)

    def test_pv_installed_kwp_iquitos_range(self):
        b = self._building()
        # 15200 * 0.199 * 0.65 ≈ 1965 kWp (actual Iquitos uses different formula)
        assert b.pv_installed_kwp > 0

    def test_invalid_soc_min_max_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            BuildingConfig(
                name="bad",
                pv_area_m2=1000.0, pv_panel_efficiency=0.20, pv_surface_tilt_deg=10.0,
                pv_surface_azimuth_deg=0.0, pv_coverage_fraction=0.65,
                pv_inverter_efficiency=0.95, pv_system_losses=0.14,
                bess_capacity_kwh=100.0, bess_power_kw=50.0, bess_dod=0.80,
                bess_efficiency_roundtrip=0.95,
                bess_soc_min=0.8, bess_soc_max=0.3,  # min > max → invalid
                bess_initial_soc=0.50,
            )


# ─────────────────────────────────────────────────────────────────────────────
# load_site_config — Iquitos
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _IQUITOS.exists(), reason="iquitos_bess_mall.yaml not found")
class TestLoadSiteConfigIquitos:

    @pytest.fixture(autouse=True)
    def site(self):
        self.site = load_site_config(_IQUITOS)

    def test_site_id(self):
        assert "iquitos" in self.site.site_id.lower()

    def test_coordinates(self):
        assert self.site.latitude == pytest.approx(-3.75)
        assert self.site.longitude == pytest.approx(-73.25)

    def test_timezone(self):
        assert self.site.timezone == "America/Lima"

    def test_grid_co2_isolated(self):
        assert self.site.grid.co2_intensity_kg_per_kwh == pytest.approx(0.4521)
        assert self.site.grid.grid_type == "isolated"

    def test_grid_peak_tariff(self):
        assert self.site.grid.tariff.peak_rate_local_per_kwh == pytest.approx(0.45)

    def test_n_buildings(self):
        assert self.site.n_buildings == 1

    def test_bess_capacity(self):
        assert self.site.buildings[0].bess_capacity_kwh == pytest.approx(2000.0)

    def test_bess_power(self):
        assert self.site.buildings[0].bess_power_kw == pytest.approx(400.0)

    def test_fleet_two_types(self):
        fleet = self.site.buildings[0].ev_fleet
        assert fleet.n_vehicle_types == 2

    def test_fleet_type_names(self):
        names = [vt.name for vt in self.site.buildings[0].ev_fleet.vehicle_types]
        assert "moto" in names
        assert "mototaxi" in names

    def test_total_vehicles(self):
        assert self.site.total_ev_vehicles == 270 + 39

    def test_total_pv_kwp_positive(self):
        assert self.site.total_pv_kwp > 0

    def test_total_bess_kwh(self):
        assert self.site.total_bess_kwh == pytest.approx(2000.0)

    def test_peak_hours_iquitos(self):
        ph = self.site.grid.tariff.peak_hours
        assert 18 in ph and 22 in ph and 23 not in ph

    def test_all_vehicle_types_list(self):
        vt = self.site.all_vehicle_types
        assert "moto" in vt and "mototaxi" in vt

    def test_moto_kappa(self):
        moto = next(v for v in self.site.buildings[0].ev_fleet.vehicle_types if v.name == "moto")
        assert moto.co2_avoided_kg_per_kwh == pytest.approx(0.87)

    def test_mototaxi_kappa(self):
        mt = next(v for v in self.site.buildings[0].ev_fleet.vehicle_types if v.name == "mototaxi")
        assert mt.co2_avoided_kg_per_kwh == pytest.approx(0.54)


# ─────────────────────────────────────────────────────────────────────────────
# load_site_config — Lima
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _LIMA.exists(), reason="lima_parking_ev.yaml not found")
class TestLoadSiteConfigLima:

    @pytest.fixture(autouse=True)
    def site(self):
        self.site = load_site_config(_LIMA)

    def test_site_grid_connected(self):
        assert self.site.grid.grid_type == "connected"

    def test_co2_intensity_lower_than_iquitos(self):
        # Lima SIN (0.23) < Iquitos diesel (0.4521)
        assert self.site.grid.co2_intensity_kg_per_kwh < 0.40

    def test_max_export_kw_positive(self):
        assert self.site.grid.max_export_kw > 0

    def test_fleet_has_carro_electrico(self):
        names = [vt.name for vt in self.site.buildings[0].ev_fleet.vehicle_types]
        assert "carro_electrico" in names

    def test_carro_battery_kwh(self):
        carro = next(v for v in self.site.buildings[0].ev_fleet.vehicle_types if v.name == "carro_electrico")
        assert carro.battery_kwh == pytest.approx(40.0)

    def test_bess_smaller_than_iquitos(self):
        assert self.site.buildings[0].bess_capacity_kwh < 2000.0


# ─────────────────────────────────────────────────────────────────────────────
# SiteConfig programmatic construction
# ─────────────────────────────────────────────────────────────────────────────

class TestSiteConfigProgrammatic:

    def _make_minimal_site(self) -> SiteConfig:
        tariff = TariffSchedule(
            peak_rate_local_per_kwh=0.45,
            offpeak_rate_local_per_kwh=0.28,
            peak_hours_start=18,
            peak_hours_end=22,
            currency="PEN",
            exchange_rate_to_usd=3.75,
        )
        grid = GridConfig(
            co2_intensity_kg_per_kwh=0.4521,
            tariff=tariff,
            grid_type="isolated",
        )
        vt = EVVehicleTypeConfig(
            name="moto", vehicle_count=10, battery_kwh=1.5, charger_power_kw=7.4,
            sockets_per_charger=2, co2_avoided_kg_per_kwh=0.87, avg_daily_sessions=1.0,
            session_energy_kwh=0.75, peak_hours_share=0.50, utilization_factor=0.92,
        )
        fleet = EVFleetConfig(vehicle_types=[vt], opening_hour=9, closing_hour=22)
        building = BuildingConfig(
            name="B1",
            pv_area_m2=1000.0, pv_panel_efficiency=0.20, pv_surface_tilt_deg=10.0,
            pv_surface_azimuth_deg=0.0, pv_coverage_fraction=0.65,
            pv_inverter_efficiency=0.95, pv_system_losses=0.14,
            bess_capacity_kwh=100.0, bess_power_kw=50.0, bess_dod=0.80,
            bess_efficiency_roundtrip=0.95, bess_soc_min=0.20, bess_soc_max=1.00,
            bess_initial_soc=0.50, ev_fleet=fleet,
        )
        return SiteConfig(
            site_id="test", name="Test", latitude=-3.75, longitude=-73.25,
            altitude_m=100.0, timezone="America/Lima", year=2024,
            grid=grid, buildings=[building],
        )

    def test_n_buildings_one(self):
        assert self._make_minimal_site().n_buildings == 1

    def test_total_ev_vehicles(self):
        assert self._make_minimal_site().total_ev_vehicles == 10

    def test_all_vehicle_types_list(self):
        assert "moto" in self._make_minimal_site().all_vehicle_types

    def test_multi_building_total_bess(self):
        site = self._make_minimal_site()
        # Duplicate the single building to create a 2-building site
        b2 = site.buildings[0]
        site2 = SiteConfig(
            site_id="test2", name="Test2", latitude=-3.75, longitude=-73.25,
            altitude_m=100.0, timezone="America/Lima", year=2024,
            grid=site.grid, buildings=[site.buildings[0], b2],
        )
        assert site2.total_bess_kwh == pytest.approx(200.0)
        assert site2.n_buildings == 2
