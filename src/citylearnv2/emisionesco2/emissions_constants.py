"""
Constantes de emisiones para el sistema pvbesscar - Iquitos.

Este módulo centraliza todas las constantes relacionadas con emisiones de CO₂
para mantener consistencia en todo el proyecto.

SINCRONIZACIÓN:
- configs/default.yaml → oe3.emissions + oe3.co2_emissions
- rewards.py → IquitosContext
- Todos los agentes (SAC, PPO, A2C)
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EmissionsConstants:
    """Constantes de emisiones para Iquitos (inmutables)."""

    # Factor de emisión de la red eléctrica (central térmica aislada)
    GRID_CO2_FACTOR_KG_PER_KWH: float = 0.4521  # kg CO₂/kWh

    # Vehículos eléctricos (motos/mototaxis)
    EV_KM_PER_KWH: float = 35.0  # Eficiencia: km recorridos por kWh

    # Vehículos de combustión (motos/mototaxis a gasolina)
    ICE_KM_PER_GALLON: float = 120.0  # Eficiencia: km recorridos por galón
    ICE_KGCO2_PER_GALLON: float = 8.9  # Emisiones: kg CO₂ por galón

    # Vida útil del proyecto
    PROJECT_LIFE_YEARS: int = 20

    # Cálculos derivados
    @property
    def ice_kgco2_per_km(self) -> float:
        """kg CO₂ por km (vehículo de combustión)."""
        return self.ICE_KGCO2_PER_GALLON / self.ICE_KM_PER_GALLON

    @property
    def ev_kgco2_per_km_grid(self) -> float:
        """kg CO₂ por km (vehículo eléctrico cargado desde grid)."""
        kwh_per_km = 1.0 / self.EV_KM_PER_KWH
        return kwh_per_km * self.GRID_CO2_FACTOR_KG_PER_KWH

    @property
    def co2_reduction_per_km(self) -> float:
        """Reducción de CO₂ por km (EV vs ICE)."""
        return self.ice_kgco2_per_km - self.ev_kgco2_per_km_grid


# Instancia global singleton
EMISSIONS = EmissionsConstants()


def calculate_ev_co2_avoided(ev_charging_kwh: float) -> float:
    """Calcula CO₂ evitado por usar vehículos eléctricos vs combustión.

    Args:
        ev_charging_kwh: Energía entregada a vehículos eléctricos (kWh)

    Returns:
        CO₂ evitado en kg (emisiones combustión - emisiones EV desde grid)
    """
    if ev_charging_kwh <= 0:
        return 0.0

    # km recorridos con la energía cargada
    total_km = ev_charging_kwh * EMISSIONS.EV_KM_PER_KWH

    # Gasolina que se habría consumido
    gallons_avoided = total_km / EMISSIONS.ICE_KM_PER_GALLON

    # CO₂ que se habría emitido
    co2_combustion_kg = gallons_avoided * EMISSIONS.ICE_KGCO2_PER_GALLON

    # CO₂ que se emitió al cargar desde grid
    co2_grid_kg = ev_charging_kwh * EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH

    # Reducción neta
    return co2_combustion_kg - co2_grid_kg


def calculate_solar_co2_avoided(solar_consumed_kwh: float) -> float:
    """Calcula CO₂ evitado por usar energía solar vs grid térmico.

    Args:
        solar_consumed_kwh: Energía solar consumida (kWh)

    Returns:
        CO₂ evitado en kg
    """
    return solar_consumed_kwh * EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH


def validate_config_consistency(config: dict) -> list[str]:
    """Valida que las constantes en el config YAML coincidan con las del código.

    Args:
        config: Diccionario de configuración cargado de YAML

    Returns:
        Lista de mensajes de error (vacía si todo es consistente)
    """
    errors = []

    # Validar oe3.emissions
    emissions = config.get("oe3", {}).get("emissions", {})
    if emissions.get("km_per_kwh") != EMISSIONS.EV_KM_PER_KWH:
        errors.append(
            f"oe3.emissions.km_per_kwh={emissions.get('km_per_kwh')} "
            f"!= {EMISSIONS.EV_KM_PER_KWH}"
        )
    if emissions.get("km_per_gallon") != EMISSIONS.ICE_KM_PER_GALLON:
        errors.append(
            f"oe3.emissions.km_per_gallon={emissions.get('km_per_gallon')} "
            f"!= {EMISSIONS.ICE_KM_PER_GALLON}"
        )
    if emissions.get("kgco2_per_gallon") != EMISSIONS.ICE_KGCO2_PER_GALLON:
        errors.append(
            f"oe3.emissions.kgco2_per_gallon={emissions.get('kgco2_per_gallon')} "
            f"!= {EMISSIONS.ICE_KGCO2_PER_GALLON}"
        )

    # Validar oe3.co2_emissions
    co2_emissions = config.get("oe3", {}).get("co2_emissions", {})
    if co2_emissions.get("grid_import_factor_kg_kwh") != EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH:
        errors.append(
            f"oe3.co2_emissions.grid_import_factor_kg_kwh="
            f"{co2_emissions.get('grid_import_factor_kg_kwh')} "
            f"!= {EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH}"
        )

    # Validar oe3.grid
    grid = config.get("oe3", {}).get("grid", {})
    if grid.get("carbon_intensity_kg_per_kwh") != EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH:
        errors.append(
            f"oe3.grid.carbon_intensity_kg_per_kwh="
            f"{grid.get('carbon_intensity_kg_per_kwh')} "
            f"!= {EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH}"
        )

    return errors
