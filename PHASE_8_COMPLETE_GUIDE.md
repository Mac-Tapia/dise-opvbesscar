# PHASE 8: AGENT TRAINING - COMPLETE GUIDE

**Status**: Ready to Begin (After Python 3.11 Installation)  
**Date**: 2026-01-25  
**Duration**: 4-6 hours (sequential execution)  
**Prerequisites**: Python 3.11 + CityLearn v2  

---

## 📋 TABLE OF CONTENTS

1. [Quick Start (5 minutes)](#quick-start)
2. [Detailed Walkthrough](#detailed-walkthrough)
3. [Agent Specifications](#agent-specifications)
4. [Training Execution](#training-execution)
5. [Monitoring & Troubleshooting](#monitoring)
6. [Performance Evaluation](#evaluation)
7. [Results Analysis](#results-analysis)
8. [Next Steps](#next-steps)

---

## 🚀 QUICK START {#quick-start}

### Prerequisites Check (1 minute)

<!-- markdownlint-disable MD013 -->
```bash
# Verify Python 3.11
python --version  # Should output: Python 3.11.x

# Verify CityLearn installed
python -c "import citylearn; print('✅ CityLearn ready')"

# Verify project structure
ls -la src/iquitos_citylearn/oe3/agents/
# Should show: sac.py, ppo_sb3.py, a2c_sb3.py
```bash
<!-- markdownlint-enable MD013 -->

### Step 1: Build Dataset (15-30 minutes)

<!-- markdownlint-disable MD013 -->
```ba...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Step 2: Quick Test (5 minutes - OPTIONAL)

<!-- markdownlint-disable MD013 -->
```bash
# Test one agent for 1 episode (verify no errors)
python scripts/train_quick.py --episodes 1 --agent PPO

# Expected: Completes in ~5 min without errors
```bash
<!-- markdownlint-enable MD013 -->

### Step 3: Full Training (4-5 hours)

<!-- markdownlint-disable MD013 -->
```bash
# Train all 3 agents sequentially
python scripts/train_agents_serial.py --device cuda --episodes 50

# Or individual age...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Step 4: View Results (1 minute)

<!-- markdownlint-disable MD013 -->
```bash
# Show CO2 comparison
cat COMPARACION_BASELINE_VS_RL.txt

# View training logs
tail -50 analyses/logs/ppo_training.log
```bash
<!-- markdownlint-enable MD013 -->

---

## 📚 DETAILED WALKTHROUGH {#detailed-walkthrough}

### What is Phase 8?

Phase 8 trains **three reinforcement learning agents** (SAC, PPO, A2C) to
optimize EV charger scheduling:

**Problem**: 128 chargers × 8,760 hourly decisions =...
```

[Ver código completo en GitHub]bash
CityLearn Environment (534 dims in, 126 dims out)
    ↓
 RL Agent (PPO/SAC/A2C)
    ↓
 Neural Network Policy (1024 → 1024 → 126)
    ↓
 Action: Charger power setpoints [0, 1]
    ↓
 Reward: Multi-objective
  - CO2: -0.50 × (grid_import_kwh × 0.4521)
  - Solar: +0.20 × (pv_used / pv_generated)
  - Cost: -0.10 × (grid_import_kwh × 0.20)
  - EV: -0.10 × max(0, demand - supply)
  - Grid: -0.10 × max(0, peak - baseline)
```bash
<!-- markdownlint-enable MD013 -->

### Data Flow (Phase 7 → Phase 8)

<!-- markdownlint-disable MD013 -->
```bash
Phase 7 Outputs                Phase 8 Execution
    ↓                               ↓
data/interim/oe2/          Build Dataset
  - solar_ts.csv      →    (dataset_builder.py)
  - chargers/              ↓
  - bess_config.json   outputs/schema.json
    ↓                      + charger_...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🤖 AGENT SPECIFICATIONS {#agent-specifications}

### SAC (Soft Actor-Critic)

**Type**: Off-policy entropy-regularized actor-critic  
**Key Innovation**: Maximizes reward AND entropy (encourages exploration)  
**Pros**:

- Sample-efficient (learns from replay buffer)
- Handles continuous action spaces well
- Good with sparse rewards

**Cons**:

- Can be unstable in large action spaces
- Entropy coefficient requires tuning

**Hyperparameters**:

<!-- markdownlint-disable MD013 -->
```bash
learning_rate: 2.0e-4
batch_size: 256 (large for stability)
hidden_sizes: [1024, 1024]
entropy_coef: "auto" (learned)
target_update_interval: 1
use_sde: true (stochastic dynamics exploration)
use_amp: true (mixed precision)
```bash
<!-- markdownlint-enable MD013 -->

**Expected Performance**:

- **Convergence**: 20-30 episodes
- **CO₂ Reduction**: 20-26% vs baseline
- **Solar Utilization**: 60-65%...
```

[Ver código completo en GitHub]bash
learning_rate: 2.0e-4 (linear decay)
batch_size: 128
n_epochs: 20 (repeated gradient updates)
n_steps: 2048 (rollout length)
clip_range: 0.1 (conservative clipping)
gae_lambda: 0.98 (generalized advantage estimation)
use_amp: true
```bash
<!-- markdownlint-enable MD013 -->

**Expected Performance**:

- **Convergence**: 25-35 episodes (slower but stable)
- **CO₂ Reduction**: 25-29% vs baseline (best)
- **Solar Utilization**: 65-70% (best)
- **Final Reward**: -700 to -400 (most stable)
- **Training Time**: 90-120 min

**When to Use**: When you need reliability and best performance

---

### A2C (Advantage Actor-Critic)

**Type**: On-...
```

[Ver código completo en GitHub]bash
learning_rate: 2.0e-4 (linear decay)
n_steps: 2048 (multi-step advantage)
batch_size: 64 (smaller batches)
gae_lambda: 1.0 (Monte Carlo)
use_rms_prop: true (RMSProp instead of Adam)
normalize_advantage: true
```bash
<!-- markdownlint-enable MD013 -->

**Expected Performance**:

- **Convergence**: 20-30 episodes (fastest)
- **CO₂ Reduction**: 20-25% vs baseline
- **Solar Utilization**: 60-65%
- **Final Reward**: -850 to -550 (variable)
- **Training Time**: 60-90 min (fastest)

**When to Use**: When you need fast training and reasonable performance

---

### Common Architecture (All Agents)

<!-- markdownlint-d...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Total Parameters**: ~1.3M per agent

---

## ⚙️ TRAINING EXECUTION {#training-execution}

### Pre-Training Checklist

<!-- markdownlint-disable MD013 -->
```bash
# 1. Verify Python version
python --version  # → Python 3.11.x ✓

# 2. Verify CityLearn
python -c "import citylearn; print(citylearn.__version__)"  # → 2.5.x ✓

# 3. Check output directory
ls -la outputs/  # Should have schema_*.json

# 4. Verify checkpoints directory
mkdir -p checkpoints/{SAC,PPO,A2C}
mkdir -p analyses/logs/

# 5. Verify dataset exists
ls data/processed/citylearnv2_dataset/schema...
```

[Ver código completo en GitHub]bash
# One command trains all 3 agents sequentially
python scripts/train_agents_serial.py \
  --device cuda \
  --episodes 50 \
  --save_interval 8760 \
  --verbose 1

# Expected output: (2)
# Starting SAC training...
#   Episode 1/50: reward=-750, CO2_reduction=18%
#   Episode 5/50: reward=-600, CO2_reduction=22%
#   ...
#   Episode 50/50: reward=-550, CO2_reduction=25%
# SAC training complete. Checkpoint saved.
#
# Starting PPO training...
#   [similar output]
#
# Starting A2C training...
# [similar output] (2)
#
# All agents trained. Results in COMPARACION_BASELINE_VS_RL.txt
```bash
<!-- markdownlint-enable MD013 -->

**Expected Duration**: 4-5 hours on GPU

---

### Option B: Individual Agent Training

<!-- markdownlint-disable MD013 -->
```bash
# Train SAC only
python -m scripts.run_oe3_sac_training \
  --episodes 50 \
  --device cuda \
  --learning_rate 2e-4 \
  --batch_size 256

# Train PPO only
python -m scripts.run_oe3_ppo_training \
  --episodes 50 \
  --device cuda \
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Pros**: Can run in parallel on different GPUs  
**Cons**: More manual management

---

### Option C: Quick Test (1 episode, 5 minutes)

<!-- markdownlint-disable MD013 -->
```bash
# Verify everything works before full training
python scripts/train_quick.py \
  --agent PPO \
  --episodes 1 \
  --device cuda

# Expected: Completes in ~5 minutes
# If successful, proceed to full training
# If fails, check error message and troubleshoot
```bash
<!-- markdownlint-enable MD013 -->

---

### Option D: Resume from Checkpoint

<!-- markdownlint-disable MD013 -->
```bash
# If training...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 📊 MONITORING & TROUBLESHOOTING {#monitoring}

### Real-Time Monitoring

**In a separate terminal (while training runs)**:

<!-- markdownlint-disable MD013 -->
```bash
# Watch training progress (updates every 5 seconds)
python scripts/monitor_training_live_2026.py

# Output:
# Agent     Episode  Reward    Total Steps   Progress
# ========================================================
# SAC       15/50    -650      131400        30%
# PPO       0/50     -       0             0%
# A2C       0/50     -       0             0%
```bash
<!-- markdownlint-enable MD013...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

### Log Files

**Where to find logs**:

<!-- markdownlint-disable MD013 -->
```bash
analyses/logs/
├── SAC_training_20260125.log      # Detailed SAC logs
├── PPO_training_20260125.log      # Detailed PPO logs
├── A2C_training_20260125.log      # Detailed A2C logs
├── SAC/events.out.tfevents.*      # TensorBoard events
├── PPO/events.out.tfevents.*
└── A2C/events.out.tfevents.*
```bash
<!-- markdownlint-enable MD013 -->

**View logs**:

<!-- markdownlint-disable MD013 -->
```bash
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

### Common Issues & Solutions

#### Issue 1: "ImportError: No module named 'citylearn'"

**Cause**: CityLearn not installed (requires Python 3.11)

**Solution**:

<!-- markdownlint-disable MD013 -->
```bash
# Verify Python 3.11 (2)
python --version  # Must be 3.11.x

# Install CityLearn
pip install citylearn>=2.5.0

# Verify
python -c "import citylearn; print('✅ Ready')"
```bash
<!-- markdownlint-enable MD013 -->

---

#### Issue 2: "CUDA out of memory" / "RuntimeError: CUDA error"

**Cause**: GPU memory exceeded

**Solutions** (try in order):

<!-- markdownlint-disable MD013 -->
```bash
# 1. Reduce ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

#### Issue 3: "Agent training stuck at negative rewards (not learning)"

**Cause**: Dataset not generated or old schema used

**Solution**:

<!-- markdownlint-disable MD013 -->
```bash
# Regenerate dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Verify schema generated
ls outputs/schema_*.json

# Verify charger CSVs created
ls data/processed/citylearnv2_dataset/buildings/*/charger_simulation_*.csv|wc -l
# Should show 128 files

# Try training again
python scripts/train_quick.py --episodes 1
```bash
<!-- markdownlint-enable MD013 -->

---

#### Is...
```

[Ver código completo en GitHub]bash
# Update gymnasium to compatible version
pip install gymnasium==0.28.1

# Verify (2)
python -c "import gymnasium; print(gymnasium.__version__)"
```bash
<!-- markdownlint-enable MD013 -->

---

#### Issue 5: "Checkpoint incompatible: KeyError in loading state dict"

**Cause**: Agent code changed but trying to load old checkpoint

**Solution**:

<!-- markdownlint-disable MD013 -->
```bash
# Delete old checkpoints
rm -rf checkpoints/PPO/*
rm -rf checkpoints/SAC/*
rm -rf checkpoints/A2C/*

# Restart training from scratch
python scripts/train_agents_s...
```

[Ver código completo en GitHub]bash
Episode Reward: Total reward accumulated (should increase/stabilize)
CO2 Reduction: Percentage vs baseline (target: ≥20%)
Solar Utilization: Percentage of PV used (target: ≥60%)
Grid Stability: Peak demand reduction (target: ≥15%)
```bash
<!-- markdownlint-enable MD013 -->

**Healthy training curves**:

- Reward increases quickly in first 10 episodes
- Then stabilizes around final value
- Minimal variance after episode 30
- No sudden drops (indicates learning plateau)

**Red flags**:

- Reward stays flat (agent not learning)
- Reward decreases over time (wrong configuration)
- Huge variance (unstable learning)
- NaN values (numeric...
```

[Ver código completo en GitHub]bash
# Automatic (part of training script output)
cat COMPARACION_BASELINE_VS_RL.txt

# Expected output: (3)
# ┌─────────────────────────────────────────┐
# │ Agent │ CO2 Reduction │ Solar % │ Cost  │
# ├───────┼───────────────┼─────────┼───────┤
# │Baseline│ 0%           │ 40%    │ 0%    │
# │ SAC    │ 25%          │ 65%    │ 8%    │
# │ PPO    │ 29%          │ 68%    │ 12%   │
# │ A2C    │ 22%          │ 62%    │ 6%    │
# └─────────────────────────────────────────┘
```bash
<!-- markdownlint-enable MD013 -->

---

#### 2. Analyze Training Logs

<!-- markdownlint-disable MD013 -->
```bash
# Extract key metrics
python -c "
import json
logs = json.load(open('TRAINING_CHECKPOINTS_SUMMARY_*.json'))
for agent in logs:
    print(f\"{agent['agent']}: \")
    print(f\"  Episodes: {agent['episode']}\")
    print(f\"  Total steps: {agent['total_steps']}\")
    print(f\"  Best r...
```

[Ver código completo en GitHub]bash
# Create visualization (if implemented)
python scripts/plot_training_results.py

# Outputs:
# analyses/plots/reward_curves.png        # Reward vs episode
# analyses/plots/co2_comparison.png       # CO2 vs baseline
# analyses/plots/solar_utilization.png    # Solar usage
# analyses/plots/grid_stability.png       # Peak demand reduction
```bash
<!-- markdownlint-enable MD013 -->

---

#### 4. Detailed Agent Comparison

<!-- markdownlint-disable MD013 -->
```bash
# Compare agents side-by-side
python scripts/agent_comparison_report.py

# Output: analyses/agent_comparison_report.txt
# Contains:
# - Performance metrics for each agent
# - Convergence speed comparison
# - Robustness analysis
# - Recommendations for production
```bash
<!-- mark...
```

[Ver código completo en GitHub]bash
┌──────────────────────────────────────────────────────────┐
│ AGENT PERFORMANCE AFTER 50 EPISODES                     │
├──────────────────────────────────────────────────────────┤
│ Metric              │ SAC    │ PPO    │ A2C    │ Target │
├─────────────────────┼────────┼────────┼────────┼────────┤
│ CO₂ Reduction       │ 25%    │ 29%    │ 22%    │ ≥20%   │
│ Solar Utilization   │ 65%    │ 68%    │ 62%    │ ≥60%   │
│ Cost Savings        │ 8%     │ 12%    │ 6%     │ ≥5%    │
│ Grid Peak Reduction │ 12%    │ 15%    │ 10%    │ ≥15%   │
│ EV Satisfaction     │ 98%    │ 99%    │ 97%    │ ≥95%   │
│ Final Episode Reward│ -550   │ -450   │ -650   │ Stable │
│ Convergence Speed   │ Fast   │ Medium │ Fast   │ <30ep  │
└──────────────────────────────────────────────────────────┘

RECOMMENDATION: Use PPO for production (best performance + stability)
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔄 NEXT STEPS {#next-steps}

### Immediate (After Phase 8 Complete)

1. **Review Results**

<!-- markdownlint-disable MD013 -->
   ```bash
   cat COMPARACION_BASELINE_VS_RL.txt
   # Verify CO2 reduction ≥20% and solar ≥60%
```bash
<!-- markdownlint-enable MD013 -->

2. **Document Findings**
   - Create final performance report
   - Screenshot key metrics
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

### Short-Term (Optional - Fine-tuning)

1. **Hyperparameter Tuning** (if needed)
   - Adjust learning rates
   - Modify reward weights
   - Test different network architectures

2. **Extended Training** (if convergence incomplete)

<!-- markdownlint-disable MD013 -->
   ```bash
   python scripts/train_agents_serial.py --episodes 100  # Double training
```bash
<!-- markdownlint-enable MD013 -->

3. **Agent Comparison**
   - Run same test episode for all 3 agents
   - Compare decisions (action distributions)
   - Analyze failure modes

---

### Medium-Term (Phase 9 - Deployment)

1. **Production Selection**
   - Select best agent (likely PPO)
   - Export model weights
   -...
```

[Ver código completo en GitHub]bash
# Once Python 3.11 installed and CityLearn installed:
python scripts/train_agents_serial.py --device cuda --episodes 50
```bash
<!-- markdownlint-enable MD013 -->

Good luck! 🚀
