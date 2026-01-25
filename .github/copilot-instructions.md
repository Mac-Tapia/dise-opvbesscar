# Copilot Instructions for pvbesscar

## Project Overview

**pvbesscar** is a two-phase reinforcement learning energy management system for Iquitos, Perú:

- **OE2 (Dimensioning)**: Photovoltaic (4,050 kWp Kyocera KS20 + Eaton Xpert1670 inverter), BESS (2 MWh/1.2 MW), and 128 EV chargers (272 kW installed: 112 motos @2kW + 16 mototaxis @3kW)
- **OE3 (Control)**: CityLearn v2 environment with SAC/PPO/A2C agents optimizing multi-objective rewards (CO₂ minimization as primary objective)

**Key Results**: 6,707.86 tCO₂/year net reduction; 8.31 GWh annual PV generation with 29.6% capacity factor

---

## Architecture & Data Flow

### Three-Tier Structure
```
Input (OE2 artifacts) → Dataset Builder → CityLearn Environment → RL Agents
   ↓                        ↓                     ↓                   ↓
data/interim/oe2/      dataset_builder.py    schema.json          simulate.py
  (solar, chargers,    (enriched_observables  (building,           (SAC, PPO,
   BESS profiles)      + dispatch rules)       energy_sim)          A2C configs)
```

### Critical Data Dependencies

1. **Solar Generation** (`data/interim/oe2/solar/pv_generation_timeseries.csv`): 8,760 hourly values from PVGIS/pvlib, normalized to Eaton Xpert1670 spec (2 inverters, 31 modules/string, 6,472 strings)
2. **EV Charger Profiles** (`data/interim/oe2/chargers/perfil_horario_carga.csv`): Per-charger 24-hour demand profiles from MATLAB simulation (3,061 vehicles/day, 92% utilization)
3. **Dispatch Rules** (`configs/default.yaml` → `oe3.dispatch_rules`): Priority-based BESS control (PV→EV→BESS→Grid ordering)
4. **Carbon Intensity**: Fixed at 0.4521 kg CO₂/kWh (thermal grid isolation in Iquitos)

### Key Files by Responsibility

- **Config management**: `src/iquitos_citylearn/config.py` (runtime paths, YAML loading)
- **Dataset construction**: `src/iquitos_citylearn/oe3/dataset_builder.py` (charger CSV discovery, schema generation)
- **Reward system**: `src/iquitos_citylearn/oe3/rewards.py` (multi-objective weighting: CO₂ 0.50, solar 0.20, cost 0.10, EV/grid 0.20)
- **Agent training**: `src/iquitos_citylearn/oe3/agents/{ppo_sb3,sac,a2c_sb3}.py` (stable-baselines3 configs with GPU support)
- **Simulation**: `src/iquitos_citylearn/oe3/simulate.py` (episode runner, checkpoint management)

---

## Developer Workflows

### Common Tasks

#### 1. Build CityLearn Dataset (Required Before Training)
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```
- Validates OE2 artifacts (solar, chargers, BESS)
- Generates `outputs/schema_<timestamp>.json`
- Verifies 128 chargers with 4 sockets each = 512 controllable outlets
- **Output**: `data/processed/citylearnv2_dataset/`

#### 2. Run Baseline Simulation (Uncontrolled)
```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```
- No intelligent control; chargers draw maximum available power
- Produces CO₂/cost baseline for comparison
- Takes ~5 min (8,760 timesteps)

#### 3. Train RL Agents (SAC → PPO → A2C Serial)
```bash
python scripts/train_agents_serial.py --device cuda --episodes 5
```
- Trains 3 agents sequentially (each ~1 hour on GPU)
- **Agents trained**: SAC (off-policy, sample-efficient), PPO (on-policy, stable), A2C (on-policy, multi-step)
- **Resume from checkpoint**: Automatically loads `checkpoints/agent/<latest>`
- Output: Training logs in `analyses/logs/`

#### 4. Compare Baseline vs RL Results
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```
- Generates comparison table (baseline CO₂ vs each agent's CO₂)
- Output: `COMPARACION_BASELINE_VS_RL.txt`

#### 5. Monitor Live Training Progress
```bash
python scripts/monitor_training_live_2026.py
```
- Polls checkpoint metadata every 5 sec
- Shows agent, episode, reward, timesteps

---

## Agent Configuration Pattern

All agents follow same structure in `src/iquitos_citylearn/oe3/agents/`:

```python
@dataclass
class XXXConfig:
    train_steps: int = 1000000      # Total training steps
    learning_rate: float = 2.0e-4   # With linear decay if enabled
    batch_size: int = 128            # SAC: 256; PPO: 128; A2C: 64
    hidden_sizes: tuple = (1024, 1024)  # Network architecture
    device: str = "auto"             # GPU auto-detection via torch
    use_amp: bool = True             # Mixed precision training
```

**Key Hyperparameters** (tuned for thermal grid CO₂ minimization):
- **PPO**: `n_epochs=20`, `clip_range=0.1`, `gae_lambda=0.98` (long horizon, conservative clipping)
- **SAC**: `target_update_interval=1`, `use_sde=True` (off-policy flexibility for sparse rewards)
- **A2C**: `n_steps=2048`, `lr_schedule="linear"` (simpler on-policy baseline)

---

## Multi-Objective Reward Function

Located in `src/iquitos_citylearn/oe3/rewards.py`:

```python
@dataclass
class MultiObjectiveWeights:
    co2: float = 0.50              # PRIMARY: Minimize thermal grid imports
    solar: float = 0.20            # SECONDARY: Maximize PV self-consumption
    cost: float = 0.10             # TERTIARY: Low tariff (0.20 USD/kWh)
    ev_satisfaction: float = 0.10  # Baseline charging requirement
    grid_stability: float = 0.10   # Peak demand smoothing
```

**Context**: Iquitos is grid-isolated (diesel thermoelectric); CO₂ mitigation is primary objective. Cost is secondary (tariff already low).

### Detailed Reward Calculation

The reward signal combines 5 normalized components:

$$r_{total}(t) = w_{CO2} \cdot r_{CO2}(t) + w_{solar} \cdot r_{solar}(t) + w_{cost} \cdot r_{cost}(t) + w_{EV} \cdot r_{EV}(t) + w_{grid} \cdot r_{grid}(t)$$

#### Component Breakdown

1. **CO₂ Reduction** ($w_{CO2} = 0.50$):
   - Penalizes grid imports proportional to carbon intensity: $r_{CO2} = -\text{grid\_import\_kwh} \times 0.4521$
   - Directly maps thermal generation to kg CO₂
   - Incentivizes PV self-consumption and BESS discharge during peak hours

2. **Solar Self-Consumption** ($w_{solar} = 0.20$):
   - Rewards using PV generation before battery or grid: $r_{solar} = \frac{\text{pv\_used\_directly}}{(\text{pv\_generated} + 0.1)}$
   - Normalized [0,1] to prevent division by zero during night hours
   - Secondary goal: maximizes renewable utilization

3. **Cost Minimization** ($w_{cost} = 0.10$):
   - Based on tariff: $r_{cost} = -\text{grid\_import\_kwh} \times 0.20$ (USD/kWh)
   - Low weight (0.10) because baseline tariff is already competitive in Iquitos
   - Acts as tie-breaker when CO₂ and solar are equal

4. **EV Satisfaction** ($w_{EV} = 0.10$):
   - Penalizes unmet charger demand: $r_{EV} = -\max(0, \text{charger\_demand} - \text{charger\_power})$
   - Ensures EVs still get charged (baseline service level)

5. **Grid Stability** ($w_{grid} = 0.10$):
   - Penalizes peak demand spikes: $r_{grid} = -\max(0, \text{peak\_power} - \text{baseline\_threshold})$
   - Reduces sudden load swings on isolated grid

**How to Modify**:
1. Edit `src/iquitos_citylearn/oe3/rewards.py::MultiObjectiveWeights` dataclass
2. Ensure new weights sum to ~1.0 (auto-normalized in `__post_init__`)
3. Re-run `train_agents_serial.py` (agents will reload new weights)
4. Compare results: `python -m scripts.run_oe3_co2_table`

**Example**: To prioritize solar usage over CO₂, change to `co2: 0.30, solar: 0.50`

---

## Data Processing Pipeline (OE2 → OE3)

### Phase 1: OE2 Artifact Generation

**Location**: `data/interim/oe2/`

**Inputs** (from external sources):
- **PVGIS TMY data**: Weather normals for Iquitos (5.5°S, 73.3°W)
- **MATLAB charger simulation**: 3,061 vehicles/day, 92% utilization profile

**Outputs** (generated by scripts):
```
data/interim/oe2/
├── solar/
│   ├── pv_generation_timeseries.csv      # 8,760 hourly AC output (kW)
│   ├── solar_technical_report.md         # String/inverter config
│   └── solar_results.json                # Yield, PR, capacity factor
├── chargers/
│   ├── perfil_horario_carga.csv          # 24-hour profile (kW by hour)
│   ├── individual_chargers.json          # 32 chargers × 4 sockets × power_rating
│   └── charger_results.json              # Total 272 kW installed
└── bess/
    └── bess_config.json                  # Fixed: 2 MWh / 1.2 MW
```

**Key validation**:
- Solar timeseries must have exactly 8,760 rows (1 year, hourly)
- Each charger in `individual_chargers.json` must have 4 sockets
- Sum of charger power ratings = 272 kW

### Phase 2: Dataset Construction (run_oe3_build_dataset.py)

**Process**:
1. **Load OE2 artifacts**: Solar, charger profiles, BESS config
2. **Enrich observables**: Add time-of-day, solar availability, BESS state
3. **Build CityLearn schema**: Create `schema.json` with building definition
4. **Validate chargers**: Verify all 128 sockets (32 chargers × 4) discovered
5. **Generate dispatch rules**: Embed priority stack into schema

**Output**: `data/processed/citylearnv2_dataset/` with:
```
citylearnv2_dataset/
├── schema.json                                 # CityLearn environment config
├── climate_zones/
│   └── default_climate_zone/
│       ├── weather.csv                        # PVGIS weather (temp, irradiance)
│       ├── carbon_intensity.csv               # Fixed 0.4521 kg CO₂/kWh
│       └── pricing.csv                        # Tariff 0.20 USD/kWh
└── buildings/
    └── <building_name>/
        ├── energy_simulation.csv              # From OE2 solar + charger load
        └── charger_simulation_<i>.csv         # Per-charger 8,760 profiles
```

**Code pattern**:
```python
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
build_citylearn_dataset(
    cfg=config,
    raw_dir=paths.raw_dir,
    interim_dir=paths.interim_dir,
    processed_dir=paths.processed_dir,
)
```

### Phase 3: Environment Initialization (CityLearn)

**Environment creation**:
```python
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema=schema_path)
obs, info = env.reset()
```

**Observation space** (534 dims when flattened):
- Building energy metrics (solar generation, demand, grid import)
- 128 charger states (power draw, occupancy, battery level per charger)
- Time features (hour, month, day-of-week)
- BESS state (SOC, available power)

**Action space** (126 dims when flattened):
- 126 continuous values in [0, 1] representing charger power setpoints
- Mapped to actual power: `action_power = action_normalized * charger_rated_power`
- Note: Only 126 of 128 chargers are controllable (2 reserved for baseline)

### Data Flow Diagram
```
OE2 Artifacts              Dataset Builder              CityLearn Env
   ↓                            ↓                           ↓
solar_ts.csv ──┐                                    obs (534d)
charger_csv ───┼─→ enrich ──→ schema.json ──→ CityLearnEnv
bess_config.json─                                    action (126d)
```

---

## Agent Architecture Details

### Observation & Action Spaces

**Observation** (534-dimensional when flattened):
```python
# Building-level (per timestep)
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
```

**Action** (126-dimensional, continuous):
```python
# Charger power setpoints (normalized [0,1])
- 126 actions → agent_power_i = action_i × charger_i_max_power
# Examples:
- action_i = 1.0 → charger charges at max capacity
- action_i = 0.5 → charger charges at 50% capacity
- action_i = 0.0 → charger off
```

### Network Architecture

All agents use same **policy network** (stable-baselines3 MlpPolicy):
```
Input Layer (534 dims)
    ↓
Dense(1024, activation=relu)   # Layer 1
    ↓
Dense(1024, activation=relu)   # Layer 2
    ↓
Output Layer (126 dims)        # Action space
```

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
```

**Build & run**:
```bash
docker-compose -f docker-compose.gpu.yml up -d
```

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
```

**Run server**:
```bash
python scripts/fastapi_server.py --port 8000
```

**API usage**:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"observation": [...]}'  # 534-dim array
```

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
```

**Deploy**:
```bash
kubectl apply -f docker/k8s-deployment.yaml
kubectl scale deployment rl-agent-server --replicas 5
```

---



### Unit Testing Pattern
```bash
pytest tests/ -v
```
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

### CityLearn Environment Setup
- **Observation space**: Flattened 534-dim array (building energy, charger states, time features)
- **Action space**: Flattened 126-dim array (126 chargers × power setpoint normalized to [0,1])
- **Episode length**: 8,760 timesteps (1 year) per episode
- **Wrapper requirement**: Some agents need `ListToArrayWrapper` to convert CityLearn's list-based observations to numpy arrays

### Checkpoint Management
- Location: `checkpoints/{SAC,PPO,A2C}/<latest_checkpoint>`
- Auto-resume: `simulate()` checks `reset_num_timesteps=False` to accumulate steps across resumptions
- Metadata: `TRAINING_CHECKPOINTS_SUMMARY_*.json` tracks agent, episode, total_steps, best_reward

### Dispatch Rules in BESS Control
Priority stack (in `configs/default.yaml`):
1. **PV→EV**: Direct solar to chargers (low-cost, zero-loss preferred path)
2. **PV→BESS**: Excess solar charges battery for evening peak
3. **BESS→EV**: Night charging from stored solar energy
4. **BESS→Grid**: Frequency support (if needed)

---

## Docker & Deployment

- **Training container**: `docker-compose.gpu.yml` mounts GPU and runs agent training
- **API endpoint**: `scripts/fastapi_server.py` serves trained agent predictions
- **Kubernetes**: `docker/k8s-deployment.yaml` for multi-agent horizontal scaling

---

## Common Pitfalls & Solutions

| Issue | Solution |
|-------|----------|
| "128 chargers not found" in dataset_builder | Check `data/interim/oe2/chargers/individual_chargers.json` exists; validate all 32 chargers have 4 sockets |
| GPU out of memory during PPO | Reduce `n_steps` from 2048 to 1024; disable `use_amp=False` in config; reduce `batch_size` from 128 to 64 |
| Reward explosion (NaN values) | Verify MultiObjectiveWeights normalized in `__post_init__`; check observation scaling; ensure solar timeseries not all zeros |
| Agent training stuck at negative rewards | Ensure solar timeseries loaded; validate dispatch rules enabled in config; check BESS not over-discharged (SOC < min_soc) |
| Old checkpoint fails to load | Agent class signatures must match checkpoint (if modified, restart from scratch); verify checkpoint path exists |
| Training loops never converge | Check reward signal not flat (add print statements in compute_reward); verify action space is continuous not discrete |
| Solar generation zeros at night causing issues | Expected behavior; rewards should account for nighttime; ensure solar bonus (0.20 weight) uses normalized form |
| Charger profiles all identical | Verify `individual_chargers.json` has unique power ratings per charger (motos 2kW, mototaxis 3kW) |

### Diagnostic Commands

**Check dataset integrity**:
```bash
# Verify schema
python -c "import json; s=json.load(open('outputs/schema_*.json')); print(len(s['buildings']), 'buildings')"

# Verify solar timeseries length
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); print(f'{len(df)} rows')"

# List discovered chargers
python -c "import json; c=json.load(open('data/interim/oe2/chargers/individual_chargers.json')); print(f'{len(c)} chargers, {len(c)*4} sockets')"
```

**Monitor training in real-time**:
```bash
python scripts/monitor_training_live_2026.py
# Output: Updates every 5s with agent name, episode, reward, total timesteps
```

**Check checkpoint compatibility**:
```bash
python -c "from stable_baselines3 import PPO; m=PPO.load('checkpoints/PPO/latest.zip'); print(m.policy)"
```

**Validate environment**:
```bash
python -c "from citylearn.citylearn import CityLearnEnv; e=CityLearnEnv('outputs/schema_*.json'); o,i=e.reset(); print(f'Obs shape: {len(o)} dims')"
```

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
```

**Step 2**: Implement in compute function:
```python
def compute_reward(obs, actions, ...):
    # ... existing components ...
    r_new_metric = calculate_new_metric(obs)  # Return normalized value [0, 1]
    
    # Add to total
    r_total += weights.new_metric * r_new_metric
    return r_total
```

**Step 3**: Test before full training:
```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
# Should complete without errors
```

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
```

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
```

---



## Key References

- **Main README**: [README.md](../README.md) — project scope, OE2 dimensioning specs
- **Reward audit**: [docs/AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md](../docs/) — detailed reward component breakdown
- **Training status**: [docs/INFORME_UNICO_ENTRENAMIENTO_TIER2.md](../docs/) — latest training runs and KPIs
- **Comparison baseline vs RL**: [COMPARACION_BASELINE_VS_RL.txt](../) — quantitative results by agent
