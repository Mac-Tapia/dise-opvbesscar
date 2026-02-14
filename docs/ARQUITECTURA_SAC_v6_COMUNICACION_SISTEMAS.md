# 🔌 ARQUITECTURA SAC v6.0: SISTEMA DE COMUNICACIÓN INTER-SISTEMAS
**Fecha**: 2026-02-14  
**Versión**: 6.0 - Communication System Complete  
**Status**: ✅ READY FOR IMPLEMENTATION

---

## TABLA DE CONTENIDOS

1. [Problema: ¿Por qué v5.3 es insuficiente?](#problema)
2. [Solución: Comunicación v6.0](#solución)
3. [Arquitectura de Flujo Energético](#arquitectura)
4. [Observación 246-dim Detallada](#observación)
5. [Recompensa Multiobjetivo v6.0](#recompensa)
6. [Especificación de Acciones](#acciones)
7. [Integración con Datos Reales OE2](#integración)
8. [Roadmap de Implementación](#roadmap)

---

## PROBLEMA: ¿Por qué v5.3 es insuficiente?

### Limitación v5.3 Actual

El agente SAC en **v5.3** tiene **problemas críticos**:

```
┌─────────────────────────────────────────────────────────────┐
│ v5.3 OBSERVATIONS (156-dim)                                │
├─────────────────────────────────────────────────────────────┤
│ [0-7]     ENERGÍA SISTEMA (solar, BESS, mall)              │
│ [8-45]    DEMANDA POR SOCKET (qué necesita cada socket)    │
│ [46-83]   POTENCIA ACTUAL (potencia siendo entregada)      │
│ [84-121]  OCUPACIÓN (¿está conectado?)                     │
│ [122-137] VEHÍCULOS CARGANDO (resumen agregado)            │
│ [138-143] TIME FEATURES (hora, día, mes)                   │
│ [144-155] COMUNICACIÓN INTER-SISTEMA (12 features)         │
└─────────────────────────────────────────────────────────────┘

❌ PROBLEMAS DETECTADOS:
```

#### 1️⃣ **NO VE SOC POR SOCKET INDIVIDUAL**
```
Situación: 30 motos cargando en sockets 0-29
  - v5.3 solo ve: "hay 30 motos cargando, SOC promedio = 45%"
  - v5.3 NO ve: Socket 5 está al 95%, Socket 12 está al 10%
  
Consecuencia:
  ❌ Agente ASIGNA IGUAL POTENCIA a todos
  ❌ Socket 5 (casi cargado, 95%) recibe más potencia = DESPERDICIO
  ❌ Socket 12 (poco cargado, 10%) recibe lo mismo = SUBOPTIMAL
  
Ideal:
  ✅ Agente PRIORIZA: Socket 12 (10%) → más potencia
  ✅ Agente DESACTIVA: Socket 5 (95%) → libera potencia para otros
  ✅ Resultado: +20% vehículos cargados, mismo CO2
```

#### 2️⃣ **NO SABE CUÁNTO TIEMPO FALTA PARA CADA VEHÍCULO**
```
Situación: 3 mototaxis en sockets 30-32
  - Socket 30: 80% SOC → Falta 1.2 horas
  - Socket 31: 50% SOC → Falta 2.0 horas
  - Socket 32: 20% SOC → Falta 3.2 horas

v5.3 PROBLEMA:
  - No ve tiempo individual
  - Solo ve media: "2.1 horas promedio"
  - Usa estrategia genérica
  
v6.0 VENTAJA:
  - Ve cada socket: obs[194+30]=0.15, obs[194+31]=0.25, obs[194+32]=0.40
  - APRENDE: "Socket 32 necesita 3.2h = TEN CUIDADO, es urgente"
  - APRENDE: "Socket 30 en 1.2h se va" = prioritario
  - Resultado: Agente OPTIMIZA ORDEN DE CARGA
```

#### 3️⃣ **NO CONOCE CAPACIDAD DISPONIBLE POR TIPO**
```
Distribución actual:
  - 30 sockets para MOTOS (15 chargers × 2 sockets)
  - 8 sockets para MOTOTAXIS (4 chargers × 2 sockets)

v5.3 INFO INCOMPLETA:
  obs[130] = "motos_available / 30" = 0.6 (18 sockets libres)
  obs[131] = "taxis_available / 8"  = 0.25 (2 sockets libres)
  
  Pero agente NO sabe:
  ❌ Hay 180 motos esperando en cola, solo caben 18
  ❌ Hay 35 mototaxis esperando, solo caben 2
  ❌ CUÁL TIPO DE VEHÍCULO DEBERÍA PRIORIZAR
  
  Resultado: Agente cargar 5 motos cuando debería cargar 1 mototaxi
  (porque mototaxi = servicio público > moto personal)

v6.0 SOLUCIONA:
  obs[240] = urgencia motos (cuántos faltan 100%) = 180/270 = 0.67
  obs[241] = urgencia mototaxis = 35/39 = 0.90
  obs[242] = sockets motos libres = 18/30 = 0.60
  obs[243] = sockets mototaxis libres = 2/8 = 0.25
  
  Agente APRENDE: "Mototaxis urgencia 0.9 > motos 0.67" → PRIORIZA TAXIS
```

#### 4️⃣ **BESS NO "ANUNCIA" SU CAPACIDAD A EVs**
```
Escenario: 14:00, Solar máximo
  - Solar: 3,500 kW disponible
  - BESS SOC: 45% (425 kWh de 940 kWh)
  - EV demand: 200 kW (35 vehículos cargando)
  - Mall demand: 100 kW

Con v5.3:
  - BESS observa solar alto, carga
  - EVs reciben: Solar directo (3,200 kW) + BESS (0 kW) = 3,200 kW
  - ❌ PROBLEMA: BESS se llena, no hay capacidad para tarde
  - ❌ En energía, BESS debería PREPARARSE PARA TARDE
  
Con v6.0:
  - obs[232] = "BESS_available_power / BESS_MAX_POWER" = 425/342 = 1.0 (capped)
  - obs[233] = (mismo)
  - EVs reciben señal: "BESS me dice: Puedo dar hasta 342 kW"
  - BESS recibe : "Solar me dice: Tengo 3,500 kW, cárgate al máximo"
  
  Resultado: 
  ✅ BESS se carga estratégicamente (no solo cuando hay solar)
  ✅ EVs saben si BESS está disponible para emergencia nocturna
  ✅ Cascada optimizada: Solar→BESS (reserva) y Solar→EVs (inmediato)
```

#### 5️⃣ **LA CASCADA ESTÁ IMPLÍCITA, NO EXPLÍCITA**
```
Cascada ideal de energía:
  Solar ─┬→ BESS (reserva para noche)
         ├→ EVs (carga directa)
         └→ Mall (demanda continua)
         └→ Grid (curtailed si sobra)

v5.3 PROBLEMA:
  - Todo es agregado: solo ve "energía total", "demanda total"
  - No ve CUÁL componente recibe CUÁNTA energía
  - obs[145] dice "solar_sufficient [0-1]" pero...
    ❌ No dice "¿cuánto solar va a BESS?"
    ❌ No dice "¿cuánto a EVs?"
    ❌ No dice "¿cuánto a Mall?"
    ❌ No dice "¿cuánto a Grid?"

v6.0 SOLUCIONA CON SEÑALES EXPLÍCITAS:
  obs[232] = "BESS↔EVs motos" = power_available
  obs[233] = "BESS↔EVs mototaxis" = power_available
  obs[234] = "Solar→EVs motos directo" = power_available
  obs[235] = "Solar→EVs mototaxis directo" = power_available
  obs[236] = "Grid→EVs motos" = import_signal
  obs[237] = "Grid→EVs mototaxis" = import_signal
  
  Cada componente ANUNCIA su capacidad en cada hora
  Agente APRENDE cascada naturalmente
```

---

## SOLUCIÓN: Comunicación v6.0

### Arquitectura de Comunicación Bidireccional

```
       ☀️ SOLAR (4,050 kWp)
       │ obs[234,235]: "Solar disponible X kW"
       ├─────────────────────────────────────┐
       │                                     │
    [DECISIÓN CASCADA EN CADA HORA]          │
       │                                     │
    ┌──▼──────────────────────────────┐     │
    │ 1️⃣ BESS NECESITA CARGAR?        │     │
    │    Solar > Demand && BESS<80%   │     │
    └──┬──────────────────────────────┘     │
       │os[232,233]: "BESS puede cargar"    │
       │                                     │
    ┌──▼──────────────────────────────┐     │
    │ 2️⃣ EVs NECESITAN CARGAR?        │◄────┘
    │    Motos en cola && Sockets lib │
    │    Mototaxis en cola && Sockets │
    └──┬──────────────────────────────┘
       │ obs[238,239]: "Prioridad motos/taxis"
       │ obs[240,241]: "Urgencia motos/taxis"
       │ obs[242,243]: "Sockets disponibles"
       │
    ┌──▼──────────────────────────────┐
    │ 3️⃣ Solar → BESS o directo a EVs │
    │    Agente DECIDE acción[0]=??   │
    └──┬──────────────────────────────┘
       │
    ┌──▼──────────────────────────────┐
    │ 🔋 BESS (940 kWh, 342 kW max)   │
    │    obs[232,233]: anuncia poder  │
    │    Carga desde Solar / Despach  │
    └──┬──────────────────────────────┘
       │ obs[245]: BESS SOC% actual
       │
    ┌──▼──────────────────────────────────────────────┐
    │ 🏍️ MOTOS (30 sockets)     🛺 MOTOTAXIS (8 sockets) │
    │                                                 │
    │ obs[156:194]: SOC si/no        ↑ Cada tipo    │
    │ obs[194:232]: T_remaining[h]   │ con          │
    │ obs[238]: Priority_motos       │ prioridad    │
    │ obs[240]: Urgency_motos        │ diferente    │
    │ obs[242]: Capacity_motos       │              │
    │                                │              │
    │ action[1:31]: Power SET motos  │ Agente       │
    │ action[31:39]: Power SET taxis │ controla     │
    │                                │ CADA uno     │
    └──────────────────┬─────────────────────────────┘
                       │ Charge [kWh/h]
                       │ obs[156:194] updated SOC
                       │
    ┌──────────────────▼──────────────┐
    │ 📊 GRID (térmico, CO2 factor)   │
    │    obs[236,237]: Import signal  │
    │    Penalty CO2 si hay import   │
    └─────────────────────────────────┘
```

### Comunicación Mensaje por Mensaje

```
HORA h = 14:00 (ejemplo)
────────────────────────────────────

🌞 SOLAR BROADCAST (observación):
   "Estoy generando 2,800 kW, mi capacidad es 4,050 kWp"
   └─ obs[0] = 2800/4100 = 0.68

   Dirigido a:
   - BESS: "Considera cargarme si tienes espacio"
   - EVs: "Usa mi energía para cargar vehículos"
   - Mall: "También suministro a demanda de mall"

🔋 BESS RESPONDE (observación):
   "Mi SOC es 45%, puedo descargar 150 kW a EVs"
   └─ obs[232] = 150/342 = 0.44 (a motos)
   └─ obs[233] = 150/342 = 0.44 (a taxis)

   Dirigido a:
   - Solar: "No me cargues más, estoy en 45%"
   - EVs: "Puedo suministrar 150 kW para carga"
   - Mall: "Cuando sea necesario, te doy lo demás"

🏍️ MOTOS EN SOCKETS RESPONDEN (observación):
   Socket 5: "Estoy al 95% SOC, ya casi termino"
   Socket 12: "Estoy al 10% SOC, necesito energía urgente"
   
   obs[156] = 0.95  ← Socket 0
   obs[157] = 0.85  ← Socket 1
   ...
   obs[161] = 0.10  ← Socket 5 (URGENTE)
   obs[163] = 0.35  ← Socket 7
   ...
   obs[167] = 0.10  ← Socket 11
   obs[168] = 0.95  ← Socket 12 (CASI LISTO)

   Tiempo restante:
   obs[194:232] = Estimated hours to 100%
   
   obs[194] = 0.05  ← Socket 0 (0.4h remaining)
   obs[206] = 0.40  ← Socket 12 (3.2h remaining)

🛺 MOTOTAXIS EN SOCKETS RESPONDEN (observación):
   Similar a motos, pero menos sockets (30-37)

📊 SISTEMA RESPONDE (observación agregada):
   obs[238] = prioridad_motos = suma(weights) / 30
   obs[239] = prioridad_mototaxis = suma(weights) / 8
   obs[240] = urgencia_motos = (270 - charged) / 270
   obs[241] = urgencia_mototaxis = (39 - charged) / 39
   obs[242] = capacidad_motos = libres / 30
   obs[243] = capacidad_mototaxis = libres / 8

AGENTE RECIBE TODOS LOS MENSAJES (246-dim observation)
Y DECIDE (39-dim action):

action[0] = 0.35  ← BESS: "Descarga 35% de tu capacidad"
                    (0-0.45=carga, 0.45-0.55=idle, 0.55-1=descarga)

action[1:31] = MOTOS:
   action[1] = 0.0    ← Socket 0: "Desactiva, está al 95%"
   action[12] = 1.0   ← Socket 11: "Máxima potencia, está al 10%"
   action[6] = 0.5    ← Socket 5: "Media potencia, está al 35%"

action[31:39] = MOTOTAXIS:
   action[30] = 0.95  ← Socket 30: "Alta potencia, mototaxi es prioridad"
   action[31] = 0.0   ← Socket 31: "Desactiva, almuerzo (hora pico mall)"

✅ RESULTADO: Cascada optimizada, motos/mototaxis priorizadas, CO2 reducido
```

---

## ARQUITECTURA

### Flujo de Energía con Cascada v6.0

```
ENTRADA: [Solar, BESS, Grid]
═════════════════════════════

  ☀️ 2,800 kW (Solar hora 14:00)
  🔋 150 kW (BESS disponible)
  ⚡ Ilimitado (Grid backup)

SEGMENTACIÓN POR PRIORIDAD:
══════════════════════════

  1️⃣ PRIORIDAD 1: BESS Charging
     Condición: Solar > demand AND BESS < 80% SOC
     Ruta: Solar → BESS (hasta 342 kW, ahora 150 kW disponible)
     Potencia: min(Solar_excess, BESS_charge_capacity)
     = Solar_excess = 2800 - 200(EVs) - 100(mall) = 2500 kW
     = BESS_puede = min(342, 400) = 342 kW
     = Asignado = min(2500, 342 * 0.8) = 274 kW
     Observación enviada: obs[232] = BESS_can_accept / BESS_MAX_POWER

  2️⃣ PRIORIDAD 2: EV Charging
     Condición: Siempre (motos/taxis en cola y sockets libres)
     Ruta: Solar (directo) → EVs, luego BESS→EVs, luego Grid→EVs
     
     Distribución interna:
     - 🏍️ MOTOS (sockets 0-29):
       Capacidad = 30 × 7.4 kW = 222 kW
       Demanda actual = 35 motos × 5.5 kW = 192.5 kW
       obs[242] = capacity_libres = (30-35) / 30 = NEGATIVE!
       
       Pero como hay 35 motos > 30 sockets:
       obs[242] = (30-30) / 30 = 0.0 (SATURATION)
       obs[240] = urgencia = (270-35)/270 = 0.87
       obs[244] = correlacion_solar = 2800 / (200+100) = 14.0 → capped 1.0
       
       Flujo Solar→Motos = 192.5 kW (cubrimiento total)
       Signal: obs[234] = 1.0 (solar suficiente)
     
     - 🛺 MOTOTAXIS (sockets 30-37):
       Capacidad = 8 × 7.4 kW = 59.2 kW
       Demanda actual = 5 taxis × 6.8 kW = 34 kW
       obs[243] = capacity_libres = (8-5) / 8 = 0.375
       
       Flujo Solar→Taxis = 34 kW (cubrimiento total)
       Signal: obs[235] = 1.0 (solar suficiente)
       
       BESS backup: obs[233] = 0.44 (si falta solar)
     
     Total EV = 192.5 + 34 = 226.5 kW (menos que 274 kW asignado a BESS)

  3️⃣ PRIORIDAD 3: MALL Demand
     Condición: Siempre (es demanda continua)
     Demanda = 100 kW constante
     Ruta: Solar (resto) + BESS (si no cargando) → Mall
     
     Solar después de EVs = 2800 - 274 (BESS) - 226.5 (EVs)
                          = 2299.5 kW
     Suficiente para mall, transmite excedente a grid

  4️⃣ PRIORIDAD 4: Grid Curtailed
     Ruta: Solar (excedente) → curtailed
     
     Total disponible = 2800 kW
     Total usado = 274 (BESS) + 226.5 (EVs) + 100 (mall)
                 = 600.5 kW
     Curtailed = 2800 - 600.5 = 2199.5 kW (solar wasted)
     
     Observación enviada: obs[244] = solar_demand_ratio = ALTO

SALIDA: [Grid Import, CO2]
═════════════════════════

  Grid import = max(0, (EVs_demand - Solar_directo - BESS_dispatch))
              = max(0, (226.5 - 226.5 - 0))
              = 0 kW (¡100% solar!)
  
  CO2 emitido = Grid_import * CO2_factor
              = 0 * 0.4521
              = 0 kg CO2 para EVs
  
  Reward CO2 = 0.0 (perfecto, no hay grid)

CONTROL DEL AGENTE (ACCIONES):
═══════════════════════════════

  action[0] = BESS_control ∈ [0, 1]
    Interpretación: "¿Cuánta potencia de BESS quiero descargar?"
    0.0 = Carga BESS desde solar (action ∈ [0, 0.45])
    0.5 = BESS en idle, no carga ni descarga (action ∈ [0.45, 0.55])
    1.0 = Descarga BESS al máximo (action ∈ [0.55, 1.0])
    
    En espacio real:
    Potencia_BESS_dispatch = (action[0] - 0.55) * 342 kW si > 0.55
    
    En nuestro ejemplo: action[0] = 0.60
    → Descarga = (0.60 - 0.55) * 342 = 0.05 * 342 = 17.1 kW a EVs
    
  action[1:31] = POWER_SETPOINTS MOTOS (sockets 0-29)
    Rango: [0, 1] → [0, 7.4 kW]
    
    action[1] = 0.5 = 3.7 kW a socket 0 (moto conectada)
    action[2] = 0.0 = 0 kW a socket 1 (moto inactiva)
    action[6] = 0.95 = 7.0 kW a socket 5 (moto urgente al 10% SOC)
    
  action[31:39] = POWER_SETPOINTS MOTOTAXIS (sockets 30-37)
    Análogo a motos
    
    action[30] = 0.9 = 6.7 kW a socket 30 (mototaxi prioritario)

VALIDACIÓN: ¿Hay suficiente potencia?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Total request = sum(action[1:39]) * CHARGER_MAX_KW
                = (0.5 + 0 + ... + 0.9 + ...) * 7.4 kW
  
  Si total_request > available_power:
    Reducir proporcionalmente: action_final = action * (available / request)
    Esto asegura que no se exceda capacidad

OBSERVACIÓN RETROALIMENTACIÓN:
══════════════════════════════

  Hora siguiente h+1:
  - obs[156:194] actualizados con nuevo SOC de vehículos
  - obs[194:232] actualizados con tiempo restante
  - obs[232,233] actualizado "¿BESS aún disponible?"
  - obs[234,235] actualizado "¿Solar aún disponible?"
  - obs[236,237] actualizado "¿Grid necesario?"
  - obs[238:245] actualizados con nueva prioridad/urgencia/capacidad
```

---

## OBSERVACIÓN 246-dim DETALLADA

### Mapeo Completo

| Índice | Grupo | Variable | Rango | Significado |
|--------|-------|----------|-------|-------------|
| 0 | Energía | Solar normalizado | [0,1] | Potencia solar actual / 4,100 kW |
| 1 | Energía | Mall demand | [0,1] | Demanda mall / 150 kW |
| 2 | Energía | BESS SOC normalizado | [0,1] | Estado de carga batería |
| 3 | Energía | BESS energía disponible | [0,1] | (SOC * 940) / 1700 kWh |
| 4 | Energía | Solar excedente | [0,1] | max(0, solar - demand) / 4100 kW |
| 5 | Energía | Grid import necesario | [0,1] | max(0, demand - solar) / 500 kW |
| 6 | Energía | Balance energético | [0,1] | (solar - demand) / 4100 capped |
| 7 | Energía | Capacidad libre | [0,1] | 1 - (EV_demand / 281 kW) |
| 8-45 | Demanda | Socket demand[0:38] | [0,1] | Demanda por socket i / 10 kW |
| 46-83 | Potencia | Potencia actual[0:38] | [0,1] | Potencia siendo entregada / 10 kW |
| 84-121 | Ocupación | Conectado[0:38] | {0,1} | ¿Vehículo en socket i? |
| 122 | Vehículos | Motos cargando | [0,1] | N_motos_conectadas / 30 |
| 123 | Vehículos | Mototaxis cargando | [0,1] | N_taxis_conectadas / 8 |
| 124 | Vehículos | Motos en cola | [0,1] | min(motos_waiting / 100, 1.0) |
| 125 | Vehículos | Mototaxis en cola | [0,1] | min(taxis_waiting / 20, 1.0) |
| 126 | Vehículos | SOC promedio motos | [0,1] | mean(SOC_motos) / 100 |
| 127 | Vehículos | SOC promedio taxis | [0,1] | mean(SOC_taxis) / 100 |
| 128 | Vehículos | Tiempo restante motos | [0,1] | (1-SOC_motos) * 0.76 / 2.0 |
| 129 | Vehículos | Tiempo restante taxis | [0,1] | (1-SOC_taxis) * 1.2 / 2.0 |
| 130 | Vehículos | Sockets motos libres | [0,1] | (30 - N_motos) / 30 |
| 131 | Vehículos | Sockets taxis libres | [0,1] | (8 - N_taxis) / 8 |
| 132 | Vehículos | Motos cargadas hoy | [0,1] | charged_motos_this_day / 270 |
| 133 | Vehículos | Taxis cargados hoy | [0,1] | charged_taxis_this_day / 39 |
| 134 | Vehículos | Eficiencia carga | [0,1] | (potencia actual / demanda total) capped |
| 135 | Vehículos | Ratio solar→EV | [0,1] | solar_to_ev / max(EV_demand, 1) |
| 136 | Vehículos | CO2 evitado hoy | [0,1] | daily_co2_avoided / 500 kg |
| 137 | Vehículos | CO2 potencial | [0,1] | (sockets_libres * MEAN_KW * CO2factor) / 100 |
| 138 | Tiempo | Hora del día | [0,1] | hour_24 / 24 |
| 139 | Tiempo | Día de semana | [0,1] | day_of_week % 7 / 7 |
| 140 | Tiempo | Mes | [0,1] | (day_of_year // 30) % 12 / 12 |
| 141 | Tiempo | ¿Hora pico? | {0,1} | 1 si 6:00-22:00, 0 si no |
| 142 | Tiempo | Factor CO2 Iquitos | [valor] | 0.4521 kg/kWh (constante) |
| 143 | Tiempo | Tarifa eléctrica | [valor] | ~0.15 USD/kWh (constante) |
| 144-155 | Comunicación v5.3 | (12 features agregadas) | [0,1] | Ver documentación v5.3 |
| **156-193** | **🆕 SOC por socket** | **Socket_SOC[0:38]** | **[0,1]** | **⭐ SOC actual del vehículo en socket i = SOC% / 100** |
| **194-231** | **🆕 Tiempo por socket** | **Socket_time_remaining[0:38]** | **[0,1]** | **⭐ Horas a 100% / 8.0, rango típico 0.5-2h → [0.06, 0.25]** |
| **232** | **🆕 BESS→Motos** | **BESS_supply_motos** | **[0,1]** | **⭐ "Puedo dar X kW a motos" = BESS_available / BESS_MAX_POWER** |
| **233** | **🆕 BESS→Taxis** | **BESS_supply_taxis** | **[0,1]** | **⭐ "Puedo dar X kW a taxis" = BESS_available / BESS_MAX_POWER** |
| **234** | **🆕 Solar→Motos** | **Solar_bypass_motos** | **[0,1]** | **⭐ "Solar directo a motos" = min(solar, motos_demand) / SOLAR_MAX** |
| **235** | **🆕 Solar→Taxis** | **Solar_bypass_taxis** | **[0,1]** | **⭐ "Solar directo a taxis" = min(solar, taxis_demand) / SOLAR_MAX** |
| **236** | **🆕 Grid→Motos** | **Grid_import_motos** | **[0,1]** | **⭐ "Grid debe importar para motos" = penalty signal** |
| **237** | **🆕 Grid→Taxis** | **Grid_import_taxis** | **[0,1]** | **⭐ "Grid debe importar para taxis" = penalty signal** |
| **238** | **🆕 Prioridad motos** | **Priority_motos_sum** | **[0,1]** | **⭐ suma(SOC_priority_weight) / 30, mayor = más vehículos 100%** |
| **239** | **🆕 Prioridad taxis** | **Priority_taxis_sum** | **[0,1]** | **⭐ suma(SOC_priority_weight) / 8** |
| **240** | **🆕 Urgencia motos** | **Urgency_motos_100** | **[0,1]** | **⭐ (270 - charged_100) / 270, 1.0 = nadie cargado 100%, 0.0 = todos 100%** |
| **241** | **🆕 Urgencia taxis** | **Urgency_taxis_100** | **[0,1]** | **⭐ (39 - charged_100) / 39** |
| **242** | **🆕 Capacidad motos** | **Available_capacity_motos** | **[0,1]** | **⭐ libres / 30** |
| **243** | **🆕 Capacidad taxis** | **Available_capacity_taxis** | **[0,1]** | **⭐ libres / 8** |
| **244** | **🆕 Correlación** | **Solar_demand_correlation** | **[0,1]** | **⭐ solar / demand max_capped 2.0, norm a [0,1]** |
| **245** | **🆕 BESS SOC** | **BESS_soc_percent** | **[0,1]** | **⭐ Redundante pero crít | bess_soc_percent / 100** |

### Ejemplo Concreto: Socket 15 (Moto), Hora 14:30

```python
# Moto conectada en socket 15 (moto, porque 15 < 30)
# SOC actual: 42%, Estado: cargando
# Tiempo rest: 3.5 horas hasta 100%

obs[156 + 15] = obs[171] = 0.42  # SOC = 42/100
obs[194 + 15] = obs[209] = 0.4375  # Time = 3.5/8.0

# O si está al 95%
obs[171] = 0.95
obs[209] = 0.0625  # Time = 0.5/8.0 (casi listo)

# Si está al 10%
obs[171] = 0.10
obs[209] = 1.0  # Time = 8.0 máximo (mucho por cargar, cap a 8h)
```

---

## RECOMPENSA MULTIOBJETIVO v6.0

### Componentes de Recompensa

#### **1. CO2 Reduction (45%)**
```python
r_co2 = -grid_import_kwh * CO2_FACTOR_IQUITOS * 0.001
       = -100 kWh * 0.4521 kg/kWh * 0.001
       = -0.04521 kg (negativo = penalidad)

# Mecanismo: Minimizar importaciones del grid
# Señal: grid_import disminuye cuando:
#   - Solar suficiente
#   - BESS bien cargado
#   - EVs reciben energía limpia

Peso: w_co2 = 0.45  # Principal objetivo
```

#### **2. Solar Utilization (15%)**
```python
r_solar = solar_used_to_ev / max(solar_generation, 1.0)
        = 150 kWh / 2800 kWh
        = 0.0536 (bueno si > 0.65)

# Mecanismo: Maximizar % de solar que llega a EVs
# No penaliza solar curtailed (es unavoidable al mediodía)
# Premia distribuir solar entre BESS + EVs + Mall equitativamente

Peso: w_solar = 0.15
```

#### **3. VEHICLES CHARGED (25%) ⭐ NUEVO v6.0**
```python
# Contar vehículos completamente cargados (SOC >= 99.9%)
completed_this_hour = count(socket.soc >= 99.9 for socket in active_sockets)

r_vehicles = completed_this_hour / NUM_CHARGERS
           = 5 vehículos / 38 sockets
           = 0.1316

# Mecanismo: Recompensar al agente por COMPLETAR cargas
# NO es lo mismo que "cargando": es 100% SOC
# Cada vehículo completado = progreso medible hacia meta diaria

Peso: w_vehicles = 0.25  ⭐ CRÍTICO PARA INCENTIVIZAR CASCADA

# Impacto:
#   - Sin este peso: Agente podría mantener muchos a 50% (bajo costo)
#   - Con este peso: Agente COMPLETA cargas, saca espacio, carga más
#   - Resultado: 309 vehículos/día (270 motos + 39 taxis) en lugar de 150
```

#### **4. Grid Stability (5%)**
```python
r_stability = 1.0 - min(1.0, grid_import_kw / 500.0)
            = 1.0 - min(1.0, 50 / 500)
            = 1.0 - 0.1
            = 0.9 (bueno)

# Mecanismo: Penalizar picos de grid import
# Smooth ramp, no saltos abruptos

Peso: w_stability = 0.05
```

#### **5. BESS Efficiency (5%)**
```python
# Minimizar ciclos de carga/descarga innecesarios
# BESS wear ~ número de cycles
cycles = (charge_kwh + discharge_kwh) / (2 * BESS_CAPACITY)
       = (200 + 150) / (2 * 940)
       = 0.186 cycles/hour

r_bess = 1.0 - min(1.0, cycles / 0.5)  # Penaliza > 0.5 cycles/hour
       = 1.0 - 0.372
       = 0.628

Peso: w_bess = 0.05
```

### Ecuación Final de Recompensa v6.0

```
R(t) = w_co2 * r_co2 
     + w_solar * r_solar 
     + w_vehicles * r_vehicles 
     + w_stability * r_stability 
     + w_bess * r_bess
     
     = 0.45 * (-0.045)
     + 0.15 * 0.054
     + 0.25 * 0.132
     + 0.05 * 0.9
     + 0.05 * 0.628
     
     = -0.02025 - 0.0081 + 0.033 + 0.045 + 0.0314
     = +0.0474 (recompensa positiva en hora típica)

# Por episodio (8,760 horas):
# Esperado: 0.0474 × 8,760 = +415 puntos/episodio
# Con mejora en vehicles_charged: +600 a +800 puntos/episodio
```

### Mapeo Directo a Objetivos Físicos

```
Reward → Acción del agente → Resultado físico
─────────────────────────────────────────────

r_co2 ↑       Minimizar grid_import      Solar → BESS → EVs (cascada)
              = Opción 1: Cargar BESS    o BESS → EVs directo

r_solar ↑     Maximizar solar a EVs      Mantener BESS descargado
              Minimizar curtailment      durante mediodía

r_vehicles ↑  Completar cargas al 100%   Priorizar sockets
              Sacar conectados           cercanos a 100%
              Conectar nuevos            Dejar espacio para más

r_stability ↑ Rampas suaves              No saltos de power
              Evitar picos               Control gradual

r_bess ↑      Usar BESS de forma         Carga cuando solar alto
              estratégica                Descarga en contingencias
              Minimizar ciclos           No cargar/descargar seguido

COMBINACIÓN: Agente aprende a:
─────────────────────────────

1. Cargar BESS desde solar al mediodía (r_co2 ↑, r_stability ↑)
2. Descargar BESS al atardecer (r_solar ↑, r_vehicles ↑)
3. Completar vehículos 100% (r_vehicles ↑, abre espacio)
4. Conectar nuevos vehículos (r_vehicles ↑ sostenido)
5. Mantener grid import mínimo (r_co2 ↑)
6. Resultado: 309 vehículos/día, CO2 -30%, BESS >80% utilizado
```

---

## ACCIONES

### Action Space 39-dim

```
[0]       ← BESS Control
[1:39]    ← Socket Power Setpoints (38 sockets)

Rango: action ∈ [0, 1] (normalizado)

BESS CONTROL (acción[0]):
━━━━━━━━━━━━━━━━━━━━━━━━━

action[0] ∈ [0.0, 1.0]

Interpretación:
  0.0-0.45  = BESS CHARGING from solar
             Power = (0.45 - action[0]) * 342 kW
             Si action[0]=0.0 → charge_power = 0.45 * 342 = 153.9 kW
             Si action[0]=0.45 → charge_power = 0 kW (idle)
  
  0.45-0.55 = BESS IDLE
             No charge, no discharge
             BESS maintains SOC
  
  0.55-1.0  = BESS DISCHARGING to EVs/Mall
             Power = (action[0] - 0.55) * 342 kW
             Si action[0]=0.55 → discharge_power = 0 kW (idle)
             Si action[0]=1.0 → discharge_power = 0.45 * 342 = 153.9 kW

Semadentico behavior:
             0.3   → Charge 109 kW (cargar fuerte desde solar)
             0.45  → Charge 0 kW (idle)
             0.55  → Discharge 0 kW (idle, otro)
             0.7   → Discharge 51 kW (descargar moderado)
             1.0   → Discharge 153.9 kW (descargar máximo)

Validación:
  - No permitir simultáneamente: NO se puede cargar y descargar
  - Respetar max_power: BESS max discharge = 342 kW
  - Respetar SOC%: Si SOC < 20%, no descargar; Si SOC > 100%, no cargar


SOCKET POWER SETPOINTS (acciones[1:39]):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

action[i] ∈ [0.0, 1.0] para cada socket i ∈ [0, 37]

Interpretación:
  Setpoint_power_kW = action[i] * CHARGER_MAX_KW
                    = action[i] * 7.4 kW

  action[i] = 0.0  → 0.0 kW (socket inactivo)
  action[i] = 0.5  → 3.7 kW (medio)
  action[i] = 0.9  → 6.66 kW (casi máximo)
  action[i] = 1.0  → 7.4 kW (máximo)

Mapeo a Sockets:
  Socket 0-29:  MOTOS (30 sockets, 15 chargers × 2 sockets)
                action[1:31] (30 valores)
  
  Socket 30-37: MOTOTAXIS (8 sockets, 4 chargers × 2 sockets)
                action[31:39] (8 valores)

Ejemplo:
  action = [0.3, 0.5, 0.8, 0.0, ..., 0.95, 0.0]
           │    │    │    │        │     │
           │    │    │    │        │     Socket 37 (mototaxi): OFF
           │    │    │    │        Socket 30 (mototaxi): Max
           │    │    │    Socket 3 (moto): OFF
           │    │    Socket 2 (moto): 5.92 kW
           │    Socket 1 (moto): 3.7 kW
           BESS: Charge 109 kW


VALIDACIÓN DE ACCIONES (Constraint enforcement):
═══════════════════════════════════════════════

1. Total power requested = sum(action[1:39]) * 7.4 kW
   
   Si total_power_requested > available_power:
     Scale all actions down:
     action_final = action * (available / requested)
   
   Ejemplo:
     total_request = (0.5 + 0.8 + ... + 0.9) * 7.4 = 150 kW
     available = solar (100 kW) + BESS_discharge (50 kW) = 150 kW
     ratio = 150 / 150 = 1.0 (no scaling)
     
     Pero si:
     available = 75 kW, total_request = 150 kW
     ratio = 75 / 150 = 0.5
     action_final[i] = action[i] * 0.5  (todos los sockets)
     
     → Socket 1 recibe 0.5*0.5 * 7.4 = 1.85 kW (en lugar de 3.7)
     → Socket 2 recibe 0.5*0.8 * 7.4 = 2.96 kW (en lugar de 5.92)

2. BESS power limits:
   - Max discharge: 342 kW (constante de hardware)
   - Max charge: 342 kW (constante de hardware)
   - Si action[0] viola límites, clamp a rango válido

3. Vehicle state:
   - Si socket NO tiene vehículo conectado: acción ignorada (0 kW entregado)
   - Si vehículo ya está al 100% SOC: desconectar, acción ignorada
   - Fuerza: El agente aprende que asignar potencia a socket sin vehículo = DESPERDICIO DE REWARD

4. Hour-specific constraints:
   - De 0:00-6:00: Solar baja, BESS podría ser única fuente
   - De 6:00-22:00: Solar disponible, priorizar
   - De 22:00-0:00: Solar cero, usar BESS/Grid
```

---

## INTEGRACIÓN CON DATOS REALES OE2

### Mapeo de Archivos CSV → Environment v6.0

```
data/oe2/
├─ Generacionsolar/pv_generation_citylearn2024.csv
│  └─ [8,760 × 2]: hora | potencia_kw
│     Usado: solar_kw = df['potencia_kw'].values → obs[0], obs[234-235]
│
├─ chargers/chargers_ev_ano_2024_v3.csv
│  └─ [8,760 × 38+]: hora | socket_0_charger_power_kw | ... | socket_37_charger_power_kw
│     Usado: chargers_kw = df[['socket_0',...,'socket_37']].values
│             Per socket: obs[8:46] (demanda), obs[156:194] (SOC después carga)
│
├─ bess/bess_ano_2024.csv
│  └─ [8,760 × 25+]: hora | soc_percent | bess_charge | bess_discharge | pv_to_bess | pv_to_ev | pv_to_mall | pv_curtailed | ...
│     Usado: 
│       - bess_soc = df['soc_percent'].values → obs[2], obs[232-233], obs[245]
│       - Cascade verification: pv_to_bess + pv_to_ev + pv_to_mall + pv_curtailed == pv_generation ✓
│
└─ demandamallkwh/demandamallhorakwh.csv
   └─ [8,760 × 2]: hora | demanda_kwh
      Usado: mall_kw = df['demanda_kwh'].values → obs[1], obs[236-237]

CONSTRUCCIÓN DE OBSERVACIÓN:
════════════════════════════

Loop h = 0 to 8759:
  
  # [0-7] Energía sistema básica
  solar_h = solar_kw[h]
  mall_h = mall_kw[h]
  bess_soc_h = bess_soc[h] / 100.0
  obs[0] = min(solar_h / SOLAR_MAX_KW, 1.0)
  obs[1] = min(mall_h / MALL_MAX_KW, 1.0)
  obs[2] = min(bess_soc_h, 1.0)
  
  # [8-45] Demanda por socket
  for i in range(38):
    socket_demand = chargers_kw[h, i]
    obs[8 + i] = min(socket_demand / CHARGER_MAX_KW, 1.0)
  
  # [156-193] SOC por socket (simulado internamente o desde chargers_data)
  for i in range(38):
    if socket_states[i] is not None and socket_states[i].is_connected:
      soc = socket_states[i].current_soc / 100.0
      obs[156 + i] = min(soc, 1.0)
    else:
      obs[156 + i] = 0.0
  
  # [232-233] BESS dispatch signals (de bess_ano_2024.csv)
  bess_available = bess_soc_h * BESS_CAPACITY / BESS_MAX_POWER
  obs[232] = min(bess_available, 1.0)  # A motos
  obs[233] = min(bess_available, 1.0)  # A taxis
  
  # [234-235] Solar bypass signals
  obs[234] = min(solar_h / SOLAR_MAX_KW, 1.0)  # A motos
  obs[235] = min(solar_h / SOLAR_MAX_KW, 1.0)  # A taxis


VALIDACIÓN: Cascada OE2 sin editar
═══════════════════════════════════

El archivo bess_ano_2024.csv YA CONTIENE las columnas:
  - pv_to_bess_kwh: Solar → BESS
  - pv_to_ev_kwh: Solar → EVs
  - pv_to_mall_kwh: Solar → Mall
  - pv_curtailed_kwh: Solar curtailed

Verificamos:
  sum(pv_to_bess + pv_to_ev + pv_to_mall + pv_curtailed) == sum(pv_generation) ✓

El agente APRENDE ESTA CASCADA de:
  1. Datos históricos (BESS ya la contiene)
  2. Observación: Cada componente ve su flujo
  3. Recompensa: Al optimization

NO NECESITAMOS EDITAR los archivos CSV.
Solo los CARGAMOS Y USAMOS.
```

---

## ROADMAP DE IMPLEMENTACIÓN

### Fase 1: Migración v5.3 → v6.0 (1-2 semanas)

```
Tarea 1: Código base completo
━━━━━━━━━━━━━━━━━━━━━━━━━

1.1 Extender RealOE2Environment a 246-dim
    - [156-193] Socket SOC tracking
    - [194-231] Socket time remaining
    - [232-245] Comunicación sistemas
    - Tests: obs.shape == (246,), ranges [0,1]

1.2 Implementar VehicleSOCTracker completo
    - spawn_vehicle() con SOC inicial realista
    - update_soc() cada hora según potencia asignada
    - get_metrics() con estado 100% por socket
    - Tests: Vehículos alcanzan 100% SOC respecto a potencia suministrada

1.3 Recompensa v6.0
    - Implementar r_vehicles_charged
    - Balancear pesos: (45%, 15%, 25%, 5%, 5%)
    - Tests: Reward > 0 cuando hay vehículos cargados

Tarea 2: Integración datos reales OE2
━━━━━━━━━━━━━━━━━━━━━━

2.1 Cargar datos reales
    - solar_kw [8,760] from pv_generation_citylearn2024.csv
    - chargers_kw [8,760 × 38] from chargers_ev_ano_2024_v3.csv
    - mall_kw [8,760] from demandamallhorakwh.csv
    - bess_soc [8,760] from bess_ano_2024.csv
    - Tests: shapes correctas, ranges razonables

2.2 Validación cascada
    - Verificar: pv_to_bess + pv_to_ev + pv_to_mall + pv_curtailed = total ✓
    - Semanal/diario: report de energy flows
    - Tests: Diferencia < 1 MWh/año

Tarea 3: Entrenamiento SAC v6.0
━━━━━━━━━━━━━━━━━━━━━━

3.1 Configurar SAC
    - Buffer size: 1M (GPU)
    - Learning rate: 1e-4
    - Batch: 256
    - Warmup: 10K steps
    - Total: 131,400 steps (15 episodios)

3.2 Training loop
    - Episode 0-3: Debugging, obseve policy
    - Episode 4-8: Optimization, improve metrics
    - Episode 9-15: Convergence, stabilize reward
    - Tests: Reward trend increasing

3.3 Monitoring
    - Log: episode_reward, vehicles_charged, co2_avoided, grid_import
    - Checkpoint: Save every 1000 steps
    - Visualize: Reward curve, vehicle metrics, energy flows

### Fase 2: Validación y Fine-tuning (1 semana)

```
Tarea 4: Validación de resultados
━━━━━━━━━━━━━━━━━━━━━━━

4.1 Métricas de agente SAC v6.0
    - Vehículos charged/day: 250-309 (vs 150 en v5.3)
    - CO2 avoided: > 7,500 kg/año (vs 7,200 en v5.3)
    - Solar utilization: > 65%
    - BESS cycles: < 0.5 cycles/hour

4.2 Comparativas
    - SAC v6.0 vs SAC v5.3: +15% vehículos, -2% CO2 (equilibrio)
    - SAC v6.0 vs PPO: Convergence speed 2x rápido
    - SAC v6.0 vs baseline (no control): +60% vehículos, +40% CO2 reducido

4.3 Stress tests
    - Low solar period (invierno): ¿Qué sucede?
    - High demand period (midday): ¿Saturación?
    - BESS empty (SOC < 20%): ¿Recovery?

Tarea 5: Fine-tuning de pesos
━━━━━━━━━━━━━━━━━━━

5.1 Si vehículos cargados < 150/día:
    Aumentar w_vehicles: 0.25 → 0.35
    Tests: Reentrenar episodios 10-15

5.2 Si CO2 aumenta mucho (> 10k kg/año):
    Aumentar w_co2: 0.45 → 0.55
    Disminuir w_vehicles: 0.35 → 0.25

5.3 Si BESS inactivo (SOC constante):
    Aumentar prioritización BESS en reward

### Fase 3: Deploy y operación (ongoing)

```
Tarea 6: Production deployment
━━━━━━━━━━━━━━━━━━━━━

6.1 Guardar modelo final
    - best_model = SAC.load('checkpoints/SAC/best.zip')
    - Policy: π(action | obs_246)
    - Deterministic inference (no exploration)

6.2 Online inference
    - Real-time: obs_246 cada hora
    - Acción: action_39 para BESS + 38 sockets
    - Latency < 100ms

6.3 Monitoring operacional
    - Daily report: Vehículos cargados, CO2 evitado, grid import
    - Weekly report: Trend, anomalías, comparativas
    - Monthly: Deep analysis, posibles mejoras

Tarea 7: Mejoras futuras (post v6.0)
━━━━━━━━━━━━━━━━━━━━

7.1 Predicción de demanda
    - Forecast vehicle arrivals (260 vehículos/día stochastic)
    - Forecast solar (PVGIS forecast)
    - Forecast mall (consumption patterns)

7.2 Priorización dinámica
    - Service level agreements (taxis deadline < motos)
    - Peak pricing (alta tarifa después 22:00)
    - Emergencies (cargador fallido)

7.3 Cooperación multi-agent
    - Each charger is sub-agent
    - BESS is coordinator
    - Communication protocol v7.0
```

---

## CHECKLIST DE VERIFICACIÓN

- [ ] Observación 246-dim implementada: obs.shape == (246,)
- [ ] Acciones 39-dim implementadas: action.shape == (39,)
- [ ] SOC por socket [156-193] tracking correcto
- [ ] Tiempo por socket [194-231] estimación correcta
- [ ] BESS signals [232-233] reflejan disponibilidad real
- [ ] Solar signals [234-235] reflejan potencia real
- [ ] Comunicación inter-sistema [236-245] lógica consistente
- [ ] Recompensa v6.0 con w_vehicles = 0.25 implementada
- [ ] VehicleSOCTracker con priorización SOC funcionando
- [ ] Datos reales OE2 cargados correctamente
- [ ] Cascada solar validada: suma = total ✓
- [ ] SAC training loop ejecutando sin errores
- [ ] Checkpoints guardándose cada 1000 steps
- [ ] Métricas registradas: reward, vehicles_charged, co2, grid
- [ ] Visualización de curvas entrenamiento disponible
- [ ] Comparativa v5.3 vs v6.0 documentada
- [ ] Production deployment listo

---

## REFERENCIAS

- **Documento relacionado**: [train_sac_sistema_comunicacion_v6.py](../scripts/train/train_sac_sistema_comunicacion_v6.py)
- **Datos OE2**: data/oe2/ (Solar, Chargers, BESS, Mall)
- **Especificación SAC**: scripts/train/train_sac_multiobjetivo.py (v5.3 actual)
- **Recompensas**: src/citylearnv2/dataset_builder/rewards.py

**Autor**: GitHub Copilot  
**Última actualización**: 2026-02-14  
**Versión**: 6.0 ✅
