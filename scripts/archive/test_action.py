#!/usr/bin/env python
"""Test correct action format for CityLearn."""
from citylearn.citylearn import CityLearnEnv
import numpy as np

schema_path = 'data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'

env = CityLearnEnv(schema_path)
print(f"Action space: {env.action_space}")
print(f"Action space type: {type(env.action_space)}")
if isinstance(env.action_space, list):
    print(f"First action space shape: {env.action_space[0].shape}")

obs, info = env.reset()

# Test: Send actions as list with one array per building/agent
action = [np.array([1.0, 1.0, 1.0])]  # List containing 1 array
print(f"\nSending action: {action}")

result = env.step(action)
print(f"✓ Step successful!")
print(f"✓ Result length: {len(result)}")
print(f"✓ Result types: {[type(r) for r in result]}")

if len(result) == 5:
    obs, reward, done, truncated, info = result
    print(f"✓ obs type: {type(obs)}")
    print(f"✓ reward: {reward}")
    print(f"✓ done: {done}")
    print(f"✓ truncated: {truncated}")
    print(f"✓ info: {info}")
else:
    print(f"Unknown result format with {len(result)} values")

print("\n✓✓✓ CORRECT ACTION FORMAT: [np.array([1.0, 1.0, 1.0])] ✓✓✓")
