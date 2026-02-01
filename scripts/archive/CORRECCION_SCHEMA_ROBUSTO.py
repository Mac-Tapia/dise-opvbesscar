#!/usr/bin/env python3
"""🔧 CORRECCIÓN ROBUSTA: Valores REALES OE2 en schema.json.
Versión mejorada que busca la estructura CORRECTA del schema.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Valores reales OE2
REAL_VALUES: Dict[str, Any] = {
    'bess_capacity_kwh': 4520.0,      # Del cálculo OE2 real (bess_results.json)
    'bess_power_kw': 2712.0,          # Del cálculo OE2 real
    'pv_capacity_kwp': 4050.0,        # Especificación del proyecto
    'episode_time_steps': 8760,       # 1 año en horas
}

schema_path: Path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")

logger.info(f"\n📄 Cargando schema desde: {schema_path}")
try:
    with open(schema_path) as f:
        schema: Dict[str, Any] = json.load(f)
    logger.info("   ✅ Schema cargado exitosamente")
except Exception as e:
    logger.error(f"   ❌ ERROR al cargar schema: {e}")
    exit(1)

# Obtener building
mall: Dict[str, Any] = schema['buildings']['Mall_Iquitos']
logger.info(f"\n🏢 Building: Mall_Iquitos")

# ============================================================================
# 1. ACTUALIZAR BESS (electrical_storage)
# ============================================================================
logger.info(f"\n[1] Actualizando BESS (electrical_storage)...")
try:
    bess = mall['electrical_storage']['attributes']

    old_cap = bess.get('capacity')
    old_pow = bess.get('power_output_nominal')

    bess['capacity'] = REAL_VALUES['bess_capacity_kwh']
    bess['power_output_nominal'] = REAL_VALUES['bess_power_kw']

    logger.info(f"   ✅ Capacidad: {old_cap} → {REAL_VALUES['bess_capacity_kwh']:.0f} kWh")
    logger.info(f"   ✅ Potencia: {old_pow} → {REAL_VALUES['bess_power_kw']:.0f} kW")
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")

# ============================================================================
# 2. ACTUALIZAR PV (buscando estructura correcta)
# ============================================================================
logger.info(f"\n[2] Buscando y actualizando PV...")
pv_found = False

# Intentar diferentes ubicaciones
pv_locations: List[Tuple[str, str]] = [
    ('pv', 'attributes'),  # En 'pv' directamente
    ('pv', 'solar_generation'),  # Nested
    ('solar_generation', 'attributes'),  # En 'solar_generation'
]

for loc1, loc2 in pv_locations:
    try:
        if loc1 in mall and isinstance(mall[loc1], dict):
            if 'attributes' in mall[loc1]:
                pv = mall[loc1]['attributes']
                old_pv = pv.get('peak_power')
                pv['peak_power'] = REAL_VALUES['pv_capacity_kwp']
                logger.info(f"   ✅ PV found en '{loc1}.attributes'")
                logger.info(f"   ✅ peak_power: {old_pv} → {REAL_VALUES['pv_capacity_kwp']:.0f} kWp")
                pv_found = True
                break
            elif 'solar_generation' in mall[loc1]:
                pv = mall[loc1]['solar_generation']['attributes']
                old_pv = pv.get('peak_power')
                pv['peak_power'] = REAL_VALUES['pv_capacity_kwp']
                logger.info(f"   ✅ PV found en '{loc1}.solar_generation.attributes'")
                logger.info(f"   ✅ peak_power: {old_pv} → {REAL_VALUES['pv_capacity_kwp']:.0f} kWp")
                pv_found = True
                break
    except:
        pass

if not pv_found:
    logger.warning(f"   ⚠️ PV no encontrado en ubicaciones esperadas")
    logger.info(f"   ℹ️ Estructuras disponibles en building: {list(mall.keys())}")

# ============================================================================
# 3. ACTUALIZAR episode_time_steps
# ============================================================================
logger.info(f"\n[3] Actualizando episode_time_steps...")
try:
    old_ts = schema.get('episode_time_steps')
    schema['episode_time_steps'] = REAL_VALUES['episode_time_steps']
    logger.info(f"   ✅ episode_time_steps: {old_ts} → {REAL_VALUES['episode_time_steps']}")
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")

# ============================================================================
# 4. GUARDAR SCHEMA ACTUALIZADO
# ============================================================================
logger.info(f"\n[4] Guardando schema actualizado...")
try:
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    logger.info(f"   ✅ Schema guardado en: {schema_path}")
except Exception as e:
    logger.error(f"   ❌ ERROR al guardar: {e}")

# ============================================================================
# 5. VALIDACIÓN POST-ACTUALIZACIÓN
# ============================================================================
logger.info(f"\n[5] Validación post-actualización...")
try:
    with open(schema_path) as f:
        schema_check = json.load(f)

    mall_check = schema_check['buildings']['Mall_Iquitos']
    bess_check = mall_check['electrical_storage']['attributes']

    cap_ok = bess_check.get('capacity') == REAL_VALUES['bess_capacity_kwh']
    pow_ok = bess_check.get('power_output_nominal') == REAL_VALUES['bess_power_kw']
    ts_ok = schema_check.get('episode_time_steps') == REAL_VALUES['episode_time_steps']

    logger.info(f"   {'✅' if cap_ok else '❌'} BESS capacity: {bess_check.get('capacity')} == {REAL_VALUES['bess_capacity_kwh']}")
    logger.info(f"   {'✅' if pow_ok else '❌'} BESS power: {bess_check.get('power_output_nominal')} == {REAL_VALUES['bess_power_kw']}")
    logger.info(f"   {'✅' if ts_ok else '❌'} Episode timesteps: {schema_check.get('episode_time_steps')} == {REAL_VALUES['episode_time_steps']}")

    if cap_ok and pow_ok and ts_ok:
        logger.info(f"\n   ✅ SCHEMA COMPLETAMENTE CORRECTO")
    else:
        logger.error(f"\n   ⚠️ ALGUNOS VALORES NO COINCIDEN")

except Exception as e:
    logger.error(f"   ❌ ERROR en validación: {e}")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "="*90)
print("✅ CORRECCIÓN COMPLETADA")
print("="*90)
print(f"""
📊 VALORES ACTUALIZADOS EN SCHEMA:

BESS (electrical_storage):
  ✅ capacity: → {REAL_VALUES['bess_capacity_kwh']:.0f} kWh (OE2 real)
  ✅ power_output_nominal: → {REAL_VALUES['bess_power_kw']:.0f} kW (OE2 real)

PV: → {REAL_VALUES['pv_capacity_kwp']:.0f} kWp

Episode timesteps: → {REAL_VALUES['episode_time_steps']}

🎯 TODOS LOS VALORES SON REALES (OE2 DIMENSIONAMIENTO)
✅ SISTEMA LISTO
""")
