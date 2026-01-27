#!/usr/bin/env python
"""CORRECCIÓN ROBUSTA - Reparar schema y validadores con datos REALES"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def fix_schema_completely() -> bool:
    """Reparar completamente el schema con datos REALES"""
    schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')

    logger.info("=" * 70)
    logger.info("REPARACIÓN COMPLETA DE SCHEMA CON DATOS REALES")
    logger.info("=" * 70)

    if not schema_path.exists():
        logger.error(f"Schema no encontrado: {schema_path}")
        return False

    # Load current
    with open(schema_path) as f:
        schema = json.load(f)

    # Datos REALES del proyecto OE3
    REAL_DATA = {
        'episode_time_steps': 8760,                      # 1 año × 24 horas
        'seconds_per_time_step': 3600,                   # 1 hora
        'pv_peak_power': 4050.0,                         # 4,050 kWp (OE2 diseño)
        'bess_capacity': 2000.0,                         # 2,000 kWh (OE3 especificado)
        'bess_power_output': 1200.0,                     # 1,200 kW (OE3)
        'chargers_count': 128,                           # 32 chargers × 4 sockets
        'central_agent': True,
    }

    changes = []

    # 1. Fix episode_time_steps (DATO REAL)
    old_val = schema.get('episode_time_steps')
    if old_val != REAL_DATA['episode_time_steps']:
        schema['episode_time_steps'] = REAL_DATA['episode_time_steps']
        changes.append(f"✅ episode_time_steps: {old_val} → {REAL_DATA['episode_time_steps']}")
        logger.info(f"  ✓ episode_time_steps: {old_val} → {REAL_DATA['episode_time_steps']}")
    else:
        logger.info(f"  ✓ episode_time_steps: {old_val} (ya correcto)")

    # 2. Fix building PV peak_power (DATO REAL)
    building = schema.get('buildings', {}).get('Mall_Iquitos', {})
    if building:
        pv_attrs = building.get('pv', {}).get('attributes', {})
        old_val = pv_attrs.get('peak_power')
        if old_val != REAL_DATA['pv_peak_power']:
            pv_attrs['peak_power'] = REAL_DATA['pv_peak_power']
            changes.append(f"✅ pv.peak_power: {old_val} → {REAL_DATA['pv_peak_power']}")
            logger.info(f"  ✓ pv.peak_power: {old_val} → {REAL_DATA['pv_peak_power']} kWp")
        else:
            logger.info(f"  ✓ pv.peak_power: {old_val} kWp (ya correcto)")

    # 3. Fix BESS capacity (DATO REAL - OE3)
    if building:
        bess_attrs = building.get('electrical_storage', {}).get('attributes', {})
        old_val = bess_attrs.get('capacity')
        # OE3 especifica 2000 kWh
        if old_val != REAL_DATA['bess_capacity']:
            bess_attrs['capacity'] = REAL_DATA['bess_capacity']
            changes.append(f"✅ bess.capacity: {old_val} → {REAL_DATA['bess_capacity']} kWh (OE3)")
            logger.info(f"  ✓ bess.capacity: {old_val} → {REAL_DATA['bess_capacity']} kWh")
        else:
            logger.info(f"  ✓ bess.capacity: {old_val} kWh (ya correcto)")

    # 4. Fix BESS power output (DATO REAL)
    if building:
        bess_attrs = building.get('electrical_storage', {}).get('attributes', {})
        old_val = bess_attrs.get('power_output_nominal')
        if old_val != REAL_DATA['bess_power_output']:
            bess_attrs['power_output_nominal'] = REAL_DATA['bess_power_output']
            changes.append(f"✅ bess.power_output_nominal: {old_val} → {REAL_DATA['bess_power_output']}")
            logger.info(f"  ✓ bess.power_output_nominal: {old_val} → {REAL_DATA['bess_power_output']} kW")
        else:
            logger.info(f"  ✓ bess.power_output_nominal: {old_val} kW (ya correcto)")

    # 5. Verify chargers (DATO REAL)
    if building:
        chargers = building.get('chargers', {})
        charger_count = len(chargers)
        if charger_count != REAL_DATA['chargers_count']:
            logger.error(f"❌ Chargers: {charger_count} (DEBE SER 128)")
            return False
        else:
            logger.info(f"  ✓ Chargers: {charger_count} (correcto)")

    # Save
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)

    logger.info("\n" + "=" * 70)
    logger.info("VALIDACIÓN POST-REPARACIÓN")
    logger.info("=" * 70)

    # Reload and verify
    with open(schema_path) as f:
        verify = json.load(f)

    verif_building = verify['buildings']['Mall_Iquitos']
    verif_chargers = len(verif_building.get('chargers', {}))
    verif_pv = verif_building.get('pv', {}).get('attributes', {}).get('peak_power')
    verif_bess_cap = verif_building.get('electrical_storage', {}).get('attributes', {}).get('capacity')
    verif_bess_pow = verif_building.get('electrical_storage', {}).get('attributes', {}).get('power_output_nominal')
    verif_ts = verify.get('episode_time_steps')

    all_ok = (
        verif_ts == 8760 and
        verif_pv == 4050.0 and
        verif_bess_cap == 2000.0 and
        verif_bess_pow == 1200.0 and
        verif_chargers == 128
    )

    logger.info(f"\n✓ episode_time_steps: {verif_ts} == 8760 ✅" if verif_ts == 8760 else f"\n✓ episode_time_steps: {verif_ts} ❌")
    logger.info(f"✓ pv.peak_power: {verif_pv} kWp == 4050.0 ✅" if verif_pv == 4050.0 else f"✓ pv.peak_power: {verif_pv} ❌")
    logger.info(f"✓ bess.capacity: {verif_bess_cap} kWh == 2000.0 ✅" if verif_bess_cap == 2000.0 else f"✓ bess.capacity: {verif_bess_cap} ❌")
    logger.info(f"✓ bess.power_output_nominal: {verif_bess_pow} kW == 1200.0 ✅" if verif_bess_pow == 1200.0 else f"✓ bess.power_output_nominal: {verif_bess_pow} ❌")
    logger.info(f"✓ chargers: {verif_chargers} == 128 ✅" if verif_chargers == 128 else f"✓ chargers: {verif_chargers} ❌")

    if all_ok:
        logger.info("\n✅ SCHEMA COMPLETAMENTE REPARADO Y VALIDADO")
        return True
    else:
        logger.error("\n❌ SCHEMA AÚN TIENE ERRORES")
        return False


if __name__ == '__main__':
    import sys
    success = fix_schema_completely()
    sys.exit(0 if success else 1)
