#!/usr/bin/env python3
"""Simple wrapper to run validation with UTF-8 output."""
import sys
import io
import os

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['PYTHONIOENCODING'] = 'utf-8'

# Now import and run
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Manually run the validation checks instead of using the fancy script
from iquitos_citylearn.config import load_config, load_paths
import json
import pandas as pd
import numpy as np

cfg = load_config(Path(__file__).parent.parent / "configs" / "default.yaml")
rp = load_paths(cfg)

print("\n" + "="*80)
print("PHASE 5: SCHEMA.JSON CHARGERS VALIDATION")
print("="*80)

schema_path = rp.processed_dir / "citylearn" / "iquitos_ev_mall" / "schema.json"
if schema_path.exists():
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    buildings = schema.get("buildings", {})
    for bname, building in buildings.items():
        chargers = building.get("chargers", {})
        print(f"\nBuilding: {bname}")
        print(f"  Total chargers in schema: {len(chargers)}/128")
        if chargers:
            charger_names = list(chargers.keys())
            print(f"  First 3: {charger_names[:3]}")
            print(f"  Last 3: {charger_names[-3:]}")

            # Check if all have charger_simulation references
            with_sim = 0
            for cname, cdef in chargers.items():
                if "charger_simulation" in cdef and cdef["charger_simulation"]:
                    with_sim += 1
            print(f"  With charger_simulation refs: {with_sim}/128")

            if len(chargers) == 128 and with_sim == 128:
                print("  ✅ SCHEMA CHARGERS: PASSED")
            else:
                print(f"  ❌ SCHEMA CHARGERS: FAILED (expected 128/128 with refs, got {len(chargers)}/{with_sim})")
else:
    print(f"❌ schema.json not found at {schema_path}")

print("\n" + "="*80)
print("PHASE 7: PPO ACTION SPACE VALIDATION")
print("="*80)

# Check if PPO would have correct action dimensions
print(f"\nExpected PPO Action Space:")
print(f"  BESS actions: 1 dimension")
print(f"  Charger actions: 128 dimensions (1 per charger)")
print(f"  Total: 129 dimensions")

if len(chargers) == 128:
    print(f"\n✅ PPO ACTION SPACE: PASSED")
    print(f"  PPO will have correct 129-dimensional action space")
else:
    print(f"\n❌ PPO ACTION SPACE: FAILED")
    print(f"  PPO would only have {len(chargers)+1} dimensions instead of 129")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Schema chargers: {len(chargers)}/128")
print(f"PPO ready: {'✅ YES' if len(chargers) == 128 else '❌ NO'}")
print()
