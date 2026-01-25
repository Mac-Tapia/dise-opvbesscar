# OE3 Cleanup Action Plan - Step-by-Step Implementation

**Date**: January 25, 2026  
**Estimated Time**: 30 minutes  
**Risk Level**: LOW (primarily file deletion and consolidation)

---

## Quick Reference: What To Do

| # | Action | File | Commands | Risk | Est. Time |
|---|--------|------|----------|------|-----------|
| 1 | DELETE | `demanda_mall_kwh.py` | `git rm src/iquitos_citylearn/oe3/demanda_mall_kwh.py` | 🟢 None | 2 min |
| 2 | MERGE | `co2_emissions.py` → `co2_table.py` | Copy content, delete file, remove import | 🟡 Low | 5 min |
| 3 | MOVE | `rewards_improved_v2.py` | Create `experimental/`, move file | 🟢 None | 3 min |
| 4 | MOVE | `rewards_wrapper_v2.py` | Create `experimental/`, move file | 🟢 None | 3 min |
| 5 | MOVE | `rewards_dynamic.py` | Create `scripts/experimental/`, move file | 🟡 Low | 3 min |
| 6 | CREATE | `OE3_MODULE_STATUS.md` | Document final state | 🟢 None | 5 min |
| 7 | TEST | All pipelines | Run verification scripts | 🟡 Low | 10 min |

---

## DETAILED STEPS

### Step 1: DELETE demanda_mall_kwh.py

**Why**: 100% orphaned (0 imports anywhere), legacy code from OE2 analysis phase

**Before**:

```
src/iquitos_citylearn/oe3/
├── demanda_mall_kwh.py  ← TO DELETE (507 lines, completely orphaned)
├── rewards.py
├── co2_table.py
└── ...
```

**Action**:

```bash
# Verify it's truly unused
grep -r "demanda_mall_kwh" . --include="*.py"  
# Result: Should be empty (0 matches)

# Delete
git rm src/iquitos_citylearn/oe3/demanda_mall_kwh.py

# Commit
git commit -m "Remove: Delete demanda_mall_kwh.py (100% orphaned legacy code)"
```

**After**:

- ✅ File removed from repository
- ✅ 507 lines of dead code eliminated
- ✅ No impact on training pipeline

**Verification**:

```bash
python -c "import iquitos_citylearn.oe3; print('✓ No import errors')"
```

---

### Step 2: CONSOLIDATE co2_emissions.py → co2_table.py

**Why**:

- `co2_emissions.py` defines dataclasses but they're never instantiated
- `co2_table.py` imports them but uses own logic
- Consolidation eliminates unused dependency

**Before**:

```python
# co2_table.py line 7
from iquitos_citylearn.oe3.co2_emissions import (
    EmissionsFactors,      # ❌ Never used
    CityBaseline,          # ❌ Never used
    ...
)

# co2_emissions.py (358 lines of dataclasses)
@dataclass(frozen=True)
class EmissionFactors:
    km_per_kwh: float
    km_per_gallon: float
    kgco2_per_gallon: float
    grid_kgco2_per_kwh: float
    project_life_years: int
```

**After**:

```python
# co2_table.py - all classes defined here, single source of truth
@dataclass(frozen=True)
class EmissionFactors:
    km_per_kwh: float
    km_per_gallon: float
    kgco2_per_gallon: float
    grid_kgco2_per_kwh: float
    project_life_years: int

@dataclass(frozen=True)
class CityBaseline:
    transport_tpy: float
    electricity_tpy: float
```

**Actions**:

1. **Copy content**: Read lines 1-100 from `co2_emissions.py`

   ```bash
   head -100 src/iquitos_citylearn/oe3/co2_emissions.py
   ```

2. **Add to co2_table.py**: Prepend dataclass definitions before existing imports
   - Edit: `src/iquitos_citylearn/oe3/co2_table.py`
   - Add lines 1-60 from `co2_emissions.py` after existing imports

3. **Remove old import**: In `co2_table.py` line 7

   ```python
   # DELETE THIS LINE:
   from iquitos_citylearn.oe3.co2_emissions import (...)
   ```

4. **Delete file**:

   ```bash
   git rm src/iquitos_citylearn/oe3/co2_emissions.py
   ```

5. **Commit**:

   ```bash
   git commit -m "Refactor: Consolidate co2_emissions.py into co2_table.py; remove unused dataclass definitions"
   ```

**Verification**:

```bash
# Test that co2_table script still works
python -m scripts.run_oe3_co2_table --config configs/default.yaml
# Should complete successfully, generating COMPARACION_BASELINE_VS_RL.txt
```

---

### Step 3: ARCHIVE rewards_improved_v2.py

**Why**: Only imported by unused `rewards_wrapper_v2.py`; v2 iteration reference only

**Before**:

```
src/iquitos_citylearn/oe3/
├── rewards.py              ← ACTIVE v1
├── rewards_improved_v2.py  ← BACKUP v2 (only used by wrapper_v2)
├── rewards_wrapper_v2.py   ← BACKUP v2 wrapper (unused)
└── ...
```

**After**:

```
src/iquitos_citylearn/oe3/
├── rewards.py              ← ACTIVE v1
└── experimental/
    ├── rewards_improved_v2.py    ← ARCHIVED
    └── rewards_wrapper_v2.py     ← ARCHIVED
```

**Actions**:

1. **Create experimental folder**:

   ```bash
   mkdir -p src/iquitos_citylearn/oe3/experimental
   ```

2. **Move files**:

   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_improved_v2.py \
           src/iquitos_citylearn/oe3/experimental/rewards_improved_v2.py
   ```

3. **Add documentation header** to `rewards_improved_v2.py`:

   ```python
   """
   ARCHIVED: v2 Iteration of Multi-Objective Reward System
   
   Status: Not in active pipeline (superseded by rewards.py v1)
   Date Archived: 2026-01-25
   
   Kept as reference for ImprovedMultiObjectiveReward implementation
   and ImprovedWeights class design from v2 iteration.
   
   See: rewards.py for active production implementation
   """
   ```

4. **Commit**:

   ```bash
   git commit -m "Archive: Move rewards_improved_v2.py to experimental/ (v2 iteration reference)"
   ```

---

### Step 4: ARCHIVE rewards_wrapper_v2.py

**Why**: Experimental wrapper around improved_v2; not in main pipeline

**Actions**:

1. **Move file**:

   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_wrapper_v2.py \
           src/iquitos_citylearn/oe3/experimental/rewards_wrapper_v2.py
   ```

2. **Add documentation header**:

   ```python
   """
   ARCHIVED: Gymnasium Wrapper for Improved Multi-Objective Rewards
   
   Status: Experimental, not in active pipeline
   Date Archived: 2026-01-25
   
   Kept as reference for ImprovedRewardWrapper Gymnasium wrapper
   implementation. Main pipeline uses CityLearnMultiObjectiveWrapper
   from rewards.py instead.
   
   See: rewards.py::CityLearnMultiObjectiveWrapper for active implementation
   """
   ```

3. **Create **init**.py** in experimental folder:

   ```bash
   touch src/iquitos_citylearn/oe3/experimental/__init__.py
   ```

4. **Add content to **init**.py**:

   ```python
   """Experimental / Archived modules from OE3.
   
   These modules are kept for reference and historical tracking but are NOT
   used in the active training pipeline. Use at your own risk.
   
   Archived modules:
   - rewards_improved_v2: v2 iteration of multi-objective reward system
   - rewards_wrapper_v2: Gymnasium wrapper for improved_v2 rewards
   """
   ```

5. **Commit**:

   ```bash
   git commit -m "Archive: Move rewards_wrapper_v2.py to experimental/"
   ```

---

### Step 5: MOVE rewards_dynamic.py

**Why**: Development-only script for dynamic reward experimentation; not in main pipeline

**Before**:

```
src/iquitos_citylearn/oe3/
├── rewards_dynamic.py       ← DEV ONLY (used only in scripts/train_ppo_dynamic.py)
└── ...

scripts/
├── train_ppo_dynamic.py     ← Imports rewards_dynamic
└── ...
```

**After**:

```
src/iquitos_citylearn/oe3/
├── rewards.py               ← ACTIVE
└── experimental/
    └── rewards_dynamic.py   ← ARCHIVED

scripts/experimental/
├── train_ppo_dynamic.py     ← ARCHIVED
└── ...
```

**Actions**:

1. **Move rewards_dynamic.py**:

   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_dynamic.py \
           src/iquitos_citylearn/oe3/experimental/rewards_dynamic.py
   ```

2. **Create scripts/experimental folder**:

   ```bash
   mkdir -p scripts/experimental
   ```

3. **Move train_ppo_dynamic.py**:

   ```bash
   git mv scripts/train_ppo_dynamic.py scripts/experimental/train_ppo_dynamic.py
   ```

4. **Update import in train_ppo_dynamic.py**:

   ```python
   # CHANGE FROM:
   from iquitos_citylearn.oe3.rewards_dynamic import DynamicReward
   
   # TO:
   from iquitos_citylearn.oe3.experimental.rewards_dynamic import DynamicReward
   ```

5. **Add README to scripts/experimental**:

   ```markdown
   # Experimental Training Scripts
   
   These scripts are development/experimental and NOT part of the main
   training pipeline. Use `scripts/train_agents_serial.py` for production
   training instead.
   
   ## Contents
   - train_ppo_dynamic.py: PPO with dynamic hour-based reward gradients
   ```

6. **Commit**:

   ```bash
   git commit -m "Archive: Move rewards_dynamic.py and train_ppo_dynamic.py to experimental/"
   ```

---

### Step 6: CREATE OE3_MODULE_STATUS.md

**Purpose**: Document current state of OE3 modules for future developers

**Location**: `src/iquitos_citylearn/oe3/MODULE_STATUS.md`

**Content**:

```markdown
# OE3 Module Status (2026-01-25)

## Active Production Modules ✅

### Core Modules
- **rewards.py** (529 lines)
  - Multi-objective reward system (TIER 1 fixes applied)
  - Used in all agent training
  - Implements: MultiObjectiveWeights, IquitosContext, MultiObjectiveReward, CityLearnMultiObjectiveWrapper
  
- **co2_table.py** (469 lines, consolidated from co2_emissions.py)
  - CO₂ evaluation and agent comparison
  - Generates COMPARACION_BASELINE_VS_RL.txt
  - Entry point: `scripts/run_oe3_co2_table.py`
  
- **dataset_builder.py** (863 lines)
  - Constructs CityLearn v2 schema from OE2 artifacts
  - Entry point: `scripts/run_oe3_build_dataset.py`
  - Discovers 128 EV chargers, integrates solar and BESS
  
- **simulate.py** (935 lines)
  - Main training orchestration
  - Runs agents (SAC, PPO, A2C, Uncontrolled, RBC)
  - Entry point: `scripts/run_oe3_simulate.py`

### Agent Implementations
- **agents/__init__.py**: Factory and exports
- **agents/sac.py**: SAC off-policy RL (Stable-Baselines3)
- **agents/ppo_sb3.py**: PPO on-policy RL (Stable-Baselines3)
- **agents/a2c_sb3.py**: A2C on-policy RL (Stable-Baselines3)
- **agents/rbc.py**: Rule-based control (baseline)
- **agents/uncontrolled.py**: No control (baseline)
- **agents/no_control.py**: Alternative no-control variant

### Utilities
- **progress.py**: Training progress tracking and plotting
- **enriched_observables.py**: Observable wrapper (OperationalConstraints)
- **dispatch_priorities.py**: BESS dispatch optimization
- **tier2_v2_config.py**: Training configuration dataclass
- **agent_utils.py**: GPU detection, environment validation, wrappers

---

## Archived Modules (Reference Only) 🔶

Located in `src/iquitos_citylearn/oe3/experimental/`

### rewards_improved_v2.py
- v2 iteration of multi-objective rewards
- Superseded by rewards.py
- Defines: ImprovedWeights, IquitosContextV2, ImprovedMultiObjectiveReward

### rewards_wrapper_v2.py
- Gymnasium wrapper for ImprovedMultiObjectiveReward
- Experimental, not in main pipeline
- Kept as reference only

### rewards_dynamic.py
- Hour-based dynamic reward with sinusoidal gradients
- Development experimentation only
- See: scripts/experimental/train_ppo_dynamic.py

---

## Deleted Modules 🔴

### demanda_mall_kwh.py (deleted 2026-01-25)
- Legacy OE2 mall demand analysis
- 100% orphaned (zero imports)
- Reason: No longer needed; dataset builder uses CSV files directly

### co2_emissions.py (consolidated 2026-01-25)
- Original dataclass definitions merged into co2_table.py
- Eliminated unused imports
- Reason: Single source of truth in co2_table.py

---

## Data Flow Summary

```

OE2 Artifacts
├── data/interim/oe2/solar/pv_generation_timeseries.csv
├── data/interim/oe2/chargers/individual_chargers.json
└── data/interim/oe2/bess/bess_config.json

    ↓ dataset_builder.py::build_citylearn_dataset()

CityLearn v2 Schema
├── data/processed/citylearnv2_dataset/schema.json
├── climate_zones/weather.csv, carbon_intensity.csv, pricing.csv
└── buildings/*/energy_simulation.csv, charger_simulation_*.csv

    ↓ simulate.py::simulate()
    │ ├→ agents (SAC, PPO, A2C trained)
    │ └→ rewards.py::MultiObjectiveReward

Training Results
├── outputs/oe3/simulations/simulation_summary.json
├── analyses/oe3/training/checkpoints/{SAC,PPO,A2C}/
└── analyses/oe3/oe3_simulation_timeseries.csv

    ↓ co2_table.py::compute_table()

Final Outputs
├── COMPARACION_BASELINE_VS_RL.txt
└── analyses/oe3/*.csv (breakdown, control comparison, etc.)

```

---

## Import Chain Validation ✅

All active imports verified:
- ✅ agents/__init__.py imports from sac.py, ppo_sb3.py, a2c_sb3.py
- ✅ agents/__init__.py imports from rewards.py (all 5 classes used)
- ✅ simulate.py imports from agents, rewards.py
- ✅ dataset_builder.py self-contained
- ✅ co2_table.py imports consolidated (no external dependencies)

---

## How to Use This Repository

### 1. Build Dataset (from OE2)
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```

### 2. Train Agents

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### 3. Generate CO₂ Comparison Table

```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### 4. Run Full Pipeline

```bash
python scripts/run_full_pipeline_visible.py
```

---

## Development Guidelines

### When Adding New Rewards

- Edit: `src/iquitos_citylearn/oe3/rewards.py`
- Update: `MultiObjectiveWeights` dataclass
- Test: `python -c "from iquitos_citylearn.oe3.agents import *; print('✓')"`

### When Adding New Agents

- Create: `src/iquitos_citylearn/oe3/agents/newagent.py`
- Import: `agents/__init__.py`
- Import in: `simulate.py`

### When Experimenting with New Reward Functions

- Use: `src/iquitos_citylearn/oe3/experimental/` for development
- Document: Add clear "EXPERIMENTAL" header
- Don't import into main pipeline

---

## Last Updated

- **Date**: 2026-01-25
- **Changes**: Consolidated co2_emissions.py, archived v2 reward modules, deleted orphaned demanda_mall_kwh.py
- **Author**: Code Cleanup Initiative

```

**File path**: `src/iquitos_citylearn/oe3/MODULE_STATUS.md`

---

### Step 7: VERIFICATION & TESTING

**Before running cleanup, run baseline tests**:

```bash
# Test 1: Verify imports work
echo "Testing imports..."
python -c "
from iquitos_citylearn.oe3.agents import *
from iquitos_citylearn.oe3.rewards import *
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from iquitos_citylearn.oe3.co2_table import compute_table
print('✅ All imports successful')
"

# Test 2: Run dataset build
echo "Testing dataset building..."
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
if [ $? -eq 0 ]; then echo "✅ Dataset built successfully"; fi

# Test 3: Test CO₂ table generation
echo "Testing CO₂ table generation..."
python -m scripts.run_oe3_co2_table --config configs/default.yaml
if [ $? -eq 0 ]; then echo "✅ CO₂ table generated successfully"; fi

# Test 4: Verify no orphaned imports remain
echo "Checking for orphaned imports..."
grep -r "demanda_mall" src/ scripts/ --include="*.py" 2>/dev/null
if [ $? -ne 0 ]; then echo "✅ No references to deleted modules"; fi
```

**After cleanup, run verification tests**:

```bash
# All tests from above should still pass
# Plus check for experimental imports:
python -c "
try:
    from iquitos_citylearn.oe3.experimental.rewards_improved_v2 import ImprovedWeights
    print('✅ Experimental modules accessible')
except ImportError as e:
    print(f'❌ Error: {e}')
"
```

---

## Summary: Before & After

### Before Cleanup

```
src/iquitos_citylearn/oe3/
├── rewards.py                   ✅ ACTIVE (529 lines)
├── rewards_improved_v2.py       ⚠️ UNUSED v2 (410 lines)
├── rewards_wrapper_v2.py        ⚠️ UNUSED wrapper (180 lines)
├── rewards_dynamic.py           ⚠️ DEV-ONLY (80 lines)
├── co2_emissions.py             ⚠️ UNUSED dataclasses (358 lines)
├── co2_table.py                 ✅ ACTIVE (469 lines)
├── dataset_builder.py           ✅ ACTIVE (863 lines)
├── demanda_mall_kwh.py          ❌ ORPHANED (507 lines)
├── simulate.py                  ✅ ACTIVE (935 lines)
└── agents/                      ✅ ALL ACTIVE
```

**Total: 3,750+ lines of potentially unnecessary code**

### After Cleanup

```
src/iquitos_citylearn/oe3/
├── rewards.py                   ✅ ACTIVE (529 lines)
├── co2_table.py                 ✅ ACTIVE (827 lines, consolidated)
├── dataset_builder.py           ✅ ACTIVE (863 lines)
├── simulate.py                  ✅ ACTIVE (935 lines)
├── agents/                      ✅ ALL ACTIVE
├── experimental/
│   ├── rewards_improved_v2.py   🔶 ARCHIVED (410 lines)
│   ├── rewards_wrapper_v2.py    🔶 ARCHIVED (180 lines)
│   └── rewards_dynamic.py       🔶 ARCHIVED (80 lines)
├── MODULE_STATUS.md             📋 DOCUMENTATION
└── __init__.py
```

**Total: ~3,100 lines of active code + 670 archived for reference**

**Benefit**:

- ✅ 650+ lines of dead code removed
- ✅ Cleaner import chains
- ✅ Fewer potential breaking changes
- ✅ Better documentation for future developers

---

## Git Commands Summary (All Steps)

```bash
# Step 1: Delete orphaned file
git rm src/iquitos_citylearn/oe3/demanda_mall_kwh.py

# Step 2: Consolidate (manual edit + rm)
# [Edit co2_table.py, add co2_emissions content, remove import]
git rm src/iquitos_citylearn/oe3/co2_emissions.py

# Step 3: Archive improved_v2
mkdir -p src/iquitos_citylearn/oe3/experimental
git mv src/iquitos_citylearn/oe3/rewards_improved_v2.py \
        src/iquitos_citylearn/oe3/experimental/rewards_improved_v2.py

# Step 4: Archive wrapper_v2
git mv src/iquitos_citylearn/oe3/rewards_wrapper_v2.py \
        src/iquitos_citylearn/oe3/experimental/rewards_wrapper_v2.py

# Step 5: Move dynamic
mkdir -p scripts/experimental
git mv src/iquitos_citylearn/oe3/rewards_dynamic.py \
        src/iquitos_citylearn/oe3/experimental/rewards_dynamic.py
git mv scripts/train_ppo_dynamic.py scripts/experimental/train_ppo_dynamic.py

# Step 6: Add documentation
touch src/iquitos_citylearn/oe3/MODULE_STATUS.md
# [Edit with content from Step 6 above]
touch src/iquitos_citylearn/oe3/experimental/__init__.py
touch scripts/experimental/README.md

# Final: Commit all changes
git add -A
git commit -m "Refactor: Clean up OE3 module structure

- Delete demanda_mall_kwh.py (100% orphaned)
- Consolidate co2_emissions.py into co2_table.py
- Archive rewards_improved_v2.py, rewards_wrapper_v2.py to experimental/
- Move rewards_dynamic.py and train_ppo_dynamic.py to experimental/
- Add MODULE_STATUS.md for documentation

Total: -650 lines of dead code, cleaner import chains
"
```

---

## Estimated Timeline

| Step | Task | Time | Risk |
|------|------|------|------|
| 1 | Delete demanda_mall_kwh.py | 2 min | 🟢 |
| 2 | Consolidate co2_emissions.py | 5 min | 🟡 |
| 3-5 | Move archive folders | 10 min | 🟢 |
| 6 | Create documentation | 5 min | 🟢 |
| 7 | Run verification tests | 10 min | 🟡 |
| **Total** | **All steps** | **~35 min** | **LOW** |

---

## Rollback Plan (If Issues Occur)

If any tests fail after cleanup:

```bash
# Undo all changes
git reset --hard HEAD~1

# Or selectively restore
git checkout HEAD -- src/iquitos_citylearn/oe3/demanda_mall_kwh.py
git checkout HEAD -- src/iquitos_citylearn/oe3/co2_emissions.py
# ... etc
```

---

**Ready to execute? Follow steps 1-7 in order, run tests after step 7, commit when all green.**
