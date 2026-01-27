# ✅ Pre-Training Verification Checklist

**Use this checklist BEFORE starting agent training to ensure everything is ready.**

---

## Phase 1: Document Review (5 minutes)

- [ ] Read [SCHEMA_VERIFICATION_RESULTS.txt](SCHEMA_VERIFICATION_RESULTS.txt)
  - Understand the 8 verification checks
  - Confirm all marked ✅ PASS

- [ ] Review [SCHEMA_AGENTS_QUICK_REF.md](SCHEMA_AGENTS_QUICK_REF.md)
  - Know the agent configurations (SAC/PPO/A2C)
  - Understand which schema file is used

- [ ] Check [FINAL_SUMMARY_SCHEMA_VERIFICATION.md](FINAL_SUMMARY_SCHEMA_VERIFICATION.md)
  - Confirm guardrails (locked specs vs changeable params)
  - Understand immutability protection

---

## Phase 2: Schema Audit (15 seconds)

Run automated audit:
```bash
python scripts/audit_schema_integrity.py
```

Expected output:
```
[OK] AUDITORIA PASADA - SCHEMA LISTO PARA TODOS LOS AGENTES
```

Checklist:
- [ ] Command executed without errors
- [ ] Output shows "AUDITORIA PASADA"
- [ ] All checks marked [OK]

---

## Phase 3: Agent Compatibility Verification (15 seconds)

Run agent verification:
```bash
python scripts/verify_agents_same_schema.py
```

Expected output:
```
[OK] TODOS LOS AGENTES USAN MISMO SCHEMA
[OK] SAC:  Uses schema.json
[OK] PPO:  Uses schema.json
[OK] A2C:  Uses schema.json
```

Checklist:
- [ ] Command executed without errors
- [ ] All agents verified
- [ ] All point to schema.json (SAME FILE)
- [ ] No errors on CityLearn env creation

---

## Phase 4: Lock Integrity Check (5 seconds)

Verify schema protection:
```bash
python scripts/schema_lock.py verify
```

Expected output:
```
[OK] Schema NO fue modificado
Integridad: VERIFICADA
```

Checklist:
- [ ] Lock file exists (.schema.lock)
- [ ] Output shows "NO fue modificado"
- [ ] Hash matches expected value
- [ ] Timestamp is recent (today or yesterday)

---

## Phase 5: Configuration Review (5 minutes)

Open `configs/default.yaml` and verify:

```bash
# View agent settings
grep -A 10 "evaluation:" configs/default.yaml
```

Checklist:
- [ ] SAC configuration present
  - [ ] learning_rate: 0.001 (or acceptable value)
  - [ ] device: "auto" (for GPU)

- [ ] PPO configuration present
  - [ ] learning_rate: 0.0001 (or acceptable value)
  - [ ] n_steps: 2048 (or acceptable value)
  - [ ] device: "auto" (for GPU)

- [ ] A2C configuration present
  - [ ] learning_rate: 0.002 (or acceptable value)
  - [ ] batch_size: 1024 (or acceptable value)
  - [ ] device: "auto" (for GPU)

---

## Phase 6: Environment Check (10 seconds)

Verify Python environment:
```bash
# Check Python version
python --version

# Should output: Python 3.11.x or later
```

Checklist:
- [ ] Python 3.11+ installed
- [ ] Virtual environment active (if using venv)
- [ ] All packages installed: `pip list | grep -E "stable-baselines3|gym|torch"`

---

## Phase 7: Disk Space Check (10 seconds)

Verify sufficient disk space:
```bash
# Check free space (Windows)
Get-Volume

# Check project directory
Get-ChildItem -Path . -Recurse | Measure-Object -Sum Length
```

Checklist:
- [ ] At least 10 GB free disk space available
- [ ] Checkpoint directory writable: `checkpoints/`
- [ ] Output directory writable: `outputs/`

---

## Phase 8: GPU Availability (Optional, 10 seconds)

If planning to use GPU:
```bash
# Check if GPU detected
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"

# If True: GPU training will be ~10x faster
# If False: CPU training will work but slower
```

Checklist:
- [ ] GPU available: ✅ (RECOMMENDED) or ⚠️ CPU-only
- [ ] CUDA drivers installed (if GPU)
- [ ] torch with CUDA support installed (if GPU)

---

## Final Approval ✅

If ALL checks above are marked ✅, you are READY TO TRAIN:

```bash
# Run the full pipeline (all agents)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# OR run individual agents
python -m scripts.run_oe3_simulate --config configs/default.yaml --agents sac
```

---

## Troubleshooting Quick Reference

| Issue | Command | Solution |
|-------|---------|----------|
| "128 chargers not found" | `python scripts/audit_schema_integrity.py` | Rebuild dataset |
| "Hash mismatch" | `python scripts/schema_lock.py verify` | See Phase 4 |
| "Agents use different schemas" | `python scripts/verify_agents_same_schema.py` | Check output |
| "Python version wrong" | `python --version` | Install Python 3.11+ |
| "GPU not available" | `python -c "import torch; print(torch.cuda.is_available())"` | Use CPU or install CUDA |

---

## Time Estimates

| Phase | Duration | Status |
|-------|----------|--------|
| 1. Document Review | 5 min | 📖 |
| 2. Schema Audit | 15 sec | ⚡ |
| 3. Agent Verification | 15 sec | ⚡ |
| 4. Lock Integrity | 5 sec | ⚡ |
| 5. Config Review | 5 min | 📖 |
| 6. Environment Check | 10 sec | ⚡ |
| 7. Disk Space Check | 10 sec | ⚡ |
| 8. GPU Availability | 10 sec | ⚡ |
| **TOTAL** | **~11 minutes** | ✅ |

---

## Success Criteria ✅

All of the following must be true:

- ✅ audit_schema_integrity.py outputs "AUDITORIA PASADA"
- ✅ verify_agents_same_schema.py outputs "TODOS LOS AGENTES USAN MISMO SCHEMA"
- ✅ schema_lock.py verify outputs "Schema NO fue modificado"
- ✅ configs/default.yaml has agent settings
- ✅ Python 3.11+ is installed
- ✅ Virtual environment is active (if using)
- ✅ GPU available (optional but recommended)
- ✅ At least 10 GB free disk space

**If all are ✅, training will proceed successfully.**

---

## Commands Summary

Copy-paste ready:

```bash
# 1. Audit schema
python scripts/audit_schema_integrity.py

# 2. Verify agents
python scripts/verify_agents_same_schema.py

# 3. Check lock
python scripts/schema_lock.py verify

# 4. Verify Python
python --version

# 5. Start training
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

---

## Need Help?

| Question | File | Section |
|----------|------|---------|
| What was verified? | SCHEMA_VERIFICATION_RESULTS.txt | Verification Summary |
| How do I train? | SCHEMA_AGENTS_QUICK_REF.md | Training Commands |
| Why does it matter? | FINAL_SUMMARY_SCHEMA_VERIFICATION.md | Executive Summary |
| Technical details? | SCHEMA_ARCHITECTURE_AND_AGENTS.md | Full Reference |
| Which document? | SCHEMA_DOCUMENTATION_INDEX.md | Navigation |

---

## Print This Checklist

Print this page and check off each item as you complete it.

**Estimated time**: 11 minutes  
**Difficulty**: Easy (mostly automated checks)  
**Risk level**: Low (read-only operations)

---

**READY TO TRAIN? Start with Phase 1 above.** ✅

Once all checks pass → Execute:
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

🚀 **Begin OE3 RL Training Pipeline**
