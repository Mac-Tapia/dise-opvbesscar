"""
================================================================================
EV DEMAND CALCULATOR - Cálculo Dinámico de Demanda de Carga de EVs
================================================================================

Calcula la demanda de carga de EVs basándose en:
- SOC del vehículo al llegar (battery_soc_arrival: 0-1)
- SOC requerido al partir (battery_soc_target: 0-1)
- Capacidad de batería del EV (battery_capacity_kwh)
- Potencia del charger (charger_power_kw)
- Tiempo disponible para carga (charging_duration_hours)

Modelo realista:
- Cada EV llega con SOC bajo (~20-30%)
- Necesita alcanzar SOC alto (~80-90%) para el día siguiente
- La energía requerida = (SOC_target - SOC_arrival) × battery_capacity_kwh
- El tiempo de carga = energía_requerida / charger_power_kw
- Si tiempo_disponible < tiempo_requerido: carga parcial
- Si tiempo_disponible >= tiempo_requerido: carga completa

Variabilidad temporal:
- Horas pico (18-21h): Mayor demanda de EVs
- Horas valle (00-09h): Menor demanda de EVs
- Fin de semana: Patrones diferentes
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EVChargerConfig:
    """Configuración de un charger individual."""
    charger_id: int
    charger_type: str  # "moto" o "mototaxi"
    charger_power_kw: float  # Potencia del charger (kW)

    # Configuración de batería del EV típico
    battery_capacity_kwh: float
    battery_soc_arrival: float  # SOC al llegar (fracción 0-1)
    battery_soc_target: float  # SOC requerido al salir (fracción 0-1)

    # Horarios
    opening_hour: int = 9   # 9 AM
    closing_hour: int = 22  # 10 PM

    def __post_init__(self):
        # Validaciones
        if not (0 <= self.battery_soc_arrival <= 1.0):
            raise ValueError(f"battery_soc_arrival debe estar en [0, 1], got {self.battery_soc_arrival}")
        if not (0 <= self.battery_soc_target <= 1.0):
            raise ValueError(f"battery_soc_target debe estar en [0, 1], got {self.battery_soc_target}")
        if self.battery_soc_target <= self.battery_soc_arrival:
            raise ValueError(f"battery_soc_target ({self.battery_soc_target}) debe ser > battery_soc_arrival ({self.battery_soc_arrival})")


class EVDemandCalculator:
    """Calcula demanda de carga de EV dinámicamente."""

    def __init__(self, charger_config: EVChargerConfig):
        self.config = charger_config
        self._validate_config()

    def _validate_config(self):
        """Valida configuración."""
        if self.config.charger_power_kw <= 0:
            raise ValueError(f"Potencia del charger debe ser > 0, got {self.config.charger_power_kw}")
        if self.config.battery_capacity_kwh <= 0:
            raise ValueError(f"Capacidad de batería debe ser > 0, got {self.config.battery_capacity_kwh}")

    def calculate_energy_required(self) -> float:
        """Calcula energía requerida para cargar (kWh).

        Energía = (SOC_target - SOC_arrival) × Capacidad_batería

        Returns:
            Energía requerida en kWh
        """
        energy_required = (
            (self.config.battery_soc_target - self.config.battery_soc_arrival)
            * self.config.battery_capacity_kwh
        )
        return energy_required

    def calculate_charging_time(self) -> float:
        """Calcula tiempo requerido para carga completa (horas).

        Tiempo = Energía / Potencia

        Returns:
            Tiempo de carga en horas
        """
        energy_required = self.calculate_energy_required()
        charging_time = energy_required / self.config.charger_power_kw
        return charging_time

    def calculate_available_charging_duration(self, hour_of_day: int) -> float:
        """Calcula duración disponible de carga en una hora específica (horas).

        Durante horarios de operación (opening_hour a closing_hour):
        - Si es primera llegada: tiempo desde hora actual hasta closing_hour
        - Si ya está cargado: 0 (no más carga)

        Returns:
            Duración disponible en horas
        """
        if hour_of_day < self.config.opening_hour or hour_of_day >= self.config.closing_hour:
            # Fuera de horario: no hay carga
            return 0.0

        # Dentro de horario: tiempo restante hasta cierre
        hours_until_closing = self.config.closing_hour - hour_of_day
        return float(hours_until_closing)

    def calculate_hourly_demand(self, hour_of_day: int, day_of_week: int, is_connected: bool) -> float:
        """Calcula demanda de carga para una hora específica (kW).

        Lógica:
        - Si no está conectado (is_connected=False): demanda = 0
        - Si está conectado pero batería llena: demanda = 0
        - Si está conectado y batería no llena: demanda = potencia del charger

        Con variabilidad temporal:
        - Horas pico (18-21h): +30% carga (pero limitado por horario)
        - Fin de semana: -10% carga (menos presión)

        Args:
            hour_of_day: Hora del día (0-23)
            day_of_week: Día de la semana (0=lunes, 6=domingo)
            is_connected: Si el EV está conectado

        Returns:
            Demanda en kW (0 si no está cargando)
        """
        # Si no está conectado: sin demanda
        if not is_connected:
            return 0.0

        # Si está fuera de horario: sin demanda
        if hour_of_day < self.config.opening_hour or hour_of_day >= self.config.closing_hour:
            return 0.0

        # Base: potencia del charger
        base_demand = self.config.charger_power_kw

        # Factores de modulación
        peak_factor = 1.0
        weekend_factor = 1.0

        # Horas pico (18-21h): +30% (más EVs queriendo cargar)
        if 18 <= hour_of_day <= 21:
            peak_factor = 1.3

        # Fin de semana (sábado/domingo): -10% (menos presión)
        if day_of_week >= 5:  # 5=sábado, 6=domingo
            weekend_factor = 0.9

        # Demanda modulada
        demand = base_demand * peak_factor * weekend_factor

        return float(demand)

    def calculate_daily_profile(self, day_of_week: int, occupancy_pattern: np.ndarray) -> np.ndarray:
        """Calcula perfil de demanda para un día completo (24 horas).

        Args:
            day_of_week: Día de la semana (0=lunes, 6=domingo)
            occupancy_pattern: Array de 24 elementos con 1=ocupado, 0=libre

        Returns:
            Array de 24 elementos con demanda horaria (kW)
        """
        hourly_demand = np.zeros(24, dtype=float)

        for hour in range(24):
            is_connected = bool(occupancy_pattern[hour])
            hourly_demand[hour] = self.calculate_hourly_demand(hour, day_of_week, is_connected)

        return hourly_demand

    def calculate_annual_profile(self, occupancy_pattern_annual: np.ndarray) -> np.ndarray:
        """Calcula perfil de demanda para un año completo (8760 horas).

        Args:
            occupancy_pattern_annual: Array de 8760 elementos (1=ocupado, 0=libre)

        Returns:
            Array de 8760 elementos con demanda horaria (kW)
        """
        annual_demand = np.zeros(8760, dtype=float)

        for t in range(8760):
            hour_of_day = t % 24
            day_of_year = t // 24
            day_of_week = day_of_year % 7

            is_connected = bool(occupancy_pattern_annual[t])
            annual_demand[t] = self.calculate_hourly_demand(hour_of_day, day_of_week, is_connected)

        return annual_demand


class EVFleetAggregator:
    """Agrega demanda de múltiples EVs en un charger."""

    def __init__(self, chargers: List[EVChargerConfig]):
        self.chargers = chargers
        self.calculators = [EVDemandCalculator(c) for c in chargers]

    def calculate_fleet_demand_hourly(
        self,
        occupancy_matrix: np.ndarray,  # shape (8760, n_chargers)
        hour_index: int,
    ) -> float:
        """Calcula demanda total de la flota para una hora específica.

        Args:
            occupancy_matrix: Array de ocupancia (8760, n_chargers)
            hour_index: Índice de hora (0-8759)

        Returns:
            Demanda total agregada (kW)
        """
        hour_of_day = hour_index % 24
        day_of_year = hour_index // 24
        day_of_week = day_of_year % 7

        total_demand = 0.0
        for charger_idx, calc in enumerate(self.calculators):
            is_connected = bool(occupancy_matrix[hour_index, charger_idx])
            demand = calc.calculate_hourly_demand(hour_of_day, day_of_week, is_connected)
            total_demand += demand

        return total_demand

    def calculate_fleet_demand_annual(self, occupancy_matrix: np.ndarray) -> np.ndarray:
        """Calcula demanda anual total de la flota.

        Args:
            occupancy_matrix: Array de ocupancia (8760, n_chargers)

        Returns:
            Array de demanda horaria (8760,) en kW
        """
        annual_demand = np.zeros(8760, dtype=float)

        for t in range(8760):
            annual_demand[t] = self.calculate_fleet_demand_hourly(occupancy_matrix, t)

        return annual_demand


def create_ev_configs_iquitos() -> Tuple[List[EVChargerConfig], List[EVChargerConfig]]:
    """Crea configuraciones de chargers para Iquitos.

    Returns:
        Tupla (configs_motos, configs_mototaxis)
    """
    # Configuración de motos (112 chargers)
    moto_configs = [
        EVChargerConfig(
            charger_id=i,
            charger_type="moto",
            charger_power_kw=2.0,
            battery_capacity_kwh=2.5,  # Batería típica de moto eléctrica
            battery_soc_arrival=0.20,  # Llegan al 20% (cansados)
            battery_soc_target=0.90,   # Necesitan 90% para el día siguiente
        )
        for i in range(1, 113)
    ]

    # Configuración de mototaxis (16 chargers)
    mototaxi_configs = [
        EVChargerConfig(
            charger_id=i,
            charger_type="mototaxi",
            charger_power_kw=3.0,
            battery_capacity_kwh=4.5,  # Batería más grande
            battery_soc_arrival=0.25,  # Llegan al 25%
            battery_soc_target=0.85,   # Necesitan 85%
        )
        for i in range(113, 129)
    ]

    return moto_configs, mototaxi_configs


if __name__ == "__main__":
    # Ejemplo de uso
    logging.basicConfig(level=logging.INFO)

    # Crear configuraciones
    moto_configs, mototaxi_configs = create_ev_configs_iquitos()

    # Crear calculadora para primer moto
    calc = EVDemandCalculator(moto_configs[0])

    # Calcular métricas
    energy_req = calc.calculate_energy_required()
    charging_time = calc.calculate_charging_time()

    print(f"Charger 1 (Moto):")
    print(f"  Energía requerida: {energy_req:.2f} kWh")
    print(f"  Tiempo de carga: {charging_time:.2f} horas")
    print(f"  Potencia: {calc.config.charger_power_kw:.1f} kW")
    print(f"  Demanda @ hora 12: {calc.calculate_hourly_demand(12, 0, True):.2f} kW (conectado)")
    print(f"  Demanda @ hora 12: {calc.calculate_hourly_demand(12, 0, False):.2f} kW (desconectado)")
