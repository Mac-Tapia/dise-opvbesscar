# Copilot Instructions for Iquitos EV + PV/BESS Project

## Project Overview

**Iquitos EV+PV/BESS** is a reinforcement learning-based control system for electric vehicle charging with solar PV and battery storage integration in Iquitos, Peru. The codebase has three distinct operational tiers:

- **OE1:** Site assessment (location, solar potential, vehicle fleet profile)
- **OE2:** System design/dimensioning (PV array using pvlib+PVGIS, BESS capacity, charger configuration)
- **OE3:** ML-based control optimization (CityLearn v2 environment with SAC/PPO/A2C agents)

## Architecture & Key Components

### OE2: Solar Simulation (Rigorous Sandia Model)
- **Entry point:** `scripts/run_oe2_solar.py`
- **Core module:** [src/iquitos_citylearn/oe2/solar_pvlib.py](src/iquitos_citylearn/oe2/solar_pvlib.py)
- **Key functions:**
  - `build_pv_timeseries_sandia()` — orchestrates pvlib ModelChain with PVGIS TMY data (15-min intervals)
  - `_get_pvgis_tmy()` — downloads hourly Typical Meteorological Year data, applies UTC→Lima timezone adjustment (-5h)
  - `_calculate_string_config()` — optimizes series/parallel strings respecting inverter MPP voltage window
  - `run_pv_simulation()` — ModelChain execution: Perez POA irradiance, Sandia cell temperature, losses
- **Selected components:** Kyocera KS20 (20.2W, 280 W/m²), Eaton Xpert1670 inverter
- **Physics validation:** Performance Ratio ≈123% indicates good irradiance model fit for equatorial location

### OE3: RL Control Environment
- **Entry point:** `scripts/run_oe3_simulate.py` or `scripts/run_training_pipeline.py`
- **Dataset builder:** [src/iquitos_citylearn/oe3/dataset_builder.py](src/iquitos_citylearn/oe3/dataset_builder.py) — constructs CityLearn v2 schema with PV/BESS profiles
- **Reward system:** [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py)
  - **Weights:** CO₂ 0.50 (primary), Solar 0.20, Cost 0.10, EV satisfaction 0.10, Grid stability 0.10
  - **Context-aware:** 0.45 kg CO₂/kWh (thermal grid), 0.20 USD/kWh tariff, peak 19:00h (900 motos + 130 mototaxis)
- **Agents:**
  - SAC (best exploration/stability): [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py)
  - PPO (policy gradient): [src/iquitos_citylearn/oe3/agents/ppo_sb3.py](src/iquitos_citylearn/oe3/agents/ppo_sb3.py)
  - A2C (synchronous actor-critic): [src/iquitos_citylearn/oe3/agents/a2c_sb3.py](src/iquitos_citylearn/oe3/agents/a2c_sb3.py)
- **Agent-to-CityLearn bridge:** `CityLearnWrapper` in each agent class flattens multi-agent obs, unflatten actions, normalizes rewards (scale 0.01), handles truncation→termination conversion

### Configuration & Paths
- **YAML config:** `configs/default.yaml` — all OE1/OE2/OE3 parameters (solar sizing, BESS, fleet, rewards)
- **Path management:** [src/iquitos_citylearn/config.py](src/iquitos_citylearn/config.py) — `load_config()`, `RuntimePaths` dataclass manages `data/interim/oe2/`, `data/processed/`, `reports/`

## Key Patterns & Conventions

### Data Flow Pattern
1. **OE2 output** → `data/interim/oe2/solar/pv_generation_timeseries.csv` (15-min profiles, kWh per interval)
2. **Dataset builder** → reads PV + BESS configs, constructs CityLearn schema JSON
3. **Agents train** on simulated year → save checkpoints in `outputs/checkpoints/{SAC,PPO,A2C}/`
4. **Analysis outputs** → CO₂ tables, reward traces in `analyses/` and `reports/`

### Configuration Pattern
- Config YAML nests OE stages: `oe2.solar.target_dc_kw`, `oe3.rl.train_steps`
- Environment variables override: `GRID_CARBON_INTENSITY_KG_PER_KWH` → `float(cfg['oe3']['grid'][...])` (see `_env_float()`)
- Load with: `from iquitos_citylearn.config import load_config; cfg = load_config("configs/default.yaml")`

### Agent Wrapper Pattern
**All agents (SAC/PPO/A2C) use identical wrapper architecture:**
```python
class CityLearnWrapper(gym.Wrapper):
    def __init__(self, env, smooth_lambda=0.0, normalize_obs=True, normalize_rewards=True, reward_scale=0.01):
        # Flatten multi-agent obs to 1D array + PV/SOC enrichment features
        self.obs_dim = len(obs_flat) + len([pv_kw, bess_soc])
    def step(self, action):
        citylearn_action = self._unflatten_action(action)  # gym Box→list for CityLearn
        obs, reward, terminated, truncated, info = self.env.step(citylearn_action)
        # Convert list reward→scalar, apply normalization (scale 0.01), handle truncation
        normalized_reward = self._normalize_reward(sum(reward))
        return self._flatten(obs), normalized_reward, terminated, truncated, info
```
- **Key normalization:** reward *= 0.01 to keep values in [-10, 10] range (prevents divergence)
- **Action smoothing:** `reward -= smooth_lambda * ||delta_action||` penalizes jerky control

### Reward Multiobjetivo Design
[src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py) implements Iquitos-specific objectives:
- **CO₂ primary (0.50):** minimize grid import (thermal generation 0.45 kg/kWh)
- **Solar secondary (0.20):** maximize local PV consumption (clean energy available on-site)
- **Dynamic peak penalty:** applied in `compute()` when grid import > threshold (hour 18-21h peak)

### Solar Data Timezone Handling
**Critical pattern:** PVGIS returns UTC hourly data. For Iquitos (UTC-5):
```python
# PVGIS hour 5 UTC = 00:00 Lima local → rotate data by -5 hours
utc_offset_hours = 5
tmy_rotated = np.roll(tmy_data.values, -utc_offset_hours, axis=0)
# Create local index in America/Lima timezone
local_times = pd.date_range(start=f"{year}-01-01 00:00:00", periods=len(tmy_data), freq="h", tz="America/Lima")
```
This ensures PV irradiance peaks align with 11:00 AM local time (observed maximum).

### Charger Configuration
- **128 controllable sockets** (not 32 chargers): 31 chargers × 4 sockets/charger
- **Power distribution:** 28 chargers × 4 sockets × 2kW (motos) + 3 chargers × 4 × 3kW (mototaxis) = 272 kW installed
- **Fleet profile:** Daily sessions ~3,061 vehicles, 30-min charging (Modo 3), 92% utilization
- **Encoded in dataset schema** as separate charger_simulation files per socket type

## Common Development Workflows

### Building Solar Profiles
```bash
python scripts/run_oe2_solar.py --config configs/default.yaml --interval 15 --no-plots
```
- Outputs: `data/interim/oe2/solar/{pv_generation_timeseries.csv, solar_results.json, solar_technical_report.md}`
- Generates candidate module/inverter rankings (top 5) in CSVs

### Training an RL Agent
```bash
python scripts/run_training_pipeline.py --config configs/default.yaml --agent sac --episodes 2
```
- Trains SAC for 2 episodes, saves checkpoint to `outputs/checkpoints/SAC/`
- Logs progress to terminal + JSON traces in `analyses/`

### Evaluating Baseline vs RL
```bash
python scripts/run_oe3_simulate.py --dataset <path> --baseline --output reports/baseline_comparison.json
```
- Runs uncontrolled charging (baseline) and trained agent in parallel
- Outputs CO₂, cost, grid peaks, solar % side-by-side

## Critical Gotchas & Fixes

1. **CityLearn truncation handling:** Always convert `truncated=True, terminated=False` → `terminated=True` (CityLearn bug workaround, see agent wrappers)
2. **Reward list→scalar:** CityLearn returns list of rewards; always `sum(reward)` before passing to RL algorithm
3. **Observation flattening:** Multi-agent obs from CityLearn is dict/list; flatten + enrich with PV/SOC before passing to RL
4. **Action unflattening:** RL outputs 1D array; reshape to list of per-agent action vectors before CityLearn.step()
5. **PVGIS data quality:** If PVGIS unavailable (network error), falls back to synthetic TMY (random cloud factor, hourly interpolated). Check log for "WARN Synthetic TMY" messages
6. **Timezone-aware indexing:** Always use `tz="America/Lima"` when creating DatetimeIndex for Iquitos data; naive indices cause DST mismatch

## Testing & Validation

- **Unit tests:** `tests/` (limited coverage; rely on integration tests)
- **Smoke tests:** Run OE2 → OE3 dataset → SAC training with 1 episode (~10 min on CPU)
- **Regression:** Compare new solar results against baseline (expected: annual AC ≈8.31 GWh ±2%, PR ≈123%)
- **RL convergence:** Monitor episode reward trace in `analyses/training_progress_*.json`; should flatten after 100k timesteps

## Entry Points for AI Agents

### Adding a New Agent Algorithm
1. Copy [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py) structure (config dataclass + learn() method)
2. Implement `CityLearnWrapper` with flattening/unflattening logic
3. Register in [src/iquitos_citylearn/oe3/agents/__init__.py](src/iquitos_citylearn/oe3/agents/__init__.py)
4. Update `scripts/run_training_pipeline.py` argument parser

### Modifying Solar Model
- Physics changes: edit [src/iquitos_citylearn/oe2/solar_pvlib.py](src/iquitos_citylearn/oe2/solar_pvlib.py) (pvlib ModelChain, Sandia params)
- Component selection: update `IQUITOS_PARAMS` or `_select_module()`, `_select_inverter()` functions
- Validate: run `run_oe2_solar.py` and verify annual kWh + PR vs known baselines

### Updating Reward Function
- Edit [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py): `MultiObjectiveWeights` dataclass for weight tuning
- **Key rule:** weights must sum to 1.0 (auto-normalized in `__post_init__`)
- Test: run SAC with new weights, check reward trace evolution in `analyses/`

## Language & Style

- **Python 3.11+**, type hints enforced (pyright strict mode in `pyrightconfig.json`)
- **Naming:** CamelCase for classes, snake_case for functions/variables, CONSTANTS for globals
- **Line length:** 120 chars (black, isort configured)
- **Docstrings:** Peruvian Spanish + English (mixed); module-level docstrings describe physics/config parameters
