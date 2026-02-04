# 🔧 PPO & A2C Advantage Function Integration (PENDING IMPLEMENTATION)

**Date**: 2026-02-04  
**Status**: 📋 READY FOR IMPLEMENTATION  
**Scope**: Complete advantage function integration for EV utilization bonus in PPO and A2C

---

## 📍 Overview

This document describes HOW to integrate the EV utilization bonus into the advantage function (critic) for PPO and A2C agents. The configuration phase is complete; this covers the implementation phase.

### Why Advantage Function Integration?

- **SAC**: Off-policy, learns from replay buffer → Bonus as reward component ✅ DONE
- **PPO**: On-policy batch → Bonus modulates advantages from GAE
- **A2C**: On-policy synchronous → Bonus directly modulates critic target

---

## 🎯 PPO Integration Strategy

### Architecture: Advantage Modulation via GAE

PPO uses **Generalized Advantage Estimation** (GAE):
```
advantage_t = rt + γ V(s_{t+1}) - V(st)  (TD residual)
    ↓ (with GAE)
advantages = low-pass-filter(advantage_t)  (smooth over trajectory)
```

### Integration Point: After GAE Computation

**Location**: `ppo_sb3.py` → `PPOAgent.learn()` method (around lines 250-300)

**Implementation Pattern**:
```python
def learn(self, total_timesteps: int) -> None:
    """Train PPO with EV utilization bonus modulation."""
    
    # Standard PPO training loop setup...
    self.model = PPO(...)
    
    # >>> ADD BONUS MODULATION HERE <<<
    original_learn = self.model.learn
    
    def learn_with_bonus(total_timesteps):
        # Collect rollouts
        rollouts = self.collect_rollouts(total_timesteps)
        
        for epoch in range(self.config.n_epochs):
            # Compute advantages with GAE
            advantages = self.compute_gae_advantages(rollouts)
            
            # 🟢 BONUS MODULATION
            if self.config.use_ev_utilization_bonus:
                ev_utilization_scores = self.extract_ev_utilization_from_obs(rollouts)
                
                # Scale bonus by decaying entropy factor
                entropy_factor = max(0.5, 1.0 - (epoch / self.config.n_epochs))
                bonus_weight = (self.config.ev_utilization_weight * 
                               entropy_factor)
                
                # Modulate advantages
                advantages *= (1.0 + bonus_weight * ev_utilization_scores)
            
            # Update policy with modulated advantages
            self.update_policy(rollouts, advantages)
    
    learn_with_bonus(total_timesteps)
```

### Key Variables

| Variable | Source | Type | Range |
|----------|--------|------|-------|
| `advantages` | GAE computation | ndarray (n_steps,) | [-∞, +∞] typically [-1, 1] |
| `ev_utilization_scores` | Observation extraction | ndarray (n_steps,) | [-1, 1] |
| `entropy_factor` | Epoch schedule | float | [0.5, 1.0] |
| `bonus_weight` | Config × entropy | float | [0.025, 0.05] |
| `modulated_advantages` | advantages × (1 + bonus) | ndarray (n_steps,) | [-1.5, 1.5] |

### Extraction Logic: `extract_ev_utilization_from_obs()`

PPO observations include EV SOC data. Extract and compute bonus:

```python
def extract_ev_utilization_from_obs(self, rollouts) -> np.ndarray:
    """Extract EV utilization scores from PPO observations.
    
    Observations (394-dim) structure:
    - [0-100]: Weather/Grid metrics
    - [101-228]: Building load + Solar + BESS states
    - [229-356]: 128 chargers × 1 metric (SOC or state)
    - [357-393]: Time features (hour, month, day_of_week)
    
    Returns:
        ev_utilization_scores: ndarray shape (n_steps,) with values [-1, 1]
    """
    obs = rollouts.observations  # shape (n_steps, 394)
    
    # Extract EV-related observations (charger SOC data)
    # Assuming columns 229-356 contain charger SOC (128 chargers)
    charger_soc_cols = slice(229, 357)  # 128 columns
    charger_soc = obs[:, charger_soc_cols]  # shape (n_steps, 128)
    
    # Compute average SOC per step
    ev_soc_avg = np.mean(charger_soc, axis=1)  # shape (n_steps,)
    
    # Compute utilization score (matches reward calculation)
    scores = np.zeros(len(ev_soc_avg))
    for t, soc in enumerate(ev_soc_avg):
        if soc < self.config.ev_soc_optimal_min:  # 0.70
            scores[t] = -0.2 * min(1.0, (self.config.ev_soc_optimal_min - soc) / 0.30)
        elif soc <= self.config.ev_soc_optimal_max:  # 0.90
            utilization_score = (soc - 0.70) / 0.20
            scores[t] = 2.0 * utilization_score - 1.0
        else:  # > 0.90
            if soc > self.config.ev_soc_overcharge_threshold:  # 0.95
                overcharge = (soc - 0.95) / 0.05
                scores[t] = -0.3 * min(1.0, overcharge)
            else:  # 0.90-0.95
                scores[t] = +1.0  # Still in good zone
    
    return scores  # shape (n_steps,) with values in [-1, 1]
```

### Entropy Decay Integration

PPO entropy decay affects bonus impact:

```python
# In learn() loop
for epoch in range(self.config.n_epochs):
    # Entropy decay: 0.999 → slows down faster than A2C (0.998)
    entropy_mult = self.config.ent_decay_rate ** epoch
    
    # Bonus weight decays with entropy for stability
    effective_bonus_weight = self.config.ev_utilization_weight * entropy_mult
    
    # Apply modulation
    advantages *= (1.0 + effective_bonus_weight * ev_utilization_scores)
```

---

## 🎯 A2C Integration Strategy

### Architecture: Direct Advantage Modulation

A2C is simpler than PPO (no GAE, no n_epochs):
```
advantage_t = rt + γ V(s_{t+1}) - V(st)  (simple TD)
target_value_t = rt + γ V(s_{t+1})
```

### Integration Point: Critic Target Computation

**Location**: `a2c_sb3.py` → `A2CAgent.learn()` method (around lines 280-330)

**Implementation Pattern**:
```python
def learn(self, total_timesteps: int) -> None:
    """Train A2C with direct EV utilization bonus modulation."""
    
    self.model = A2C(...)
    
    # >>> ADD BONUS INTEGRATION HERE <<<
    original_compute_advantage = self.model.compute_advantage
    
    def compute_advantage_with_bonus(obs, returns, last_values):
        # Compute standard A2C advantage
        advantages = returns - self.model.value_fn(obs)
        
        # 🟢 BONUS MODULATION (A2C-SPECIFIC)
        if self.config.use_ev_utilization_bonus:
            ev_utilization_scores = self.extract_ev_utilization_from_obs(obs)
            
            # A2C: Very slow decay for synchronous on-policy stability
            step_counter = getattr(self, '_step_counter', 0)
            decay_factor = self.config.ev_utilization_decay ** (step_counter / 1000)
            
            bonus_weight = self.config.ev_utilization_weight * decay_factor
            
            # Direct advantage modulation (simpler than PPO)
            advantages += bonus_weight * ev_utilization_scores * returns.std()
        
        return advantages
    
    self.model.compute_advantage = compute_advantage_with_bonus
    self.model.learn(total_timesteps)
```

### Key Difference: Decay Application

**PPO**: Entropy decay affects bonus → `entropy_mult ** epoch`
**A2C**: Step-based decay → `decay ** (step_count / 1000)`

```python
# A2C decay is global (not per-epoch)
# Reason: A2C updates synchronously, no epoch concept
# Example: After 1M steps, decay = 0.998^1000 ≈ 0.368 (from 0.05 → 0.018)
```

### Extraction Logic: Same as PPO

A2C uses same observation structure, so extraction is identical:

```python
def extract_ev_utilization_from_obs(self, obs) -> np.ndarray:
    # Same implementation as PPO
    # Extract charger_soc columns 229-356
    # Compute utilization score [-1, 1]
    # Return shape (batch_size,)
    pass
```

### Stability Considerations for A2C

A2C is more sensitive to advantage scaling:

```python
# Option 1: Scale by returns std (recommended)
advantages += bonus_weight * scores * returns.std()

# Option 2: Scale by running estimate of advantage std
advantages += bonus_weight * scores * self.advantage_running_std

# Option 3: Clip bonus impact (safest)
bonus_impact = np.clip(bonus_weight * scores, -0.1, 0.1)
advantages += bonus_impact
```

**Recommended**: Use Option 1 (returns std scaling) - automatically adapts to training phase.

---

## 🔄 Comparison: PPO vs A2C Implementation

| Aspect | PPO | A2C |
|--------|-----|-----|
| **Decay Schedule** | Per-epoch: `decay ** epoch` | Global per-step: `decay ** (steps/1000)` |
| **Advantage Scaling** | Multiplication: `adv *= (1 + bonus)` | Addition: `adv += bonus * std` |
| **Entropy Integration** | Yes: `entropy_factor` | No: pure step decay |
| **Update Frequency** | Multiple epochs per batch | Single update per batch |
| **Stability Risk** | Medium (GAE smoothing) | High (no smoothing) |
| **Bonus Impact Range** | adv × [0.95, 1.05] (multiplicative) | adv ± [0.05, 0.10] (additive) |

---

## 📋 Implementation Checklist

### Phase 1: PPO Advantage Integration

- [ ] Locate PPO.learn() method in ppo_sb3.py
- [ ] Identify GAE advantage computation section
- [ ] Add `extract_ev_utilization_from_obs()` method (30 lines)
- [ ] Implement bonus modulation in epoch loop (15 lines)
- [ ] Add entropy_factor scaling (5 lines)
- [ ] Test with dummy episode (no training)
- [ ] Verify r_ev_utilization appears in metrics

### Phase 2: A2C Advantage Integration

- [ ] Locate A2C.learn() method in a2c_sb3.py
- [ ] Identify critic target computation section
- [ ] Add `extract_ev_utilization_from_obs()` method (30 lines)
- [ ] Implement bonus modulation with decay (15 lines)
- [ ] Add returns.std() scaling (5 lines)
- [ ] Test with dummy episode (no training)
- [ ] Verify decay factor decreases over time

### Phase 3: Unified Testing

- [ ] Train SAC 1 episode (verify r_ev_utilization in logs)
- [ ] Train PPO 1 episode (verify advantage modulation works)
- [ ] Train A2C 1 episode (verify decay factor decreases)
- [ ] Compare r_ev scores across all 3 agents
- [ ] Check total rewards scale correctly

### Phase 4: Production Training

- [ ] Train SAC for full schedule (default: 5 episodes)
- [ ] Train PPO for full schedule (default: 500k timesteps)
- [ ] Train A2C for full schedule (default: 500k timesteps)
- [ ] Generate CO₂ comparison table
- [ ] Verify EV utilization improvements vs baseline

---

## 🧪 Testing Strategy

### Unit Tests for Extraction Logic

```python
def test_extract_ev_utilization():
    # Create mock observations
    obs = np.random.uniform(0, 1, (100, 394))
    
    # Test low utilization (SOC < 0.70)
    obs[:, 229:357] = 0.50  # All chargers at 50% SOC
    scores = extract_ev_utilization_from_obs(obs)
    assert scores.mean() < -0.1  # Should penalize low util
    
    # Test optimal utilization (SOC = 0.80)
    obs[:, 229:357] = 0.80
    scores = extract_ev_utilization_from_obs(obs)
    assert scores.mean() > 0.5  # Should reward
    
    # Test overcharge (SOC > 0.95)
    obs[:, 229:357] = 0.97
    scores = extract_ev_utilization_from_obs(obs)
    assert scores.mean() < 0.2  # Should penalize concentration
```

### Integration Tests

```python
def test_ppo_advantage_modulation():
    config = PPOConfig(use_ev_utilization_bonus=True, 
                      ev_utilization_weight=0.05)
    agent = PPOAgent(env, config)
    
    # Collect one trajectory
    rollouts = agent.collect_rollouts(2048)
    
    # Compute advantages
    advantages = agent.compute_gae_advantages(rollouts)
    
    # Extract bonus scores
    scores = agent.extract_ev_utilization_from_obs(rollouts.observations)
    
    # Verify modulation
    original_std = advantages.std()
    modulated = advantages * (1.0 + 0.05 * scores)
    new_std = modulated.std()
    
    assert new_std > original_std * 0.95  # Not inverted
    assert new_std < original_std * 1.10  # Reasonable increase
```

---

## 📊 Expected Impact on Training

### PPO Training Curves

**Before Integration**:
```
Episode 1: avg_reward = -0.15
Episode 2: avg_reward = -0.08
Episode 3: avg_reward = +0.12
Episode 4: avg_reward = +0.28
Episode 5: avg_reward = +0.35
```

**After Integration** (expected):
```
Episode 1: avg_reward = +0.05  ← Bonus encourages utilization early
Episode 2: avg_reward = +0.18
Episode 3: avg_reward = +0.35
Episode 4: avg_reward = +0.45  ← Convergence with bonus signal
Episode 5: avg_reward = +0.52
```

### A2C Training Curves

**Convergence Time**:
- Without bonus: 500k steps to convergence
- With bonus: 450k steps (faster due to bonus signal)
- Stability: Same or slightly better (slow decay helps)

---

## ⚙️ Configuration Values for Fine-Tuning

### If Training is Unstable

**PPO** (if advantages explode):
```python
ev_utilization_weight: float = 0.02  # Reduce from 0.05
# Rationale: Smaller weight for more stable training
```

**A2C** (if oscillating):
```python
ev_utilization_decay: float = 0.990  # Slower from 0.998
# Rationale: Even slower decay for stability
```

### If Agents Are Not Improving EV Utilization

**PPO** (maximize bonus impact):
```python
ev_utilization_weight: float = 0.10  # Increase from 0.05
ev_soc_optimal_min: float = 0.60  # Lower threshold
# Rationale: More reward for any charging activity
```

**A2C** (same as PPO):
```python
ev_utilization_weight: float = 0.10
ev_soc_optimal_min: float = 0.60
```

---

## 🎯 Success Criteria

✅ **Implementation Complete When**:
1. PPO.learn() calls bonus modulation function every epoch
2. A2C.learn() applies decay factor every 1000 steps
3. r_ev_utilization scores appear in training logs
4. Average EV SOC increases to 0.75-0.85 range (optimal zone)
5. No advantage explosion (std < 2x original)
6. Training loss remains stable across episodes

✅ **Production Ready When**:
1. All 3 agents train 1 full episode without errors
2. CO₂ comparison shows EV utilization bonus effect (+2-5% improvement)
3. Bonus not overpowering other objectives (co2, cost, solar)
4. Total training time acceptable (< 2 hours for 5 episodes SAC)

---

## 📚 Reference Materials

**Files to Modify**:
- `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` (~300 lines, modify .learn() method)
- `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` (~330 lines, modify .learn() method)

**Files to Reference**:
- `src/iquitos_citylearn/oe3/rewards.py` (r_ev_utilization logic)
- `src/iquitos_citylearn/oe3/simulate.py` (observation structure, line 100+)

**Testing**:
- `scripts/run_agent_ppo.py` (launch PPO training)
- `scripts/run_agent_a2c.py` (launch A2C training)

---

**Status**: 📋 READY FOR DEVELOPER IMPLEMENTATION  
**Estimated Time**: 2-3 hours for both PPO + A2C + testing  
**Complexity**: Medium (straightforward, well-documented)

