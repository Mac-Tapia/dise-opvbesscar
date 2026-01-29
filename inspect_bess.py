#!/usr/bin/env python
import json
from pathlib import Path

schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
with open(schema_path) as f:
    schema = json.load(f)

b = schema["buildings"]["Mall_Iquitos"]
print("BESS type:", type(b['electrical_storage']))
print("BESS keys:", list(b['electrical_storage'].keys()) if isinstance(b['electrical_storage'], dict) else f"list len {len(b['electrical_storage'])}")
if isinstance(b['electrical_storage'], dict):
    print("BESS content:", json.dumps(b['electrical_storage'], indent=2)[:800])
