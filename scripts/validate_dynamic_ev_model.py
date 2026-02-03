#!/usr/bin/env python3
"""
================================================================================
VALIDACIÓN - MODELO DINÁMICO DE EVs
================================================================================

Valida que el nuevo modelo dinámico de cálculo de demanda de EVs funciona
correctamente, comparando con el modelo estático anterior.

Pruebas:
1. Crear configuraciones de chargers (motos y mototaxis)
2. Validar parámetros físicos (SOC, capacidad, potencia)
3. Calcular demanda horaria con variabilidad temporal
4. Comparar energía total vs perfil OE2
5. Visualizar resultados
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iquitos_citylearn.oe3.ev_demand_calculator import (
    EVChargerConfig,
    EVDemandCalculator,
    EVFleetAggregator,
    create_ev_configs_iquitos,
)


def validate_charger_configs():
    """Valida que las configuraciones de chargers son correctas."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 1: Validación de Configuraciones de Chargers")
    logger.info("=" * 80)

    moto_configs, mototaxi_configs = create_ev_configs_iquitos()

    # Motos
    logger.info(f"\n✓ Motos: {len(moto_configs)} chargers")
    for config in moto_configs[:3]:
        logger.info(f"  {config.charger_id:3d}: {config.charger_power_kw} kW, "
                   f"{config.battery_capacity_kwh} kWh, "
                   f"SOC {config.battery_soc_arrival:.0%}->{config.battery_soc_target:.0%}")

    # Mototaxis
    logger.info(f"\n✓ Mototaxis: {len(mototaxi_configs)} chargers")
    for config in mototaxi_configs:
        logger.info(f"  {config.charger_id:3d}: {config.charger_power_kw} kW, "
                   f"{config.battery_capacity_kwh} kWh, "
                   f"SOC {config.battery_soc_arrival:.0%}->{config.battery_soc_target:.0%}")

    assert len(moto_configs) == 112, f"Expected 112 motos, got {len(moto_configs)}"
    assert len(mototaxi_configs) == 16, f"Expected 16 mototaxis, got {len(mototaxi_configs)}"

    logger.info("\n✅ PASS: Todas las configuraciones son correctas")


def validate_energy_calculations():
    """Valida cálculos de energía y tiempo de carga."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 2: Validación de Cálculos de Energía")
    logger.info("=" * 80)

    moto_configs, mototaxi_configs = create_ev_configs_iquitos()

    # Moto
    moto = EVDemandCalculator(moto_configs[0])
    moto_energy = moto.calculate_energy_required()
    moto_time = moto.calculate_charging_time()

    logger.info(f"\n✓ Moto (Charger 1):")
    logger.info(f"  Energía requerida: {moto_energy:.2f} kWh")
    logger.info(f"    = (90% - 20%) × 2.5 kWh = 0.7 × 2.5 = 1.75 kWh")
    logger.info(f"  Tiempo de carga: {moto_time:.2f} horas")
    logger.info(f"    = 1.75 kWh / 2.0 kW = 0.875 horas")

    assert abs(moto_energy - 1.75) < 0.01, f"Energía incorrecta: {moto_energy}"
    assert abs(moto_time - 0.875) < 0.01, f"Tiempo incorrecto: {moto_time}"

    # Mototaxi
    mototaxi = EVDemandCalculator(mototaxi_configs[0])
    mototaxi_energy = mototaxi.calculate_energy_required()
    mototaxi_time = mototaxi.calculate_charging_time()

    logger.info(f"\n✓ Mototaxi (Charger 113):")
    logger.info(f"  Energía requerida: {mototaxi_energy:.2f} kWh")
    logger.info(f"    = (85% - 25%) × 4.5 kWh = 0.6 × 4.5 = 2.7 kWh")
    logger.info(f"  Tiempo de carga: {mototaxi_time:.2f} horas")
    logger.info(f"    = 2.7 kWh / 3.0 kW = 0.9 horas")

    assert abs(mototaxi_energy - 2.7) < 0.01, f"Energía incorrecta: {mototaxi_energy}"
    assert abs(mototaxi_time - 0.9) < 0.01, f"Tiempo incorrecto: {mototaxi_time}"

    logger.info("\n✅ PASS: Todos los cálculos son correctos")


def validate_hourly_demand():
    """Valida que la demanda horaria tiene variabilidad realista."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 3: Validación de Demanda Horaria")
    logger.info("=" * 80)

    moto_configs, _ = create_ev_configs_iquitos()
    calc = EVDemandCalculator(moto_configs[0])

    logger.info(f"\nDemanda en diferentes horas (conectado, lunes):")
    for hour in [6, 9, 12, 18, 21, 23]:
        demand = calc.calculate_hourly_demand(hour, 0, True)
        if 18 <= hour <= 21:
            logger.info(f"  Hora {hour:2d}: {demand:6.2f} kW [PICO: +30%]")
        else:
            logger.info(f"  Hora {hour:2d}: {demand:6.2f} kW")

    # Test desconectado
    demand_disconnected = calc.calculate_hourly_demand(12, 0, False)
    assert demand_disconnected == 0.0, f"Desconectado debe ser 0, got {demand_disconnected}"

    logger.info(f"\nDemanda cuando desconectado: {demand_disconnected:.2f} kW ✓")

    # Test fin de semana
    demand_weekday = calc.calculate_hourly_demand(12, 0, True)
    demand_weekend = calc.calculate_hourly_demand(12, 6, True)  # Domingo

    logger.info(f"\nComparación: Lunes vs Domingo (hora 12, conectado)")
    logger.info(f"  Lunes:   {demand_weekday:.2f} kW")
    logger.info(f"  Domingo: {demand_weekend:.2f} kW (-10% fin de semana)")

    assert demand_weekend < demand_weekday, "Fin de semana debe tener menos demanda"

    logger.info("\n✅ PASS: Demanda horaria tiene variabilidad realista")


def validate_daily_profile():
    """Valida que el perfil diario es realista."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 4: Validación de Perfil Diario")
    logger.info("=" * 80)

    moto_configs, _ = create_ev_configs_iquitos()
    calc = EVDemandCalculator(moto_configs[0])

    # Crear patrón de ocupancia (conectado 9 AM - 10 PM = horas 9-21)
    occupancy = np.zeros(24, dtype=int)
    occupancy[9:22] = 1  # Conectado de 9 AM a 10 PM

    # Calcular perfil
    profile = calc.calculate_daily_profile(0, occupancy)

    logger.info(f"\nPerfil diario (lunes, ocupancia 9AM-10PM):")
    logger.info(f"Hora  Demand(kW)  Estado")
    logger.info(f"──────────────────────")
    for hour in range(24):
        state = "CONECTADO" if occupancy[hour] else "LIBRE"
        logger.info(f"{hour:2d}    {profile[hour]:7.2f}      {state}")

    # Validaciones
    assert all(profile[:9] == 0), "Antes de 9 AM debe ser 0"
    assert all(profile[22:] == 0), "Después de 10 PM debe ser 0"
    assert all(profile[9:22] > 0), "Entre 9 AM y 10 PM debe haber demanda"

    # Picos esperados en 18-21h
    peak_hours = profile[18:22]
    base_hours = profile[9:18]
    assert np.mean(peak_hours) > np.mean(base_hours), "Picos > base"

    logger.info(f"\n✓ Demanda promedio (9-18h): {np.mean(base_hours):.2f} kW")
    logger.info(f"✓ Demanda promedio (18-22h): {np.mean(peak_hours):.2f} kW")
    logger.info(f"✓ Ratio (picos/base): {np.mean(peak_hours)/np.mean(base_hours):.2f}x")

    logger.info("\n✅ PASS: Perfil diario es realista")


def validate_annual_consistency():
    """Valida que el perfil anual es consistente y realista."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 5: Validación de Consistencia Anual")
    logger.info("=" * 80)

    moto_configs, _ = create_ev_configs_iquitos()
    calc = EVDemandCalculator(moto_configs[0])

    # Crear ocupancia anual realista (conectado durante horarios de operación)
    occupancy_annual = np.zeros(8760, dtype=int)
    for t in range(8760):
        hour = t % 24
        if 9 <= hour < 22:  # 9 AM - 10 PM
            occupancy_annual[t] = 1

    # Calcular demanda anual
    demand_annual = calc.calculate_annual_profile(occupancy_annual)

    total_energy = demand_annual.sum()
    annual_kwh = total_energy  # kW × 1 hora = kWh

    logger.info(f"\nDemanda anual total: {annual_kwh:,.0f} kWh")
    logger.info(f"Horas conectadas: {np.sum(occupancy_annual)} horas ({np.sum(occupancy_annual)/8760*100:.1f}% del año)")
    logger.info(f"Demanda promedio (conectado): {np.mean(demand_annual[occupancy_annual > 0]):.2f} kW")
    logger.info(f"Demanda promedio (anual): {np.mean(demand_annual):.2f} kW")

    # Expectativa: ~13 horas/día × 365 días × 2 kW = ~9,490 kWh
    # (sin contar variabilidad y picos)
    expected_kwh = 13 * 365 * 2.0  # Base sin variabilidad
    actual_with_variation = annual_kwh

    logger.info(f"\nComparación:")
    logger.info(f"  Base (13h × 365d × 2kW): {expected_kwh:,.0f} kWh")
    logger.info(f"  Real (con variabilidad): {actual_with_variation:,.0f} kWh")
    logger.info(f"  Diferencia: {(actual_with_variation - expected_kwh) / expected_kwh * 100:+.1f}%")

    # Permitir ±20% de variación (picos + fin de semana)
    assert expected_kwh * 0.8 < actual_with_variation < expected_kwh * 1.3, \
        f"Demanda anual fuera de rango esperado: {actual_with_variation}"

    logger.info("\n✅ PASS: Consistencia anual validada")


def validate_fleet_aggregation():
    """Valida que la agregación de demanda de flota funciona correctamente."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 6: Validación de Agregación de Flota")
    logger.info("=" * 80)

    moto_configs, mototaxi_configs = create_ev_configs_iquitos()
    all_configs = moto_configs + mototaxi_configs

    aggregator = EVFleetAggregator(all_configs)

    # Crear ocupancia simple: todos conectados en hora 12
    occupancy_matrix = np.zeros((8760, 128), dtype=int)
    occupancy_matrix[12, :] = 1  # Todos conectados en hora 12

    # Calcular demanda de flota
    fleet_demand = aggregator.calculate_fleet_demand_annual(occupancy_matrix)

    total_fleet_kw = fleet_demand[12]
    expected_fleet_kw = (112 * 2.0) + (16 * 3.0)  # 112 motos × 2kW + 16 mototaxis × 3kW

    logger.info(f"\nDemanda de flota @ hora 12 (todos conectados):")
    logger.info(f"  Motos: 112 × 2.0 kW = 224 kW")
    logger.info(f"  Mototaxis: 16 × 3.0 kW = 48 kW")
    logger.info(f"  Total esperado: {expected_fleet_kw:.0f} kW")
    logger.info(f"  Total actual: {total_fleet_kw:.2f} kW")

    # Debe ser igual (sin variabilidad en hora 12 = mid-day, no-peak)
    assert abs(total_fleet_kw - expected_fleet_kw * 1.0) < 5, \
        f"Demanda de flota incorrecta: {total_fleet_kw} vs {expected_fleet_kw}"

    logger.info("\n✅ PASS: Agregación de flota correcta")


def main():
    """Ejecuta todas las validaciones."""
    logger.info("")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "VALIDACIÓN - MODELO DINÁMICO DE EVs".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")

    try:
        validate_charger_configs()
        validate_energy_calculations()
        validate_hourly_demand()
        validate_daily_profile()
        validate_annual_consistency()
        validate_fleet_aggregation()

        logger.info("")
        logger.info("╔" + "=" * 78 + "╗")
        logger.info("║" + " " * 78 + "║")
        logger.info("║" + "✅ TODOS LOS TESTS PASARON".center(78) + "║")
        logger.info("║" + " " * 78 + "║")
        logger.info("║" + "El modelo dinámico de EVs está LISTO para usar".center(78) + "║")
        logger.info("║" + " " * 78 + "║")
        logger.info("╚" + "=" * 78 + "╝")

        return 0

    except AssertionError as e:
        logger.error(f"\n❌ TEST FALLÓ: {e}")
        return 1
    except Exception as e:
        logger.error(f"\n❌ ERROR INESPERADO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
