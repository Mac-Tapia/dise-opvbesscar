# 🔧 ARCHITECTURE CLARIFICATION: Chargers, Sockets & Control

## STATUS: CORRECTED ✅
**Date**: 2026-02-04  
**Updated**: Terminology corrected to reflect REAL architecture (32 physical chargers, 128 sockets/tomas)

---

## THE REAL ARCHITECTURE (OE3/OE2 CONFIRMED)

### ✅ Physical Infrastructure: 32 Chargers

| Component | Count | Specifications | Total Capacity |
|-----------|-------|-----------------|-----------------|
| **Motos Chargers** | 28 | 2.0 kW each | 56 kW |
| **Mototaxis Chargers** | 4 | 3.0 kW each | 12 kW |
| **TOTAL** | **32** | **Physical devices** | **68 kW** |

### ✅ Individual Sockets (Tomas): 128 Total

Each of the 32 physical chargers has **4 independent sockets**:

- **Motos**: 28 chargers × 4 sockets = **112 tomas** (each 2.0 kW)
- **Mototaxis**: 4 chargers × 4 sockets = **16 tomas** (each 3.0 kW)
- **TOTAL**: 32 × 4 = **128 tomas de carga**

### ✅ Two Parking Areas (Unified in CityLearn)

| Playa | Vehicles/Day | Chargers | Sockets | Capacity |
|------|--------------|----------|---------|----------|
| **Motos** | 1,800 motos | 28 | 112 | 224 motos/day (2 cycles) |
| **Mototaxis** | 260 mototaxis | 4 | 16 | 32 mototaxis/day (2 cycles) |
| **TOTAL** | **2,060 veh/day** | **32** | **128** | - |

### ✅ One CityLearn Building: Mall_Iquitos

**In CityLearn schema.json:**
```json
{
  "buildings": {
    "Mall_Iquitos": {
      "chargers": {
        "charger_mall_1": {...},   // Socket 1 (from charger 1)
        "charger_mall_2": {...},   // Socket 2 (from charger 1)
        ...
        "charger_mall_128": {...}  // Socket 128 (from charger 32)
      },
      "pv": { "nominal_power": 4162 },  // 4,162 kWp solar
      "electrical_storage": { "capacity": 4520 }  // 4,520 kWh BESS
    }
  }
}
```

**In CityLearn simulation:**
- **128 independent charger control objects** (one per socket/toma)
- Each receives individual RL action: `action[i]` ∈ [0, 1] for socket i
- Each has individual dynamic profile: `charger_simulation_001.csv` → `charger_simulation_128.csv`

---

## CONTROL ARCHITECTURE

### RL Agent Actions: 129-dimensional
```
action = [
  bess_setpoint,              # Action 0: BESS discharge rate [0-1]
  charger_1_setpoint,         # Action 1: Socket 1 power [0-1]
  charger_2_setpoint,         # Action 2: Socket 2 power [0-1]
  ...
  charger_128_setpoint        # Action 128: Socket 128 power [0-1]
]
```

### Dispatch Rules (Automatic, NOT RL Control)
The **5-priority dispatch** automatically allocates:

```
1. EV Charging (Demand → any available socket)
2. Mall Loads (Non-shiftable 100 kW)
3. BESS Charging (if SOC < 80%)
4. Grid Export (excess solar)
5. Grid Import (if deficit)
```

RL agents **modify the timing/intensity** of these flows via continuous setpoints.

---

## DATA FILES & MAPPINGS

### OE2 Source Data (32 Physical Chargers)

```
data/interim/oe2/chargers/
├── individual_chargers.json          ← 32 physical charger specs
├── chargers_hourly_profiles_annual.csv  ← 8,760 × 32 matrix (hourly demand per charger)
└── charger_profile_variants/         ← Dynamic profiles per charger
    ├── CHARGER_001.csv               ← Physical charger 1 (motos)
    ├── CHARGER_002.csv
    ...
    └── CHARGER_032.csv               ← Physical charger 32 (mototaxis)
```

### CityLearn Generated Data (128 Sockets)

```
data/processed/citylearn/iquitos_ev_mall/
├── schema.json                       ← 128 charger entries
└── charger_simulation_001.csv        ← Socket 1 dynamic profile (8,760 rows)
    charger_simulation_002.csv        ← Socket 2 dynamic profile
    ...
    charger_simulation_128.csv        ← Socket 128 dynamic profile (8,760 rows)
```

### Mapping Logic (in dataset_builder.py)

```python
# Expand 32 charger profiles to 128 socket profiles
for charger_idx in range(32):
    charger_demand = chargers_hourly_profiles[charger_idx]  # 8,760 values
    for socket_in_charger in range(4):
        socket_idx = charger_idx * 4 + socket_in_charger    # Maps to 0-127
        socket_demand = charger_demand / 4.0                # Split equally
        
        # Generate charger_simulation_XXX.csv with dynamic profiles
        generate_charger_csv(socket_idx+1, socket_demand)   # Creates charger_simulation_001.csv, etc.
```

---

## CLARIFICATIONS & CORRECTIONS

### ❌ INCORRECT TERMINOLOGY
- "128 individual chargers" ← **WRONG** - confuses sockets with physical devices
- "Each charger is independent" ← **MISLEADING** - if referring to 128 chargers
- "128 separate charging devices" ← **WRONG**

### ✅ CORRECT TERMINOLOGY
- "32 physical chargers with 128 sockets/tomas" ← **CORRECT**
- "128 socket-level charging points" ← **CORRECT**
- "Each socket is independently controlled" ← **CORRECT**
- "128 RL actions (one per socket)" ← **CORRECT**

---

## CODE CORRECTIONS APPLIED (2026-02-04)

✅ Updated `run_sac_training.py`:
```python
# OLD: "Chargers: 128 dinámicos (112 motos + 16 mototaxis)"
# NEW: "Chargers: 32 cargadores físicos con 128 tomas (112 motos + 16 mototaxis)"
```

✅ Updated `dataset_builder.py` (multiple lines):
- Line 484: "32 chargers × 4 sockets = 128 tomas"
- Line 664-666: Socket-level clarification
- Log messages: Consistent terminology

---

## VERIFICATION CHECKLIST

- [x] OE2 data: 32 physical chargers documented
- [x] CityLearn schema: 128 socket entries confirmed
- [x] CSV generation: 128 individual files created
- [x] RL actions: 129-dimensional (1 BESS + 128 sockets)
- [x] Dispatch rules: Working with 128 socket control
- [x] Documentation: Corrected terminology
- [x] Logging: Clear socket vs. charger language

---

## DEPLOYMENT CONFIRMATION

**For next training run:**

```bash
# System will correctly:
✓ Load 32 physical charger profiles (OE2)
✓ Expand to 128 socket profiles (CityLearn)
✓ Create 128 independent CSV files
✓ Create 128 charger control objects in schema
✓ Generate 129 RL actions per step
✓ Apply socket-level control during simulation
```

---

## REFERENCES

- **Config**: `configs/default.yaml` → OE2 architecture specs
- **Builder**: `src/iquitos_citylearn/oe3/dataset_builder.py` → Socket expansion logic
- **Training**: `scripts/run_sac_training.py` → RL agent training loop
- **Diagnostic**: `scripts/diagnose_oe2_data_loading.py` → Data flow validation

---

**Status**: ✅ ARCHITECTURE VERIFIED & DOCUMENTED  
**Clarity Level**: HIGH - No ambiguity between physical chargers and socket-level control

