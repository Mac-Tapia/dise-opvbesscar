# Copilot Instructions for pvbesscar

## Project Overview

**pvbesscar** is a two-phase reinforcement learning energy management system for Iquitos, Perú designed to optimize EV charging for electric motorcycles (motos) and mototaxis using solar PV and battery storage.

- **OE2 (Dimensioning)**: Photovoltaic (4,050 kWp), BESS (2 MWh/1.2 MW), and 128 EV chargers (32 physical chargers × 4 sockets = 128 controllable outlets, totaling 272 kW)
- **OE3 (Control)**: CityLearn v2 RL environment with SAC/PPO/A2C agents minimizing CO₂ emissions and optimizing solar self-consumption
- **Context**: Iquitos is grid-isolated (thermal generators, 0.45 kg CO₂/kWh). Tariff is low (0.20 USD/kWh), so CO₂ minimization is the primary objective, not cost optimization.

---

## Architecture & Data Flow

### ⚠️ CRITICAL: Hourly Data Only
**Solar timeseries MUST be exactly 8,760 rows per year (hourly resolution).** NO 15-minute, 30-minute, or sub-hourly data. If you have PVGIS 15-min data, downsample: `df.set_index('time').resample('h').mean()`

### Three-Phase Pipeline
1. **OE2 Artifacts** (`data/interim/oe2/`): Solar timeseries (8,760 hrs), charger profiles, BESS config
2. **Dataset Builder** (`src/iquitos_citylearn/oe3/dataset_builder.py`): Constructs CityLearn schema with 534-dim obs space, 126-dim action space (128 chargers - 2 reserved)
3. **Simulation** (`src/iquitos_citylearn/oe3/simulate.py`): Trains SAC/PPO/A2C agents; compares vs baseline
4. **Results** (`outputs/oe3_simulations/`): Timeseries CSV, CO₂ comparisons, checkpoints

### Critical Data Dependencies

**OE2 Input Files** (must exist before dataset build):
- `data/interim/oe2/solar/pv_generation_timeseries.csv`: **8,760 hourly AC output (kW)** from PVGIS/pvlib (1 row per hour, exactly 1 year). **NO 15-minute or sub-hourly data supported**
- `data/interim/oe2/chargers/perfil_horario_carga.csv`: 24-hour load profile (kW by hour)
- `data/interim/oe2/chargers/individual_chargers.json`: 32 chargers with 4 sockets each, rated power (2kW motos, 3kW mototaxis)
- `data/interim/oe2/bess/bess_config.json`: Fixed 2 MWh / 1.2 MW

**Key Validation Rules** (enforced in dataset builder):
- Solar timeseries MUST be exactly 8,760 rows (hourly resolution, 1 hour per row). **NO 15-minute data supported**
- Charger count MUST be 32 (128 sockets = 32 × 4)
- BESS config immutable in OE3 (not controlled by agents)
- Observation space: 534 dims (building energy + 128 chargers + time + grid state)
- Action space: 126 dims (continuous [0,1] per charger, 2 reserved)

**Dispatch Rules** (`configs/default.yaml` → `oe3.dispatch_rules`):
1. **PV→EV**: Direct solar to chargers (priority 1)
2. **PV→BESS**: Charge battery during peak sun (priority 2)
3. **BESS→EV**: Night charging from stored solar (priority 3)
4. **BESS→Grid**: Sell excess when SOC > 95% (priority 4)
5. **Grid Import**: If deficit (priority 5)

### Key Files by Responsibility

**Core Modules** (`src/iquitos_citylearn/`):
- `config.py`: Load YAML + env vars; `RuntimePaths` for directory resolution
- `oe3/dataset_builder.py`: Reads OE2 artifacts → generates CityLearn schema + CSV files
- `oe3/rewards.py`: 5-component multi-objective reward (CO₂ 0.50, solar 0.20, cost 0.10, EV 0.10, grid 0.10)
- `oe3/simulate.py`: Main training loop; checkpoint resume; episode orchestration
- `oe3/agents/{sac.py, ppo_sb3.py, a2c_sb3.py}`: Stable-baselines3 wrappers with GPU config

**Entry Points** (`scripts/`):
- `run_oe3_build_dataset.py`: Build CityLearn dataset from OE2 artifacts
- `run_uncontrolled_baseline.py`: Calculate baseline (no intelligent control)
- `run_oe3_simulate.py`: Full pipeline (dataset → baseline → train 3 agents → compare)
- `_common.py`: Shared config/path loading; Python 3.11 version check

---

## Environment & Dependencies

**Python Version**: 3.11+ required (type hints with `from __future__ import annotations`)

**Key Dependencies**:
- `stable-baselines3`: RL agents (SAC, PPO, A2C)
- `citylearn`: CityLearn v2 environment
- `pandas`, `numpy`: Data manipulation
- `torch`: GPU computation (optional but recommended for training)
- `pyyaml`: Config loading
- `python-dotenv`: Environment variable management

**Installation**:
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows or source .venv/bin/activate on Linux
pip install -r requirements.txt
pip install -r requirements-training.txt  # For GPU training
```

**GPU Setup** (optional but 10× faster):
- Requires CUDA 11.8+ and `torch` with CUDA support
- Auto-detected in agent config via `device: "auto"` or `torch.cuda.is_available()`
- CPU fallback works for debugging (slow; ~1 hour per episode vs 5-10 min with GPU)

---

## Developer Workflows

### Quick Start Commands

**1. Full Pipeline (dataset → baseline → train all 3 agents)**
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```
Duration: 15-30 min (GPU RTX 4060) | Output: `outputs/oe3_simulations/simulation_summary.json`

**2. Build Dataset Only**
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```
Duration: ~1 min | Validates: 128 chargers, 8,760 solar timeseries

**3. Baseline Simulation (no intelligent control)**
```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```
Duration: ~10 sec | Produces reference CO₂/cost for comparison

**4. Compare Results**
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```
Duration: <1 sec | Generates markdown comparison table

## Code Patterns & Conventions

### Module Structure
- **Always** use `from __future__ import annotations` at file start (Python 3.11+ type hints)
- **Always** use `@dataclass` for configs/data containers (see `SACConfig`, `PPOConfig`, `A2CConfig` in `agents/`)
- **Path resolution**: Use `RuntimePaths` from `config.py` for all directory access (not hardcoded paths)
- **Config loading**: Use `load_config(config_path)` + `load_paths(cfg)` from `scripts/_common.py`

### Type Hints & Python Version
- Minimum Python 3.11 (enforced in `_common.py` with `sys.version_info[:2] != (3, 11)` check)
- All functions must have type hints for parameters and return values
- Use `Dict[str, Any]` not `dict`, `List[Path]` not `list`, `Optional[str]` not `str | None`

### Error Handling Patterns
When working with OE2 artifacts, validate before proceeding:
```python
# Check critical files exist before build_citylearn_dataset()
solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
if not solar_path.exists():
    raise FileNotFoundError(f"Missing OE2 solar timeseries: {solar_path}")
```

### Logging
- Use `logging.getLogger(__name__)` at module level
- Setup logging in entry points via `iquitos_citylearn.utils.logging.setup_logging()`
- Log level info for major milestones (dataset build, training start/end)

---

## Multi-Objective Reward Function

Located in `src/iquitos_citylearn/oe3/rewards.py`:

**Weights** (in `MultiObjectiveWeights` dataclass):
- CO₂ minimization: 0.50 (primary: grid imports at 0.4521 kg CO₂/kWh)
- Solar self-consumption: 0.20 (secondary: maximize PV direct usage)
- Cost minimization: 0.10 (tertiary: low tariff, not binding constraint)
- EV satisfaction + grid stability: 0.20 combined (ensure baseline service)

**How to adjust weights**:
1. Edit `MultiObjectiveWeights` dataclass in `rewards.py`
2. Ensure weights sum to 1.0 (auto-normalized in `__post_init__`)
3. Restart training - agents auto-reload new weights
4. Compare results: `python -m scripts.run_oe3_co2_table`

**Example**: To prioritize solar over CO₂, change to `co2: 0.30, solar: 0.50`

---

## Critical Implementation Details

### Checkpoint Management
- **Location**: `checkpoints/{SAC,PPO,A2C}/`
- **Resume behavior**: `simulate()` auto-loads latest checkpoint (by modification date) if exists
- **Key config**: `reset_num_timesteps=False` to accumulate steps across resumptions
- **Metadata file**: `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

### Module Import Structure
Key modules must be imported in correct order to avoid circular imports:
```python
# Correct order (from simulate.py)
from iquitos_citylearn.config import load_config, load_paths  # Config first
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset  # Dataset
from iquitos_citylearn.oe3.agents import SACConfig, PPOConfig, A2CConfig  # Configs
from iquitos_citylearn.oe3.simulate import simulate  # Simulation last
```

### CityLearn Environment Setup
- **Observation**: Flattened 534-dim array (building energy + 128 charger states + time features)
- **Action**: 126 continuous [0,1] values (2 chargers reserved for comparison)
- **Episode length**: 8,760 timesteps (1 year = 365 days × 24 hours per day, hourly resolution)
- **Time step**: 1 hour (3,600 seconds per timestep)
- **Wrapper pattern**: Some agents need `ListToArrayWrapper` to convert CityLearn list obs to numpy

### OE2 ↔ OE3 Connection Points
- **Solar**: `pv_generation_timeseries.csv` → CityLearn `weather.csv`
- **Chargers**: `individual_chargers.json` (32 units) + `perfil_horario_carga.csv` → 128 charger observables
- **BESS**: Config immutable in OE3 (not agent-controlled, dispatch rules instead)
- **Dispatch validation**: Verify priority rules in `configs/default.yaml` match `dataset_builder.py` expectations

### Data Flow Diagram
```bash
OE2 Artifacts              Dataset Builder              CityLearn Env
   ↓                            ↓                           ↓
solar_ts.csv ──┐                                    obs (534d)
charger_csv ───┼─→ enrich ──→ schema.json ──→ CityLearnEnv
bess_config.json─                                    action (126d)
```bash

---

## Agent Architecture Details

### Observation & Action Spaces

**Observation** (534-dimensional when flattened):
```python
# Building-level (per hourly timestep)
- Solar generation (kW)                          # 1 value
- Total electricity demand (kW)                  # 1 value
- Grid import (kW)                               # 1 value
- BESS SOC (%)                                   # 1 value

# Charger-level (128 chargers)
- Charger demand (kW)                            # 128 values
- Charger power (actual draw)                    # 128 values
- Charger occupancy (boolean)                    # 128 values
- Charger battery level if applicable            # 128 values (0 if not)

# Time features
- Hour of day [0,23]                             # 1 value
- Month [0,11]                                   # 1 value
- Day of week [0,6]                              # 1 value
- Is peak hours [0,1]                            # 1 value

# Grid state
- Grid carbon intensity (kg CO₂/kWh)             # 1 value
- Electricity tariff ($/kWh)                     # 1 value
```bash

**Action** (126-dimensional, continuous):
```python
# Charger power setpoints (normalized [0,1])
- 126 actions → agent_power_i = action_i × charger_i_max_power
# Examples:
- action_i = 1.0 → charger charges at max capacity
- action_i = 0.5 → charger charges at 50% capacity
- action_i = 0.0 → charger off
```bash

### Network Architecture

All agents use same **policy network** (stable-baselines3 MlpPolicy):
```bash
Input Layer (534 dims)
    ↓
Dense(1024, activation=relu)   # Layer 1
    ↓
Dense(1024, activation=relu)   # Layer 2
    ↓
Output Layer (126 dims)        # Action space
```bash

**Activation functions**: ReLU for hidden layers, Tanh for continuous action output

**Weight initialization**: Orthogonal init (improves convergence for RL)

### Agent-Specific Modifications

- **SAC**: Uses target networks + replay buffer (off-policy stability)
- **PPO**: Uses advantage function + clipping (on-policy stability)
- **A2C**: Uses multi-step advantage (simpler baseline)

---

## Deployment & Scaling

### Docker Setup

**Training container** (`docker-compose.gpu.yml`):
```yaml
services:
  training:
    image: pytorch:2.0-cuda11.8
    gpus: all
    volumes:
      - ./data:/workspace/data
      - ./checkpoints:/workspace/checkpoints
    command: python scripts/train_agents_serial.py --device cuda --episodes 50
```bash

**Build & run**:
```bash
docker-compose -f docker-compose.gpu.yml up -d
```bash

### FastAPI Server (Model Serving)

**Endpoint**: `scripts/fastapi_server.py`

```python
from fastapi import FastAPI
from iquitos_citylearn.oe3.agents import PPOAgent

app = FastAPI()
agent = PPOAgent.load("checkpoints/PPO/latest.zip")

@app.post("/predict")
def predict(observation: List[float]):
    action, _ = agent.predict(observation)
    return {"action": action.tolist()}
```bash

**Run server**:
```bash
python scripts/fastapi_server.py --port 8000
```bash

**API usage**:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"observation": [...]}'  # 534-dim array
```bash

### Kubernetes Deployment

**Config**: `docker/k8s-deployment.yaml`

**Multi-agent horizontal scaling**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rl-agent-server
spec:
  replicas: 3  # Scale to 3 API instances
  template:
    spec:
      containers:
      - name: api
        image: pvbesscar:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: checkpoints
          mountPath: /workspace/checkpoints
```bash

**Deploy**:
```bash
kubectl apply -f docker/k8s-deployment.yaml
kubectl scale deployment rl-agent-server --replicas 5
```bash

---



### Unit Testing Pattern
```bash
pytest tests/ -v
```bash
- Test files: `tests/test_*.py`
- Use pytest fixtures for shared dataset/config

### Validation Checklist Before Committing
1. **Dataset consistency**: All 128 chargers present; solar timeseries 8,760 length
2. **Reward normalization**: MultiObjectiveWeights sum to 1.0 (auto-normalized in `__post_init__`)
3. **GPU detection**: Run `detect_device()` in agent config instantiation
4. **Checkpoint compatibility**: Old checkpoints loadable if agent class unchanged

---

## Code Style & Conventions

- **Line length**: 120 characters (black/isort configured in `pyproject.toml`)
- **Type hints**: Required for function signatures; use `from __future__ import annotations`
- **Docstrings**: First sentence only for brief configs; full docstring for complex functions
- **Imports**: Alphabetical within groups (standard, third-party, local); `isort` auto-fixes
- **Logging**: Use `logging.getLogger(__name__)`; no print() in production code

### File Naming
- Scripts: `train_*.py`, `run_*.py`, `monitor_*.py`
- Agent classes: `*_sb3.py` (stable-baselines3 wrapper)
- Utilities: `*_utils.py` or grouped in `utils/`

---

## Critical Implementation Details

### Module Import Structure

Key modules and their responsibilities:
- **`src/iquitos_citylearn/config.py`**: Centralized config loading, path resolution via `RuntimePaths` dataclass
- **`src/iquitos_citylearn/oe3/dataset_builder.py`**: Reads OE2 artifacts and generates CityLearn schema + CSV files
- **`src/iquitos_citylearn/oe3/rewards.py`**: Multi-objective reward computation with 5 components
- **`src/iquitos_citylearn/oe3/agents/{sac,ppo_sb3,a2c_sb3}.py`**: Stable-baselines3 wrappers with agent-specific hyperparams
- **`src/iquitos_citylearn/oe3/simulate.py`**: Episode runner, checkpoint management, training loop orchestration

**Import pattern for training**:
```python
from src.iquitos_citylearn.config import RuntimePaths, load_yaml
from src.iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from src.iquitos_citylearn.oe3.agents.sac import SACAgent
env = CityLearnEnv(schema_path)
agent = SACAgent(env=env, config=config)
agent.learn(total_timesteps=8760)
```

### CityLearn Environment Setup
- **Observation space**: Flattened 534-dim array (building energy, 128 charger states, time features)
- **Action space**: 126 continuous values [0,1] representing charger power setpoints (2 reserved)
- **Episode length**: 8,760 timesteps (1 year hourly)
- **Wrapper requirement**: Some agents need `ListToArrayWrapper` to convert CityLearn's list-based obs to numpy

### Checkpoint Management
- **Location**: `checkpoints/{SAC,PPO,A2C}/<latest_checkpoint>`
- **Auto-resume**: `simulate()` checks `reset_num_timesteps=False` to accumulate steps across resumptions
- **Metadata**: `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

### Dispatch Rules in BESS Control
Priority stack (in `configs/default.yaml`):
1. **PV→EV**: Direct solar to chargers (low-cost, zero-loss preferred path)
2. **PV→BESS**: Excess solar charges battery for evening peak
3. **BESS→EV**: Night charging from stored solar energy
4. **BESS→Mall**: Desaturate BESS when SOC > 95%
5. **Grid import**: If deficit after BESS discharge

---

## Docker & Deployment

- **Training container**: `docker-compose.gpu.yml` mounts GPU and runs agent training
- **API endpoint**: `scripts/fastapi_server.py` serves trained agent predictions
- **Kubernetes**: `docker/k8s-deployment.yaml` for multi-agent horizontal scaling

---

## Common Pitfalls & Solutions

| Issue | Solution |
|-------|----------|
| "128 chargers not found" in dataset_builder | Check `data/interim/oe2/chargers/individual_chargers.json` exists; validate all 32 chargers have 4 sockets (128 total). Note: only 126 are controllable by agents |
| GPU out of memory during PPO training | Reduce `n_steps` from 2048 to 1024; disable `use_amp=False` in config; reduce `batch_size` from 128 to 64; use `device: "cpu"` for debugging |
| Reward explosion (NaN values) | Verify MultiObjectiveWeights normalized in `__post_init__`; check observation scaling; ensure solar timeseries not all zeros; enable `log_rewards=True` in simulate.py |
| Agent training stuck at negative rewards or not learning | Ensure OE2 artifacts loaded (solar CSV 8,760 rows); validate dispatch rules enabled in `configs/default.yaml`; check BESS not over-discharged (SOC must stay > min_soc); examine charger profiles in `perfil_horario_carga.csv` |
| Old checkpoint fails to load | Agent class signatures must match checkpoint; if reward function changed, restart from scratch; verify checkpoint path exists (`checkpoints/{SAC,PPO,A2C}/latest/`) |
| Training loops never converge (reward stays flat) | Check observation vector not all zeros; verify action space is continuous [0,1] not discrete; enable `print_rewards` debugging in `compute_reward()` |
| Solar generation zeros at night causing reward issues | Expected behavior; rewards should account for nighttime (solar bonus uses normalized form); BESS discharge should cover night EV charging |
| Charger profiles all identical/unrealistic | Verify `individual_chargers.json` has unique power ratings per charger (motos 2kW, mototaxis 3kW); check `perfil_horario_carga.csv` has proper 24-hour demand curve |
| **15-minute solar data provided (NOT SUPPORTED)** | **This codebase ONLY accepts hourly data with exactly 8,760 rows per year.** If using PVGIS 15-min raw data, downsample: `df.set_index('time').resample('h').mean()` |

### Diagnostic Commands

**Check dataset integrity**:
```bash
# Verify schema
python -c "import json; s=json.load(open('outputs/schema_*.json')); print(len(s['buildings']), 'buildings')"

# Verify solar timeseries is exactly 8,760 rows (hourly, NOT 15-minute)
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); assert len(df)==8760, f'ERROR: Expected 8760 rows, got {len(df)}'; print(f'✓ Solar timeseries: {len(df)} rows (correct hourly)')"

# List discovered chargers
python -c "import json; c=json.load(open('data/interim/oe2/chargers/individual_chargers.json')); print(f'{len(c)} chargers, {len(c)*4} sockets')"
```bash

**Monitor training in real-time**:
```bash
python scripts/monitor_training_live_2026.py
# Output: Updates every 5s with agent name, episode, reward, total timesteps
```bash

**Check checkpoint compatibility**:
```bash
python -c "from stable_baselines3 import PPO; m=PPO.load('checkpoints/PPO/latest.zip'); print(m.policy)"
```bash

**Validate environment**:
```bash
python -c "from citylearn.citylearn import CityLearnEnv; e=CityLearnEnv('outputs/schema_*.json'); o,i=e.reset(); print(f'Obs shape: {len(o)} dims')"
```bash

---

## Performance Baselines & Expected Results

### Baseline (Uncontrolled)
- **CO₂ emissions**: ~10,200 kg/year (grid import at max during peak hours)
- **Grid import**: ~41,300 kWh/year (peak evening demand)
- **EV satisfaction**: 100% (chargers always on)
- **Solar utilization**: ~40% (much wasted PV generation)

### RL Agents (Expected after tuning)
- **SAC** (off-policy, sample-efficient):
  - CO₂: ~7,500 kg/year (-26% vs baseline)
  - Solar utilization: ~65%
  - Training speed: Fastest (handles sparse rewards well)

- **PPO** (on-policy, stable):
  - CO₂: ~7,200 kg/year (-29% vs baseline)
  - Solar utilization: ~68%
  - Training speed: Medium (~1 hour per episode on GPU)

- **A2C** (on-policy, simple):
  - CO₂: ~7,800 kg/year (-24% vs baseline)
  - Solar utilization: ~60%
  - Training speed: Fastest wall-clock (simple network)

### Tuning Impact
- Increasing `co2_weight` from 0.50 → 0.70: +3-5% additional CO₂ reduction
- Increasing `solar_weight` from 0.20 → 0.40: +5-8% solar utilization, may sacrifice cost
- Reducing learning rate 2e-4 → 1e-4: Slower convergence but more stable (less reward noise)

---

## Debugging & Development Tips

### Adding New Reward Component

**Step 1**: Define in `rewards.py`:
```python
@dataclass
class MultiObjectiveWeights:
    # ... existing ...
    new_metric: float = 0.05
    
    def __post_init__(self):
        # Auto-normalize all weights
        total = sum([self.co2, self.solar, self.cost, self.ev_satisfaction, 
                     self.grid_stability, self.new_metric])
        # Apply factor to all
```bash

**Step 2**: Implement in compute function:
```python
def compute_reward(obs, actions, ...):
    # ... existing components ...
    r_new_metric = calculate_new_metric(obs)  # Return normalized value [0, 1]
    
    # Add to total
    r_total += weights.new_metric * r_new_metric
    return r_total
```bash

**Step 3**: Test before full training:
```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
# Should complete without errors
```bash

### Profiling Agent Training

**Identify bottlenecks**:
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Train for 1 episode
agent.learn(total_timesteps=8760)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(20)
```bash

**Expected slow sections**: CityLearn environment step (physics simulation), reward computation

### Checkpoint Investigation

**Load and inspect**:
```python
from stable_baselines3 import PPO
import numpy as np

model = PPO.load('checkpoints/PPO/latest.zip')
print(f"Total timesteps: {model.num_timesteps}")
print(f"Policy params: {sum(p.numel() for p in model.policy.parameters())}")

# Test prediction
obs = np.random.randn(534)
action, _ = model.predict(obs, deterministic=True)
print(f"Action shape: {action.shape}")
```bash

---



## Key References

- **Project Overview** (Line 3): project scope, OE2 dimensioning specs
- **Reward Function** (Line 148): detailed reward component breakdown
- **Training workflows** (Line 80): latest training commands and KPIs
- **Troubleshooting** (Line 531): solutions by agent and issue type
