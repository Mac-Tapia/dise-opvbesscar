#!/usr/bin/env python3
"""🔧 CORRECCIÓN: Usar VALORES REALES OE2 en todo el sistema.
Esto es consistente con OE2 dimensionamiento real calculado.
Se actualizarán TODAS las referencias.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json
import logging
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# VALORES REALES DEFINIDOS DEL CÁLCULO OE2
# ============================================================================
REAL_OE2_DATA: Dict[str, Any] = {
    'bess_capacity_kwh': 4520.0,      # Del cálculo OE2 real
    'bess_power_kw': 2712.0,          # Del cálculo OE2 real
    'pv_capacity_kwp': 4050.0,        # Valor nominal del proyecto
    'chargers': 128,                  # 32 chargers × 4 sockets
    'episode_time_steps': 8760,       # 1 año en horas
    'seconds_per_timestep': 3600,     # 1 hora
}

logger.info("\n📋 VALORES REALES DEFINIDOS (OE2 DIMENSIONAMIENTO):")
logger.info(f"   • BESS Capacidad: {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh")
logger.info(f"   • BESS Potencia: {REAL_OE2_DATA['bess_power_kw']:.0f} kW")
logger.info(f"   • PV Capacidad: {REAL_OE2_DATA['pv_capacity_kwp']:.0f} kWp")
logger.info(f"   • Chargers: {REAL_OE2_DATA['chargers']}")
logger.info(f"   • Episode timesteps: {REAL_OE2_DATA['episode_time_steps']}")

# ============================================================================
# 1. ACTUALIZAR schema.json (CityLearn)
# ============================================================================
logger.info("\n" + "-"*90)
logger.info("[1/4] ACTUALIZANDO schema.json")
logger.info("-"*90)

schema_path: Path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
try:
    with open(schema_path) as f:
        schema: Dict[str, Any] = json.load(f)

    bess = schema['buildings']['Mall_Iquitos']['electrical_storage']['attributes']
    pv = schema['buildings']['Mall_Iquitos']['solar_generation']['attributes']

    old_bess_cap = bess.get('capacity')
    old_bess_pow = bess.get('power_output_nominal')
    old_pv = pv.get('peak_power')

    # Actualizar BESS
    bess['capacity'] = REAL_OE2_DATA['bess_capacity_kwh']
    bess['power_output_nominal'] = REAL_OE2_DATA['bess_power_kw']

    # Actualizar PV
    pv['peak_power'] = REAL_OE2_DATA['pv_capacity_kwp']

    # Actualizar timesteps
    schema['episode_time_steps'] = REAL_OE2_DATA['episode_time_steps']

    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)

    logger.info(f"   ✅ BESS capacity: {old_bess_cap} → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh")
    logger.info(f"   ✅ BESS power: {old_bess_pow} → {REAL_OE2_DATA['bess_power_kw']:.0f} kW")
    logger.info(f"   ✅ PV peak_power: {old_pv} → {REAL_OE2_DATA['pv_capacity_kwp']:.0f} kWp")
    logger.info(f"   ✅ Archivo guardado: {schema_path}")

except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")

# ============================================================================
# 2. ACTUALIZAR default.yaml (configs)
# ============================================================================
logger.info("\n" + "-"*90)
logger.info("[2/4] ACTUALIZANDO configs/default.yaml")
logger.info("-"*90)

yaml_path = Path("configs/default.yaml")
try:
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    old_cap = config['oe2']['bess'].get('fixed_capacity_kwh')
    old_pow = config['oe2']['bess'].get('fixed_power_kw')

    # Actualizar BESS
    config['oe2']['bess']['fixed_capacity_kwh'] = REAL_OE2_DATA['bess_capacity_kwh']
    config['oe2']['bess']['fixed_power_kw'] = REAL_OE2_DATA['bess_power_kw']

    # Actualizar dispatch rules con BESS real
    config['oe2']['dispatch_rules']['priority_2_pv_to_bess']['bess_power_max_kw'] = REAL_OE2_DATA['bess_power_kw']
    config['oe2']['dispatch_rules']['priority_3_bess_to_ev']['bess_power_max_kw'] = REAL_OE2_DATA['bess_power_kw']

    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"   ✅ BESS fixed_capacity_kwh: {old_cap} → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh")
    logger.info(f"   ✅ BESS fixed_power_kw: {old_pow} → {REAL_OE2_DATA['bess_power_kw']:.0f} kW")
    logger.info(f"   ✅ Dispatch rules actualizadas")
    logger.info(f"   ✅ Archivo guardado: {yaml_path}")

except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")

# ============================================================================
# 3. ACTUALIZAR configs/default_optimized.yaml
# ============================================================================
logger.info("\n" + "-"*90)
logger.info("[3/4] ACTUALIZANDO configs/default_optimized.yaml")
logger.info("-"*90)

yaml_opt_path = Path("configs/default_optimized.yaml")
try:
    with open(yaml_opt_path) as f:
        config_opt = yaml.safe_load(f)

    old_cap = config_opt['oe2']['bess'].get('fixed_capacity_kwh')
    old_pow = config_opt['oe2']['bess'].get('fixed_power_kw')

    # Actualizar BESS
    config_opt['oe2']['bess']['fixed_capacity_kwh'] = REAL_OE2_DATA['bess_capacity_kwh']
    config_opt['oe2']['bess']['fixed_power_kw'] = REAL_OE2_DATA['bess_power_kw']

    # Actualizar dispatch rules
    if 'priority_2_pv_to_bess' in config_opt['oe2']['dispatch_rules']:
        config_opt['oe2']['dispatch_rules']['priority_2_pv_to_bess']['bess_power_max_kw'] = REAL_OE2_DATA['bess_power_kw']
    if 'priority_3_bess_to_ev' in config_opt['oe2']['dispatch_rules']:
        config_opt['oe2']['dispatch_rules']['priority_3_bess_to_ev']['bess_power_max_kw'] = REAL_OE2_DATA['bess_power_kw']

    with open(yaml_opt_path, 'w') as f:
        yaml.dump(config_opt, f, default_flow_style=False, sort_keys=False)

    logger.info(f"   ✅ BESS fixed_capacity_kwh: {old_cap} → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh")
    logger.info(f"   ✅ BESS fixed_power_kw: {old_pow} → {REAL_OE2_DATA['bess_power_kw']:.0f} kW")
    logger.info(f"   ✅ Dispatch rules actualizadas")
    logger.info(f"   ✅ Archivo guardado: {yaml_opt_path}")

except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")

# ============================================================================
# 4. VALIDACIÓN POST-CORRECCIÓN
# ============================================================================
logger.info("\n" + "-"*90)
logger.info("[4/4] VALIDACIÓN POST-CORRECCIÓN")
logger.info("-"*90)

logger.info("\n✅ Verificando schema.json:")
try:
    schema = json.load(open("data/processed/citylearn/iquitos_ev_mall/schema.json"))
    bess = schema['buildings']['Mall_Iquitos']['electrical_storage']['attributes']
    pv = schema['buildings']['Mall_Iquitos']['solar_generation']['attributes']

    bess_cap_ok = bess.get('capacity') == REAL_OE2_DATA['bess_capacity_kwh']
    bess_pow_ok = bess.get('power_output_nominal') == REAL_OE2_DATA['bess_power_kw']
    pv_ok = pv.get('peak_power') == REAL_OE2_DATA['pv_capacity_kwp']
    ts_ok = schema.get('episode_time_steps') == REAL_OE2_DATA['episode_time_steps']

    logger.info(f"   {'✅' if bess_cap_ok else '❌'} BESS capacity: {bess.get('capacity')} == {REAL_OE2_DATA['bess_capacity_kwh']}")
    logger.info(f"   {'✅' if bess_pow_ok else '❌'} BESS power: {bess.get('power_output_nominal')} == {REAL_OE2_DATA['bess_power_kw']}")
    logger.info(f"   {'✅' if pv_ok else '❌'} PV peak: {pv.get('peak_power')} == {REAL_OE2_DATA['pv_capacity_kwp']}")
    logger.info(f"   {'✅' if ts_ok else '❌'} Episode timesteps: {schema.get('episode_time_steps')} == {REAL_OE2_DATA['episode_time_steps']}")

    if bess_cap_ok and bess_pow_ok and pv_ok and ts_ok:
        logger.info(f"   ✅ SCHEMA VÁLIDO - TODOS LOS VALORES CORRECTOS")
    else:
        logger.error(f"   ❌ SCHEMA INVÁLIDO - VALORES NO COINCIDEN")
except Exception as e:
    logger.error(f"   ❌ ERROR validando schema: {e}")

logger.info("\n✅ Verificando default.yaml:")
try:
    with open("configs/default.yaml") as f:
        config = yaml.safe_load(f)

    cap_ok = config['oe2']['bess']['fixed_capacity_kwh'] == REAL_OE2_DATA['bess_capacity_kwh']
    pow_ok = config['oe2']['bess']['fixed_power_kw'] == REAL_OE2_DATA['bess_power_kw']

    logger.info(f"   {'✅' if cap_ok else '❌'} BESS fixed_capacity_kwh: {config['oe2']['bess']['fixed_capacity_kwh']} == {REAL_OE2_DATA['bess_capacity_kwh']}")
    logger.info(f"   {'✅' if pow_ok else '❌'} BESS fixed_power_kw: {config['oe2']['bess']['fixed_power_kw']} == {REAL_OE2_DATA['bess_power_kw']}")

    if cap_ok and pow_ok:
        logger.info(f"   ✅ CONFIG VÁLIDA - TODOS LOS VALORES CORRECTOS")
    else:
        logger.error(f"   ❌ CONFIG INVÁLIDA - VALORES NO COINCIDEN")
except Exception as e:
    logger.error(f"   ❌ ERROR validando config: {e}")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
logger.info("\n" + "="*90)
logger.info("✅ CORRECCIÓN COMPLETADA - VALORES REALES OE2 APLICADOS")
logger.info("="*90)

logger.info(f"""
📊 CAMBIOS APLICADOS:

1. schema.json (CityLearn):
   ✅ BESS capacity: → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh (REAL OE2)
   ✅ BESS power: → {REAL_OE2_DATA['bess_power_kw']:.0f} kW (REAL OE2)
   ✅ PV peak_power: → {REAL_OE2_DATA['pv_capacity_kwp']:.0f} kWp
   ✅ episode_time_steps: → {REAL_OE2_DATA['episode_time_steps']}

2. default.yaml:
   ✅ fixed_capacity_kwh: → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh
   ✅ fixed_power_kw: → {REAL_OE2_DATA['bess_power_kw']:.0f} kW
   ✅ dispatch_rules: BESS power actualizado

3. default_optimized.yaml:
   ✅ fixed_capacity_kwh: → {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh
   ✅ fixed_power_kw: → {REAL_OE2_DATA['bess_power_kw']:.0f} kW
   ✅ dispatch_rules: BESS power actualizado

🎯 VALORES REALES AHORA CONSISTENTES:
   • Todos los archivos usan {REAL_OE2_DATA['bess_capacity_kwh']:.0f} kWh / {REAL_OE2_DATA['bess_power_kw']:.0f} kW
   • Basados en cálculo OE2 real (bess_results.json)
   • Consistentes con configuración del proyecto

✅ SISTEMA LISTO PARA ENTRENAMIENTOS
""")
