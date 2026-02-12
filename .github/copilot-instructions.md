# Copilot Instructions for pvbesscar

## 🎯 Project Purpose in 30 Seconds

**pvbesscar** optimizes EV charging for 38 electric sockets (270 motos + 39 mototaxis/day) using solar PV (4,050 kWp) + battery storage (4,520 kWh BESS) via reinforcement learning agents (SAC/PPO/A2C) to minimize CO₂ emissions in an isolated grid (Iquitos, Perú, 0.4521 kg CO₂/kWh from thermal generation).

**Infrastructure (v5.2):**
- 19 chargers (15 motos + 4 mototaxis) × 2 sockets = 38 total sockets
- Mode 3 charging @ 7.4 kW per socket (monofásico 32A @ 230V)
- 281.2 kW installed power

**Two Phases:**
- **OE2 (Dimensioning)**: Infrastructure specs (solar, BESS, chargers, demand profiles) in `src/dimensionamiento/oe2/`
- **OE3 (Control)**: CityLearn v2 RL simulation with observations, actions, CO₂ minimization reward in `src/agents/`

---

## 🆕 Dual Baselines (2026-02-03)

**Two comparison scenarios** to measure RL agent improvements:

```
BASELINE 1: "CON SOLAR" (4,050 kWp)
├─ Mall 100kW + EVs 50kW + Solar 4,050 kWp, no BESS, no RL
└─ CO₂: ~190,000 kg/año ← REFERENCE POINT FOR RL AGENTS

BASELINE 2: "SIN SOLAR" (0 kWp)  
├─ Mall 100kW + EVs 50kW + No solar, no BESS, no RL
└─ CO₂: ~640,000 kg/año ← Shows impact of 4,050 kWp (410k kg CO₂ saved)
```

**Quick Start:**
```bash
python -m scripts.run_dual_baselines --config configs/default.yaml
# Generates: outputs/baselines/{with_solar,without_solar}/baseline_comparison.csv
```

See [BASELINE_QUICK_START.md](../BASELINE_QUICK_START.md) for details.

---

## 📂 Actual Codebase Structure

### OE2 (Dimensioning Phase)
**Location:** `src/dimensionamiento/oe2/`
- [data_loader.py](../src/dimensionamiento/oe2/data_loader.py): Loads solar, chargers, BESS with validation
- [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py): Charger models v5.2 (19 chargers × 2 sockets = 38 total). **Key pattern:** Extensive use of `@dataclass(frozen=True)` for immutable specs
- [solar_pvlib.py](../src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py): PVGIS solar generation timeseries validation
- **Critical constraint:** All solar data must be 8,760 hourly rows (NOT 15-minute)

### OE3 (Control Phase)
**Location:** `src/agents/`
- [sac.py](../src/agents/sac.py): Soft Actor-Critic agent (off-policy, best for asymmetric rewards)
- [ppo_sb3.py](../src/agents/ppo_sb3.py), [a2c_sb3.py](../src/agents/a2c_sb3.py): On-policy agents from stable-baselines3
- [no_control.py](../src/agents/no_control.py): Baseline agent (uncontrolled dispatch)
- [agent_utils.py](../src/utils/agent_utils.py): **Key patterns:** `validate_env_spaces()`, checkpoint management, observation wrappers

### Agent Utilities & Shared Code
**Location:** `src/utils/`
- [agent_utils.py](../src/utils/agent_utils.py): **Core pattern for validation:** `validate_env_spaces(env)` checks observation/action spaces
- [logging.py](../src/utils/logging.py), [time.py](../src/utils/time.py), [series.py](../src/utils/series.py): Shared infrastructure

---



### ⚠️ CRITICAL: Hourly Data Only (8,760 rows = 1 year)
**Solar timeseries MUST be exactly hourly (NOT 15-minute).** If you have PVGIS 15-min data: `df.set_index('time').resample('h').mean()`. Validation enforced in [dataset_builder.py](../src/citylearnv2/dataset_builder/dataset_builder.py).

### The Pipeline: OE2 → OE3
```
OE2 Artifacts (infrastructure specs: solar CSV, charger JSON, BESS config)
  ↓ [data_loader.py validates & loads]
CityLearn v2 Environment (8,760 hourly timesteps, 394-dim observations)
  ↓ [agents/{sac,ppo_sb3,a2c_sb3}.py train with stable-baselines3]
Checkpoints saved to /checkpoints/{SAC,PPO,A2C}/
  ↓
Results: CO₂ reduction %, solar self-consumption %, training metrics CSV
```

### Key Files by Responsibility (ACTUAL CODEBASE)
- [data_loader.py](../src/dimensionamiento/oe2/data_loader.py): **Load & validate** OE2 artifacts; raises `OE2ValidationError` early if solar not 8,760 rows
- [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py): **Charger specs v5.2** with immutable `@dataclass(frozen=True)` - 19 units × 2 sockets = 38 controllable sockets
- [agent_utils.py](../src/utils/agent_utils.py): **Environment validation** with `validate_env_spaces()` - checks obs/action dimensions
- [sac.py](../src/agents/sac.py), [ppo_sb3.py](../src/agents/ppo_sb3.py), [a2c_sb3.py](../src/agents/a2c_sb3.py): **Agent implementations** - stable-baselines3 wrappers with GPU/CPU config

### Charger Scaling (v5.2: 19 → 38)
```python
# Pattern from chargers.py v5.2:
chargers = create_iquitos_chargers()  # 19 chargers (15 motos + 4 mototaxis)
total_sockets = 19 * 2  # = 38 controllable charging actions
# Each charger has 2 sockets @ 7.4 kW (Mode 3, 32A @ 230V)
```
**See:** [chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py) for charger specifications with `ChargerSpec` and `ChargerSet` dataclasses.

### Observation & Action Spaces (v5.2)
- **Observation:** Solar W/m², grid Hz, BESS % SOC, 38 sockets × 3 values each, time features (hour/month/day_of_week)
- **Action:** Continuous [0,1] normalized power setpoints → 1 BESS + 38 sockets (actual kW via `action_bounds`)

---

## Environment & Dependencies

**Python Version**: 3.11+ required (type hints with `from __future__ import annotations`)

**Key Dependencies** (from pyproject.toml):
- `stable-baselines3` (≥2.0): RL agents (SAC, PPO, A2C)
- `gymnasium` (≥0.27): RL environment interface
- `pandas`, `numpy`: Data manipulation
- `torch` (optional): GPU training (RTX 4060 recommended for 15-30 min training)
- `pyyaml`: Config loading

**Installation**:
```bash
python -m venv .venv
.venv/Scripts/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
pip install -r requirements-training.txt  # For GPU training
```

---

## Developer Workflows

### Real Training Commands (VERIFIED 2026-02-04)
```bash
# Option 1: Run dual baselines (WITH and WITHOUT solar)
python -m scripts.run_dual_baselines --config configs/default.yaml
# Duration: ~20 seconds total | Outputs: outputs/baselines/

# Option 2: Train single agent (SAC, PPO, or A2C)
python -c "from src.agents.sac import make_sac; env = ...; agent = make_sac(env); agent.learn(...)"
# Or use checkpoint resume pattern (auto-loads latest from /checkpoints/)

# Option 3: Verify system (diagnostic)
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); assert len(df)==8760, f'ERROR: {len(df)} rows != 8760'; print('✓ Solar OK')"
```

**Duration estimates (GPU RTX 4060):** 
- Baselines: ~20 seconds 
- SAC training (26,280 steps): ~5-7 hours
- PPO/A2C: ~4-6 hours (on-policy, typically faster)

### Code Patterns (ENFORCED)
- **ALWAYS** import `from __future__ import annotations` (Python 3.11+ required)
- **ALWAYS** use `@dataclass(frozen=True)` for immutable config/spec containers (see [chargers.py](../src/dimensionamiento/oe2/chargers.py))
- **ALWAYS** validate environment with `validate_env_spaces(env)` from [agent_utils.py](../src/utils/agent_utils.py) before agent init
- **Path handling:** Use `Path()` from pathlib; avoid hardcoded paths
- **Error handling:** Raise `OE2ValidationError` (from data_loader) or custom exceptions early, don't silently fail

### Checkpoint Management (AUTO-RESUME PATTERN)
```python
# Agents auto-load latest checkpoint if it exists:
agent = make_sac(env)  # Checks /checkpoints/SAC/ for latest .zip
agent.learn(total_timesteps=10000, reset_num_timesteps=False)
# Key: reset_num_timesteps=False accumulates steps across resumptions
```
**Checkpoint metadata:** `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

---

## Multi-Objective Reward Function

**Location:** Embedded in agent initialization (weights currently hardcoded, subject to refactor)

**Reward Weights** (logical, from CO₂ tracking):
- CO₂ grid minimization: 0.50 (primary: grid imports × 0.4521 kg CO₂/kWh)
- Solar self-consumption: 0.20 (secondary: maximize PV direct usage)
- EV charge completion: 0.15 (tertiary: ensure EVs charged by deadline)
- Grid stability: 0.10 (tertiary: smooth power ramping)
- Cost minimization: 0.05 (tertiary: low tariff preference)

**How to adjust weights:**
1. Weights are typically in agent config or reward calculation
2. Ensure weights sum to 1.0 (auto-normalized if using softmax)
3. Restart training - agents will reoptimize with new priorities
4. Compare results via checkpoint inspection or simulation output

**Key insight:** SAC (off-policy) handles asymmetric rewards better than PPO/A2C for this problem.

---

## Critical Implementation Details

### Checkpoint Management
- **Location:** `checkpoints/{SAC,PPO,A2C}/` (agent-specific subdirs)
- **Resume behavior:** Agents auto-load latest checkpoint (by modification date) if exists
- **Key config:** `reset_num_timesteps=False` to accumulate steps across resumptions
- **Metadata file:** `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

### CityLearn Environment Setup
- **Observation:** Flattened array (building energy + 38 socket states + time features)
- **Action:** Continuous [0,1] values (1 BESS + 38 sockets)
- **Episode length:** 8,760 timesteps (1 year = 365 days × 24 hours, hourly resolution)
- **Time step:** 1 hour (3,600 seconds per timestep)
- **Wrapper pattern:** Some agents use `ListToArrayWrapper` to convert CityLearn list obs → numpy arrays

### OE2 ↔ OE3 Connection Points
- **Solar:** `data/interim/oe2/solar/pv_generation_timeseries.csv` (must be 8,760 hourly rows, not 15-minute)
- **Chargers:** `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` (19 chargers × 2 sockets = 38 controllable) + demand profiles
- **BESS:** Config immutable in OE3; dispatch rules manage charging/discharging (agents control priority/timing)

---

## Common Pitfalls & Solutions

| Issue | Solution |
|-------|----------|
| "38 sockets not found" in dataset_builder | Check `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` exists; validate 19 chargers × 2 sockets = 38 total |
| GPU out of memory during PPO training | Reduce `n_steps` from 2048 to 1024; reduce `batch_size` from 128 to 64 |
| Reward explosion (NaN values) | Verify MultiObjectiveWeights normalized in `__post_init__`; ensure solar timeseries not all zeros |
| Agent training stuck at negative rewards | Ensure OE2 artifacts loaded (solar CSV 8,760 rows); validate dispatch rules enabled in `configs/default.yaml` |
| Old checkpoint fails to load | Agent class signatures must match checkpoint; if reward function changed, restart from scratch |
| **15-minute solar data provided (NOT SUPPORTED)** | **ONLY accept hourly data with exactly 8,760 rows per year.** Downsample: `df.set_index('time').resample('h').mean()` |

### Diagnostic Commands

**Check dataset integrity:**
```bash
# Verify solar timeseries is exactly 8,760 rows (hourly, NOT 15-minute)
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); assert len(df)==8760, f'ERROR: Expected 8760, got {len(df)}'; print(f'✓ Solar timeseries: {len(df)} rows (correct hourly)')"

# Check checkpoint compatibility
python -c "from stable_baselines3 import PPO; m=PPO.load('checkpoints/PPO/latest.zip'); print(m.policy)"

# List discovered chargers
python -c "import json; c=json.load(open('data/interim/oe2/chargers/individual_chargers.json')); print(f'{len(c)} chargers, {len(c)*4} sockets')"
```

---

## Performance Baselines & Expected Results

### Baseline (Uncontrolled)
- **CO₂ emissions**: ~10,200 kg/year (grid import at max during peak hours)
- **Solar utilization**: ~40% (much wasted PV generation)

### RL Agents (Expected after tuning)
- **SAC** (off-policy): CO₂ ~7,500 kg/year (-26%), solar ~65%, fastest training
- **PPO** (on-policy): CO₂ ~7,200 kg/year (-29%), solar ~68%, medium speed
- **A2C** (on-policy, simple): CO₂ ~7,800 kg/year (-24%), solar ~60%, fastest wall-clock

### Tuning Impact
- Increasing `co2_weight` from 0.50 → 0.70: +3-5% additional CO₂ reduction
- Increasing `solar_weight` from 0.20 → 0.40: +5-8% solar utilization
- Reducing learning rate 2e-4 → 1e-4: Slower convergence but more stable

---

## Key References

- **Project Overview** (Line 3): project scope, OE2 dimensioning specs
- **Reward Function** (Line 100): detailed reward component breakdown
- **Training workflows** (Line 70): latest training commands and KPIs
- **Troubleshooting** (Line 165): solutions by agent and issue type
