#!/usr/bin/env python3
"""Check result files content."""
import json
from pathlib import Path

results_dir = Path("outputs/oe3/simulations")
for result_file in sorted(results_dir.glob("result_*.json")):
    try:
        data = json.loads(result_file.read_text())
        steps = data.get("total_steps", "?")
        print(f"{result_file.name}: {steps} steps")
    except Exception as e:
        print(f"{result_file.name}: ERROR - {e}")
