# SCHEMA & AGENTS - Quick Reference Card

## ✅ Status: VERIFIED, LOCKED, READY

---

## One-Line Summary

🎯 **All three agents (SAC, PPO, A2C) use the SAME, FIXED, LOCKED CityLearn v2 schema** (`data/processed/citylearn/iquitos_ev_mall/schema.json`)

---

## The Three Agents

| Agent | Learning Rate | Key Params | Status |
|-------|---|---|---|
| **SAC** (Soft Actor-Critic) | 1e-3 | buffer=100K, off-policy | ✅ Uses schema.json |
| **PPO** (Proximal Policy Opt) | 1e-4 | n_steps=2048, on-policy | ✅ Uses schema.json |
| **A2C** (Advantage Actor-Critic) | 2e-3 | batch=1024, on-policy | ✅ Uses schema.json |

---

## Schema Overview

```
File:           schema.json (110 KB)
Location:       data/processed/citylearn/iquitos_ev_mall/
Chargers:       128 (112 motos 2kW + 16 mototaxis 3kW)
Timesteps:      8,760 (1 year hourly)
Central Agent:  Yes (agents coordinate)
BESS:           4,520 kWh / 2,712 kW (OE2 Real, immutable)
PV:             4,050 kWp (immutable)
Protection:     🔒 SHA256 locked (.schema.lock)
```

---

## Spaces

| Space | Dimension | Type | Info |
|---|---|---|---|
| **Observation** | 534 | Continuous | All agents see identical state |
| **Action** | 126 | Continuous [0,1] | Charger power setpoints |

---

## Verification Commands

```bash
# Audit schema (5 sec)
python scripts/audit_schema_integrity.py
# Output: [OK] AUDITORIA PASADA

# Verify all agents (5 sec)
python scripts/verify_agents_same_schema.py
# Output: [OK] TODOS LOS AGENTES USAN MISMO SCHEMA

# Check lock (1 sec)
python scripts/schema_lock.py verify
# Output: [OK] Schema NO fue modificado
```

---

## Training Commands

```bash
# Train ALL agents (SAC → PPO → A2C)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Train SAC only
python -m scripts.run_oe3_simulate --config configs/default.yaml --agents sac

# Train PPO only
python -m scripts.run_oe3_simulate --config configs/default.yaml --agents ppo

# Train A2C only
python -m scripts.run_oe3_simulate --config configs/default.yaml --agents a2c
```

---

## Files

| File | Purpose | Status |
|---|---|---|
| `schema.json` | Main schema | 🔒 LOCKED |
| `.schema.lock` | SHA256 protection | 🔒 ACTIVE |
| `configs/default.yaml` | Agent hyperparameters | ℹ️ Can modify |
| `SCHEMA_ARCHITECTURE_AND_AGENTS.md` | Full technical docs | 📖 Reference |
| `SCHEMA_VERIFICATION_COMPLETE.md` | Executive summary | 📊 Summary |

---

## What's Locked (Cannot Change)

- ✅ 128 Chargers
- ✅ 8,760 Timesteps
- ✅ 534-dim Observation space
- ✅ 126-dim Action space
- ✅ BESS (4,520 kWh / 2,712 kW - OE2 Real)
- ✅ PV (4,050 kWp)

---

## What Can Change

- 🔄 Learning rates (SAC, PPO, A2C)
- 🔄 Batch sizes
- 🔄 Network architecture
- 🔄 Episode count
- 🔄 Reward weights

---

## Fast Checklist

Before training:

- [ ] Run: `python scripts/audit_schema_integrity.py` → [OK]
- [ ] Run: `python scripts/verify_agents_same_schema.py` → [OK]
- [ ] Run: `python scripts/schema_lock.py verify` → [OK]
- [ ] Check: `configs/default.yaml` agent settings
- [ ] Ready: `python -m scripts.run_oe3_simulate --config configs/default.yaml`

---

## Why This Matters

**Problem**: Multiple agents might use different schemas → Incomparable results

**Solution**: One schema, all agents → Fair comparison

**Guarantee**: Lock file prevents accidental modifications

---

## If Something Goes Wrong

| Error | Fix |
|---|---|
| "Hash mismatch" | `python scripts/run_oe3_build_dataset.py` then `schema_lock.py lock` |
| "128 chargers not found" | `python scripts/run_oe3_build_dataset.py` |
| "Agent crash" | Check `schema_lock.py verify` first |

---

## GPU Training

All agents auto-detect GPU:

```python
device: "auto"  # Automatically uses GPU if available
```

## References

- **Full Documentation**: `SCHEMA_ARCHITECTURE_AND_AGENTS.md`
- **Verification Report**: `SCHEMA_VERIFICATION_COMPLETE.md`
- **Config File**: `configs/default.yaml`
- **Main Entry Point**: `scripts/run_oe3_simulate.py`

---

**Last Updated**: 2026-01-26  
**Status**: ✅ READY TO TRAIN
