"""
PREDICTOR DE TIEMPO DE CARGA
=============================

Calcula tiempo restante para cargar cada EV considerando:
- SOC actual
- Capacidad batería
- Curva de carga (no lineal: empieza rápido, termina lento)
- Potencia asignada
- Degradación térmica
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BatteryProfile:
    """Perfil de carga de una batería de EV."""
    ev_type: str  # "moto" o "mototaxi"
    capacity_kwh: float
    voltage_v: float = 48.0  # Típico motos
    max_charge_rate_c: float = 2.0  # 2C para motos rápidas
    min_soc_percent: float = 5.0
    max_soc_percent: float = 95.0

    @property
    def usable_capacity(self) -> float:
        """Capacidad utilizable (min-max)."""
        return self.capacity_kwh * (self.max_soc_percent - self.min_soc_percent) / 100.0

    def get_max_charge_power(self) -> float:
        """Potencia máxima de carga en kW."""
        return self.capacity_kwh * self.max_charge_rate_c


@dataclass
class ChargeTimingEstimate:
    """Estimación de tiempo de carga."""
    soc_initial: float
    soc_target: float
    power_assigned_kw: float
    battery_profile: BatteryProfile

    estimated_time_hours: float = 0.0
    confidence_percent: float = 0.0

    def calculate(self) -> None:
        """Calcular tiempo de carga basado en curva realista."""
        soc_delta = self.soc_target - self.soc_initial

        if soc_delta <= 0:
            self.estimated_time_hours = 0.0
            self.confidence_percent = 100.0
            return

        energy_needed = soc_delta * self.battery_profile.usable_capacity

        # Simulación de curva de carga (típica Li-ion)
        # Fase 1: Carga rápida (0-80%): lineal
        # Fase 2: Carga lenta (80-100%): exponencial

        if self.soc_initial < 0.80:
            # Fase rápida (lineal)
            if self.soc_target <= 0.80:
                # Completamente en fase rápida
                average_power = self.power_assigned_kw
                time_phase1 = energy_needed / max(average_power, 0.1)
                self.estimated_time_hours = time_phase1
            else:
                # Cruzar ambas fases
                energy_phase1 = (0.80 - self.soc_initial) * self.battery_profile.usable_capacity
                time_phase1 = energy_phase1 / max(self.power_assigned_kw, 0.1)

                energy_phase2 = (self.soc_target - 0.80) * self.battery_profile.usable_capacity
                # Fase lenta: potencia decrece a 50% máximo
                avg_power_phase2 = self.power_assigned_kw * 0.5
                time_phase2 = energy_phase2 / max(avg_power_phase2, 0.1)

                self.estimated_time_hours = time_phase1 + time_phase2
        else:
            # Completamente en fase lenta
            avg_power = self.power_assigned_kw * 0.5
            self.estimated_time_hours = energy_needed / max(avg_power, 0.1)

        # Ajuste por degradación térmica (batería caliente reduce velocidad)
        # Si carga > 2 horas, degradación térmica
        if self.estimated_time_hours > 2.0:
            degradation_factor = 1.0 + (self.estimated_time_hours - 2.0) * 0.05
            self.estimated_time_hours *= degradation_factor

        # Confianza disminuye con tiempo largo
        self.confidence_percent = max(50.0, 100.0 - self.estimated_time_hours * 5)


class ChargeTimePredictor:
    """
    Predice tiempo de carga para todos los EVs en el sistema.
    """

    def __init__(self) -> None:
        """Inicializar con perfiles estándar."""
        self.battery_profiles: Dict[str, BatteryProfile] = {
            "moto": BatteryProfile(
                ev_type="moto",
                capacity_kwh=2.5,  # Típico: moto 125cc equivale a 2.5 kWh
                max_charge_rate_c=2.0,
            ),
            "mototaxi": BatteryProfile(
                ev_type="mototaxi",
                capacity_kwh=5.0,  # Mayor rango: taxis viajan más
                max_charge_rate_c=1.5,
            ),
        }

    def predict_charge_time(
        self,
        charger_id: int,
        ev_type: str,
        soc_current: float,
        soc_target: float,
        power_assigned_kw: float,
    ) -> ChargeTimingEstimate:
        """
        Predecir tiempo de carga para un EV.

        Args:
            charger_id: ID del charger
            ev_type: "moto" o "mototaxi"
            soc_current: SOC actual [0, 1]
            soc_target: SOC objetivo [0, 1]
            power_assigned_kw: Potencia asignada en kW

        Returns:
            ChargeTimingEstimate con tiempo predicho
        """
        if ev_type not in self.battery_profiles:
            logger.warning(f"Tipo EV desconocido: {ev_type}, usando moto")
            ev_type = "moto"

        profile = self.battery_profiles[ev_type]

        estimate = ChargeTimingEstimate(
            soc_initial=soc_current,
            soc_target=soc_target,
            power_assigned_kw=power_assigned_kw,
            battery_profile=profile,
        )
        estimate.calculate()

        return estimate

    def predict_all_chargers(
        self,
        charger_states: Dict[int, Dict],  # {charger_id: {ev_type, soc, power_assigned, ...}}
        soc_target: float = 0.95,
    ) -> Dict[int, ChargeTimingEstimate]:
        """
        Predecir tiempo de carga para todos los chargers.

        Returns:
            {charger_id: ChargeTimingEstimate}
        """
        estimates = {}

        for charger_id, state in charger_states.items():
            if not state.get("occupied", False):
                continue

            ev_type = state.get("ev_type", "moto")
            soc_current = state.get("soc", 0.0)
            power_assigned = state.get("power_assigned", 0.0)

            estimate = self.predict_charge_time(
                charger_id=charger_id,
                ev_type=ev_type,
                soc_current=soc_current,
                soc_target=soc_target,
                power_assigned_kw=power_assigned,
            )

            estimates[charger_id] = estimate

        return estimates

    def print_charge_forecast(
        self,
        charger_states: Dict[int, Dict],
        current_hour: int,
        soc_target: float = 0.95,
    ) -> None:
        """
        Imprimir previsión de cargas.
        """
        estimates = self.predict_all_chargers(charger_states, soc_target)

        if not estimates:
            print("Sin EVs conectados actualmente")
            return

        print(f"\n{'='*120}")
        print(f"{'PREVISIÓN DE CARGAS':^120} (Hora actual: {current_hour}:00)")
        print(f"{'='*120}")
        print(f"{'ID':<5} {'Tipo':<10} {'SOC':<10} {'Objetivo':<10} {'Potencia':<15} {'Tiempo Est.':<15} {'Hora Fin':<12} {'Confianza':<10}")
        print(f"{'-'*120}")

        # Ordenar por tiempo de carga (más urgentes primero)
        sorted_estimates = sorted(
            estimates.items(),
            key=lambda x: x[1].estimated_time_hours
        )

        for charger_id, estimate in sorted_estimates:
            state = charger_states[charger_id]
            ev_type = state.get("ev_type", "moto")
            soc_current = estimate.soc_initial

            time_hours = estimate.estimated_time_hours
            finish_hour = (current_hour + time_hours) % 24

            # Colorear urgencia
            if time_hours < 0.5:
                urgency_mark = "✓ PRONTO"
            elif time_hours < 2.0:
                urgency_mark = "→ NORMAL"
            else:
                urgency_mark = "ⓘ LENTO"

            print(
                f"{charger_id:<5} {ev_type:<10} "
                f"{soc_current:>6.1%}    {estimate.soc_target:>6.1%} "
                f"{estimate.power_assigned_kw:>6.2f} kW    "
                f"{time_hours:>6.2f}h ({urgency_mark:<10}) "
                f"{finish_hour:>6.0f}:00        "
                f"{estimate.confidence_percent:>6.0f}%"
            )

        print(f"{'-'*120}")

        # Estadísticas
        avg_time = np.mean([e.estimated_time_hours for e in estimates.values()])
        max_time = max([e.estimated_time_hours for e in estimates.values()])
        total_energy_needed = sum([
            (e.soc_target - e.soc_initial) * e.battery_profile.usable_capacity
            for e in estimates.values()
        ])

        print(f"Resumen: {len(estimates)} EVs | Tiempo promedio: {avg_time:.2f}h | Máximo: {max_time:.2f}h | Energía total: {total_energy_needed:.1f} kWh")
        print(f"{'='*120}\n")

    def get_urgency_ranking(
        self,
        charger_states: Dict[int, Dict],
        soc_target: float = 0.95,
    ) -> List[Tuple[int, float, float]]:
        """
        Ranking de urgencia (charger_id, urgency_score, time_remaining).

        Mayor urgency_score = más urgente
        """
        estimates = self.predict_all_chargers(charger_states, soc_target)

        ranking = []
        for charger_id, estimate in estimates.items():
            # Urgency = (capacidad faltante) / (tiempo disponible)
            energy_pct = estimate.soc_target - estimate.soc_initial
            time_available = max(estimate.estimated_time_hours, 0.1)
            urgency = energy_pct / time_available

            ranking.append((charger_id, urgency, estimate.estimated_time_hours))

        # Ordenar por urgencia (descendente)
        return sorted(ranking, key=lambda x: x[1], reverse=True)


class ChargeScheduler:
    """
    Programador de cargas que respeta restricciones de tiempo.

    Objetivo: Maximizar EVs completamente cargados considerando:
    - Tiempo disponible hasta cierre del mall
    - Potencia total disponible
    - Prioridades de usuario
    """

    def __init__(self, mall_closing_hour: int = 22) -> None:
        """
        Inicializar programador.

        Args:
            mall_closing_hour: Hora de cierre del mall (0-23)
        """
        self.mall_closing_hour = mall_closing_hour
        self.predictor = ChargeTimePredictor()

    def get_feasible_completions(
        self,
        current_hour: int,
        charger_states: Dict[int, Dict],
        available_power_kw: float,
    ) -> Dict:
        """
        Calcular qué EVs pueden completar carga antes de cierre.

        Returns:
            {
                "feasible": [charger_ids],  # Pueden terminar a tiempo
                "marginal": [charger_ids],  # Tiempo ajustado pero posible
                "infeasible": [charger_ids],  # Necesitarían extender horario
            }
        """
        time_to_closing = (self.mall_closing_hour - current_hour) % 24
        if time_to_closing == 0:
            time_to_closing = 24

        estimates = self.predictor.predict_all_chargers(charger_states)

        feasible = []
        marginal = []
        infeasible = []

        for charger_id, estimate in estimates.items():
            if estimate.estimated_time_hours <= time_to_closing * 0.9:  # 90% margen
                feasible.append(charger_id)
            elif estimate.estimated_time_hours <= time_to_closing:
                marginal.append(charger_id)
            else:
                infeasible.append(charger_id)

        return {
            "feasible": feasible,
            "marginal": marginal,
            "infeasible": infeasible,
            "time_to_closing": time_to_closing,
        }

    def print_charge_summary(
        self,
        current_hour: int,
        charger_states: Dict[int, Dict],
        available_power_kw: float,
    ) -> None:
        """Imprimir resumen de cargas posibles."""
        feasibility = self.get_feasible_completions(
            current_hour, charger_states, available_power_kw
        )

        print(f"\n{'='*100}")
        print(f"{'ANÁLISIS DE FACTIBILIDAD DE CARGAS':^100}")
        time_avail = feasibility["time_to_closing"]
        print(f"{'Hora actual: ' + f'{current_hour}:00 | Cierre: {self.mall_closing_hour}:00 | Tiempo disponible: {time_avail:.1f}h':^100}")
        print(f"{'='*100}")

        print(f"\n✓ FACTIBLES (terminan a tiempo): {len(feasibility['feasible'])} EVs")
        for charger_id in feasibility['feasible'][:5]:
            print(f"  - Charger {charger_id}")

        print(f"\n⚠ MARGINALES (tiempo ajustado): {len(feasibility['marginal'])} EVs")
        for charger_id in feasibility['marginal'][:5]:
            print(f"  - Charger {charger_id}")

        print(f"\n✗ NO FACTIBLES (necesitan extender): {len(feasibility['infeasible'])} EVs")
        for charger_id in feasibility['infeasible'][:5]:
            print(f"  - Charger {charger_id}")

        print(f"\n{'='*100}\n")
