from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.dataset_builder_citylearn.data_loader import (
    BESS_CAPACITY_KWH,
    BESS_MAX_POWER_KW,
    CO2_FACTOR_GRID_KG_PER_KWH,
    DEFAULT_BESS_PATH,
    DEFAULT_CHARGERS_PATH,
    DEFAULT_MALL_DEMAND_PATH,
    DEFAULT_SOLAR_PATH,
    N_CHARGERS,
    SOLAR_PV_KWP,
    TOTAL_SOCKETS,
    load_chargers_data,
    rebuild_oe2_datasets_complete,
)


def test_oe2_loader_uses_existing_canonical_paths() -> None:
    for path in [
        DEFAULT_SOLAR_PATH,
        DEFAULT_BESS_PATH,
        DEFAULT_CHARGERS_PATH,
        DEFAULT_MALL_DEMAND_PATH,
    ]:
        assert Path(path).exists(), f"Missing canonical OE2 dataset: {path}"


def test_oe2_system_constants_match_architecture() -> None:
    assert BESS_CAPACITY_KWH == pytest.approx(2000.0)
    assert BESS_MAX_POWER_KW == pytest.approx(400.0)
    assert N_CHARGERS == 19
    assert TOTAL_SOCKETS == 38
    assert SOLAR_PV_KWP == pytest.approx(4162.0)
    assert CO2_FACTOR_GRID_KG_PER_KWH == pytest.approx(0.4521)


def test_rebuild_oe2_datasets_complete_loads_hourly_data() -> None:
    datasets = rebuild_oe2_datasets_complete()

    assert datasets["solar"].n_hours == 8760
    assert datasets["bess"].n_hours == 8760
    assert datasets["chargers"].n_hours == 8760
    assert datasets["demand"].n_hours == 8760
    assert datasets["chargers"].n_chargers == 19
    assert datasets["chargers"].total_sockets == 38
    assert datasets["bess"].capacity_kwh == pytest.approx(2000.0)


def test_chargers_energy_aggregates_match_socket_columns() -> None:
    chargers = load_chargers_data()
    df = chargers.df

    socket_power_cols = [col for col in df.columns if re.fullmatch(r"socket_\d{3}_charging_power_kw", col)]
    moto_cols = [col for col in socket_power_cols if int(col.split("_")[1]) < 30]
    mototaxi_cols = [col for col in socket_power_cols if int(col.split("_")[1]) >= 30]

    assert df.shape[0] == 8760
    assert len(socket_power_cols) == 38
    assert len(moto_cols) == 30
    assert len(mototaxi_cols) == 8
    assert (df[socket_power_cols] >= 0).all().all()

    assert df["ev_energia_total_kwh"].sum() == pytest.approx(df[socket_power_cols].sum().sum())
    assert df["ev_energia_motos_kwh"].sum() == pytest.approx(df[moto_cols].sum().sum())
    assert df["ev_energia_mototaxis_kwh"].sum() == pytest.approx(df[mototaxi_cols].sum().sum())
    assert df["ev_energia_total_kwh"].sum() == pytest.approx(408_281.532)
    assert df["ev_energia_motos_kwh"].sum() == pytest.approx(345_343.348)
    assert df["ev_energia_mototaxis_kwh"].sum() == pytest.approx(62_938.184)
