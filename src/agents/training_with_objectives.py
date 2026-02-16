#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAMIENTO SAC CON CICLOS DE VEHICULOS Y OBJETIVOS REALES
Integra simulador de vueltas (llega->carga->se va->vuelve) con reward intelligente
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple
from src.agents.vehicle_cycle_simulator import VehicleCycleSimulator, VehicleTrip
from src.agents.device_communication import (
    ChargerManager,
    BESSCommunicationController,
    EnergyPrioritizer,
)


@dataclass
class TrainingObjectives:
    """Objetivos concretos y medibles para el entrenamiento"""
    
    # Objetivo 1: Charged completion
    motos_target_100_percent: float = 0.80        # 80% de motos al 100%
    mototaxis_target_100_percent: float = 0.85    # 85% de mototaxis al 100%
    
    # Objetivo 2: SOC promedio en partida
    motos_target_departure_soc: float = 78.0      # Salir con 78% SOC
    mototaxis_target_departure_soc: float = 92.0  # Salir con 92% SOC
    
    # Objetivo 3: Urgencias
    urgent_response_time_hours: float = 1.5       # Atender urgencias en <1.5h
    urgent_satisfaction_percent: float = 0.95     # 95% de urgencias atendidas
    
    # Objetivo 4: BESS
    bess_ev_priority_kwh_min: float = 500.0       # Minimo 500 kWh a EVs por dia
    bess_mall_cutoffs_success: float = 0.90       # 90% de cortes exitosos >2000kW
    
    # Objetivo 5: CO2
    co2_reduction_target_kg: float = 9500.0       # 9500 kg CO2 evitado/ano
    solar_penetration_target: float = 0.35        # 35% autosuficiencia solar
    
    def compute_objective_score(self, metrics: Dict) -> float:
        """
        Calcular score agregado de objetivos cumplidos [0, 1]
        """
        scores = []
        weights = []
        
        # Score 1: Carga al 100%
        motos_score = min(1.0, metrics.get('motos_charged_100_percent', 0) / self.motos_target_100_percent)
        mototaxis_score = min(1.0, metrics.get('mototaxis_charged_100_percent', 0) / self.mototaxis_target_100_percent)
        charge_score = (motos_score * 0.6 + mototaxis_score * 0.4)
        scores.append(charge_score)
        weights.append(0.25)  # 25% del score
        
        # Score 2: SOC promedio partida
        motos_departure_score = max(0, 1.0 - abs(metrics.get('motos_avg_departure_soc', 0) - self.motos_target_departure_soc) / 20.0)
        mototaxis_departure_score = max(0, 1.0 - abs(metrics.get('mototaxis_avg_departure_soc', 0) - self.mototaxis_target_departure_soc) / 15.0)
        departure_score = (motos_departure_score * 0.6 + mototaxis_departure_score * 0.4)
        scores.append(departure_score)
        weights.append(0.20)  # 20%
        
        # Score 3: Urgencias
        urgent_response = min(1.0, metrics.get('urgent_avg_response_time', 999) / self.urgent_response_time_hours)
        urgent_satisfaction = min(1.0, metrics.get('urgent_satisfaction_percent', 0) / self.urgent_satisfaction_percent)
        urgent_score = (urgent_response * 0.4 + urgent_satisfaction * 0.6)
        scores.append(urgent_score)
        weights.append(0.20)  # 20%
        
        # Score 4: CO2
        co2_score = min(1.0, metrics.get('co2_avoided_kg', 0) / self.co2_reduction_target_kg)
        solar_score = min(1.0, metrics.get('solar_penetration', 0) / self.solar_penetration_target)
        sustainability_score = (co2_score * 0.6 + solar_score * 0.4)
        scores.append(sustainability_score)
        weights.append(0.20)  # 20%
        
        # Score 5: BESS
        bess_ev_score = min(1.0, metrics.get('bess_to_ev_kwh', 0) / self.bess_ev_priority_kwh_min)
        bess_cutoff_score = metrics.get('bess_mall_cutoff_success_rate', 0)
        bess_score = (bess_ev_score * 0.5 + bess_cutoff_score * 0.5)
        scores.append(bess_score)
        weights.append(0.15)  # 15%
        
        # Calcular promedio ponderado
        weights = np.array(weights)
        weights = weights / weights.sum()
        final_score = np.dot(scores, weights)
        
        return float(final_score)


class RealWorldSimulationEnvironment:
    """
    Ambiente que simula entrenamiento REAL con ciclos de vehiculos y objetivos
    """
    
    def __init__(self, year_hours: int = 8760):
        self.year_hours = year_hours
        self.current_hour = 0
        
        # Simulador de ciclos
        self.cycle_simulator = VehicleCycleSimulator(n_motos=30, n_mototaxis=8)
        self.cycle_simulator.generate_yearly_schedule()
        
        # Controladores
        self.charger_manager = ChargerManager(n_moto_sockets=30, n_mototaxi_sockets=8)
        self.bess_controller = BESSCommunicationController(
            bess_capacity_kwh=940.0,
            bess_max_power_kw=342.0,
            current_soc_percent=50.0
        )
        self.energy_prioritizer = EnergyPrioritizer(
            charger_manager=self.charger_manager,
            bess_controller=self.bess_controller
        )
        
        # Objetivos
        self.objectives = TrainingObjectives()
        
        # Metricas acumulativas
        self.episode_metrics = {}
        self._reset_metrics()
    
    def _reset_metrics(self):
        """Resetear metricas del episodio"""
        self.episode_metrics = {
            'motos_charged_100_count': 0,
            'motos_charged_100_percent': 0.0,
            'motos_avg_arrival_soc': 0.0,
            'motos_avg_departure_soc': 0.0,
            'mototaxis_charged_100_count': 0,
            'mototaxis_charged_100_percent': 0.0,
            'mototaxis_avg_arrival_soc': 0.0,
            'mototaxis_avg_departure_soc': 0.0,
            'urgent_count': 0,
            'urgent_satisfied': 0,
            'urgent_avg_response_time': 0.0,
            'urgent_satisfaction_percent': 0.0,
            'bess_to_ev_kwh': 0.0,
            'bess_to_mall_kwh': 0.0,
            'bess_mall_cutoff_count': 0,
            'bess_mall_cutoff_success': 0,
            'bess_mall_cutoff_success_rate': 0.0,
            'co2_avoided_kg': 0.0,
            'solar_penetration': 0.0,
            'total_solar_kwh': 0.0,
            'total_demand_kwh': 0.0,
        }
    
    def step(self, 
             action: np.ndarray,
             solar_kw: float,
             mall_kw: float) -> Tuple[Dict, float, bool]:
        """
        Ejecutar un timestep con ciclos de vehiculos y objetivos
        
        Args:
            action: [39] del agente SAC
            solar_kw: Generacion solar en esta hora
            mall_kw: Demanda mall en esta hora
        
        Returns:
            (metrics_dict, objective_reward, done)
        """
        
        # Decodificar acciones
        bess_action = float(action[0])
        charger_actions = action[1:39]
        
        charger_power_kw = charger_actions * 7.4  # Normalizar a [0, 7.4] kW
        
        # Obtener vehiculos en ciclo
        cycle_stats = self.cycle_simulator.update_hourly(
            self.current_hour,
            {i: charger_power_kw[i] for i in range(38)}
        )
        
        # Procesar ENERGIAS con priorizacion
        dispatch = self.energy_prioritizer.dispatch_energy(
            solar_available_kw=solar_kw,
            grid_available_kw=500.0,
            mall_demand_kw=mall_kw,
            time_step=1.0
        )
        
        # Procesar urgencias
        motos_stats = self.charger_manager.get_motos_stats()
        mototaxis_stats = self.charger_manager.get_mototaxis_stats()
        
        urgent_motos = motos_stats.get('urgent_count', 0)
        urgent_mototaxis = mototaxis_stats.get('urgent_count', 0)
        total_urgent = urgent_motos + urgent_mototaxis
        
        # Calcular reward de objetivos
        objective_reward = self._compute_objective_reward(
            cycle_stats, dispatch, total_urgent, solar_kw, mall_kw
        )
        
        # Actualizar metricas
        self._update_metrics(cycle_stats, dispatch, objective_reward)
        
        # Avanzar
        self.current_hour += 1
        done = self.current_hour >= self.year_hours
        
        return self.episode_metrics, objective_reward, done
    
    def _compute_objective_reward(self,
                                  cycle_stats: Dict,
                                  dispatch: Dict,
                                  urgent_count: int,
                                  solar_kw: float,
                                  mall_kw: float) -> float:
        """Calcular reward basado en cumplimiento de objetivos"""
        
        reward_components = []
        
        # Componente 1: Carga al 100%
        motos_100 = cycle_stats.get('motos_cargadas_100', 0)
        mototaxis_100 = cycle_stats.get('mototaxis_cargadas_100', 0)
        charge_reward = (motos_100 + mototaxis_100) * 0.01  # 1% por vehiculo al 100%
        reward_components.append(charge_reward)
        
        # Componente 2: Energia a EVs (prioridad)
        energy_to_evs = dispatch['to_evs_from_solar'] + dispatch['to_evs_from_bess']
        if energy_to_evs < 50:
            priority_reward = -0.05  # Penalidad si no hay energia a EVs
        elif energy_to_evs > 100:
            priority_reward = 0.05   # Bonus si hay mucha energia a EVs
        else:
            priority_reward = 0.0
        reward_components.append(priority_reward)
        
        # Componente 3: Urgencias
        if urgent_count > 0:
            urgent_satisfaction = energy_to_evs / (urgent_count * 10.0)
            urgent_reward = min(0.05, 0.05 * urgent_satisfaction)
        else:
            urgent_reward = 0.02  # Bonus si no hay urgencias (mantenimiento preventivo)
        reward_components.append(urgent_reward)
        
        # Componente 4: CO2 (solar > grid)
        solar_used = min(solar_kw, 200.0)  # Normalizar a 200 kW de demanda
        co2_reward = (solar_used / 200.0) * 0.03
        reward_components.append(co2_reward)
        
        # Componente 5: Cortes inteligentes al mall (si demanda >2000 kW)
        if mall_kw > 2000.0:
            # Si mall se corta (energia limitada = 0), bonus
            cutoff_success = 1.0 if dispatch['to_mall_from_bess'] < 50 else 0.5
            cutoff_reward = 0.03 * cutoff_success
        else:
            cutoff_reward = 0.0
        reward_components.append(cutoff_reward)
        
        # Componente 6: Penalidad por desperdicio o ineficiencia
        total_reward = sum(reward_components)
        final_reward = np.clip(total_reward, -0.1, 0.15)
        
        return float(final_reward)
    
    def _update_metrics(self, cycle_stats: Dict, dispatch: Dict, reward: float):
        """Actualizar metricas del episodio"""
        
        self.episode_metrics['bess_to_ev_kwh'] += dispatch['to_evs_from_bess']
        self.episode_metrics['bess_to_mall_kwh'] += dispatch['to_mall_from_bess']
        self.episode_metrics['motos_charged_100_count'] += cycle_stats.get('motos_cargadas_100', 0)
        self.episode_metrics['mototaxis_charged_100_count'] += cycle_stats.get('mototaxis_cargadas_100', 0)
    
    def get_final_metrics(self) -> Dict:
        """Obtener metricas finales del episodio"""
        
        final_stats = self.cycle_simulator.get_statistics()
        
        motos = [t for t in self.cycle_simulator.completed_trips if t.vehicle_type == 'moto']
        mototaxis = [t for t in self.cycle_simulator.completed_trips if t.vehicle_type == 'mototaxi']
        
        # Calcular metricas
        if motos:
            self.episode_metrics['motos_avg_arrival_soc'] = np.mean([t.arrival_soc for t in motos])
            self.episode_metrics['motos_avg_departure_soc'] = np.mean([t.departure_soc for t in motos])
            self.episode_metrics['motos_charged_100_percent'] = (
                self.episode_metrics['motos_charged_100_count'] / len(motos) * 100.0
            )
        
        if mototaxis:
            self.episode_metrics['mototaxis_avg_arrival_soc'] = np.mean([t.arrival_soc for t in mototaxis])
            self.episode_metrics['mototaxis_avg_departure_soc'] = np.mean([t.departure_soc for t in mototaxis])
            self.episode_metrics['mototaxis_charged_100_percent'] = (
                self.episode_metrics['mototaxis_charged_100_count'] / len(mototaxis) * 100.0
            )
        
        # Calcular score de objetivos
        objective_score = self.objectives.compute_objective_score(self.episode_metrics)
        self.episode_metrics['objective_score'] = objective_score
        
        return self.episode_metrics
    
    def print_summary(self):
        """Mostrar resumen de metricas"""
        metrics = self.get_final_metrics()
        
        print("\n" + "="*80)
        print("RESUMEN DE ENTRENAMIENTO CON CICLOS DE VEHICULOS")
        print("="*80)
        
        print("\nOBJETIVOS Y CUMPLIMIENTO:")
        print(f"  Score Objetivos: {metrics.get('objective_score', 0):.2%}")
        print(f"\n  MOTOS:")
        print(f"    - Cargadas 100%: {metrics.get('motos_charged_100_percent', 0):.1f}% (Objetivo: {self.objectives.motos_target_100_percent*100:.1f}%)")
        print(f"    - SOC llegada: {metrics.get('motos_avg_arrival_soc', 0):.1f}%")
        print(f"    - SOC partida: {metrics.get('motos_avg_departure_soc', 0):.1f}% (Objetivo: {self.objectives.motos_target_departure_soc:.1f}%)")
        
        print(f"\n  MOTOTAXIS:")
        print(f"    - Cargadas 100%: {metrics.get('mototaxis_charged_100_percent', 0):.1f}% (Objetivo: {self.objectives.mototaxis_target_100_percent*100:.1f}%)")
        print(f"    - SOC llegada: {metrics.get('mototaxis_avg_arrival_soc', 0):.1f}%")
        print(f"    - SOC partida: {metrics.get('mototaxis_avg_departure_soc', 0):.1f}% (Objetivo: {self.objectives.mototaxis_target_departure_soc:.1f}%)")
        
        print(f"\n  BESS PRIORIZACION:")
        print(f"    - Energia a EVs: {metrics.get('bess_to_ev_kwh', 0):.0f} kWh (Objetivo: {self.objectives.bess_ev_priority_kwh_min:.0f} kWh/dia)")
        print(f"    - Energia a Mall: {metrics.get('bess_to_mall_kwh', 0):.0f} kWh")
        print(f"    - Cortes exitosos: {metrics.get('bess_mall_cutoff_success_rate', 0):.1%} (Objetivo: {self.objectives.bess_mall_cutoffs_success:.1%})")


if __name__ == '__main__':
    # Prueba
    print("\n" + "="*80)
    print("ENTRENAMIENTO SAC CON CICLOS DE VEHICULOS Y OBJETIVOS REALES")
    print("="*80)
    
    env = RealWorldSimulationEnvironment(year_hours=24)  # 1 dia para prueba rapida
    env._reset_metrics()
    
    print(f"\nSimulando 1 dia (24 horas)...")
    
    for hour in range(24):
        # Simular datos reales
        solar_kw = 3000 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
        mall_kw = 1500 + 200 * np.sin(np.pi * hour / 24)
        
        # Accion random del agente (sera SAC luego)
        action_agent = np.random.uniform(0, 1, 39)
        
        # Ejecutar step
        metrics, reward, done = env.step(action_agent, solar_kw, mall_kw)
        
        if hour % 6 == 0 or hour == 23:
            print(f"  Hora {hour:02d}:00 | Reward={reward:+.4f} | Solar={solar_kw:6.0f}kW | Mall={mall_kw:6.0f}kW")
    
    # Mostrar resumen
    env.print_summary()
