#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEVICE CONTROLLERS - Logica separada por cada aparato del sistema
Cada aparato tiene su propio tracker/contador independiente
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SolarMetrics:
    """Metricas independientes del controlador SOLAR"""
    timesteps_counted: int = 0
    total_generation_kwh: float = 0.0
    total_to_eva_kwh: float = 0.0
    total_to_mall_kwh: float = 0.0
    total_to_bess_kwh: float = 0.0
    total_curtailed_kwh: float = 0.0
    peak_generation_kw: float = 0.0
    avg_generation_kw: float = 0.0
    self_consumption_ratio: float = 0.0
    
    def reset(self):
        self.timesteps_counted = 0
        self.total_generation_kwh = 0.0
        self.total_to_eva_kwh = 0.0
        self.total_to_mall_kwh = 0.0
        self.total_to_bess_kwh = 0.0
        self.total_curtailed_kwh = 0.0
        self.peak_generation_kw = 0.0


@dataclass
class ChargerMetrics:
    """Metricas independientes del controlador CHARGERS"""
    timesteps_counted: int = 0
    total_energy_delivered_kwh: float = 0.0
    total_energy_requested_kwh: float = 0.0
    motos_charged_100: int = 0
    mototaxis_charged_100: int = 0
    motos_currently_charging: int = 0
    mototaxis_currently_charging: int = 0
    avg_charging_power_kw: float = 0.0
    peak_charging_power_kw: float = 0.0
    charger_efficiency: float = 0.0
    sockets_active_total: int = 0
    motos_avg_soc: float = 0.0
    mototaxis_avg_soc: float = 0.0
    prioritization_decisions: int = 0
    waitlist_motos: int = 0
    waitlist_mototaxis: int = 0
    
    def reset(self):
        self.timesteps_counted = 0
        self.total_energy_delivered_kwh = 0.0
        self.total_energy_requested_kwh = 0.0
        self.motos_charged_100 = 0
        self.mototaxis_charged_100 = 0
        self.motos_currently_charging = 0
        self.mototaxis_currently_charging = 0
        self.avg_charging_power_kw = 0.0
        self.peak_charging_power_kw = 0.0
        self.charger_efficiency = 0.0
        self.sockets_active_total = 0
        self.motos_avg_soc = 0.0
        self.mototaxis_avg_soc = 0.0
        self.prioritization_decisions = 0
        self.waitlist_motos = 0
        self.waitlist_mototaxis = 0


@dataclass
class BESSMetrics:
    """Metricas independientes del controlador BESS"""
    timesteps_counted: int = 0
    total_charge_kwh: float = 0.0
    total_discharge_kwh: float = 0.0
    total_to_ev_kwh: float = 0.0
    total_to_mall_kwh: float = 0.0
    charging_cycles: int = 0
    discharging_cycles: int = 0
    peak_charge_power_kw: float = 0.0
    peak_discharge_power_kw: float = 0.0
    avg_soc_percent: float = 0.0
    min_soc_percent: float = 100.0
    max_soc_percent: float = 0.0
    times_at_100_percent: int = 0
    times_at_0_percent: int = 0
    efficiency_roundtrip: float = 0.95
    
    def reset(self):
        self.timesteps_counted = 0
        self.total_charge_kwh = 0.0
        self.total_discharge_kwh = 0.0
        self.total_to_ev_kwh = 0.0
        self.total_to_mall_kwh = 0.0
        self.charging_cycles = 0
        self.discharging_cycles = 0
        self.peak_charge_power_kw = 0.0
        self.peak_discharge_power_kw = 0.0
        self.avg_soc_percent = 0.0
        self.min_soc_percent = 100.0
        self.max_soc_percent = 0.0
        self.times_at_100_percent = 0
        self.times_at_0_percent = 0


@dataclass
class MallMetrics:
    """Metricas independientes del controlador MALL"""
    timesteps_counted: int = 0
    total_demand_kwh: float = 0.0
    total_from_solar_kwh: float = 0.0
    total_from_bess_kwh: float = 0.0
    total_from_grid_kwh: float = 0.0
    peak_demand_kw: float = 0.0
    avg_demand_kw: float = 0.0
    solar_penetration_ratio: float = 0.0
    bess_penetration_ratio: float = 0.0
    cost_paid_soles: float = 0.0
    
    def reset(self):
        self.timesteps_counted = 0
        self.total_demand_kwh = 0.0
        self.total_from_solar_kwh = 0.0
        self.total_from_bess_kwh = 0.0
        self.total_from_grid_kwh = 0.0
        self.peak_demand_kw = 0.0
        self.avg_demand_kw = 0.0
        self.solar_penetration_ratio = 0.0
        self.bess_penetration_ratio = 0.0
        self.cost_paid_soles = 0.0


class SolarController:
    """Controlador INDEPENDIENTE para generacion SOLAR"""
    
    def __init__(self, solar_data: np.ndarray):
        self.solar_data = solar_data
        self.metrics = SolarMetrics()
        self.step_count = 0
    
    def step(self, timestep: int, action_dispatch: float) -> Dict[str, float]:
        """
        Procesar un timestep de generacion SOLAR
        Args:
            timestep: Indice horario [0-8759]
            action_dispatch: Accion del agente para priorizar destino (0-1)
        
        Returns:
            Dict con flujos de energia disponibles
        """
        self.step_count += 1
        self.metrics.timesteps_counted += 1
        
        # Obtener generacion REAL de este timestep
        generation_kw = float(self.solar_data[timestep]) if timestep < len(self.solar_data) else 0.0
        
        # Accionable: cantidad de generacion que va a diferentes destinos
        # action_dispatch: 0.0 = priorizar EV, 1.0 = priorizar BESS/Mall
        to_ev_ratio = 1.0 - action_dispatch
        to_other_ratio = action_dispatch
        
        generation_to_ev = generation_kw * to_ev_ratio
        generation_to_other = generation_kw * to_other_ratio
        
        # Tracking
        self.metrics.total_generation_kwh += generation_kw
        self.metrics.total_to_eva_kwh += generation_to_ev
        self.metrics.total_to_mall_kwh += generation_to_other * 0.5
        self.metrics.total_to_bess_kwh += generation_to_other * 0.5
        self.metrics.peak_generation_kw = max(self.metrics.peak_generation_kw, generation_kw)
        
        if self.step_count > 0:
            self.metrics.avg_generation_kw = self.metrics.total_generation_kwh / self.step_count
        
        return {
            'solar_generation_kw': generation_kw,
            'solar_to_ev_kw': generation_to_ev,
            'solar_to_other_kw': generation_to_other,
            'solar_timestamp': timestep
        }
    
    def reset(self):
        self.metrics.reset()
        self.step_count = 0
    
    def get_metrics(self) -> Dict[str, float]:
        return {
            'solar_timesteps': self.metrics.timesteps_counted,
            'solar_total_kwh': self.metrics.total_generation_kwh,
            'solar_to_ev_kwh': self.metrics.total_to_eva_kwh,
            'solar_peak_kw': self.metrics.peak_generation_kw,
            'solar_avg_kw': self.metrics.avg_generation_kw,
        }


class ChargerController:
    """Controlador INDEPENDIENTE para carga EV"""
    
    def __init__(self, n_motos: int = 30, n_mototaxis: int = 8):
        self.n_motos = n_motos
        self.n_mototaxis = n_mototaxis
        self.n_total_sockets = n_motos + n_mototaxis
        self.metrics = ChargerMetrics()
        self.step_count = 0
        self.vehicle_socs: Dict[int, float] = {}  # socket_id -> current_soc %
    
    def step(self, timestep: int, actions: np.ndarray, available_power_kw: float, 
             demand_profile: float) -> Dict[str, float]:
        """
        Procesar un timestep de carga EV
        Args:
            timestep: Indice horario [0-8759]
            actions: Array de potencias para cada socket [n_sockets]
            available_power_kw: Potencia disponible para chargers
            demand_profile: Demanda de carga esperada
        
        Returns:
            Dict con energia entregada y estados
        """
        self.step_count += 1
        self.metrics.timesteps_counted += 1
        
        total_requested = float(np.sum(actions))
        total_available = min(total_requested, available_power_kw)
        
        # Distribuir potencia disponible proporcionalmente
        if total_requested > 0:
            scaling_factor = total_available / total_requested
        else:
            scaling_factor = 0.0
        
        energy_delivered = 0.0
        motos_charging = 0
        taxis_charging = 0
        
        for socket_id, power_action in enumerate(actions):
            if power_action > 0.1:
                actual_power = power_action * scaling_factor
                energy = actual_power * 1.0  # 1 hora
                energy_delivered += energy
                
                # Actualizar SOC del vehiculo
                if socket_id not in self.vehicle_socs:
                    self.vehicle_socs[socket_id] = np.random.uniform(0, 5)  # Llegan vacios
                
                self.vehicle_socs[socket_id] = min(100.0, self.vehicle_socs[socket_id] + energy / 50.0)
                
                # Contar por tipo
                if socket_id < self.n_motos:
                    motos_charging += 1
                else:
                    taxis_charging += 1
                
                # Si alcanzo 100%, contar
                if self.vehicle_socs[socket_id] >= 100.0:
                    if socket_id < self.n_motos:
                        self.metrics.motos_charged_100 += 1
                    else:
                        self.metrics.mototaxis_charged_100 += 1
        
        # Tracking
        self.metrics.total_energy_delivered_kwh += energy_delivered
        self.metrics.total_energy_requested_kwh += total_requested
        self.metrics.motos_currently_charging = motos_charging
        self.metrics.mototaxis_currently_charging = taxis_charging
        self.metrics.peak_charging_power_kw = max(self.metrics.peak_charging_power_kw, energy_delivered)
        self.metrics.sockets_active_total = motos_charging + taxis_charging
        
        if self.step_count > 0:
            self.metrics.avg_charging_power_kw = self.metrics.total_energy_delivered_kwh / self.step_count
            if self.metrics.total_energy_requested_kwh > 0:
                self.metrics.charger_efficiency = self.metrics.total_energy_delivered_kwh / self.metrics.total_energy_requested_kwh
        
        if self.vehicle_socs:
            # vehicle_socs es un Dict[int, float], no una lista
            # Acceder solo a las claves que existen
            motos_socs = [self.vehicle_socs[i] for i in range(self.n_motos) if i in self.vehicle_socs]
            taxis_socs = [self.vehicle_socs[i] for i in range(self.n_motos, self.n_total_sockets) if i in self.vehicle_socs]
            if motos_socs:
                self.metrics.motos_avg_soc = float(np.mean(motos_socs))
            if taxis_socs:
                self.metrics.mototaxis_avg_soc = float(np.mean(taxis_socs))
        
        return {
            'charger_energy_delivered_kwh': energy_delivered,
            'charger_energy_requested_kwh': total_requested,
            'charger_motos_charging': motos_charging,
            'charger_taxis_charging': taxis_charging,
            'charger_motos_100': self.metrics.motos_charged_100,
            'charger_taxis_100': self.metrics.mototaxis_charged_100,
            'charger_timestamp': timestep
        }
    
    def reset(self):
        self.metrics.reset()
        self.step_count = 0
        self.vehicle_socs = {}
    
    def get_metrics(self) -> Dict[str, float]:
        return {
            'charger_timesteps': self.metrics.timesteps_counted,
            'charger_total_kwh': self.metrics.total_energy_delivered_kwh,
            'charger_motos_100': self.metrics.motos_charged_100,
            'charger_taxis_100': self.metrics.mototaxis_charged_100,
            'charger_avg_power': self.metrics.avg_charging_power_kw,
            'charger_peak_power': self.metrics.peak_charging_power_kw,
            'charger_efficiency': self.metrics.charger_efficiency,
            'charger_motos_avg_soc': self.metrics.motos_avg_soc,
            'charger_taxis_avg_soc': self.metrics.mototaxis_avg_soc,
        }


class BESSController:
    """Controlador INDEPENDIENTE para almacenamiento BESS"""
    
    def __init__(self, capacity_kwh: float = 940.0, max_power_kw: float = 342.0, 
                 initial_soc_percent: float = 50.0):
        self.capacity_kwh = capacity_kwh
        self.max_power_kw = max_power_kw
        self.current_soc_percent = initial_soc_percent
        self.metrics = BESSMetrics()
        self.step_count = 0
        self._last_action = 0.5
    
    def step(self, timestep: int, action: float, solar_available_kw: float,
             ev_demand_kw: float, mall_demand_kw: float) -> Dict[str, float]:
        """
        Procesar un timestep de BESS
        Args:
            timestep: Indice horario [0-8759]
            action: Accion normalizador [0-1]: 0=carga max, 0.5=neutro, 1=descarga max
            solar_available_kw: Generacion PV disponible
            ev_demand_kw: Demanda actual EV
            mall_demand_kw: Demanda actual Mall
        
        Returns:
            Dict con flujos de energia y estado SOC
        """
        self.step_count += 1
        self.metrics.timesteps_counted += 1
        
        # Normalizar accion a potencia
        bess_power_kw = (action - 0.5) * 2.0 * self.max_power_kw  # -342 a +342
        
        # Limitar por SOC actual
        available_kwh = self.current_soc_percent / 100.0 * self.capacity_kwh
        
        if bess_power_kw > 0:  # DESCARGA
            # No puede descargar mas de lo que tiene
            max_discharge_kwh = available_kwh
            actual_discharge_kwh = min(abs(bess_power_kw) * 1.0, max_discharge_kwh)
            
            self.metrics.total_discharge_kwh += actual_discharge_kwh
            self.metrics.peak_discharge_power_kw = max(self.metrics.peak_discharge_power_kw, actual_discharge_kwh)
            
            if action != self._last_action and action > 0.5:
                self.metrics.discharging_cycles += 1
            
            # Flujo de descarga (prioritario a EV)
            to_ev = min(actual_discharge_kwh, ev_demand_kw)
            to_mall = min(actual_discharge_kwh - to_ev, mall_demand_kw)
            
            self.metrics.total_to_ev_kwh += to_ev
            self.metrics.total_to_mall_kwh += to_mall
            
            # Actualizar SOC
            self.current_soc_percent = max(0, self.current_soc_percent - (actual_discharge_kwh / self.capacity_kwh * 100.0))
            
        else:  # CARGA
            # No puede cargar mas alla de capacidad
            max_charge_kwh = (100.0 - self.current_soc_percent) / 100.0 * self.capacity_kwh
            actual_charge_kwh = min(abs(bess_power_kw) * 1.0, max_charge_kwh)
            
            # Limitar por solar disponible
            actual_charge_kwh = min(actual_charge_kwh, solar_available_kw)
            
            self.metrics.total_charge_kwh += actual_charge_kwh
            self.metrics.peak_charge_power_kw = max(self.metrics.peak_charge_power_kw, actual_charge_kwh)
            
            if action != self._last_action and action < 0.5:
                self.metrics.charging_cycles += 1
            
            # Actualizar SOC
            self.current_soc_percent = min(100.0, self.current_soc_percent + (actual_charge_kwh / self.capacity_kwh * 100.0))
        
        # Tracking de limites
        if self.current_soc_percent >= 99.0:
            self.metrics.times_at_100_percent += 1
        if self.current_soc_percent <= 1.0:
            self.metrics.times_at_0_percent += 1
        
        self.metrics.min_soc_percent = min(self.metrics.min_soc_percent, self.current_soc_percent)
        self.metrics.max_soc_percent = max(self.metrics.max_soc_percent, self.current_soc_percent)
        
        if self.step_count > 0:
            self.metrics.avg_soc_percent = (self.metrics.avg_soc_percent * (self.step_count - 1) + self.current_soc_percent) / self.step_count
        
        self._last_action = action
        
        return {
            'bess_charge_kwh': self.metrics.total_charge_kwh,
            'bess_discharge_kwh': self.metrics.total_discharge_kwh,
            'bess_soc_percent': self.current_soc_percent,
            'bess_to_ev_kwh': self.metrics.total_to_ev_kwh,
            'bess_to_mall_kwh': self.metrics.total_to_mall_kwh,
            'bess_timestamp': timestep
        }
    
    def reset(self, initial_soc_percent: float = 50.0):
        self.metrics.reset()
        self.step_count = 0
        self.current_soc_percent = initial_soc_percent
        self._last_action = 0.5
    
    def get_metrics(self) -> Dict[str, float]:
        return {
            'bess_timesteps': self.metrics.timesteps_counted,
            'bess_total_charge_kwh': self.metrics.total_charge_kwh,
            'bess_total_discharge_kwh': self.metrics.total_discharge_kwh,
            'bess_to_ev_kwh': self.metrics.total_to_ev_kwh,
            'bess_to_mall_kwh': self.metrics.total_to_mall_kwh,
            'bess_cycles': self.metrics.charging_cycles + self.metrics.discharging_cycles,
            'bess_avg_soc': self.metrics.avg_soc_percent,
            'bess_min_soc': self.metrics.min_soc_percent,
            'bess_max_soc': self.metrics.max_soc_percent,
        }


class MallController:
    """Controlador INDEPENDIENTE para demanda MALL"""
    
    def __init__(self, mall_data: np.ndarray):
        self.mall_data = mall_data
        self.metrics = MallMetrics()
        self.step_count = 0
    
    def step(self, timestep: int, solar_available_kw: float, bess_available_kw: float,
             grid_import_kw: float) -> Dict[str, float]:
        """
        Procesar un timestep de demanda MALL
        Args:
            timestep: Indice horario [0-8759]
            solar_available_kw: Potencia solar asignada al mall
            bess_available_kw: Potencia BESS asignada al mall
            grid_import_kw: Potencia importada del grid
        
        Returns:
            Dict con consumo y fuentes de energia
        """
        self.step_count += 1
        self.metrics.timesteps_counted += 1
        
        # Obtener demanda REAL
        demand_kw = float(self.mall_data[timestep]) if timestep < len(self.mall_data) else 0.0
        
        # Fuentes de energia (1 hora)
        from_solar_kwh = solar_available_kw * 1.0
        from_bess_kwh = bess_available_kw * 1.0
        from_grid_kwh = grid_import_kw * 1.0
        
        # Tracking
        self.metrics.total_demand_kwh += demand_kw
        self.metrics.total_from_solar_kwh += from_solar_kwh
        self.metrics.total_from_bess_kwh += from_bess_kwh
        self.metrics.total_from_grid_kwh += from_grid_kwh
        self.metrics.peak_demand_kw = max(self.metrics.peak_demand_kw, demand_kw)
        
        if self.step_count > 0:
            self.metrics.avg_demand_kw = self.metrics.total_demand_kwh / self.step_count
            total_supply = self.metrics.total_from_solar_kwh + self.metrics.total_from_bess_kwh + self.metrics.total_from_grid_kwh
            if total_supply > 0:
                self.metrics.solar_penetration_ratio = self.metrics.total_from_solar_kwh / total_supply
                self.metrics.bess_penetration_ratio = self.metrics.total_from_bess_kwh / total_supply
        
        return {
            'mall_demand_kwh': demand_kw,
            'mall_from_solar_kwh': from_solar_kwh,
            'mall_from_bess_kwh': from_bess_kwh,
            'mall_from_grid_kwh': from_grid_kwh,
            'mall_timestamp': timestep
        }
    
    def reset(self):
        self.metrics.reset()
        self.step_count = 0
    
    def get_metrics(self) -> Dict[str, float]:
        return {
            'mall_timesteps': self.metrics.timesteps_counted,
            'mall_total_demand_kwh': self.metrics.total_demand_kwh,
            'mall_from_solar_kwh': self.metrics.total_from_solar_kwh,
            'mall_from_bess_kwh': self.metrics.total_from_bess_kwh,
            'mall_from_grid_kwh': self.metrics.total_from_grid_kwh,
            'mall_avg_demand': self.metrics.avg_demand_kw,
            'mall_solar_penetration': self.metrics.solar_penetration_ratio,
            'mall_bess_penetration': self.metrics.bess_penetration_ratio,
        }


class SystemOrchestrator:
    """Orquestador CENTRAL que coordina todos los controladores"""
    
    def __init__(self, solar_data: np.ndarray, chargers_data: np.ndarray,
                 mall_data: np.ndarray, n_motos: int = 30, n_mototaxis: int = 8):
        self.global_timestep = 0
        
        self.solar_controller = SolarController(solar_data)
        self.charger_controller = ChargerController(n_motos=n_motos, n_mototaxis=n_mototaxis)
        self.bess_controller = BESSController(capacity_kwh=1700.0, max_power_kw=342.0)  # v5.2: 1,700 kWh max SOC (verified from bess_simulation_hourly.csv)
        self.mall_controller = MallController(mall_data)
    
    def step(self, timestep: int, action: np.ndarray, solar_data: np.ndarray,
             chargers_data: np.ndarray, mall_data: np.ndarray) -> Dict[str, Dict]:
        """
        Procesar un timestep COMPLETO coordinando todos los aparatos
        
        Args:
            timestep: Hora [0-8759]
            action: [bess_action, charger_actions[38]]
            solar_data, chargers_data, mall_data: Arrays de datos REALES
        
        Returns:
            Dict con resultados de cada controlador
        """
        self.global_timestep = timestep
        
        # 1. PROCESAR SOLAR (independiente)
        solar_result = self.solar_controller.step(timestep, float(action[0]) if len(action) > 0 else 0.5)
        solar_gen = solar_result['solar_generation_kw']
        
        # 2. PROCESAR CHARGERS (requiere energia disponible)
        # Energia disponible: solar directo + BESS disponible
        charger_action = action[1:39] if len(action) > 1 else np.zeros(38)
        current_charger_result = self.charger_controller.step(
            timestep, charger_action, 
            available_power_kw=solar_gen + (self.bess_controller.current_soc_percent / 100.0 * self.bess_controller.max_power_kw),
            demand_profile=float(chargers_data[timestep].sum()) if timestep < len(chargers_data) else 0.0
        )
        
        # 3. PROCESAR BESS (requiere EVs demand y solar surplus)
        ev_demand = current_charger_result['charger_energy_requested_kwh']
        mall_demand = float(mall_data[timestep]) if timestep < len(mall_data) else 0.0
        
        bess_result = self.bess_controller.step(
            timestep, action[0] if len(action) > 0 else 0.5,
            solar_available_kw=solar_gen,
            ev_demand_kw=ev_demand,
            mall_demand_kw=mall_demand
        )
        
        # 4. PROCESAR MALL (requiere energia asignada)
        solar_for_mall = solar_gen - current_charger_result['charger_energy_delivered_kwh']
        mall_result = self.mall_controller.step(
            timestep,
            solar_available_kw=max(0, solar_for_mall),
            bess_available_kw=bess_result['bess_to_mall_kwh'],
            grid_import_kw=0.0  # TODO: calcular del balance
        )
        
        return {
            'solar': solar_result,
            'charger': current_charger_result,
            'bess': bess_result,
            'mall': mall_result,
            'global_timestep': self.global_timestep
        }
    
    def reset(self):
        self.global_timestep = 0
        self.solar_controller.reset()
        self.charger_controller.reset()
        self.bess_controller.reset()
        self.mall_controller.reset()
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """Obtener metricas de todos los controladores"""
        return {
            'solar': self.solar_controller.get_metrics(),
            'charger': self.charger_controller.get_metrics(),
            'bess': self.bess_controller.get_metrics(),
            'mall': self.mall_controller.get_metrics(),
            'global_timestep': self.global_timestep,
        }
    
    def get_timestep_summary(self) -> str:
        """Resumen de un timestep especifico"""
        metrics = self.get_all_metrics()
        summary = (
            f"[TIMESTEP {self.global_timestep:05d}]\n"
            f"  SOLAR:    {metrics['solar'].get('solar_generation_kw', 0):.1f} kW\n"
            f"  CHARGERS: {metrics['charger'].get('charger_motos_charging', 0)}M + {metrics['charger'].get('charger_taxis_charging', 0)}T\n"
            f"  BESS:     SOC={metrics['bess'].get('bess_soc_percent', 0):.1f}% | "
            f"Charge={metrics['bess'].get('bess_total_charge_kwh', 0):.1f} | "
            f"Discharge={metrics['bess'].get('bess_total_discharge_kwh', 0):.1f}\n"
            f"  MALL:     {metrics['mall'].get('mall_total_demand_kwh', 0):.1f} kWh\n"
        )
        return summary
