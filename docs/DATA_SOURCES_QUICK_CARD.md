# Data Sources Quick Reference Card

**pvbesscar v5.2 | OE2 → OE3 Pipeline | 2026-02-14**

---

## The Four Data Pillars (OE2 Dimensioning)

| Data | Status | Where | Size | Key Column | Annual Qty | RL Use |
|------|--------|-------|------|-----------|-----------|--------|
| **Solar PV** | ✅ REAL | `Generacionsolar/pv_generation_hourly_*.csv` | 8,760h × 1 | `ac_power_kw` | ~8,000 MWh | Maximize PV self-use |
| **Chargers (38)** | ✅ REAL | `chargers/chargers_ev_ano_2024_v3.csv` | 365d × 353 cols (38 sockets) | `socket_000..socket_037` | ~19,500 kWh | Hard constraint: satisfy demand |
| **Mall Load** | ✅ REAL | `demandamallkwh/demandamallhorakwh.csv` | 8,760h × 1 | `demand_kwh` | ~875 MWh | Non-controllable baseline |
| **BESS Dispatch** | ⚠️ SIMULATED | `bess/bess_simulation_hourly.csv` | 8,760h × 8 | `bess_soc_percent` | SOC 0-100% | Reference trajectory |

---

## Status Symbol Legend

| Symbol | Meaning | Immutable | Updates | Trust Level |
|--------|---------|-----------|---------|------------|
| **✅** | REAL measured data | Yes (yearly cycle) | Annual audit | High |
| **⚠️** | Simulated/optimized | No (rule-based) | RL replaces | Medium (baseline) |
| **🧮** | Derived/computed | N/A (runtime) | Per step | Depends on inputs |

---

## Where Data Flows in OE3 (RL Training)

```
Input Data Sources (OE2)          CityLearn v2 Environment         RL Agent
─────────────────────────         ──────────────────────          ────────

✅ Solar                           Observations (394-dim) ──────→  SAC/PPO/A2C
✅ Chargers (38)     ┐                                              Policy
✅ Mall Demand    ───┼──→ Dataset Builder  ─────────────────→    Network
⚠️ BESS (ref)        ┘             ↓
+ Time (hour/day)                  Reward:                        ◄─ Actions
                                   • CO₂ min (0.4521 kg/kWh)      [0,1] × 39
                                   • Solar util                    channels
                                   • EV completion
                                   • Stability                     ↓
                                   • Cost (optional)               Convert to
                                                                    physical kW
                                   ↓
                                Feedback (next obs)
```

---

## Critical Validation Rules

### ❌ Data will FAIL if:
- Solar: ≠ 8,760 hourly rows (15-min data → downsample first!)
- Chargers: ≠ 38 columns, ≠ 8,760 rows
- Mall: < 8,760 rows (auto-padded, but warns)
- BESS: Negative values, gaps in SOC timeline

### ✅ Data is GOOD if:
```bash
# Quick diagnostic commands
python -c "import pandas as pd; df=pd.read_csv('solar.csv'); assert len(df)==8760, f'Bad: {len(df)}rows'; print('✓ Solar OK')"
python -c "import pandas as pd; df=pd.read_csv('chargers.csv'); assert df.shape==(8760,38), f'Bad shape'; print('✓ Chargers OK')"
```

---

## Key File Locations

```
data/
├── interim/oe2/
│   ├── solar/
│   │   └── pv_generation_citylearn_v2.csv        ✅
│   ├── chargers/
│   │   └── chargers_ev_ano_2024_v3.csv           ✅
│   ├── demandamallkwh/
│   │   └── demandamallhorakwh.csv                 ✅
│   └── bess/
│       └── bess_simulation_hourly.csv             ⚠️
│
└── processed/citylearn/iquitos_ev_mall/          (Fallback copies)
    ├── Generacionsolar/
    ├── chargers/
    ├── demandamallkwh/
    └── bess/
```

---

## Reward Function Breakdown (SAC Agent)

```python
reward = (
    0.50 * CO2_minimization          # Primary: grid imports × 0.4521 kg CO₂/kWh (✅ REAL)
    + 0.20 * solar_utilization       # Secondary: PV direct use vs grid import
    + 0.15 * ev_completion           # Tertiary: chargers satisfied by deadline
    + 0.10 * grid_stability          # Tertiary: smooth power ramps
    + 0.05 * cost_minimization       # Tertiary: off-peak tariff preference
)
```

**Adjust weights?** Edit [src/rewards/rewards.py](../src/rewards/rewards.py), then **restart training**.

---

## Common Issues & Fixes

| Issue | Root Cause | Fix | Time |
|-------|-----------|-----|------|
| "8760 rows required" | 15-min solar data | `df.resample('h').mean()` | 1 min |
| "38 sockets not found" | Chargers CSV has wrong columns | Find correct file in `/chargers` | 5 min |
| "BESS path not found" | File not in expected location | Ensure `bess_simulation_hourly.csv` exists | 2 min |
| Agent reward NaN | Zeroed solar data | Validate solar CSV annual sum > 0 | 5 min |
| Training stuck | Bad BESS trajectory | Regenerate from OE2 dispatch rules | 10 min |

---

## Who Uses What Data?

| Component | Solar | Chargers | Mall | BESS | CO₂ Factor |
|-----------|-------|----------|------|------|-----------|
| Dataset builder | ✅ | ✅ | ✅ | ✅ | - |
| Observation space | ✅ | ✅ | - | ✅ | - |
| Reward function | ✅ | ✅ | ✅ | - | ✅ 0.4521 |
| Baseline (no RL) | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| SAC training | ✅ | ✅ | ✅ | ✅ init | ✅ |

---

## Before You Train

**✓ 1-minute checklist:**

```bash
# Step 1: Verify solar
wc -l data/interim/oe2/solar/pv_generation_citylearn_v2.csv  # Should be 8761 (8760 + header)

# Step 2: Verify chargers
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/chargers/chargers_ev_ano_2024_v3.csv'); print(f'{df.shape[0]} rows, {df.shape[1]} cols'); assert 'socket_000' in df.columns"

# Step 3: Verify mall
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv'); print(f'Mall: {len(df)} rows'); assert len(df)>=8760"

# Step 4: Verify BESS
python -c "import pandas as pd; df=pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv'); print(f'BESS: {df.shape}'); assert 'bess_soc_percent' in df.columns"

# If all ✓, you're ready to train!
```

---

## Next Steps

1. **Learn the full architecture:** [DATA_SOURCES_REAL_VS_SIMULATED.md](./DATA_SOURCES_REAL_VS_SIMULATED.md)
2. **Run baselines:** `python -m scripts.run_dual_baselines --config configs/default.yaml`
3. **Start training SAC:** `python scripts/train/train_sac_multiobjetivo.py`
4. **Monitor results:** Check `outputs/sac_training/` for reward curves

---

**Questions?** See [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) or [Common Pitfalls](./QUICK_REFERENCE.md#common-pitfalls--solutions)
