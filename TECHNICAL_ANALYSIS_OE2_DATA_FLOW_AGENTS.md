# Technical Analysis Report: OE2 Data Flow to RL Agents

## pvbesscar Project - Agent Integration Analysis

**Date**: January 25, 2026  
**Scope**: Complete analysis of agent files in
`src/iquitos_citylearn/oe3/agents/`
**Objective**: Identify OE2 data connections, \
    type errors, data mismatches, and architectural issues

---

## Executive Summary

### Files Analyzed

<!-- markdownlint-disable MD013 -->
```bash
âœ“ __init__.py                    (Agent exports & device detection)
âœ“ sac.py                         (Soft Actor-Critic - 1,113 lines)
âœ“ ppo_sb3.py                     (Proximal Policy Optimization - 868 lines)
âœ“ a2c_sb3.py                     (Advantage Actor-Critic - 715 lines)
âœ“ agent_utils.py                 (Shared utilities - 189 lines)
âœ“ no_control.py                  (Baseline ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

<!-- markdownlint-disable MD013 -->
### Key Findings Summary | Category | Status | Severity | |----------|--------|----------| | **OE2 Data Connection** | âœ“ Indirect via CityLearn | Medium | | **128 Chargers Handling** | âœ“ Correct via wrapper flattening | Low | | **Solar Generation (8,760 hrs)** | âœ“ Loaded in... | Low | | **BESS (2MWh/1.2MW)** | âœ“ Via environment attribute access | Low | | **Type Errors** | âš  Minor issues in wrappers | Low | | **Data Mismatches** | âš  Pre-scaling hardcoded to 0.001 | Medium | | **Code Quality** | âœ“ Good modular design | Low | | **Architecture** | âœ“ Proper abstraction layers | Low | ---

## 1. DATA FLOW ANALYSIS: OE2 â†’ AGENTS

### 1.1 Data Connection Architecture

<!-- markdownlint-disable MD013 -->
```bash
<details>
<summary>â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”...</summary>

â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”

</details>
â”‚ OE2 ARTIFACTS (data/interim/oe2/)                              â”‚
<details>
<summary>â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”...</summary>

â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â...

</details>
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### 1.2 Connection Points Analysis

#### **SAC Agent** (sac.py)

**Data Intake**:

- Constructor: `__init__(env, config)` expects CityLearnEnv with schema
- No direct file reads; relies on environment providing observations
- Operates in two modes:
  1. **CityLearn native** (prefer_citylearn=True): Uses CityLearn's SAC
  2. **Stable-Baselines3** (default): Wraps env with `CityLearnWrapper`

**CityLearnWrapper (sac.py, lines 335-550)**:

<!-- markdownlint-disable MD013 -->
```python
def _get_pv_bess_feats(self):
    """Extract PV available & BESS SOC from environment"""
    t = getattr(self.env, "time_step", 0)  # Current timestep
    buildings = getattr(self.env, "buildings", [])
    for b in buildings:
        sg = getattr(b, "solar_generation", None)  # Array of 8,760 values
        if sg is not None and len(sg) > t:
            pv_kw += float(max(0.0, sg[t]))
        es =...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Accesses solar_generation[t] (8,760-element array from OE2
dataset)
**âœ“ Correct**: Accesses electrical_storage.state_of_charge (BESS parameter)  
**âš  Issue**: Silent failure if buildings/attributes missing (catches
AttributeError)

**Observation Flattening (sac.py, lines 545-560)**:

<!-- markdownlint-disable MD013 -->
```python
def _flatten(self, obs):
    base = self._flatten_base(obs)     # Flatten CityLearn obs (534 dims)
    feats = self._get_pv_bess_feats()  # Add [pv_kw, soc] (2 dims)
    arr = np.concatenate([base, feats])  # Total: 536 dims
    # Pad/trim to target obs_dim
    return self._normalize_observation(arr.astype(np.float32))
```bash
<!-- markdownlint-enable MD013 -->

**Normalization (sac.py, lines 510-...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**âš  CRITICAL ISSUE**: Hardcoded pre-scaling by 0.001 assumes:

- Solar generation in kW: 4,162 kWp â†’ 4.162 (after scaling)
- BESS: 2,000 kWh â†’ 2.0 (after scaling)
- Charger demand: 272 kW â†’ 0.272 (after scaling)

This is **dimensionally inconsistent** and **fragile** if data ranges change.

**Action Space (sac.py, lines ~515-525)**:

<!-- markdownlint-disable MD013 -->
```python
def _get_act_dim(self):
    if isinstance(self.env.action_space, list):
        return sum(sp.shape[0] for sp in self.env.action_space)
    return self.env.action_space.shape[0]
```bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Handles both list and \
    single action spaces; defaults to 126 (chargers)

---

#### **PPO Agent** (ppo_sb3.py)

**Data Intake**: Identical to SAC  
**CityLea...
```

[Ver código completo en GitHub]python
def _get_act_dim(self):
    action_space = getattr(self.env, "action_space", None)
    if isinstance(action_space, list):
        return sum(sp.shape[0] for sp in action_space)
    if action_space is not None and hasattr(action_space, "shape"):
        return int(action_space.shape[0])
    return 126  # Default fallback
```bash
<!-- markdownlint-enable MD013 -->

**âš TYPE ERROR**: Uses `getattr()`but doesn't handle missing action_space
gracefully
**âœ“ Good**: Has fallback to 126

---

#### **A2C Agent** (a2c_sb3.py)

**CityLearnWrapper (lines 65-350)**: Nearly identical to PPO/SAC  
**Key additions**:

<!-- markdownlint-disable MD013 -->
```python
def _get_pv_bess_feats(self):  # Line 185-200
    pv_kw = 0.0
    soc = ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**âœ“ Better**: Explicit exception handling with debug logging

**Issue in A2C (line 270)**:

<!-- markdownlint-disable MD013 -->
```python
def _get_act_dim(self):
    action_space = getattr(self.env, "action_space", None)
    if isinstance(action_space, list):
        return sum(sp.shape[0] for sp in action_space)
    if action_space is not None and hasattr(action_space, "shape"):
        return int(action_space.shape[0])
    return 126  # Default to 126 charger actions as fallback
```bash
<!-- markdownlint-enable MD013 -->

**âš TYP...
```

[Ver código completo en GitHub]bash
32 physical chargers Ã— 4 sockets = 128 controllable outlets
â”œâ”€ Playa Motos: 28 chargers Ã— 4 sockets Ã— 2.0 kW = 224 kW
â””â”€ Playa Mototaxis: 4 chargers Ã— 4 sockets Ã— 3.0 kW = 48 kW
Total: 272 kW installed
```bash
<!-- markdownlint-enable MD013 -->

**Agent Action Space Definition**:

In **SAC wrapper** (sac.py, lines 515-520):

<!-- markdownlint-disable MD013 -->
```python
self.action_space = gym.spaces.Box(
    low=-1.0, high=1.0,
    shape=(self.act_dim,), dtype=np.float32
)
# act_dim = 126 (from _get_act_dim())
```bash
<!-- markdownlint-enable MD013 -->

**âš  DISCREPANCY**: Config defines 126 controlla...
```

[Ver código completo en GitHub]python
def _unflatten_action(self, action):
    """Convert flat 126-dim action back to CityLearn list format"""
    if isinstance(self.env.action_space, list):
        result = []
        idx = 0
        for sp in self.env.action_space:
            dim = sp.shape[0]
            result.append(action[idx:idx + dim].tolist())
            idx += dim
        return result
    return [action.tolist()]
```bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Handles both flat and list action spaces  
**âœ“ Correct**: Returns list of actions compatible with CityLearn

### 2.3 Charger Feature Extraction

**RBC Agent (rbc.py)** provides explicit charger handling:

<!-- markdownlint-disable MD013 -->
```python
# Configuration
n_chargers: int = 128
sockets_per_charger: int = 1  # Actually 4, but treated ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Issue**: Treats "4 sockets per charger" but charger_power_kw is averaged  
**Better approach**: Model chargers as individual control units (already done
in 126-dim action space)

### 2.4 Charger Observation Features

**Currently**: Charger state embedded in CityLearn's base observation (534 dims)  
**Not explicitly extracted**: Per-charger power, occupancy, or battery level  
**Consequence**: Agent must infer charger states from aggregated observation

**Improvement**: Could add per-charger features to observation (128 more dims):

<!-- markdownlint-disable MD013 -->
```python
charger_demands = \
    [building.electric_vehicle[i].power_demand for i in range(128)]
charger_available = \
    [building.electric_vehicle[i].available_battery_capacity for i in range(128)]
# Add to observation: obs_extended = np.concatenate([obs, charger_demands,
# charger_available])
```bash
<!-- markdownlint-enable MD013 -->

---

## 3. SOLAR GENERATION (8,760 Hourly Values) HANDLING

### 3.1...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Loading in dataset_builder.py** (lines 195-210):

<!-- markdownlint-disable MD013 -->
```python
def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    # Solar timeseries
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = pd.read_csv(solar_path)  # Shape: (8760, 1)
    
    # Optional: CityLearn solar generation CSV
    solar_citylearn_csv = interim_dir / "oe2" / "citylearn" / "solar_generation...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Loads both raw OE2 timeseries and CityLearn-formatted version

### 3.2 Runtime Access in Agents

**Wrapper method (all agents, lines ~180-200)**:

<!-- markdownlint-disable MD013 -->
```python
def _get_pv_bess_feats(self):
    """Extract current PV generation from environment"""
    pv_kw = 0.0
    try:
        t = getattr(self.env, "time_step", 0)        # Current hour (0-8759)
        buildings = getattr(self.env, "buildings", [])
        for b in buildings:
            sg = getattr(b, "solar_generation", None)  # Array: [8760]
            if sg is not None and len(sg) > t:
          ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Accesses `solar_generation[t]` at each timestep  
**âœ“ Correct**: Handles multiple buildings (aggregates PV across all)  
**âœ“ Safe**: Silent fail if solar_generation not available

### 3.3 Observation Normalization Impact

**Critical issue**: Solar generation (0-4162 kW) scaled by 0.001:

<!-- markdownlint-disable MD013 -->
```bash
4162 kW â†’ 4.162 (after prescaling)
â†’ Normalized: (4.162 - mean) / std
â†’ Clipped: [-10, 10]
```bash
<!-- markdownlint-enable MD013 -->

**Problem**: If mean/std computed over full year:

- Mean ~1500 kW (accounting for nighttime zeros)
- Std ~1200 kW
- â†’ Normalized midday: (4162 - 1500) / 1200 â‰ˆ 2.22 (good)
- â†’ Normalized night: (0 - 1500) / 1200 â‰ˆ -1.25 (good)

**Analysis**: Pre-scal...
```

[Ver código completo en GitHub]python
def compute(self, grid_import_kwh, solar_generation_kwh, ...):
    # Solar self-consumption bonus
    if solar_generation_kwh > 0:
        solar_score = pv_used_directly / (solar_generation_kwh + 0.1)
        reward += weights.solar * solar_score  # weight = 0.20
```bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Rewards direct use of solar (avoiding battery/grid
inefficiency)
**âœ“ Correct**: Normalized to [0, 1]

---

## 4. BESS (2 MWh / 1.2 MW) HANDLING

### 4.1 BESS Configuration

**OE2 Specification**:

<!-- markdownlint-disable MD013 -->
```json
{
  "capacity_kwh": 2000,
  "power_kw": 1200,
  "efficiency_round_trip": 0.95,
  "depth_of_discharge": 0...
```

[Ver código completo en GitHub]python
es = getattr(b, "electrical_storage", None)  # Get BESS object
if es is not None:
    soc = float(getattr(es, "state_of_charge", soc))  # SOC in [0, 1]
```bash
<!-- markdownlint-enable MD013 -->

**âœ“ Correct**: Accesses electrical_storage.state_of_charge at each timestep

### 4.3 BESS in Observation

**Feature vector includes**:

<!-- markdownlint-disable MD013 -->
```python
return np.array([pv_kw, soc], dtype=np.float32)
# pv_kw: 0 - 4162 kW
# soc: 0 - 1.0
```bash
<!-- markdownlint-enable MD013 -->

**After prescaling by 0.001**:

<!-- markdownlint-di...
```

[Ver código completo en GitHub]python
# Use different prescaling for SOC
self._obs_prescale_soc = 1.0  # Keep SOC as-is
return np.array([pv_kw * 0.001, soc * 1.0], dtype=np.float32)
```bash
<!-- markdownlint-enable MD013 -->

### 4.4 BESS in Reward Function

**From rewards.py**:

<!-- markdownlint-disable MD013 -->
```python
# BESS used in multi-objective reward calculation
# But no explicit BESS penalty for over/under-discharge
# BESS control is implicit: SOC in observation guides policy
```bash
<!-- markdownlint-enable MD013 -->

**Gap**: No explicit reward term for BESS health (Do...
```

[Ver código completo en GitHub]python
# In all CityLearnWrapper classes
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001
# Set BESS SOC (usually last 2 elements) to 1.0
self._obs_prescale[-2] = 1.0  # Assuming [pv_kw, soc] at end

# OR better: separate feature groups
def _get_pv_bess_feats(self):
    return np.array([pv_kw * 0.001, soc * 1.0], dtype=np.float32)
```bash
<!-- markdownlint-enable MD013 -->

**Impact**: Allow agent to properly observe BESS state

---

**Issue**: Hardcoded prescale constants (0.001) not documented or configurable

**Fix**: Add prescaling to agent config

<!-- markdownlint-disable MD013 -->
```python
@dataclass
class SACConfig:
    # ... existing ...
    obs_prescale_pv: float = 0.001      # PV generation scaling
    obs_prescale_powe...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Impact**: Make normalization strategy explicit and tunable

---

### 7.2 Medium Priority (Improve Within 1-2 Weeks)

**Issue**: 300+ lines of wrapper code duplicated in SAC/PPO/A2C

**Fix**: Extract CityLearnWrapper to `agent_utils.py`

<!-- markdownlint-disable MD013 -->
```python
# src/iquitos_citylearn/oe3/agents/agent_utils.py

class CityLearnWrapper(gym.Wrapper):
    """Generic wrapper for CityLearn compatibility"""
    # Consolidate all wrapper logic here
    # Use from sac.py, ppo_sb3.py, a2c_sb3.py
```bash
<!-- markdownlint-enable MD013 -->

**Impact**: Easier maintenance, consistent behavior across agents

---

**Issue**: No validation of OE2 artifacts

**Fix**: Add...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Impact**: Catch configuration errors early

---

**Issue**: No per-charger state features in observation

**Fix**: Add optional per-charger extension

<!-- markdownlint-disable MD013 -->
```python
# In CityLearnWrapper

def _get_charger_feats(self):
    """Extract per-charger demand/occupancy"""
    charger_feats = np.zeros(128, dtype=np.float32)  # Demand per charger
    try:
        t = getattr(self.env, "time_step", 0)
        buildings = getattr(self.env, "buildings", [])
        for b in buildings:
            evs = getattr(b, "electric_vehicle", [])
            for i, ev in enumerate(...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Impact**: Richer observation space; agent can learn per-charger control

---

### 7.3 Low Priority (Nice to Have)

**Issue**: RBC and baseline agents not fully integrated

**Recommendation**: Add comparison script

<!-- markdownlint-disable MD013 -->
```bash
# scripts/compare_all_agents.py
python compare_all_agents.py \
  --episodes 2 \
  --agents NoControl UncontrolledCharging RBC SAC PPO A2C \
  --output analyses/comparison_all_agents.csv
```bash
<!-- markdownlint-enable MD013 -->

**Output**: COâ‚‚, cost, peak load, solar use for each agent

---

**Issue**: No explicit BESS health tracking

**Recommendation**: Add BESS cycling penalty to reward

<!...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 8. DATA FLOW VERIFICATION CHECKLIST

### OE2 â†’ CityLearn Schema

- [x] Solar timeseries (8,760 rows) loaded from CSV
- [x] Charger profiles (24h + annual variants) loaded from JSON/CSV
- [x] BESS config (2 MWh / 1.2 MW) loaded from JSON
- [x] Building load aggregated and included in schema
- [x] Carbon intensity (0.4521 kg COâ‚‚/kWh) hardcoded for Iquitos

### CityLearn Schema â†’ Agent Observation

- [x] Solar generation accessed via `building.solar_generation[t]`
- [x] BESS SOC accessed via `building.electrical_storage.state_of_charge`
- [x] Charger demands accessed via CityLearn's base observation
- [âš ] Observation normalization uses hardcoded prescaling (0.001)
- [âš ] BESS SOC normalization not optimized

### Agent Action â†’ CityLearn Control

- [x] 126 continuous actions mapped to charger power setpoints [0, 1]
- [x] Action unflattening handles both single and list action spaces
- [x] Actions clipped to [-1, 1] for legal input to gym.Box

---

## 9. CONCLUSION

### Summary

The OE2 data flow to agents is **architecturally sound** but has **critical
<!-- markdownlint-disable MD013 -->
tuning issues**: | Aspect | Status | Risk | |--------|--------|------| | Data connection | âœ“ Correct | Low | | 128 chargers | âœ“ Correct (126 controllable) | Low | | Solar (8,760 hrs) | âœ“ Correct | Medium (prescaling hardcoded) | | BESS (2MWh/1.2MW) | âš  Partially correct | **High** (SOC not observable) | | Type safety | âš  Duck typing | Low | | Code quality | âœ“ Good (except duplication) | Medium | | Architectural | âœ“ Excellent abstraction | Low | ### Critical Issues to Address

1. **BESS SOC prescaling by 0.001** â†’ Makes SOC invisible in normalized space
2. **Hardcoded 0.001 prescaling** â†’ Fragile if data ranges change
3. **Wrapper code duplication** â†’ Maintenance burden (300+ lines Ã— 3)
4. **No OE2 validation** â†’ Silent failures if artifacts missing

### Next Steps

1. **Immediate**: Fix BESS SOC scaling (use 1.0 instead of 0.001)
2. **This week**: Extract wrapper to `agent_utils.py` for DRY principle
3. **Next week**: Add OE2 artifact validation
4. **Optional**: Extend observation with per-charger states

---

<!-- markdownlint-disable MD013 -->
## 10. APPENDIX: File Reference | File | Purpose | Lines | Status | |------|---------|-------|--------| | `__init__.py` | Exports + device detection | 75 | âœ“ Clean | | `sac.py` | SAC agent (SB3 + CityLearn) | 1,113 | âš  Hardcoded params | | `ppo_sb3.py` | PPO agent | 868 | âš  Hardcoded params | | `a2c_sb3.py` | A2C agent | 715 | âš  Hardcoded params | | `agent_utils.py` | Shared utilities | 189 | âœ“ Light | | `no_control.py` | Zero action baseline | ~50 | âœ“ Simple | | `uncontrolled.py` | EV-max baseline | ~60 | âœ“ Simple | | `rbc.py` | Rule-based controller | 320 | âœ“ Good | | `validate_training_env.py` | Pre-training checks | 137 | âœ“ Useful | ---

<!-- markdownlint-disable MD013 -->
 **Report Generated**: 2026-01-25 | **Python 3.11** | **stable-baselines3 1.8+** 
