#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULADOR DE CICLOS DE VEHICULOS (VUELTAS)
Motos y mototaxis hacen multiples ciclos: llegan -> cargan -> se van -> vuelven
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np


class VehicleState(Enum):
    """Estados del vehiculo en su ciclo"""
    WAITING = "esperando"      # Esperando socket libre
    CHARGING = "cargando"      # Conectado cargando
    CHARGED = "cargado"        # Alcanzo target, desconectando
    IN_USE = "en_uso"          # Afuera en la calle, gastando bateria
    RETURNING = "regresando"   # En camino de vuelta al estacionamiento


@dataclass
class VehicleTrip:
    """Representa un viaje de vehiculo (desde que llega hasta que se va)"""
    vehicle_id: int
    vehicle_type: str          # 'moto' o 'mototaxi'
    arrival_hour: int          # Hora cuando llega al estacionamiento
    arrival_soc: float         # SOC cuando llega [0, 100%]
    target_soc: float          # Objetivo de carga [70, 100%]
    expected_trip_duration_hours: float  # Cuanto tiempo estara fuera (viaje)
    
    # Estado durante ciclo
    current_soc: float = field(init=False)
    charge_start_hour: Optional[int] = None
    charge_end_hour: Optional[int] = None
    energy_charged_kwh: float = 0.0
    state: VehicleState = VehicleState.WAITING
    
    # Estadisticas
    hours_parked: float = 0.0
    hours_charging: float = 0.0
    hours_charged_waiting: float = 0.0  # Tiempo esperando a irse
    departure_hour: Optional[int] = None
    departure_soc: float = 0.0
    
    def __post_init__(self):
        self.current_soc = self.arrival_soc
    
    def get_trip_id(self) -> str:
        """Identificador unico del viaje"""
        return f"{self.vehicle_type[0]}{self.vehicle_id:02d}_h{self.arrival_hour:02d}"
    
    def needs_charging(self) -> bool:
        """Si aun necesita carga para alcanzar target"""
        return self.current_soc < self.target_soc
    
    def is_overdue(self, current_hour: int) -> bool:
        """Si el vehiculo deberia haber salido ya"""
        time_parked = current_hour - self.arrival_hour
        return time_parked > (self.expected_trip_duration_hours + 2.0)  # 2h tolerance
    
    def charge(self, power_kw: float, time_hours: float = 1.0) -> float:
        """
        Cargar el vehiculo
        Retorna: energia cargada [kWh]
        """
        # Capacidad segun tipo
        if self.vehicle_type == 'moto':
            capacity = 48.0  # kWh
            max_soc = 80.0   # %
        else:  # mototaxi
            capacity = 60.0
            max_soc = 100.0
        
        # Energia entregada en este timestep
        energy = power_kw * time_hours
        
        # Actualizar SOC
        soc_increase = (energy / capacity) * 100.0
        new_soc = min(max_soc, self.current_soc + soc_increase)
        
        # Energia realmente cargada
        energy_actually_charged = ((new_soc - self.current_soc) / 100.0) * capacity
        
        self.current_soc = new_soc
        self.energy_charged_kwh += energy_actually_charged
        
        # Actualizar estado
        if self.charge_start_hour is None:
            self.charge_start_hour = int(np.random.randint(0, 23))  # Placeholder
        
        if self.current_soc >= self.target_soc:
            self.state = VehicleState.CHARGED
            self.charge_end_hour = int(np.random.randint(0, 23))
        else:
            self.state = VehicleState.CHARGING
        
        return energy_actually_charged
    
    def discharge_in_trip(self, hours_on_road: float) -> float:
        """
        Simular consumo de bateria durante viaje
        """
        if self.vehicle_type == 'moto':
            consumption_percent_per_hour = 15.0  # 15% por hora en viaje
            capacity = 48.0
        else:
            consumption_percent_per_hour = 12.0  # 12% por hora
            capacity = 60.0
        
        soc_decrease = consumption_percent_per_hour * hours_on_road
        self.current_soc = max(0.0, self.current_soc - soc_decrease)
        
        return (soc_decrease / 100.0) * capacity


@dataclass
class VehicleCycleSimulator:
    """Simula ciclos completos de vehiculos a lo largo del ano"""
    
    n_motos: int = 30
    n_mototaxis: int = 8
    
    # Patrones de llegadas (horarios)
    moto_arrival_hours: List[int] = field(default_factory=lambda: [6, 8, 11, 14, 17, 19, 21])
    mototaxi_arrival_hours: List[int] = field(default_factory=lambda: [7, 12, 16, 20])
    
    # Duracion de viajes
    moto_trip_duration_min: float = 1.5  # horas
    moto_trip_duration_max: float = 3.0
    mototaxi_trip_duration_min: float = 2.0
    mototaxi_trip_duration_max: float = 4.0
    
    # SOC en llegadas
    moto_arrival_soc_min: float = 5.0   # %
    moto_arrival_soc_max: float = 15.0
    mototaxi_arrival_soc_min: float = 5.0
    mototaxi_arrival_soc_max: float = 10.0
    
    # Mapa de viajes por hora: { hour: [VehicleTrip, ...] }
    scheduled_trips: Dict[int, List[VehicleTrip]] = field(default_factory=dict)
    active_trips: Dict[int, VehicleTrip] = field(default_factory=dict)  # {vehicle_id: trip}
    
    completed_trips: List[VehicleTrip] = field(default_factory=list)
    
    def generate_yearly_schedule(self):
        """
        Genera cronograma de viajes para todo el ano
        Cada dia se repite el patron de llegadas
        """
        trips_per_day = []
        
        # Motos: multiples viajes por dia
        vehicle_counter = 0
        for arrival_hour in self.moto_arrival_hours:
            for _ in range(max(1, self.n_motos // len(self.moto_arrival_hours))):
                trip = VehicleTrip(
                    vehicle_id=vehicle_counter,
                    vehicle_type='moto',
                    arrival_hour=arrival_hour,
                    arrival_soc=np.random.uniform(self.moto_arrival_soc_min, self.moto_arrival_soc_max),
                    target_soc=np.random.uniform(70.0, 85.0),
                    expected_trip_duration_hours=np.random.uniform(self.moto_trip_duration_min, self.moto_trip_duration_max)
                )
                trips_per_day.append(trip)
                vehicle_counter += 1
        
        # Mototaxis: menos viajes pero mas largos
        for arrival_hour in self.mototaxi_arrival_hours:
            for _ in range(max(1, self.n_mototaxis // len(self.mototaxi_arrival_hours))):
                trip = VehicleTrip(
                    vehicle_id=vehicle_counter,
                    vehicle_type='mototaxi',
                    arrival_hour=arrival_hour,
                    arrival_soc=np.random.uniform(self.mototaxi_arrival_soc_min, self.mototaxi_arrival_soc_max),
                    target_soc=np.random.uniform(85.0, 100.0),
                    expected_trip_duration_hours=np.random.uniform(self.mototaxi_trip_duration_min, self.mototaxi_trip_duration_max)
                )
                trips_per_day.append(trip)
                vehicle_counter += 1
        
        # Replicar para 365 dias del ano
        for day in range(365):
            day_start_hour = day * 24
            
            for trip_template in trips_per_day:
                # Crear copia del viaje para este dia
                hour_key = day_start_hour + trip_template.arrival_hour
                
                # Agregar variabilidad (+-30 min)
                hour_key += np.random.randint(-1, 2)
                
                new_trip = VehicleTrip(
                    vehicle_id=trip_template.vehicle_id,
                    vehicle_type=trip_template.vehicle_type,
                    arrival_hour=hour_key,
                    arrival_soc=np.random.uniform(
                        trip_template.vehicle_type == 'moto' and self.moto_arrival_soc_min or self.mototaxi_arrival_soc_min,
                        trip_template.vehicle_type == 'moto' and self.moto_arrival_soc_max or self.mototaxi_arrival_soc_max
                    ),
                    target_soc=trip_template.target_soc,
                    expected_trip_duration_hours=trip_template.expected_trip_duration_hours
                )
                
                if hour_key not in self.scheduled_trips:
                    self.scheduled_trips[hour_key] = []
                self.scheduled_trips[hour_key].append(new_trip)
    
    def get_arriving_vehicles(self, current_hour: int) -> List[VehicleTrip]:
        """Obtener vehiculos que llegan en esta hora"""
        return self.scheduled_trips.get(current_hour, [])
    
    def update_hourly(self, current_hour: int, chargers_available: Dict[int, float]) -> Dict:
        """
        Actualizar estado de todos los viajes activos en esta hora
        
        Args:
            current_hour: Hora actual [0, 8759]
            chargers_available: {charger_index: power_kw} potencia asignada a cada charger
        
        Returns:
            Dict con estadisticas de viajes
        """
        
        stats = {
            'trips_active': 0,
            'trips_charging': 0,
            'trips_charged': 0,
            'motos_cargadas_100': 0,
            'mototaxis_cargadas_100': 0,
            'total_energy_charged_kwh': 0.0,
            'departing_soon': 0,
            'departed': 0,
            'new_arrivals': 0
        }
        
        # 1. Procesar nuevas llegadas
        arriving = self.get_arriving_vehicles(current_hour)
        for trip in arriving:
            # Usar trip_id unico en lugar de id() de Python
            trip_key = trip.get_trip_id()
            self.active_trips[trip_key] = trip
            stats['new_arrivals'] += 1
        
        # 2. Actualizar viajes activos
        vehicles_to_remove = []
        charger_index = 0  # Asignar chargers secuencialmente
        
        for trip_key, trip in list(self.active_trips.items()):
            stats['trips_active'] += 1
            
            # Obtener potencia asignada (usa indice de charger, no vehicle_id)
            power_kw = chargers_available.get(charger_index, 0.0)
            charger_index += 1
            
            # Cargar
            energy = trip.charge(power_kw, time_hours=1.0)
            stats['total_energy_charged_kwh'] += energy
            
            if trip.state == VehicleState.CHARGING:
                stats['trips_charging'] += 1
            elif trip.state == VehicleState.CHARGED:
                stats['trips_charged'] += 1
            
            # Verificar si alcanzo 100%
            if trip.current_soc >= 99.0:
                if trip.vehicle_type == 'moto':
                    stats['motos_cargadas_100'] += 1
                else:
                    stats['mototaxis_cargadas_100'] += 1
            
            # Verificar si debe partir (tiempo maximo en estacionamiento)
            hours_parked = current_hour - trip.arrival_hour
            
            if trip.current_soc >= trip.target_soc and hours_parked >= 1.0:
                # Puede partir si alcanzo target y paso tiempo minimo
                trip.departure_hour = current_hour
                trip.departure_soc = trip.current_soc
                trip.state = VehicleState.IN_USE
                
                # Simular descarga durante viaje
                trip.discharge_in_trip(trip.expected_trip_duration_hours)
                
                self.completed_trips.append(trip)
                vehicles_to_remove.append(trip_key)
                stats['departed'] += 1
            
            elif trip.is_overdue(current_hour):
                # Forzar partida si esta retrasado
                trip.departure_hour = current_hour
                trip.departure_soc = trip.current_soc
                trip.state = VehicleState.IN_USE
                trip.discharge_in_trip(trip.expected_trip_duration_hours)
                
                self.completed_trips.append(trip)
                vehicles_to_remove.append(trip_key)
                stats['departed'] += 1
            
            elif hours_parked < 0.5:
                stats['departing_soon'] += 1
        
            # Remover viajes completados
        for trip_key in vehicles_to_remove:
            if trip_key in self.active_trips:
                del self.active_trips[trip_key]
        
        return stats
    
    def get_statistics(self) -> Dict:
        """Obtener estadisticas finales del ano"""
        
        stats = {
            'total_trips': len(self.completed_trips),
            'trips_by_type': {'moto': 0, 'mototaxi': 0},
            'charging_statistics': {
                'motos_charged_100': 0,
                'mototaxis_charged_100': 0,
                'total_energy_charged_kwh': 0.0,
                'avg_charge_time_hours': 0.0,
            },
            'trip_statistics': {
                'motos_avg_arrival_soc': 0.0,
                'motos_avg_departure_soc': 0.0,
                'mototaxis_avg_arrival_soc': 0.0,
                'mototaxis_avg_departure_soc': 0.0,
            }
        }
        
        motos = [t for t in self.completed_trips if t.vehicle_type == 'moto']
        mototaxis = [t for t in self.completed_trips if t.vehicle_type == 'mototaxi']
        
        stats['trips_by_type']['moto'] = len(motos)
        stats['trips_by_type']['mototaxi'] = len(mototaxis)
        
        # Charging stats
        stats['charging_statistics']['motos_charged_100'] = sum(1 for t in motos if t.departure_soc >= 99.0)
        stats['charging_statistics']['mototaxis_charged_100'] = sum(1 for t in mototaxis if t.departure_soc >= 99.0)
        stats['charging_statistics']['total_energy_charged_kwh'] = sum(t.energy_charged_kwh for t in self.completed_trips)
        
        if motos:
            stats['charging_statistics']['motos_charged_100_pct'] = stats['charging_statistics']['motos_charged_100'] / len(motos) * 100.0
            stats['trip_statistics']['motos_avg_arrival_soc'] = np.mean([t.arrival_soc for t in motos])
            stats['trip_statistics']['motos_avg_departure_soc'] = np.mean([t.departure_soc for t in motos])
        
        if mototaxis:
            stats['charging_statistics']['mototaxis_charged_100_pct'] = stats['charging_statistics']['mototaxis_charged_100'] / len(mototaxis) * 100.0
            stats['trip_statistics']['mototaxis_avg_arrival_soc'] = np.mean([t.arrival_soc for t in mototaxis])
            stats['trip_statistics']['mototaxis_avg_departure_soc'] = np.mean([t.departure_soc for t in mototaxis])
        
        total_trip_hours = sum(t.charge_end_hour - t.charge_start_hour if t.charge_end_hour else 0 for t in self.completed_trips)
        if self.completed_trips:
            stats['charging_statistics']['avg_charge_time_hours'] = total_trip_hours / len(self.completed_trips)
        
        return stats


if __name__ == '__main__':
    # Prueba del simulador
    print("\n" + "="*80)
    print("SIMULADOR DE CICLOS DE VEHICULOS (VUELTAS)")
    print("="*80)
    
    simulator = VehicleCycleSimulator(n_motos=30, n_mototaxis=8)
    simulator.generate_yearly_schedule()
    
    print(f"\nCronograma generado: {len(simulator.scheduled_trips)} horas con llegadas")
    print(f"Total de viajes programados: {sum(len(v) for v in simulator.scheduled_trips.values())}")
    
    # Simular 3 dias
    print("\nSimulando primeros 3 dias (72 horas)...")
    
    for hour in range(72):
        # Simular asignacion de potencia (random por ahora)
        chargers = {i: np.random.uniform(0, 7.4) for i in range(38)}
        
        stats = simulator.update_hourly(hour, chargers)
        
        if hour % 24 == 0:
            day = hour // 24
            print(f"\nDia {day + 1}:")
            print(f"  Llegadas nuevas: {stats['new_arrivals']}")
            print(f"  Activos ahora: {stats['trips_active']}")
            print(f"  Cargando: {stats['trips_charging']}")
            print(f"  Cargados (listos): {stats['trips_charged']}")
            print(f"  Partieron: {stats['departed']}")
            print(f"  Motos 100%: {stats['motos_cargadas_100']}")
            print(f"  Mototaxis 100%: {stats['mototaxis_cargadas_100']}")
    
    # Estadisticas
    final_stats = simulator.get_statistics()
    print("\n" + "="*80)
    print("ESTADISTICAS DEL ANO (extrapoladas de 3 dias)")
    print("="*80)
    print(f"\nViajes completados (3 dias): {final_stats['total_trips']}")
    print(f"  Motos: {final_stats['trips_by_type']['moto']}")
    print(f"  Mototaxis: {final_stats['trips_by_type']['mototaxi']}")
    
    print(f"\nCarga:")
    print(f"  Motos al 100%: {final_stats['charging_statistics']['motos_charged_100']} (~{final_stats['charging_statistics'].get('motos_charged_100_pct', 0):.1f}%)")
    print(f"  Mototaxis al 100%: {final_stats['charging_statistics']['mototaxis_charged_100']} (~{final_stats['charging_statistics'].get('mototaxis_charged_100_pct', 0):.1f}%)")
    print(f"  Energia total: {final_stats['charging_statistics']['total_energy_charged_kwh']:.0f} kWh")
    
    print(f"\nSOC promedio:")
    print(f"  Motos llegada: {final_stats['trip_statistics']['motos_avg_arrival_soc']:.1f}%")
    print(f"  Motos partida: {final_stats['trip_statistics']['motos_avg_departure_soc']:.1f}%")
    print(f"  Mototaxis llegada: {final_stats['trip_statistics']['mototaxis_avg_arrival_soc']:.1f}%")
    print(f"  Mototaxis partida: {final_stats['trip_statistics']['mototaxis_avg_departure_soc']:.1f}%")
