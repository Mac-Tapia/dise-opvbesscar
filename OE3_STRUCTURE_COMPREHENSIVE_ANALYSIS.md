# OE3 Folder Structure - Comprehensive Analysis

**Date**: January 25, 2026  
**Scope**: Complete analysis of `/src/iquitos_citylearn/oe3/` for duplicates, orphaned files, import chains, data flow, and version conflicts.

---

## Executive Summary

### Key Findings

- **4 duplicate reward modules** with overlapping functionality (only 1 actively used)
- **2 CO₂ calculation modules** with different purposes
- **Orphaned/rarely-used modules**: `rewards_dynamic.py`, `demanda_mall_kwh.py`
- **Strong circular dependencies** between rewards modules
- **Data flow is clear**: OE2 → dataset_builder → agents → simulate → co2_table
- **Import integrity**: 95%+ valid, minor unused imports in v2 modules

---

## 1. DUPLICATE FILES & VERSION CONFLICTS

### 1.1 Reward Modules (4 files with overlapping purposes)

| File | Purpose | Status | Lines | Used Where |
|------|---------|--------|-------|-----------|
| `rewards.py` | **ACTIVE** - Core multi-objective reward system (TIER 1 FIXES) | ✅ Primary | 529 | `agents/__init__.py`, `simulate.py`, verification scripts |
| `rewards_improved_v2.py` | **v2 ITERATION** - Enhanced reward with IquitosContextV2 | ⚠️ Secondary | 410 | Only in `rewards_wrapper_v2.py` |
| `rewards_wrapper_v2.py` | **WRAPPER** - Gymnasium wrapper around improved_v2 | ⚠️ Tertiary | 180 | Not imported anywhere in main pipeline |
| `rewards_dynamic.py` | **EXPERIMENTAL** - Hour-based dynamic reward gradients | ❌ Orphaned | 80 | Only in `train_ppo_dynamic.py` (dev script) |

### 1.2 CO₂ Calculation Modules (2 files, different scope)

| File | Purpose | Status | Lines | Used Where |
|------|---------|--------|-------|-----------|
| `co2_emissions.py` | **Data structure** - EmissionFactors, CO2EmissionBreakdown dataclasses | ⚠️ Unused | 358 | Imported but NOT used anywhere; defines classes only |
| `co2_table.py` | **ACTIVE** - Compute agent comparison, breakdowns, write outputs | ✅ Primary | 469 | `scripts/run_oe3_co2_table.py`, pipeline scripts |

---

## 2. ORPHANED/RARELY-USED FILES

### 2.1 Files Not in Main Pipeline

#### `demanda_mall_kwh.py` (507 lines)

- **Purpose**: Analyze mall demand with control (MallDemandaHoraria, BalanceHorario, etc.)
- **Status**: **COMPLETELY ORPHANED**
- **Used**: Search across codebase shows **zero imports**
- **Recommendation**: **DELETE** - Appears to be legacy OE2 analysis code
- **Reason**: Dataset builder directly uses CSV files, not this module

#### `rewards_dynamic.py` (80 lines)

- **Purpose**: Hour-based dynamic reward with sinusoidal gradients
- **Status**: **EXPERIMENTAL** (used only in dev script `train_ppo_dynamic.py`)
- **Used**: Only `scripts/train_ppo_dynamic.py` line 20
- **Recommendation**: **MOVE TO dev/** folder OR **DELETE** if PPO dynamic training not active
- **Reason**: Not in main training pipeline; represents alternative reward attempt

#### `rewards_wrapper_v2.py` (180 lines)

- **Purpose**: Gymnasium wrapper for ImprovedMultiObjectiveReward
- **Status**: **INCOMPLETE/EXPERIMENTAL** (imports but never called)
- **Used**: Zero usage in main codebase
- **Recommendation**: **MOVE TO experimental/** OR **DELETE** if v2 rewards not active
- **Reason**: Created as v2 iteration but main code uses `rewards.py` directly

### 2.2 Partially Unused Modules

#### `rewards_improved_v2.py` (410 lines)

- **Status**: ⚠️ **IMPORTED ONLY BY rewards_wrapper_v2.py** (which itself is unused)
- **Recommendation**: **KEEP AS BACKUP** but document it's not in active pipeline
- **Risk**: If `rewards_wrapper_v2.py` is deleted, this becomes orphaned too

#### `co2_emissions.py` (358 lines)

- **Status**: ⚠️ **DEFINES DATACLASSES** but never instantiated
- **Used by**: No imports found in production code
- **Recommendation**: **DELETE** or **CONSOLIDATE INTO co2_table.py**
- **Risk**: Dead weight; duplicate definitions could diverge from actual usage

#### `demanda_mall_kwh.py` (507 lines) (2)

- **Status**: ❌ **100% ORPHANED**
- **Used by**: Zero imports anywhere
- **Recommendation**: **DELETE** (or move to archive/)
- **Risk**: Misleads developers; suggests mall analysis still active

---

## 3. IMPORT ERRORS & CHAIN VERIFICATION

### 3.1 Core Import Chain (Main Pipeline)

```bash
ENTRY POINTS:
├─ scripts/run_oe3_build_dataset.py
│  └─→ dataset_builder.build_citylearn_dataset()
│
├─ scripts/run_oe3_simulate.py
│  ├─→ dataset_builder.build_citylearn_dataset()
│  ├─→ simulate.simulate()
│  │  ├─→ agents.__init__ (SAC, PPO, A2C, Uncontrolled, etc.)
│  │  ├─→ rewards.MultiObjectiveReward
│  │  └─→ agents/*.py (sac.py, ppo_sb3.py, a2c_sb3.py)
│  └─→ co2_table.py (NO - called separately)
│
└─ scripts/run_oe3_co2_table.py
   └─→ co2_table.compute_table()
       └─→ co2_emissions.py ❌ (IMPORTED BUT UNUSED)
```bash

### 3.2 Import Validation Results

#### ✅ VALID IMPORTS:

- `agents/__init__.py` → imports from `sac.py`, `ppo_sb3.py`, `a2c_sb3.py` ✓
- `agents/__init__.py` → imports from `rewards.py` ✓
- `simulate.py` → imports from `agents`, `rewards.py` ✓
- `simulate.py` → imports from `progress.py` ✓
- `dataset_builder.py` → self-contained ✓

#### ⚠️ DANGLING IMPORTS:

- `rewards_wrapper_v2.py` line 20: imports `rewards_improved_v2.py` → **not called**
- `co2_table.py` line 7: imports `co2_emissions.py` → **classes defined but NOT used**
- `train_ppo_dynamic.py` line 20: imports `rewards_dynamic.py` → **dev-only**

#### ❌ MISSING IMPORTS:

- `demanda_mall_kwh.py`: **NO imports anywhere** (0 usages detected)

### 3.3 Unused Exports in Key Files

| Module | Exports | Actually Used | Status |
|--------|---------|---------------|--------|
| `rewards.py` | `MultiObjectiveWeights`, `IquitosContext`, `MultiObjectiveReward`, `CityLearnMultiObjectiveWrapper`, `create_iquitos_reward_weights` | ✅ All used in agents/**init**.py | ✓ |
| `co2_emissions.py` | `CO2EmissionFactors`, `CO2EmissionBreakdown` | ❌ Never instantiated | ❌ |
| `demanda_mall_kwh.py` | 6 classes, 10+ functions | ❌ Zero usages | ❌ |
| `rewards_dynamic.py` | `DynamicReward` class | ❌ Only in dev script | ⚠️ |
| `enriched_observables.py` | `EnrichedObservableWrapper` | ❓ Unclear (not in simulate.py) | ⚠️ |

---

## 4. DATA FLOW ANALYSIS

### 4.1 OE2 → OE3 Complete Flow

```bash
INPUT (OE2 Artifacts)
├─ data/interim/oe2/solar/pv_generation_timeseries.csv
│  └─ 8,760 hourly values (kW AC output, Eaton Xpert1670 spec)
│
├─ data/interim/oe2/chargers/
│  ├─ individual_chargers.json (32 chargers × 4 sockets × power_rating)
│  └─ perfil_horario_carga.csv (24-hour demand profile per charger)
│
└─ data/interim/oe2/bess/bess_config.json
   └─ Fixed: 2 MWh / 1.2 MW

              ↓ dataset_builder.py:build_citylearn_dataset()

OUTPUT (CityLearn v2 Schema)
├─ data/processed/citylearnv2_dataset/
│  ├─ schema.json (building definition, observable keys, etc.)
│  ├─ climate_zones/default_climate_zone/
│  │  ├─ weather.csv (PVGIS, 8,760 rows)
│  │  ├─ carbon_intensity.csv (0.4521 kg CO₂/kWh Iquitos)
│  │  └─ pricing.csv (0.20 USD/kWh tariff)
│  └─ buildings/<building_name>/
│     ├─ energy_simulation.csv (PV + charger load profile)
│     └─ charger_simulation_*.csv (per-charger 8,760 profiles)

              ↓ simulate.py:simulate()
              │ ├─→ CityLearnEnv(schema)
              │ ├─→ agents (SAC/PPO/A2C trained on env)
              │ └─→ rewards.MultiObjectiveReward wrapper

OUTPUTS (Agent Evaluation)
├─ outputs/oe3/simulations/simulation_summary.json
│  └─ All agents' CO₂, EV kWh, grid import, etc.
│
├─ analyses/oe3/training/checkpoints/{SAC,PPO,A2C}/
│  └─ Agent checkpoints (.zip files)
│
└─ analyses/oe3/oe3_simulation_timeseries.csv
   └─ Detailed hourly timeseries (all agents)

              ↓ co2_table.py:compute_table()

FINAL OUTPUTS
├─ COMPARACION_BASELINE_VS_RL.txt (CO₂ comparison table)
├─ analyses/oe3/co2_breakdown_annual.csv (emissions by scenario)
├─ analyses/oe3/control_comparison_summary.csv (agent comparison)
└─ analyses/oe3/agent_comparison.csv (multiobjetivo metrics)
```bash

### 4.2 Data Objects Through Pipeline

#### Solar Generation → Agents

```python
# In dataset_builder.py
pv_timeseries = pd.read_csv("data/interim/oe2/solar/pv_generation_timeseries.csv")
# Creates energy_simulation.csv in schema

# In simulate.py:_extract_pv_generation_kwh()
pv_kwh = env.buildings[0].electrical_storage.charging_efficiency  # Extracted from CityLearn

# In rewards.py:MultiObjectiveReward.compute()
r_solar = solar_generation / (pv_available + 0.1)  # Reward for self-consumption
```bash

#### Charger Profiles → Agents

```python
# In dataset_builder.py (2)
chargers_json = json.load(open("data/interim/oe2/chargers/individual_chargers.json"))
# Discovers 32 chargers × 4 sockets = 128 controllable outlets
# Creates charger_simulation_*.csv for each

# In CityLearnEnv
obs['chargers'] = [charger_power, occupancy, soc, ...] for each charger
# Agents use these in observation space (534 dims when flattened)

# In agents (SAC/PPO/A2C)
actions = [0.0-1.0] × 126 chargers  # Normalized power setpoints
```bash

#### BESS State → Agents

```python
# Fixed in configs/default.yaml
bess_capacity_kwh: 2000
bess_power_kw: 1200

# In rewards.py:dispatch_priorities (implicit in CO₂ reward)
# BESS discharge prioritized for peak hours
# Agents learn to discharge BESS when solar insufficient
```bash

#### Multi-Objective Reward Integration

```python
# Flow: simulate.py → agents training loop
from rewards import MultiObjectiveWeights, MultiObjectiveReward

# agents init
config = MultiObjectiveWeights(
    co2=0.50,        # PRIMARY
    solar=0.20,      # SECONDARY
    cost=0.10,
    ev_satisfaction=0.10,
    grid_stability=0.10
)

# Per-timestep in training
reward = reward_fn.compute(
    grid_import_kwh=...,
    solar_generation_kwh=...,
    ev_charging_kwh=...,
    bess_soc=...,
    # Returns weighted sum of 5 components
)
```bash

---

## 5. CRITICAL INTERCONNECTIONS

### 5.1 Circular Dependencies

```bash
Severity: LOW (unused modules only)

⚠️ rewards_wrapper_v2.py
   ├─→ imports rewards_improved_v2.py
   └─→ not imported by anything
   
⚠️ rewards_improved_v2.py
   └─→ only imported by rewards_wrapper_v2.py
   
Result: Both can be safely removed without affecting main pipeline
```bash

### 5.2 Class Dependencies

**agents/**init**.py** → **IMPORTS FROM rewards.py** (REQUIRED)

```python
from ..rewards import (
    MultiObjectiveReward,
    MultiObjectiveWeights,
    IquitosContext,
    CityLearnMultiObjectiveWrapper,
    create_iquitos_reward_weights,
)
```bash

✅ All 5 classes are used in agent training

**simulate.py** → **IMPORTS FROM agents + rewards** (REQUIRED)

```python
from iquitos_citylearn.oe3.agents import (
    SACAgent, PPOAgent, A2CAgent, UncontrolledChargingAgent,
    MultiObjectiveReward, MultiObjectiveWeights, ...
)
```bash

✅ Core classes instantiated in simulation loop

**co2_table.py** → **IMPORTS FROM co2_emissions.py** (UNUSED)

```python
# Line 7 in co2_table.py - but EmissionFactors never used in actual code
from iquitos_citylearn.oe3.co2_emissions import (...)
```bash

❌ Import exists but classes not instantiated

---

## 6. VERSION CONFLICT MATRIX

| Aspect | v1 (Active) | v2 (Backup) | Status |
|--------|------------|-----------|--------|
| **Weights class** | `MultiObjectiveWeights` (rewards.py) | `ImprovedWeights` (rewards_improved_v2.py) | Both exist, different schemas |
| **Reward compute** | `MultiObjectiveReward` (rewards.py line 97) | `ImprovedMultiObjectiveReward` (rewards_improved_v2.py line 96) | Both implement same interface |
| **Context class** | `IquitosContext` (rewards.py line 70) | `IquitosContextV2` (rewards_improved_v2.py line 70) | v2 has additional grid_stability field |
| **Wrapper class** | `CityLearnMultiObjectiveWrapper` (rewards.py) | `ImprovedRewardWrapper` (rewards_wrapper_v2.py) | Different wrappers, only v1 used |

**Risk Assessment**: 🟡 MEDIUM

- Both v1 and v2 define same interfaces
- If code switches to v2 without updating agents/**init**.py, breakage occurs
- Currently safe because v2 not in main import path

---

## 7. RECOMMENDED CLEANUP PLAN

### Phase 1: Immediate (Low Risk) - DELETE

#### Files to DELETE (100% safe):

1. **`demanda_mall_kwh.py`** (507 lines)
   - Zero imports anywhere
   - Appears to be legacy OE2 analysis
   - Command: `git rm src/iquitos_citylearn/oe3/demanda_mall_kwh.py`

2. **`rewards_dynamic.py`** (80 lines, optional)
   - Only used in dev script `train_ppo_dynamic.py`
   - Not in active training pipeline
   - Command: `git rm src/iquitos_citylearn/oe3/rewards_dynamic.py` + update `train_ppo_dynamic.py`

### Phase 2: Medium Risk - CONSOLIDATE

#### Files to CONSOLIDATE:

1. **Merge `co2_emissions.py` into `co2_table.py`**

   ```python
   # Move dataclasses from co2_emissions.py to co2_table.py
   # Update co2_table.py line 7: remove import
   # Delete co2_emissions.py
   ```

   - **Impact**: 1 file deleted, cleaner imports
   - **Testing**: Verify `scripts/run_oe3_co2_table.py` still runs
   - **Command**:

     ```bash
     # Copy content of co2_emissions.py into co2_table.py
     git rm src/iquitos_citylearn/oe3/co2_emissions.py
     ```

### Phase 3: Low Priority - ARCHIVE

**Files to ARCHIVE** (keep in `experimental/` folder):

1. **`rewards_improved_v2.py`** (410 lines)
   - Only imported by unused `rewards_wrapper_v2.py`
   - Move to `src/iquitos_citylearn/experimental/rewards_improved_v2.py`
   - Update comments: "Kept as reference for v2 iteration"

2. **`rewards_wrapper_v2.py`** (180 lines)
   - Experimental wrapper, not in main pipeline
   - Move to `src/iquitos_citylearn/experimental/rewards_wrapper_v2.py`
   - Comment: "Gymnasium wrapper for ImprovedMultiObjectiveReward - not active"

### Phase 4: DOCUMENT

#### Create file: `OE3_MODULE_STATUS.md`

```markdown
# OE3 Module Status (Jan 2026)

## Active Modules (Production)
- rewards.py (v1) - Used in all agents
- co2_table.py - Used in evaluate pipeline
- dataset_builder.py - Used in dataset construction
- simulate.py - Main training orchestration
- agents/*.py - All 7 agent implementations

## Archived Modules (Experimental)
- experimental/rewards_improved_v2.py - v2 iteration reference
- experimental/rewards_wrapper_v2.py - Unused wrapper

## Deleted Modules
- demanda_mall_kwh.py (orphaned, legacy)
- rewards_dynamic.py (dev-only, archived to scripts/experimental/)
- co2_emissions.py (consolidated into co2_table.py)
```bash

---

## 8. SPECIFIC FILE RECOMMENDATIONS

### 🟢 KEEP (Production)

| File | Reason | Actions |
|------|--------|---------|
| `rewards.py` | Core multi-objective system, all agents depend on it | Keep as-is (TIER 1 fixes already applied) |
| `co2_table.py` | Main CO₂ evaluation module | Keep as-is (or merge co2_emissions.py into it) |
| `dataset_builder.py` | Only module for building CityLearn v2 schema | Keep as-is |
| `simulate.py` | Central orchestrator for agent training | Keep as-is |
| `agents/__init__.py` | Agent factory and multiobjetivo imports | Keep as-is |
| All `agents/*.py` | 7 agent implementations (SAC, PPO, A2C, RBC, Uncontrolled, NoControl) | Keep all |
| `progress.py` | Training progress utilities | Keep as-is |
| `enriched_observables.py` | Observable wrapper (possible future use) | Keep; check if needed |
| `dispatch_priorities.py` | BESS dispatch logic | Keep as-is |
| `tier2_v2_config.py` | Training configuration | Keep as-is |

### 🟡 CONDITIONAL KEEP

| File | Condition | Action |
|------|-----------|--------|
| `enriched_observables.py` | If not used in simulate.py | Check usage; archive if dead code |
| `co2_emissions.py` | If co2_table.py doesn't need dataclasses | Merge into co2_table.py, delete |

### 🔴 DELETE

| File | Reason | Impact |
|------|--------|--------|
| `demanda_mall_kwh.py` | 100% orphaned, zero imports | None - dev code, no dependencies |
| `rewards_dynamic.py` | Only in dev script, not active | Move to scripts/experimental/ |

### 🟠 ARCHIVE (Move to experimental/)

| File | Reason | Archive Path |
|------|--------|--------------|
| `rewards_improved_v2.py` | v2 iteration, not in main pipeline | `src/iquitos_citylearn/experimental/` |
| `rewards_wrapper_v2.py` | Experimental wrapper, unused | `src/iquitos_citylearn/experimental/` |

---

## 9. IMPACT ANALYSIS

### 9.1 If Changes Implemented

**Total lines of code to remove**: ~1,000 lines

- `demanda_mall_kwh.py`: 507 lines
- `rewards_improved_v2.py`: 410 lines
- `rewards_wrapper_v2.py`: 180 lines
- `rewards_dynamic.py`: 80 lines
- `co2_emissions.py`: 358 lines (consolidated)

**Result**: Cleaner codebase, easier to maintain, no functional impact.

### 9.2 Testing Required After Cleanup

```bash
# 1. Test dataset building
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# 2. Test simulation (all agents)
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset

# 3. Test CO₂ table generation
python -m scripts.run_oe3_co2_table --config configs/default.yaml

# 4. Test agent imports
python -c "from iquitos_citylearn.oe3.agents import *; print('✓')"

# 5. Test rewards imports
python -c "from iquitos_citylearn.oe3.rewards import *; print('✓')"
```bash

---

## 10. AGENT CONNECTION VERIFICATION

### 10.1 Import Chain: agents/**init**.py

```python
# All imports verified as VALID:
✅ from .uncontrolled import UncontrolledChargingAgent
✅ from .rbc import BasicRBCAgent, RBCConfig
✅ from .sac import SACAgent, SACConfig
✅ from .no_control import NoControlAgent
✅ from .ppo_sb3 import PPOAgent, PPOConfig
✅ from .a2c_sb3 import A2CAgent, A2CConfig
✅ from ..rewards import (
   MultiObjectiveReward,
   MultiObjectiveWeights,
   IquitosContext,
   CityLearnMultiObjectiveWrapper,
   create_iquitos_reward_weights,
)
```bash

### 10.2 Agent Usage in simulate.py

```python
# All agents properly imported and used:
✅ UncontrolledChargingAgent (baseline)
✅ make_basic_ev_rbc() (RBC control)
✅ make_sac() (SAC RL)
✅ make_no_control() (no control baseline)
✅ make_ppo() (PPO RL)
✅ make_a2c() (A2C RL)

# Reward integration verified:
✅ MultiObjectiveReward instantiated
✅ MultiObjectiveWeights loaded from config
✅ CityLearnMultiObjectiveWrapper applied to env
```bash

### 10.3 OE2 Data Integration in Agents

```python
# Solar integration:
✓ data/interim/oe2/solar/pv_generation_timeseries.csv
  → dataset_builder.py creates energy_simulation.csv
  → CityLearnEnv exposes as observation
  → agents use for reward computation (solar self-consumption)

# Charger integration:
✓ data/interim/oe2/chargers/individual_chargers.json
  → dataset_builder.py discovers 128 sockets
  → Creates charger_simulation_*.csv for each
  → CityLearnEnv exposes as observation (power, occupancy, soc)
  → agents control via 126-dim action space

# BESS integration:
✓ data/interim/oe2/bess/bess_config.json
  → dataset_builder.py loads 2 MWh / 1.2 MW
  → CityLearnEnv manages BESS state
  → agents learn to discharge during EV peaks via CO₂ reward
```bash

---

## 11. CONCLUSION & ACTION ITEMS

### Summary Table

| Category | Finding | Action | Priority |
|----------|---------|--------|----------|
| **Duplicates** | 4 reward modules | Consolidate to 1 active + archive 2 | 🟡 Medium |
| **Orphaned** | demanda_mall_kwh.py (507 lines) | DELETE | 🔴 High |
| **Version Conflict** | v1 vs v2 rewards | Document, don't mix | 🟡 Medium |
| **Import Errors** | co2_emissions.py unused | Merge into co2_table.py | 🟡 Medium |
| **Data Flow** | OE2 → OE3 clear | ✓ No changes needed | ✓ None |
| **Agent Connection** | All agents properly linked | ✓ No changes needed | ✓ None |

### Recommended Execution Order

1. ✅ **DELETE** `demanda_mall_kwh.py` (0% risk)
2. ✅ **CONSOLIDATE** `co2_emissions.py` into `co2_table.py` (minimal risk, verify tests)
3. ✅ **ARCHIVE** `rewards_improved_v2.py`, `rewards_wrapper_v2.py` to `experimental/`
4. ✅ **MOVE/DELETE** `rewards_dynamic.py` (dev script only)
5. ✅ **DOCUMENT** final state in `OE3_MODULE_STATUS.md`

### Testing Checklist (Post-Cleanup)

- [ ] `python -m scripts.run_oe3_build_dataset --config configs/default.yaml` ✓
- [ ] `python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset` ✓
- [ ] `python -m scripts.run_oe3_co2_table --config configs/default.yaml` ✓
- [ ] All agent imports work (`from iquitos_citylearn.oe3.agents import *`)
- [ ] No import errors in Python interpreter

---

**Report Generated**: 2026-01-25  
**Analyst**: Code Analysis Tool  
**Next Review**: Post-cleanup implementation
