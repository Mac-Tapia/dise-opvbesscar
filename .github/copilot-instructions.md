# Copilot Instructions - Iquitos CityLearn EV Infrastructure

## Project Overview

CO₂ emissions reduction pipeline for EV charging infrastructure in Iquitos, Peru (lat=-3.75, lon=-73.25, tz=America/Lima). Three objectives:

- **OE1**: Strategic location analysis (Mall de Iquitos site viability)
- **OE2**: Dimension solar PV (4162 kW DC), BESS (2000 kWh), and 128 chargers for 1030 vehicles (900 motos + 130 mototaxis)
- **OE3**: Evaluate RL agents (SAC, PPO, A2C, Uncontrolled) using CityLearn with 2 buildings (Playa_Motos, Playa_Mototaxis) and multi-objective rewards

## Architecture & Data Flow

```
scripts/run_pipeline.py     → Orchestrates all stages
    ├── run_oe1_location.py → Site viability (→ reports/oe1/)
    ├── run_oe2_solar.py    → PV sizing via pvlib + PVGIS TMY
    ├── run_oe2_chargers.py → 128 chargers (112 motos + 16 mototaxis) sizing
    ├── run_oe2_bess.py     → Battery: 2000kWh/1200kW fixed mode
    ├── run_oe3_build_dataset.py → CityLearn dataset from OE2
    ├── run_oe3_simulate.py → Multi-agent training + evaluation
    └── run_oe3_co2_table.py → Emissions comparison report
```

**Outputs**: `data/interim/oe2/` (JSON+CSV) → `data/processed/citylearn/iquitos_ev_mall/` → `analyses/oe3/`

## Critical Patterns

### Configuration & Script Entry

```python
# All scripts use _common.py (enforces Python 3.11)
from scripts._common import load_all
cfg, rp = load_all(args.config)  # cfg dict, rp = RuntimePaths dataclass

# Nested access: cfg["oe2"]["solar"]["target_dc_kw"], cfg["oe3"]["evaluation"]["agents"]
```

### Output Dataclasses

Each OE2/OE3 module returns a frozen dataclass serialized to JSON:

- `SolarSizingOutput` → `data/interim/oe2/solar/solar_results.json`
- `BessSizingOutput` → `data/interim/oe2/bess/bess_results.json`
- `SimulationResult` → `outputs/oe3/simulations/<agent>_*.json`

## RL Agents (OE3)

Located in `src/iquitos_citylearn/oe3/agents/`:

| Agent | Factory | Training | Purpose |
|-------|---------|----------|---------|
| `Uncontrolled` | `UncontrolledChargingAgent()` | None | Baseline: max charge |
| `SAC` | `make_sac(env, cfg)` | `learn(episodes)` | Soft Actor-Critic |
| `PPO` | `make_ppo(env, cfg)` | `learn(timesteps)` | Proximal Policy Opt. |
| `A2C` | `make_a2c(env, cfg)` | `learn(timesteps)` | Advantage Actor-Critic |

### Multi-Objective Rewards (`oe3/rewards.py`)

Configured via `cfg["oe3"]["evaluation"]["sac"]["multi_objective_weights"]`:

```yaml
multi_objective_weights:
  co2: 0.50      # Minimize emissions
  cost: 0.15     # Minimize electricity cost
  solar: 0.20    # Maximize self-consumption
  ev: 0.10       # EV charging satisfaction
  grid: 0.05     # Grid stability (peak shaving)
```

### Adding New Agents

1. Create `src/iquitos_citylearn/oe3/agents/my_agent.py` with `predict(obs, deterministic)` method
2. Export in `agents/__init__.py`
3. Add to `cfg["oe3"]["evaluation"]["agents"]` list
4. Handle instantiation in `simulate.py`

## CityLearn Dataset

`dataset_builder.py` creates CityLearn-compatible datasets with **2 separate buildings**:

1. Downloads template: `citylearn_challenge_2022_phase_all_plus_evs`
2. Creates 2 buildings representing separate parking areas ("playas"):
   - **Playa_Motos**: 112 chargers (2 kW each), 3641.8 kWp PV, 1750 kWh BESS
   - **Playa_Mototaxis**: 16 chargers (3 kW each), 520.2 kWp PV, 250 kWh BESS
3. Overwrites CSVs with OE2 artifacts (PV timeseries, carbon intensity)
4. Generates 128 charger simulation CSVs (112 MOTO + 16 MOTOTAXI)
5. Generates two schemas for comparison:
   - `schema_grid_only.json` → No PV/BESS (grid-only baseline)
   - `schema_pv_bess.json` → Full OE2 system with both buildings

### Infrastructure Distribution (87.5% / 12.5%)

| Component | Playa_Motos | Playa_Mototaxis | Total |
|-----------|-------------|-----------------|-------|
| Chargers | 112 (2 kW) | 16 (3 kW) | 128 |
| Power | 224 kW | 48 kW | 272 kW |
| PV | 3641.8 kWp | 520.2 kWp | 4162 kWp |
| BESS | 1750 kWh | 250 kWh | 2000 kWh |

## Development Commands

```bash
# Activate venv (Python 3.11 required - enforced at runtime)
.venv\Scripts\activate  # Windows

# Full pipeline
python -m scripts.run_pipeline --config configs/default.yaml

# Individual stages (for debugging)
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Install as editable package
pip install -e .
```

## Validation (No Test Suite)

Validation via runtime assertions - **DO NOT REMOVE**:

- `solar_pvlib.py`: `len(index) == 8760` (full year), `annual_kwh >= target * 0.95`
- `bess.py`: DoD 0.7-0.95, efficiency 0.85-0.98

## Environment Variables

Override via `.env`:

- `GRID_CARBON_INTENSITY_KG_PER_KWH` (default: 0.4521 kg/kWh - Iquitos thermal grid)
- `TARIFF_USD_PER_KWH` (default: 0.20)

## Key Dependencies

`pvlib` (solar), `citylearn>=2.5.0` (simulation), `torch` (RL), `stable-baselines3` (PPO/A2C)

## Checkpoint & Resume Training

RL agents support checkpoint-based training recovery. Checkpoints are saved every N steps and can resume interrupted training.

**Config keys** (`cfg["oe3"]["evaluation"]["sac"]`):
```yaml
resume_checkpoints: true          # Enable resume from last checkpoint
checkpoint_freq_steps: 1000       # Save every 1000 steps
save_final: true                  # Save final model as <agent>_final.zip
```

**Checkpoint locations**: `outputs/oe3/checkpoints/<agent>/`
- `sac_step_1000.zip`, `sac_step_2000.zip`, ... (incremental)
- `sac_final.zip` (after training completes)

**Resume logic** (`simulate.py` → `_latest_checkpoint()`): Automatically finds highest step checkpoint or `*_final.zip`.

## GPU/CUDA Configuration

Agents auto-detect GPU via `detect_device()` in `oe3/agents/sac.py`:
- **CUDA** (NVIDIA): Preferred, set `device: cuda` in config
- **MPS** (Apple Silicon): Auto-detected
- **CPU**: Fallback when no GPU available

**Config keys**:
```yaml
device: cuda          # Force CUDA (or "cpu", "mps", "auto")
use_amp: true         # Mixed precision (faster on modern GPUs)
batch_size: 1024      # Increase for GPU memory utilization
```

**Verify GPU**: Run `python -c "import torch; print(torch.cuda.is_available())"` before training.

## Training Episodes & Recommendations

**Current config** (`episodes: 5`) is for **quick testing/debugging**. For production results:

| Agent | Testing | Production | Notes |
|-------|---------|------------|-------|
| SAC   | 5 eps   | 50-100 eps | `learn(episodes=N)` |
| PPO   | 43800 steps | 438000 steps | `timesteps` param (10x) |
| A2C   | 5 eps   | 50 eps | Similar to SAC |

**Recommendation**: For final CO₂ comparison reports, increase `episodes` 10x and enable `resume_checkpoints: true` for fault tolerance.

## LIMPIAR_*.py Scripts

**Status**: Active utilities for documentation post-processing. **NOT part of main pipeline**.

| Script | Purpose | When to use |
|--------|---------|-------------|
| `LIMPIAR_FINAL.py` | Remove punctuation from headings, fix code blocks | After generating reports |
| `LIMPIAR_BACKTICKS.py` | Fix malformed markdown fences | Broken `.md` files |
| `LIMPIAR_ESPACIOS.py` | Normalize whitespace | Before commits |
| `LIMPIAR_CUMPLIMIENTO.py` | Clean compliance docs | Specific to `CUMPLIMIENTO*.md` |
| `VALIDAR_CUMPLIMIENTO_ESTRICTO.py` | Verify project requirements | Before submission |

**Usage**: Run manually when editing documentation:
```bash
python scripts/LIMPIAR_FINAL.py <file.md>
```

## File Conventions

- Scripts: `run_<stage>_<component>.py` | `LIMPIAR_*.py` (doc cleanup utilities, not pipeline)
- Outputs: `*_results.json` (summary) + `*_timeseries.csv` (hourly)
- Reports: Always dual `.csv` + `.md` versions
