SISTEMA DE COMUNICACION INTER-DISPOSITIVOS v5.3
Arquitectura de Entrenamiento SAC con Rastreo Modular

================================================================================
RESUMEN EJECUTIVO
================================================================================

El agente SAC ahora controla un sistema de 3 componentes que se comunican:

1. CHARGERS (38 sockets: 30 motos + 8 mototaxis)
   - Cada socket reporta: SOC [0,100%], energia_faltante [kWh], tiempo_restante [horas]
   - Rastrean urgencia (SOC bajo + tiempo bajo)
   - Separaci

on motos (sockets 0-29) vs mototaxis (sockets 30-37)

2. BESS (Bateria 940 kWh)
   - Control: action[0] [0,1] -> carga/idle/descarga
   - Logica inteligente de cortes: si mall_demand >2000kW -> cortar al mall
   - 100% prioridad a EVs (motos + mototaxis)
   - Carga desde solar excedente

3. MALL (Demanda comercial)
   - Suministro limitado cuando demanda >2000kW (corte del 20-22%)
   - Recibe energia: solar excedente + BESS idle + grid
   - Penalidad de demanda alta en reward

COMUNICACION: Los 3 componentes reportan estado, agente coordina distribucion

================================================================================
ARQUITECTURA DETALLADA
================================================================================

COMPONENTE 1: CHARGER MANAGER
---

Clase: ChargerManager (device_communication.py)
Responsabilidad: Rastrear estado individual de 38 sockets

Estructura:
  chargers: Dict[socket_id: int, ChargerCommunication]
  
  MOTOS (30 sockets):
    - IDs: 0-29
    - Capacidad bateria: 48 kWh
    - Max SOC: 80% (usos frecuentes)
    - Potencia nominal: 7.4 kW
  
  MOTOTAXIS (8 sockets):
    - IDs: 30-37
    - Capacidad bateria: 60 kWh
    - Max SOC: 100% (viajes largos)
    - Potencia nominal: 7.4 kW

Por Socket (ChargerCommunication):
  - current_soc: [0, 1] fraccion de carga
  - energy_needed_kwh: kWh necesarios para llegar target
  - time_remaining_hours: Horas hasta desconexion
  - energy_charged_so_far_kwh: Acumulativo por ciclo
  - priority_level: [1, 10] para arbitrage cuando hay escasez
  - is_urgent(): True si time_remaining <2h Y energy_needed >5kWh

Metodos claves:
  - get_motos_stats(): Dict con count, charging_now, energy_needed, avg_soc, urgent_count
  - get_mototaxis_stats(): Idem para mototaxis
  - total_ev_energy_demand_kwh(): Suma demanda EVs
  - update_chargers(power_per_socket, time_step): Actualizar SOC cada hora

Flow ejemplo:
  h=8 (8:00 AM):
    - 15 motos conectadas (sockets 0-14), SOC promedio 20%
    - 4 mototaxis conectadas (sockets 30-33), SOC promedio 5%
    - 2 motos urgentes (socket 3, 7)
    - 1 mototaxi urgente (socket 30)
    
  Agent action[1:39] = [0.5, 0.7, 0.8, 0.9, ...] (40 potencias)
  
  Translation:
    - Socket 0-14: potencia 0-7.4 kW segun action
    - Socket 15-29: sin vehiculo (0 kW)
    - Socket 30-33: potencia segun action
    - Socket 34-37: sin vehiculo (0 kW)
  
  charger_manager.update_chargers(power_array):
    - Modo 1 (socket 0): +0.5*7.4=3.7kWh en 1 hora -> SOC +3.7/48=7.7%
    - Modo 7 (socket 3): +0.8*7.4=5.92kWh -> SOC +12.3% (URGENTE, prioridad)
    - Mototaxi 30: +0.9*7.4=6.66kWh -> SOC +11.1%


COMPONENTE 2: BESS COMMUNICATION CONTROLLER
---

Clase: BESSCommunicationController (device_communication.py)
Responsabilidad: Distribucion inteligente con cortes al mall

Parametros:
  - capacity_kwh: 940 kWh
  - max_power_kw: 342 kW (potencia maxima descarga)
  - mall_max_power_kw: 2000 kW (limite demanda mall)

Estados posibles:
  - CARGA (action < 0.45): bess_action -> charge_power en [0, 171] kW
  - IDLE (action [0.45, 0.55]): sin movimiento
  - DESCARGA (action > 0.55): bess_action -> discharge_power en [0, 342] kW

Logica de cortes inteligentes:

  Si mall_demand >= 2000kW:
    -> 100% energia a EVs (motos + mototaxis)
    -> REST

O a mall = 0 (CORTE TOTAL)
    -> Razon: grid termico saturado, priorizar EVs
    -> Ahorro CO2: EVs evitan gasolina (directo), mall usa grid
  
  Si mall_demand < 2000kW:
    -> 100% energia a EVs
    -> Resto a mall (segun disponibilidad BESS)
    
  Carga desde solar:
    -> Si hay excedente solar (solar > demanda EVs + mall)
    -> Cargar BESS hasta 100%

Estados SOC BESS:
  - [0, 10%]: Sin energía (panic mode)
  - [10%, 20%]: Crítico (limitar descargas)
  - [20%, 50%]: Bajo (solo emergencias)
  - [50%, 80%]: Normal (descarga completa disponible)
  - [80%, 100%]: Lleno (cargar limitado, priorizar uso)

Metodos claves:
  - can_supply_to_evs(ev_power_demand): -> (power_to_ev, remaining_power)
  - handle_high_mall_demand(mall_demand, ev_demand): -> (power_to_ev, power_to_mall)
  - charge_from_solar(solar_available, ...): -> energy_charged_kwh
  - simulate_discharge(discharge_kw): -> energy_discharged_kwh
  - get_status_message(): -> {soc_percent, status, can_discharge}

Flow ejemplo BESS:

  h=10 (10:00 AM): MAÑANA soleada
    - Solar: 3500 kW
    - EVs demanda: 200 kW (20 motos + 2 mototaxis)
    - Mall demanda: 1500 kW
    - BESS SOC: 40%
    
    Logica:
    1. Solar a EVs: min(3500, 200) = 200 kW (100% EVs)
    2. Solar a Mall: min(3300, 1500) = 1500 kW (100% mall)
    3. Solar excedente: 3500 - 200 - 1500 = 1800 kW
    4. Cargar BESS: min(1800, 342) = 342 kW
    5. Resultado: BESS +3.42 kWh en 1h -> SOC sube 0.36%

  h=19 (19:00): NOCHE con pico mall
    - Solar: 50 kW (atardecer)
    - EVs demanda: 180 kW (carga nocturna)
    - Mall demanda: 2800 kW (PICO)
    - BESS SOC: 70%
    
    Logica:
    1. Solar a EVs: 50 kW
    2. EV faltante: 180 - 50 = 130 kW
    3. BESS a EVs: min(130, 240) = 130 kW (70% SOC = 240kW disponible)
    4. Solar a Mall: 0 kW (ya asignado)
    5. BESS a Mall: 0 kW (CORTE por >2000kW en mall)
    6. Mall debe importar: 2800 kW del grid
    7. BESS descarga: 130 kW -> SOC baja 1.3%


COMPONENTE 3: ENERGY PRIORITIZER
---

Clase: EnergyPrioritizer (device_communication.py)
Responsabilidad: Orquestar distribucion global de energias

Metodo principal: dispatch_energy()

Entrada:
  - solar_available_kw: Generacion solar en hora h
  - grid_available_kw: Importacion grid maxima
  - mall_demand_kw: Demanda del mall
  - time_step: 1.0 horas

Proceso (prioridades):

  Paso 1: Obtener demandas
    - ev_demand = charger_manager.total_ev_power_demand_kw()
  
  Paso 2: 100% a EVs (PRIORIDAD MAXIMA)
    - to_evs_solar = min(solar_available, ev_demand)
    - ev_faltante = max(0, ev_demand - to_evs_solar)
    - to_evs_bess = min(ev_faltante, bess.can_supply_to_evs())
    - ev_faltante_2 = max(0, ev_faltante - to_evs_bess)
    - to_evs_grid = ev_faltante_2  # Grid completa
  
  Paso 3: Resto a Mall (PRIORIDAD MEDIA)
    - solar_after_ev = max(0, solar_available - to_evs_solar)
    - to_mall_solar = min(solar_after_ev, mall_demand)
    - mall_faltante = max(0, mall_demand - to_mall_solar)
    - to_mall_bess = bess.handle_high_mall_demand(...) <- LOGICA DE CORTES
    - mall_faltante_2 = max(0, mall_faltante - to_mall_bess)
    - to_mall_grid = mall_faltante_2
  
  Paso 4: Cargar BESS desde excedente (PRIORIDAD BAJA)
    - bess_charge_solar = bess.charge_from_solar(...)
    
  Retorna:
    dispatch = {
      'to_evs_from_solar': float,
      'to_evs_from_bess': float,
      'to_evs_from_grid': float,
      'to_mall_from_solar': float,
      'to_mall_from_bess': float,
      'to_mall_from_grid': float,
      'to_bess_from_solar': float,
      'bess_of_discharge': float,
      'bess_charge': float,
    }

Metodo secundario: get_communication_observation()

Retorna vector [12] de observacion:
  [0] BESS puede suministrar (1 si SOC>20%)
  [1] EVs tienen urgencia (1 si hay urgentes)
  [2] SOC promedio motos
  [3] SOC promedio mototaxis
  [4] Energia faltante EVs (normalizado)
  [5] Tiempo restante motos
  [6] Tiempo restante mototaxis
  [7] BESS SOC
  [8] Motos cargando (normalizado)
  [9] Mototaxis cargando (normalizado)
  [10] Demanda total EVs (normalizado)
  [11] Sistema saturado (1 si >20 vehiculos cargando)

================================================================================
FLUJO EN ENTRENAM IENTO SAC (por timestep)
================================================================================

h=10 (ejemplo)

ENTRADA:
  obs[246] = vector de observacion completo

AGENTE:
  actor_network(obs[246]) -> action[39]
  
  action[0] = 0.6 (BESS: 0.6 > 0.55 -> DESCARGA)
  action[1:39] = [0.4, 0.7, 0.5, ..., 0.3] (potencias chargers)

ENVIRONMENT.step(action):
  
  1. DECODIFICAR ACCION
     bess_action = action[0] = 0.6
     charger_actions = action[1:39]
  
  2. APLICAR A CHARGERS
     charger_power_kw = charger_actions * 7.4 kW
     charger_manager.update_chargers(charger_power_kw)
     -> Actualiza SOC de todos los chargers
  
  3. COMUNICACION: BESS + PRIORITIZER
     solar_h = self.solar[h] = 3200 kW (dato real)
     mall_h = self.mall[h] = 1800 kW (dato real)
     
     dispatch = energy_prioritizer.dispatch_energy(
       solar_available_kw=3200,
       grid_available_kw=400,
       mall_demand_kw=1800
     )
     
     dispatch = {
       'to_evs_from_solar': 180,
       'to_evs_from_bess': 50,
       'to_evs_from_grid': 0,
       'to_mall_from_solar': 1700,
       'to_mall_from_bess': 100,
       'to_mall_from_grid': 0,
       'to_bess_from_solar': 1370,
       ...
     }
  
  4. CALCULAR REWARD MULTIOBJETIVO
     
     co2_reward = (solar_h * w_solar - grid_import * CO2_FACTOR) / 10000
     ev_reward = charger_satisfaction (de charger_manager.get_motos_stats(), etc)
     
     [NEW] REWARD DE COMUNICACION:
     
     # Bonus si atendemos urgentes
     motos_urgent = motos_stats['urgent_count']
     mototaxis_urgent = mototaxis_stats['urgent_count']
     
     if motos_urgent + mototaxis_urgent > 0:
       power_to_urgent = dispatch['to_evs_from_solar'] + dispatch['to_evs_from_bess']
       priority_bonus = 0.05 * min(1.0, power_to_urgent / 200.0)
     else:
       priority_bonus = 0.0
     
     # Penalty si mall viola limite
     if mall_h > 2000:
       power_to_mall = dispatch['to_mall_from_solar'] + dispatch['to_mall_from_bess'] + dispatch['to_mall_from_grid']
       if power_to_mall > mall_h * 1.22:
         priority_penalty = -0.05
       else:
         priority_penalty = 0.0
     else:
       priority_penalty = 0.0
     
     reward = base_reward + priority_bonus + priority_penalty
     reward = clip(reward, -1, 1)
  
  5. OBSERVACION SIGUIENTE
     
     communication_obs = energy_prioritizer.get_communication_observation()
     obs_next[144:156] = communication_obs
     
     [otros features del sistema...]
  
  6. RETORNAR
     return obs_next, reward, done, info

================================================================================
METRICAS DE SEGUIMIENTO (por episodio)
================================================================================

MOTOS (30 sockets):
  - total_motos_cargadas_100: int (cuantas llegaron a 100%)
  - motos_soc_promedio: float (SOC% medio al final)
  - motos_urgentes_atendidas: int (urgencias resueltas con energia BESS)
  - motos_energia_total_kwh: float (energia total cargada en episodio)

MOTOTAXIS (8 sockets):
  - total_mototaxis_cargadas_100: int
  - mototaxis_soc_promedio: float
  - mototaxis_urgentes_atendidas: int
  - mototaxis_energia_total_kwh: float

BESS:
  - energia_a_evs_total_kwh: float (BESS -> motos + mototaxis)
  - energia_a_mall_total_kwh: float
  - cortes_al_mall: int (veces que demanda >2000kW)
  - ciclos_completos: int (carga/descarga completo)
  - promedio_soc: float

COMUNICACION (nuevas):
  - urgencias_no_atendidas: int (cuando falta energia)
  - eficiencia_priorizacion: float (% de urgencias resueltas)
  - saturacion_maxima: float (pico de vehiculos cargando)

================================================================================
RESULTADOS ESPERADOS (despues de entrenamiento 3 episodios)
================================================================================

BASELINE (sin comunicacion/control):
  - Motos 100%: 5-8 / 30
  - Mototaxis 100%: 2-3 / 8
  - BESS ciencia: no optimizado
  - CO2 evitado: ~7800 kg/ano

CON CONTROL COMUNICACION:
  - Motos 100%: 22-27 / 30 (+170%)
  - Mototaxis 100%: 6-7 / 8 (+120%)
  - BESS energia a EVs: +45%
  - BESS cortes al mall exitosos: >200 en ano
  - CO2 evitado: ~9200 kg/ano (+18%)

CONVERGENCIA:
  SAC debe aprender que:
  1. Urgentes (tiempo bajo) merecen mayor potencia
  2. Motos/mototaxis diferente estrategia
  3. Solar excedente -> cargar BESS
  4. BESS bajo -> solo EVs, no mall
  5. Mall >2000kW -> cortar para no saturar red

================================================================================
COMANDO PARA ENTRENAR CON COMUNICACION
================================================================================

python scripts/train/train_sac_multiobjetivo.py --enable-communication --log-dispatch


Esto ejecutara:
  - SAC con 3 episodios (26,280 timesteps)
  - ChargerManager rastreando motos vs mototaxis
  - BESSController con logica de cortes
  - EnergyPrioritizer orquestando distribucion
  - Metricas completas de motos, mototaxis, BESS
  - Output: entrenamiento_sac_comunicacion.log

