# Architecture Documentation Summary (2026-02-14)

**Updated:** 2026-02-14 | **Status:** Production-Ready | **Contributors:** pvbesscar Team

---

## What Was Just Completed

### New Documentation Created

1. **[DATA_SOURCES_REAL_VS_SIMULATED.md](docs/DATA_SOURCES_REAL_VS_SIMULATED.md)** (Complete Reference)
   - Maps every data source to its origin: ✅ REAL (measured) or ⚠️ SIMULATED (calculated)
   - Shows dependency graph: OE2 → OE3 pipeline
   - Answers 5 common questions about data reliability
   - Validation checklist for dataset integrity
   - ~700 lines, comprehensive reference

2. **[DATA_SOURCES_QUICK_CARD.md](docs/DATA_SOURCES_QUICK_CARD.md)** (One-Page Summary)
   - Printable quick reference card
   - Status table: Solar ✅, Chargers ✅, Mall ✅, BESS ⚠️
   - Key file locations and diagnostic commands
   - 1-minute validation checklist
   - Common issues & fixes table

3. **Updated Copilot Instructions** (.github/copilot-instructions.md)
   - References new DATA_SOURCES guides
   - Synced with production codebase

4. **Updated Documentation Index** (ÍNDICE_DOCUMENTACIÓN_ARQUITECTURA.md)
   - Added entries for new data source documentation
   - Organized by learning time (5 min → 30 min)

### Code Alignment

The training scripts already implement correct status markers:
- [scripts/train/train_sac_multiobjetivo.py](scripts/train/train_sac_multiobjetivo.py) lines 193-333
  - ✅ Solar loading (line 197)
  - ✅ Chargers loading (line 223)
  - ✅ Mall loading (line 254)
  - ⚠️ BESS loading (line 273) with clear "SIMULATED" label
  - Validation for 8,760 hourly rows enforced

---

## Quick Facts About Data

### ✅ REAL Sources (Measured / Ground Truth)
| Data | Annual Qty | Key Constraint | Use in RL |
|------|-----------|-----------------|-----------|
| **Solar PV** | ~8,000 MWh | 8,760h hourly | Maximize direct use |
| **Chargers (38 sockets)** | ~19,500 kWh | 38 cols × 8,760h | Hard demand constraint |
| **Shopping Mall** | ~875 MWh | 100 kW avg | Non-controllable baseline |

### ⚠️ SIMULATED Sources (Calculated / Reference Baseline)
| Data | Annual Qty | Purpose | Note |
|------|-----------|---------|------|
| **BESS Dispatch** | SOC 0-100% | OE2 baseline trajectory | RL agent replaces this |

### 🧮 DERIVED Sources (Runtime Outputs)
| Component | Source | Role |
|-----------|--------|------|
| **Observations** | Merged: SOLAR + CHARGERS + MALL + BESS + TIME | RL input (394-dim) |
| **Rewards** | CO₂ factor (0.4521 kg/kWh) × Grid import | RL objective |
| **Actions** | SAC/PPO/A2C policy | BESS + 38 socket setpoints |

---

## Why This Matters for Development

### Problem Solved
**Before:** Unclear distinction between ground truth (measured) vs reference (simulated) data  
**After:** Every data source labeled ✅ or ⚠️, with dependency graph and validation rules

### Impact
1. **Data Quality:** Developers know which CSV files represent measured reality vs calculated baselines
2. **Training Confidence:** RL training starts with validated data sources
3. **Reproducibility:** Clear record of which data is immutable (solar, chargers, mall) vs replaceable (BESS dispatch)
4. **Maintenance:** Documentation maps changes → impacts (e.g., changing BESS capacity requires retraining)

---

## How to Use This Documentation

### For Data Engineers
→ Read **[DATA_SOURCES_REAL_VS_SIMULATED.md](docs/DATA_SOURCES_REAL_VS_SIMULATED.md)**
- Complete mapping of data flows
- Validation rules per dataset
- How each raw data becomes RL observations

### For ML Engineers (Training)
→ Read **[DATA_SOURCES_QUICK_CARD.md](docs/DATA_SOURCES_QUICK_CARD.md)**
- Status table (✅ REAL | ⚠️ SIMULATED)
- 1-minute validation checklist
- Common diagnostic commands

### For Project Managers
→ Read this summary + [ARQUITECTURA_GUÍA_RÁPIDA.md](ARQUITECTURA_GUÍA_RÁPIDA.md)
- What data is stable (✅ REAL) vs what changes (⚠️ SIMULATED)
- Dependencies between OE2 and OE3 phases
- Training pipeline overview

---

## Key Architecture Facts (Updated 2026-02-14)

### Infrastructure (Immutable)
- **Solar:** 4,050 kWp (photovoltaic array installed)
- **Chargers:** 19 units × 2 sockets = **38 total sockets** (Mode 3, 7.4 kW each)
- **BESS:** 1,700 kWh max SOC storage
- **Grid:** Isolated system (Iquitos, Perú, ~0.4521 kg CO₂/kWh from diesel)

### Data Requirements (Verified)
- **Temporal resolution:** 1 hour (NOT 15-min)
- **Time span:** 8,760 hours (365 days × 24 hours, 1 full year)
- **Validation:** Enforced in dataset_builder.py
- **Status:** ✅ REAL for solar/chargers/mall, ⚠️ SIMULATED for BESS baseline

### RL Training Setup
- **Environment:** CityLearn v2
- **Agents:** SAC, PPO, A2C (stable-baselines3)
- **Observation space:** 394-dimensional (solar, chargers, temps, BESS, time)
- **Action space:** 39-dimensional (1 BESS + 38 socket setpoints, [0,1])
- **Reward:** Multi-objective (CO₂ 50% weight, solar util 20%, EV completion 15%, stability 10%, cost 5%)

---

## Files Modified on 2026-02-14

### Created
- `docs/DATA_SOURCES_REAL_VS_SIMULATED.md` (700 lines)
- `docs/DATA_SOURCES_QUICK_CARD.md` (200 lines)
- `DOCUMENTATION_SUMMARY_2026-02-14.md` (this file)

### Updated
- `.github/copilot-instructions.md` - Added reference to new data source documentation
- `ÍNDICE_DOCUMENTACIÓN_ARQUITECTURA.md` - Added two new entries in "¿DÓNDE BUSCAR QUÉ?" section

### No Changes Required
- Training scripts already have correct status markers
- Data loading logic already validated
- Environment specs confirmed (38 sockets, 1,700 kWh BESS, etc.)

---

## Cross-References

### From Copilot Instructions
- **Line ~180:** "Data Sources Map" now points to `docs/DATA_SOURCES_REAL_VS_SIMULATED.md`
- **Multi-Objective Reward Function:** Details in same doc, section "Multi-Objective Reward Function"

### From ÍNDICE_DOCUMENTACIÓN_ARQUITECTURA.md
```markdown
### 🔍 Necesito entender cuales datos son REALES vs SIMULADOS (15 min)
→ docs/DATA_SOURCES_REAL_VS_SIMULATED.md

### 📋 Necesito TARJETA RÁPIDA de datos (1 página, imprimible)
→ docs/DATA_SOURCES_QUICK_CARD.md
```

---

## Validation Status ✓

- [x] Data sources documented (✅ REAL vs ⚠️ SIMULATED)
- [x] Dependency graph created (OE2 → OE3)
- [x] Validation rules specified
- [x] Quick reference card created (printable)
- [x] Training script confirmed (data loading markers in place)
- [x] Copilot instructions updated
- [x] Documentation index updated

**Status:** Ready for production use

---

## Next Steps for Enhancement (Optional)

- [ ] Add video walkthrough of data flow (OE2 → OE3)
- [ ] Create Jupyter notebook demonstrating validation commands
- [ ] Add interactive data quality dashboard
- [ ] Archive old baseline docs (BASELINE_v1.md, etc.)

---

## Questions? See:

1. **Quick facts:** [DATA_SOURCES_QUICK_CARD.md](docs/DATA_SOURCES_QUICK_CARD.md) (1 page)
2. **Complete reference:** [DATA_SOURCES_REAL_VS_SIMULATED.md](docs/DATA_SOURCES_REAL_VS_SIMULATED.md) (700 lines)
3. **System overview:** [ARQUITECTURA_GUÍA_RÁPIDA.md](ARQUITECTURA_GUÍA_RÁPIDA.md)
4. **Data flow details:** [FLOW_ARCHITECTURE.md](FLOW_ARCHITECTURE.md)

---

**Last Updated:** 2026-02-14  
**Maintained By:** pvbesscar Documentation Team  
**License:** Same as parent project
