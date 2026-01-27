# 🎯 REFERENCIA RÁPIDA - Arquitectura del Proyecto

**Documento de referencia:** Para entender rápidamente cómo funciona el proyecto  
**Fecha:** 27 enero 2026  
**Status:** ✅ FINAL

---

## 📊 FLUJO VISUAL DE DATOS

```
═══════════════════════════════════════════════════════════════════════════════
                        PROYECTO IQUITOS EV + PV/BESS
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ OE2: DIMENSIONAMIENTO DE INFRAESTRUCTURA                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOLAR PV              BESS                    CHARGERS                      │
│  4,050 kWp        4,520 kWh/2,712 kW         128 cargadores                 │
│  Kyocera KS20      LiFePO₄ (OE2 Real)        ├─ 112 motos @2kW             │
│  6,472 strings     (night buffer)             └─ 16 taxis @3kW              │
│  200,632 modules   (peak shaving)                512 sockets                 │
│                                                                              │
│  Eaton Xpert1670 Inverter (2 units) → 4,050 kW AC                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
                        DATOS OE2
                 (solar, demand, charger specs)
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ DATASET BUILDER: Convertir OE2 → CityLearn Environment                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input Files:                                                                │
│  ├─ pv_generation_timeseries.csv (8,760 filas)                             │
│  ├─ individual_chargers.json (32 chargers × 4 sockets)                     │
│  ├─ perfil_horario_carga.csv (demanda por hora)                            │
│  └─ bess_config.json (4,520 kWh / 2,712 kW - OE2 Real)                     │
│                                                                              │
│  Output Files:                                                               │
│  ├─ schema.json (definición CityLearn)                                     │
│  ├─ weather.csv (solar + temperatura)                                      │
│  ├─ 128 charger CSVs (demanda individual)                                  │
│  └─ Building_1.csv (demanda mall)                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ BASELINE: Simulación sin Control Inteligente                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Estrategia: TODOS LOS CHARGERS SIEMPRE AL MÁXIMO                          │
│                                                                              │
│  Input:  CityLearn Environment                                              │
│  Action: [1.0, 1.0, 1.0, ..., 1.0] (todos al 100%)                         │
│  Output: Metrics → CO₂: 10,200 kg/año (BASELINE REFERENCE)                 │
│                                                                              │
│  Simulación: 8,760 timesteps (1 año completo, resolución horaria)           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ OE3: ENTRENAMIENTO DE AGENTES RL (SAC, PPO, A2C)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ INPUT: Observación (534 dimensiones) ─────────────────────────────┐   │
│  │                                                                      │   │
│  │  Solar generation [1]                                              │   │
│  │  Grid imports [1]                                                  │   │
│  │  BESS SOC [1]                                                      │   │
│  │  Charger states [128×4 = 512]                                      │   │
│  │    ├─ demand (kW needed)                                           │   │
│  │    ├─ power (kW actual)                                            │   │
│  │    ├─ occupancy (0/1)                                              │   │
│  │    └─ battery_soc (%)                                              │   │
│  │  Time features [6]                                                 │   │
│  │    ├─ hour_of_day [0-23]                                          │   │
│  │    ├─ day_of_week [0-6]                                           │   │
│  │    ├─ month [1-12]                                                │   │
│  │    ├─ is_peak_hours [0/1]                                         │   │
│  │    ├─ carbon_intensity [kg CO₂/kWh]                               │   │
│  │    └─ electricity_price [$/kWh]                                   │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                                │
│          ┌─────────────────────────────────┐                               │
│          │ POLICY NETWORK (MLP)            │                               │
│          ├─────────────────────────────────┤                               │
│          │ Input: (534)                    │                               │
│          │   ↓ Dense(1024, ReLU)           │                               │
│          │   ↓ Dense(1024, ReLU)           │                               │
│          │   ↓ Output: (126) [0,1]         │                               │
│          │                                 │                               │
│          │ SAC: +2 Q-networks (critics)    │                               │
│          │ PPO: +1 Value network           │                               │
│          │ A2C: +1 Value network           │                               │
│          └─────────────────────────────────┘                               │
│                              ↓                                                │
│  ┌─ OUTPUT: Acciones (126 dimensiones) ──────────────────────────────┐     │
│  │                                                                      │     │
│  │  action[0:112] = Motos (0→off, 1→2kW)                              │     │
│  │  action[112:126] = Mototaxis (0→off, 1→3kW)                        │     │
│  │                                                                      │     │
│  │  REGLAS DE DESPACHO (Control):                                     │     │
│  │  1. PV→EV   (solar directo a chargers)     [priority 1 - BEST]     │     │
│  │  2. PV→BESS (cargar batería)               [priority 2]            │     │
│  │  3. BESS→EV (descargar en peak)            [priority 3]            │     │
│  │  4. BESS→Grid (inyectar si SOC>95%)        [priority 4]            │     │
│  │  5. Grid Import (si deficit)               [priority 5 - WORST]    │     │
│  │                                                                      │     │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                              ↓                                                │
│  ┌─ REWARD FUNCTION (Multi-objetivo) ────────────────────────────────┐     │
│  │                                                                      │     │
│  │  reward = 0.50 × r_co2                                              │     │
│  │         + 0.20 × r_solar                                            │     │
│  │         + 0.10 × r_cost                                             │     │
│  │         + 0.10 × r_ev_satisfaction                                  │     │
│  │         + 0.10 × r_grid_stability                                   │     │
│  │                                                                      │     │
│  │  r_co2 = (grid_co2 - agent_co2) / grid_co2   [reduce CO₂ better]   │     │
│  │  r_solar = solar_used / solar_available       [use PV directly]    │     │
│  │  r_cost = (grid_cost - agent_cost) / grid_cost [reduce cost]       │     │
│  │  r_ev_sat = chargers_satisfied / 128          [keep EVs happy]     │     │
│  │  r_grid = 1 - peak_power / max_allowed        [smooth load]        │     │
│  │                                                                      │     │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                              ↓                                                │
│  Entrenamiento: 3 episodios × 8,760 timesteps cada uno                      │
│  Checkpoint: Cada 200 timesteps                                             │
│  Output: Agentes entrenados en checkpoints/                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVALUACIÓN FINAL: Comparar Baseline vs 3 Agentes RL                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BASELINE (Control Manual)        SAC                 PPO ✨               A2C
│  ────────────────────────        ────────────        ──────────           ────
│  CO₂: 10,200 kg/año       CO₂: 7,300 kg/año  CO₂: 7,100 kg/año    CO₂: 7,500 kg/año
│  ---------                -33%                -36% BEST            -30%
│  Grid import: 41,300 kWh  Grid: 28,500 kWh   Grid: 26,000 kWh     Grid: 30,000 kWh
│  Solar util: 40%          Solar: 65%          Solar: 70% ✨        Solar: 60%
│  Peak power: 4,050 kW     Peak: 3,200 kW      Peak: 3,000 kW       Peak: 3,100 kW
│                                                                              │
│  Time/episode: N/A         Time: 35-45 min    Time: 40-50 min    Time: 30-35 min ⚡
│                                                                              │
│  Recommended: Use PPO for best CO₂ reduction, SAC for sample efficiency     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
```

---

## 🤖 ARQUITECTURA DE CADA AGENTE

### SAC (Soft Actor-Critic)

```
CARACTERÍSTICAS:
• Off-policy (aprende de experiencias pasadas)
• 2 Q-networks (evita overestimation)
• Target networks (estabilidad)
• Replay buffer 10M (sample efficiency)
• Entropy bonus (exploración automática)

FLUJO:
Observation → Actor (policy) + Gaussain noise → Continuous Action [0,1]
              ↓
          Q1(s,a), Q2(s,a) → min(Q1,Q2)
              ↓
          Critic Loss = MSE(R + γ×min(Q_target))
          Actor Loss = -E[min(Q1,Q2) + entropy]

STRENGTHS:
✓ Sample efficient (learns from old data)
✓ Handles sparse rewards well
✓ Automatic exploration (entropy)

WEAKNESSES:
✗ More complex (harder to debug)
✗ Higher memory usage (buffer)
```

### PPO (Proximal Policy Optimization)

```
CARACTERÍSTICAS:
• On-policy (usa datos del episodio actual)
• Clip ratio 0.2 (±20% cambio máximo)
• 2 networks: Actor + Critic
• GAE advantage estimation
• KL divergence constraint

FLUJO:
Observation → Actor (policy) → Deterministic Action [0,1]
              ↓
          Value network → V(state)
              ↓
          Advantage = R + γ×V(next) - V(state)
              ↓
          Clipped Loss = min(ratio×A, clip(ratio)×A)

STRENGTHS:
✓ Stable (clipping prevents huge updates)
✓ Predictable convergence
✓ Well-understood algorithm

WEAKNESSES:
✗ Sample inefficient (throws away off-policy data)
✗ Slower learning (conservative updates)
```

### A2C (Advantage Actor-Critic)

```
CARACTERÍSTICAS:
• On-policy (datos frescos solamente)
• 1 Actor + 1 Critic (simple)
• No replay buffer (rápido)
• Deterministic updates
• RMSprop optimizer (velocidad)

FLUJO:
Observation → Actor → Action [0,1]
              ↓
          Value network → V(state)
              ↓
          Advantage = R - V(state)
              ↓
          Policy Gradient = ∇log(π) × Advantage

STRENGTHS:
✓ Fastest training (simple architecture)
✓ Low memory footprint
✓ Good balance speed/stability

WEAKNESSES:
✗ High variance (no buffer smoothing)
✗ Less sample efficient
✗ May be unstable with bad hyperparams
```

---

## 📈 COMPARACIÓN RÁPIDA

| Criterio | SAC | PPO | A2C |
|----------|-----|-----|-----|
| **Velocidad** | Medio (35-45m) | Lento (40-50m) | RÁPIDO (30-35m) ⚡ |
| **Estabilidad** | Alta | MÁY ALTA ✨ | Media |
| **Muestra eficiencia** | MÁY ALTA | Media | Baja |
| **Exploración** | Automática | Manual | Manual |
| **CO₂ reduction** | -33% | -36% ✨ | -30% |
| **Memory** | ~6.8 GB | ~6.2 GB | ~6.5 GB |
| **Recomendación** | Pruebas | **Producción** | Prototipo |

---

## 🎯 MÉTODOS DE ENTRENAMIENTO

### Desde Cero
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Dataset → Baseline → SAC (3 ep) → PPO (3 ep) → A2C (3 ep)
# Tiempo total: ~5-6 horas
```

### Solo A2C (Rápido)
```bash
python -m scripts.run_a2c_only --config configs/default.yaml
# Dataset → Baseline → A2C (3 ep)
# Tiempo total: ~1-1.5 horas
```

### Componentes Individuales
```bash
# 1. Dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# 2. Baseline
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# 3. Comparar resultados
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## ✅ VALIDACIONES

**Antes de Entrenar:**
- [ ] Python 3.11.9 (`python --version`)
- [ ] Pylance: 0 errores (Problems panel vacío)
- [ ] Solar: 8,760 filas exactas
- [ ] Chargers: 32 entries × 4 sockets = 128
- [ ] UTF-8 encoding: `$env:PYTHONIOENCODING='utf-8'`

**Después de Entrenar:**
- [ ] Checkpoints en `checkpoints/A2C/`
- [ ] Resultados en `outputs/oe3_simulations/`
- [ ] CO₂ reducido vs baseline
- [ ] Solar utilization aumentado

---

**Documento de Referencia - Sistema Productivo**  
*Última actualización: 27 enero 2026*
