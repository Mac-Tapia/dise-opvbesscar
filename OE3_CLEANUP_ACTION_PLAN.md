# OE3 Cleanup Action Plan - Step-by-Step Implementation

**Date**: January 25, 2026  
**Estimated Time**: 30 minutes  
**Risk Level**: LOW (primarily file deletion and consolidation)

---

<!-- markdownlint-disable MD013 -->
## Quick Reference: What To Do | # | Action | File | Commands | Risk | Est. Time | |---|--------|------|----------|------|-----------| ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
|2|MERGE|`co2_emissions.py` → `co2_table.py`|Copy content, delete...|🟡 Low|5 min|
|3|MOVE|`rewards_improved_v2.py`|Create `experimental/`, move file|🟢 None|3 min|
|4|MOVE|`rewards_wrapper_v2.py`|Create `experimental/`, move file|🟢 None|3 min|
|5|MOVE|`rewards_dynamic.py`|Create `scripts/experimental/`,...|🟡 Low|3 min|
|6|CREATE|`OE3_MODULE_STATUS.md`|Document final state|🟢 None|5 min| | 7 | TEST | All pipelines | Run verification scripts | 🟡 Low | 10 min | ---

## DETAILED STEPS

### Step 1: DELETE demanda_mall_kwh.py

**Why**: 100% orphaned (0 imports anywhere), legacy code from OE2 analysis phase

**Before**:

<!-- markdownlint-disable MD013 -->
```bash
src/iquitos_citylearn/oe3/
├── demanda_mall_kwh.py  ← TO DELETE (507 lines, completely orphaned)
├── rewards.py
├── co2_table.py
└── ...
```bash
<!-- markdownlint-enable MD013 -->

**Action**:

<!-- markdownlint-disable MD013 -->
```bash
# Verify it's truly unused
grep -r "demanda_mall_kwh" . --include="*.py"  
# Result: Should be empty (0 matches)

# Delete
git rm src/iquitos_citylearn/oe3/demand...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**After**:

- ✅ File removed from repository
- ✅ 507 lines of dead code eliminated
- ✅ No impact on training pipeline

**Verification**:

<!-- markdownlint-disable MD013 -->
```bash
python -c "import iquitos_citylearn.oe3; print('✓ No import errors')"
```bash
<!-- markdownlint-enable MD013 -->

---

### Step 2: CONSOLIDATE co2_emissions.py → co2_table.py

**Why**:

- `co2_emissions.py` defines dataclasses but they're never instantiated
- `co2_table.py` imports them but uses own logic
- Consolidation eliminates unused dependency

**Before**:

<!-- markdownlint-disable MD013 --...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**After**:

<!-- markdownlint-disable MD013 -->
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
```bash
<!-- markdownlint-enable MD013 -->

**Actions**:
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

2. **Add to co2_table.py**: Prepend dataclass definitions before existing
imports
   - Edit: `src/iquitos_citylearn/oe3/co2_table.py`
   - Add lines 1-60 from `co2_emissions.py` after existing imports

3. **Remove old import**: In `co2_table.py` line 7

<!-- markdownlint-disable MD013 -->
   ```python
   # DELETE THIS LINE:
   from iquitos_citylearn.oe3.co2_emissions import (...)
```bash
<!-- markdownlint-enable MD013 -->

4. **Delete file**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git rm src/iquitos_citylearn/oe3/co2_emissions.py
```bash
<!-- markdownlint-enable MD013 -->

5. **Commit**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git commit -m "Refactor: Consolidate co2_emis...
```

[Ver código completo en GitHub]bash
# Test that co2_table script still works
python -m scripts.run_oe3_co2_table --config configs/default.yaml
# Should complete successfully, generating COMPARACION_BASELINE_VS_RL.txt
```bash
<!-- markdownlint-enable MD013 -->

---

### Step 3: ARCHIVE rewards_improved_v2.py

**Why**: Only imported by unused `rewards_wrapper_v2.py`; v2 iteration
reference only

**Before**:

<!-- markdownlint-disable MD013 -->
```bash
src/iquitos_citylearn/oe3/
├── rewards.py              ← ACTIVE v1
├── rewards_improved_v2.py  ← BACKUP v2 (only used by wrapper_v2)
├── rewards_wrapper_v2.py   ← BACKUP v...
```

[Ver código completo en GitHub]bash
src/iquitos_citylearn/oe3/
├── rewards.py              ← ACTIVE v1
└── experimental/
    ├── rewards_improved_v2.py    ← ARCHIVED
    └── rewards_wrapper_v2.py     ← ARCHIVED
```bash
<!-- markdownlint-enable MD013 -->

**Actions**:

1. **Create experimental folder**:

<!-- markdownlint-disable MD013 -->
   ```bash
   mkdir -p src/iquitos_citylearn/oe3/experimental
```bash
<!-- markdownlint-enable MD013 -->

2. **Move files**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_improved_v2.py \
           src/iquitos_citylearn/oe3/experim...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

4. **Commit**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git commit -m "Archive: Move rewards_improved_v2.py to"
       "experimental/ (v2 iteration reference)"
```bash
<!-- markdownlint-enable MD013 -->

---

### Step 4: ARCHIVE rewards_wrapper_v2.py

**Why**: Experimental wrapper around improved_v2; not in main pipeline

**Actions**:

1. **Move file**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_wrapp...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

3. **Create **init**.py** in experimental folder:

<!-- markdownlint-disable MD013 -->
   ```bash
   touch src/iquitos_citylearn/oe3/experimental/__init__.py
```bash
<!-- markdownlint-enable MD013 -->

4. **Add content to **init**.py**:

<!-- markdownlint-disable MD013 -->
   ```python
   """Experimental / Archived modules from OE3.
   
   These modules are kept for reference and historical tracking but are NOT
   used in the active training pipeline. Use at your own risk.
   
   Archived modu...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

5. **Commit**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git commit -m "Archive: Move rewards_wrapper_v2.py to experimental/"
```bash
<!-- markdownlint-enable MD013 -->

---

### Step 5: MOVE rewards_dynamic.py

**Why**: Development-only script for dynamic reward experimentation; not in
main pipeline

**Before**:

<!-- markdownlint-disable MD013 -->
```bash
src/iquitos_citylearn/oe3/
├── rewards_dynamic.py       ← DEV ONLY (used only in scripts/train...
```

[Ver código completo en GitHub]bash
src/iquitos_citylearn/oe3/
├── rewards.py               ← ACTIVE
└── experimental/
    └── rewards_dynamic.py   ← ARCHIVED

scripts/experimental/
├── train_ppo_dynamic.py     ← ARCHIVED
└── ...
```bash
<!-- markdownlint-enable MD013 -->

**Actions**:

1. **Move rewards_dynamic.py**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git mv src/iquitos_citylearn/oe3/rewards_dynamic.py \
           src/iquitos_citylearn/oe3/experimental/rewards_dynamic.py
```bash
<!-- markdownlint-enable MD013 -->

2. **Create scripts/experimental folder**:

<!-- markdownlint-disable MD013 -->
   ```bash
   mkdir ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

4. **Update import in train_ppo_dynamic.py**:

<!-- markdownlint-disable MD013 -->
   ```python
   # CHANGE FROM:
   from iquitos_citylearn.oe3.rewards_dynamic import DynamicReward
   
   # TO:
   from iquitos_citylearn.oe3.experimental.rewards_dynamic import DynamicReward
```bash
<!-- markdownlint-enable MD013 -->

5. **Add README to scripts/experimental**:

<!-- markdownlint-disable MD013 -->
   ```markdown
   # Experimental Training Scripts
   
   These scripts are development/experimenta...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

6. **Commit**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git commit -m "Archive: Move rewards_dynamic.py and"
       "train_ppo_dynamic.py to experimental/"
```bash
<!-- markdownlint-enable MD013 -->

---

### Step 6: CREATE OE3_MODULE_STATUS.md

**Purpose**: Document current state of OE3 modules for future developers

**Location**: `src/iquitos_citylearn/oe3/MODULE_STATUS.md`

**Content**:

<!-- markdownlint-disable MD013 -->
```markdown
# OE3 Modul...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

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

<!-- markdownlint-disable MD013 -->
```bash

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

### 1. Build...
```

[Ver código completo en GitHub]bash

### 2. Train Agents

```bash
<!-- markdownlint-enable MD013 -->
python -m scripts.run_oe3_simulate --config configs/default.yaml
<!-- markdownlint-disable MD013 -->
```bash

### 3. Generate CO₂ Comparison Table

```bash
<!-- markdownlint-enable MD013 -->
python -m scripts.run_oe3_co2_table --config configs/default.yaml
<!-- markdownlint-disable MD013 -->
```bash

### 4. Run Full Pipeline

```bash
<!-- markdownlint-enable MD01...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**File path**: `src/iquitos_citylearn/oe3/MODULE_STATUS.md`

---

### Step 7: VERIFICATION & TESTING

**Before running cleanup, run baseline tests**:

<!-- markdownlint-disable MD013 -->
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

# Test 2: Run dataset bu...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**After cleanup, run verification tests**:

<!-- markdownlint-disable MD013 -->
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
```bash
<!-- markdownlint-enable MD013 -->

---

## Summary: Before & After

### Before Cleanup

<!-- markdownlint-...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### Total: 3,750+ lines of potentially unnecessary code

### After Cleanup

<!-- markdownlint-disable MD013 -->
```bash
src/iquitos_citylearn/oe3/
├── rewards.py                   ✅ ACTIVE (529 lines)
├── co2_table.py                 ✅ ACTIVE (827 lines, consolidated)
├── dataset_builder.py           ✅ ACTIVE (863 lines)
├── simulate.py                  ✅ ACTIVE (935 lines)
├── agents/                      ✅ ALL ACTIVE
├── experimental/
│   ├── rewards_improved_v2.py   🔶 ARCHIVED (410 lines)
│   ├── rewards_wrapper...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Total: ~3,100 lines of active code + 670 archived for reference**

**Benefit**:

- ✅ 650+ lines of dead code removed
- ✅ Cleaner import chains
- ✅ Fewer potential breaking changes
- ✅ Better documentation for future developers

---

## Git Commands Summary (All Steps)

<!-- markdownlint-disable MD013 -->
```bash
# Step 1: Delete orphaned file
git rm src/iquitos_citylearn/oe3/demanda_mall_kwh.py

# Step 2: Consolidate (manual edit + rm)
# [Edit co2_table.py, add co2_emissions content, remove import]
git rm src/iquitos_citylearn/oe3/co2_emissions.py

# Step 3: Archive improved_v2
mkdir -p src/iquitos_citylearn/oe3/experimental
git mv src/iquitos_citylearn/oe3/rewards_improved_v2.py \
        src/iquitos_cit...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

<!-- markdownlint-disable MD013 -->
## Estimated Timeline | Step | Task | Time | Risk | |------|------|------|------| | 1 | Delete demanda_mall_kwh.py | 2 min | 🟢 | | 2 | Consolidate co2_emissions.py | 5 min | 🟡 | | 3-5 | Move archive folders | 10 min | 🟢 | | 6 | Create documentation | 5 min | 🟢 | | 7 | Run verification tests | 10 min | 🟡 | | **Total** | **All steps** | **~35 min** | **LOW** | ---

## Rollback Plan (If Issues Occur)

If any tests fail after cleanup:

<!-- markdownlint-disable MD013 -->
```bash
# Undo all changes
git reset --hard HEAD~1

# Or selectively restore
git checkout HEAD -- src/iquitos_citylearn/oe3/demanda_mall_kwh.py
git checkout HEAD -- src/iquitos_citylearn/oe3/co2_emissions.py
# ... etc
```bash
<!-- markdownlint-enable MD013 -->

---

**Ready to execute? Follow steps 1-7 in order, run tests after step 7, commit
when all green.**
