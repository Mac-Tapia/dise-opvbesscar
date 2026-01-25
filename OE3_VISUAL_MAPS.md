# OE3 Structure - Visual Maps & Dependency Graphs

---

## 1. Current File Structure (Before Cleanup)

```
src/iquitos_citylearn/oe3/
│
├── 🟢 ACTIVE PRODUCTION FILES
│   ├── rewards.py                          [529 lines] ← All agents depend on this
│   ├── co2_table.py                        [469 lines] ← Main evaluation output
│   ├── dataset_builder.py                  [863 lines] ← Creates CityLearn schema
│   ├── simulate.py                         [935 lines] ← Central orchestrator
│   ├── progress.py                         [50 lines]  ← Training utilities
│   ├── enriched_observables.py             [180 lines] ← Observable wrapper
│   ├── dispatch_priorities.py              [265 lines] ← BESS dispatch logic
│   ├── tier2_v2_config.py                  [50 lines]  ← Config dataclass
│   │
│   └── agents/                             [7 implementations]
│       ├── __init__.py                     ← Central exports
│       ├── sac.py                          [1,200 lines] ← SAC RL agent
│       ├── ppo_sb3.py                      [900 lines]  ← PPO RL agent
│       ├── a2c_sb3.py                      [750 lines]  ← A2C RL agent
│       ├── rbc.py                          [350 lines]  ← Rule-based control
│       ├── uncontrolled.py                 [100 lines]  ← No control baseline
│       ├── no_control.py                   [100 lines]  ← No control variant
│       ├── agent_utils.py                  [200 lines]  ← Utilities
│       ├── validate_training_env.py        [120 lines]  ← Environment validation
│       └── __pycache__/
│
├── 🟡 SECONDARY / BACKUP FILES (Should Archive)
│   ├── rewards_improved_v2.py              [410 lines] ← v2 iteration
│   ├── rewards_wrapper_v2.py               [180 lines] ← v2 wrapper
│   └── rewards_dynamic.py                  [80 lines]  ← Dynamic reward (dev)
│
├── ⚠️  UNUSED / ORPHANED FILES (Should Delete/Merge)
│   ├── co2_emissions.py                    [358 lines] ← Unused dataclasses (MERGE)
│   └── demanda_mall_kwh.py                 [507 lines] ← 100% orphaned (DELETE)
│
├── __init__.py
└── __pycache__/
```

**Summary**:

- ✅ **7 active core files** (~4,500 lines)
- ✅ **7 agent implementations** (~3,600 lines)
- ⚠️ **3 secondary files** (~670 lines to archive)
- ❌ **2 unused files** (~865 lines to delete/merge)
- **Total**: ~9,600 lines in OE3 module

---

## 2. Import Dependency Graph (Current)

```
ENTRY POINTS (Scripts)
│
├─ run_oe3_build_dataset.py ────────┐
│                                    │
├─ run_oe3_simulate.py ─────────────┤─→ dataset_builder.py
│                                    │
├─ run_oe3_co2_table.py ────────────┤
│                                    │
└─ train_agents_serial.py ──────────┘

                    ↓

            dataset_builder.py
                    │
                    ↓
        ┌───────────────────────┐
        │  Creates CityLearn    │
        │  Schema (JSON)        │
        └───────────────────────┘
                    │
                    ↓

            simulate.py
        (Central Orchestrator)
            │        │
    ┌───────┘        └────────────┐
    │                             │
    ↓                             ↓

agents/__init__.py          rewards.py
    │                           │
    ├─→ sac.py ─────────────────┤
    ├─→ ppo_sb3.py ────────────┐│
    ├─→ a2c_sb3.py ────────────┘│
    ├─→ rbc.py ──────────────────│
    ├─→ uncontrolled.py ────────┤
    ├─→ no_control.py ──────────┤
    │                           │
    └───────────────────────────┘
                    │
                    ↓
        (Training Loop with
        Multi-Objective Reward)
                    │
                    ↓

        outputs/oe3/simulations/
        simulation_summary.json
                    │
                    ↓

            co2_table.py
        (Evaluate all agents)
            │        │        │
    ┌───────┘        │        └──────────┐
    │                │                   │
    ↓                ↓                   ↓

OUTPUTS:
├─ COMPARACION_BASELINE_VS_RL.txt
├─ co2_breakdown_annual.csv
├─ agent_comparison.csv
└─ control_comparison_summary.csv


UNUSED IMPORTS:
└─ co2_emissions.py ❌ (imported but classes never used)
```

---

## 3. Data Flow: OE2 → OE3 → Training → Results

```
╔══════════════════════════════════════════════════════════════════════╗
║                    INPUT LAYER (OE2 Artifacts)                      ║
╚══════════════════════════════════════════════════════════════════════╝

  data/interim/oe2/
  ├── solar/pv_generation_timeseries.csv      [8,760 hourly kW AC values]
  │   └─ Eaton Xpert1670 spec: 2 inverters, 31 modules/string, 6,472 strings
  │
  ├── chargers/individual_chargers.json       [32 chargers × 4 sockets]
  │   └─ 112 motos @2kW + 16 mototaxis @3kW = 272 kW installed
  │
  ├── chargers/perfil_horario_carga.csv       [24-hour per-charger profile]
  │   └─ 3,061 vehicles/day, 92% utilization
  │
  └── bess/bess_config.json                   [2 MWh / 1.2 MW BESS]
      └─ Fixed capacity, DoD 80%, eff 95%


          ↓ ↓ ↓ DATASET BUILDER ↓ ↓ ↓
          (src/iquitos_citylearn/oe3/dataset_builder.py)


╔══════════════════════════════════════════════════════════════════════╗
║              PROCESSING LAYER (CityLearn v2 Schema)                 ║
╚══════════════════════════════════════════════════════════════════════╝

  data/processed/citylearnv2_dataset/
  │
  ├── schema.json                             [Building definition]
  │   ├─ 1 building (Mall Iquitos)
  │   ├─ 128 controllable charger outlets
  │   ├─ PV system (4,050 kWp)
  │   ├─ BESS system (2 MWh / 1.2 MW)
  │   └─ Grid connection (import/export)
  │
  ├── climate_zones/default_climate_zone/
  │   ├─ weather.csv                  [PVGIS TMY, 8,760 rows]
  │   ├─ carbon_intensity.csv         [0.4521 kg CO₂/kWh - Iquitos thermal]
  │   └─ pricing.csv                  [0.20 USD/kWh tariff]
  │
  └── buildings/Iquitos_EV_Mall_PV_BESS/
      ├─ energy_simulation.csv        [PV + chargers + building load]
      ├─ charger_simulation_0.csv     [Charger 1 profile, 8,760 rows]
      ├─ charger_simulation_1.csv     [Charger 2 profile, 8,760 rows]
      ├─ ...
      └─ charger_simulation_127.csv   [Charger 128 profile, 8,760 rows]


          ↓ ↓ ↓ AGENTS & ENVIRONMENT ↓ ↓ ↓
          (src/iquitos_citylearn/oe3/simulate.py)


╔══════════════════════════════════════════════════════════════════════╗
║                  TRAINING LAYER (RL Agents)                         ║
╚══════════════════════════════════════════════════════════════════════╝

  CityLearnEnv(schema)
  │
  ├─ Observation Space: 534 dimensions (flattened)
  │  ├─ Building energy (solar, demand, grid)  [4 values]
  │  ├─ Charger states (power, occupancy, SOC) [128×3 = 384 values]
  │  └─ Time features (hour, month, dow)       [4 values]
  │
  └─ Action Space: 126 continuous [0, 1]
     └─ Charger power setpoints (126 of 128 controllable)

          │ ↓
          │ Training Loop (per-timestep):
          │  1. Observe env state
          │  2. Agent.predict(obs) → action
          │  3. env.step(action)
          │  4. Compute Multi-Objective Reward:
          │     r_total = 0.50·r_CO₂ + 0.20·r_solar + 0.10·r_cost + ...
          │  5. Repeat 8,760 timesteps (1 year)
          │
          └─ Trained Agents:
             ├─ SAC (off-policy)
             ├─ PPO (on-policy)
             ├─ A2C (on-policy, simple)
             └─ Baselines (Uncontrolled, RBC, NoControl)


          ↓ ↓ ↓ EVALUATION & RESULTS ↓ ↓ ↓
          (src/iquitos_citylearn/oe3/co2_table.py)


╔══════════════════════════════════════════════════════════════════════╗
║              OUTPUT LAYER (Results & Comparisons)                   ║
╚══════════════════════════════════════════════════════════════════════╝

  outputs/oe3/simulations/
  ├─ simulation_summary.json          [All agents' metrics]
  │  ├─ pv_bess_results
  │  │  ├─ SAC: {CO₂, kWh, rewards, ...}
  │  │  ├─ PPO: {CO₂, kWh, rewards, ...}
  │  │  └─ A2C: {CO₂, kWh, rewards, ...}
  │  └─ pv_bess_uncontrolled: {baseline metrics}
  │
  └─ *_results.json                  [Per-agent detailed results]

  analyses/oe3/training/
  └─ checkpoints/
     ├─ SAC/*.zip                     [Trained models]
     ├─ PPO/*.zip
     └─ A2C/*.zip

  analyses/oe3/
  ├─ COMPARACION_BASELINE_VS_RL.txt   [CO₂ comparison table]
  ├─ co2_breakdown_annual.csv         [Emissions by scenario]
  ├─ agent_comparison.csv             [Multiobjetivo metrics]
  └─ control_comparison_summary.csv   [Control strategies]


╔══════════════════════════════════════════════════════════════════════╗
║                      FINAL OUTPUTS                                  ║
╚══════════════════════════════════════════════════════════════════════╝

  Key Metrics for Each Agent:
  ├─ CO₂ emissions (kg/year)
  ├─ EV charging (kWh/year)
  ├─ Grid import (kWh/year)
  ├─ Solar generation (kWh/year)
  ├─ Self-consumption rate (%)
  ├─ Multi-objective reward components (5 metrics)
  └─ Cost (USD/year)

  Comparison: Baseline vs SAC vs PPO vs A2C
  └─ Ranking: [Best CO₂ reduction] → Recommended agent
```

---

## 4. Reward System Architecture

```
Multi-Objective Reward Function
═════════════════════════════════════════════════════════════════

Input per timestep:
  obs, actions, env state, carbon_intensity

                    ↓

MultiObjectiveWeights (Dataclass)
├─ co2: 0.50                     ← PRIMARY objective
├─ solar: 0.20                   ← SECONDARY objective
├─ cost: 0.10                    ← TERTIARY objective
├─ ev_satisfaction: 0.10         ← BASELINE
└─ grid_stability: 0.10          ← BASELINE


                    ↓

MultiObjectiveReward.compute()
(Function in rewards.py)

    ├─ Component 1: r_CO₂ = -grid_import_kwh × 0.4521
    │  └─ Penalizes thermal grid imports
    │
    ├─ Component 2: r_solar = pv_used_directly / (pv_generated + 0.1)
    │  └─ Rewards PV self-consumption
    │
    ├─ Component 3: r_cost = -grid_import_kwh × 0.20 (USD/kWh)
    │  └─ Penalizes electricity cost
    │
    ├─ Component 4: r_ev = -max(0, charger_demand - charger_power)
    │  └─ Penalizes unmet EV charging demand
    │
    └─ Component 5: r_grid = -max(0, peak_power - threshold)
       └─ Penalizes grid demand peaks

                    ↓

Weighted Sum:
    r_total = 0.50·r_CO₂ + 0.20·r_solar + 0.10·r_cost + ...

                    ↓

Output: Single scalar reward per timestep
└─ Agents optimize total cumulative reward over 8,760 timesteps


VERSION STATUS:
═════════════════════════════════════════════════════════════════

v1 ACTIVE (rewards.py):
├─ MultiObjectiveWeights [co2, solar, cost, ev_satisfaction, grid_stability]
├─ IquitosContext [grid_carbon_intensity, tariff, charger_count]
├─ MultiObjectiveReward [compute() method]
└─ CityLearnMultiObjectiveWrapper [Gymnasium wrapper]
   └─ Used in: simulate.py (MAIN PIPELINE)

v2 ARCHIVED (rewards_improved_v2.py):
├─ ImprovedWeights [co2, solar, cost, ev_satisfaction, grid_stability + peak_import_penalty]
├─ IquitosContextV2 [adds grid_stability_threshold]
├─ ImprovedMultiObjectiveReward [compute_detailed() method]
└─ ImprovedRewardWrapper [Alternative Gymnasium wrapper]
   └─ Used in: rewards_wrapper_v2.py (NOT IN PIPELINE)

DYNAMIC (rewards_dynamic.py):
├─ DynamicReward [Hour-based sinusoidal gradients]
└─ Used in: train_ppo_dynamic.py (DEV SCRIPT ONLY)
```

---

## 5. Agent Dependency Chain

```
AGENT FACTORY
═════════════════════════════════════════════════════════════════

src/iquitos_citylearn/oe3/agents/__init__.py
│
├─→ make_sac(env, config) → SACAgent
│   └─ src/iquitos_citylearn/oe3/agents/sac.py
│      ├─ Implements: learn(), predict(), load(), save()
│      ├─ Depends on: stable_baselines3.SAC
│      ├─ Uses: progress.py (training logging)
│      └─ Requires: rewards.py (reward function)
│
├─→ make_ppo(env, config) → PPOAgent
│   └─ src/iquitos_citylearn/oe3/agents/ppo_sb3.py
│      ├─ Implements: learn(), predict(), load(), save()
│      ├─ Depends on: stable_baselines3.PPO
│      ├─ Uses: progress.py (training logging)
│      └─ Requires: rewards.py (reward function)
│
├─→ make_a2c(env, config) → A2CAgent
│   └─ src/iquitos_citylearn/oe3/agents/a2c_sb3.py
│      ├─ Implements: learn(), predict(), load(), save()
│      ├─ Depends on: stable_baselines3.A2C
│      ├─ Uses: progress.py (training logging)
│      └─ Requires: rewards.py (reward function)
│
├─→ make_basic_ev_rbc(env, config) → BasicRBCAgent
│   └─ src/iquitos_citylearn/oe3/agents/rbc.py
│      ├─ Implements: predict() [deterministic control]
│      └─ Rule: Charge if solar > demand, discharge at peak hours
│
├─→ UncontrolledChargingAgent
│   └─ src/iquitos_citylearn/oe3/agents/uncontrolled.py
│      ├─ Implements: predict() [maximum power setpoint]
│      └─ Always: action = [1.0, 1.0, ..., 1.0] (all chargers at max)
│
├─→ make_no_control(env) → NoControlAgent
│   └─ src/iquitos_citylearn/oe3/agents/no_control.py
│      ├─ Implements: predict() [zero power]
│      └─ Always: action = [0.0, 0.0, ..., 0.0] (no charging)
│
├─ Utilities: agent_utils.py
│  ├─ validate_env_spaces(env)
│  ├─ ListToArrayWrapper (CityLearn list → numpy array)
│  ├─ flatten_action(), unflatten_action()
│  └─ normalize_observations(), clip_observations()
│
└─ Validation: validate_training_env.py
   ├─ check_dataset()
   ├─ check_agents()
   ├─ check_rewards()
   └─ check_gpu()


REWARDS DEPENDENCY
═════════════════════════════════════════════════════════════════

rewards.py
│
├─ MultiObjectiveWeights dataclass
│  ├─ Instantiated by: agent configs (SAC, PPO, A2C)
│  └─ Used in: simulate.py, agents training loops
│
├─ IquitosContext dataclass
│  ├─ Instantiated by: CityLearnMultiObjectiveWrapper
│  └─ Provides: grid carbon intensity, tariff, charger count
│
├─ MultiObjectiveReward class
│  ├─ Instantiated by: CityLearnMultiObjectiveWrapper
│  ├─ Method: compute(obs, actions, info) → float reward
│  └─ Used in: Training loop (called 8,760 times per episode)
│
├─ CityLearnMultiObjectiveWrapper class
│  ├─ Wraps: CityLearnEnv (Gymnasium wrapper)
│  ├─ Override: step() method to apply custom reward
│  └─ Used in: simulate.py
│     ```python
│     env = CityLearnEnv(schema)
│     weights = MultiObjectiveWeights(...)
│     reward_fn = MultiObjectiveReward(weights, context)
│     env = CityLearnMultiObjectiveWrapper(env, reward_fn)
│     ```
│
└─ create_iquitos_reward_weights() function
   ├─ Factory: creates weights from config dict
   └─ Used in: verification scripts, config loading


TRAINING LOOP EXECUTION
═════════════════════════════════════════════════════════════════

simulate.py::simulate()
│
├─ Load schema and create CityLearnEnv
├─ Wrap with CityLearnMultiObjectiveWrapper
│
├─ Select agent: SAC / PPO / A2C / RBC / Uncontrolled
│  └─ Create agent: make_sac() / make_ppo() / make_a2c() / ...
│
├─ Training loop (per episode):
│  │
│  ├─ obs, info = env.reset()
│  │
│  ├─ For t in range(8760):  # 1 year
│  │  │
│  │  ├─ action = agent.predict(obs)  [Agent decides charger power]
│  │  │
│  │  ├─ obs, reward, terminated, truncated, info = env.step(action)
│  │  │  │
│  │  │  ├─ env executes action
│  │  │  ├─ CityLearn simulates physics
│  │  │  └─ MultiObjectiveReward.compute() → reward [CUSTOM REWARD]
│  │  │
│  │  ├─ agent.learn(obs, action, reward, next_obs, done)
│  │  │  └─ Update agent policy
│  │  │
│  │  └─ Track metrics: CO₂, EV kWh, grid import, solar gen, etc.
│  │
│  └─ Save checkpoint: agent_final.zip
│
└─ Return SimulationResult with CO₂, kWh, rewards, etc.
```

---

## 6. File Status Matrix (Before & After Cleanup)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        BEFORE CLEANUP (Current State)                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝

File                          Lines   Status      Used By              Action
─────────────────────────────────────────────────────────────────────────────
rewards.py                    529     ✅ ACTIVE   agents/__init__.py   KEEP
co2_table.py                  469     ✅ ACTIVE   run_oe3_co2_table    KEEP
dataset_builder.py            863     ✅ ACTIVE   run_oe3_build_*      KEEP
simulate.py                   935     ✅ ACTIVE   run_oe3_simulate     KEEP
progress.py                   50      ✅ ACTIVE   agents/*.py          KEEP
enriched_observables.py       180     ✅ ACTIVE   [?] Need review      KEEP*
dispatch_priorities.py        265     ✅ ACTIVE   rewards.py           KEEP
tier2_v2_config.py            50      ✅ ACTIVE   config mgmt          KEEP

agents/__init__.py            100     ✅ ACTIVE   entry point          KEEP
agents/sac.py                 1200    ✅ ACTIVE   simulate.py          KEEP
agents/ppo_sb3.py             900     ✅ ACTIVE   simulate.py          KEEP
agents/a2c_sb3.py             750     ✅ ACTIVE   simulate.py          KEEP
agents/rbc.py                 350     ✅ ACTIVE   simulate.py          KEEP
agents/uncontrolled.py        100     ✅ ACTIVE   simulate.py          KEEP
agents/no_control.py          100     ✅ ACTIVE   simulate.py          KEEP
agents/agent_utils.py         200     ✅ ACTIVE   agents/*.py          KEEP
agents/validate_training_env  120     ✅ ACTIVE   verification         KEEP

rewards_improved_v2.py        410     ⚠️  BACKUP  rewards_wrapper_v2   ARCHIVE
rewards_wrapper_v2.py         180     ⚠️  BACKUP  [NOT USED]           ARCHIVE
rewards_dynamic.py            80      ⚠️  DEV     train_ppo_dynamic    ARCHIVE

co2_emissions.py              358     ❌ UNUSED   co2_table (import)   MERGE
demanda_mall_kwh.py           507     ❌ ORPHAN   [ZERO imports]       DELETE

                            ──────
TOTAL ACTIVE CODE:         ~5,100 lines
TOTAL BACKUP CODE:            670 lines  ← Can be archived
TOTAL UNUSED CODE:            865 lines  ← Can be deleted/merged


╔═══════════════════════════════════════════════════════════════════════════════╗
║                        AFTER CLEANUP (Recommended State)                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

File                          Lines   Status      Location             Impact
─────────────────────────────────────────────────────────────────────────────
rewards.py                    529     ✅ ACTIVE   oe3/                 NONE
co2_table.py                  827     ✅ ACTIVE   oe3/                 Merged
dataset_builder.py            863     ✅ ACTIVE   oe3/                 NONE
simulate.py                   935     ✅ ACTIVE   oe3/                 NONE
progress.py                   50      ✅ ACTIVE   oe3/                 NONE
enriched_observables.py       180     ✅ ACTIVE   oe3/                 NONE
dispatch_priorities.py        265     ✅ ACTIVE   oe3/                 NONE
tier2_v2_config.py            50      ✅ ACTIVE   oe3/                 NONE

agents/                       3600    ✅ ACTIVE   oe3/agents/          NONE

rewards_improved_v2.py        410     🔶 ARCHIVE experimental/         Reference
rewards_wrapper_v2.py         180     🔶 ARCHIVE experimental/         Reference
rewards_dynamic.py            80      🔶 ARCHIVE experimental/         Reference

[DELETED co2_emissions.py]     —       —          —                    —
[DELETED demanda_mall_kwh.py]  —       —          —                    —

                            ──────
TOTAL ACTIVE CODE:         ~5,100 lines
TOTAL ARCHIVED CODE:          670 lines  ← Separate experimental/ folder
TOTAL DELETED CODE:           865 lines  ← Removed from repo

RESULT: Cleaner, easier to maintain, no functional changes to production
```

---

## 7. Risk Assessment Heat Map

```
CLEANUP OPERATIONS RISK ASSESSMENT
═════════════════════════════════════════════════════════════════════════════

Operation                          Risk Level   Rollback Time   Impact
─────────────────────────────────────────────────────────────────────────
1. DELETE demanda_mall_kwh.py      🟢 NONE      1 minute        Zero
2. MERGE co2_emissions → co2_table 🟡 LOW       2 minutes       Minor (test)
3. ARCHIVE rewards_improved_v2.py  🟢 NONE      1 minute        Zero
4. ARCHIVE rewards_wrapper_v2.py   🟢 NONE      1 minute        Zero
5. ARCHIVE rewards_dynamic.py      🟡 LOW       1 minute        Minor (dev)
6. CREATE documentation            🟢 NONE      1 minute        Zero
7. RUN VERIFICATION TESTS          🟡 LOW       5 minutes       Catch issues

TOTAL CLEANUP TIME:                ~35 minutes
TOTAL ROLLBACK TIME IF NEEDED:    ~15 minutes
CONFIDENCE LEVEL:                 95% (Very Low Risk)
```

---

**Visual analysis complete!** Use these diagrams to understand module structure, dependencies, and data flow.
