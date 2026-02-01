#!/usr/bin/env python
"""Diagnose CityLearn action format requirements."""
from citylearn.citylearn import CityLearnEnv
import json

schema_path = 'data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'

# Load schema
with open(schema_path) as f:
    schema = json.load(f)
    buildings = schema.get('buildings', schema)  # Schema might be list or dict
    if isinstance(buildings, dict):
        buildings = [buildings]
    elif not isinstance(buildings, list):
        buildings = []
    print(f"✓ Número de buildings: {len(buildings)}")

# Create environment
env = CityLearnEnv(schema_path)
print(f"\n✓ Environment created")
print(f"✓ Action space: {env.action_space}")
print(f"✓ Action shape: {env.action_space.shape}")

# Test action with correct format
try:
    import numpy as np
    action = np.array([1.0] * 129)  # 129 values: 1 BESS + 128 chargers
    print(f"✓ Using action format: [1.0]*129 (shape={action.shape})")
except Exception as e:
    print(f"✗ Failed: {e}")

# Reset environment
obs, info = env.reset()
if isinstance(obs, list):
    print(f"\n✓ Observation is list with {len(obs)} elements")
    print(f"  - Each element shape: {obs[0].shape if hasattr(obs[0], 'shape') else len(obs[0])}")
else:
    print(f"\n✓ Observation shape: {obs.shape}")

# Test action formats
print("\n--- TESTING ACTION FORMATS ---")

# Test 1: List of arrays (one per agent/building)
try:
    import numpy as np
    action_1 = [np.array([1.0] * 129)]  # 1 building
    print(f"✓ Test 1: [np.array([1.0]*129)] - OK format")
except Exception as e:
    print(f"✗ Test 1 failed: {e}")

# Test 2: Nested list
try:
    action_2 = [[1.0] * 129]  # 1 building
    print(f"✓ Test 2: [[1.0]*129] - OK format")
except Exception as e:
    print(f"✗ Test 2 failed: {e}")

# Test 3: Simple list
try:
    action_3 = [1.0] * 129
    print(f"✓ Test 3: [1.0]*129 - OK format")
except Exception as e:
    print(f"✗ Test 3 failed: {e}")

# Test 4: Multiple agents (if n_agents > 1)
if env.n_agents > 1:
    try:
        action_4 = [[1.0] * 129 for _ in range(env.n_agents)]
        print(f"✓ Test 4: [[1.0]*129 for _ in range(n_agents)] - OK format")
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")

print(f"\n--- EXECUTING TEST STEP ---")
# Execute a test step with the correct format
try:
    import numpy as np
    # Action space is (129,) - 1 BESS + 128 chargers
    action = np.array([1.0] * 129)
    print(f"Sending action: shape={action.shape}")

    obs, reward, done, info = env.step(action)
    print(f"✓ Step successful!")
    print(f"✓ Reward type: {type(reward)}")
except Exception as e:
    import traceback
    traceback.print_exc()
