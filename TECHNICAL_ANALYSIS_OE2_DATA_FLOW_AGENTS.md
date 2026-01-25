# Technical Analysis Report: OE2 Data Flow to RL Agents

## pvbesscar Project - Agent Integration Analysis

**Date**: January 25, 2026  
**Scope**: Complete analysis of agent files in `src/iquitos_citylearn/oe3/agents/`  
**Objective**: Identify OE2 data connections, type errors, data mismatches, and architectural issues

---

## Executive Summary

### Files Analyzed

```bash
âœ“ __init__.py                    (Agent exports & device detection)
âœ“ sac.py                         (Soft Actor-Critic - 1,113 lines)
âœ“ ppo_sb3.py                     (Proximal Policy Optimization - 868 lines)
âœ“ a2c_sb3.py                     (Advantage Actor-Critic - 715 lines)
âœ“ agent_utils.py                 (Shared utilities - 189 lines)
âœ“ no_control.py                  (Baseline agent)
âœ“ uncontrolled.py                (Uncontrolled EV charging baseline)
âœ“ rbc.py                         (Rule-based controller - 320 lines)
âœ“ validate_training_env.py       (Pre-training validation - 137 lines)
```bash

### Key Findings Summary

| Category | Status | Severity |
|----------|--------|----------|
| **OE2 Data Connection** | âœ“ Indirect via CityLearn | Medium |
| **128 Chargers Handling** | âœ“ Correct via wrapper flattening | Low |
| **Solar Generation (8,760 hrs)** | âœ“ Loaded in wrapper, used in feature extraction | Low |
| **BESS (2MWh/1.2MW)** | âœ“ Via environment attribute access | Low |
| **Type Errors** | âš  Minor issues in wrappers | Low |
| **Data Mismatches** | âš  Pre-scaling hardcoded to 0.001 | Medium |
| **Code Quality** | âœ“ Good modular design | Low |
| **Architecture** | âœ“ Proper abstraction layers | Low |

---

## 1. DATA FLOW ANALYSIS: OE2 â†’ AGENTS

### 1.1 Data Connection Architecture

```bash
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ OE2 ARTIFACTS (data/interim/oe2/)                              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ â”œâ”€ solar/pv_generation_timeseries.csv     (8,760 rows Ã— 1 col) â”‚
â”‚ â”œâ”€ chargers/individual_chargers.json      (32 chargers Ã— 4)    â”‚
â”‚ â”œâ”€ chargers/perfil_horario_carga.csv      (24h demand profile) â”‚
â”‚ â”œâ”€ chargers/annual_datasets/               (Playa_Motos/Mototaxis)
â”‚ â””â”€ bess/bess_results.json                 (2 MWh / 1.2 MW)     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ DATASET BUILDER (src/iquitos_citylearn/oe3/dataset_builder.py)  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ âœ“ Loads OE2 artifacts from interim_dir                          â”‚
â”‚ âœ“ Enriches observables (adds solar, charger profiles)           â”‚
â”‚ âœ“ Builds CityLearn schema.json                                  â”‚
â”‚ âœ“ Generates energy_simulation.csv & charger_simulation_*.csv    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ CityLearn v2 Environment (data/processed/citylearnv2_dataset/)  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ â”œâ”€ schema.json (contains all building/charger/energy configs)  â”‚
â”‚ â”œâ”€ climate_zones/weather.csv                                   â”‚
â”‚ â”œâ”€ buildings/energy_simulation.csv        (aggregated load)    â”‚
â”‚ â””â”€ buildings/charger_simulation_0-127.csv (per-charger 8760)   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚
                     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ RL AGENTS (src/iquitos_citylearn/oe3/agents/*.py)               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ â”œâ”€ SAC/PPO/A2C: CityLearnWrapper extracts obs at runtime      â”‚
â”‚ â”œâ”€ Wrapper._get_pv_bess_feats(): Reads from env.buildings     â”‚
â”‚ â”œâ”€ Flattens 128 charger actions â†’ 126 controllable actions    â”‚
â”‚ â””â”€ Normalizes obs & rewards (key source of data mismatches)   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```bash

### 1.2 Connection Points Analysis

#### **SAC Agent** (sac.py)

**Data Intake**:

- Constructor: `__init__(env, config)` expects CityLearnEnv with schema
- No direct file reads; relies on environment providing observations
- Operates in two modes:
  1. **CityLearn native** (prefer_citylearn=True): Uses CityLearn's SAC
  2. **Stable-Baselines3** (default): Wraps env with `CityLearnWrapper`

**CityLearnWrapper (sac.py, lines 335-550)**:

```python
def _get_pv_bess_feats(self):
    """Extract PV available & BESS SOC from environment"""
    t = getattr(self.env, "time_step", 0)  # Current timestep
    buildings = getattr(self.env, "buildings", [])
    for b in buildings:
        sg = getattr(b, "solar_generation", None)  # Array of 8,760 values
        if sg is not None and len(sg) > t:
            pv_kw += float(max(0.0, sg[t]))
        es = getattr(b, "electrical_storage", None)  # BESS object
        if es is not None:
            soc = float(getattr(es, "state_of_charge", soc))
    return np.array([pv_kw, soc], dtype=np.float32)
```bash

**âœ“ Correct**: Accesses solar_generation[t] (8,760-element array from OE2 dataset)  
**âœ“ Correct**: Accesses electrical_storage.state_of_charge (BESS parameter)  
**âš  Issue**: Silent failure if buildings/attributes missing (catches AttributeError)

**Observation Flattening (sac.py, lines 545-560)**:

```python
def _flatten(self, obs):
    base = self._flatten_base(obs)     # Flatten CityLearn obs (534 dims)
    feats = self._get_pv_bess_feats()  # Add [pv_kw, soc] (2 dims)
    arr = np.concatenate([base, feats])  # Total: 536 dims
    # Pad/trim to target obs_dim
    return self._normalize_observation(arr.astype(np.float32))
```bash

**Normalization (sac.py, lines 510-525)**:

```python
# PRE-ESCALADO: hardcoded divide by 1000
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001

def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
    prescaled = obs * self._obs_prescale  # Divide all by 1000
    normalized = (prescaled - self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
    clipped = np.clip(normalized, -self._clip_obs, self._clip_obs)
    return np.asarray(clipped, dtype=np.float32)
```bash

**âš  CRITICAL ISSUE**: Hardcoded pre-scaling by 0.001 assumes:

- Solar generation in kW: 4,162 kWp â†’ 4.162 (after scaling)
- BESS: 2,000 kWh â†’ 2.0 (after scaling)
- Charger demand: 272 kW â†’ 0.272 (after scaling)

This is **dimensionally inconsistent** and **fragile** if data ranges change.

**Action Space (sac.py, lines ~515-525)**:

```python
def _get_act_dim(self):
    if isinstance(self.env.action_space, list):
        return sum(sp.shape[0] for sp in self.env.action_space)
    return self.env.action_space.shape[0]
```bash

**âœ“ Correct**: Handles both list and single action spaces; defaults to 126 (chargers)

---

#### **PPO Agent** (ppo_sb3.py)

**Data Intake**: Identical to SAC  
**CityLearnWrapper**: Nearly identical implementation (lines 220-400)  
**Key difference**: Uses GAE (Generalized Advantage Estimation)

**Issue in CityLearnWrapper (ppo_sb3.py, line 290)**:

```python
def _get_act_dim(self):
    action_space = getattr(self.env, "action_space", None)
    if isinstance(action_space, list):
        return sum(sp.shape[0] for sp in action_space)
    if action_space is not None and hasattr(action_space, "shape"):
        return int(action_space.shape[0])
    return 126  # Default fallback
```bash

**âš  TYPE ERROR**: Uses `getattr()` but doesn't handle missing action_space gracefully  
**âœ“ Good**: Has fallback to 126

---

#### **A2C Agent** (a2c_sb3.py)

**CityLearnWrapper (lines 65-350)**: Nearly identical to PPO/SAC  
**Key additions**:

```python
def _get_pv_bess_feats(self):  # Line 185-200
    pv_kw = 0.0
    soc = 0.0
    try:
        t = getattr(self.env, "time_step", 0)
        buildings = getattr(self.env, "buildings", [])
        for b in buildings:
            sg = getattr(b, "solar_generation", None)
            if sg is not None and len(sg) > t:
                pv_kw += float(max(0.0, sg[t]))
            es = getattr(b, "electrical_storage", None)
            if es is not None:
                soc = float(getattr(es, "state_of_charge", soc))
    except (AttributeError, TypeError, IndexError, ValueError) as err:
        logger.debug("Error extracting PV/BESS features: %s", err)
    return np.array([pv_kw, soc], dtype=np.float32)
```bash

**âœ“ Better**: Explicit exception handling with debug logging

**Issue in A2C (line 270)**:

```python
def _get_act_dim(self):
    action_space = getattr(self.env, "action_space", None)
    if isinstance(action_space, list):
        return sum(sp.shape[0] for sp in action_space)
    if action_space is not None and hasattr(action_space, "shape"):
        return int(action_space.shape[0])
    return 126  # Default to 126 charger actions as fallback
```bash

**âš  TYPE ERROR**: Comment says "126 charger actions" but config defines **126 controllable out of 128** (2 reserved)

---

### 1.3 OE2 Parameters in Agent Configs

All three agents (SAC/PPO/A2C) embed OE2 parameters in dataclass configs:

| Parameter | SAC | PPO | A2C | OE2 Spec | Status |
|-----------|-----|-----|-----|----------|--------|
| `co2_target_kg_per_kwh` | 0.4521 | 0.4521 | 0.4521 | âœ“ Correct (Iquitos thermal) | âœ“ |
| `cost_target_usd_per_kwh` | 0.20 | 0.20 | 0.20 | âœ“ Correct | âœ“ |
| `ev_soc_target` | 0.90 | 0.90 | 0.90 | âœ“ Correct | âœ“ |
| `peak_demand_limit_kw` | 200.0 | 200.0 | 200.0 | âœ“ Reasonable (272 kW total) | âœ“ |
| (No charger count) | â€” | â€” | â€” | âš  Missing | âš  |
| (No BESS capacity) | â€” | â€” | â€” | âš  Missing | âš  |

---

## 2. 128 CHARGERS HANDLING ANALYSIS

### 2.1 Charger Action Space

**OE2 Specification**:

```bash
32 physical chargers Ã— 4 sockets = 128 controllable outlets
â”œâ”€ Playa Motos: 28 chargers Ã— 4 sockets Ã— 2.0 kW = 224 kW
â””â”€ Playa Mototaxis: 4 chargers Ã— 4 sockets Ã— 3.0 kW = 48 kW
Total: 272 kW installed
```bash

**Agent Action Space Definition**:

In **SAC wrapper** (sac.py, lines 515-520):

```python
self.action_space = gym.spaces.Box(
    low=-1.0, high=1.0,
    shape=(self.act_dim,), dtype=np.float32
)
# act_dim = 126 (from _get_act_dim())
```bash

**âš  DISCREPANCY**: Config defines 126 controllable actions but OE2 has 128 sockets  
**âœ“ Correct interpretation**: 2 chargers reserved for baseline comparison (128 - 2 = 126)

### 2.2 Action Unflattening

**SAC wrapper (sac.py, lines ~560-570)**:

```python
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

**âœ“ Correct**: Handles both flat and list action spaces  
**âœ“ Correct**: Returns list of actions compatible with CityLearn

### 2.3 Charger Feature Extraction

**RBC Agent (rbc.py)** provides explicit charger handling:

```python
# Configuration
n_chargers: int = 128
sockets_per_charger: int = 1  # Actually 4, but treated as combined unit
charger_power_kw: float = 2.125  # Average: (224 + 48) / 128

# Charger action distribution (lines 140-180)
def _distribute_charging_load(self, available_power, n_active_chargers):
    rates = np.zeros(self.config.n_chargers)
    power_per_charger = self.config.charger_power_kw * self.config.sockets_per_charger
    # Round-robin, solar-priority, or sequential distribution
    # Returns 128-dim array of charge rates [0, 1]
```bash

**Issue**: Treats "4 sockets per charger" but charger_power_kw is averaged  
**Better approach**: Model chargers as individual control units (already done in 126-dim action space)

### 2.4 Charger Observation Features

**Currently**: Charger state embedded in CityLearn's base observation (534 dims)  
**Not explicitly extracted**: Per-charger power, occupancy, or battery level  
**Consequence**: Agent must infer charger states from aggregated observation

**Improvement**: Could add per-charger features to observation (128 more dims):

```python
charger_demands = [building.electric_vehicle[i].power_demand for i in range(128)]
charger_available = [building.electric_vehicle[i].available_battery_capacity for i in range(128)]
# Add to observation: obs_extended = np.concatenate([obs, charger_demands, charger_available])
```bash

---

## 3. SOLAR GENERATION (8,760 Hourly Values) HANDLING

### 3.1 Data Loading Path

**OE2 Dataset**:

```bash
data/interim/oe2/solar/pv_generation_timeseries.csv
â”œâ”€ Format: 8,760 rows Ã— 1 column
â”œâ”€ Values: Hourly AC output (kW) from Kyocera KS20 + Eaton Xpert1670
â”œâ”€ Range: 0 - 4,162 kW (peak at noon)
â””â”€ Profile: 05:00-17:00 Iquitos time (UTC-5)
```bash

**Loading in dataset_builder.py** (lines 195-210):

```python
def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    # Solar timeseries
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        artifacts["solar_ts"] = pd.read_csv(solar_path)  # Shape: (8760, 1)
    
    # Optional: CityLearn solar generation CSV
    solar_citylearn_csv = interim_dir / "oe2" / "citylearn" / "solar_generation.csv"
    if solar_citylearn_csv.exists():
        artifacts["solar_generation_citylearn"] = pd.read_csv(solar_citylearn_csv)
    
    return artifacts
```bash

**âœ“ Correct**: Loads both raw OE2 timeseries and CityLearn-formatted version

### 3.2 Runtime Access in Agents

**Wrapper method (all agents, lines ~180-200)**:

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
                pv_kw += float(max(0.0, sg[t]))      # Access sg[t]
    except Exception:
        pass
    return np.array([pv_kw, soc], dtype=np.float32)
```bash

**âœ“ Correct**: Accesses `solar_generation[t]` at each timestep  
**âœ“ Correct**: Handles multiple buildings (aggregates PV across all)  
**âœ“ Safe**: Silent fail if solar_generation not available

### 3.3 Observation Normalization Impact

**Critical issue**: Solar generation (0-4162 kW) scaled by 0.001:

```bash
4162 kW â†’ 4.162 (after prescaling)
â†’ Normalized: (4.162 - mean) / std
â†’ Clipped: [-10, 10]
```bash

**Problem**: If mean/std computed over full year:

- Mean ~1500 kW (accounting for nighttime zeros)
- Std ~1200 kW
- â†’ Normalized midday: (4162 - 1500) / 1200 â‰ˆ 2.22 (good)
- â†’ Normalized night: (0 - 1500) / 1200 â‰ˆ -1.25 (good)

**Analysis**: Pre-scaling by 0.001 **appears reasonable** but:

- Depends on running stats initialization (starts with mean=0, var=1)
- First few hours will have normalized values >> 10 (clipped)
- Stabilizes after ~100 timesteps

### 3.4 Solar Usage in Reward Function

**From rewards.py** (lines ~200-250):

```python
def compute(self, grid_import_kwh, solar_generation_kwh, ...):
    # Solar self-consumption bonus
    if solar_generation_kwh > 0:
        solar_score = pv_used_directly / (solar_generation_kwh + 0.1)
        reward += weights.solar * solar_score  # weight = 0.20
```bash

**âœ“ Correct**: Rewards direct use of solar (avoiding battery/grid inefficiency)  
**âœ“ Correct**: Normalized to [0, 1]

---

## 4. BESS (2 MWh / 1.2 MW) HANDLING

### 4.1 BESS Configuration

**OE2 Specification**:

```json
{
  "capacity_kwh": 2000,
  "power_kw": 1200,
  "efficiency_round_trip": 0.95,
  "depth_of_discharge": 0.80,
  "soc_min": 0.10,
  "soc_max": 0.90
}
```bash

### 4.2 BESS Access in Agents

**Wrapper feature extraction**:

```python
es = getattr(b, "electrical_storage", None)  # Get BESS object
if es is not None:
    soc = float(getattr(es, "state_of_charge", soc))  # SOC in [0, 1]
```bash

**âœ“ Correct**: Accesses electrical_storage.state_of_charge at each timestep

### 4.3 BESS in Observation

**Feature vector includes**:

```python
return np.array([pv_kw, soc], dtype=np.float32)
# pv_kw: 0 - 4162 kW
# soc: 0 - 1.0
```bash

**After prescaling by 0.001**:

```bash
[pv_kw * 0.001, soc * 0.001]
â†’ [0 - 4.162, 0 - 0.001]
```bash

**âš  CRITICAL MISMATCH**:

- PV is scaled to ~1-4 range (reasonable)
- **BESS SOC is scaled to 0.001-1 range (unreasonably small)**
- Normalized SOC will collapse to near-zero in normalized space

**Impact**: Agent cannot distinguish between BESS states effectively

**Recommended fix**:

```python
# Use different prescaling for SOC
self._obs_prescale_soc = 1.0  # Keep SOC as-is
return np.array([pv_kw * 0.001, soc * 1.0], dtype=np.float32)
```bash

### 4.4 BESS in Reward Function

**From rewards.py**:

```python
# BESS used in multi-objective reward calculation
# But no explicit BESS penalty for over/under-discharge
# BESS control is implicit: SOC in observation guides policy
```bash

**Gap**: No explicit reward term for BESS health (DoD, cycling)  
**Current approach**: Relies on agent learning to maintain SOC within [0.1, 0.9]

---

## 5. IDENTIFIED ISSUES

### 5.1 Type Errors

| File | Location | Issue | Severity |
|------|----------|-------|----------|
| ppo_sb3.py | Line 290 | `_get_act_dim()` returns `int` but used as `shape[0]` | Low |
| a2c_sb3.py | Line 270 | Same as above | Low |
| sac.py | Line 515-525 | `_obs_prescale` is float array but applied element-wise | Low |
| All wrappers | Lines ~180-200 | `getattr()` without type checking before `.shape[]` | Low |

**Assessment**: Type errors are **not fatal** due to duck typing in NumPy

---

### 5.2 Data Mismatches

| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| Hardcoded prescale 0.001 | All wrappers | Assumes specific data ranges (PV, power) | **HIGH** |
| BESS SOC prescaled by 0.001 | All wrappers | Makes SOC near-zero in normalized space | **HIGH** |
| No per-charger state features | All agents | Agent cannot distinguish individual charger demands | **MEDIUM** |
| 126 vs 128 chargers not documented | Config docstrings | Confusion about controllable vs total chargers | **MEDIUM** |
| Silent failures in feature extraction | All wrappers | Missing buildings/storage attributes silently ignored | **MEDIUM** |

---

### 5.3 Code Quality Issues

| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| Inconsistent exception handling | All wrappers | Some use try/except, others use getattr() | Low |
| Magic numbers (0.001, 1000) | All wrappers | Hardcoded assumptions not documented | Medium |
| No validation of OE2 data | dataset_builder.py | Silent failures if solar/charger files missing | Medium |
| Duplicate wrapper code | sac.py, ppo_sb3.py, a2c_sb3.py | 300+ lines copied; maintenance burden | Medium |

---

## 6. ARCHITECTURAL ASSESSMENT

### 6.1 Strengths

1. **Proper abstraction layers**
   - OE2 data â†’ Dataset builder â†’ CityLearn schema â†’ Agent wrappers
   - Clean separation of concerns

2. **Multiple agent implementations**
   - SAC (off-policy), PPO (on-policy), A2C (simpler baseline)
   - Allows empirical comparison

3. **Flexible GPU support**
   - Auto-detection of CUDA/MPS/CPU
   - Mixed precision training option
   - Proper device setup in config

4. **Multi-objective rewards**
   - Weight-based combination of COâ‚‚, cost, solar, EV, grid objectives
   - Normalized components
   - Configurable thresholds

5. **Robust baselines**
   - NoControl (zero actions)
   - UncontrolledCharging (EV max, BESS inactive)
   - RBC (rule-based controller for comparison)

### 6.2 Weaknesses

1. **Tightly coupled to CityLearn**
   - Heavy dependency on specific environment API
   - Difficult to test without full environment

2. **Data normalization hardcoded**
   - Prescaling constants (0.001) embedded in wrapper classes
   - Not parameterizable
   - Fragile to data range changes

3. **No explicit OE2 validation**
   - Dataset builder doesn't validate charger count, solar length
   - No warnings if artifacts missing
   - Agents fail silently

4. **Incomplete charger modeling**
   - 128 chargers â†’ 126 actions (2 reserved)
   - Reservation logic not documented
   - No per-charger state features

5. **BESS modeling simplistic**
   - Only SOC in observation
   - No power constraints (1.2 MW)
   - No efficiency/temperature factors

---

## 7. RECOMMENDATIONS

### 7.1 High Priority (Fix Immediately)

**Issue**: BESS SOC prescaled by 0.001 (makes it invisible in normalized space)

**Fix**: Use separate prescaling for BESS

```python
# In all CityLearnWrapper classes
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001
# Set BESS SOC (usually last 2 elements) to 1.0
self._obs_prescale[-2] = 1.0  # Assuming [pv_kw, soc] at end

# OR better: separate feature groups
def _get_pv_bess_feats(self):
    return np.array([pv_kw * 0.001, soc * 1.0], dtype=np.float32)
```bash

**Impact**: Allow agent to properly observe BESS state

---

**Issue**: Hardcoded prescale constants (0.001) not documented or configurable

**Fix**: Add prescaling to agent config

```python
@dataclass
class SACConfig:
    # ... existing ...
    obs_prescale_pv: float = 0.001      # PV generation scaling
    obs_prescale_power: float = 0.001   # Power/load scaling
    obs_prescale_soc: float = 1.0       # SOC scaling (keep as-is)
    obs_prescale_cost: float = 1.0      # Cost/tariff scaling
```bash

**Impact**: Make normalization strategy explicit and tunable

---

### 7.2 Medium Priority (Improve Within 1-2 Weeks)

**Issue**: 300+ lines of wrapper code duplicated in SAC/PPO/A2C

**Fix**: Extract CityLearnWrapper to `agent_utils.py`

```python
# src/iquitos_citylearn/oe3/agents/agent_utils.py

class CityLearnWrapper(gym.Wrapper):
    """Generic wrapper for CityLearn compatibility"""
    # Consolidate all wrapper logic here
    # Use from sac.py, ppo_sb3.py, a2c_sb3.py
```bash

**Impact**: Easier maintenance, consistent behavior across agents

---

**Issue**: No validation of OE2 artifacts

**Fix**: Add validation function

```python
# src/iquitos_citylearn/oe3/dataset_builder.py

def validate_oe2_artifacts(artifacts: Dict) -> Tuple[bool, List[str]]:
    """Validate that all required OE2 artifacts are present and correct"""
    errors = []
    
    # Check solar
    if "solar_ts" not in artifacts:
        errors.append("Missing: pv_generation_timeseries.csv")
    elif len(artifacts["solar_ts"]) != 8760:
        errors.append(f"Solar timeseries has {len(artifacts['solar_ts'])} rows, expected 8760")
    
    # Check chargers
    if "ev_chargers" in artifacts:
        n_chargers = len(artifacts["ev_chargers"])
        n_sockets = n_chargers * 4
        if n_sockets != 128:
            errors.append(f"Chargers have {n_sockets} sockets, expected 128 (32 Ã— 4)")
    
    # Check BESS
    if "bess" in artifacts:
        bess = artifacts["bess"]
        if bess.get("capacity_kwh") != 2000:
            errors.append(f"BESS capacity {bess['capacity_kwh']} kWh, expected 2000")
    
    return len(errors) == 0, errors
```bash

**Impact**: Catch configuration errors early

---

**Issue**: No per-charger state features in observation

**Fix**: Add optional per-charger extension

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
            for i, ev in enumerate(evs[:128]):
                demand = getattr(ev, "power_demand", [])
                if len(demand) > t:
                    charger_feats[i] = float(max(0, demand[t]))
    except Exception:
        pass
    return charger_feats

def _flatten(self, obs):
    base = self._flatten_base(obs)
    feats = self._get_pv_bess_feats()
    charger_feats = self._get_charger_feats()  # NEW
    arr = np.concatenate([base, feats, charger_feats])
    # ... rest of processing
```bash

**Impact**: Richer observation space; agent can learn per-charger control

---

### 7.3 Low Priority (Nice to Have)

**Issue**: RBC and baseline agents not fully integrated

**Recommendation**: Add comparison script

```bash
# scripts/compare_all_agents.py
python compare_all_agents.py \
  --episodes 2 \
  --agents NoControl UncontrolledCharging RBC SAC PPO A2C \
  --output analyses/comparison_all_agents.csv
```bash

**Output**: COâ‚‚, cost, peak load, solar use for each agent

---

**Issue**: No explicit BESS health tracking

**Recommendation**: Add BESS cycling penalty to reward

```python
# rewards.py

def compute(..., bess_soc: float, prev_bess_soc: float, ...):
    # ... existing ...
    # BESS cycling penalty (avoid continuous charge/discharge)
    cycling_penalty = abs(bess_soc - prev_bess_soc) * 0.05
    reward -= cycling_penalty
```bash

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

The OE2 data flow to agents is **architecturally sound** but has **critical tuning issues**:

| Aspect | Status | Risk |
|--------|--------|------|
| Data connection | âœ“ Correct | Low |
| 128 chargers | âœ“ Correct (126 controllable) | Low |
| Solar (8,760 hrs) | âœ“ Correct | Medium (prescaling hardcoded) |
| BESS (2MWh/1.2MW) | âš  Partially correct | **High** (SOC not observable) |
| Type safety | âš  Duck typing | Low |
| Code quality | âœ“ Good (except duplication) | Medium |
| Architectural | âœ“ Excellent abstraction | Low |

### Critical Issues to Address

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

## 10. APPENDIX: File Reference

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `__init__.py` | Exports + device detection | 75 | âœ“ Clean |
| `sac.py` | SAC agent (SB3 + CityLearn) | 1,113 | âš  Hardcoded params |
| `ppo_sb3.py` | PPO agent | 868 | âš  Hardcoded params |
| `a2c_sb3.py` | A2C agent | 715 | âš  Hardcoded params |
| `agent_utils.py` | Shared utilities | 189 | âœ“ Light |
| `no_control.py` | Zero action baseline | ~50 | âœ“ Simple |
| `uncontrolled.py` | EV-max baseline | ~60 | âœ“ Simple |
| `rbc.py` | Rule-based controller | 320 | âœ“ Good |
| `validate_training_env.py` | Pre-training checks | 137 | âœ“ Useful |

---

**Report Generated**: 2026-01-25 | **Python 3.11** | **stable-baselines3 1.8+**
