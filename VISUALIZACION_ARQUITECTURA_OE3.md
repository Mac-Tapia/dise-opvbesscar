# 🎯 VISUALIZACIÓN ARQUITECTURA OE3 - Estructura Correcta

## 1️⃣ Vista Física (Hardware Real)

```
┌─────────────────────────────────────────────────────────────┐
│                     SISTEMA OE3 FÍSICO                      │
└─────────────────────────────────────────────────────────────┘

          Charger 1      Charger 2     ...    Charger 32
          (2.0 kW)       (2.0 kW)             (3.0 kW)
              │              │                    │
        ┌─────┴─────┐   ┌─────┴─────┐       ┌─────┴─────┐
        │ S1 S2 S3 S4│   │ S5 S6 S7 S8│ ... │S125 S126 S127 S128│
        └─────┬─────┘   └─────┬─────┘       └─────┬─────┘
              │              │                    │
              ├──────────────┼────────────────────┤
              │
        "Playa de Motos"        "Playa de Mototaxis"
        (28 Chargers)           (4 Chargers)
        (112 Sockets)           (16 Sockets)

TOTAL: 32 CHARGERS × 4 SOCKETS/CHARGER = 128 SOCKETS

Key: S = Socket/Toma
```

## 2️⃣ Vista Lógica (CityLearn)

```
┌──────────────────────────────────────────────────────────────┐
│         CityLearn Building: "Mall_Iquitos" (UN EDIFICIO)    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  [Solar 4,162 kWp] [BESS 4,520 kWh] [Mall 100 kW]          │
│           │                │               │                  │
│           └────────────────┼───────────────┘                  │
│                            │                                   │
│                    ┌───────▼────────┐                          │
│                    │  Chargers: 128 │                          │
│                    │   Sockets      │                          │
│                    └───────┬────────┘                          │
│                            │                                   │
│         ┌──────────┬───────┼───────┬──────────┐               │
│         │          │       │       │          │               │
│     Socket1    Socket2 Socket3...Socket128                    │
│     (Moto)     (Moto) (Moto)    (MotoTaxi)                   │
│         │          │       │       │          │               │
│         └──────────┴───────┴───────┴──────────┘               │
│                            │                                   │
│                    [RL Control: 129 actions]                  │
│                     (1 BESS + 128 Sockets)                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## 3️⃣ Matriz de Control RL

```
┌───────────────────────────────────────────────────┐
│  Action Vector (129-dimensional)                  │
├───────────────────────────────────────────────────┤
│  Action[0]:   BESS Discharge Setpoint   ∈ [0, 1] │
│  Action[1]:   Socket 001 Power         ∈ [0, 1] │
│  Action[2]:   Socket 002 Power         ∈ [0, 1] │
│  ...                                              │
│  Action[128]: Socket 128 Power         ∈ [0, 1] │
└───────────────────────────────────────────────────┘

TOTAL: 1 + 128 = 129 ACCIONES POR TIMESTEP
```

## 4️⃣ Mapa de Sockets → Chargers Físicos

```
Chargers 1-28 (MOTOS)
├─ Charger 01 → Sockets 001-004  (Playa Motos)
├─ Charger 02 → Sockets 005-008  (Playa Motos)
├─ Charger 03 → Sockets 009-012  (Playa Motos)
├─ Charger 04 → Sockets 013-016  (Playa Motos)
├─ Charger 05 → Sockets 017-020  (Playa Motos)
├─ Charger 06 → Sockets 021-024  (Playa Motos)
├─ Charger 07 → Sockets 025-028  (Playa Motos)
├─ Charger 08 → Sockets 029-032  (Playa Motos)
├─ Charger 09 → Sockets 033-036  (Playa Motos)
├─ Charger 10 → Sockets 037-040  (Playa Motos)
├─ Charger 11 → Sockets 041-044  (Playa Motos)
├─ Charger 12 → Sockets 045-048  (Playa Motos)
├─ Charger 13 → Sockets 049-052  (Playa Motos)
├─ Charger 14 → Sockets 053-056  (Playa Motos)
├─ Charger 15 → Sockets 057-060  (Playa Motos)
├─ Charger 16 → Sockets 061-064  (Playa Motos)
├─ Charger 17 → Sockets 065-068  (Playa Motos)
├─ Charger 18 → Sockets 069-072  (Playa Motos)
├─ Charger 19 → Sockets 073-076  (Playa Motos)
├─ Charger 20 → Sockets 077-080  (Playa Motos)
├─ Charger 21 → Sockets 081-084  (Playa Motos)
├─ Charger 22 → Sockets 085-088  (Playa Motos)
├─ Charger 23 → Sockets 089-092  (Playa Motos)
├─ Charger 24 → Sockets 093-096  (Playa Motos)
├─ Charger 25 → Sockets 097-100  (Playa Motos)
├─ Charger 26 → Sockets 101-104  (Playa Motos)
├─ Charger 27 → Sockets 105-108  (Playa Motos)
└─ Charger 28 → Sockets 109-112  (Playa Motos)

Chargers 29-32 (MOTOTAXIS)
├─ Charger 29 → Sockets 113-116  (Playa MotoTaxis)
├─ Charger 30 → Sockets 117-120  (Playa MotoTaxis)
├─ Charger 31 → Sockets 121-124  (Playa MotoTaxis)
└─ Charger 32 → Sockets 125-128  (Playa MotoTaxis)

RESUMEN:
- Motos (Chargers 1-28):     112 sockets → Action[1-112]
- MotoTaxis (Chargers 29-32):  16 sockets → Action[113-128]
```

## 5️⃣ Archivos Generados por Socket

```
data/processed/citylearn/iquitos_ev_mall/

charger_simulation_001.csv  ← Datos Socket 001 (Charger 1, Socket 1) - Moto
charger_simulation_002.csv  ← Datos Socket 002 (Charger 1, Socket 2) - Moto
charger_simulation_003.csv  ← Datos Socket 003 (Charger 1, Socket 3) - Moto
charger_simulation_004.csv  ← Datos Socket 004 (Charger 1, Socket 4) - Moto

charger_simulation_005.csv  ← Datos Socket 005 (Charger 2, Socket 1) - Moto
charger_simulation_006.csv  ← Datos Socket 006 (Charger 2, Socket 2) - Moto
...
charger_simulation_112.csv  ← Datos Socket 112 (Charger 28, Socket 4) - Moto

charger_simulation_113.csv  ← Datos Socket 113 (Charger 29, Socket 1) - MotoTaxi
charger_simulation_114.csv  ← Datos Socket 114 (Charger 29, Socket 2) - MotoTaxi
...
charger_simulation_128.csv  ← Datos Socket 128 (Charger 32, Socket 4) - MotoTaxi

CADA ARCHIVO:
- 8,760 filas (1 hora × 365 días)
- Columnas: occupancy, EV_id, SOC, charging_power, etc.
- Perfil dinámico único por socket
```

## 6️⃣ Flujo de Datos OE2 → CityLearn

```
OE2 (Fuente)
  │
  └─ data/interim/oe2/chargers/
     ├─ individual_chargers.json         [32 chargers definitions]
     │  └─ CHARGER_001: {type: moto, power: 2.0kW}
     │  └─ CHARGER_002: {type: moto, power: 2.0kW}
     │  ...
     │  └─ CHARGER_032: {type: mototaxi, power: 3.0kW}
     │
     └─ chargers_hourly_profiles_annual.csv  [32 columnas × 8,760 filas]
        └─ Columna 1: Demanda horaria Charger 1 (agregada 4 sockets)
        └─ Columna 2: Demanda horaria Charger 2 (agregada 4 sockets)
        ...
        └─ Columna 32: Demanda horaria Charger 32 (agregada 4 sockets)

        [dataset_builder.py EXPANDE]
             │
             └─→ [Divide cada charger en 4 sockets]
                 [Crea 128 archivos individuales]

CityLearn (Destino)
  │
  └─ data/processed/citylearn/iquitos_ev_mall/
     ├─ schema.json [128 charger entries]
     │
     └─ charger_simulation_001.csv  [8,760 filas - Socket 1]
        charger_simulation_002.csv  [8,760 filas - Socket 2]
        ...
        charger_simulation_128.csv  [8,760 filas - Socket 128]
```

## 7️⃣ Variables por Socket (En charger_simulation_NNN.csv)

```
Fila 1 (Hora 00:00-01:00):
┌─────────────────────────────────────────────────┐
│ electric_vehicle_charger_state: 3 (Available)   │
│ electric_vehicle_id: ""                         │
│ electric_vehicle_departure_time: 0.0            │
│ electric_vehicle_required_soc_departure: 0.0    │
│ electric_vehicle_estimated_arrival_time: 2.0   │
│ electric_vehicle_estimated_soc_arrival: 0.0    │
└─────────────────────────────────────────────────┘

Fila 200 (Hora 19:00-20:00 - Pico):
┌─────────────────────────────────────────────────┐
│ electric_vehicle_charger_state: 1 (Charging)    │
│ electric_vehicle_id: "MOTO_001"                 │
│ electric_vehicle_departure_time: 2.5 (horas)   │
│ electric_vehicle_required_soc_departure: 0.90   │
│ electric_vehicle_estimated_arrival_time: 0.0   │
│ electric_vehicle_estimated_soc_arrival: 0.25   │
└─────────────────────────────────────────────────┘
```

## 8️⃣ Control RL en Simulación

```
TIMESTEP t (hora X):

Observation (394-dim):
  ├─ Solar generation (kW)
  ├─ Grid metrics
  ├─ BESS SOC (%)
  ├─ 128 Chargers: [occupancy, soc, power_request, ...]
  └─ Time features (hour, month, day_of_week)

        [Agent.predict(obs) via SAC/PPO/A2C]
             │
             ▼

Action (129-dim):
  ├─ action[0]:   BESS discharge rate [0.0 - 1.0]
  ├─ action[1]:   Socket 001 power setpoint [0.0 - 1.0]
  ├─ action[2]:   Socket 002 power setpoint [0.0 - 1.0]
  ...
  └─ action[128]: Socket 128 power setpoint [0.0 - 1.0]

        [Environment.step(action)]
             │
             ▼

Reward (Multi-objective):
  ├─ CO₂ minimization (0.50 weight)
  ├─ Solar utilization (0.20 weight)
  ├─ Cost minimization (0.15 weight)
  ├─ EV satisfaction (0.10 weight)
  └─ Grid stability (0.05 weight)
```

---

## ✅ PUNTOS CLAVE A RECORDAR

1. **32 ≠ 128**
   - 32 = Cargadores físicos (devices en el parking)
   - 128 = Tomas de carga (sockets, puntos de control)

2. **Un edificio CityLearn**
   - Unificación lógica de ambas playas
   - Simplifica schema pero mantiene 128 controles individuales

3. **Control individual de CADA toma**
   - Cada socket tiene su propia acción RL
   - Cada socket tiene su perfil dinámico único
   - 129 acciones totales (BESS + 128 sockets)

4. **Datos reales OE2**
   - Probados y confirmados (ver diagnóstico)
   - Solar: 8,030,119 kWh/año ✓
   - Mall: 12,322,765 kWh/año ✓
   - Chargers: 128 perfiles dinámicos ✓

---

**Status**: ✅ Visualización Completa
**Última Actualización**: 2026-02-04
**Claridad**: MÁXIMA - Sin ambigüedad

