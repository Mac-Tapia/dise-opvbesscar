#!/usr/bin/env python
"""Verificar si solar_generation está presente en CityLearn env"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))

try:
    from citylearn.citylearn import CityLearnEnv
    import json
    
    print("="*80)
    print("VERIFICAR SOLAR EN CITYLEARN ENV")
    print("="*80)
    print()
    
    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")
    
    if not schema_path.exists():
        print(f"❌ Schema no encontrado: {schema_path}")
        sys.exit(1)
    
    # Crear environment
    print(f"Cargando schema: {schema_path}")
    env = CityLearnEnv(
        schema_path=str(schema_path),
        active_observations=None,
        central_agent=True
    )
    
    print(f"✅ Environment creado")
    print()
    
    # Reset
    obs = env.reset()
    print(f"Observation shape: {[o.shape if hasattr(o, 'shape') else len(o) for o in obs]}")
    print()
    
    # Verificar buildings
    for i, building in enumerate(env.buildings):
        print(f"Building {i}: {building.name}")
        print(f"  Has solar_generation: {hasattr(building, 'solar_generation')}")
        if hasattr(building, 'solar_generation'):
            print(f"  solar_generation value: {building.solar_generation}")
            print(f"  solar_generation type: {type(building.solar_generation)}")
        print()
    
    # Step simulado
    print("Simulando 24 pasos (1 día)...")
    solar_values = []
    for step in range(24):
        action = [[0.0] * len(env.action_space)]  # No action
        obs, reward, done, info = env.step(action)
        
        for i, b in enumerate(env.buildings):
            if hasattr(b, 'solar_generation'):
                val = b.solar_generation[-1] if b.solar_generation else 0
                solar_values.append(float(val))
                if step < 5 or step > 20:
                    print(f"  Step {step}: {b.name} solar_generation = {val:.2f}")
    
    print()
    print(f"Solar values recolectados: {len(solar_values)}")
    print(f"Sum: {sum(solar_values):.1f}")
    print(f"Non-zero count: {len([v for v in solar_values if v != 0])}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
