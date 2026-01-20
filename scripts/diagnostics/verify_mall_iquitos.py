#!/usr/bin/env python
"""
VERIFICACION MALL IQUITOS - 1 Edificio con 2 playas de estacionamiento
"""
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from citylearn.citylearn import CityLearnEnv

logger.info("="*100)
logger.info("MALL IQUITOS - 1 EDIFICIO CON 2 PLAYAS DE ESTACIONAMIENTO")
logger.info("="*100)

# Schema correcto
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")

if not schema_path.exists():
    logger.error(f"Schema no encontrado: {schema_path}")
    sys.exit(1)

# Leer schema
with open(schema_path) as f:
    schema = json.load(f)

logger.info(f"\n[1] SCHEMA INFO")
logger.info(f"  - Path: {schema_path}")
logger.info(f"  - Start date: {schema.get('start_date')}")
logger.info(f"  - Timesteps: {schema.get('simulation_end_time_step')} (1 year)")
logger.info(f"  - Central agent: {schema.get('central_agent')}")

# Building
mall = schema['buildings']['Mall_Iquitos']
logger.info(f"\n[2] MALL_IQUITOS ARCHITECTURE")
logger.info(f"  - Surface area: {mall.get('surface_area', 'N/A')} sqm")
logger.info(f"  - Volume: {mall.get('volume', 'N/A')} m3")

logger.info(f"\n  DEVICES:")
devices = mall.get('devices', {})
for device_name, device_config in sorted(devices.items()):
    logger.info(f"    - {device_name}: {device_config}")

# Create environment
logger.info(f"\n[3] CREATING ENVIRONMENT")
try:
    env = CityLearnEnv(schema=str(schema_path))
    logger.info(f"  V Environment created successfully")
    logger.info(f"  - Num buildings: {len(env.buildings)}")
    logger.info(f"  - Building name: {env.buildings[0].name if env.buildings else 'None'}")
    logger.info(f"  - Timesteps: {env.time_steps}")
    
    # Action space
    logger.info(f"\n[4] ACTION SPACE")
    logger.info(f"  - Type: {type(env.action_space)}")
    logger.info(f"  - Num actions per building: {env.action_space[0].shape[0]}")
    logger.info(f"  - Action bounds: {env.action_space[0]}")
    
    # Observations
    logger.info(f"\n[5] OBSERVATIONS (AFTER RESET)")
    obs, _ = env.reset()
    logger.info(f"  - Type: {type(obs)}")
    logger.info(f"  - Num agents: {len(obs)}")
    logger.info(f"  - Features per agent: {len(obs[0])}")
    logger.info(f"  - First 10 features: {obs[0][:10]}")
    
    logger.info(f"\n[RESULTADO] V MALL IQUITOS READY FOR TRAINING")
    logger.info(f"  - 1 edificio (MALL Iquitos)")
    logger.info(f"  - Action dimensions: {env.action_space[0].shape[0]}")
    logger.info(f"  - Observation dimensions: {len(obs[0])}")
    logger.info(f"  - PV + BESS devices included")
    
except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    env.close()

logger.info("\n" + "="*100)
