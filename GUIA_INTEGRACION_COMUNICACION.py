#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIA DE INTEGRACION: COMUNICACION INTER-DISPOSITIVOS EN SAC TRAINING
Conecta ChargerManager, BESSController y EnergyPrioritizer al environment
"""

import numpy as np
from pathlib import Path


# ===== INTEGRACION EN RealOE2Environment.step() =====
"""
Ubicacion: scripts/train/train_sac_multiobjetivo.py ~ linea 1600-1800 (metodo step)

CAMBIOS REQUERIDOS:

1. ACTUALIZAR ACCION DEL AGENTE PARA APLICAR A CHARGERS:
   
   # Agente retorna 39 acciones [0,1]
   action = agent.predict(obs)[0] if is_training else actions
   
   # [NEW] Decodificar acciones
   bess_action = action[0]          # [0,1]: 0=carga max, 0.5=idle, 1=descarga max
   charger_actions = action[1:39]   # [0,1]: potencia normalizada per socket
   
   # [NEW] Aplicar acciones a ChargerManager
   charger_power_kw = charger_actions * self.CHARGER_MAX_KW  # [0, 7.4] kW per socket
   self.charger_manager.update_chargers(charger_power_kw, time_step=1.0)
   
   # Esto actualiza:
   # - charger.current_soc (0-100%)
   # - charger.energy_charged_so_far_kwh
   # - charger.time_remaining_hours
   # - charger.percent_complete()
   # - charger.is_urgent()


2. COMUNICACION ENTRE COMPONENTES (FLUJO DE ENERGIAS):
   
   # Obtener demandas en tiempo real
   solar_kw = float(self.solar[h])
   mall_kw = float(self.mall[h])
   ev_power_demand = self.charger_manager.total_ev_power_demand_kw()  # [NEW]
   
   # [NEW] Usar EnergyPrioritizer para distribuir
   dispatch = self.energy_prioritizer.dispatch_energy(
       solar_available_kw=solar_kw,
       grid_available_kw=300.0,  # Grid max imports
       mall_demand_kw=mall_kw,
       time_step=1.0
   )
   
   # Distribucion resultante:
   # dispatch['to_evs_from_solar'] = energia solar directa a EVs
   # dispatch['to_evs_from_bess'] = energia BESS a EVs
   # dispatch['to_evs_from_grid'] = energia grid a EVs
   # dispatch['to_mall_from_solar'] = energia solar a mall
   # dispatch['to_mall_from_bess'] = energia BESS a mall (limitado si >2000kW)
   # dispatch['to_mall_from_grid'] = energia grid a mall
   # dispatch['bess_of_discharge'] = total BESS descargando
   # dispatch['to_bess_from_solar'] = solar cargando BESS


3. ACTUALIZAR BESS SEGUN ACCION DEL AGENTE:
   
   # Interpretar BESS action [0,1]
   if bess_action < 0.45:  # Carga
       charge_power = (0.5 - bess_action) * BESS_MAX_POWER_KW  # [0, 171] kW
       energy_charged = self.bess_controller.charge_from_solar(
           solar_available_kw=solar_kw,
           ev_demand_kw=ev_power_demand,
           mall_demand_kw=mall_kw,
           time_step=1.0
       )
       
   elif bess_action > 0.55:  # Descarga
       discharge_power = (bess_action - 0.5) * BESS_MAX_POWER_KW
       energy_discharged = self.bess_controller.simulate_discharge(
           discharge_power,
           time_step=1.0
       )
   else:  # Idle [0.45, 0.55]
       pass  # BESS reposa
   
   # Update BESS status message
   bess_status = self.bess_controller.get_status_message()
   print(f"BESS: {bess_status['soc_percent']} ({bess_status['status']})")


4. OBSERVACION CON COMUNICACION (12 FEATURES NUEVAS):
   
   # Agregar al vector de observacion (en _make_observation)
   # Posicion: [144:156] (12 features)
   
   communication_obs = self.energy_prioritizer.get_communication_observation()
   obs[144:156] = communication_obs
   
   # Features:
   # [144] BESS puede suministrar (1 si SOC>20%)
   # [145] EVs urgentes (1 si hay urgencia)
   # [146] SOC promedio motos
   # [147] SOC promedio mototaxis
   # [148] Energia faltante EVs (normalizado)
   # [149] Tiempo restante motos
   # [150] Tiempo restante mototaxis
   # [151] BESS SOC
   # [152] Motos cargando (count normalizado)
   # [153] Mototaxis cargando (count normalizado)
   # [154] Demanda total EVs (normalizado)
   # [155] Sistema saturado (1 si >20 vehiculos)


5. REWARD CON PRIORIZACION COMUNICACION:
   
   # Agregar bonus/penalty para satisfacer comunicacion
   
   # [BONUS] Si EVs tienen urgencia y los alimentamos
   motos_stats = self.charger_manager.get_motos_stats()
   mototaxis_stats = self.charger_manager.get_mototaxis_stats()
   
   urgent_count = motos_stats['urgent_count'] + mototaxis_stats['urgent_count']
   if urgent_count > 0:
       # Bonus si suministramos energía a urgentes
       power_to_urgent = dispatch['to_evs_from_solar'] + dispatch['to_evs_from_bess']
       priority_bonus = 0.05 * (power_to_urgent / 200.0)  # Bonus hasta +0.05
   else:
       priority_bonus = 0.0
   
   # [PENALTY] Si mall recibe mas que lo permitido (cuando demanda >2000kW)
   if mall_kw > 2000.0:
       power_to_mall = dispatch['to_mall_from_solar'] + dispatch['to_mall_from_bess'] + dispatch['to_mall_from_grid']
       if power_to_mall > mall_kw * 0.22:  # >22% corte
           priority_penalty = -0.05
       else:
           priority_penalty = 0.0
   else:
       priority_penalty = 0.0
   
   # Reward final
   base_reward = ... # Calculo existente (CO2, solar, etc)
   final_reward = base_reward + priority_bonus + priority_penalty
   reward = np.clip(final_reward, -1.0, 1.0)


6. METRICAS POR EPISODIO (tracking de comunicacion):
   
   # Rastrear satisfaccion de comunicacion
   
   # Motos metrics
   motos_stats = self.charger_manager.get_motos_stats()
   self.episode_motos_charged_100 += sum(1 for c in self.charger_manager.chargers.values() 
                                         if c.vehicle_type == 'moto' and c.current_soc >= 0.99)
   self.episode_motos_avg_soc = motos_stats['avg_soc']
   self.episode_motos_urgent = motos_stats['urgent_count']
   
   # Mototaxis metrics
   mototaxis_stats = self.charger_manager.get_mototaxis_stats()
   self.episode_mototaxis_charged_100 += sum(1 for c in self.charger_manager.chargers.values() 
                                             if c.vehicle_type == 'mototaxi' and c.current_soc >= 0.99)
   self.episode_mototaxis_avg_soc = mototaxis_stats['avg_soc']
   self.episode_mototaxis_urgent = mototaxis_stats['urgent_count']
   
   # BESS metrics
   self.episode_bess_ev_priority += dispatch['to_evs_from_bess']
   self.episode_bess_mall_cutoffs += 1 if mall_kw > 2000.0 else 0
   
   # Al final del episodio
   if done:
       print(f"MOTOS (30):")
       print(f"  Cargadas 100%: {self.episode_motos_charged_100}")
       print(f"  SOC promedio: {self.episode_motos_avg_soc*100:.1f}%")
       print(f"  Urgentes atendidas: {motos_stats['urgent_count']}")
       print(f"MOTOTAXIS (8):")
       print(f"  Cargadas 100%: {self.episode_mototaxis_charged_100}")
       print(f"  SOC promedio: {self.episode_mototaxis_avg_soc*100:.1f}%")
       print(f"  Urgentes atendidas: {mototaxis_stats['urgent_count']}")
       print(f"BESS Priorizacion:")
       print(f"  Energia a EVs (urgentes): {self.episode_bess_ev_priority:.0f} kWh")
       print(f"  Cortes al mall (>2000kW): {self.episode_bess_mall_cutoffs}")
"""


# ===== CHECKLIST DE CAMBIOS =====
INTEGRATION_CHECKLIST = """
CHECKLIST: Integrar comunicacion inter-dispositivos en SAC

Fase 1: CARGADORES (Chargers)
  [ ] Importar ChargerManager en train_sac_multiobjetivo.py (HECHO)
  [ ] Inicializar self.charger_manager en RealOE2Environment.__init__ (HECHO)
  [ ] Actualizar cargadores en step() con action[1:39]
  [ ] Rastrear SOC, tiempo_restante, energia_faltante por socket
  [ ] Generar observacion parcial para motos vs mototaxis
  
Fase 2: BESS LOGICA DE CORTES
  [ ] Importar BESSCommunicationController (HECHO)
  [ ] Inicializar self.bess_controller en __init__ (HECHO)
  [ ] Decodificar action[0] -> BESS control
  [ ] Aplicar logica: si mall>2000kW -> corte a 0, 100% a EVs
  [ ] Actualizar SOC segun carga/descarga
  [ ] Generar observacion del estado BESS
  
Fase 3: DISTRIBUCION DE ENERGIAS (EnergyPrioritizer)
  [ ] Importar EnergyPrioritizer (HECHO)
  [ ] Inicializar self.energy_prioritizer en __init__ (HECHO)
  [ ] Llamar dispatch_energy() en step()
  [ ] Usar resultados para reward calculation
  [ ] Log de distribucion (debug)
  
Fase 4: OBSERVACION COMPLETA
  [ ] Agregar 12 features de comunicacion a observacion
  [ ] Normalizar [0,1] todas las features
  [ ] Validar dimension final = 246 o ajustar
  [ ] Test de observacion shape
  
Fase 5: REWARD CON PRIORIZACION
  [ ] Bonus si urgentes son atendidas
  [ ] Penalty si mall viola limite
  [ ] Bonus si BESS prioriza correctamente
  [ ] Clip final [-1, 1]
  
Fase 6: METRICAS Y LOGGING
  [ ] Track motos: cargadas_100%, soc_avg, urgentes
  [ ] Track mototaxis: cargadas_100%, soc_avg, urgentes
  [ ] Track BESS: energia_a_evs, cutoffs_mall
  [ ] Mostrar al final episodio
  
Fase 7: VALIDACION
  [ ] Ejecutar 1 episodio y verificar shape observacion
  [ ] Verificar reward no es NaN
  [ ] Verificar accion del agente se aplica correctamente
  [ ] Ejecutar training 3 episodios y verificar convergencia
  [ ] Comparar metricas con baseline
  
Fase 8: DEPLOYMENT
  [ ] Lanzar training SAC con comunicacion
  [ ] Monitorear log (metricas de motos/mototaxis)
  [ ] Verificar BESS cortes estan funcionando
  [ ] Generar reporte final
"""

print(__doc__)
print("\n" + "="*80)
print(INTEGRATION_CHECKLIST)
print("="*80)
