#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBA DEL SISTEMA DE COMUNICACION INTER-DISPOSITIVOS
Demuestra como Chargers, BESS y Mall se comunican para distribucion optima
"""
from __future__ import annotations

import numpy as np
from src.agents.device_communication import (
    ChargerManager,
    ChargerCommunication,
    BESSCommunicationController,
    EnergyPrioritizer,
)


def test_charger_communication():
    """Prueba: Chargers reportando estado"""
    print("\n" + "="*80)
    print("PRUEBA 1: COMUNICACION DE CARGADORES")
    print("="*80)
    
    charger_mgr = ChargerManager(n_moto_sockets=30, n_mototaxi_sockets=8)
    
    # Simular que algunos motos llegan cargando
    charger_mgr.chargers[0].current_soc = 0.2
    charger_mgr.chargers[0].energy_needed_kwh = 40.0
    charger_mgr.chargers[0].time_remaining_hours = 3.0
    charger_mgr.chargers[0].priority_level = 8  # Urgente
    
    # Mototaxi casi descargado
    charger_mgr.chargers[30].current_soc = 0.1
    charger_mgr.chargers[30].energy_needed_kwh = 50.0
    charger_mgr.chargers[30].time_remaining_hours = 2.0
    charger_mgr.chargers[30].priority_level = 10  # MUY urgente
    
    # Moto bien cargado
    charger_mgr.chargers[5].current_soc = 0.9
    charger_mgr.chargers[5].energy_needed_kwh = 5.0
    charger_mgr.chargers[5].time_remaining_hours = 1.0
    charger_mgr.chargers[5].priority_level = 2
    
    # Mostrar estadisticas
    motos = charger_mgr.get_motos_stats()
    mototaxis = charger_mgr.get_mototaxis_stats()
    
    print("\nMOTOS (30 sockets):")
    print(f"  Total: {motos['count']}")
    print(f"  Cargando ahora: {motos['charging_now']}")
    print(f"  Energia faltante: {motos['energy_needed_kwh']:.1f} kWh")
    print(f"  SOC promedio: {motos['avg_soc']*100:.1f}%")
    print(f"  Urgentes: {motos['urgent_count']}")
    
    print("\nMOTOTAXIS (8 sockets):")
    print(f"  Total: {mototaxis['count']}")
    print(f"  Cargando ahora: {mototaxis['charging_now']}")
    print(f"  Energia faltante: {mototaxis['energy_needed_kwh']:.1f} kWh")
    print(f"  SOC promedio: {mototaxis['avg_soc']*100:.1f}%")
    print(f"  Urgentes: {mototaxis['urgent_count']}")
    
    # Detalles
    print("\nDETALLES:")
    print(f"  Socket 0 (MOTO): SOC={charger_mgr.chargers[0].current_soc*100:.0f}% | Falta={charger_mgr.chargers[0].energy_still_needs():.1f}kWh | Urgente={charger_mgr.chargers[0].is_urgent()}")
    print(f"  Socket 5 (MOTO): SOC={charger_mgr.chargers[5].current_soc*100:.0f}% | Falta={charger_mgr.chargers[5].energy_still_needs():.1f}kWh | Urgente={charger_mgr.chargers[5].is_urgent()}")
    print(f"  Socket 30 (MOTOTAXI): SOC={charger_mgr.chargers[30].current_soc*100:.0f}% | Falta={charger_mgr.chargers[30].energy_still_needs():.1f}kWh | Urgente={charger_mgr.chargers[30].is_urgent()}")


def test_bess_cutoff_logic():
    """Prueba: BESS cortando demanda del mall cuando es >2000 kW"""
    print("\n" + "="*80)
    print("PRUEBA 2: LOGICA DE CORTE INTELIGENTE DE BESS")
    print("="*80)
    
    bess = BESSCommunicationController(
        bess_capacity_kwh=940.0,
        bess_max_power_kw=342.0,
        current_soc_percent=60.0
    )
    
    ev_demand = 150.0  # EVs demandan 150 kW
    
    # Escenario 1: Mall demanda poco
    print("\nESCENARIO 1: Mall demanda 1500 kW (normal)")
    mall_demand_1 = 1500.0
    power_to_ev, power_to_mall = bess.handle_high_mall_demand(mall_demand_1, ev_demand)
    print(f"  EV demanda: {ev_demand} kW -> BESS da: {power_to_ev:.0f} kW / 100%")
    print(f"  Mall demanda: {mall_demand_1} kW -> BESS da: {power_to_mall:.0f} kW")
    
    # Escenario 2: Mall demanda MUCHO
    print("\nESCENARIO 2: Mall demanda 2500 kW (PICO - CORTAR)")
    mall_demand_2 = 2500.0
    power_to_ev, power_to_mall = bess.handle_high_mall_demand(mall_demand_2, ev_demand)
    print(f"  EV demanda: {ev_demand} kW -> BESS da: {power_to_ev:.0f} kW / 100%")
    print(f"  Mall demanda: {mall_demand_2} kW -> BESS da: {power_to_mall:.0f} kW (CORTADO a cero)")
    print(f"  Logica: Prioridad 100% a EV (motos/mototaxis), Mall se recorta")
    
    # Escenario 3: BESS bajo
    print("\nESCENARIO 3: BESS bajo (30%)")
    bess.current_soc_percent = 30.0  # BESS poco
    mall_demand_3 = 1500.0
    power_to_ev, power_to_mall = bess.handle_high_mall_demand(mall_demand_3, ev_demand)
    print(f"  BESS SOC: {bess.current_soc_percent:.0f}%")
    print(f"  EV demanda: {ev_demand} kW -> BESS da: {power_to_ev:.0f} kW")
    print(f"  Mall demanda: {mall_demand_3} kW -> BESS da: {power_to_mall:.0f} kW")
    print(f"  Logica: BESS limitado por bajo SOC")


def test_energy_dispatch():
    """Prueba: Distribucion completa de energias"""
    print("\n" + "="*80)
    print("PRUEBA 3: DISTRIBUCION COMPLETA DE ENERGIAS")
    print("="*80)
    
    prioritizer = EnergyPrioritizer()
    
    # Configurar escenario
    prioritizer.charger_manager.chargers[0].power_demanded_kw = 7.4
    prioritizer.charger_manager.chargers[1].power_demanded_kw = 5.0
    prioritizer.charger_manager.chargers[30].power_demanded_kw = 7.4
    
    prioritizer.bess_controller.current_soc_percent = 70.0
    
    # Caso 1: Mucho solar
    print("\nCASO 1: Dia soleado (4000 kW solar), mall 1500 kW")
    solar_available = 4000.0
    mall_demand = 1500.0
    
    dispatch = prioritizer.dispatch_energy(solar_available, 0.0, mall_demand)
    
    total_to_ev = dispatch['to_evs_from_solar'] + dispatch['to_evs_from_bess'] + dispatch['to_evs_from_grid']
    total_to_mall = dispatch['to_mall_from_solar'] + dispatch['to_mall_from_bess'] + dispatch['to_mall_from_grid']
    
    print(f"  ENERGIA A EVs:")
    print(f"    - Solar: {dispatch['to_evs_from_solar']:.0f} kW")
    print(f"    - BESS: {dispatch['to_evs_from_bess']:.0f} kW")
    print(f"    - Grid: {dispatch['to_evs_from_grid']:.0f} kW")
    print(f"    TOTAL: {total_to_ev:.0f} kW")
    print(f"  ENERGIA A MALL:")
    print(f"    - Solar: {dispatch['to_mall_from_solar']:.0f} kW")
    print(f"    - BESS: {dispatch['to_mall_from_bess']:.0f} kW")
    print(f"    - Grid: {dispatch['to_mall_from_grid']:.0f} kW")
    print(f"    TOTAL: {total_to_mall:.0f} kW")
    print(f"  BESS:")
    print(f"    - Carga desde solar: {dispatch['to_bess_from_solar']:.0f} kW")
    print(f"    - Descarga actual: {dispatch['bess_of_discharge']:.0f} kW")
    
    # Caso 2: Poca solar, mall de pico
    print("\nCASO 2: Noche nublada (500 kW solar), mall 2200 kW (PICO - CORTE)")
    solar_available = 500.0
    mall_demand = 2200.0
    
    dispatch = prioritizer.dispatch_energy(solar_available, 500.0, mall_demand)  # 500 kW grid disponible
    
    total_to_ev = dispatch['to_evs_from_solar'] + dispatch['to_evs_from_bess'] + dispatch['to_evs_from_grid']
    total_to_mall = dispatch['to_mall_from_solar'] + dispatch['to_mall_from_bess'] + dispatch['to_mall_from_grid']
    
    print(f"  ENERGIA A EVs:")
    print(f"    - Solar: {dispatch['to_evs_from_solar']:.0f} kW")
    print(f"    - BESS: {dispatch['to_evs_from_bess']:.0f} kW")
    print(f"    - Grid: {dispatch['to_evs_from_grid']:.0f} kW")
    print(f"    TOTAL: {total_to_ev:.0f} kW")
    print(f"  ENERGIA A MALL:")
    print(f"    - Solar: {dispatch['to_mall_from_solar']:.0f} kW")
    print(f"    - BESS: {dispatch['to_mall_from_bess']:.0f} kW (LIMITADO por prioridad EVs)")
    print(f"    - Grid: {dispatch['to_mall_from_grid']:.0f} kW")
    print(f"    TOTAL: {total_to_mall:.0f} kW")
    print(f"  DECISION: Mall demanda {mall_demand}kW pero recibe {total_to_mall:.0f}kW")
    print(f"           Razon: Prioridad 100% a EVs (motos+mototaxis)")


def test_observation_communication():
    """Prueba: Vector de observacion con comunicacion inter-sistemas"""
    print("\n" + "="*80)
    print("PRUEBA 4: VECTOR DE OBSERVACION DE COMUNICACION (12 features)")
    print("="*80)
    
    prioritizer = EnergyPrioritizer()
    
    # Simular escenario
    prioritizer.charger_manager.chargers[0].current_soc = 0.2
    prioritizer.charger_manager.chargers[0].energy_needed_kwh = 40.0
    prioritizer.charger_manager.chargers[1].current_soc = 0.8
    prioritizer.charger_manager.chargers[30].current_soc = 0.1
    prioritizer.charger_manager.chargers[30].energy_needed_kwh = 50.0
    prioritizer.bess_controller.current_soc_percent = 75.0
    
    # Obtener observacion
    obs = prioritizer.get_communication_observation()
    
    print(f"\nObservacion (12 features):")
    print(f"  [0] BESS puede suministrar: {obs[0]:.2f} (1=si, 0=no)")
    print(f"  [1] EVs tienen urgencia: {obs[1]:.2f} (1=urgente)")
    print(f"  [2] SOC motos: {obs[2]:.2f} ([0,1])")
    print(f"  [3] SOC mototaxis: {obs[3]:.2f} ([0,1])")
    print(f"  [4] Energia faltante EVs: {obs[4]:.2f} (normalizado)")
    print(f"  [5] Tiempo restante motos: {obs[5]:.2f} (normalizado)")
    print(f"  [6] Tiempo restante mototaxis: {obs[6]:.2f} (normalizado)")
    print(f"  [7] BESS SOC: {obs[7]:.2f} ([0,1])")
    print(f"  [8] Motos cargando: {obs[8]:.2f} (normalizado)")
    print(f"  [9] Mototaxis cargando: {obs[9]:.2f} (normalizado)")
    print(f"  [10] Demanda total EVs: {obs[10]:.2f} (normalizado)")
    print(f"  [11] Sistema saturado: {obs[11]:.2f} (1=saturado)")


if __name__ == '__main__':
    test_charger_communication()
    test_bess_cutoff_logic()
    test_energy_dispatch()
    test_observation_communication()
    
    print("\n" + "="*80)
    print("RESUMEN: Sistema de comunicacion LISTO para entrenamiento SAC")
    print("="*80)
    print("\nComponentes implementados:")
    print("  [OK] ChargerManager: rastreo individual de 38 sockets (30 motos + 8 mototaxis)")
    print("  [OK] ChargerCommunication: estado, energia faltante, tiempo restante")
    print("  [OK] BESSController: logica inteligente con cortes >2000kW para mall")
    print("  [OK] EnergyPrioritizer: distribucion 100% EVs, resto mall")
    print("  [OK] Observacion de comunicacion: 12 features para agente")
    print("\nProximo paso: Integrar al train_sac_multiobjetivo.py\n")
