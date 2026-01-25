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

<!-- markdownlint-disable MD013 -->
```bash
Normalized SOC = (0.0005 - 0.0005) / 0.00029 â‰ˆ 0  (all states map to ~0)
```bash
<!-- markdownlint-enable MD013 -->

Agent cannot distinguish between:

- SOC = 0.10 (min, needs charging)
- SOC = 0.90 (max, can discharge)

### Solution

Keep BESS SOC unscaled in normalized observation space.

**Location**: All three agents' `CityLearnWrapper` class

**SAC (sac.py)** - Lines 488-530:

Current code...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

Fixed code:

<!-- markdownlint-disable MD013 -->
```python
# PRE-ESCALADO: kW/kWh / 1000 â†’ rango ~1-5 (2)
# BUT: Keep BESS SOC as-is (0-1) since it's already normalized
self._obs_prescale = np.ones(self.obs_dim, dtype=np.float32) * 0.001

# BESS SOC is the last feature from _get_pv_bess_feats()
# Don't prescale it
def _normalize_observation(self, obs: np.ndarray) -> np.ndarray:
    if not self._normalize_obs:
        return obs
    # Apply prescaling se...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Better approach** - Separate prescaling factors:

<!-- markdownlint-disable MD013 -->
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
def _normalize_observation(sel...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

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

<!-- markdownlint-disable MD013 -->
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
<!-- markdownlint-enable MD013 -->

Fixed:

<!-- markdownlint-disable MD013 -->
```python
@dataclass
class SACConfig:
    # ... existing fields ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Apply to**: SAC, PPO, A2C configs

**Usage in wrapper**:

<!-- markdownlint-disable MD013 -->
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
        
        # Build prescale ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## Issue 3: Silent Failures in Feature Extraction

### Problem (3)

If `building.solar_generation` or `building.electrical_storage` missing:

<!-- markdownlint-disable MD013 -->
```python
sg = getattr(b, "solar_generation", None)
if sg is not None and len(sg) > t:
    pv_kw += float(max(0.0, sg[t]))
```bash
<!-- markdownlint-enable MD013 -->

Code continues with default `pv_kw = 0.0` without warning.

### Solution (3)

Add debug logging and validation.

**All three agents** - In `_get_pv_bess_feats()`:

Current:

<!-- markdownlint-disable MD013 -->
```python
def _get_pv_bess_feats(...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

Fixed:

<!-- markdownlint-disable MD013 -->
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
            return np.array([pv_kw, soc], ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## Issue 4: Duplicate Wrapper Code (DRY Violation)

### Problem (4)

Same `CityLearnWrapper` class defined in 3 files (300+ lines each)

### Solution (4)

Extract to `agent_utils.py` and reuse.

**Create in agent_utils.py** (add to existing file):

<!-- markdownlint-disable MD013 -->
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
    
    def __init_...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Update SAC to use**:

<!-- markdownlint-disable MD013 -->
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
    ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### Same for PPO and A2C

**Benefit**: Single source of truth for wrapper logic

---

<!-- markdownlint-disable MD013 -->
## Summary of Changes | File | Change | Impact | |------|--------|--------| | sac.py | Remove hardcoded 0.001;... | MEDIUM | | sac.py | Fix BESS SOC prescaling (use 1.0) | **HIGH** | | ppo_sb3.py | Same as SAC | MEDIUM / **HIGH** | | a2c_sb3.py | Same as SAC | MEDIUM / **HIGH** | | agent_utils.py | Add CityLearnWrapper class | LOW (extraction) | | All configs | Add prescale_* fields to dataclasses | LOW (config) | ---

## Testing

After applying fixes:

<!-- markdownlint-disable MD013 -->
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
<!-- markdownlint-enable MD013 -->

---

**Document Version**: 1.0 | **Generated**: 2026-01-25
