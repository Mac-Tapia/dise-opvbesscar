# Copilot Instructions - Iquitos CityLearn EV Infrastructure

## Project Overview

This is a **CO₂ emissions reduction pipeline** for electric vehicle (EV) charging infrastructure in Iquitos, Peru. It has two major objectives:

- **OE2**: Dimension solar PV, BESS (battery storage), and EV chargers for a moto/mototaxi fleet
- **OE3**: Evaluate RL-based charging control algorithms using CityLearn simulations

## Architecture

```
scripts/run_pipeline.py    → Orchestrates all stages sequentially
    ├── run_oe2_solar.py   → PV generation (pvlib)
    ├── run_oe2_chargers.py → Charger sizing
    ├── run_oe2_bess.py    → Battery sizing
    ├── run_oe3_build_dataset.py → CityLearn dataset creation
    ├── run_oe3_simulate.py → Agent evaluation
    └── run_oe3_co2_table.py → Final emissions report
```

### Key Data Flow
1. **Config** (`configs/default.yaml`) → All parameters centralized here
2. **OE2 artifacts** → `data/interim/oe2/` (JSON + CSV timeseries)
3. **CityLearn dataset** → `data/processed/citylearn/<name>/`
4. **Reports** → `reports/oe3/co2_comparison_table.{csv,md}`

## Critical Patterns

### Configuration Loading
Always use the centralized config system:
```python
from iquitos_citylearn.config import load_config, load_paths
cfg = load_config(Path("configs/default.yaml"))
rp = load_paths(cfg)  # Returns RuntimePaths dataclass
```

### Script Pattern
All `scripts/run_*.py` follow this structure:
```python
from scripts._common import load_all
cfg, rp = load_all(args.config)
# Access nested config: cfg["oe2"]["solar"]["target_dc_kw"]
```

### Output Dataclasses
Each module returns a frozen dataclass (e.g., `SolarSizingOutput`, `BessSizingOutput`). Results are serialized to JSON via:
```python
pd.Series(output.__dict__).to_json()
```

## RL Agents (OE3) - Detailed Guide

Agents in `src/iquitos_citylearn/oe3/agents/` control EV charging decisions:

| Agent | File | Interface | Purpose |
|-------|------|-----------|---------|
| `UncontrolledChargingAgent` | `uncontrolled.py` | `predict(obs, deterministic)` | Baseline: charge EVs at max, BESS idle |
| `BasicEVRBC` | `rbc.py` | CityLearn's RBC | Rule-based: prioritize solar hours |
| `SAC` | `sac.py` | `learn(episodes)` + `predict()` | RL: Soft Actor-Critic from CityLearn |

### Agent Interface Contract
```python
# Option A: Stable Baselines3 style
def predict(self, observations, deterministic=True) -> action

# Option B: Simple callable
def act(self, observations) -> action
```

### SAC Training Flow (in `simulate.py`)
```python
agent = make_sac(env)
agent.learn(episodes=5)  # Training phase
_run_episode(env, agent, deterministic=True)  # Evaluation
```

### Adding New Agents
1. Create `src/iquitos_citylearn/oe3/agents/my_agent.py`
2. Implement `predict()` or `act()` method
3. Export in `agents/__init__.py`
4. Add to `cfg["oe3"]["evaluation"]["agents"]` list
5. Handle in `simulate.py` agent selection logic

## CityLearn Dataset Integration

The dataset builder (`src/iquitos_citylearn/oe3/dataset_builder.py`) creates CityLearn-compatible datasets:

### Strategy
1. Downloads template from `citylearn.data.DataSet.get_dataset("citylearn_challenge_2022_phase_all_plus_evs")`
2. Copies to `data/processed/citylearn/<name>/`
3. Overwrites CSVs with OE2 results (PV, load, carbon intensity)
4. Updates `schema.json` with PV/BESS capacities

### Schema Manipulation
```python
# Key schema updates
schema["central_agent"] = True
schema["seconds_per_time_step"] = 3600
b["photovoltaic"]["nominal_power"] = pv_dc_kw
b["electrical_storage"]["capacity"] = bess_cap_kwh
```

### Two Schema Variants (for comparison)
- `schema_grid_only.json` → No PV/BESS (baseline)
- `schema_pv_bess.json` → Full system with OE2 sizing

## Development Commands (Python 3.11)

Activate the .venv first so all runs use Python 3.11.

```bash
# Full pipeline
python -m scripts.run_pipeline --config configs/default.yaml

# Individual stages (useful for debugging)
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Install editable
pip install -e .
```

## Validation & Testing Approach

**No formal test suite** - validation is via strict runtime assertions:

### Critical Assertions (DO NOT REMOVE)
| File | Validation | Rationale |
|------|------------|-----------|
| `solar_pvlib.py` | `len(index) == 8760` | Hourly data for full year |
| `solar_pvlib.py` | `annual_kwh >= target * 0.95` | Generation meets design target |
| `bess.py` | `0.7 <= dod <= 0.95` | Realistic battery depth of discharge |
| `bess.py` | `0.85 <= efficiency <= 0.98` | Valid round-trip efficiency |
| `bess.py` | `autonomy_hours >= 24` | Minimum 1-day storage autonomy |

### Manual Validation
Run individual scripts and check outputs:
```bash
python -m scripts.run_oe2_solar --config configs/default.yaml
# Check: data/interim/oe2/solar/solar_results.json
```

## Utility Scripts (LIMPIAR_*.py)

Markdown cleanup utilities for documentation files - **not part of the main pipeline**:

| Script | Purpose |
|--------|---------|
| `LIMPIAR_FINAL.py` | Remove punctuation from headings, fix empty code blocks |
| `LIMPIAR_BACKTICKS.py` | Fix malformed markdown code fences |
| `LIMPIAR_ESPACIOS.py` | Normalize whitespace |
| `VALIDAR_CUMPLIMIENTO_ESTRICTO.py` | Verify project requirements compliance |

Run only when editing documentation:
```bash
python scripts/LIMPIAR_FINAL.py
```

## Environment Variables

Override config via `.env`:
- `GRID_CARBON_INTENSITY_KG_PER_KWH` (default: 0.45)
- `TARIFF_USD_PER_KWH` (default: 0.20)

## Dependencies

Core: `pvlib` (solar), `citylearn>=2.5.0` (simulation), `torch` (RL agents), `gymnasium` (RL environments)

## File Naming Conventions

- Scripts: `run_<stage>_<component>.py` (pipeline) or `LIMPIAR_*.py` (utilities)
- Outputs: `*_results.json` (summary), `*_timeseries.csv` (hourly data)
- Reports always include `.csv` + `.md` versions

## Location Context

All calculations assume Iquitos, Peru: **lat=-3.7437, lon=-73.2516, tz=America/Lima**
