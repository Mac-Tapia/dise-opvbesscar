# 🚀 QUICK REFERENCE - TRAINING MONITORING

## Current Status
- **Status**: 🟢 TRAINING ACTIVE
- **Agent**: SAC (Episode 1)
- **Progress**: Step 300+ / ~8,760 per episode
- **Start Time**: 2026-02-03 03:21:22
- **Expected End**: 2026-02-03 06:00-09:00

---

## Monitor Training in Real-Time

### Option 1: Watch Progress File (Every 30 seconds)
```powershell
# PowerShell
while ($true) {
    Get-Content d:\diseñopvbesscar\checkpoints\progress\sac_progress.csv -Tail 3
    Start-Sleep 30
}
```

### Option 2: Python Monitor Script
```bash
python d:\diseñopvbesscar\scripts\monitor_pipeline_live.py
```

### Option 3: Check Main Training Log
```powershell
# See latest 50 lines from main training terminal
Get-Content d:\diseñopvbesscar\checkpoints\progress\sac_progress.csv -Tail 50
```

---

## Expected Behavior

### SAC (Current Phase - 1-2 hours)
```
✓ Starts from scratch (fresh checkpoints)
✓ Runs 3 episodes (26,280 timesteps total)
✓ Saves checkpoint every 500 steps
✓ Generates:
  - checkpoints/sac/sac_step_500.zip
  - checkpoints/sac/sac_step_1000.zip
  - ... (continuing)
  - checkpoints/sac/sac_final.zip
  - outputs/oe3_simulations/result_SAC.json
  - outputs/oe3_simulations/timeseries_SAC.csv
  - outputs/oe3_simulations/trace_SAC.csv
✓ Automatically triggers PPO start when complete
```

### PPO (Next Phase - Automatic)
```
✓ Waits for result_SAC.json creation
✓ Automatically starts (no manual action needed)
✓ Runs 3 episodes (26,280 timesteps)
✓ Same checkpoint & output pattern
✓ Automatically triggers A2C start when complete
```

### A2C (Final Phase - Automatic)
```
✓ Waits for result_PPO.json creation
✓ Automatically starts (no manual action needed)
✓ Runs 3 episodes (26,280 timesteps)
✓ Final results saved
✓ Pipeline complete
```

---

## Files to Check

### Progress Tracking
```
✓ SAC Progress:  checkpoints/progress/sac_progress.csv  [ACTIVE]
✓ PPO Progress:  checkpoints/progress/ppo_progress.csv  [PENDING]
✓ A2C Progress:  checkpoints/progress/a2c_progress.csv  [PENDING]
```

### Results Completion
```
✓ SAC Complete:  outputs/oe3_simulations/result_SAC.json  [MONITORING]
✓ PPO Complete:  outputs/oe3_simulations/result_PPO.json  [PENDING]
✓ A2C Complete:  outputs/oe3_simulations/result_A2C.json  [PENDING]
```

---

## If Something Goes Wrong

### Check Main Training Log
```powershell
# Terminal with training process
Get-ChildItem c7d09f60-7a76-4be2-aeb7-5a56e3bb8b5a
```

### Check for Errors
```powershell
# Look for ERROR or WARNING in logs
Get-Content d:\diseñopvbesscar\checkpoints\progress\sac_progress.csv | 
  Select-String -Pattern "ERROR|WARNING"
```

### Restart if Needed
```bash
# Clean all checkpoints and restart
powershell -Command "
  Remove-Item d:\diseñopvbesscar\checkpoints\* -Recurse -Force
  cd d:\diseñopvbesscar
  python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-baseline
"
```

---

## Performance Expectations

### SAC Metrics (Real-Time Example - Step 300)
```
Reward Avg:         0.3385 (improving)
Actor Loss:         -133.73
Critic Loss:        4,093.61
Entropy Coeff:      0.9901
Grid Import:        54,585.8 kWh
Solar Generation:   255,150.9 kWh ✨
CO2 Avoided:        115,353.7 kg (solar) + 32,190 kg (EV) 🌱
```

### Expected Trend
```
Episode 1: Reward 0.30-0.40 (learning starts)
Episode 2: Reward 0.40-0.60 (convergence)
Episode 3: Reward 0.50-0.70 (stabilization)
```

---

## Success Criteria

✅ **SAC Complete When**:
- `result_SAC.json` exists
- `timeseries_SAC.csv` has 8,760 rows
- `trace_SAC.csv` has 8,760 rows
- File size > 100 KB

✅ **PPO Complete When**:
- Same criteria as SAC
- Auto-triggered after SAC done
- Should see result_PPO.json after 1-2 hours of PPO training

✅ **A2C Complete When**:
- Same criteria as SAC/PPO
- Auto-triggered after PPO done
- Final file in pipeline

✅ **Pipeline Complete When**:
- All 9 files present (3 agents × 3 files each)
- All files have 8,760 rows
- All agents have result JSON files

---

## 🎯 Bottom Line

**Just Let It Run!**

The pipeline is autonomous:
1. ✅ SAC is training now
2. ✅ PPO will auto-start when SAC finishes
3. ✅ A2C will auto-start when PPO finishes
4. ✅ All files will be auto-generated
5. ✅ No manual intervention needed

**Expected Total Time**: 3-6 hours
**When Complete**: 2026-02-03 06:00-09:00

Monitor occasionally, but the system handles everything automatically.
