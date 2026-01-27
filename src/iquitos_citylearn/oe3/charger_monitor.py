"""
MONITOR EN TIEMPO REAL - ESTADO DE MOTOS Y MOTOTAXIS
=====================================================

Visualiza estado de carga por charger:
- SOC actual (%)
- Tiempo restante para cargar
- Potencia asignada vs solicitada
- Prioridad de carga
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ChargerMonitor:
    """Monitorea estado de todos los chargers y EVs conectados."""

    total_chargers: int = 128
    chargers_per_type: Dict[str, int] = None  # {"motos": 32, "mototaxis": 96}

    def __post_init__(self):
        if self.chargers_per_type is None:
            # Iquitos EV Mall típico
            self.chargers_per_type = {
                "motos": 32,      # 2 kW cada una
                "mototaxis": 96,  # 3 kW cada una
            }

    def get_charger_type(self, charger_id: int) -> str:
        """Obtener tipo de charger por ID."""
        if charger_id < 32:
            return "moto"
        else:
            return "mototaxi"

    def get_charger_max_power(self, charger_id: int) -> float:
        """Obtener potencia máxima del charger."""
        charger_type = self.get_charger_type(charger_id)
        return 2.0 if charger_type == "moto" else 3.0

    def calculate_charge_priority(
        self,
        soc: float,  # 0-1
        time_to_charge: float,  # horas
        battery_capacity: float,  # kWh
    ) -> float:
        """
        Calcular prioridad de carga (0-1).

        Mayor prioridad:
        - SOC bajo (falta cargar mucho)
        - Tiempo limitado (urgencia)

        Returns:
            Prioridad [0, 1] donde 1=máxima urgencia
        """
        # Factor 1: Capacidad restante (0-1)
        capacity_factor = 1.0 - soc

        # Factor 2: Urgencia temporal (decrece con tiempo disponible)
        # Si time_to_charge es muy bajo, urgencia es alta
        time_urgency = 1.0 / (1.0 + time_to_charge)  # Normalizado

        # Factor 3: Energía absoluta faltante
        energy_factor = ((1.0 - soc) * battery_capacity) / 10.0  # Normalizado a 10 kWh

        # Prioridad combinada (promedio ponderado)
        priority = (
            0.4 * capacity_factor +
            0.4 * time_urgency +
            0.2 * energy_factor
        )

        return min(1.0, priority)

    def print_charger_status(
        self,
        charger_states: Dict[int, Dict],  # {charger_id: {soc, time_to_charge, occupied, power_assigned, ...}}
        power_available_kw: float,
    ) -> None:
        """
        Imprimir estado visual de todos los chargers.

        Args:
            charger_states: Diccionario con estado de cada charger
            power_available_kw: Potencia disponible para distribución
        """
        print("\n" + "="*140)
        print(f"{'ESTADO DE CHARGERS':^140}")
        print(f"{'Potencia disponible para EVs: ' + f'{power_available_kw:.1f} kW':^140}")
        print("="*140)

        # Separar por tipo
        motos_states = {}
        mototaxis_states = {}

        for charger_id, state in charger_states.items():
            if self.get_charger_type(charger_id) == "moto":
                motos_states[charger_id] = state
            else:
                mototaxis_states[charger_id] = state

        # Imprimir motos
        print(f"\n{'─'*140}")
        print(f"MOTOS (32 chargers × 2 kW = 64 kW max)")
        print(f"{'─'*140}")
        print(f"{'ID':<5} {'Tipo':<8} {'SOC':<10} {'Carga':<20} {'Tiempo':<12} {'Potencia':<20} {'Prioridad':<15} {'Estado':<15}")
        print(f"{'─'*140}")

        for charger_id in sorted(motos_states.keys()):
            state = motos_states[charger_id]
            self._print_charger_row(charger_id, state)

        # Imprimir mototaxis
        print(f"\n{'─'*140}")
        print(f"MOTOTAXIS (96 chargers × 3 kW = 288 kW max)")
        print(f"{'─'*140}")
        print(f"{'ID':<5} {'Tipo':<8} {'SOC':<10} {'Carga':<20} {'Tiempo':<12} {'Potencia':<20} {'Prioridad':<15} {'Estado':<15}")
        print(f"{'─'*140}")

        for charger_id in sorted(mototaxis_states.keys()):
            state = mototaxis_states[charger_id]
            self._print_charger_row(charger_id, state)

        # Estadísticas
        occupied = sum(1 for s in charger_states.values() if s.get("occupied", False))
        print(f"\n{'─'*140}")
        print(f"RESUMEN: {occupied}/{self.total_chargers} chargers ocupados | Carga promedio: {np.mean([s.get('soc', 0) for s in charger_states.values()]):.1%}")
        print("="*140 + "\n")

    def _print_charger_row(self, charger_id: int, state: Dict) -> None:
        """Imprimir una fila de charger."""
        charger_type = self.get_charger_type(charger_id)
        type_str = "MOTO" if charger_type == "moto" else "TAXI"

        soc = state.get("soc", 0.0)
        battery_capacity = state.get("battery_capacity", 10.0)
        time_to_charge = state.get("time_to_charge", 99.9)
        power_assigned = state.get("power_assigned", 0.0)
        occupied = state.get("occupied", False)

        # Barra de carga
        bar_length = 15
        filled = int(soc * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Cálculo de prioridad
        priority = self.calculate_charge_priority(soc, time_to_charge, battery_capacity)
        priority_bar = "★" * int(priority * 5)  # 0-5 estrellas

        # Estado
        if not occupied:
            estado = "VACÍO"
        elif soc >= 0.95:
            estado = "COMPLETO"
        elif soc >= 0.80:
            estado = "CASI LLENO"
        elif soc >= 0.50:
            estado = "CARGANDO"
        else:
            estado = "🔴 URGENTE"

        # Potencia
        max_power = self.get_charger_max_power(charger_id)
        power_str = f"{power_assigned:.2f}/{max_power:.1f} kW"

        # Tiempo
        if time_to_charge > 90:
            time_str = "—"
        else:
            time_str = f"{time_to_charge:.1f}h"

        # Imprimir fila
        print(
            f"{charger_id:<5} {type_str:<8} "
            f"{soc:>6.1%}  {bar:<20} "
            f"{time_str:<12} {power_str:<20} "
            f"{priority_bar:<15} {estado:<15}"
        )

    def get_charger_report(self, charger_states: Dict[int, Dict]) -> Dict[str, any]:
        """
        Generar reporte ejecutivo de estado de chargers.

        Returns:
            Dict con estadísticas agregadas
        """
        occupied_count = sum(1 for s in charger_states.values() if s.get("occupied", False))
        avg_soc = np.mean([s.get("soc", 0) for s in charger_states.values()])

        # Urgentes (SOC < 20% y ocupados)
        urgent_count = sum(
            1 for s in charger_states.values()
            if s.get("occupied", False) and s.get("soc", 0) < 0.20
        )

        # Calculando cargas
        charging_count = sum(
            1 for s in charger_states.values()
            if s.get("occupied", False) and s.get("soc", 0) < 0.95
        )

        return {
            "total_chargers": self.total_chargers,
            "occupied_chargers": occupied_count,
            "occupancy_rate": occupied_count / self.total_chargers,
            "avg_soc": avg_soc,
            "urgent_count": urgent_count,
            "charging_count": charging_count,
        }


class PowerAllocationStrategy:
    """
    Estrategia de distribución de potencia entre chargers.

    Opciones:
    1. EQUITATIVA: Distribuir partes iguales
    2. PRIORIDAD: Más potencia a urgentes
    3. VELOCIDAD: Máximo para terminar rápido
    """

    @staticmethod
    def distribute_equitable(
        available_power_kw: float,
        charger_demands: List[Tuple[int, float]],  # [(charger_id, requested_kw)]
    ) -> Dict[int, float]:
        """
        Distribuir potencia equitativamente entre chargers solicitantes.

        Si disponible > demanda total: saturable todos
        Si disponible < demanda total: proporcional a demanda
        """
        if not charger_demands:
            return {}

        total_demand = sum(demand for _, demand in charger_demands)

        if total_demand <= available_power_kw:
            # Hay suficiente para todos
            return {charger_id: demand for charger_id, demand in charger_demands}

        # Racionamiento proporcional
        ratio = available_power_kw / total_demand
        return {
            charger_id: demand * ratio
            for charger_id, demand in charger_demands
        }

    @staticmethod
    def distribute_by_priority(
        available_power_kw: float,
        charger_priorities: List[Tuple[int, float, float]],  # [(charger_id, priority, requested_kw)]
    ) -> Dict[int, float]:
        """
        Distribuir potencia priorizando chargers por urgencia.

        Primero: máxima prioridad
        Luego: prioridades menores si quedan recursos
        """
        # Ordenar por prioridad (descendente)
        sorted_chargers = sorted(charger_priorities, key=lambda x: x[1], reverse=True)

        allocation = {}
        remaining_power = available_power_kw

        for charger_id, priority, requested_kw in sorted_chargers:
            # Asignar min(solicitado, disponible)
            power_assigned = min(requested_kw, remaining_power)
            allocation[charger_id] = power_assigned
            remaining_power -= power_assigned

            if remaining_power < 0.01:
                break

        return allocation

    @staticmethod
    def distribute_speed_optimized(
        available_power_kw: float,
        charger_states: List[Tuple[int, float, float, float]],  # [(charger_id, soc, time_to_charge, max_power)]
    ) -> Dict[int, float]:
        """
        Distribuir potencia para minimizar tiempo total de carga del sistema.

        Heurística: Mayor potencia a EVs que menos tiempo faltan
        """
        # Score = (1 - SOC) / time_to_charge
        # Más alto = más urgente
        scored = [
            (charger_id, (1.0 - soc) / max(ttc, 0.1), min(requested, max_power))
            for charger_id, soc, ttc, max_power, requested in charger_states
        ]

        # Ordenar por score
        sorted_chargers = sorted(scored, key=lambda x: x[1], reverse=True)

        allocation = {}
        remaining_power = available_power_kw

        for charger_id, score, max_power in sorted_chargers:
            power_assigned = min(max_power, remaining_power)
            allocation[charger_id] = power_assigned
            remaining_power -= power_assigned

            if remaining_power < 0.01:
                break

        return allocation
