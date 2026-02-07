"""
Dataset Builder for CityLearn v2.5.0 Environments - OE3 Integration.

Este módulo proporciona la funcionalidad para construir datasets compatibles
con CityLearn v2.5.0 a partir de datos OE2 (solar, chargers, BESS, mall).

Exports principales:
- build_citylearn_dataset: Función principal para construir el dataset
- BuiltDataset: Dataclass con resultado de construcción
- CityLearnDataValidator: Validador post-construcción

Datasets OE2 requeridos (8760 filas horarias):
1. Solar: data/interim/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
2. Chargers: data/interim/oe2/chargers/chargers_real_hourly_2024.csv
3. BESS: data/interim/oe2/bess/bess_hourly_dataset_2024.csv
4. Mall: data/interim/oe2/demandamallkwh/demandamallhorakwh.csv
5. Chargers JSON: data/interim/oe2/chargers/individual_chargers.json

Version: 2026-02-07 (Consolidado)
"""

from __future__ import annotations

# Exportar funciones principales desde dataset_builder.py
from .dataset_builder import (
    build_citylearn_dataset,
    BuiltDataset,
    _validate_solar_timeseries_hourly,
    _load_oe2_artifacts,
    _find_first_building,
    _discover_csv_paths,
    _generate_individual_charger_csvs,
    REWARDS_AVAILABLE,
)

# Exportar validador post-build
from .validate_citylearn_build import CityLearnDataValidator

__all__ = [
    # Dataset construction
    "build_citylearn_dataset",
    "BuiltDataset",
    # Validation
    "CityLearnDataValidator",
    "_validate_solar_timeseries_hourly",
    # Internal utilities (for advanced use)
    "_load_oe2_artifacts",
    "_find_first_building",
    "_discover_csv_paths",
    "_generate_individual_charger_csvs",
    "REWARDS_AVAILABLE",
]
