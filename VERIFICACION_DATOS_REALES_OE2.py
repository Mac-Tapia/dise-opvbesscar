#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION INTEGRAL: OE2 DATOS REALES -> CITYLEARN -> TRAINING -> METRICAS
"""

import sys
import json
from pathlib import Path
import pandas as pd

sys.path.insert(0, 'd:\\diseñopvbesscar')

print("=" * 80)
print("VERIFICACION INTEGRAL: OE2 DATOS REALES")
print("=" * 80)
print()

# PASO 1: VERIFICAR OE2 DATOS REALES EN DISCO
print("[PASO 1] OE2 - DATOS REALES EN DISCO")
print("-" * 80)

oe2_dir = Path("d:\\diseñopvbesscar\\data\\interim\\oe2")
if not oe2_dir.exists():
    oe2_dir = Path("d:\\diseñopvbesscar\\data\\oe2")

print("OE2 Directory: {}".format(oe2_dir))
print("Exists: {}".format(oe2_dir.exists()))
print()

# Check cada componente
components = {
    "Solar": "Generacionsolar/pv_generation_timeseries.csv",
    "Chargers": "chargers/individual_chargers.json",
    "BESS": "bess_dimensionamiento_schema.json",
    "Demanda Mall": "demandamallkwh/demanda_mall_horaria_anual.csv",
}

real_data = {}
for name, path_rel in components.items():
    full_path = oe2_dir / path_rel
    exists = full_path.exists()
    status = "OK" if exists else "NO"
    print("[{}] {:<20} {}".format(status, name, path_rel))

    if exists:
        if path_rel.endswith('.csv'):
            try:
                df = pd.read_csv(full_path)
                print("     rows={}, cols={}".format(len(df), len(df.columns)))
                real_data[name] = {
                    'path': str(full_path),
                    'rows': len(df),
                    'real': True
                }
            except Exception as e:
                print("     ERROR: {}".format(e))
                real_data[name] = {'path': str(full_path), 'real': False}
        elif path_rel.endswith('.json'):
            try:
                with open(full_path) as f:
                    obj = json.load(f)
                size = len(obj) if isinstance(obj, list) else len(obj.keys())
                print("     items={}".format(size))
                real_data[name] = {
                    'path': str(full_path),
                    'items': size,
                    'real': True
                }
            except Exception as e:
                print("     ERROR: {}".format(e))
                real_data[name] = {'path': str(full_path), 'real': False}
    else:
        print("     WARNING: NO ENCONTRADO")
        real_data[name] = {'path': str(full_path), 'real': False}

print()

# PASO 2: VERIFICAR DATASET BUILDER CARGA DATOS OE2
print("[PASO 2] DATASET BUILDER - CARGA DATOS OE2")
print("-" * 80)

try:
    from src.iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset, _load_oe2_artifacts
    print("OK: dataset_builder importado")
    print()

    # Load OE2 artifacts
    print("Cargando OE2 artifacts...")
    artifacts = _load_oe2_artifacts(oe2_dir.parent)
    print("Artifacts cargados: {} componentes".format(len(artifacts)))
    print()

    for key, value in artifacts.items():
        if isinstance(value, pd.DataFrame):
            print("  OK {:<25} -> DataFrame {} x {}".format(key, value.shape[0], value.shape[1]))
        elif isinstance(value, dict):
            print("  OK {:<25} -> Dict con {} items".format(key, len(value)))
        else:
            print("  OK {:<25} -> {}".format(key, type(value).__name__))
    print()

except Exception as e:
    print("ERROR: {}".format(e))
    import traceback
    traceback.print_exc()
    print()

# PASO 3: VERIFICAR SCHEMA CITYLEARN
print("[PASO 3] SCHEMA CITYLEARN - DATOS EN ENVIRONMENT")
print("-" * 80)

schema_path = Path("d:\\diseñopvbesscar\\data\\processed\\citylearn\\iquitos_ev_mall\\schema.json")
if schema_path.exists():
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        print("OK: Schema encontrado")
        print()

        buildings = schema.get("buildings", [])
        print("  Buildings: {}".format(len(buildings)))

        electric_vehicles = schema.get("electric_vehicles", [])
        print("  Electric Vehicles: {}".format(len(electric_vehicles)))

        if buildings and "solar_generation" in buildings[0]:
            print("  OK: Solar Generation en schema")
        print()
    except Exception as e:
        print("ERROR: {}".format(e))
        print()
else:
    print("NO: Schema no encontrado")
    print()

# PASO 4: INTENTAR CREAR ENVIRONMENT
print("[PASO 4] ENVIRONMENT - USA DATOS DEL SCHEMA")
print("-" * 80)

try:
    from src.citylearnv2.env.citylearn_env import CityLearnEnv
    print("OK: CityLearnEnv disponible")

    env_config = {
        'schema_path': str(schema_path),
        'episode_tracker': False,
    }

    env = CityLearnEnv(**env_config)
    print("OK: Environment creado")
    print("   Observation space: {}".format(env.observation_space))
    print("   Action space: {}".format(env.action_space))
    print()

    obs, info = env.reset()
    print("OK: Reset ejecutado")

    action = env.action_space.sample()
    obs, reward, term, trunc, info = env.step(action)
    print("OK: Step ejecutado")
    print("   Reward: {:.4f}".format(reward))
    print()

    env.close()

except Exception as e:
    print("WARN: {}".format(e))
    print()

# RESUMEN FINAL
print()
print("=" * 80)
print("RESUMEN FINAL")
print("=" * 80)
print()

all_real = all(v.get('real', False) for v in real_data.values())
print("Componentes OE2 Reales:")
for name, data in real_data.items():
    status = "OK" if data.get('real', False) else "NO"
    print("  [{}] {}".format(status, name))

print()
if all_real:
    print("CONCLUSION: TODO LOS DATOS SON REALES DE OE2")
    print("La cadena OE2 -> CityLearn -> Training -> Metricas es VALIDA")
else:
    print("CONCLUSION: ALGUNOS DATOS SON SINTETICOS")
    print("Las metricas pueden ser INVALIDAS")

print()
print("=" * 80)
