import json
from pathlib import Path
js=json.loads(Path('outputs/oe3/simulations/simulation_summary.json').read_text())
print('grid', js['grid_only_result']['carbon_kg'])
print('uncontrolled', js['pv_bess_uncontrolled']['carbon_kg'])
print('best_agent', js['best_agent'], js['best_result']['carbon_kg'])

