# Data Sources: REAL vs SIMULATED Architecture Map

**Date:** 2026-02-14  
**Status:** Production-Ready  
**Version:** pvbesscar v5.2

---

## Overview

This document maps every data source in pvbesscar to its **REAL** (measured/observed) or **SIMULATED** (calculated/optimized) origin, helping understand:
1. Where ground truth ends
2. Which outputs are optimization targets vs constraints
3. How baseline scenarios validate agent behavior

---

## Quick Legend

| Symbol | Meaning | Source | Immutable? | Updates? |
|--------|---------|--------|-----------|----------|
| **✅** | REAL | Measured from site/devices | Yes | Yearly review |
| **⚠️** | SIMULATED | Calculated from OE2 logic | No | Changes with dispatch rules |
| **🧮** | DERIVED | Computed from REAL/SIMULATED | Dynamic | Real-time |

---

## Data Source Index (OE2 → OE3 Pipeline)

### **PHASE OE2 (Dimensioning)** - Infrastructure Ground Truth

#### **✅ SOLAR GENERATION**
- **Status:** REAL - Measured hourly PV output
- **Location:** `data/interim/oe2/solar/pv_generation_citylearn_v2.csv`  
  or `data/processed/citylearn/iquitos_ev_mall/Generacionsolar/pv_generation_hourly_citylearn_v2.csv`
- **Time Series:** 8,760 hours (1 full year 2024)
- **Column:** `ac_power_kw` (grid-tied inverter output), `pv_kw` (alternative)
- **Annual Total:** ~4,050 kWp × capacity factor = 8,000-9,000 MWh
- **Validation:** Must have exactly 8,760 rows (hourly), NOT 15-minute data
- **Used By:** 
  - [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py#L197-L221)
  - [train_ppo_sb3.py](../scripts/train/train_ppo_sb3.py) (similar pattern)
  - [dataset_builder.py](../src/citylearnv2/dataset_builder/dataset_builder.py) (validation)
- **Impact:** Primary decarbonization lever; agent optimizes dispatch timing to maximize solar self-consumption

---

#### **✅ CHARGERS (EV Demand)**
- **Status:** REAL - Measured hourly charging demand profiles
- **Location:** `data/interim/oe2/chargers/chargers_real_hourly_2024.csv`  
  or `data/processed/citylearn/iquitos_ev_mall/chargers/chargers_real_hourly_2024.csv`
- **Specification:** 19 chargers × 2 sockets = **38 total sockets** (v5.2)
  - 15 chargers for motos
  - 4 chargers for mototaxis
  - Each socket: 7.4 kW (Mode 3, 32A @ 230V monofásico)
- **Time Series:** 8,760 hours (1 full year 2024)
- **Columns:** `socket_000` to `socket_037` (38 cols)
- **Annual Demand:** 18,500–21,000 kWh total
- **Validation:** Must have exactly 38 columns matching socket names
- **Used By:**
  - [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py#L223-L252)
  - [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py) - Defines `ChargerSpec`, `ChargerSet` (immutable)
  - RL agents: observation/action space builder
- **Impact:** Defines hard constraints: agent MUST satisfy 38-socket demand within daily charging window

---

#### **✅ SHOPPING MALL DEMAND**
- **Status:** REAL - Measured hourly consumption (base load)
- **Location:** `data/interim/oe2/demandamallkwh/demandamallhorakwh.csv`  
  or `data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv`
- **Time Series:** 8,760 hours
- **Column:** `demand_kwh` or last column if unnamed
- **Annual Demand:** 876–900 MWh (~100 kW average base load)
- **Validation:** Fill missing rows with circular wrap-around if necessary
- **Used By:**
  - [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py#L254-L271)
  - Building energy simulation (CityLearn)
- **Impact:** Non-controllable baseline load; RL agent must minimize grid import to cover (mall + chargers - solar)

---

### **PHASE OE2 (Dimensioning)** - Optimization Outputs

#### **⚠️ BESS STATE & DISPATCH**
- **Status:** SIMULATED - Calculated output from OE2 dispatch optimization
- **Location:** `data/oe2/bess/bess_simulation_hourly.csv`  
  or fallback: `data/interim/oe2/bess/bess_simulation_hourly.csv`
- **Time Series:** 8,760 hours
- **Key Columns:**
  - `bess_soc_percent` or `soc_kwh` (State of Charge)
  - `bess_charge_kw` (charging power) ✅ REAL constraint from charger data
  - `cost_grid_import_soles` (⚠️ SIMULATED from tariff rules)
  - `co2_avoided_indirect_kg` (⚠️ ESTIMATED from grid factor)
- **BESS Specs (Fixed):**
  - Energy capacity: 1,700 kWh max SOC (verified from dimensioning OE2)
  - Max charge: 281.2 kW (19 chargers × 14.8 kW AC/DC losses)
  - Max discharge: 500 kW (infrastructure spec)
- **Validation:** SOC timeline must respect charge/discharge rates
- **Used By:**
  - [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py#L273-L333)
  - RL observation space (SOC observation)
  - Reward function (cost/CO2 components)
- **Impact:** **Reference trajectory** for RL training; determines feasible reward bounds and baseline performance

---

### **PHASE OE3 (Control)** - Runtime Signals

#### **🧮 OBSERVATIONS** (RL Agent Inputs)
- **Source:** CityLearn environment builder
- **Merged From:** SOLAR (✅) + CHARGERS (✅) + MALL (✅) + BESS (⚠️) + TIME
- **Composition (example, 394-dim):**
  ```
  [1 solar + 1 grid_freq + 1 BESS_SOC + 38 socket_power + 38 socket_availability
   + 24 timestep features (hour/weekday/month)] = ~104 base dims per building
  ```
- **Timestamp Resolution:** 1 hour (3,600 seconds)
- **Normalization:** [0,1] via environment wrapper
- **Used By:** SAC/PPO/A2C policy networks
- **Impact:** Temporal dynamics encoded; hour-of-day directly observes solar/demand patterns

---

#### **🧮 ACTIONS** (RL Agent Outputs)
- **Source:** SAC/PPO/A2C policy network
- **Specification:** 39-dim continuous [0,1]
  - Dim 0: BESS charging power setpoint (0=discharge max, 1=charge max)
  - Dims 1-38: Per-socket EV charger power setpoints (0=off, 1=full)
- **Conversion:** Normalized [0,1] → physical kW via `action_bounds` dict
- **Physical Limits:**
  - BESS: [-500, +281.2] kW (discharge / charge)
  - Socket: [0, 7.4] kW each (unidirectional charging only)
- **Impact:** Agents learn when to defer charging to high-solar hours

---

#### **🧮 REWARDS** (RL Objective Function)
- **Source:** `src/rewards/rewards.py` - MultiObjectiveReward
- **Composition (default weights):**
  ```python
  reward = 0.50 * co2_minimization      # ← Primary: minimize grid CO2 imports
          + 0.20 * solar_utilization     # ← Secondary: maximize PV self-consumption
          + 0.15 * ev_completion         # ← Tertiary: ensure EVs charged
          + 0.10 * grid_stability        # ← Tertiary: smooth ramps
          + 0.05 * cost_minimization     # ← Tertiary: favor off-peak tariffs
  ```
- **Ground Truth (CO₂ factor):**
  - **✅ Real:** Iquitos isolated grid CO₂ factor = **0.4521 kg CO₂/kWh** (from diesel generation)
  - **⚠️ Simulated:** Grid frequency stability metric
- **Data Sources for Reward Components:**
  - `co2_minimization`: Grid import (⚠️ simulated) × CO₂ factor (✅ fixed)
  - `solar_utilization`: PV generation (✅) vs PV curtailment (🧮 derived)
  - `ev_completion`: Charger demand (✅) vs delivered energy (⚠️ optimization)
- **Impact:** Drives entire agent optimization loop; weight changes trigger retraining

---

## Dependency Graph: OE2 → OE3

```
┌─────────────────────────────────────────────────────────────────┐
│ OE2 DIMENSIONING (Infrastructure Ground Truth) ✅ REAL          │
├─────────────────────────────────────────────────────────────────┤
│ • Solar 4,050 kWp, 8,760h timeseries                           │
│ • 19 chargers × 2 sockets = 38 total, 8,760h demand profiles   │
│ • Mall base load, 100 kW avg, 8,760h timeseries                │
│ • BESS 1,700 kWh spec (immutable infrastructure)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
         OE2 DISPATCH OPTIMIZATION (Rule-based)
         ⚠️ SIMULATED reference trajectory
         ┌─────────────────────────────────┐
         │ BESS dispatch rules:            │
         │ • Charge from PV excess         │
         │ • Discharge for EV demand       │
         │ • Minimize grid import          │
         │ Outputs:                        │
         │ - bess_soc_percent              │
         │ - cost_grid_import              │
         │ - co2_avoided_kg                │
         └────────────┬────────────────────┘
                      │
        ┌─────────────▼────────────────────┐
        │ OE3 CONTROL (RL training) 🧮 DERIVED
        ├─────────────────────────────────┤
        │ Environment: CityLearn v2       │
        │ Inputs (Observations):          │
        │ • Solar ✅ REAL                 │
        │ • Chargers ✅ REAL              │
        │ • Mall ✅ REAL                  │
        │ • BESS SOC ⚠️ SIMULATED (init)  │
        │                                 │
        │ Agent Output (Actions): [BESS + 38 sockets] [0,1]
        │                                 │
        │ Rewards:                        │
        │ • CO₂: Grid import × 0.4521 kg/kWh ✅
        │ • Other: Derived metrics 🧮     │
        │                                 │
        │ Training Loop (SAC/PPO/A2C):    │
        │ Agent learns optimal dispatch   │
        │ Checkpoints saved after each    │
        │ improvement                     │
        └─────────────┬────────────────────┘
                      │
            ┌─────────▼──────────┐
            │ AGENT CHECKPOINTS  │
            │ ✅ REAL results    │
            │ (CO₂ reduction %)  │
            │ (Solar util %)     │
            │ (Reward curve)     │
            └────────────────────┘
```

---

## Common Questions

### Q1: "Why is BESS status ⚠️ SIMULATED, but Solar/Chargers/Mall are ✅ REAL?"
**A:** OE2 creates a reference dispatch profile using rule-based optimization (not real device telemetry). The RL agent in OE3 replaces this optimization logic and learns better dispatch. But the BESS *capacity* (1,700 kWh) and *charging speed* (281.2 kW) are fixed infrastructure specs (✅ REAL). The *trajectory* in bess_simulation_hourly.csv is a baseline for comparison, not a constraint.

---

### Q2: "Can I change the BESS capacity from 1,700 kWh to something else?"
**A:** Yes, but it requires:
1. Modify [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py) - `BESS_CONFIG` constant
2. Regenerate `bess_simulation_hourly.csv` via OE2 dispatch optimization
3. Update environment config in CityLearn v2 dataset builder
4. **Restart training from scratch** (old checkpoints won't match)

---

### Q3: "If I have 15-minute solar data, not hourly, what do I do?"
**A:** **DO NOT use as-is.** The dataset builder expects exactly 8,760 hourly rows. Resample first:
```python
import pandas as pd
df = pd.read_csv('solar_15min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df_hourly = df.set_index('timestamp').resample('h')['ac_power_kw'].mean()
df_hourly.to_csv('solar_hourly.csv')
```
Verify: `len(df_hourly) == 8760`

---

### Q4: "Why does the RL reward use CO₂ factor 0.4521, not a variable grid emissions intensity?"
**A:** Iquitos operates an **isolated grid** with stable diesel generation mix (no external grid to reduce). The 0.4521 kg CO₂/kWh is **empirically validated** from thermal generation in Peru's northern region. Treating it as a constant is correct for this site.

If you model grid interconnection later, parameterize it as:
```python
CO2_FACTOR_IQUITOS = 0.4521  # ✅ REAL, isolated diesel grid
CO2_FACTOR_PERU_GRID = 0.285  # ⚠️ SIMULATED, if future interconnection
```

---

### Q5: "The BESS simulation shows lower costs than my tariff calculations. Why?"
**A:** The BESS simulation uses a **rule-based dispatch** that may not capture dynamic tariff pricing or real-time market signals. The RL agent replaces this with a learned policy. Compare:
- `bess_simulation_hourly.csv`: ⚠️ OE2 baseline (rule-based)
- SAC/PPO/A2C results: Better dispatch (RL-learned)

If they're nearly identical, the rule-based dispatch is already optimal for this scenario.

---

## Validation Checklist

Before running training:

- [ ] **Solar** (`pv_generation_hourly_citylearn_v2.csv`):
  - Size: 8,760 rows × 1 column (or more)
  - Column name contains: `ac_power_kw` or `pv_kw` or `pv_generation_kwh`
  - Non-negative values
  - Annual sum: 7,000–10,000 MWh (sanity check)

- [ ] **Chargers** (`chargers_real_hourly_2024.csv`):
  - Size: 8,760 rows × 38 columns
  - Column names: `socket_000` to `socket_037`
  - Non-negative values
  - Annual sum per socket: 300–600 kWh (typical EV usage)

- [ ] **Mall** (`demandamallhorakwh.csv`):
  - Size: 8,760 rows (or padded to 8,760)
  - Column: `demand_kwh` or last column
  - Non-negative values
  - Annual sum: 850–950 MWh (100 kW avg × 8,760h)

- [ ] **BESS** (`bess_simulation_hourly.csv`):
  - Size: 8,760 rows
  - Columns: `bess_soc_percent` (0–100) or `soc_kwh` (0–1,700)
  - `bess_charge_kw` or similar (rate constraint)
  - All timestamps present (no gaps)

---

## References

- **Implementation:** [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py) - Lines 193–333 (data loading + validation)
- **Charger Specs:** [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py) - v5.2 immutable specs
- **Reward Function:** [rewards.py](../src/rewards/rewards.py) - MultiObjectiveReward weights
- **Environment:** [dataset_builder.py](../src/citylearnv2/dataset_builder/dataset_builder.py) - CityLearn v2 validator
- **Diagnostics:** See [Common Pitfalls & Solutions](../docs/QUICK_REFERENCE.md#common-pitfalls--solutions) in QUICK_REFERENCE.md

---

**Last Updated:** 2026-02-14  
**Maintained By:** pvbesscar Team
