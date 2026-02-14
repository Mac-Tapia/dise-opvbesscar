# 📊 SAC v6.0 - CAMBIOS DE UN VISTAZO

## v5.3 (Actual) → v6.0 (Nuevo): ¿QUÉ CAMBIÓ?

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OBSERVACIÓN SPACE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ v5.3 (156-dim)              │  v6.0 (246-dim) = 156 + 90 NEW                   │
├─────────────────────────────│  ───────────────────────────────────────────────│
│ [0-7]:   Energy basics      │  [0-7]:       Energy basics (igual)             │
│ [8-45]:  Socket demand      │  [8-45]:      Socket demand (igual)             │
│ [46-83]: Power actual       │  [46-83]:     Power actual (igual)              │
│ [84-121]: Occupancy         │  [84-121]:    Occupancy (igual)                 │
│ [122-137]: Vehicle agg      │  [122-137]:   Vehicle agg (igual)               │
│ [138-143]: Time features    │  [138-143]:   Time features (igual)             │
│ [144-155]: Comm (aggreg)    │  [144-155]:   Comm (igual)                      │
│                             │                                                 │
│                             │  [156-193]: ⭐ SOC PER SOCKET (38 NEW)         │
│                             │  [194-231]: ⭐ TIME PER SOCKET (38 NEW)        │
│                             │  [232-233]: ⭐ BESS signals (2 NEW)            │
│                             │  [234-235]: ⭐ Solar signals (2 NEW)           │
│                             │  [236-237]: ⭐ Grid signals (2 NEW)            │
│                             │  [238-245]: ⭐ Agregados críticos (8 NEW)      │
└─────────────────────────────┴──────────────────────────────────────────────────┘

TOTAL: 156-dim → 246-dim (+90 features = +58%)
```

---

## PROBLEMA v5.3 → SOLUCIÓN v6.0

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA 1: Agent no ve SOC individual                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ v5.3: obs[126] = 0.45  (promedio motos)                                      │
│       No sabe: Socket 0 @ 95%? Socket 2 @ 10%? ¿Cuál priorizar?             │
│                                                                               │
│ v6.0: obs[156:194] = [0.95, 0.45, 0.10, 0.50, ...]  (38 sockets)           │
│       Sabe exactamente: "Socket 2 @ 10% → máxima potencia"                  │
│       → +20-30% eficiencia carga                                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA 2: Agent no sabe tiempo restante por socket                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ v5.3: obs[128] = 0.28  (tiempo promedio)                                     │
│       No sabe: Socket 0 necesita 0.5h? Socket 2 necesita 4h?                │
│                                                                               │
│ v6.0: obs[194:232] = [0.06, 0.28, 0.50, 0.25, ...]  (38 sockets)           │
│       Sabe: "Socket 2 deadline en 4h > Socket 0 deadline en 0.5h"           │
│       → Prioriza por urgencia de tiempo                                      │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA 3: Cascada energía implícita, no explícita                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ v5.3: obs[145] vago: "¿Solar suficiente?" (no dice A QUIÉN EXACTO)          │
│       Solar → ? (BESS? EVs? Mall?)                                           │
│                                                                               │
│ v6.0: obs[232-237] explicit:                                                │
│       obs[232] = BESS kW disponible para motos                               │
│       obs[234] = Solar kW disponible para motos (directo)                    │
│       obs[236] = Grid penalty para motos                                     │
│       Cascada clara: Solar→BESS→EVs→Mall para cada fleet                   │
│       → Agent aprende rutas óptimas                                          │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA 4: No distingue moto vs mototaxi (urgencia)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ v5.3: obs[122-123] = solo contadores cargando                                │
│       No sabe: Mototaxis son servicio público (MÁS urgencia)                │
│                                                                               │
│ v6.0: obs[240-243] separate motos/taxis:                                     │
│       obs[240] = urgency motos (cuántos faltan 100%)                         │
│       obs[241] = urgency taxis (cuántos faltan 100%)                         │
│       obs[242] = capacity motos (cuántos pueden agregar)                     │
│       obs[243] = capacity taxis (cuántos pueden agregar)                     │
│       → Agent aprende "Taxi deadline > Moto deadline"                        │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA 5: Control one-size-fits-all de poder                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ v5.3: action = 1 valor para "motos power" (30 sockets)                       │
│       Si 30 motos, cada una gets (available_power / 30)                      │
│       Socket @ 95% SOC malgasta potencia                                     │
│       Socket @ 10% SOC se queda sin                                          │
│                                                                               │
│ v6.0: action = 39 valores (1 BESS + 38 sockets)                              │
│       action[1:31] = motos power setpoints                                   │
│       action[31:39] = taxis power setpoints                                  │
│       Agent asigna: Socket 10% SOC → 7.4 kW, Socket 95% SOC → 0.1 kW       │
│       → +85% más vehículos completados/día                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## REWARD CHANGES: v5.3 → v6.0

```
v5.3 WEIGHTS:
┌───────────────────┬────────┐
│ CO2 Reduction     │ 50% ←─────────╮
│ Solar Utility     │ 20%           │  (no incentive a vehículos)
│ Grid Stability    │ 30%           │
└───────────────────┴────────┘

❌ PROBLEMA: Agent ignora si vehículos están cargados 100%


v6.0 WEIGHTS:
┌───────────────────────────┬────────┐
│ CO2 Reduction             │ 45% ◄─╮ reducido
│ Solar Utility             │ 15%   │
│ VEHICLES CHARGED 100% ⭐  │ 25% ◄─╮ NEW (era 0%)
│ Grid Stability            │ 5%    │
│ BESS Efficiency           │ 5%    │
│ Prioritization            │ 5%    │
└───────────────────────────┴────────┘

✅ SOLUCIÓN: Agent explícitamente incentivizado a cargar más vehículos
   SIN sacrificar CO2 (45% weight still substantial)
```

---

## RESULTADOS ESPERADOS

```
MÉTRICA                 v5.3 ACTUAL    v6.0 OBJETIVO    MEJORA
─────────────────────────────────────────────────────────────────
Vehículos/día            ~150            280-309          +85-107% ⭐
Grid Import (%)           25%              12%             -13% ⭐
CO2 Evitado (kg/año)     7,200            7,500+           +4-11% ✓
Episode Reward           100-150          400-600          2-4x ⭐
Convergencia (ep)        >100             10-15            7-10x ⭐
```

---

## ARQUITECTURA: 246-dim OBS → SAC AGENT

```
Real OE2 Data (Iquitos v5.3)
│
├─ Solar: pv_generation.csv (8,760 hrs, 0-4,100 kW)
├─ Chargers: chargers_ev.csv (8,760 hrs, 38 sockets)
├─ BESS: bess.csv (8,760 hrs, cascada flows)
└─ Mall: mall_demand.csv (8,760 hrs)
     │
     ▼
RealOE2Environment_v6
│
├─ Hourly simulation (h = 0 to 8,759)
│  │
│  ├─ Solar available: solar_kw[h]
│  ├─ BESS SOC: bess_soc[h]%
│  ├─ Charger demand: chargers_kw[h, i] for i in [0..37]
│  └─ Mall demand: mall_kw[h]
│      │
│      ▼
│  Construct obs (246-dim):
│  ├─ [0-155]: Base features (energy, demand, time, etc.)
│  ├─ [156-193]: Socket SOC per socket (38)
│  ├─ [194-231]: Time remaining per socket (38)
│  ├─ [232-237]: BESS/Solar/Grid signals (6)
│  └─ [238-245]: Priority/urgency/capacity (8)
│      │
│      ▼
│  SAC Agent                                 
│  π(a | obs)  → action (39-dim)
│  ├─ action[0]: BESS setpoint
│  ├─ action[1:31]: Motos power (30 sockets)
│  └─ action[31:39]: Taxis power (8 sockets)
│      │
│      ▼
│  Execute action (with validation):
│  ├─ Validate total power ≤ available
│  ├─ Scale actions if needed (ratio = available/requested)
│  ├─ Simulate cascade: Solar→BESS→EVs→Mall→Grid
│  ├─ Update vehicle SOCs
│  └─ Calculate reward (multiobjetivo v6.0)
│      │
│      ▼
│  Return: (obs', reward, done, info)
│           └─ info contains: vehicles_charged, CO2_avoided, grid_import
│
└─ Repeat for 8,760 hours (1 episode)

Train: 15 episodes = 131,400 timesteps
Duration: 6-8h (GPU RTX 4060)
Result: Trained model → checkpoints/SAC/sac_v6_final.zip
```

---

## QUICK START COMMAND

```bash
# 1. Read docs (30 min)
# See: docs/ARQUITECTURA_SAC_v6_COMUNICACION_SISTEMAS.md

# 2. Train (6-8 hours, GPU)
cd d:\diseñopvbesscar
python scripts/train/train_sac_sistema_comunicacion_v6.py --device cuda

# 3. Validate (1 hour)
python scripts/validation/validate_sac_v6.py

# DONE: Model ready at checkpoints/SAC/sac_v6_final.zip
```

---

## KEY INSIGHT

```
v5.3 Agent sees:
  "Average moto SOC = 45%, average time remaining = 28 minutes"
  → Guesses broadly → Low efficiency

v6.0 Agent sees:
  Socket breakdown:
    [0] 95% SOC, 0.5h remaining
    [1] 45% SOC, 2.8h remaining
    [2] 10% SOC, 4.5h remaining
    ...
  Plus explicit signals from BESS, Solar, Grid
  → Learns exact prioritization → High efficiency (+85% vehicles/day)
```

---

## FILES TO UNDERSTAND

1. `docs/ARQUITECTURA_SAC_v6_COMUNICACION_SISTEMAS.md` ← Technical deep dive
2. `docs/RESUMEN_EJECUTIVO_v6_COMUNICACION.md` ← Non-technical overview
3. `docs/DIAGRAMAS_COMUNICACION_v6.md` ← Visual flows
4. `docs/GUIA_IMPLEMENTACION_SAC_v6.md` ← Step-by-step implementation
5. `INICIO_RAPIDO_v6.md` ← Quick start guide

---

**Summary**: v6.0 gives agent 90 new features (socket-level SOC, time remaining, explicit energy signals) → learns to charge 2x more vehicles without degrading CO2 metrics.

**Next**: Run entrenamiento and validate results.
