#!/usr/bin/env python
"""
Analiza la estructura detallada de las playas de estacionamiento
- Playa 1: 16 tomas
- Playa 2: 122 tomas
Cada toma tiene su propio estado base
"""
import json
from pathlib import Path
from typing import Any
import numpy as np
from citylearn.citylearn import CityLearnEnv

print("="*100)
print("ANALISIS DETALLADO DE PLAYAS DE ESTACIONAMIENTO - MALL IQUITOS")
print("="*100)

# Cargar schema
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")
with open(schema_path) as f:
    schema = json.load(f)

building_config = schema['buildings'][0]
print(f"\n[1] CONFIGURACION SCHEMA")
print(f"Edificio: {building_config['name']}")
print(f"Propiedades: {list(building_config.keys())}")

# Cargar environment
print(f"\n[2] CREANDO ENVIRONMENT")
env = CityLearnEnv(schema=str(schema_path))
print(f"Central agent: {env.central_agent}")
print(f"Num buildings: {len(env.buildings)}")

building: Any = env.buildings[0]
print(f"\nBuilding: {building.name}")

# Analizar chargers/EV storage
print(f"\n[3] ANALISIS DE PLAYAS DE ESTACIONAMIENTO (EV Chargers)")
print(f"Tipo electric_vehicle_chargers: {type(building.electric_vehicle_chargers)}")
print(f"Num chargers: {len(building.electric_vehicle_chargers)}")

if hasattr(building, 'electric_vehicle_storage'):
    ev_storage = getattr(building, 'electric_vehicle_storage')  # type: ignore[attr-defined]
    print(f"\nTipo electric_vehicle_storage: {type(ev_storage)}")
    if isinstance(ev_storage, list):
        print(f"Num EV storage: {len(ev_storage)}")

# Analizar estructura de chargers
print(f"\n[4] ESTRUCTURA INDIVIDUAL DE CHARGERS")
print(f"Total chargers: {len(building.electric_vehicle_chargers)}")

# Agrupar por tipo si es posible
if len(building.electric_vehicle_chargers) > 0:
    for i, charger in enumerate(building.electric_vehicle_chargers[:5]):
        print(f"\nCharger {i}:")
        print(f"  Type: {type(charger)}")
        print(f"  Attributes: {[a for a in dir(charger) if not a.startswith('_')][:10]}")

# Obtener observaciones
print(f"\n[5] OBSERVACIONES - ESTRUCTURA")
obs, _ = env.reset()
if isinstance(obs, list):
    obs_flat = np.concatenate([np.array(o).flatten() for o in obs])
else:
    obs_flat = np.array(obs).flatten()

print(f"Total observation features: {len(obs_flat)}")
print(f"Observation space structure: {env.observation_space}")

# Obtener acciones
print(f"\n[6] ACCIONES - ESTRUCTURA")
if isinstance(env.action_space, list):
    print(f"Action spaces (list): {len(env.action_space)} agents")
    total_actions = sum(space.shape[0] for space in env.action_space)
    print(f"Total action dimensions: {total_actions}")
    
    for i, space in enumerate(env.action_space):
        print(f"  Agent {i}: Box{space.shape} = {space.shape[0]} dims")

print(f"\n[7] HIPOTESIS - DISTRIBUCION DE TOMAS")
print(f"Playas mencionadas:")
print(f"  - Playa 1: 16 tomas")
print(f"  - Playa 2: 122 tomas")
print(f"  - Total: 138 tomas individuales")
print(f"\nAcciones disponibles: {total_actions if 'total_actions' in locals() else 'N/A'}")
print(f"Observaciones disponibles: {len(obs_flat) if 'obs_flat' in locals() else 'N/A'}")

# Si las acciones son 130, podría ser:
# - 138 acciones (1 por toma) menos 8 para otros dispositivos = 130
# - O 16 + 122 = 138 pero se comprimen a 130 de alguna forma
print(f"\nAjuste posible: 138 tomas - 8 otros dispositivos = 130 acciones")

# Analizar si hay observaciones por toma
print(f"\n[8] FEATURES POR TOMA (ESTIMADO)")
if 'total_actions' in locals() and 'obs_flat' in locals():
    features_per_action = len(obs_flat) / total_actions
    print(f"Features por acción: {features_per_action:.2f}")
    print(f"Si son 138 tomas: {len(obs_flat) / 138:.2f} features/toma")
    print(f"Si son 130 acciones: {len(obs_flat) / 130:.2f} features/acción")

print("\n" + "="*100)
print("FIN ANALISIS")
print("="*100)
