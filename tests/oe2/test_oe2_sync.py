"""Tests de sincronización OE2 — valida que todos los módulos usan un único conjunto de rutas y constantes.

Garantiza que:
  1. _paths.py define las rutas canónicas y data_loader.py las importa directamente.
  2. configs/default.yaml referencia las mismas rutas que _paths.py.
  3. No existe la ruta solar deprecated como fuente primaria en ningún módulo.
  4. Las constantes clave son idénticas entre _paths.py, _constants.py y data_loader.py.
  5. Las rutas de salida OE2 apuntan a data/oe2/ (no a data/interim/ como primario).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"

# ---------------------------------------------------------------------------
# Imports de los módulos bajo prueba
# ---------------------------------------------------------------------------
from src.dimensionamiento.oe2._paths import (
    SOLAR_CANONICAL_CSV,
    BESS_CANONICAL_CSV,
    CHARGERS_CANONICAL_CSV,
    MALL_DEMAND_CANONICAL_CSV,
    CITYLEARN_OUTPUT_DIR,
    BESS_CAPACITY_KWH as PATHS_BESS_CAPACITY,
    N_CHARGERS as PATHS_N_CHARGERS,
    N_SOCKETS as PATHS_N_SOCKETS,
    SOLAR_PV_KWP as PATHS_SOLAR_KWP,
    INTERIM_SOLAR_PATHS,
)
from src.dimensionamiento.oe2._constants import (
    BESS_CAPACITY_KWH as CONST_BESS_CAPACITY,
    BESS_POWER_KW as CONST_BESS_POWER,
    FACTOR_CO2_KG_KWH as CONST_CO2_FACTOR,
    TARIFA_ENERGIA_HP_SOLES,
    TARIFA_ENERGIA_HFP_SOLES,
    HORA_FIN_HP,
)
from src.dataset_builder_citylearn.data_loader import (
    DEFAULT_SOLAR_PATH,
    DEFAULT_BESS_PATH,
    DEFAULT_CHARGERS_PATH,
    DEFAULT_MALL_DEMAND_PATH,
    PROCESSED_CITYLEARN_DIR,
    BESS_CAPACITY_KWH as LOADER_BESS_CAPACITY,
    TOTAL_SOCKETS as LOADER_TOTAL_SOCKETS,
    SOLAR_PV_KWP as LOADER_SOLAR_KWP,
    CO2_FACTOR_GRID_KG_PER_KWH as LOADER_CO2_FACTOR,
)


# ===========================================================================
# 1. Consistencia de rutas: data_loader == _paths
# ===========================================================================

class TestDataLoaderUsesCanonicalPaths:
    """data_loader.py debe importar desde _paths.py — no redefinir rutas."""

    def test_solar_path_matches_canonical(self):
        assert DEFAULT_SOLAR_PATH == SOLAR_CANONICAL_CSV, (
            f"Solar path mismatch:\n  data_loader: {DEFAULT_SOLAR_PATH}\n  _paths: {SOLAR_CANONICAL_CSV}"
        )

    def test_bess_path_matches_canonical(self):
        assert DEFAULT_BESS_PATH == BESS_CANONICAL_CSV

    def test_chargers_path_matches_canonical(self):
        assert DEFAULT_CHARGERS_PATH == CHARGERS_CANONICAL_CSV

    def test_mall_path_matches_canonical(self):
        assert DEFAULT_MALL_DEMAND_PATH == MALL_DEMAND_CANONICAL_CSV

    def test_citylearn_output_dir_matches_canonical(self):
        assert PROCESSED_CITYLEARN_DIR == CITYLEARN_OUTPUT_DIR


# ===========================================================================
# 2. Consistencia de constantes: data_loader == _paths == _constants
# ===========================================================================

class TestConstantsConsistency:
    """Los valores numéricos clave deben ser idénticos en todos los módulos."""

    def test_bess_capacity_loader_equals_paths(self):
        assert LOADER_BESS_CAPACITY == PATHS_BESS_CAPACITY == 2000.0

    def test_bess_capacity_paths_equals_constants(self):
        assert PATHS_BESS_CAPACITY == CONST_BESS_CAPACITY

    def test_total_sockets_is_double_chargers(self):
        assert LOADER_TOTAL_SOCKETS == PATHS_N_SOCKETS == PATHS_N_CHARGERS * 2

    def test_solar_kwp_consistent(self):
        assert LOADER_SOLAR_KWP == PATHS_SOLAR_KWP == 4162.0

    def test_co2_factor_consistent(self):
        assert LOADER_CO2_FACTOR == CONST_CO2_FACTOR == 0.4521

    def test_hora_fin_hp_is_23(self):
        """HP window must end at 23 (exclusive), covering hours 18-22 inclusive."""
        assert HORA_FIN_HP == 23, f"HORA_FIN_HP debe ser 23, encontrado {HORA_FIN_HP}"

    def test_tariff_hp_greater_than_hfp(self):
        assert TARIFA_ENERGIA_HP_SOLES > TARIFA_ENERGIA_HFP_SOLES

    def test_tariff_hp_value(self):
        assert TARIFA_ENERGIA_HP_SOLES == pytest.approx(0.45)

    def test_tariff_hfp_value(self):
        assert TARIFA_ENERGIA_HFP_SOLES == pytest.approx(0.28)


# ===========================================================================
# 3. Rutas de configs/default.yaml consistentes con _paths.py
# ===========================================================================

class TestConfigYamlPaths:
    """configs/default.yaml debe referenciar las rutas canónicas de _paths.py."""

    @pytest.fixture(scope="class")
    def cfg(self):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_solar_file_in_config(self, cfg):
        solar_file = cfg["oe2"]["data"]["solar_file"]
        expected = str(SOLAR_CANONICAL_CSV).replace("\\", "/")
        assert solar_file == expected, (
            f"configs/default.yaml solar_file={solar_file!r}\n  expected={expected!r}"
        )

    def test_bess_file_in_config(self, cfg):
        bess_file = cfg["oe2"]["data"]["bess_file"]
        expected = str(BESS_CANONICAL_CSV).replace("\\", "/")
        assert bess_file == expected

    def test_chargers_file_in_config(self, cfg):
        chargers_file = cfg["oe2"]["data"]["chargers_file"]
        expected = str(CHARGERS_CANONICAL_CSV).replace("\\", "/")
        assert chargers_file == expected

    def test_mall_file_in_config(self, cfg):
        mall_file = cfg["oe2"]["data"]["mall_file"]
        expected = str(MALL_DEMAND_CANONICAL_CSV).replace("\\", "/")
        assert mall_file == expected


# ===========================================================================
# 4. Ruta solar deprecated NO es la primaria
# ===========================================================================

DEPRECATED_SOLAR_FILENAME = "pv_generation_hourly_citylearn_v2.csv"

class TestNoDeprecatedPrimaryPaths:
    """La ruta solar v2 (deprecated) NO debe ser la fuente primaria en ningún módulo."""

    def test_canonical_solar_is_not_deprecated(self):
        assert DEPRECATED_SOLAR_FILENAME not in str(SOLAR_CANONICAL_CSV)

    def test_data_loader_primary_solar_is_not_deprecated(self):
        assert DEPRECATED_SOLAR_FILENAME not in str(DEFAULT_SOLAR_PATH)

    def test_deprecated_is_only_fallback_in_interim_list(self):
        """El deprecated puede existir como fallback (posición >0), nunca como primario."""
        primary = INTERIM_SOLAR_PATHS[0]
        assert DEPRECATED_SOLAR_FILENAME not in str(primary), (
            f"La ruta primaria de fallback solar no debe ser deprecated: {primary}"
        )

    def test_config_solar_file_is_not_deprecated(self):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        solar_file = cfg["oe2"]["data"]["solar_file"]
        assert DEPRECATED_SOLAR_FILENAME not in solar_file


# ===========================================================================
# 5. Rutas de salida OE2 apuntan a data/oe2/ (no interim como primario)
# ===========================================================================

class TestOutputsUseOE2Primary:
    """Los módulos OE2 deben escribir en data/oe2/, no en data/interim/ como primario."""

    def test_solar_canonical_is_under_oe2(self):
        assert str(SOLAR_CANONICAL_CSV).startswith("data/oe2") or \
               "data/oe2" in str(SOLAR_CANONICAL_CSV).replace("\\", "/")

    def test_bess_canonical_is_under_oe2(self):
        assert "data/oe2" in str(BESS_CANONICAL_CSV).replace("\\", "/")

    def test_chargers_canonical_is_under_oe2(self):
        assert "data/oe2" in str(CHARGERS_CANONICAL_CSV).replace("\\", "/")

    def test_mall_canonical_is_under_oe2(self):
        assert "data/oe2" in str(MALL_DEMAND_CANONICAL_CSV).replace("\\", "/")

    def test_citylearn_output_not_interim(self):
        assert "interim" not in str(CITYLEARN_OUTPUT_DIR)
