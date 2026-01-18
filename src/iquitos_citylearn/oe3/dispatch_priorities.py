"""
Despacho de Energía con Prioridades para Control Operativo.

Implementa el flujo de despacho ordenado por prioridades:
1. FV → EV (Directo a carga de vehículos)
2. FV excedente → BESS (Guardar lo que sobra)
3. BESS → EV (Cuando cae el sol, usar batería para EVs)
4. BESS excedente → Mall (Si batería está saturada, cargar demanda del mall)

Sin modificar capacidades: BESS 2000 kWh, Solar 4162 kWp, Chargers 272 kW
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class DispatchPriorities:
    """Configuración de prioridades de despacho de energía."""
    
    # Umbrales de luz solar (kWh/h)
    pv_night_threshold_kwh: float = 0.1       # Considerar noche si PV < esto
    pv_day_threshold_kwh: float = 0.5         # Considerar día si PV ≥ esto
    
    # Límites de BESS
    bess_soc_max_percent: float = 95.0        # No cargar más de 95%
    bess_soc_min_percent: float = 20.0        # No descargar bajo 20%
    bess_power_max_kw: float = 1200.0         # Potencia máxima BESS
    
    # Límites de EV
    ev_power_limit_kw: float = 150.0          # Límite agregado chargers
    
    # Límites de Mall
    mall_power_max_kw: float = 500.0          # Potencia máxima mall (típico pico)


@dataclass
class DispatchState:
    """Estado del despacho en un timestep."""
    
    hour: int                                  # Hora del día (0-23)
    is_peak_hour: bool                        # True si 18-21h
    
    # Disponibilidades
    pv_power_kw: float                        # Potencia solar actual [kW]
    bess_soc_percent: float                   # SOC actual [%]
    bess_capacity_kwh: float                  # Capacidad total BESS [kWh]
    bess_power_available_kw: float            # Potencia máx descarga disponible [kW]
    
    # Demandas
    ev_demand_kw: float                       # Demanda instantánea EVs [kW]
    mall_demand_kw: float                     # Demanda instantánea mall [kW]
    
    # Límites operacionales
    ev_power_limit_kw: float = 150.0          # Límite despacho EVs
    bess_soc_target_percent: float = 60.0     # SOC objetivo actual


@dataclass
class DispatchPlan:
    """Plan de despacho para un timestep (acción a tomar)."""
    
    # Flujos de potencia (kW)
    pv_to_ev_kw: float = 0.0                  # Directamente a EVs
    pv_to_bess_kw: float = 0.0                # A batería
    pv_to_mall_kw: float = 0.0                # Al mall
    
    # Descarga BESS
    bess_to_ev_kw: float = 0.0                # BESS → EVs
    bess_to_mall_kw: float = 0.0              # BESS → Mall (si BESS saturada)
    
    # Importación (deficit)
    grid_import_kw: float = 0.0               # Importación desde red
    
    # Estado
    bess_charging: bool = False               # True si BESS se está cargando
    bess_discharging: bool = False            # True si BESS se está descargando
    
    # Justificación (para logging)
    priority_sequence: str = ""               # Secuencia de prioridades ejecutada


class EnergyDispatcher:
    """
    Ejecuta despacho de energía siguiendo prioridades ordenadas.
    
    Algoritmo:
    
    1. **FV → EV** (Prioridad máxima)
       - Si hay sol (PV > umbral) y demanda EV:
         - Enviar min(PV, EV_demand, EV_limit) a EVs
    
    2. **FV excedente → BESS** (Segunda prioridad)
       - Si PV excedente > 0 y BESS no saturada:
         - Enviar min(PV_excedente, BESS_power, capacidad_restante) a BESS
    
    3. **BESS → EV** (Tercera prioridad, especialmente noche)
       - Si no hay sol (PV < umbral) y BESS > SOC_min:
         - Usar BESS para atender demanda EV
    
    4. **BESS → Mall (si saturada)** (Cuarta prioridad)
       - Si BESS está saturada (SOC > 95%) y sobra FV:
         - Cargar mall para "descargar" el exceso de BESS
    
    5. **Grid Import** (Último recurso)
       - Si todo lo anterior insuficiente, importar desde red
    """
    
    def __init__(self, priorities: Optional[DispatchPriorities] = None):
        """
        Args:
            priorities: Configuración de prioridades y umbrales
        """
        self.priorities = priorities or DispatchPriorities()
    
    def is_daytime(self, pv_power_kw: float) -> bool:
        """Determina si hay luz solar."""
        return pv_power_kw >= self.priorities.pv_day_threshold_kwh
    
    def is_nighttime(self, pv_power_kw: float) -> bool:
        """Determina si es noche."""
        return pv_power_kw < self.priorities.pv_night_threshold_kwh
    
    def dispatch(self, state: DispatchState) -> DispatchPlan:
        """
        Ejecuta despacho siguiendo prioridades.
        
        Args:
            state: Estado actual (demandas, generación, SOC, etc.)
        
        Returns:
            Plan de despacho con flujos a ejecutar
        """
        
        plan = DispatchPlan()
        priority_log = []
        
        # Disponibilidad de energía
        pv_available = state.pv_power_kw
        bess_soc_kwh = state.bess_capacity_kwh * state.bess_soc_percent / 100.0
        bess_remaining_kwh = state.bess_capacity_kwh * (100 - state.bess_soc_percent) / 100.0
        
        is_daytime = self.is_daytime(state.pv_power_kw)
        is_nighttime = self.is_nighttime(state.pv_power_kw)
        bess_saturated = state.bess_soc_percent >= 95.0  # >= para activar a 95%
        bess_depleted = state.bess_soc_percent <= self.priorities.bess_soc_min_percent
        
        # ==================== PRIORIDAD 1: FV → EV ====================
        if is_daytime and state.ev_demand_kw > 0 and pv_available > 0:
            pv_to_ev = min(
                pv_available,
                state.ev_demand_kw,
                state.ev_power_limit_kw
            )
            plan.pv_to_ev_kw = pv_to_ev
            pv_available -= pv_to_ev
            priority_log.append(f"P1_FV→EV:{pv_to_ev:.1f}kW")
        
        # ==================== PRIORIDAD 2: FV excedente → BESS ====================
        if pv_available > 0 and not bess_saturated:
            # Capacidad de carga BESS (limitada por potencia y capacidad)
            bess_charge_power = min(
                pv_available,
                self.priorities.bess_power_max_kw,
                bess_remaining_kwh,  # Capacidad restante (kWh) ≈ potencia (kW) × 1h
            )
            plan.pv_to_bess_kw = bess_charge_power
            pv_available -= bess_charge_power
            bess_soc_kwh += bess_charge_power  # Actualizar SOC simulado
            plan.bess_charging = True
            priority_log.append(f"P2_FV→BESS:{bess_charge_power:.1f}kW")
        
        # ==================== PRIORIDAD 3: BESS → EV (especialmente noche) ====================
        if is_nighttime and state.ev_demand_kw > 0 and not bess_depleted:
            # Descarga BESS para EVs
            # Limitado por SOC disponible actualizado (después de P2 si aplica)
            bess_soc_actual_kwh = state.bess_capacity_kwh * state.bess_soc_percent / 100.0 - plan.pv_to_bess_kw
            
            bess_to_ev = min(
                state.ev_demand_kw,
                state.ev_power_limit_kw,
                max(0, bess_soc_actual_kwh),  # Limitado por SOC
                self.priorities.bess_power_max_kw,
            )
            
            plan.bess_to_ev_kw = bess_to_ev
            plan.bess_discharging = True
            priority_log.append(f"P3_BESS→EV:{bess_to_ev:.1f}kW")
            state.ev_demand_kw = max(0, state.ev_demand_kw - bess_to_ev)
        
        # ==================== PRIORIDAD 4: BESS saturada → Mall ====================
        # Si BESS está saturada y sobra FV, cargar mall para "descargar" BESS
        if bess_saturated and pv_available > 0 and state.mall_demand_kw > 0:
            pv_to_mall = min(pv_available, state.mall_demand_kw)
            plan.pv_to_mall_kw = pv_to_mall
            pv_available -= pv_to_mall
            priority_log.append(f"P4_FV→MALL(saturada):{pv_to_mall:.1f}kW")
        
        # ==================== PRIORIDAD 5: Grid Import (último recurso) ====================
        # Cubrir déficits con importación
        total_served_ev = plan.pv_to_ev_kw + plan.bess_to_ev_kw
        ev_deficit = max(0, state.ev_demand_kw - total_served_ev)
        
        total_served_mall = plan.pv_to_mall_kw + plan.bess_to_mall_kw
        mall_deficit = max(0, state.mall_demand_kw - total_served_mall)
        
        grid_import = ev_deficit + mall_deficit
        plan.grid_import_kw = grid_import
        
        if grid_import > 0:
            priority_log.append(f"P5_GRID:{grid_import:.1f}kW(deficit)")
        
        # Registrar secuencia
        plan.priority_sequence = " → ".join(priority_log) if priority_log else "NO_ACTION"
        
        return plan


def validate_dispatch_plan(
    plan: DispatchPlan,
    state: DispatchState,
    priorities: DispatchPriorities,
) -> Tuple[bool, str]:
    """
    Valida que el plan de despacho cumple restricciones.
    
    Returns:
        (is_valid, message)
    """
    
    errors = []
    
    # Validar límites EV
    ev_total = plan.pv_to_ev_kw + plan.bess_to_ev_kw
    if ev_total > priorities.ev_power_limit_kw * 1.01:  # Tolerancia 1%
        errors.append(f"EV total {ev_total:.1f} > límite {priorities.ev_power_limit_kw}")
    
    # Validar BESS no descarga más de lo disponible
    bess_soc_kwh = state.bess_capacity_kwh * state.bess_soc_percent / 100.0
    if plan.bess_to_ev_kw + plan.bess_to_mall_kw > bess_soc_kwh * 1.01:
        errors.append(f"BESS descarga excesiva")
    
    # Validar BESS no carga más de su capacidad
    bess_remaining = state.bess_capacity_kwh * (100 - state.bess_soc_percent) / 100.0
    if plan.pv_to_bess_kw > bess_remaining * 1.01:
        errors.append(f"BESS carga excesiva")
    
    # Validar flujos positivos
    for attr in ['pv_to_ev_kw', 'pv_to_bess_kw', 'pv_to_mall_kw', 
                 'bess_to_ev_kw', 'bess_to_mall_kw', 'grid_import_kw']:
        if getattr(plan, attr) < -0.01:
            errors.append(f"{attr} es negativo: {getattr(plan, attr)}")
    
    if errors:
        return False, " | ".join(errors)
    
    return True, "OK"


def compute_dispatch_reward_bonus(
    plan: DispatchPlan,
    state: DispatchState,
    co2_factor_kg_kwh: float = 0.4521,
) -> Dict[str, float]:
    """
    Calcula bonificaciones de recompensa por cumplimiento de prioridades.
    
    Returns:
        Dict con bonificaciones:
        - direct_solar_bonus: Usar FV directo a EVs (mejor)
        - battery_efficient_bonus: Usar batería eficientemente
        - grid_import_penalty: Penalidad por importación
    """
    
    rewards = {}
    
    # Bonus: Usar FV directamente a EVs (máxima prioridad cumplida)
    if plan.pv_to_ev_kw > 0:
        rewards["direct_solar_bonus"] = plan.pv_to_ev_kw * 0.01  # Bonus
    else:
        rewards["direct_solar_bonus"] = 0.0
    
    # Bonus: Cargar BESS cuando hay exceso FV (prepararse para pico)
    if plan.pv_to_bess_kw > 0 and not (plan.pv_to_ev_kw > 0):
        rewards["battery_charge_bonus"] = plan.pv_to_bess_kw * 0.005
    else:
        rewards["battery_charge_bonus"] = 0.0
    
    # Penalidad: Importación (especialmente en pico)
    import_penalty = plan.grid_import_kw * co2_factor_kg_kwh * 0.0001
    if state.is_peak_hour:
        import_penalty *= 2.0  # Penalidad 2x en pico
    rewards["grid_import_penalty"] = -import_penalty
    
    rewards["total_dispatch_reward"] = sum(rewards.values())
    
    return rewards
