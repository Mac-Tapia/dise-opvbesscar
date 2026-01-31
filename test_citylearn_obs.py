"""Diagnosticar estructura de observaciones de CityLearn."""
from citylearn.citylearn import CityLearnEnv
import numpy as np

env = CityLearnEnv('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json')
obs, info = env.reset()

print("="*80)
print("ESTRUCTURA DE OBSERVACIONES CITYLEARN")
print("="*80)

print(f"\nObservation type: {type(obs)}")
print(f"Observation length: {len(obs) if isinstance(obs, (list, tuple)) else 'N/A'}")

if isinstance(obs, list) and len(obs) > 0:
    print(f"\nFirst building observation:")
    print(f"  Type: {type(obs[0])}")
    print(f"  Shape: {obs[0].shape if hasattr(obs[0], 'shape') else len(obs[0])}")
    print(f"  First 10 values: {obs[0][:10] if isinstance(obs[0], np.ndarray) else obs[0][:10]}")

# Acceder a buildings directamente
print(f"\nEnvironment buildings:")
print(f"  Count: {len(env.buildings)}")
if len(env.buildings) > 0:
    b = env.buildings[0]
    print(f"  Building name: {b.name}")

    # Intentar acceder a chargers
    if hasattr(b, 'electric_vehicle_chargers'):
        chargers = b.electric_vehicle_chargers
        print(f"  Chargers count: {len(chargers)}")
        if len(chargers) > 0:
            ch = chargers[0]
            print(f"  First charger type: {type(ch)}")
            print(f"  First charger attributes: {dir(ch)[:10]}")

            # Intentar acceder a power
            if hasattr(ch, 'charging_demand'):
                print(f"  First charger charging_demand: {ch.charging_demand}")
            if hasattr(ch, 'nominal_power'):
                print(f"  First charger nominal_power: {ch.nominal_power}")

    # Solar generation
    if hasattr(b, 'solar_generation'):
        print(f"  Solar generation available: {len(b.solar_generation)} timesteps")
        print(f"  Current solar: {b.solar_generation[-1] if len(b.solar_generation) > 0 else 'N/A'}")

print("\n" + "="*80)
