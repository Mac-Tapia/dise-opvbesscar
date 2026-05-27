from __future__ import annotations

import pytest

from src.dimensionamiento.oe2.disenocargadoresev import chargers


def test_iquitos_charger_set_matches_oe2_design() -> None:
    charger_set = chargers.create_iquitos_chargers()

    assert charger_set.count == 19
    assert charger_set.total_sockets == 38
    assert charger_set.motos_count == 15
    assert charger_set.mototaxis_count == 4
    assert {charger.max_power_kw for charger in charger_set.chargers} == {7.4}
    assert {charger.sockets for charger in charger_set.chargers} == {2}
    assert [charger.vehicle_type for charger in charger_set.chargers[:15]] == ["moto"] * 15
    assert [charger.vehicle_type for charger in charger_set.chargers[15:]] == ["mototaxi"] * 4


def test_charger_set_validation_passes_without_warnings() -> None:
    validation = chargers.validate_charger_set(chargers.create_iquitos_chargers())

    assert validation == {"is_valid": True, "errors": [], "warnings": []}


def test_vehicle_energy_constants_are_consistent() -> None:
    assert chargers.CHARGING_EFFICIENCY == pytest.approx(0.62)
    assert chargers.MOTO_BATTERY_KWH == pytest.approx(4.6)
    assert chargers.MOTOTAXI_BATTERY_KWH == pytest.approx(7.4)
    assert chargers.MOTO_ENERGY_TO_CHARGE_KWH == pytest.approx(0.60 * 4.6 / 0.95, abs=1e-12)
    assert chargers.MOTOTAXI_ENERGY_TO_CHARGE_KWH == pytest.approx(0.60 * 7.4 / 0.95, abs=1e-12)
