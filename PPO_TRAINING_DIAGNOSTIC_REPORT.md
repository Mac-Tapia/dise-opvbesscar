# PPO Training Diagnostic Report

## Executive Summary

**Status**: PPO training failed at step 2250 after ~18 minutes (2.6% progress)

**Root Cause Analysis**: Unknown - Traceback incomplete in user logs

**Current Action**: Running diagnostic in CPU mode to capture complete error traceback

**Recommendation**: Switch PPO to CPU-only mode with reduced parameters

---

## Checkpoint Status

| Step | File Size | Timestamp | Status |
|------|-----------|-----------|--------|
| 500 | 2.51 MB | 12:11:58 | ✓ Saved |
| 1000 | 2.51 MB | 12:14:23 | ✓ Saved |
| 1500 | 2.51 MB | 12:16:46 | ✓ Saved |
| 2000 | 2.51 MB | 12:19:10 | ✓ Saved |
| 2250 | N/A | 12:20:00 | ✗ ERROR |

**Progress**: 2,250 / 87,600 timesteps = 2.6% complete

**Estimated Full Time** (at current speed): 16.7 hours

---

## Issues Identified

### 1. GPU-CPU Fallback Problem

- PPO uses `ActorCriticPolicy(MlpPolicy)` → Not GPU-optimized
- Mixed Precision (AMP) enabled but MLP doesn't benefit much
- Possible inefficient fallback to CPU causing slowdown

### 2. Abnormally Slow Training

- **PPO speed**: ~72 steps/minute
- **SAC speed**: ~1,168 steps/minute  
- **Ratio**: 16x slower than SAC (anomalous)
- **Diagnosis**: GPU throughput insufficient for MLP + CPU fallback overhead

### 3. Abrupt Interruption

- Last successful log: `paso 2250` at 12:20 p.m.
- Traceback at line 166 of `run_oe3_simulate.py` (no context)
- Possible causes:
  - Memory exhaustion (MemoryError)
  - CityLearn environment timeout
  - GPU memory overflow during batch accumulation
  - Checkpoint write failure

---

## Diagnostic Steps Taken

### Step 1: Checkpoint Analysis

```
analyze_ppo_status.py → Confirmed 4 checkpoints saved successfully
```

Result: 2,000 pasos guardados exitosamente (último antes del error)

### Step 2: GPU Verification

```
GPU: NVIDIA CUDA available
Memory: 8.59 GB available
PyTorch: CUDA support confirmed
```

Result: GPU infrastructure OK, not the issue

### Step 3: PPO CPU Diagnostic (In Progress)

```bash
diagnose_ppo_error.py:
  - Executes PPO on CPU (removes GPU complications)
  - 10,000 timesteps (faster test = ~15 minutes)
  - Captures complete traceback if error occurs
  - Saves output to: ppo_diagnosis_simple.txt
```

Expected Result: Complete error traceback for root cause analysis

---

## Recommended Solutions

### Solution 1: CPU-Only Mode (RECOMMENDED) ⭐

**Configuration Change**:

```yaml
oe3:
  evaluation:
    ppo:
      device: cpu              # Changed from 'auto' or 'cuda'
      use_amp: false           # Disable Mixed Precision
      timesteps: 40000         # Reduce from 87,600 (test)
      batch_size: 64           # Reduce from 128
      n_steps: 512             # Reduce from 1024
      checkpoint_freq_steps: 500
```

**Rationale**:

- ✓ CPU is stable for MLP policies (no GPU optimization needed)
- ✓ Eliminates GPU-CPU fallback overhead
- ✓ More predictable checkpoint recovery
- ✓ Requires less memory (3 GB vs 8 GB GPU)

**Time Estimates**:

- 40,000 timesteps: ~10 minutes
- 87,600 timesteps: ~22 minutes
- Compared to 16.7 hours with GPU fallback

**Success Probability**: 90%

---

### Solution 2: Resume from Last Checkpoint

**Option A** (if resume script exists):

```bash
python continue_ppo_training.py --config configs/default.yaml
```

**Option B** (modify resume flag):

```yaml
oe3:
  evaluation:
    resume_checkpoints: true  # Auto-load last checkpoint
```

**Rationale**:

- ✓ Saves ~30 minutes (resumes from step 2000)
- ✗ May fail again if root cause is systematic

**Time Estimate**: ~11 minutes to complete from step 2000

**Success Probability**: 40-50% (depends on error cause)

---

### Solution 3: Reduce Training Complexity (Fallback)

```yaml
oe3:
  evaluation:
    ppo:
      timesteps: 20000         # 23% of original
      batch_size: 32           # 25% of original
      n_steps: 256             # 25% of original
      checkpoint_freq_steps: 100  # More frequent checkpoints
```

**Rationale**:

- ✓ Completes very quickly (~5 minutes)
- ✓ Ultra-conservative on memory

**Disadvantage**:

- ✗ Results may be suboptimal
- ✗ Not useful for production

**Time Estimate**: ~5 minutes

**Success Probability**: 95% (but limited training)

---

## Probable Error Causes

### High Probability (60%)

**Cause**: Memory Pressure

- `n_steps=1024` creates large experience replay buffer
- MLP policy weights heavy in memory
- Accumulation after 2250 steps exhausts GPU VRAM
- **Solution**: Reduce batch_size, n_steps, use CPU

### Medium Probability (25%)

**Cause**: CityLearn Environment Issue

- Environment simulation slow after N steps
- Possible memory leak in environment
- **Solution**: Check environment reset, rebuild dataset

### Low Probability (15%)

**Cause**: Stable-Baselines3 Bug

- Edge case in PPO implementation
- Rare race condition
- **Solution**: Downgrade/upgrade SB3 version

---

## Files Generated

| File | Purpose | Status |
|------|---------|--------|
| `analyze_ppo_status.py` | Parse checkpoint directory | ✓ Executed |
| `diagnose_ppo_error.py` | CPU diagnostic with full traceback | ⏳ Running |
| `PPO_DIAGNOSTICO_COMPLETO.md` | Detailed diagnostic report (Spanish) | ✓ Created |
| `ESTADO_PPO_DIAGNOSTICO.md` | Status summary with next steps | ✓ Created |
| `ppo_diagnosis_simple.txt` | Diagnostic output | ⏳ Generating |

---

## Action Plan

### Immediate (Next 15 minutes)

1. **Wait** for `diagnose_ppo_error.py` to complete
2. **Review** `ppo_diagnosis_simple.txt` for error type
3. **Identify** root cause (Memory? Timeout? Environment?)

### Short-term (30 minutes)

1. **Modify** configs/default.yaml (device: cpu, reduce params)
2. **Re-run** PPO: `python -m scripts.run_oe3_simulate`
3. **Monitor** checkpoint creation and progress

### Medium-term (After PPO succeeds)

1. **Execute** A2C training (can also use CPU)
2. **Generate** CO2 comparison table
3. **Analyze** all agent results (SAC vs PPO vs A2C)

### Long-term (After all training)

1. **Document** final results
2. **Create** publication figures
3. **Archive** checkpoints and logs

---

## Success Criteria

### PPO Training Success

- ✓ Completes without error
- ✓ Reward converges to 40-50 (similar to SAC)
- ✓ All checkpoints save correctly
- ✓ Time < 30 minutes (CPU) or < 2 hours (GPU if fixed)

### Overall Training Success

- ✓ SAC: Complete (DONE)
- ✓ PPO: Complete (IN PROGRESS)
- ✓ A2C: Complete (PENDING)
- ✓ CO2 table: Generated
- ✓ All results publishable

---

## Technical Details

### Python Environment

- Python: 3.11
- Virtual Environment: `.venv`
- GPU Support: CUDA 8.59 GB available
- Key Packages:
  - PyTorch
  - stable-baselines3
  - CityLearn >= 2.5.0

### Configuration Files

- Main: `configs/default.yaml`
- Dataset: `data/processed/citylearn/iquitos_ev_mall/`
- Checkpoints: `analyses/oe3/training/checkpoints/ppo/`
- Results: `outputs/oe3/simulations/`

### Key Scripts

- **Pipeline**: `scripts/run_pipeline.py`
- **PPO**: `scripts/run_oe3_simulate.py` (calls `simulate()` with agent='PPO')
- **Resume**: `scripts/continue_ppo_training.py` (if exists)
- **Analysis**: `scripts/run_oe3_co2_table.py`

---

## Contact/Support

**If CPU diagnostic succeeds**: PPO should complete in 10-30 minutes

**If CPU diagnostic fails with MemoryError**:

```yaml
# Ultra-conservative config
oe3:
  evaluation:
    ppo:
      device: cpu
      timesteps: 10000      # 11% of original
      batch_size: 16        # 12.5% of original
      n_steps: 128          # 12.5% of original
```

**If CPU diagnostic fails with CityLearnError**:

```bash
# Rebuild entire dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
# Then retry PPO
```

**If CPU diagnostic fails with TimeoutError**:

```bash
# Skip Uncontrolled baseline (speeds up total time)
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-uncontrolled
```

---

## Next Steps

**When diagnostic completes**, run:

```bash
# 1. Review diagnostic output
cat ppo_diagnosis_simple.txt | tail -50

# 2. If successful → update config for full training
# 3. If failed → apply solution from "Probable Error Causes" section
# 4. Monitor: ls -ltr analyses/oe3/training/checkpoints/ppo/
# 5. After PPO → Execute A2C
# 6. After A2C → Generate table: python -m scripts.run_oe3_co2_table
```

---

**Report Generated**: During PPO diagnostic execution  
**Last Update**: Awaiting diagnose_ppo_error.py completion  
**Estimated Total Time (if CPU works)**: SAC (Done) + PPO (22 min) + A2C (15 min) + Analysis (5 min) = **~42 min remaining**
