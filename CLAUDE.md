# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

**pvbesscar** optimizes EV charging for 38 electric sockets (270 motos + 39 mototaxis/day) using solar PV (4,162 kWp DC / 3,201 kW AC; 5.819 GWh/year) + BESS (2,000 kWh / 400 kW) via RL agents (SAC/PPO/A2C) to minimize CO2 in the isolated Iquitos grid (0.4521 kg CO2/kWh).

Two phases:
- **OE2 (Dimensioning)**: Infrastructure specs — solar, BESS, chargers, demand profiles → `src/dimensionamiento/oe2/`
- **OE3 (Control)**: Select the best RL agent to control EV charging and minimize CO₂ → `src/agents/` + `src/citylearnv2/`

**Results (validated):** SAC selected as winner — 55.6% CO₂ reduction vs F₀ (3,123,866 kg/year), corrected PVWatts+bifacial solar model (5.82 GWh/year). Statistical ranking: SAC > PPO ≈ A2C across 50 episodes each.

## Commands

```bash
# Environment setup (Python 3.11 only — 3.12+ not supported)
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt

# Run all tests (OE2 unit + integration)
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/oe2/ -v                    # OE2 data pipeline tests
python -m pytest tests/integration/ -v            # Universal env + site config tests
python -m pytest tests/oe2/test_chargers_config.py::test_iquitos_charger_set_matches_oe2_design -v

# Reproducible example (no dependencies beyond numpy/pandas)
python examples/single_building/run.py --random-agent   # random baseline
python examples/single_building/run.py --episodes 3     # SAC (needs checkpoint)

# Lint / format
black src/ scripts/ --line-length 120
isort src/ scripts/
flake8 src/ scripts/

# Type check
mypy src/

# Regenerar datasets OE2 → CityLearn v2 (pipeline integrado)
python scripts/generate_oe2_datasets.py               # todos los módulos
python scripts/generate_oe2_datasets.py --loader-only # solo data_loader (datos OE2 ya generados)
python scripts/generate_oe2_datasets.py --skip-solar  # saltar solar (usar datos existentes)

# Train agents (current, use _citylearn suffix)
python scripts/train/train_sac_citylearn.py
python scripts/train/train_ppo_citylearn.py
python scripts/train/train_a2c_citylearn.py

# Run baseline (uncontrolled dispatch)
python scripts/train/run_baseline.py

# Generate OE3 figures and tables
python scripts/reporting/generar_graficas_oe3_completo.py
python scripts/reporting/generar_tablas_oe3.py

# Verify data integrity
python -c "import pandas as pd; df=pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'); assert len(df)==8760, f'Solar ERROR: {len(df)} rows'; print(f'Solar OK: {df.energia_kwh.sum():,.0f} kWh/year')"
```

## Architecture

### Data Flow: OE2 → OE3

```
OE2 Generators (run once, or via pipeline — order matters: solar+chargers → BESS)
  solar_pvlib.py   → data/oe2/Generacionsolar/pv_generation_citylearn2024.csv  (8,760h, 5.819 GWh/year) [1]
  chargers.py      → data/oe2/chargers/chargers_ev_ano_2024_v3.csv              (8,760h, 1060 cols) [2]
  bess.py          → data/oe2/bess/bess_ano_2024.csv  (usa solar+chargers reales) (8,760h, 35 cols) [3]
  [external]       → data/oe2/demandamallkwh/demandamallhorakwh.csv             (8,760h, 6 cols)
         ↓ scripts/generate_oe2_datasets.py (pipeline integrado)
  src/dataset_builder_citylearn/data_loader.py (OE2DataLoader)
    — valida schema; OE2ValidationError si datos inconsistentes
    — escribe: data/iquitos_ev_mall/{solar_generation,bess_timeseries,chargers_timeseries,mall_demand}.csv
         ↓
  src/citylearnv2/ev_charging_wrapper.py  ← lee de data/iquitos_ev_mall/ (obs 18D, action 3D)
  src/citylearnv2/env_factory.py          → CityLearnEnv + IquitosEVChargingWrapper
    — obs_dim=18, action_dim=3: [bess_action∈[-1,+1], ev_motos_frac∈[0,1], ev_mototaxis_frac∈[0,1]]
         ↓
  src/agents/{sac,ppo_sb3,a2c_sb3}.py  ← stable-baselines3 + auto-device detection
  checkpoints/{SAC,PPO,A2C}/           ← .zip snapshots; auto-resume si existe
         ↓
  outputs/docx/graficas/               ← PNG figuras para tesis
  outputs/docx/INFORME_OE3_*.docx      ← Word tesis (current: v11)
```

**Observaciones CityLearn v2 (18D):** `[month, hour, day_type, temp, irr_diff, irr_dir, co2_intensity, mall_kw, solar_kw, bess_soc, net_elec, ev_motos_norm, ev_mototaxis_norm, ev_motos_debt, ev_mototaxis_debt, hour_sin, tarifa_norm, is_hora_punta]`

**Señales controladas:** `bess_timeseries.csv` (BESS SOC, dispatch) + `chargers_timeseries.csv` (38 sockets, fracción carga)

**Señales no controladas:** `solar_generation.csv` (PV generation) + `mall_demand.csv` (demanda fija mall)

**Constantes centralizadas:** `src/dimensionamiento/oe2/_constants.py` (tarifas, CO₂, BESS specs), `src/dimensionamiento/oe2/_paths.py` (rutas canónicas)

### Universal Framework (src/core/ + src/rl/)

Site-agnostic layer built on top of the OE2/OE3 Iquitos-specific code. Enables any site worldwide.

```
configs/sites/{name}.yaml           ← site specification (location, grid, buildings, EV fleet)
         ↓ load_site_config()
src/core/site.py                    ← SiteConfig, BuildingConfig, EVFleetConfig, EVVehicleTypeConfig
src/core/energy_balance.py          ← EnergyBalance.step() → PowerFlows (Wali et al. 2025 Eq. 2-11)
src/core/reward.py                  ← UniversalReward (CO2_DUAL_FOCUS v8.0) + RewardWeights presets
src/rl/obs_builder.py               ← obs_dim = 15 + N_types × 3 (scales with fleet)
src/rl/env.py                       ← UniversalPVBESSEnv (Gymnasium-compatible)
         ↓
examples/single_building/run.py     ← reproducible demo (Iquitos validated results)
tests/integration/                  ← 72 tests covering env, config, reward, energy balance
```

**Observation space:** `obs_dim = 15 + N_types × 3`  
`[time(5), solar(5), bess(2), grid(3), EV_type_j(demand_norm, debt_norm, satisfaction) × N_types]`

**Action space:** `dim = 1 + N_types`  
`[bess_action ∈ [-1,+1], ev_frac_j ∈ [0,1] × N_types]`

**Site configs:** `configs/sites/iquitos_bess_mall.yaml` (validated, isolated grid), `configs/sites/lima_parking_ev.yaml` (urban SIN grid, carros eléctricos)

### Key Source Files

| File | Responsibility |
|------|----------------|
| `src/core/site.py` | Universal site/building/fleet config dataclasses + YAML loader |
| `src/core/energy_balance.py` | `EnergyBalance.step()` → `PowerFlows`; BESS SoC dynamics, CO₂ dual accounting |
| `src/core/reward.py` | `UniversalReward` + `RewardWeights` presets (co2_dual_focus, grid_connected, ev_priority) |
| `src/rl/env.py` | `UniversalPVBESSEnv` — site-agnostic Gymnasium env; `from_dataframes()` factory |
| `src/rl/obs_builder.py` | `ObsBuilder` — normalized obs vector, scales with N_types |
| `src/dimensionamiento/oe2/disenocargadoresev/chargers.py` | Charger specs v5.4+ — `@dataclass(frozen=True)` immutable `ChargerSpec`/`ChargerSet`; stochastic EV arrival simulation |
| `src/dataset_builder_citylearn/data_loader.py` | OE2DataLoader v5.8 — single source of truth for all data paths; `OE2ValidationError` on bad data |
| `src/dataset_builder_citylearn/rewards.py` | `MultiObjectiveWeights` — CO2_DUAL_FOCUS v7.5 reward (7 components, weights must sum to 1.0) |
| `src/citylearnv2/env_factory.py` | `create_iquitos_env()` / `create_iquitos_env_for_sb3()` — entry point to training environment |
| `src/citylearnv2/ev_charging_wrapper.py` | `IquitosEVChargingWrapper` — maps 3D action to 38 sockets + integrates CO₂ reward |
| `src/agents/sac.py` | SAC agent with `detect_device()` (CUDA/MPS/CPU auto-select); `_patch_citylearn_sac_update()` for CityLearn compatibility |
| `src/utils/agent_utils.py` | `validate_env_spaces(env)` — must be called before agent init |
| `scripts/train/` | Standalone training launchers — each agent has its own `train_{agent}_citylearn.py` |
| `scripts/analysis/` | Thesis document generation (Word sections, statistical tests) |
| `tests/oe2/` | Unit tests validating OE2 specs and data loader paths |
| `tests/integration/` | Integration tests for universal env, site config, reward, energy balance |

### Reward Function (CO2_DUAL_FOCUS v7.5 — Tres objetivos OE3 equilibrados)

```python
# src/citylearnv2/ev_charging_wrapper.py  ← pesos REALES usados por SAC/PPO/A2C
# Suma: 0.25+0.30+0.25+0.10+0.05+0.03+0.02 = 1.00
_W_DIRECT_CO2   = 0.25  # OE3-1: CO₂ directa — reducción ICE→EV (transporte)
_W_INDIRECT_CO2 = 0.30  # OE3-2: CO₂ indirecta — grid import × 0.4521 kg CO₂/kWh
_W_EV_COMPLETE  = 0.25  # OE3-3: EV satisfaction/cantidad carga (motos+mototaxis)
_W_BESS_SOLAR   = 0.10  # regla op: BESS carga solar(6-18h), NO diesel nocturno
_W_SOLAR        = 0.05  # autoconsumo PV
_W_GRID_STABLE  = 0.03  # estabilidad red (suavizado rampas)
_W_COST         = 0.02  # costo tarifario OSINERGMIN HP(0.45 S/./kWh 18-23h)
                       # Fuente: Electro Oriente S.A. — Res. N° 047-2024-OS/CD
# Evolución: v7.0→v7.1→v7.2→v7.3→v7.4→v7.5 (2026-05-28 current)
# SINCRONIZADO en: ev_charging_wrapper.py, sac/ppo/a2c_config.yaml,
#   agents_config.yaml, sac_optimized.json, default.yaml, default_optimized.yaml,
#   rewards.py (MultiObjectiveWeights), core/reward.py (RewardWeights.co2_dual_focus)
# obs_dim: 18 (base=11 + ev=5 + tarifa=2: tarifa_norm, is_hora_punta)
# SAC: target_entropy=-3.0 (3D action), lr=1e-4, buffer=100k, learning_starts=5000
```

### Checkpoint Resume Pattern

```python
# Agents auto-load latest checkpoint from checkpoints/{AGENT}/ by modification date
agent = make_sac(env)          # scans checkpoints/SAC/
agent.learn(total_timesteps=N, reset_num_timesteps=False)  # accumulates steps across resumptions
```

## Critical Constraints

- **Python 3.11 strictly** — 3.12/3.13 not supported; `from __future__ import annotations` required in every module
- **Solar data: exactly 8,760 hourly rows** — NOT 15-minute data. If given 15-min PVGIS: `df.set_index('time').resample('h').mean()`
- **BESS: 2,000 kWh / 400 kW** — verified from `bess_ano_2024.csv` (max soc_kwh); DoD 80%, min SOC 20%
- **38 sockets**: 19 chargers × 2 sockets (socket_000 to socket_037); 30 motos + 8 mototaxis
- **CityLearn is optional** — not installed in the base env; use `pip install citylearn==2.5.0 --no-deps` in a separate env if needed; `src/citylearnv2` gracefully raises `ModuleNotFoundError` with a clear message if absent
- **`@dataclass(frozen=True)`** for all spec/config containers (see `ChargerSpec`, `ChargerSet`, `MultiObjectiveWeights`)
- **Validate early**: call `validate_env_spaces(env)` before agent init; `OE2DataLoader` raises `OE2ValidationError` immediately on bad paths/schema

## CO₂ Baselines (Resultados OE3 — PVWatts+bifacial, reward v7.5)

| Baseline | CO₂ (kg/año) | Description |
|----------|-------------|-------------|
| F₀ | 7,053,691 | Sin solar, sin BESS, sin RL |
| F₁ | 5,777,812 | Con solar + BESS, sin RL (reference dispatch) |
| **F₂ SAC ep50** | **3,123,866** | Con solar + BESS + SAC — **55.6% reducción vs F₀** |
| F₂ PPO ep50 | 3,370,347 | Con solar + BESS + PPO — 52.2% reducción vs F₀ |
| F₂ A2C ep50 | 3,370,840 | Con solar + BESS + A2C — 52.2% reducción vs F₀ |

Solar PV: **5,819,332 kWh/año** (4,162 kWp PVWatts + 8.7% bifacial, Jinko Tiger Neo JKM580N-72HL4-BDV)
CO₂ factor grid Iquitos: **0.4521 kg CO₂/kWh** (red térmica aislada)
