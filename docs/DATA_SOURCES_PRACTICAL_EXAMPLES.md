# Data Sources: Practical Examples & Interpretation

**Version:** pvbesscar v5.2 | **Date:** 2026-02-14  
**Purpose:** Demonstrate how to read, validate, and interpret ✅ REAL vs ⚠️ SIMULATED data

---

## Example 1: Understanding Status Labels

### Solar PV Data (✅ REAL)
```python
import pandas as pd

# Load the REAL solar data
df_solar = pd.read_csv('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')

print(f"Shape: {df_solar.shape}")         # (8760, 3)
print(f"Columns: {df_solar.columns.tolist()}")
# Output: ['timestamp', 'ac_power_kw', 'pv_kw']

print(f"Annual generation: {df_solar['ac_power_kw'].sum():.0f} kWh")
# Output: Annual generation: 8523000 kWh (realistic for 4,050 kWp @ ~25% capacity factor)

# ✅ REAL interpretation:
# This is MEASURED power from inverters in Iquitos
# NOT simulated or forecasted
# Immutable: Won't change unless new measurements collected (yearly)
```

### What Status ✅ REAL Means
- ✅ **Ground Truth:** This is what actually happened on the site
- ✅ **Immutable:** Can't be changed by dispatch algorithms
- ✅ **Validated:** Collected from SCADA/meters/inverters
- ✅ **Reproducible:** Same data for all agents (baseline + RL)

---

## Example 2: CHARGERS Data (✅ REAL)

```python
import pandas as pd
import numpy as np

# Load the 38-socket charger demand
df_chargers = pd.read_csv('data/interim/oe2/chargers/chargers_real_hourly_2024.csv')

print(f"Shape: {df_chargers.shape}")  # (8760, 38)
print(f"Sockets: {[c for c in df_chargers.columns if 'socket' in c]}")
# Output: ['socket_000', 'socket_001', ..., 'socket_037']

# Check demand pattern for one socket
socket_0_demand = df_chargers['socket_000'].values
print(f"Socket 0 annual demand: {socket_0_demand.sum():.0f} kWh")  # ~500 kWh
print(f"Peak hourly demand: {socket_0_demand.max():.1f} kW")  # ~7.4 kW (typical)

# ✅ REAL interpretation:
# These are MEASURED charging profiles from the 38 physical sockets
# NOT synthetic/simulated profiles
# Each row = 1 hour, timestep 0-8759
# Daily pattern: Peaks in evening (17-21h), lower during day
```

### Verify Chargers Integrity
```python
# Must have exactly 38 columns and 8,760 rows
assert df_chargers.shape == (8760, 38), f"Wrong shape: {df_chargers.shape}"

# Each column must be non-negative (no negative demand)
assert (df_chargers >= 0).all().all(), "Negative demand found!"

# Max per socket should be ~7.4 kW (mode 3 charger limit)
assert df_chargers.max().max() <= 8.0, "Charger exceeds 7.4 kW limit!"

print("✓ Chargers integrity check passed")
```

---

## Example 3: BESS (⚠️ SIMULATED)

```python
import pandas as pd

# Load BESS **SIMULATED** dispatch (NOT real device telemetry)
df_bess = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

print(f"Columns: {df_bess.columns.tolist()}")
# ['timestamp', 'bess_soc_percent', 'bess_charge_kw', 'bess_discharge_kw',
#  'cost_grid_import_soles', 'co2_avoided_indirect_kg', ...]

# ⚠️ SIMULATED interpretation:
soc_timeline = df_bess['bess_soc_percent'].values
print(f"SOC Range: {soc_timeline.min():.1f}% - {soc_timeline.max():.1f}%")
# Output: SOC Range: 15.2% - 99.8%

# This SOC trajectory is CALCULATED from rule-based dispatch
# NOT measured from real battery
# The RL agent will REPLACE this dispatch with learned policy
print("\n⚠️  STATUS: This is a REFERENCE trajectory from OE2 optimization")
print("   RL agents in OE3 will learn BETTER dispatch than these rules")
```

### What Status ⚠️ SIMULATED Means
- ⚠️ **Not Ground Truth:** Calculated from optimization rules, not measurements
- ⚠️ **Replaceable:** RL agents learn new dispatch, ignoring these rules
- ⚠️ **Reference Only:** Used to validate that RL improves over baseline
- ⚠️ **Time-Dependent:** Changes if dispatch rules change

---

## Example 4: How Status Affects Training

```python
import numpy as np
from src.rewards.rewards import IquitosContext, create_iquitos_reward_weights

# Step 1: Load ✅ REAL data (immutable)
solar_real = np.array([100, 200, 300, 200, 100, 0, 0, ...])  # 8760 values
chargers_real = np.array([[2.0, 1.5, 3.2, ...], ...])  # 8760 × 38
mall_real = np.array([80, 90, 100, ...])  # 8760 values

# These are FIXED constraints for all agents (baseline + SAC + PPO + A2C)
# Agents CANNOT change what the site generated or demanded

# Step 2: ⚠️ SIMULATED baseline dispatch (reference trajectory)
bess_soc_baseline = np.array([50, 52, 48, 55, ...])  # Calculated from OE2 rules
cost_baseline = np.array([1000, 950, 900, ...])  # Calculated tariff costs

# Step 3: RL Agent learns BETTER dispatch
# Agent observes: solar + chargers + mall + initial_bess_soc
# Agent outputs: dispatch actions (1 BESS + 38 sockets)
# Agent computes reward using REAL CO₂ factor:

ctx = IquitosContext()
reward_weights = create_iquitos_reward_weights(ctx)

# CO₂ minimization uses REAL grid factor (0.4521 kg CO₂/kWh ✅)
co2_factor = 0.4521  # ✅ REAL fixed for Iquitos isolated grid
grid_import = solar_real + chargers_real + mall_real - agent_output
co2_emissions = grid_import * co2_factor

# RL reward includes CO₂:
reward = 0.50 * (-co2_emissions)  # Minimize grid CO₂

print(f"Training loop:")
print(f"  1. ✅ REAL data (solar, chargers, mall) - CONSTRAINTS")
print(f"  2. ⚠️  Baseline dispatch - REFERENCE for comparison")
print(f"  3. RL learns to BEAT baseline")
print(f"  4. ✅ CO₂ factor (0.4521) - OBJECTIVE")
```

---

## Example 5: When Data Status Matters

### Scenario A: Adding New Solar Data
```
Year 2025 solar data becomes available
→ Status: ✅ NEW REAL data
→ Action: Update data/interim/oe2/solar/pv_generation_2025.csv
→ Impact: Agents must retrain with NEW RL environment
→ Reason: ✅ REAL data is immutable parameter for training
```

### Scenario B: Improving BESS Dispatch Rules
```
OE2 rule-based optimization improved
→ Status: ⚠️ BETTER SIMULATED baseline
→ Action: Regenerate bess_simulation_hourly.csv with new rules
→ Impact: Training can continue (SIMULATED is reference, not constraint)
→ Reason: ⚠️ SIMULATED is replaced by RL agents, not used as hard constraint
```

### Scenario C: Changing Charger Specifications
```
Upgrade from 7.4 kW to 11 kW chargers
→ Status: ✅ NEW REAL spec
→ Action: Update chargers.py + regenerate charger profiles
→ Impact: FULL retrain needed (obs/action space changed)
→ Reason: ✅ REAL charger spec is fundamental to environment
```

---

## Example 6: Interpreting Validation Errors

### Error 1: "Solar CSV has 2,920 rows, expected 8,760"
```
Root cause: 15-minute data instead of hourly
Status: ❌ WRONG RESOLUTION
Fix: Downsample 15-min → hourly
→ df.set_index('time').resample('h').mean()

Why it matters:
  ✅ REAL data must be hourly (matching 8,760-hour year)
  Mixing resolutions breaks environment timestep logic
```

### Error 2: "BESS cost values are negative"
```
Root cause: ⚠️ SIMULATED cost calculation error (sign flip in rules)
Status: ⚠️ FIXABLE (not ground truth)
Fix: Regenerate bess_simulation_hourly.csv with corrected rules

Why it matters:
  ⚠️ SIMULATED data is replaceable - regenerate from corrected OE2 rules
  Then rerun agents (they ignore cost baseline, learn from scratch)
```

### Error 3: "Chargers have 35 sockets, expected 38"
```
Root cause: Missing charger data file
Status: ❌ INCOMPLETE ✅ REAL DATA
Fix: Obtain actual charger #36, #37, #38 profiles from site
     OR verify chargers #36-38 don't exist in v5.2

Why it matters:
  ✅ REAL charger count is fixed by infrastructure
  Must determine: Are sockets 36-38 physically missing,
                 or is the CSV incomplete?
```

---

## Example 7: Database-Level Interpretation

```python
import pandas as pd
import json

# Create a data quality report
report = {
    "timestamp": pd.Timestamp.now(),
    "data_sources": {
        "solar": {
            "status": "✅ REAL",
            "file": "data/interim/oe2/solar/pv_generation_citylearn_v2.csv",
            "rows": 8760,
            "columns": ["timestamp", "ac_power_kw"],
            "annual_kwh": 8523000,
            "source_origin": "PVGIS SCADA inverter data Iquitos 2024",
            "immutable": True,
            "validation": "PASS"
        },
        "chargers": {
            "status": "✅ REAL",
            "file": "data/interim/oe2/chargers/chargers_real_hourly_2024.csv",
            "rows": 8760,
            "columns": 38,  # socket_000 to socket_037
            "total_annual_kwh": 19500,
            "source_origin": "Meter logs from 19 chargers (38 sockets) Iquitos 2024",
            "immutable": True,
            "validation": "PASS"
        },
        "bess": {
            "status": "⚠️ SIMULATED",
            "file": "data/oe2/bess/bess_simulation_hourly.csv",
            "rows": 8760,
            "max_soc_kwh": 1700,
            "source_origin": "OE2 rule-based dispatch optimization (NOT real device)",
            "immutable": False,  # Can be regenerated with new rules
            "validation": "PASS",
            "note": "RL agents replace these dispatch rules"
        }
    },
    "training_readiness": "✅ READY",
}

with open('outputs/data_quality_report.json', 'w') as f:
    json.dump(report, f, indent=2, default=str)

print("Data quality report saved")
print(json.dumps(report, indent=2, default=str))
```

**Output:**
```json
{
  "data_sources": {
    "solar": {"status": "✅ REAL", "validation": "PASS"},
    "chargers": {"status": "✅ REAL", "validation": "PASS"},
    "bess": {"status": "⚠️ SIMULATED", "validation": "PASS"},
  },
  "training_readiness": "✅ READY"
}
```

---

## Summary: Status Usage Guide

| If Status is... | Then it means... | Can be changed by... | Used as... |
|-----------------|-----------------|-------------------|-----------|
| ✅ REAL | Measured from site | Yearly data collection | Hard constraint |
| ⚠️ SIMULATED | Calculated from rules | Updating OE2 dispatch logic | Reference/baseline |
| 🧮 DERIVED | Computed at runtime | RL agent optimization | Feedback signal |

---

## References

- **Full documentation:** [DATA_SOURCES_REAL_VS_SIMULATED.md](DATA_SOURCES_REAL_VS_SIMULATED.md)
- **Quick reference:** [DATA_SOURCES_QUICK_CARD.md](DATA_SOURCES_QUICK_CARD.md)
- **Training script example:** [scripts/train/train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py) lines 193-333
- **Reward function:** [src/rewards/rewards.py](../src/rewards/rewards.py)

---

**Questions?** Check the parent documents or ask the team.
