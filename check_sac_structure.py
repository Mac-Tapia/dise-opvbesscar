#!/usr/bin/env python3
import json

with open('outputs/sac_training/result_sac.json') as f:
    data = json.load(f)

print("SAC JSON Structure:")
print(f"  Top-level keys ({len(data.keys())}): {list(data.keys())[:20]}")
print()

# Check for episode data
for key in ['episode_levels', 'episodes', 'training_evolution']:
    if key in data:
        val = data[key]
        if isinstance(val, list):
            print(f"  {key}: list of {len(val)} items")
            if val:
                print(f"    First item keys: {list(val[0].keys())[:10]}")
        elif isinstance(val, dict):
            print(f"  {key}: dict with {len(val)} keys")
            print(f"    Keys: {list(val.keys())[:10]}")
