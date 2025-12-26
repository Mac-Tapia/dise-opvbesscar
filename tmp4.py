import json
from pathlib import Path

out_dir=Path('outputs/oe3/simulations')
res_base=json.loads((out_dir/'result_Uncontrolled.json').read_text())
res_control=json.loads((out_dir/'result_A2C.json').read_text())
print(res_base['carbon_kg'], res_control['carbon_kg'])

