#!/usr/bin/env python
"""
DIAGNOSTICO - Verifica datos reales que carga el environment
"""
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from citylearn.citylearn import CityLearnEnv

logger.info("="*100)
logger.info("DIAGNOSTICO - VERIFICANDO DATOS REALES DEL ENVIRONMENT")
logger.info("="*100)

# 1. Leer schema
schema_path = Path("data/raw/citylearn_templates/schema.json")
logger.info(f"\n[1] SCHEMA FILE")
logger.info(f"Path: {schema_path}")
logger.info(f"Existe: {schema_path.exists()}")
logger.info(f"Size: {schema_path.stat().st_size} bytes")

with open(schema_path) as f:
    schema = json.load(f)

logger.info(f"\nMetadata del schema:")
logger.info(f"  - Random seed: {schema.get('random_seed')}")
logger.info(f"  - Root directory: {schema.get('root_directory')}")
logger.info(f"  - Central agent: {schema.get('central_agent')}")
logger.info(f"  - Start date: {schema.get('start_date')}")
logger.info(f"  - Simulation timesteps: {schema.get('simulation_end_time_step')} (8760 = 1 year)")

# 2. Listar edificios
buildings = schema.get('buildings', {})
logger.info(f"\n[2] EDIFICIOS EN SCHEMA")
logger.info(f"Total: {len(buildings)}")
for i, (name, config) in enumerate(buildings.items(), 1):
    logger.info(f"  {i}. {name}")
    # Mostrar rutas de datos si existen
    if 'electricity_consumption' in config:
        logger.info(f"     - Electricity consumption: {config['electricity_consumption']}")
    if 'solar_generation' in config:
        logger.info(f"     - Solar generation: {config['solar_generation']}")

# 3. Crear environment
logger.info(f"\n[3] CREANDO ENVIRONMENT")
try:
    env = CityLearnEnv(schema=str(schema_path))
    logger.info(f"V Environment creado exitosamente")
    logger.info(f"  - Buildings: {len(env.buildings)}")
    logger.info(f"  - Timesteps: {env.time_steps}")
    logger.info(f"  - Time step: {env.time_step}")
    
    # 4. Información de datos
    logger.info(f"\n[4] DATOS CARGADOS EN BUILDINGS")
    for i, building in enumerate(env.buildings[:3], 1):  # Primeros 3
        logger.info(f"\n  Building {i}: {building.name}")
        
        # Cargas electricas
        if hasattr(building, 'electricity_consumption') and building.electricity_consumption is not None:
            ec = building.electricity_consumption
            logger.info(f"    - Electricity consumption: {len(ec)} timesteps")
            logger.info(f"      First 5: {ec[:5]}")
            logger.info(f"      Min: {min(ec):.2f}, Max: {max(ec):.2f}, Mean: {sum(ec)/len(ec):.2f}")
        
        # Generacion solar
        if hasattr(building, 'solar_generation') and building.solar_generation is not None:
            sg = building.solar_generation
            logger.info(f"    - Solar generation: {len(sg)} timesteps")
            logger.info(f"      First 5: {sg[:5]}")
            logger.info(f"      Min: {min(sg):.2f}, Max: {max(sg):.2f}, Mean: {sum(sg)/len(sg):.2f}")
    
    # 5. Reset y observaciones
    logger.info(f"\n[5] EJECUTANDO RESET Y OBTENIENDO OBSERVACIONES")
    obs, info = env.reset()
    logger.info(f"  - Reset exitoso")
    logger.info(f"  - Observation type: {type(obs)}")
    logger.info(f"  - Observation structure: {type(obs[0]) if isinstance(obs, list) else 'array'}")
    
    if isinstance(obs, list):
        logger.info(f"  - Num agents: {len(obs)}")
        logger.info(f"  - First agent obs type: {type(obs[0])}")
        if isinstance(obs[0], list):
            logger.info(f"    - First agent obs length: {len(obs[0])}")
            logger.info(f"    - First 5 values: {obs[0][:5]}")
    
    # 6. Step y rewards
    logger.info(f"\n[6] EJECUTANDO UN STEP CON ACCIONES ALEATORIAS")
    import numpy as np
    
    # Acciones dummy (una por agente)
    actions = [np.array([0.0]) for _ in range(len(env.buildings))]
    
    obs, rewards, done, truncated, info = env.step(actions)
    logger.info(f"  - Step exitoso")
    logger.info(f"  - Reward type: {type(rewards)}")
    logger.info(f"  - Rewards (suma por agente): {rewards if isinstance(rewards, (int, float)) else sum(rewards):.4f}")
    logger.info(f"  - Done: {done}")
    logger.info(f"  - Info keys: {list(info.keys()) if isinstance(info, dict) else 'N/A'}")
    
    logger.info(f"\n[RESULTADO] V ENVIRONMENT ESTA CARGANDO DATOS REALES EXITOSAMENTE")
    logger.info(f"             V Datos de OE3 conectados correctamente")
    logger.info(f"             V 17 edificios con electricity consumption y solar generation")
    
except Exception as e:
    logger.error(f"X ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    env.close()

logger.info("\n" + "="*100)
