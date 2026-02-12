"""
Dataset Builder for CityLearn v2.5.0 Environments - OE3 Integration v5.3.

Este módulo proporciona la funcionalidad para construir datasets compatibles
con CityLearn v2.5.0 a partir de datos OE2 (solar, chargers, BESS, mall).

Exports principales:
- build_citylearn_dataset: Función principal para construir el dataset
- BuiltDataset: Dataclass con resultado de construcción
- _extract_observable_variables: Extrae variables para agentes RL
- Constantes OSINERGMIN y CO2 para rewards

Datasets OE2 requeridos (8760 filas horarias):
1. Solar: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
2. Chargers: data/oe2/chargers/chargers_ev_ano_2024_v3.csv
3. BESS: data/oe2/bess/bess_simulation_hourly.csv
4. Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv

Variables Observables v5.3:
- OSINERGMIN: is_hora_punta, tarifa_aplicada_soles (HP=0.45, HFP=0.28)
- CO2 Chargers: reduccion_directa_co2_kg, co2_reduccion_motos/mototaxis_kg
- CO2 Solar: reduccion_indirecta_co2_kg, co2_evitado_mall/ev_kg

Version: 2026-02-12 (v5.3 - OSINERGMIN + CO2)
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
    _extract_observable_variables,
    # Constantes OSINERGMIN
    TARIFA_ENERGIA_HP_SOLES,
    TARIFA_ENERGIA_HFP_SOLES,
    HORA_INICIO_HP,
    HORA_FIN_HP,
    # Constantes CO2
    FACTOR_CO2_RED_KG_KWH,
    FACTOR_CO2_GASOLINA_KG_L,
    FACTOR_CO2_NETO_MOTO_KG_KWH,
    FACTOR_CO2_NETO_MOTOTAXI_KG_KWH,
    # Listas de columnas observables
    CHARGERS_OBSERVABLE_COLS,
    SOLAR_OBSERVABLE_COLS,
    ALL_OBSERVABLE_COLS,
    REWARDS_AVAILABLE,
)

__all__ = [
    # Dataset construction
    "build_citylearn_dataset",
    "BuiltDataset",
    # Observable variables extraction
    "_extract_observable_variables",
    # Constantes OSINERGMIN
    "TARIFA_ENERGIA_HP_SOLES",
    "TARIFA_ENERGIA_HFP_SOLES",
    "HORA_INICIO_HP",
    "HORA_FIN_HP",
    # Constantes CO2
    "FACTOR_CO2_RED_KG_KWH",
    "FACTOR_CO2_GASOLINA_KG_L",
    "FACTOR_CO2_NETO_MOTO_KG_KWH",
    "FACTOR_CO2_NETO_MOTOTAXI_KG_KWH",
    # Columnas observables
    "CHARGERS_OBSERVABLE_COLS",
    "SOLAR_OBSERVABLE_COLS",
    "ALL_OBSERVABLE_COLS",
    # Validation utilities
    "_validate_solar_timeseries_hourly",
    # Internal utilities (for advanced use)
    "_load_oe2_artifacts",
    "_find_first_building",
    "_discover_csv_paths",
    "_generate_individual_charger_csvs",
    "REWARDS_AVAILABLE",
]
