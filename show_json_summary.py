#!/usr/bin/env python3
import json
from pathlib import Path

# Leer result_sac.json
result_path = Path('outputs/sac_training/result_sac.json')
with open(result_path) as f:
    result = json.load(f)

print("="*80)
print("RESUMEN result_sac.json")
print("="*80)

# Claves principales
print(f"\n✓ Agent: {result.get('agent')}")
print(f"✓ Version: {result.get('version')}")
print(f"✓ Timesteps ejecutados: {result.get('total_timesteps'):,}")
print(f"✓ Episodios completados: {result.get('episodes_completed')}")
print(f"✓ Modelo guardado: {result.get('model_path')}")

# Episodes data
if 'episodes' in result:
    episodes = result['episodes']
    print(f"\n✓ Episodios registrados: {len(episodes)}")
    
    # Últimos 3 episodios
    print(f"\n✓ Últimos 3 episodios:")
    for ep in episodes[-3:]:
        print(f"\n  Episodio {ep.get('episode_num')}:")
        print(f"    - Total Reward: {ep.get('total_reward'):.6f}")
        print(f"    - Total CO2 (grid): {ep.get('total_co2_grid_kg'):.0f} kg")
        print(f"    - Grid Import: {ep.get('mean_grid_import_kwh'):.1f} kW avg")
        print(f"    - Solar Utilization: {ep.get('solar_utilization_percent'):.1f}%")
        print(f"    - BESS Cycles: {ep.get('bess_cycles', 0)}")

print("\n" + "="*80)
