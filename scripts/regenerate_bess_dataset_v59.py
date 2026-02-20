"""
Script para regenerar bess_ano_2024.csv con protección horaria BESS v5.9
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dimensionamiento.oe2.disenobess.bess import run_bess_sizing

print("\n" + "="*80)
print("REGENERANDO: bess_ano_2024.csv con PROTECCION HORARIA BESS v5.9")
print("="*80)

out_dir = Path('data/oe2/bess')
pv_path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
ev_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
mall_path = Path('data/oe2/mall/mall_demand_ano_2024.csv')

result = run_bess_sizing(
    out_dir=out_dir,
    pv_profile_path=pv_path,
    ev_profile_path=ev_path,
    mall_demand_path=mall_path,
    year=2024,
    generate_plots=False  # Sin ploteos para ir rápido
)

print("\n" + "="*80)
print("✅ Dataset ORIGINAL regenerado: data/oe2/bess/bess_ano_2024.csv")
print("="*80)
print("")
