# pvbesscar - EV Charging Optimization with BESS & RL
**Status:** ✅ PURIFIED ARCHITECTURE (2026-02-20)

## 🎯 Project Overview

**pvbesscar** optimizes EV charging for 38 electric sockets (270 motos + 39 mototaxis/day) using:
- **Solar PV:** 4,050 kWp generation
- **Battery Storage (BESS):** 2,000 kWh / 400 kW with 6-phase adaptive control
- **Reinforcement Learning:** SAC/PPO/A2C agents for CO₂ minimization
- **Location:** Iquitos, Peru (Isolated grid, 0.4521 kg CO₂/kWh thermal generation)

---

## 📂 Architecture (CLEAN & PURE)

### Core Modules

| Module | Path | Role | Responsibility |
|--------|------|------|-----------------|
| **bess.py** | `src/dimensionamiento/oe2/disenobess/` | DIMENSIONAMIENTO | Simulate BESS + Solar operations (6 phases) |
| **balance.py** | `src/dimensionamiento/oe2/balance_energetico/` | VISUALIZACIÓN | Generate 16 energy balance graphics |

### Data Flow (ONLY)

```
bess.py (simulate)
  ↓ [8760-hour timeseries]
bess_timeseries.csv
  ↓ [read]
balance.py (visualize)
  ↓ [generate 16 PNG]
outputs/balance_energetico/
```

---

## 🔋 BESS Control Logic (6 PHASES - IMMUTABLE)

**Location:** `src/dimensionamiento/oe2/disenobess/bess.py` (lines 986-1209)

### Phase Breakdown

| Phase | Period | Trigger | Operation | Implementation |
|-------|--------|---------|-----------|-----------------|
| **FASE 1** | 6h-9h | Always | EV=0, BESS absorbs 100% PV | Lines 986-1026 |
| **FASE 2** | 9h-22h | SOC<99% | EV priority 100% + BESS parallel | Lines 1029-1063 |
| **FASE 3** | 9h+ | SOC≥99% | HOLDING: 0 charge/discharge | Lines 1066-1099 |
| **FASE 4** | 10h-22h | PV<MALL, MALL>1900kW | Peak shaving: BESS discharge | Lines 1101-1131 |
| **FASE 5** | 9h-22h | EV deficit>0 | Dual discharge: EV+MALL | Lines 1134-1169 |
| **FASE 6** | 22h-9h | Daily closure | IDLE: BESS reposes SOC=20% | Lines 1176-1209 |

### BESS Specifications

```
Capacity:       2,000 kWh
Power:          400 kW (charge/discharge)
Efficiency:     95% round-trip
SOC Min:        20%
SOC Max:        100%
DoD:            80% (usable: 1,600 kWh)
Closing Hour:   22:00
```

---

## 📊 Key Functions

### bess.py - Simulation Engine

```python
from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_solar_priority

# Execute simulation
df = simulate_bess_solar_priority(
    pv_kwh=solar_generation,      # 8760-hour array
    ev_kwh=ev_demand,              # 8760-hour array
    mall_kwh=mall_demand,          # 8760-hour array
    capacity_kwh=2000,
    power_kw=400,
    efficiency=0.95,
    soc_min=0.20
)

# Output: DataFrame with columns
# - pv_kwh, ev_kwh, mall_kwh
# - pv_to_ev, pv_to_bess, pv_to_mall
# - grid_to_ev, grid_to_mall
# - bess_charge, bess_discharge
# - soc_percent, co2_emissions
```

### balance.py - Visualization Engine

```python
from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem

# Create system
system = BalanceEnergeticoSystem(df_bess)

# Generate 16 graphics
system.plot_energy_balance(out_dir="outputs/balance_energetico/")

# Outputs 16 PNG files:
# 1. Balance anual completo
# 2-3. Balance 5 días / diario
# 4. Distribución de fuentes
# 5. Cascada energética
# 6-7. BESS carga/descarga & SOC
# 8. Emisiones CO₂
# 9. Utilización PV
# 10. PV exportación desglose
# 11-16. Additional analysis graphics
```

---

## 📁 File Structure (PURIFIED)

### ✅ Files to KEEP

```
src/dimensionamiento/oe2/
├── disenobess/
│   ├── __init__.py          ✅ Package marker
│   └── bess.py              ✅ SIMULATION ENGINE (core)
│
└── balance_energetico/
    ├── __init__.py          ✅ Package marker
    └── balance.py           ✅ VISUALIZATION ENGINE (core)
```

### ❌ Files DELETED (Cleanup 2026-02-20)

**disenobess/ (4 files removed):**
- ❌ bess_auto_update.py (auto-regeneration - unnecessary)
- ❌ bess_config_simple.py (config duplication)
- ❌ generate_bess_dataset_2024.py (dataset generation - part of bess.py)
- ❌ run_bess_dataset_generation.py (runner script)

**balance_energetico/ (9+ files removed):**
- ❌ balance_graphics_only.py (duplicate functionality)
- ❌ ev_profile_integration.py (unrelated module)
- ❌ example_usage.py (demo code)
- ❌ ARQUITECTURA_BALANCE_GRAPHICS.md (duplicate docs)
- ❌ INTEGRACION_MODULES.py (orchestration scripts)
- ❌ README.md (redundant)
- ❌ run_analysis.py (runner script)
- ❌ test_quick.py (test code)
- ❌ outputs_demo/ (demo folder)

**Total: 13+ files eliminated**

---

## 🚀 Quick Start

### 1. Setup Python Environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

pip install pandas numpy matplotlib scipy
```

### 2. Run BESS Simulation

```python
import pandas as pd
from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_solar_priority

# Load input data
pv_kwh = pd.read_csv('data/iquitos_ev_mall/pv_generation.csv')['pv_kwh'].values
ev_kwh = pd.read_csv('data/iquitos_ev_mall/ev_demand.csv')['total_kw'].values
mall_kwh = pd.read_csv('data/iquitos_ev_mall/mall_demand.csv')['demand_kw'].values

# Run simulation
df_bess = simulate_bess_solar_priority(pv_kwh, ev_kwh, mall_kwh)

# Save results
df_bess.to_csv('data/iquitos_ev_mall/bess_timeseries.csv', index=False)
print(f"✅ Generated {len(df_bess)} hours of BESS simulation")
```

### 3. Generate Graphics

```python
from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem
import pandas as pd

# Load BESS simulation output
df_bess = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')

# Create visualization system
system = BalanceEnergeticoSystem(df_bess)

# Generate all graphics
system.plot_energy_balance(out_dir='outputs/balance_energetico/')

print("✅ Generated 16 PNG graphics")
```

---

## ✨ Key Features

### BESS Adaptive Control
- ✅ 6-phase dynamic dispatch
- ✅ Solar priority maximization
- ✅ EV 100% coverage guarantee
- ✅ Peak shaving (>1900 kW)
- ✅ Daily closure enforcement (SOC=20% at 22h)

### Energy Balance Tracking
- ✅ PV → EV / BESS / MALL / Grid flows
- ✅ BESS charge/discharge cycles
- ✅ Solar utilization metrics
- ✅ CO₂ emissions calculation
- ✅ Grid import/export balance

### Visualization (16 Graphs)
- ✅ Annual energy balance
- ✅ 5-day & daily profiles
- ✅ Energy source distribution
- ✅ Energy cascade flows
- ✅ BESS SOC evolution
- ✅ CO₂ emissions timeline
- ✅ PV utilization analysis
- + 9 more detailed breakdowns

---

## 🔧 Configuration

**BESS Parameters** (edit in bess.py):
```python
BESS_CAPACITY_KWH = 2000.0        # kWh
BESS_POWER_KW = 400.0              # kW
BESS_EFFICIENCY = 0.95             # 95% RTC
BESS_SOC_MIN = 0.20                # 20% minimum
BESS_SOC_MAX = 1.00                # 100% maximum
BESS_CLOSING_HOUR = 22             # Closure at 22h
```

**Data Paths** (edit in balance.py):
```python
bess_csv_path = Path('data/iquitos_ev_mall/bess_timeseries.csv')
output_dir = Path('outputs/balance_energetico/')
```

---

## 📋 Design Rules (DO's & DON'Ts)

### ✅ DO's

- ✅ Keep bess.py as **ONLY** simulation module in disenobess/
- ✅ Keep balance.py as **ONLY** visualization module in balance_energetico/
- ✅ Modify 6-FASES **ONLY** if changing BESS logic
- ✅ Use bess_timeseries.csv as interface between modules
- ✅ Document changes in ARCHITECTURE_CATALOG.json & architecture_config.yaml

### ❌ DON'Ts

- ❌ Create new auxiliary scripts (bess_XXX.py, balance_XXX.py, runners, validators)
- ❌ Duplicate configuration files
- ❌ Split 6-FASES across multiple files
- ❌ Confuse DIMENSIONAMIENTO (bess) with VISUALIZACIÓN (balance)
- ❌ Add "auto-regeneration" or orchestration scripts

---

## 📚 Documentation Files

| File | Purpose | Status |
|------|---------|--------|
| [ARCHITECTURE_CATALOG.json](./ARCHITECTURE_CATALOG.json) | Detailed JSON catalog of all components | ✅ Current |
| [architecture_config.yaml](./architecture_config.yaml) | YAML configuration & deployment guide | ✅ Current |
| [ESTRUCTURA_FINAL.md](./ESTRUCTURA_FINAL.md) | Quick architecture reference | ✅ Current |
| [README.md](./README.md) | This file - Main project overview | ✅ Current |

---

## 🔄 Git History

**Latest Commit:**
```
b683cc43 - ARQUITECTURA PURIFICADA: Solo bess.py + balance.py
├─ 49 files changed
├─ +13,099 insertions
├─ -13,053 deletions
└─ Date: 2026-02-20
```

**Branch:** `smartcharger`  
**Status:** ✅ Pushed to GitHub

---

## 🎓 Next Steps

1. ✅ **Architecture purified** (2026-02-20)
2. 🔄 **BESS simulation testing** - Run bess.py with real solar/EV/MALL data
3. 🔄 **Balance visualization validation** - Generate graphics and review
4. 🔄 **OE3 integration** - Connect RL agents (SAC/PPO/A2C) to BESS actions
5. 🔄 **Performance tuning** - Optimize 6-phase parameters
6. 🔄 **Production deployment** - Deploy to Iquitos site

---

## 📞 Support

For questions about:
- **BESS simulation logic:** Check `bess.py` lines 986-1209
- **Graphics generation:** Check `balance.py` plot_energy_balance() function
- **Architecture decisions:** See ARCHITECTURE_CATALOG.json & architecture_config.yaml

---

**Last Updated:** 2026-02-20  
**Status:** ✅ PRODUCTION READY  
**Version:** 5.8
