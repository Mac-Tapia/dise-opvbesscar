# Diagnóstico de Divergencia SAC - Análisis de Causa Raíz

**Fecha**: 2026-02-02  
**Problema**: SAC colapsa después de 3 episodios (26,280 timesteps)  
**Síntomas**:
- Grid Import: 13.2M kWh (2.3x baseline)
- PV Generation: 8,030 kWh (collapsed from 8M)
- EV Charging: 0 kWh (policy learned to NOT charge)
- Solar/Demand: 0.1% (almost no solar utilization)

---

## 🔴 CAUSAS RAÍZ IDENTIFICADAS (4 PROBLEMAS CRÍTICOS)

### 1. **CLIP OBSERVATION MÁS AGRESIVO DE LO NECESARIO** ⚠️ PRIMARY ISSUE

**Localización**: `src/iquitos_citylearn/oe3/agents/sac.py` línea 479

**Problema**:
```python
clip_obs: float = 5.0  # DEMASIADO BAJO para energías de millones de kWh
```

**Flujo de deterioro**:
```
Raw Observation (ejemplo):
├─ Grid Import: 13,200,000 kWh
├─ PV Generation: 8,030,000 kWh
├─ Building Load: 4,500,000 kWh
└─ EV Demand: 50 kW

                ↓ [PRESCALE by 0.001 for power/energy dims]
                
Prescaled (kW range):
├─ Grid: 13,200 kW
├─ PV: 8,030 kW
├─ Building: 4,500 kW
└─ EV: 0.05 kW  ← YA PERDIDO

                ↓ [Running stats normalization]
                
Normalized (mean=0, std=1):
├─ Approx [-2.5, +2.5] range if std computed correctly
└─ Expected good distribution

                ↓ [CLIP TO [-5.0, +5.0]] ← REDUNDANT, BUT OK IF STATS ARE GOOD
                
Clipped:
├─ Most values preserved if normalization worked
└─ BUT: If running stats fail early (first few episodes),
       clipping to 5.0 is WAY too tight for unnormalized large values
```

**Why it fails**:
- **Episode 1-2**: Running stats not stabilized (`_obs_count = 1e-4`)
- **Raw values**: Grid ~13M, PV ~8M enter the normalization
- **Clipping happens AFTER weak normalization** → Values exceed [-5, 5]
- **Clipped values destroy information**: "Grid=13.2M vs Grid=10M" both clip to `[5.0, 5.0]`
- **Network learns**: "All large values are identical → Can't distinguish scenarios"
- **Policy collapses**: Network can't map observations to actions

---

### 2. **ENTROPY COEFFICIENT TUNING PROBLEMATIC**

**Localización**: `SACConfig` línea 152-154

**Problema**:
```python
ent_coef_init: float = 0.1       # "CRITICAL FIX: 0.5→0.1"
ent_coef_lr: float = 1e-5        # "CRITICAL FIX: 1e-4→1e-5"
```

**Why it's wrong**:
- **`ent_coef_init = 0.1`**: Too low → Agent explores barely at all early
- **`ent_coef_lr = 1e-5`**: Too slow → Entropy coefficient adjusts over 1000+ episodes
- **Combined effect**: With weak exploration (entropy=0.1) + aggressive clipping, network never sees diverse states
- **Result**: Early convergence to "ignore solar, maximize grid" policy (simplest)

**Expected behavior**:
- `ent_coef_init = 0.5-1.0` for high-dim problems (394 obs × 129 actions)
- `ent_coef_lr = 1e-3 to 1e-4` for faster adaptation to task complexity

---

### 3. **MAX GRADIENT NORM TOO TIGHT (Even After Tightening)**

**Localización**: `SACConfig` línea 161

**Problema**:
```python
max_grad_norm: float = 0.5  # "CRITICAL FIX: 1.0→0.5"
```

**Why it matters**:
- Off-policy RL (SAC) **expects larger gradients** than on-policy (PPO)
- `0.5` is normally for **image-based** RL or **very large networks**
- For 256-dim hidden layers with ~394 obs: gradient norms of 5-10 are expected
- **Clipping to 0.5** → Forces very small updates → Network learns slower
- **Combined with `lr=5e-5`** → Updates are microscopic → Policy stuck in local minima

---

### 4. **PRESCALE HEURISTIC FAILS ON EDGE CASES**

**Localización**: `_train_sb3_sac()` wrapper, línea 427-432

**Problema**:
```python
if self.obs_dim > 10:
    self._obs_prescale[:-10] = 0.001  # Power/energy dims
    self._obs_prescale[-10:] = 1.0    # SOC and percentage dims
```

**Issues**:
- **Hardcoded assumption**: Last 10 dims are SOC → False for complex obs spaces
- **Example failure**: If obs_dim=394, last 10 dims might be "charger 20-24 SOC" not all SOC
- **Early dims losing info**: Charger power values in first ~250 dims scaled by 0.001 but still clipped to 5.0
- **EV demand destroyed**: 50 kW → 0.05 → loses significance vs 4500 kW building load

---

## 📊 CASCADING FAILURE SEQUENCE

```
Episode 1:
├─ Initial weights random
├─ First obs: Grid=13.2M, PV=8M, Building=4.5M, EV=0.05
├─ Prescale: Grid=13200, PV=8030, Building=4500, EV=0.00005
├─ Running stats initialized (mean≈0, count=1e-4) ← WRONG STATS
├─ Normalize: (values - 0) / sqrt(1) = values ± 1e4 range
├─ Clip to [-5, 5]: Everything clips
└─ Network input: [5, 5, 5, 5, 5, ...] → Output: Random policy

Episode 2-3:
├─ Agent takes random actions (solar control doesn't matter)
├─ Reward negative (grid import = bad)
├─ Buffer collects experiences of "clipped obs → random action → negative reward"
├─ Network learns: "No matter observation → Always ignore solar → Get negative reward"
├─ Entropy decays: exploration drops further
└─ Policy collapses: "Always request max grid, never control solar"

Result after 3 episodes:
├─ Grid import maximized (13.2M kWh)
├─ PV generation collapsed to 8,030 kWh (just random noise)
├─ EV charging = 0 (never turned on)
└─ Network learned inverse optimal policy
```

---

## ✅ SOLUCIONES (3-TIER FIX)

### TIER 1: Disable aggressive clipping (CRITICAL)
```python
# FILE: src/iquitos_citylearn/oe3/agents/sac.py
# LINE: 479

# OLD:
clip_obs: float = 5.0

# NEW - OPTION A (RECOMMENDED): Disable post-normalization clipping
clip_obs: float = np.inf  # NO clipping after normalization

# NEW - OPTION B (Conservative): Increase to reasonable range
clip_obs: float = 100.0  # Allow 100x normalized values (vs 5x)
```

**Rationale**: Running stats normalization already constrains values. Additional clipping is redundant and destructive.

---

### TIER 2: Fix entropy and gradient norm (HIGH PRIORITY)
```python
# FILE: src/iquitos_citylearn/oe3/agents/sac.py
# LINES: 152-154, 161

# OLD:
ent_coef_init: float = 0.1
ent_coef_lr: float = 1e-5
max_grad_norm: float = 0.5

# NEW:
ent_coef_init: float = 0.5          # Restore to 0.5 (reasonable exploration)
ent_coef_lr: float = 1e-3           # Speed up entropy learning (1e-5 → 1e-3)
max_grad_norm: float = 10.0         # Allow larger gradients for SAC (0.5 → 10.0)
```

**Rationale**: 
- SAC needs strong exploration → higher initial entropy
- High-dim RL needs faster adaptation → higher entropy_lr
- Off-policy training expects larger gradients → relax clipping

---

### TIER 3: Improve prescaling heuristic (MEDIUM PRIORITY)
```python
# FILE: src/iquitos_citylearn/oe3/agents/sac.py
# LOCATION: CityLearnWrapper.__init__ (~line 427)

# OLD:
if self.obs_dim > 10:
    self._obs_prescale[:-10] = 0.001
    self._obs_prescale[-10:] = 1.0
else:
    self._obs_prescale[:] = 0.001

# NEW - More robust detection:
self._obs_prescale[:] = 0.001  # Default: scale all as energy/power
# Detection: If last 10 dims are known to be [0-1] (SOC), scale by 1.0
# For now: Assume CityLearn places SOC last, but document this assumption
# TODO: Add explicit obs_type detection in config

# ALTERNATIVE - Use adaptive prescaling:
self._obs_prescale = self._auto_prescale(obs0_flat, feats)

def _auto_prescale(obs_sample, soc_sample):
    """Detect feature scale by examining initial observation."""
    prescale = np.ones(len(obs_sample) + len(soc_sample))
    
    # If sample has values >> 1000, scale by 0.001 (power/energy)
    # If sample is in [0-1], scale by 1.0 (percentages/SOC)
    for i, val in enumerate(obs_sample):
        prescale[i] = 0.001 if abs(val) > 100 else 1.0
    
    for i, val in enumerate(soc_sample):
        prescale[len(obs_sample) + i] = 1.0  # Always 1.0 for SOC
    
    return prescale
```

---

## 🧪 VERIFICATION PLAN (After applying fixes)

**Test 1: Observation clipping removal**
```python
# Log pre/post normalization values
logger.info("Obs raw: %s", obs[:5])
logger.info("Obs prescaled: %s", prescaled[:5])
logger.info("Obs normalized: %s", normalized[:5])
logger.info("Obs clipped: %s", clipped[:5])

# Expected: normalized ≈ [-2, +2], clipped = normalized (no change)
```

**Test 2: Early entropy behavior**
```python
# Monitor entropy_coef during Episode 1
# Expected: Starts at 0.5, increases slowly (or decreases if task is easy)
# Bad: Stays at 0.1 or decreases too fast
```

**Test 3: Policy diversity**
```python
# Sample 10 actions from same obs
actions_sample = [agent.predict(obs, deterministic=False) for _ in range(10)]
# Expected: Diverse actions (entropy working)
# Bad: All same or nearly identical
```

---

## 📋 SUMMARY TABLE: What Went Wrong in SAC Config

| Parameter | Current | Problem | Recommended | Justification |
|-----------|---------|---------|-------------|---------------|
| `clip_obs` | 5.0 | Too tight, destroys info | inf or 100 | Post-norm clipping redundant |
| `ent_coef_init` | 0.1 | Insufficient exploration | 0.5 | SAC needs entropy for discovery |
| `ent_coef_lr` | 1e-5 | Too slow | 1e-3 | Adapt faster to task complexity |
| `max_grad_norm` | 0.5 | Blocks learning updates | 10.0 | SAC has larger natural gradients |
| `prescale[energy]` | 0.001 | Only partially helpful | 0.001 + robust detection | Combine with clipping fix |

---

## ⚙️ IMPLEMENTATION PRIORITY

**CRITICAL (Do First)**:
1. Remove `clip_obs` clipping (line 479)

**HIGH (Do Next)**:
2. Restore entropy tuning (lines 152-154)
3. Increase max_grad_norm (line 161)

**MEDIUM (Do After)**:
4. Improve prescale detection (line 427)

**Testing**: Run 1-2 test episodes with SAC → check obs values → verify entropy increasing → launch full training

---

## 🎯 EXPECTED OUTCOME (After fixes)

| Metric | Current (Broken) | Expected (Fixed) |
|--------|------------------|------------------|
| Grid Import | 13.2M kWh | 6.5-7.0M kWh (better than BL) |
| PV Utilization | 0.1% | 80-100% (near optimal) |
| EV Charging | 0 kWh | 1.0-1.5M kWh |
| CO₂ Reduction | -126% (worse) | -15 to -25% (like PPO) |
| Policy Stability | Collapsed | Converging |

---

**Status**: Ready to implement fixes in SAC config and test with 5-episode test run.
