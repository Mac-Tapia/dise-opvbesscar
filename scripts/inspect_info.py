#!/usr/bin/env python
"""Inspect what's in the info dict."""
import numpy as np
from citylearn.citylearn import CityLearnEnv

schema_path = 'data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'
env = CityLearnEnv(str(schema_path))
obs, info = env.reset()

print(f"Reset info keys: {list(info.keys())}")
print(f"Reset info values: {info}")

# Take 1 step
action = [np.array([1.0, 1.0, 0.0])]
obs, reward, done, truncated, info = env.step(action)

print(f"\nObs type: {type(obs)}")
print(f"Obs length: {len(obs)}")
print(f"Obs[0] type: {type(obs[0]) if len(obs) > 0 else 'N/A'}")
print(f"Obs[0] length: {len(obs[0]) if len(obs) > 0 else 0}")
print(f"Obs[0][:10]: {obs[0][:10] if len(obs) > 0 and hasattr(obs[0], '__getitem__') else 'N/A'}")

print(f"\nStep 1 info keys: {list(info.keys())}")
print(f"Step 1 info: {info}")
print(f"Step 1 reward: {reward}")
print(f"Step 1 done: {done}")
print(f"Step 1 truncated: {truncated}")
