#!/usr/bin/env python
import json

with open('data/oe2/bess/bess_results.json') as f:
    r = json.load(f)

print('CO2 METRICS FROM bess_results.json:')
print('='*60)
print(f"  Emisiones grid (baseline):      {r.get('co2_emissions_kg_year',0)/1000:.1f} ton/año")
print(f"  CO2 evitado por PV directo:     {r.get('co2_avoided_by_pv_kg_year',0)/1000:.1f} ton/año")
print(f"  CO2 evitado por BESS discharge: {r.get('co2_avoided_by_bess_kg_year',0)/1000:.1f} ton/año")
print(f"  ────────────────────────────────────────")
print(f"  TOTAL CO2 evitado:              {r.get('co2_avoided_kg_year',0)/1000:.1f} ton/año ✅")
print(f"  Reducción de emisiones:         {r.get('co2_reduction_percent',0):.1f}%")
print('='*60)
