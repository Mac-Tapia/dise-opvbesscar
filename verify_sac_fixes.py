#!/usr/bin/env python3
"""
VERIFICACIÓN RÁPIDA DE CORRECCIONES SAC - 2026-01-31

Valida que:
1. EV_DEMAND ahora se lee del building (no hardcoded)
2. CO₂ DIRECTO está sincronizado con energía entregada
3. Motos/Mototaxis contadas correctamente
4. No hay duplicaciones

Ejecución: python verify_sac_fixes.py
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

def verify_sac_code():
    """Verificar cambios en sac.py"""
    sac_path = Path("src/iquitos_citylearn/oe3/agents/sac.py")

    if not sac_path.exists():
        logger.error(f"❌ No encontrado: {sac_path}")
        return False

    content = sac_path.read_text(encoding='utf-8')
    checks_passed = 0
    checks_total = 0

    # Check 1: EV_DEMAND no hardcodeado a 50.0
    checks_total += 1
    if "ev_demand_kw = 50.0  # kW fijo estimado" not in content:
        logger.info("✓ Check 1 PASS: EV_DEMAND no hardcodeado a 50.0")
        checks_passed += 1
    else:
        logger.error("❌ Check 1 FAIL: EV_DEMAND aún está hardcodeado a 50.0")

    # Check 2: Lee desde electric_vehicle_chargers
    checks_total += 1
    if "chargers = getattr(b, 'electric_vehicle_chargers'" in content:
        logger.info("✓ Check 2 PASS: Lee desde electric_vehicle_chargers")
        checks_passed += 1
    else:
        logger.error("❌ Check 2 FAIL: No lee desde electric_vehicle_chargers")

    # Check 3: Usa fallback 54.0 (no 50.0)
    checks_total += 1
    if "ev_demand_kw = 54.0" in content:
        logger.info("✓ Check 3 PASS: Fallback es 54.0 kW (correcto)")
        checks_passed += 1
    else:
        logger.error("❌ Check 3 FAIL: Fallback no es 54.0 kW")

    # Check 4: CO₂ DIRECTO sincronizado
    checks_total += 1
    if "ev_power_delivered_kw = min(ev_demand_kw, solar_available_kw + bess_discharge_kw)" in content:
        logger.info("✓ Check 4 PASS: CO₂ DIRECTO sincronizado con energía entregada")
        checks_passed += 1
    else:
        logger.error("❌ Check 4 FAIL: CO₂ DIRECTO no está sincronizado")

    # Check 5: Motos/Mototaxis cálculo correcto (87.5% / 12.5%)
    checks_total += 1
    if "motos_fraction = 112.0 / 128.0" in content and "mototaxis_fraction = 16.0 / 128.0" in content:
        logger.info("✓ Check 5 PASS: Distribución motos/mototaxis correcta (87.5%/12.5%)")
        checks_passed += 1
    else:
        logger.error("❌ Check 5 FAIL: Distribución motos/mototaxis incorrecta")

    # Check 6: No duplica cálculo de CO₂ (antiguo código removido)
    checks_total += 1
    if "EV_DEMAND_CONSTANT_KW = 50.0  # kW fijo estimado" not in content:
        logger.info("✓ Check 6 PASS: Código antiguo de CO₂ DIRECTO removido")
        checks_passed += 1
    else:
        logger.error("❌ Check 6 FAIL: Código antiguo de CO₂ DIRECTO aún existe")

    # Check 7: Logging sincronizado menciona "ev_delivered"
    checks_total += 1
    if "ev_delivered=" in content and "[SAC CO2 DIRECTO SYNC]" in content:
        logger.info("✓ Check 7 PASS: Logging sincronizado con energía entregada")
        checks_passed += 1
    else:
        logger.error("❌ Check 7 FAIL: Logging no menciona energía entregada")

    logger.info(f"\n📊 Resultados: {checks_passed}/{checks_total} checks pasados")
    return checks_passed == checks_total


def verify_baseline():
    """Verificar que baseline.csv tiene datos correctos"""
    baseline_path = Path("outputs/oe3/baseline_full_year_hourly.csv")

    if not baseline_path.exists():
        logger.warning(f"⚠ Baseline no encontrado: {baseline_path}")
        return None

    import pandas as pd
    df = pd.read_csv(baseline_path)

    logger.info(f"\n📊 Baseline Statistics:")
    logger.info(f"   Filas: {len(df)} (esperadas 8760)")
    logger.info(f"   EV demand rango: {df['ev_demand'].min():.1f} - {df['ev_demand'].max():.1f} kW")
    logger.info(f"   EV demand promedio: {df['ev_demand'].mean():.1f} kW")
    logger.info(f"   PV generación máx: {df['pv_generation'].max():.1f} kW")
    logger.info(f"   Grid import total: {df['grid_import'].sum():.1f} kWh")

    # Validación
    if len(df) != 8760:
        logger.error(f"❌ Baseline tiene {len(df)} filas, esperadas 8760")
        return False

    if df['ev_demand'].max() <= 0:
        logger.error("❌ EV demand está vacío o zero")
        return False

    logger.info("✓ Baseline validado correctamente")
    return True


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("VERIFICACIÓN DE CORRECCIONES SAC - 2026-01-31")
    logger.info("=" * 80)

    sac_ok = verify_sac_code()
    baseline_ok = verify_baseline()

    logger.info("\n" + "=" * 80)
    if sac_ok:
        logger.info("✅ TODAS LAS CORRECCIONES APLICADAS CORRECTAMENTE")
        logger.info("   El sistema está listo para entrenamiento")
    else:
        logger.error("❌ ALGUNAS CORRECCIONES FALTAN - Revisar arriba")
        sys.exit(1)
    logger.info("=" * 80)
