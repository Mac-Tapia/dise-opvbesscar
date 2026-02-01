# Copilot Instructions for pvbesscar

## 🎯 Project Purpose in 30 Seconds

**pvbesscar** optimizes EV charging for 128 electric chargers (2,912 motos + 416 mototaxis) using solar PV (4,050 kWp) + battery storage (4,520 kWh BESS) via reinforcement learning agents (SAC/PPO/A2C) to minimize CO₂ emissions in an isolated grid (Iquitos, Perú, 0.4521 kg CO₂/kWh from thermal generation).

**Two Phases:**
- **OE2 (Dimensioning)**: Infrastructure specs (solar, BESS, chargers, demand profiles)
- **OE3 (Control)**: CityLearn v2 RL simulation with 394-dim observations, 129-dim actions, CO₂ minimization reward

---

## Architecture & Critical Data Flows

### ⚠️ CRITICAL: Hourly Data Only (8,760 rows = 1 year)
**Solar timeseries MUST be exactly hourly (NOT 15-minute).** If you have PVGIS 15-min data: `df.set_index('time').resample('h').mean()`. Validation enforced in [dataset_builder.py](../src/iquitos_citylearn/oe3/dataset_builder.py#L89).

### The Pipeline: OE2 → OE3
```
OE2 Artifacts (infrastructure specs)
  ↓ [dataset_builder.py]
CityLearn Schema (8,760 hourly timesteps, 394-dim observations)
  ↓ [simulate.py]
Train 3 RL Agents (SAC, PPO, A2C) + Baseline
  ↓
Results: CO₂ reduction %, solar self-consumption %, timeseries CSV
```

### Key Files by Responsibility
- [config.py](../src/iquitos_citylearn/config.py): Load YAML + env vars; `RuntimePaths` for directory resolution
- [dataset_builder.py](../src/iquitos_citylearn/oe3/dataset_builder.py): Reads OE2 artifacts → generates CityLearn schema + CSV
- [rewards.py](../src/iquitos_citylearn/oe3/rewards.py): Multi-objective reward (CO₂ 0.50, solar 0.20, cost 0.15, EV 0.10, grid 0.05)
- [simulate.py](../src/iquitos_citylearn/oe3/simulate.py): Training loop, checkpoint resume, episode orchestration
- [agents/{sac.py, ppo_sb3.py, a2c_sb3.py}](../src/iquitos_citylearn/oe3/agents): Stable-baselines3 wrappers with GPU config

### Control Architecture (NOT just agents)
**RL Agents (129 actions):** Control EV charger power setpoints (1 BESS + 128 chargers).  
**Dispatch Rules (automatic, 5 priorities):** Route energy (PV → EV/BESS, BESS → EV/Mall/Grid).  
**Result:** Coordinated system where RL decides "when to charge" and rules handle "how to supply."

### Observation & Action Spaces
- **Observation (394-dim):** Solar generation, grid metrics, BESS SOC, 128 chargers (4 values each), time features (hour/month/day_of_week)
- **Action (129-dim):** Continuous [0,1] normalized setpoints for 1 BESS + 128 chargers

---

## Environment & Dependencies

**Python Version**: 3.11+ required (type hints with `from __future__ import annotations`)

**Key Dependencies**:
- `stable-baselines3`: RL agents (SAC, PPO, A2C)
- `citylearn`: CityLearn v2 environment
- `pandas`, `numpy`: Data manipulation
- `torch`: GPU computation (optional but recommended for training)
- `pyyaml`: Config loading

**Installation**:
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
pip install -r requirements-training.txt  # For GPU training
```

---

## Developer Workflows

### Quick Start Commands
```bash
# Full pipeline (dataset → baseline → train all 3 agents)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Build dataset only
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Baseline simulation (no intelligent control)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Compare results
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

**Duration estimates (GPU RTX 4060):** Full pipeline: 15-30 min | Dataset: 1 min | Baseline: 10 sec

### Code Patterns
- **Always** import `from __future__ import annotations` (Python 3.11+ required)
- **Always** use `@dataclass` for configs/data containers
- **Path resolution:** Use `RuntimePaths` from [config.py](../src/iquitos_citylearn/config.py) (not hardcoded paths)
- **Config loading:** Use `load_config(config_path) + load_paths(cfg)` from [scripts/_common.py](../scripts/_common.py)

---

## Multi-Objective Reward Function

Located in [rewards.py](../src/iquitos_citylearn/oe3/rewards.py):

**Weights** (in `MultiObjectiveWeights` dataclass):
- CO₂ minimization: 0.50 (primary: grid imports at 0.4521 kg CO₂/kWh)
- Solar self-consumption: 0.20 (secondary: maximize PV direct usage)
- Cost minimization: 0.10 (tertiary: low tariff, not binding constraint)
- EV satisfaction + grid stability: 0.20 combined (ensure baseline service)

**How to adjust weights:**
1. Edit `MultiObjectiveWeights` dataclass in [rewards.py](../src/iquitos_citylearn/oe3/rewards.py)
2. Ensure weights sum to 1.0 (auto-normalized in `__post_init__`)
3. Restart training - agents auto-reload new weights
4. Compare results: `python -m scripts.run_oe3_co2_table`

---

## Critical Implementation Details

### Checkpoint Management
- **Location:** `checkpoints/{SAC,PPO,A2C}/`
- **Resume behavior:** `simulate()` auto-loads latest checkpoint (by modification date) if exists
- **Key config:** `reset_num_timesteps=False` to accumulate steps across resumptions
- **Metadata file:** `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

### CityLearn Environment Setup
- **Observation:** Flattened 394-dim array (building energy + 128 charger states + time features)
- **Action:** 129 continuous [0,1] values (1 BESS + 112 motos + 16 mototaxis)
- **Episode length:** 8,760 timesteps (1 year = 365 days × 24 hours per day, hourly resolution)
- **Time step:** 1 hour (3,600 seconds per timestep)
- **Wrapper pattern:** Some agents need `ListToArrayWrapper` to convert CityLearn list obs to numpy

### OE2 ↔ OE3 Connection Points
- **Solar:** `pv_generation_timeseries.csv` → CityLearn `weather.csv` (must be 8,760 hourly rows)
- **Chargers:** `individual_chargers.json` (32 units) + `perfil_horario_carga.csv` → 128 charger observables
- **BESS:** Config immutable in OE3 (not agent-controlled, dispatch rules instead)

---

## Common Pitfalls & Solutions

| Issue | Solution |
|-------|----------|
| "128 chargers not found" in dataset_builder | Check `data/interim/oe2/chargers/individual_chargers.json` exists; validate all 32 chargers have 4 sockets (128 total) |
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
