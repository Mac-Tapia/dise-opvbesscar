#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE COMUNICACION INTER-DISPOSITIVOS
Chargers, BESS, Solar, Mall se comunican para distribucion optimizada
Basado en especificaciones v5.3 (Feb 2026)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


# ===== CHARGER COMMUNICATION (CARGADOR <-> SISTEMA) =====
@dataclass
class ChargerCommunication:
    """
    Comunicacion individual de cada cargador al sistema
    Reporta: estado carga, tiempo restante, energia necesaria
    """
    socket_id: int
    vehicle_type: str  # 'moto' o 'mototaxi'
    
    # Estado de carga (actualizado cada hora)
    current_soc: float = 0.0  # [0, 1] - Porcentaje carga actual
    soc_target: float = 1.0   # [0, 1] - Objetivo de carga (100% o menos)
    
    # Energia necesaria para completar carga
    energy_needed_kwh: float = 0.0  # kWh faltantes
    
    # Tiempo estimado para completar carga
    time_remaining_hours: float = 0.0
    
    # Potencia en uso ahora
    power_demanded_kw: float = 0.0
    
    # Historial de carga en este ciclo
    energy_charged_so_far_kwh: float = 0.0
    hours_charging: float = 0.0
    
    # Prioridad (1-10, donde 10 es maxima prioridad)
    priority_level: int = 5
    
    # Timestamp cuando se conecto
    connect_time_hour: Optional[int] = None
    
    def energy_still_needs(self) -> float:
        """Energia faltante para alcanzar target"""
        return max(0.0, self.energy_needed_kwh - self.energy_charged_so_far_kwh)
    
    def percent_complete(self) -> float:
        """Porcentaje completado de la carga"""
        if self.energy_needed_kwh <= 0:
            return 1.0
        return min(1.0, self.energy_charged_so_far_kwh / self.energy_needed_kwh)
    
    def is_urgent(self) -> bool:
        """Si carga es urgente (tiempo bajo, energia faltante alta)"""
        return self.time_remaining_hours < 2.0 and self.energy_still_needs() > 5.0
    
    def update_after_power_delivery(self, power_delivered_kw: float, time_step_hours: float = 1.0):
        """Actualizar estado tras suministrar energia"""
        energy_delivered = power_delivered_kw * time_step_hours
        self.energy_charged_so_far_kwh += energy_delivered
        self.hours_charging += time_step_hours
        self.current_soc = min(1.0, self.current_soc + energy_delivered / 60.0)  # Asumiendo 60 kWh capacidad
        self.time_remaining_hours = max(0.0, self.time_remaining_hours - time_step_hours)


@dataclass
class ChargerManager:
    """
    Gestor central de todos los cargadores (38 sockets)
    Mantiene estado y coordina con BESS/Solar
    """
    n_moto_sockets: int = 30        # Sockets 0-29 para motos
    n_mototaxi_sockets: int = 8     # Sockets 30-37 para mototaxis
    
    # Caracteristicas por tipo
    moto_max_soc: float = 0.8       # Motos cargan 80% (usos frecuentes)
    mototaxi_max_soc: float = 1.0   # Mototaxis cargan 100%
    
    moto_capacity_kwh: float = 48.0     # Capacidad bateria moto
    mototaxi_capacity_kwh: float = 60.0 # Capacidad bateria mototaxi
    
    chargers: Dict[int, ChargerCommunication] = field(default_factory=dict)
    
    def __post_init__(self):
        # Crear diccionario de cargadores vacios
        for i in range(self.n_moto_sockets):
            self.chargers[i] = ChargerCommunication(
                socket_id=i,
                vehicle_type='moto'
            )
        for i in range(self.n_moto_sockets, self.n_moto_sockets + self.n_mototaxi_sockets):
            self.chargers[i] = ChargerCommunication(
                socket_id=i,
                vehicle_type='mototaxi'
            )
    
    def get_charger(self, socket_id: int) -> Optional[ChargerCommunication]:
        """Obtener cargador por socket ID"""
        return self.chargers.get(socket_id)
    
    def get_motos_stats(self) -> Dict[str, float]:
        """Estadisticas de motos en carga"""
        motos = [c for c in self.chargers.values() if c.vehicle_type == 'moto']
        charging = [c for c in motos if c.current_soc < c.soc_target]
        
        total_energy_needed = sum(c.energy_still_needs() for c in motos)
        total_time_remaining = sum(c.time_remaining_hours for c in charging) if charging else 0.0
        avg_soc = np.mean([c.current_soc for c in motos]) if motos else 0.0
        
        return {
            'count': len(motos),
            'charging_now': len(charging),
            'energy_needed_kwh': total_energy_needed,
            'avg_time_remaining_hours': total_time_remaining / len(charging) if charging else 0.0,
            'avg_soc': avg_soc,
            'urgent_count': sum(1 for c in motos if c.is_urgent())
        }
    
    def get_mototaxis_stats(self) -> Dict[str, float]:
        """Estadisticas de mototaxis"""
        mototaxis = [c for c in self.chargers.values() if c.vehicle_type == 'mototaxi']
        charging = [c for c in mototaxis if c.current_soc < c.soc_target]
        
        total_energy_needed = sum(c.energy_still_needs() for c in mototaxis)
        total_time_remaining = sum(c.time_remaining_hours for c in charging) if charging else 0.0
        avg_soc = np.mean([c.current_soc for c in mototaxis]) if mototaxis else 0.0
        
        return {
            'count': len(mototaxis),
            'charging_now': len(charging),
            'energy_needed_kwh': total_energy_needed,
            'avg_time_remaining_hours': total_time_remaining / len(charging) if charging else 0.0,
            'avg_soc': avg_soc,
            'urgent_count': sum(1 for c in mototaxis if c.is_urgent())
        }
    
    def total_ev_power_demand_kw(self) -> float:
        """Suma total de potencia demandada por todos los EVs"""
        return sum(c.power_demanded_kw for c in self.chargers.values())
    
    def total_ev_energy_demand_kwh(self) -> float:
        """Suma total de energia faltante"""
        return sum(c.energy_still_needs() for c in self.chargers.values())
    
    def update_chargers(self, power_per_socket: np.ndarray, time_step: float = 1.0):
        """Actualizar estado de todos los cargadores tras suministro"""
        for socket_id, charger in self.chargers.items():
            if socket_id < len(power_per_socket):
                charger.update_after_power_delivery(
                    power_per_socket[socket_id],
                    time_step
                )


# ===== BESS COMMUNICATION CONTROLLER =====
@dataclass
class BESSCommunicationController:
    """
    Controlador inteligente de BESS con priorizacion:
    1. 100% energIA a EVs (motos + mototaxis)
    2. Resto al Mall (con limite 2000 kW para evitar sobrecarga)
    3. Si mall demanda >2000 kW, BESS corta para mantener 20-22%
    """
    bess_capacity_kwh: float = 1700.0  # 1,700 kWh max SOC (v5.2 verified)
    bess_max_power_kw: float = 342.0  # Potencia maxima descarga
    bess_charge_max_power_kw: float = 342.0
    
    mall_max_power_kw: float = 2000.0  # Limite demanda mall
    mall_min_power_percent: float = 0.20  # Minimo 20% al mall
    mall_max_power_percent: float = 0.22  # Maximo 22% al mall (corte)
    
    current_soc_percent: float = 50.0  # [0, 100]
    
    def get_bess_soc_fraction(self) -> float:
        """SOC como fraccion [0, 1]"""
        return self.current_soc_percent / 100.0
    
    def can_supply_to_evs(self, ev_power_demand_kw: float) -> Tuple[float, float]:
        """
        Calcular cuanta potencia BESS puede suministrar a EVs
        Retorna: (power_to_evs_kw, power_available_after_ev)
        """
        soc_fraction = self.get_bess_soc_fraction()
        
        # Si SOC bajo, limitar descarga
        if soc_fraction < 0.10:
            return 0.0, 0.0  # Sin energia
        if soc_fraction < 0.20:
            available_power = self.bess_max_power_kw * 0.3
        elif soc_fraction < 0.50:
            available_power = self.bess_max_power_kw * 0.7
        else:
            available_power = self.bess_max_power_kw
        
        # Suministrar lo solicitado (hasta disponible)
        power_to_evs = min(ev_power_demand_kw, available_power)
        power_remaining = max(0.0, available_power - power_to_evs)
        
        return power_to_evs, power_remaining
    
    def handle_high_mall_demand(self, mall_demand_kw: float, ev_power_demand_kw: float) -> Tuple[float, float]:
        """
        Logica de corte cuando mall demanda >2000 kW
        Prioridad: 100% a EVs, resto a mall (limitado)
        
        Retorna: (power_to_ev, power_to_mall)
        """
        # Fase 1: Suministro 100% a EVs
        power_to_ev, remaining_power = self.can_supply_to_evs(ev_power_demand_kw)
        
        # Fase 2: Decidir cuanto al mall
        if mall_demand_kw >= self.mall_max_power_kw:
            # Mall demanda mucho - CORTAR a minimo permitido
            power_to_mall = 0.0  # No dar nada adicional al mall
            mall_limited = self.mall_max_power_kw
        else:
            # Mall demanda normal - suministrar lo faltante
            power_to_mall = min(remaining_power, mall_demand_kw)
        
        return power_to_ev, power_to_mall
    
    def calculate_required_discharge(self, ev_demand_kw: float, mall_demand_kw: float) -> float:
        """
        Calcular potencia de descarga requerida
        """
        power_to_ev, power_to_mall = self.handle_high_mall_demand(mall_demand_kw, ev_demand_kw)
        return power_to_ev + power_to_mall
    
    def charge_from_solar(self, solar_available_kw: float, ev_demand_kw: float, 
                         mall_demand_kw: float, time_step: float = 1.0) -> float:
        """
        Cargar BESS desde solar segun prioridades
        Retorna: energia cargada a BESS
        """
        # Calcular cuanto solar es excedente (no consumido por EVs/Mall ahora)
        solar_to_ev = min(solar_available_kw, ev_demand_kw)
        solar_to_mall = min(solar_available_kw - solar_to_ev, mall_demand_kw)
        solar_excedent = max(0.0, solar_available_kw - solar_to_ev - solar_to_mall)
        
        # Cargar BESS con excedente
        if solar_excedent > 0 and self.current_soc_percent < 100.0:
            charge_possible = self.bess_charge_max_power_kw
            energy_per_hour = min(solar_excedent, charge_possible) * time_step
            
            # Actualizar SOC (1 kWh carga = 1/940 * 100% SOC)
            soc_increase = (energy_per_hour / self.bess_capacity_kwh) * 100.0
            self.current_soc_percent = min(100.0, self.current_soc_percent + soc_increase)
            
            return energy_per_hour
        return 0.0
    
    def simulate_discharge(self, discharge_kw: float, time_step: float = 1.0) -> float:
        """
        Simular descarga de BESS
        Retorna: energia descargada
        """
        energy_discharged = discharge_kw * time_step
        soc_decrease = (energy_discharged / self.bess_capacity_kwh) * 100.0
        self.current_soc_percent = max(0.0, self.current_soc_percent - soc_decrease)
        return energy_discharged
    
    def get_status_message(self) -> Dict[str, str]:
        """Mensaje de estado para logging"""
        soc_fraction = self.get_bess_soc_fraction()
        
        if soc_fraction < 0.20:
            status = "BAJO"
        elif soc_fraction < 0.50:
            status = "CRITICO"
        elif soc_fraction < 0.80:
            status = "NORMAL"
        else:
            status = "LLENO"
        
        return {
            'soc_percent': f"{self.current_soc_percent:.1f}%",
            'status': status,
            'can_discharge': str(soc_fraction >= 0.10)
        }


# ===== Sistema de Priorizacion de Energias =====
@dataclass
class EnergyPrioritizer:
    """
    Asignador inteligente de energia entre componentes
    Prioridades:
    1. EVs 100% (motos + mototaxis)
    2. Mall economico
    3. Cargar BESS si solar excedente
    """
    charger_manager: ChargerManager = field(default_factory=ChargerManager)
    bess_controller: BESSCommunicationController = field(default_factory=BESSCommunicationController)
    
    def dispatch_energy(self, 
                       solar_available_kw: float,
                       grid_available_kw: float,
                       mall_demand_kw: float,
                       time_step: float = 1.0) -> Dict[str, float]:
        """
        Distribuir energia entre componentes segun prioridades
        
        Retorna dict con asignaciones:
        {
            'to_evs_from_solar': float,
            'to_evs_from_bess': float,
            'to_evs_from_grid': float,
            'to_mall_from_solar': float,
            'to_mall_from_bess': float,
            'to_mall_from_grid': float,
            'to_bess_from_solar': float,
            'bess_charge': float,
            'bess_discharge': float
        }
        """
        
        # Paso 1: Obtener demandas
        ev_demand = self.charger_manager.total_ev_power_demand_kw()
        
        # Paso 2: Prioridad 1 - EVs 100%
        to_evs_solar = min(solar_available_kw, ev_demand)
        to_evs_bess, bess_remaining = self.bess_controller.can_supply_to_evs(
            max(0.0, ev_demand - to_evs_solar)
        )
        to_evs_grid = max(0.0, ev_demand - to_evs_solar - to_evs_bess)
        
        # Paso 3: Prioridad 2 - Mall economico
        solar_after_ev = max(0.0, solar_available_kw - to_evs_solar)
        to_mall_solar = min(solar_after_ev, mall_demand_kw)
        
        to_mall_bess, _ = self.bess_controller.handle_high_mall_demand(
            mall_demand_kw - to_mall_solar,
            0.0  # EVs ya satisfechos
        )
        to_mall_grid = max(0.0, mall_demand_kw - to_mall_solar - to_mall_bess)
        
        # Paso 4: Cargar BESS desde solar excedente
        bess_charge_solar = self.bess_controller.charge_from_solar(
            max(0.0, solar_available_kw - to_evs_solar - to_mall_solar),
            0.0, 0.0, time_step
        )
        
        # Paso 5: Calcular descargas actuales BESS
        bess_discharge_total = to_evs_bess + to_mall_bess
        
        return {
            'to_evs_from_solar': to_evs_solar,
            'to_evs_from_bess': to_evs_bess,
            'to_evs_from_grid': to_evs_grid,
            'to_mall_from_solar': to_mall_solar,
            'to_mall_from_bess': to_mall_bess,
            'to_mall_from_grid': to_mall_grid,
            'to_bess_from_solar': bess_charge_solar,
            'bess_of_discharge': bess_discharge_total,
            'bess_charge': bess_charge_solar,
        }
    
    def get_communication_observation(self) -> np.ndarray:
        """
        Retorna vector de observacion de comunicacion inter-sistemas (12 features)
        Para incluir en observation space del agente
        """
        motos_stats = self.charger_manager.get_motos_stats()
        mototaxis_stats = self.charger_manager.get_mototaxis_stats()
        bess_soc = self.bess_controller.get_bess_soc_fraction()
        
        obs = np.array([
            # [0] BESS puede suministrar a EVs (1 si SOC >20%)
            1.0 if bess_soc > 0.20 else 0.0,
            
            # [1] EVs tienen urgencia de carga
            1.0 if motos_stats['urgent_count'] + mototaxis_stats['urgent_count'] > 0 else 0.0,
            
            # [2] SOC promedio motos [0, 1]
            motos_stats['avg_soc'],
            
            # [3] SOC promedio mototaxis [0, 1]
            mototaxis_stats['avg_soc'],
            
            # [4] Energia total faltante EVs / capacidad total
            min(1.0, (motos_stats['energy_needed_kwh'] + mototaxis_stats['energy_needed_kwh']) / 3000.0),
            
            # [5] Tiempo promedio restante motos / 8 horas max
            min(1.0, motos_stats['avg_time_remaining_hours'] / 8.0),
            
            # [6] Tiempo promedio restante mototaxis / 8 horas max
            min(1.0, mototaxis_stats['avg_time_remaining_hours'] / 8.0),
            
            # [7] BESS SOC [0, 1]
            bess_soc,
            
            # [8] Motos cargando ahora
            min(1.0, motos_stats['charging_now'] / 30.0),
            
            # [9] Mototaxis cargando ahora
            min(1.0, mototaxis_stats['charging_now'] / 8.0),
            
            # [10] Demanda total EVs / capacidad max (342 kW BESS)
            min(1.0, self.charger_manager.total_ev_power_demand_kw() / 342.0),
            
            # [11] Saturacion sistema (si motos+mototaxis >20)
            1.0 if (motos_stats['charging_now'] + mototaxis_stats['charging_now']) > 20 else 0.0,
        ], dtype=np.float32)
        
        return obs
