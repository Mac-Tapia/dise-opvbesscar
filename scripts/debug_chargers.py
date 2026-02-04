#!/usr/bin/env python3
"""Debug script to check ev_chargers artifacts."""
from pathlib import Path
import json
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.dataset_builder import _load_oe2_artifacts

cfg = load_config(Path(__file__).parent.parent / "configs" / "default.yaml")
rp = load_paths(cfg)

print(f"Interim dir: {rp.interim_dir}")
print(f"Checking ev_chargers...")

artifacts = _load_oe2_artifacts(rp.interim_dir)

if "ev_chargers" in artifacts:
    ev_chargers = artifacts["ev_chargers"]
    print(f"✅ ev_chargers found: {len(ev_chargers)} entries")
    if isinstance(ev_chargers, list):
        print(f"   Type: list")
        print(f"   Length: {len(ev_chargers)}")
        if ev_chargers:
            print(f"   First 3 entries: {ev_chargers[:3]}")
            print(f"   Last 3 entries: {ev_chargers[-3:]}")
    elif isinstance(ev_chargers, dict):
        print(f"   Type: dict")
        print(f"   Length: {len(ev_chargers)}")
        print(f"   Keys: {list(ev_chargers.keys())[:5]}")
else:
    print(f"❌ ev_chargers NOT found in artifacts")
    print(f"   Available artifacts: {list(artifacts.keys())}")

# Check the actual file
chargers_file = rp.interim_dir / "oe2" / "chargers" / "individual_chargers.json"
if chargers_file.exists():
    with open(chargers_file, 'r') as f:
        data = json.load(f)
    print(f"\n✅ individual_chargers.json: {len(data)} entries")
    if isinstance(data, list):
        print(f"   Type: list")
        print(f"   First: {data[0] if data else 'empty'}")
    elif isinstance(data, dict):
        print(f"   Type: dict")
        print(f"   Keys count: {len(data)}")
else:
    print(f"❌ individual_chargers.json not found at {chargers_file}")
