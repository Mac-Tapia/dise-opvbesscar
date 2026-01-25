# OE3 Structure - Visual Maps & Dependency Graphs

---

## 1. Current File Structure (Before Cleanup)

<!-- markdownlint-disable MD013 -->
```bash
src/iquitos_citylearn/oe3/
│
├── 🟢 ACTIVE PRODUCTION FILES
│   ├── rewards.py                          [529 lines] ← All agents depend on this
│   ├── co2_table.py                        [469 lines] ← Main evaluation output
│   ├── dataset_builder.py                  [863 lines] ← Creates CityLearn schema
│   ├── simulate.py                         [935 lines] ← Central orchestrator
│   ├── progre...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Summary**:

- ✅ **7 active core files** (~4,500 lines)
- ✅ **7 agent implementations** (~3,600 lines)
- ⚠️ **3 secondary files** (~670 lines to archive)
- ❌ **2 unused files** (~865 lines to delete/merge)
- **Total**: ~9,600 lines in OE3 module

---

## 2. Import Dependency Graph (Current)

<!-- markdownlint-disable MD013 -->
```bash
ENTRY POINTS (Scripts)
│
├─ run_oe3_build_dataset.py ────────┐
│                                    │
├─ run_oe3_simulate.py ─────────────┤─→ dataset_builder.py
│                                    │
├─ run_oe3_co2_table.py ────────────┤
│                                    │
└─ train_agents_serial.py ──────────┘

                    ↓

            dataset_builder.py
                    │
        ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 3. Data Flow: OE2 → OE3 → Training → Results

<!-- markdownlint-disable MD013 -->
```bash
╔══════════════════════════════════════════════════════════════════════╗
║                    INPUT LAYER (OE2 Artifacts)                      ║
╚══════════════════════════════════════════════════════════════════════╝

  data/interim/oe2/
  ├── solar/pv_generation_timeseries.csv      [8,760 hourly kW AC values]
  │   └─ Eaton Xpert1670 spec: 2 inverters, 31 modules/string, 6,472 strings
  │
  ├── ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 4. Reward System Architecture

<!-- markdownlint-disable MD013 -->
```bash
Multi-Objective Reward Function
═════════════════════════════════════════════════════════════════

Input per timestep:
  obs, actions, env state, carbon_intensity

                    ↓

MultiObjectiveWeights (Dataclass)
├─ co2: 0.50                     ← PRIMARY objective
├─ solar: 0.20                   ← SECONDARY objective
├─ cost: 0.10                    ← TERTIARY objective
├─ ev_satisfactio...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 5. Agent Dependency Chain

<!-- markdownlint-disable MD013 -->
```bash
AGENT FACTORY
═════════════════════════════════════════════════════════════════

src/iquitos_citylearn/oe3/agents/__init__.py
│
├─→ make_sac(env, config) → SACAgent
│   └─ src/iquitos_citylearn/oe3/agents/sac.py
│      ├─ Implements: learn(), predict(), load(), save()
│      ├─ Depends on: stable_baselines3.SAC
│      ├─ Uses: progress.py (training logging)
│      └─ Requires: rewards.py (reward f...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 6. File Status Matrix (Before & After Cleanup)

<!-- markdownlint-disable MD013 -->
```bash
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        BEFORE CLEANUP (Current State)                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝

File                          Lines   Status      Used By              Action
───────────────────────────────────────────────────────────────────────────...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 7. Risk Assessment Heat Map

<!-- markdownlint-disable MD013 -->
```bash
CLEANUP OPERATIONS RISK ASSESSMENT
═════════════════════════════════════════════════════════════════════════════

Operation                          Risk Level   Rollback Time   Impact
─────────────────────────────────────────────────────────────────────────
1. DELETE demanda_mall_kwh.py      🟢 NONE      1 minute        Zero
2. MERGE co2_emissions → co2_table 🟡 LOW       2 minutes       Minor (tes...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

**Visual analysis complete!** Use these diagrams to understand module
structure, dependencies, and data flow.
