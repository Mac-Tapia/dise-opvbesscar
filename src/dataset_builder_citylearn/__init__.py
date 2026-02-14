"""
Dataset Builder for CityLearn v2 - OE2 Integration Module

Este módulo centraliza todos los scripts de construcción de datasets
para CityLearn v2 desde los módulos OE2 (Solar, Chargers, BESS).

Estructura:
├── enrich_chargers.py          - Enriquecimiento CHARGERS con CO₂ directo
├── integrate_datasets.py       - Integración completa de 3 datasets
├── analyze_datasets.py         - Análisis estadístico de datasets
└── main_build_citylearn.py    - Orquestador principal

Uso:
    python -m src.dataset_builder_citylearn.main_build_citylearn
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "pvbesscar project"
__date__ = "2026-02-14"

__all__ = [
    "__version__",
    "__author__",
    "__date__",
]
