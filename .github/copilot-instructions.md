# Copilot Instructions - Iquitos EV Smart Charging Infrastructure

## Project Overview

Validates smart EV charging infrastructure (4162 kWp PV + 2000 kWh BESS + 128 chargers) in Iquitos using RL to reduce CO₂ in an isolated thermal grid (0.4521 kg/kWh).

**3-Phase Structure (OE1 → OE2 → OE3)**:
- **OE1**: Site feasibility (Mall Iquitos: 20,637 m² rooftop)
- **OE2**: Technical sizing (8.042 GWh/year solar + BESS + chargers)
- **OE3**: RL evaluation (SAC/PPO/A2C + CityLearn) with CO₂ + cost metrics

## Architecture

### Sequential Pipeline ([scripts/run_pipeline.py](scripts/run_pipeline.py))
```
OE2 (parallelizable) → OE3 (sequential)
├─ run_oe2_solar.py      → 8760h PV profile → data/interim/oe2/solar/
├─ run_oe2_chargers.py   → 128 profiles (112 motos 2kW + 16 mototaxis 3kW)
├─ run_oe2_bess.py       → 2000 kWh BESS → data/interim/oe2/bess/
├─ run_oe3_build_dataset.py → CityLearn schemas (2 buildings)
├─ run_oe3_simulate.py   → Train SAC|PPO|A2C agents
└─ run_oe3_co2_table.py  → CO₂ comparison table
```

### Key Code Patterns

**Frozen Dataclasses** - All outputs use `@dataclass(frozen=True)`. Never modify post-creation:
```python
from dataclasses import dataclass, asdict
@dataclass(frozen=True)
class SolarSizingOutput:
    annual_kwh: float
    ...
# Serialize: json.dump(asdict(output))
# Deserialize: SolarSizingOutput(**json.load())
```

**Configuration Loading** - All scripts use this pattern:
```python
from scripts._common import load_all
cfg, rp = load_all("configs/default.yaml")
rp.ensure()  # Create directories
pv_kw = cfg["oe2"]["solar"]["target_dc_kw"]
```

**RL Agent Interface** - All agents in [src/iquitos_citylearn/oe3/agents/](src/iquitos_citylearn/oe3/agents/) implement:
```python
def predict(self, observations, deterministic=True) -> List[List[float]]:
    # Returns actions for each building/agent
```

## Development Commands

```bash
.venv\Scripts\activate              # REQUIRED: Python 3.11 (validated at runtime)
pip install -e .                    # First-time setup

python -m scripts.run_pipeline --config configs/default.yaml  # Full pipeline (~2-6h)
python -m scripts.run_oe2_solar --config configs/default.yaml # Individual stages
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Resume interrupted training (auto-detects latest checkpoint)
python -m scripts.continue_sac_training --config configs/default.yaml
python monitor_checkpoints.py       # Live training progress
```

## Critical Validations (No pytest suite)

Runtime assertions in modules - **DO NOT REMOVE**:
- `solar_pvlib.py`: `len(index) == 8760` (complete year)
- `bess.py`: DoD 0.7-0.95, efficiency 0.85-0.98
- `dataset_builder.py`: Validates 128 charger CSVs, JSON schemas

## GPU/CUDA Configuration

Auto-detected via `detect_device()` in [sac.py](src/iquitos_citylearn/oe3/agents/sac.py):
```yaml
# configs/default.yaml
device: cuda    # or "cpu", "mps", "auto"
use_amp: true   # Mixed precision (faster on modern GPUs)
```
Verify: `python -c "import torch; print(torch.cuda.is_available())"`

## Multi-Objective Rewards ([rewards.py](src/iquitos_citylearn/oe3/rewards.py))

5 normalized objectives (sum=1.0):
- `co2: 0.50` - Minimize emissions
- `cost: 0.15` - Minimize electricity cost
- `solar: 0.20` - Maximize self-consumption
- `ev: 0.10` - EV charging satisfaction
- `grid: 0.05` - Grid stability

## RL Agents Status (Production Ready ✅)

| Agent | Class | Implementation | Status |
|-------|-------|----------------|--------|
| SAC | `SACAgent` | Pure PyTorch (1000+ lines) | ✅ Verified |
| PPO | `PPOAgent` | stable-baselines3 wrapper | ✅ Verified |
| A2C | `A2CAgent` | stable-baselines3 wrapper | ✅ Verified |
| Uncontrolled | `UncontrolledChargingAgent` | Baseline (max charge) | ✅ Verified |
| NoControl | `NoControlAgent` | Baseline (action=0) | ✅ Verified |

**Latest Results** (simulation_summary.json):
- Baseline (no PV): 11,282,200 kg CO₂
- SAC: 7,547,021 kg CO₂ (**Best** - 1.49% reduction vs Uncontrolled)
- PPO: 7,578,734 kg CO₂
- A2C: 7,615,072 kg CO₂

## Common Errors

| Error | Solution |
|-------|----------|
| `RuntimeError: Python 3.11 is required` | Activate venv: `.venv\Scripts\activate` |
| `FileNotFoundError` in CSVs | Run OE2 stages before OE3 |
| GPU not detected | Use `device: cpu` in config |
| `dataset_builder.py` failures | Verify `data/interim/oe2/` artifacts exist |

## Key Files

| Path | Purpose |
|------|---------|
| [configs/default.yaml](configs/default.yaml) | All project parameters |
| [scripts/_common.py](scripts/_common.py) | Config loader + Python version check |
| [src/iquitos_citylearn/oe3/simulate.py](src/iquitos_citylearn/oe3/simulate.py) | Main RL training loop |
| `outputs/oe3/checkpoints/<agent>/` | Checkpoint files (`*_step_N.zip`, `*_final.zip`) |
| `data/interim/oe2/` | OE2 artifacts (solar, bess, chargers) |
