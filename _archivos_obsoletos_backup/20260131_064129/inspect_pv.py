#!/usr/bin/env python
import json
from pathlib import Path

schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
with open(schema_path) as f:
    schema = json.load(f)

b = schema["buildings"]["Mall_Iquitos"]
print("PV type:", type(b['pv']))
print("PV content:", json.dumps(b['pv'], indent=2)[:500])
