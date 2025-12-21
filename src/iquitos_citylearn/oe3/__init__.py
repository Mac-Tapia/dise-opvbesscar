"""Objetivo Específico 3 (OE.3): CityLearn v2 con carga EV.

Este paquete contiene:
- Construcción de dataset CityLearn (schema + series temporales) a partir de los resultados del OE.2.
- Simulación y evaluación de agentes (sin control, RBC, RL/SAC).
- Cálculo de emisiones CO₂ y tabla comparativa anual y a 20 años.
"""

from .dataset_builder import build_citylearn_dataset

__all__ = ["build_citylearn_dataset"]
