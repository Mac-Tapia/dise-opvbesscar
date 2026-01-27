#!/usr/bin/env python
"""Check config agents"""
import yaml

with open('configs/default.yaml') as f:
    config = yaml.safe_load(f)

agents_list = config.get('oe3', {}).get('agents', [])
print(f"Agents list: {agents_list}")
print(f"Type: {type(agents_list)}")

print("\nAgents en config.oe3:")
oe3 = config.get('oe3', {})
for key in oe3.keys():
    print(f"  - {key}")
    if key.lower() in ['sac', 'ppo', 'a2c']:
        print(f"    Config: {type(oe3[key])}")
