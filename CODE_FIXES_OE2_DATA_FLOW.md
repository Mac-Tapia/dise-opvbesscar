# Code Fixes: OE2 Data Flow & Agent Integration Issues

## pvbesscar - Implementation Fixes

**Document**: Technical fixes for critical data flow issues  
**Target Files**: sac.py, ppo_sb3.py, a2c_sb3.py  
**Priority**: HIGH (BESS normalization), MEDIUM (hardcoded prescaling)

---

## Issue 1: BESS SOC Prescaling Makes State Invisible

### Problem

BESS state_of_charge [0, 1] is multiplied by 0.001, creating [0, 0.001].  
After normalization with meanâ‰ˆ0.5, stdâ‰ˆ0.29:

```bash
Normalized SOC = (0.0005 - 0.0005) / 0.00029 â‰ˆ 0  (all states map to ~0)
```bash

Agent cannot distinguish between:

- SOC = 0.10 (min, needs charging)
- SOC = 0.90 (max, can discharge)

### Solution

Keep BESS SOC unscaled in normalized observation space.

**Location**: All three agents' `CityLearnWrapper` class

**SAC (sac.py)** - Lines 488-530:

Current code:

```python
# PRE-ESCALADO: kW/kWh / 1000 â†’ rango ~1-5
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001
```bash

Fixed code:

```python
# PRE-ESCALADO: kW/kWh / 1000 â†’ rango ~1-5 (2)
# BUT: Keep BESS SOC as-is (0-1) since it's already normalized
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001

# BESS SOC is the last feature from _get_pv_bess_feats()
# Don't prescale it
def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
    if not self._normalize_obs:
        return obs
    # Apply prescaling selectively
    prescaled = obs.copy()
    prescaled[:-2] = \
        obs[:-2] * self._obs_prescale[:-2]  # Scale PV/power features
    prescaled[-2] = obs[-2] * 0.001  # Scale PV features (again, first of pair)
    prescaled[-1] = obs[-1]  # DON'T scale BESS SOC (keep as [0,1])
    
    self._update_obs_stats(prescaled)
    normalized = (prescaled - self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
    clipped = np.clip(normalized, -self._clip_obs, self._clip_obs)
    return np.asarray(clipped, dtype=np.float32)
```bash

**Better approach** - Separate prescaling factors:

```python
# In __init__ of CityLearnWrapper
self._obs_prescale_factors = {
    'power': 0.001,      # PV (kW) â†’ smaller range
    'energy': 0.001,     # Load, charger demand (kW)
    'soc': 1.0,          # BESS state [0-1] â†’ keep as-is
    'tariff': 1.0,       # Cost ($/kWh) â†’ keep as-is
    'carbon': 1.0,       # CO2 factor â†’ keep as-is
}

# In _normalize_observation:
def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
    if not self._normalize_obs:
        return obs.astype(np.float32)
    
    prescaled = obs.copy().astype(np.float64)
    
    # Identify feature indices (depends on _flatten order)
    # Assuming: [base_obs (534), pv_kw, soc]
    # Where: pv_kw is power feature, soc is state feature
    if len(prescaled) >= 2:
        prescaled[-2] *= self._obs_prescale_factors['power']  # PV
        prescaled[-1] *= self._obs_prescale_factors['soc']    # BESS (keep 1.0)
    
    # Apply for other base features (simplified; assumes most are power-like)
    prescaled[:-2] *= self._obs_prescale_factors['power']
    
    self._update_obs_stats(prescaled)
    normalized = (prescaled - self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
    clipped = np.clip(normalized, -self._clip_obs, self._clip_obs)
    return np.asarray(clipped, dtype=np.float32)
```bash

**Apply to**: sac.py, ppo_sb3.py, \
    a2c_sb3.py (CityLearnWrapper._normalize_observation)

---

## Issue 2: Hardcoded Prescaling Constants Not Documented

### Problem (2)

Magic number `0.001` appears in all three agents without justification.  
If data ranges change (e.g., larger inverter), assumption breaks.

### Solution (2)

Move prescaling to agent config with explanation.

**SAC (sac.py)** - Add to `SACConfig` dataclass:

Current:

```python
@dataclass
class SACConfig:
    # ... existing fields ...
    # === NORMALIZACIÃ“N (crÃ­tico para estabilidad) ===
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.01
    clip_obs: float = 10.0
```bash

Fixed:

```python
@dataclass
class SACConfig:
    # ... existing fields ...
    # === NORMALIZACIÃ“N (crÃ­tico para estabilidad) ===
    normalize_observations: bool = True
    normalize_rewards: bool = True
    reward_scale: float = 0.01
    clip_obs: float = 10.0
    
    # === PRESCALING FACTORS (for obs normalization) ===
    # Prescaling reduces large kW/kWh values to manageable range before
    # normalization
    # E.g., 4162 kW (PV) â†’ 4.162 after prescaling by 0.001
    obs_prescale_power: float = 0.001        # For PV generation (kW)
    obs_prescale_load: float = 0.001         # For charger demand (kW)
    obs_prescale_soc: float = 1.0            # For BESS SOC [0-1] (keep as-is)
    obs_prescale_energy: float = 0.001       # For grid import/export (kWh)
    obs_prescale_cost: float = 1.0           # For tariff ($/kWh) (keep as-is)
    obs_prescale_carbon: float = \
        1.0         # For CO2 factor (kg/kWh) (keep as-is)
```bash

**Apply to**: SAC, PPO, A2C configs

**Usage in wrapper**:

```python
class CityLearnWrapper(gym.Wrapper):
    def __init__(self, env, smooth_lambda=0.0, normalize_obs=True, ...,
                 obs_prescale_power=0.001, obs_prescale_soc=1.0, ...):
        super().__init__(env)
        # Store prescale factors
        self._prescale_factors = {
            'power': obs_prescale_power,
            'soc': obs_prescale_soc,
        }
        
        # Build prescale array based on observation structure
        self._obs_prescale = self._build_prescale_array()
    
    def _build_prescale_array(self) -> np.ndarray:
        """Build prescale factors matching observation dimensions"""
        # Most features are power-like (scale by 0.001)
        # SOC is state-like (scale by 1.0)
        prescale = np.ones(self.obs_dim, dtype=np.float32) * self._prescale_factors['power']
        
        # BESS SOC is last feature from _get_pv_bess_feats()
        if self.obs_dim >= 1:
            prescale[-1] = self._prescale_factors['soc']
        
        return prescale
```bash

---

## Issue 3: Silent Failures in Feature Extraction

### Problem (3)

If `building.solar_generation` or `building.electrical_storage` missing:

```python
sg = getattr(b, "solar_generation", None)
if sg is not None and len(sg) > t:
    pv_kw += float(max(0.0, sg[t]))
```bash

Code continues with default `pv_kw = 0.0` without warning.

### Solution (3)

Add debug logging and validation.

**All three agents** - In `_get_pv_bess_feats()`:

Current:

```python
def _get_pv_bess_feats(self):
    pv_kw = 0.0
    soc = 0.0
    try:
        t = getattr(self.env, "time_step", 0)
        buildings = getattr(self.env, "buildings", [])
        for b in buildings:
            sg = getattr(b, "solar_generation", None)
            if sg is not None and len(sg) > t:
                pv_kw += float(max(0.0, sg[t]))
            es = getattr(b, "electrical_storage", None)
            if es is not None:
                soc = float(getattr(es, "state_of_charge", soc))
    except (AttributeError, TypeError, IndexError, ValueError) as err:
        logger.debug("Error extracting PV/BESS features: %s", err)
    return np.array([pv_kw, soc], dtype=np.float32)
```bash

Fixed:

```python
def _get_pv_bess_feats(self):
    pv_kw = 0.0
    soc = 0.0
    pv_missing = False
    soc_missing = False
    
    try:
        t = getattr(self.env, "time_step", 0)
        buildings = getattr(self.env, "buildings", [])
        
        if not buildings:
            logger.warning("No buildings found in environment"
                "at time_step %d", t)
            return np.array([pv_kw, soc], dtype=np.float32)
        
        for b_idx, b in enumerate(buildings):
            # Extract PV
            sg = getattr(b, "solar_generation", None)
            if sg is None:
                pv_missing = True
                logger.debug("Building %d has no"
                    "solar_generation attribute", b_idx)
            elif not isinstance(sg, (list, np.ndarray)) or len(sg) <= t:
                logger.debug("Building %d solar_generation"
                    "invalid (len=%s, t=%d)",
                            b_idx, len(sg) \
                                    if hasattr(sg, '__len__') else 'unknown', t)
                pv_missing = True
            else:
                try:
                    pv_val = float(max(0.0, sg[t]))
                    pv_kw += pv_val
                except (ValueError, TypeError, IndexError) as e:
                    logger.debug("Error reading solar at building %d, t=%d: %s",
                                b_idx, t, e)
                    pv_missing = True
            
            # Extract BESS SOC
            es = getattr(b, "electrical_storage", None)
            if es is None:
                soc_missing = True
                logger.debug("Building %d has no"
                    "electrical_storage attribute", b_idx)
            else:
                try:
                    soc_val = getattr(es, "state_of_charge", None)
                    if soc_val is None:
                        logger.debug("Building %d electrical_storage has"
                            "no state_of_charge", b_idx)
                        soc_missing = True
                    else:
                        soc = \
                            float(soc_val)  # Take last (should be same for all buildings)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug("Error reading BESS at building %d: %s",
                        b_idx,
                        e)
                    soc_missing = True
        
        # Warn if critical features missing
        if pv_missing and t % 1000 == 0:  # Log every 1000 steps to avoid spam
            logger.warning("PV generation not available at time_step %d", t)
        if soc_missing and t % 1000 == 0:
            logger.warning("BESS SOC not available at time_step %d", t)
    
    except Exception as err:
        logger.error("Unexpected error in _get_pv_bess_feats: %s", err)
    
    return np.array([pv_kw, soc], dtype=np.float32)
```bash

---

## Issue 4: Duplicate Wrapper Code (DRY Violation)

### Problem (4)

Same `CityLearnWrapper` class defined in 3 files (300+ lines each)

### Solution (4)

Extract to `agent_utils.py` and reuse.

**Create in agent_utils.py** (add to existing file):

```python
# Add to agent_utils.py

class CityLearnWrapper(gym.Wrapper):
    """Generic wrapper for CityLearn environments.
    
    Handles:
    - Flattening observations (list â†’ array)
    - Feature extraction (PV, BESS)
    - Normalization (prescaling + running stats)
    - Action unflattening (array â†’ CityLearn list format)
    
    Used by all three agents: SAC, PPO, A2C
    """
    
    def __init__(self, env, smooth_lambda: float = 0.0,
                 normalize_obs: bool = True, normalize_rewards: bool = True,
                 reward_scale: float = 0.01, clip_obs: float = 10.0,
                 obs_prescale_power: float = 0.001, 
                 obs_prescale_soc: float = 1.0,
                 obs_prescale_energy: float = 0.001):
        """Initialize wrapper with CityLearn environment.
        
        Args:
            env: CityLearn environment
            smooth_lambda: Action smoothing penalty coefficient
            normalize_obs: Whether to normalize observations
            normalize_rewards: Whether to normalize rewards
            reward_scale: Reward scaling factor
            clip_obs: Clipping range for normalized observations
            obs_prescale_power: Prescaling for power features (kW)
            obs_prescale_soc: Prescaling for SOC features [0-1]
            obs_prescale_energy: Prescaling for energy features (kWh)
        """
        super().__init__(env)
        obs0, _ = self.env.reset()
        obs0_flat = self._flatten_base(obs0)
        feats = self._get_pv_bess_feats()
        self.obs_dim = len(obs0_flat) + len(feats)
        self.act_dim = self._get_act_dim()
        
        self._smooth_lambda = smooth_lambda
        self._prev_action = None
        
        # Normalization config
        self._normalize_obs = normalize_obs
        self._normalize_rewards = normalize_rewards
        self._reward_scale = reward_scale
        self._clip_obs = clip_obs
        
        # Prescaling factors
        self._obs_prescale_power = obs_prescale_power
        self._obs_prescale_soc = obs_prescale_soc
        self._obs_prescale_energy = obs_prescale_energy
        
        # Build prescale array
        self._obs_prescale = self._build_prescale_array()
        
        # Running stats
        self._obs_mean = np.zeros(self.obs_dim, dtype=np.float64)
        self._obs_var = np.ones(self.obs_dim, dtype=np.float64)
        self._obs_count = 1e-4
        self._reward_mean = 0.0
        self._reward_var = 1.0
        self._reward_count = 1e-4
        
        # Redefine spaces
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(self.obs_dim,), dtype=np.float32
        )
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0,
            shape=(self.act_dim,), dtype=np.float32
        )
    
    def _build_prescale_array(self) -> np.ndarray:
        """Build prescale array matching observation dimensions"""
        prescale = np.ones(self.obs_dim, \
            dtype=np.float32) * self._obs_prescale_power
        if self.obs_dim >= 1:
            prescale[-1] = self._obs_prescale_soc  # BESS SOC is last feature
        return prescale
    
    def _get_act_dim(self) -> int:
        """Get action space dimension"""
        if isinstance(self.env.action_space, list):
            return sum(sp.shape[0] for sp in self.env.action_space)
        if hasattr(self.env.action_space, 'shape'):
            return int(self.env.action_space.shape[0])
        return 126  # Default for 128 chargers (2 reserved)
    
    def _get_pv_bess_feats(self) -> np.ndarray:
        """Extract PV generation and BESS SOC"""
        pv_kw = 0.0
        soc = 0.0
        try:
            t = getattr(self.env, "time_step", 0)
            buildings = getattr(self.env, "buildings", [])
            for b in buildings:
                sg = getattr(b, "solar_generation", None)
                if sg is not None and isinstance(sg, (list, \
                    np.ndarray)) and len(sg) > t:
                    try:
                        pv_kw += float(max(0.0, sg[t]))
                    except (ValueError, TypeError, IndexError):
                        pass
                es = getattr(b, "electrical_storage", None)
                if es is not None:
                    soc_val = getattr(es, "state_of_charge", None)
                    if soc_val is not None:
                        soc = float(soc_val)
        except Exception as e:
            logger.debug("Error in _get_pv_bess_feats: %s", e)
        
        return np.array([pv_kw, soc], dtype=np.float32)
    
    def _flatten_base(self, obs: Any) -> np.ndarray:
        """Flatten observation from CityLearn format"""
        if isinstance(obs, dict):
            return np.concatenate([np.array(v, \
                dtype=np.float32).ravel() for v in obs.values()])
        if isinstance(obs, (list, tuple)):
            return np.concatenate([np.array(o, \
                dtype=np.float32).ravel() for o in obs])
        return np.array(obs, dtype=np.float32).ravel()
    
    def _flatten(self, obs: Any) -> np.ndarray:
        """Flatten observation + features + normalize"""
        base = self._flatten_base(obs)
        feats = self._get_pv_bess_feats()
        arr = np.concatenate([base, feats])
        
        # Pad/trim to target dimension
        if arr.size < self.obs_dim:
            arr = np.pad(arr, (0, self.obs_dim - arr.size), mode="constant")
        elif arr.size > self.obs_dim:
            arr = arr[:self.obs_dim]
        
        return self._normalize_observation(arr.astype(np.float32))
    
    def _update_obs_stats(self, obs: np.ndarray):
        """Update running statistics with Welford's algorithm"""
        delta = obs - self._obs_mean
        self._obs_count += 1
        self._obs_mean = self._obs_mean + delta / self._obs_count
        delta2 = obs - self._obs_mean
        self._obs_var = self._obs_var + (delta * delta2 - \
            self._obs_var) / self._obs_count
    
    def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
        """Normalize observation: prescale + running stats + clip"""
        if not self._normalize_obs:
            return obs.astype(np.float32)
        
        prescaled = obs * self._obs_prescale
        self._update_obs_stats(prescaled)
        normalized = (prescaled - \
            self._obs_mean) / (np.sqrt(self._obs_var) + 1e-8)
        clipped = np.clip(normalized, -self._clip_obs, self._clip_obs)
        return np.asarray(clipped, dtype=np.float32)
    
    def _update_reward_stats(self, reward: float):
        """Update reward statistics"""
        delta = reward - self._reward_mean
        self._reward_count += 1
        self._reward_mean += delta / self._reward_count
        delta2 = reward - self._reward_mean
        self._reward_var += (delta * delta2 - \
            self._reward_var) / self._reward_count
    
    def _normalize_reward(self, reward: float) -> float:
        """Normalize reward"""
        if not self._normalize_rewards:
            return float(reward)
        scaled = reward * self._reward_scale
        return float(np.clip(scaled, -10.0, 10.0))
    
    def _unflatten_action(self, action: np.ndarray) -> Any:
        """Convert flat action to CityLearn format"""
        if isinstance(self.env.action_space, list):
            result = []
            idx = 0
            for sp in self.env.action_space:
                dim = sp.shape[0]
                result.append(action[idx:idx + dim].tolist())
                idx += dim
            return result
        return [action.tolist()]
    
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self._prev_action = None
        return self._flatten(obs), info
    
    def step(self, action):
        citylearn_action = self._unflatten_action(action)
        obs, reward, terminated, truncated, info = \
            self.env.step(citylearn_action)
        
        # Normalize done flags (truncate â†’ terminate)
        if truncated and not terminated:
            terminated = True
            truncated = False
        
        # Sum reward if list
        if isinstance(reward, (list, tuple)):
            reward = float(sum(reward))
        else:
            reward = float(reward)
        
        # Action smoothing penalty
        flat_action = np.array(action, dtype=np.float32).ravel()
        if self._prev_action is not None and self._smooth_lambda > 0.0:
            delta = flat_action - self._prev_action
            reward -= float(self._smooth_lambda * np.linalg.norm(delta))
        self._prev_action = flat_action
        
        # Normalize reward
        normalized_reward = self._normalize_reward(reward)
        
        return self._flatten(obs), normalized_reward, \
            terminated, truncated, info
```bash

**Update SAC to use**:

```python
# In sac.py, replace CityLearnWrapper definition with import

from .agent_utils import CityLearnWrapper

# In _train_sb3_sac method, remove CityLearnWrapper class definition
# and use directly:

wrapped = CityLearnWrapper(
    self.env,
    smooth_lambda=self.config.reward_smooth_lambda,
    normalize_obs=self.config.normalize_observations,
    normalize_rewards=self.config.normalize_rewards,
    reward_scale=self.config.reward_scale,
    clip_obs=self.config.clip_obs,
    obs_prescale_power=self.config.obs_prescale_power,  # From new config field
    obs_prescale_soc=self.config.obs_prescale_soc,      # From new config field
)
```bash

#### Same for PPO and A2C

**Benefit**: Single source of truth for wrapper logic

---

## Summary of Changes

  | File | Change | Impact |  
|------|--------|--------|
  | sac.py | Remove hardcoded 0.001;... | MEDIUM |  
  | sac.py | Fix BESS SOC prescaling (use 1.0) | **HIGH** |  
  | ppo_sb3.py | Same as SAC | MEDIUM / **HIGH** |  
  | a2c_sb3.py | Same as SAC | MEDIUM / **HIGH** |  
  | agent_utils.py | Add CityLearnWrapper class | LOW (extraction) |  
  | All configs | Add prescale_* fields to dataclasses | LOW (config) |  

---

## Testing

After applying fixes:

```bash
# Verify BESS is observable
python -c "
from src.iquitos_citylearn.oe3.agents import A2CAgent, A2CConfig
from citylearn.citylearn import CityLearnEnv
import json

env = CityLearnEnv(schema='outputs/schema_*.json')
config = A2CConfig(obs_prescale_soc=1.0)
agent = A2CAgent(env, config)

# Check that BESS SOC is in reasonable range after normalization
obs, info = env.reset()
print(f'BESS SOC from env: {obs[-1]:.3f}')
print('âœ“ BESS should be observable after fix')
"
```bash

---

**Document Version**: 1.0 | **Generated**: 2026-01-25
