#!/usr/bin/env python3
import json

with open('data/interim/oe2/chargers/individual_chargers.json') as f:
    d = json.load(f)

print(f'Total items: {len(d)}')
print(f'Total sockets: {sum(x.get("sockets", 1) for x in d)}')

# Check BESS
with open('data/interim/oe2/bess/bess_config.json') as f:
    bess = json.load(f)
    print(f'BESS capacity: {bess.get("capacity_kwh")} kWh')
    print(f'BESS power: {bess.get("power_kw")} kW')
