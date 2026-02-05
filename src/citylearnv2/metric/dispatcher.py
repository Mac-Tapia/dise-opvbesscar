"""
SISTEMA DE DESPACHO INTELIGENTE DE ENERGÍA - IQUITOS EV MALL
============================================================

Arquitectura de despacho que sigue REGLAS DE PRIORIDAD ESTRICTAS:
1. SOLAR → CARGA DE EVs (prioridad máxima)
2. SOLAR EXCESO → CARGA DE BESS
3. SOLAR EXCESO → DEMANDA REAL MALL
4. BESS MAÑANA → Cargar durante solar
5. BESS TARDE/NOCHE → Descargar solo para EVs (NO para mall)
6. GRID IMPORT → Solo si deficit total

Objetivo principal: MINIMIZAR CO₂ (grid Iquitos = 0.4521 kg CO₂/kWh)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class EVChargeState:
    """Estado de carga de un EV en un charger."""
    charger_id: int
    socket_id: int
    ev_type: str  # "moto" (2kW) o "mototaxi" (3kW)
    battery_soc: float  # Estado de carga [0, 1]
    battery_capacity_kwh: float  # Capacidad en kWh
    time_to_charge_hours: float  # Horas restantes para cargar completamente
    is_occupied: bool  # ¿Hay EV conectado?
    power_requested_kw: float  # Potencia que pide el EV

    @property
    def charge_needed_kwh(self) -> float:
        """kWh faltantes para cargar 100%."""
        return (1.0 - self.battery_soc) * self.battery_capacity_kwh

    @property
    def current_power_request(self) -> float:
        """Potencia actual solicitada (decrece a medida que llena)."""
        if not self.is_occupied:
            return 0.0
        # Simulación: potencia decrece a medida que SOC sube (curva carga Li)
        return float(self.power_requested_kw * (1.0 - self.battery_soc ** 0.5))


@dataclass
class EnergyBalance:
    """Estado energético instantáneo del sistema."""
    solar_generation_kw: float
    mall_demand_kw: float
    ev_demand_total_kw: float  # Total demanda EVs sin restricciones
    bess_soc_percent: float
    bess_capacity_kwh: float
    bess_power_kw: float  # Potencia max carga/descarga
    grid_carbon_intensity: float = 0.4521  # kg CO₂/kWh
    tariff_usd_kwh: float = 0.20
    hour_of_day: int = 0


@dataclass
class DispatchRule:
    """Regla única de despacho."""
    priority: int  # 1=máxima, 5=mínima
    rule_name: str
    source: str  # "solar", "bess", "grid"
    target: str  # "ev", "bess", "mall", "grid"
    condition: str  # Descripción de cuándo aplica
    power_allocated_kw: float = 0.0


@dataclass
class DispatchDecision:
    """Decisión de despacho para un timestep."""
    solar_to_ev_kw: float = 0.0
    solar_to_bess_kw: float = 0.0
    solar_to_mall_kw: float = 0.0
    solar_wasted_kw: float = 0.0

    bess_to_ev_kw: float = 0.0
    bess_charge_from_solar_kw: float = 0.0

    grid_import_total_kw: float = 0.0
    grid_import_for_ev_kw: float = 0.0
    grid_import_for_mall_kw: float = 0.0

    co2_emitted_kg: float = 0.0
    cost_incurred_usd: float = 0.0

    rules_applied: List[DispatchRule] = field(default_factory=list)

    def summary(self) -> Dict[str, float]:
        """Resumen ejecutivo del despacho."""
        return {
            "solar_total": self.solar_to_ev_kw + self.solar_to_bess_kw + self.solar_to_mall_kw,
            "solar_to_ev": self.solar_to_ev_kw,
            "solar_to_bess": self.solar_to_bess_kw,
            "solar_wasted": self.solar_wasted_kw,
            "bess_discharge": self.bess_to_ev_kw,
            "grid_import": self.grid_import_total_kw,
            "co2_kg": self.co2_emitted_kg,
            "cost_usd": self.cost_incurred_usd,
        }


class EnergyDispatcher:
    """
    Despachador de energía que sigue reglas de prioridad estricta.

    REGLAS DE DESPACHO (orden de ejecución):
    =========================================
    1. SOLAR → EVs
       - Satura primero los EVs con demanda inmediata
       - Si solar < ev_demand: distribuir proporcionalmente

    2. SOLAR EXCESO → BESS (solo mañana/madrugada)
       - Si hora_almacenamiento (5-11h): cargar BESS si SOC < 90%
       - Tasa: min(solar_exceso, bess_power, (100% - bess_soc) / time_remaining)

    3. SOLAR EXCESO → MALL
       - Cubrir demanda real del mall
       - Secundario a EVs

    4. BESS → EVs (tarde/noche)
       - Si solar < ev_demand y BESS SOC > min_soc:
       - Descargar primero para EVs (nunca para mall)

    5. GRID → Deficit total
       - Si (solar + bess) < (ev_demand + mall_demand)
       - Importar grid solo lo necesario
    """

    def __init__(self, bess_config: Dict[str, float]):
        """
        Inicializar despachador.

        Args:
            bess_config: {"capacity_kwh": 4520, "power_kw": 2712, "min_soc": 0.10, ...}
        """
        self.bess_capacity = bess_config.get("capacity_kwh", 4520)
        self.bess_power_max = bess_config.get("power_kw", 2712)
        self.bess_min_soc = bess_config.get("min_soc", 0.10)
        self.bess_max_soc = bess_config.get("max_soc", 0.95)
        self.bess_efficiency = bess_config.get("efficiency", 0.92)

        # Horarios de operación
        self.ev_mall_hours = (9, 22)  # 9am-10pm operación
        self.solar_storage_hours = (5, 11)  # Mañana: almacenar solar
        self.peak_demand_hours = (18, 21)  # Pico: 6pm-9pm

        # Trackers
        self.dispatch_history: List[DispatchDecision] = []

        logger.info(
            f"EnergyDispatcher inicializado: "
            f"BESS {self.bess_capacity} kWh / {self.bess_power_max} kW, "
            f"SOC [{self.bess_min_soc:.0%}, {self.bess_max_soc:.0%}]"
        )

    def dispatch(
        self,
        balance: EnergyBalance,
        ev_states: List[EVChargeState],
        co2_weight: float = 0.50,
    ) -> DispatchDecision:
        """
        Ejecutar despacho de energía para un timestep.

        Args:
            balance: Estado energético actual
            ev_states: Estados de todos los EVs
            co2_weight: Peso de CO₂ en decisiones (0.50 = máxima prioridad)

        Returns:
            DispatchDecision con detalles del despacho
        """
        decision = DispatchDecision()

        # Calcular demandas
        ev_demand_immediate = sum(
            ev.current_power_request for ev in ev_states if ev.is_occupied
        )
        _ = sum(
            ev.charge_needed_kwh / max(ev.time_to_charge_hours, 0.1)
            for ev in ev_states
            if ev.is_occupied
        )

        solar_available = balance.solar_generation_kw
        mall_demand = balance.mall_demand_kw
        bess_soc = balance.bess_soc_percent / 100.0

        # ========== REGLA 1: SOLAR → EVs ==========
        solar_to_ev = min(solar_available, ev_demand_immediate)
        decision.solar_to_ev_kw = solar_to_ev
        solar_remaining = solar_available - solar_to_ev

        # Log
        decision.rules_applied.append(DispatchRule(
            priority=1,
            rule_name="SOLAR → EVs",
            source="solar",
            target="ev",
            condition=f"ev_demand={ev_demand_immediate:.1f}kW",
            power_allocated_kw=solar_to_ev,
        ))

        # ========== REGLA 2: SOLAR EXCESO → BESS (mañana) ==========
        is_morning_storage = self.solar_storage_hours[0] <= balance.hour_of_day < self.solar_storage_hours[1]
        can_charge_bess = bess_soc < self.bess_max_soc and is_morning_storage

        if can_charge_bess and solar_remaining > 0:
            bess_soc_needed = (self.bess_max_soc - bess_soc) * self.bess_capacity
            bess_power_available = min(
                self.bess_power_max,
                bess_soc_needed / max(self.bess_efficiency, 1.0)
            )
            solar_to_bess = min(solar_remaining, bess_power_available)
            decision.solar_to_bess_kw = solar_to_bess
            solar_remaining -= solar_to_bess

            decision.rules_applied.append(DispatchRule(
                priority=2,
                rule_name="SOLAR EXCESO → BESS (almacenamiento mañana)",
                source="solar",
                target="bess",
                condition=f"mañana={is_morning_storage}, SOC={bess_soc:.0%}",
                power_allocated_kw=solar_to_bess,
            ))

        # ========== REGLA 3: SOLAR EXCESO → MALL ==========
        if solar_remaining > 0:
            solar_to_mall = min(solar_remaining, mall_demand)
            decision.solar_to_mall_kw = solar_to_mall
            solar_remaining -= solar_to_mall

            decision.rules_applied.append(DispatchRule(
                priority=3,
                rule_name="SOLAR EXCESO → MALL",
                source="solar",
                target="mall",
                condition=f"mall_demand={mall_demand:.1f}kW",
                power_allocated_kw=solar_to_mall,
            ))

        # Solar desperdiciado
        decision.solar_wasted_kw = max(0, solar_remaining)
        if decision.solar_wasted_kw > 0.1:
            decision.rules_applied.append(DispatchRule(
                priority=0,  # No aplicable
                rule_name="SOLAR DESPERDICIADO",
                source="solar",
                target="none",
                condition="exceso de generación",
                power_allocated_kw=decision.solar_wasted_kw,
            ))

        # ========== REGLA 4: BESS → EVs (tarde/noche) ==========
        is_discharge_time = balance.hour_of_day >= self.solar_storage_hours[1]
        ev_deficit = max(0, ev_demand_immediate - decision.solar_to_ev_kw)
        can_discharge_bess = bess_soc > self.bess_min_soc and is_discharge_time and ev_deficit > 0

        if can_discharge_bess:
            bess_energy_available = (bess_soc - self.bess_min_soc) * self.bess_capacity
            bess_power_available = min(self.bess_power_max, bess_energy_available)
            bess_to_ev = min(bess_power_available, ev_deficit)
            decision.bess_to_ev_kw = bess_to_ev

            decision.rules_applied.append(DispatchRule(
                priority=4,
                rule_name="BESS → EVs (tarde/noche)",
                source="bess",
                target="ev",
                condition=f"tarde={is_discharge_time}, ev_deficit={ev_deficit:.1f}kW, SOC={bess_soc:.0%}",
                power_allocated_kw=bess_to_ev,
            ))

        # ========== REGLA 5: GRID IMPORT (solo deficit) ==========
        total_ev_power = decision.solar_to_ev_kw + decision.bess_to_ev_kw
        ev_deficit_after_bess = max(0, ev_demand_immediate - total_ev_power)
        mall_deficit = max(0, mall_demand - decision.solar_to_mall_kw)

        grid_for_ev = ev_deficit_after_bess
        grid_for_mall = mall_deficit
        decision.grid_import_total_kw = grid_for_ev + grid_for_mall
        decision.grid_import_for_ev_kw = grid_for_ev
        decision.grid_import_for_mall_kw = grid_for_mall

        if decision.grid_import_total_kw > 0.1:
            decision.rules_applied.append(DispatchRule(
                priority=5,
                rule_name="GRID IMPORT (deficit total)",
                source="grid",
                target="ev+mall",
                condition=f"deficit={decision.grid_import_total_kw:.1f}kW",
                power_allocated_kw=decision.grid_import_total_kw,
            ))

        # ========== CÁLCULO DE IMPACTO CO₂ Y COSTO ==========
        decision.co2_emitted_kg = decision.grid_import_total_kw * balance.grid_carbon_intensity
        decision.cost_incurred_usd = decision.grid_import_total_kw * balance.tariff_usd_kwh

        # Almacenar en histórico
        self.dispatch_history.append(decision)

        return decision

    def get_charger_power_allocation(
        self,
        charger_id: int,
        ev_state: EVChargeState,
        available_power_for_ev_kw: float,
    ) -> float:
        """
        Asignar potencia a un charger específico (control independiente).

        Args:
            charger_id: ID del charger (0-127)
            ev_state: Estado del EV en este charger
            available_power_for_ev_kw: Potencia total disponible para EVs

        Returns:
            Potencia a asignar a este charger (kW)
        """
        if not ev_state.is_occupied:
            return 0.0

        # Prioridad: mayor potencia a los EVs que faltan más tiempo
        time_coefficient = 1.0 / max(ev_state.time_to_charge_hours, 0.1)

        # Limitar a capacidad del charger
        power_requested = ev_state.current_power_request

        # Distribuir equitativamente si hay limitación
        power_allocated = min(power_requested, available_power_for_ev_kw * time_coefficient)

        return max(0.0, power_allocated)

    def calculate_charge_time_remaining(
        self,
        ev_state: EVChargeState,
        power_allocated_kw: float,
    ) -> float:
        """
        Calcular tiempo restante para cargar completamente.

        Args:
            ev_state: Estado actual del EV
            power_allocated_kw: Potencia asignada

        Returns:
            Horas restantes para cargar al 100%
        """
        if power_allocated_kw < 0.01:
            return float('inf')

        charge_needed = ev_state.charge_needed_kwh

        # Simulación de curva de carga (decrece con SOC)
        average_power = power_allocated_kw * (1.0 - ev_state.battery_soc ** 0.5) / 2.0

        if average_power < 0.01:
            return float('inf')

        return float(charge_needed / average_power)

    def get_summary_stats(self) -> Dict[str, float]:
        """
        Obtener estadísticas del despacho en el período.

        Returns:
            Dict con métricas agregadas
        """
        if not self.dispatch_history:
            return {}

        df_history = pd.DataFrame([
            d.summary() for d in self.dispatch_history
        ])

        return {
            "total_solar_used_kwh": df_history["solar_total"].sum(),
            "total_solar_wasted_kwh": df_history["solar_wasted"].sum(),
            "total_bess_charge_kwh": df_history["solar_to_bess"].sum(),
            "total_bess_discharge_kwh": df_history["bess_discharge"].sum(),
            "total_grid_import_kwh": df_history["grid_import"].sum(),
            "total_co2_kg": df_history["co2_kg"].sum(),
            "total_cost_usd": df_history["cost_usd"].sum(),
            "solar_efficiency": df_history["solar_total"].sum() / (df_history["solar_total"].sum() + df_history["solar_wasted"].sum() + 0.01),
        }


def validate_dispatch(decision: DispatchDecision, balance: EnergyBalance) -> bool:
    """
    Validar que el despacho respete las reglas de balance energético.

    Returns:
        True si el despacho es válido, False si viola alguna restricción
    """
    total_supply = (
        decision.solar_to_ev_kw +
        decision.solar_to_bess_kw +
        decision.solar_to_mall_kw +
        decision.bess_to_ev_kw +
        decision.grid_import_total_kw
    )

    total_demand = balance.ev_demand_total_kw + balance.mall_demand_kw

    # Tolerancia: 1% por pérdidas
    if total_supply > total_demand * 1.01:
        logger.warning(
            f"⚠️ ADVERTENCIA: Supply ({total_supply:.1f}kW) > demand ({total_demand:.1f}kW)"
        )
        return False

    return True
