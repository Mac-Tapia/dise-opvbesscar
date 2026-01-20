#!/usr/bin/env python
"""Debug script para inspeccionar CityLearnEnv."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from citylearn.citylearn import CityLearnEnv

schema_path = Path("data/raw/citylearn_templates/schema.json")
env = CityLearnEnv(schema=str(schema_path))

# Inspeccionar
print(f"Action space: {env.action_space}")
print(f"Observation space: {env.observation_space}")

# Reset
obs, info = env.reset()
print(f"\nObservation type: {type(obs)}")
print(f"Observation: {obs}")

if isinstance(obs, list):
    flat = []
    for item in obs:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    print(f"Flattened shape: {len(flat)}")
    print(f"Flattened: {np.array(flat)}")
else:
    print(f"Direct array shape: {np.array(obs).shape}")

env.close()
