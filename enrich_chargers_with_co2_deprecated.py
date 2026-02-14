#!/usr/bin/env python3
"""
Importadores de compatibilidad: Redirigen antiguas importaciones a la nueva ubicación.

Los scripts se han movido a src/dataset_builder_citylearn/ pero mantenemos
compatibilidad con importaciones antiguas desde la raíz del proyecto.

Uso antiguo (DEPRECATED):
    python enrich_chargers_with_co2.py

Uso nuevo (RECOMENDADO):
    python -m src.dataset_builder_citylearn.main_build_citylearn
"""

# Re-exportar desde nueva ubicación
from src.dataset_builder_citylearn.enrich_chargers import enrich_chargers_dataset

__all__ = ['enrich_chargers_dataset']

if __name__ == "__main__":
    print("\n⚠️  DEPRECATED: Use 'python -m src.dataset_builder_citylearn.main_build_citylearn' instead\n")
    enrich_chargers_dataset()
