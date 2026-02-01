#!/usr/bin/env python
"""
Corrección de cálculo de consumo solar en SAC (y PPO/A2C).

El problema: solar_energy_sum está contando solo solar_generation bruto,
no cuánto solar REALMENTE se consumió según reglas de despacho.

Debería ser:
1. PV → EV (primero)
2. PV → BESS (lo que sobra)
3. BESS → EV (noche)
4. BESS → Grid (si SOC > 95%)
5. Grid → Demanda (si hace falta)

Este script analiza y propone la corrección.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def analyze_current_calculation():
    """Analiza cómo se está calculando solar_energy_sum actualmente."""

    print("\n" + "="*80)
    print("ANÁLISIS ACTUAL: Cálculo de solar_energy_sum en SAC")
    print("="*80)

    sac_file = Path("src/iquitos_citylearn/oe3/agents/sac.py")
    content = sac_file.read_text(encoding='utf-8')

    # Buscar el cálculo
    if "extracted_solar" in content:
        print("\n✓ Encontrado: extracted_solar calculation")
        print("  - Extrae: b.solar_generation (último valor)")
        print("  - Acumula: self.solar_energy_sum += extracted_solar")
        print("  - PROBLEMA: No filtra por consumo real (EV, BESS, MALL)")
        print("  - PROBLEMA: Cuenta solar_generation DISPONIBLE, no solar USADO")

    print("\nCálculo ACTUAL (incorrecto):")
    print("  solar_energy_sum = suma(solar_generation cada step)")
    print("  ≠ Consumo real según despacho")

    print("\nEjemplo con paso 400:")
    print("  - solar_generation disponible: 248.0 kWh acumulado")
    print("  - Pero puede ser que solo 150 kWh se hayan usado por EV")
    print("  - Y 50 kWh cargaron BESS")
    print("  - Y 48 kWh demanda MALL")
    print("  - Total consumo real: 248 kWh (coincide por causalidad)")
    print("  - PERO la métrica no está reflejando la LÓGICA de despacho")


def propose_correct_calculation():
    """Propone el cálculo correcto."""

    print("\n" + "="*80)
    print("CÁLCULO CORRECTO: Solar consumido según reglas de despacho")
    print("="*80)

    print("\nPseudocódigo para cada step:")
    print("""
    solar_available = current_solar_generation_kw  # [kW/step]

    # 1. PV → EV directamente
    ev_demand = sum(charger.demand for charger in chargers)  # [kW]
    solar_to_ev = min(solar_available, ev_demand)
    solar_remaining = solar_available - solar_to_ev

    # 2. PV → BESS (cargar batería)
    bess_available_power = bess_max_power - current_discharge_power
    bess_soc_margin = (bess_max_soc_percent - current_soc) / 100 * bess_capacity_kwh / discharge_time_hours
    solar_to_bess = min(solar_remaining, bess_available_power, bess_soc_margin)
    solar_remaining = solar_remaining - solar_to_bess

    # 3. PV → MALL demand (demanda del edificio)
    mall_demand = building.net_electricity_consumption  # [kW]
    solar_to_mall = min(solar_remaining, mall_demand)
    solar_remaining = solar_remaining - solar_to_mall

    # 4. Solar excedente → fuera del sistema
    solar_curtailed = solar_remaining

    # MÉTRICAS CORRECTAS:
    solar_consumed_kwh += (solar_to_ev + solar_to_bess + solar_to_mall) * 1h
    solar_curtailed_kwh += solar_curtailed * 1h
    grid_import_kwh += remaining_demand_after_solar * 1h
    """)


def show_data_sources():
    """Muestra dónde obtener cada variable necesaria."""

    print("\n" + "="*80)
    print("FUENTES DE DATOS para cálculo correcto")
    print("="*80)

    print("\nDesde CityLearn environment (env):")
    print("  - env.buildings[0].net_electricity_consumption → demanda neta actual [kW]")
    print("  - env.buildings[0].solar_generation → generación solar disponible [kW]")
    print("  - env.buildings[0].control_space → 129 acciones (1 BESS + 128 chargers)")

    print("\nDesde BESS (battery):")
    print("  - battery.soc → State of Charge actual [%]")
    print("  - battery.max_capacity → 4,520 kWh (inmutable en OE3)")
    print("  - battery.max_power → 2,712 kW (inmutable en OE3)")
    print("  - battery.max_soc_percent → 95% (config)")
    print("  - battery.min_soc_percent → 25.86% (config)")

    print("\nDesde Chargers (128 total):")
    print("  - charger[i].power_demand → demanda actual del charger i [kW]")
    print("  - charger[i].max_power → 2 kW (motos) o 3 kW (mototaxis)")
    print("  - sum(charger[i].power_demand) → demanda total EV [kW]")

    print("\nDesde Config (dispatch_rules):")
    print("  - priority_1_pv_to_ev.ev_power_limit_kw → 150 kW max a EVs")
    print("  - priority_2_pv_to_bess.bess_soc_target_percent → 85%")


def show_implementation_location():
    """Muestra dónde implementar la corrección."""

    print("\n" + "="*80)
    print("UBICACIÓN DE IMPLEMENTACIÓN")
    print("="*80)

    print("\nArchivos a modificar:")
    print("  1. src/iquitos_citylearn/oe3/agents/sac.py (línea ~830)")
    print("     - Reemplazar cálculo simple de extracted_solar")
    print("     - Implementar lógica de despacho completa")

    print("\n  2. src/iquitos_citylearn/oe3/agents/ppo_sb3.py (mismo cambio)")
    print("     - Aplicar el mismo cálculo en step_callback()")

    print("\n  3. src/iquitos_citylearn/oe3/agents/a2c_sb3.py (mismo cambio)")
    print("     - Aplicar el mismo cálculo en step_callback()")

    print("\nNueva estructura de código:")
    print("""
    # Paso 1: Extraer variables necesarias
    buildings = env.buildings if hasattr(env, 'buildings') else []
    if len(buildings) > 0:
        b = buildings[0]
        solar_available_kw = getattr(b, 'solar_generation', [0])[-1] or 0
        ev_demand_kw = sum(charger.power_demand for charger in chargers)
        mall_demand_kw = getattr(b, 'net_electricity_consumption', [0])[-1] or 0
        bess_soc_pct = battery.soc if hasattr(battery, 'soc') else 50

        # Paso 2: Aplicar reglas de despacho
        solar_to_ev = min(solar_available_kw, ev_demand_kw)
        solar_remaining = solar_available_kw - solar_to_ev

        # ... continuar con BESS, MALL ...

        # Paso 3: Acumular solo lo consumido
        total_solar_consumed = solar_to_ev + solar_to_bess + solar_to_mall
        self.solar_energy_sum += total_solar_consumed  # En kWh/paso (1 hora = 1 kWh por 1 kW)
    """)


def show_expected_differences():
    """Muestra qué cambios esperamos ver en los logs."""

    print("\n" + "="*80)
    print("CAMBIOS ESPERADOS en los logs")
    print("="*80)

    print("\nANTES (incorrecto):")
    print("  paso 100: solar_kWh=62.0, grid_kWh=137.0, co2_kg=61.9")
    print("  paso 200: solar_kWh=124.0, grid_kWh=274.0, co2_kg=123.9")
    print("  paso 400: solar_kWh=248.0, grid_kWh=548.0, co2_kg=247.8")
    print("  → solar_kWh = solar_generation disponible (bruto)")

    print("\nDESPUÉS (correcto):")
    print("  paso 100: solar_consumed_kWh=45.0, solar_to_ev_kWh=25.0, solar_to_bess_kWh=15.0, solar_to_mall_kWh=5.0, grid_kWh=92.0, co2_kg=41.6")
    print("  paso 200: solar_consumed_kWh=88.0, solar_to_ev_kWh=50.0, solar_to_bess_kWh=30.0, solar_to_mall_kWh=8.0, grid_kWh=186.0, co2_kg=84.2")
    print("  paso 400: solar_consumed_kWh=172.0, solar_to_ev_kWh=98.0, solar_to_bess_kWh=58.0, solar_to_mall_kWh=16.0, grid_kWh=376.0, co2_kg=170.2")
    print("  → Desglose por uso final")
    print("  → solar_consumed < solar_generation (hay desperdicio/curtailment)")
    print("  → grid_import menor porque solar se consume primero")


def main():
    """Ejecuta el análisis completo."""

    print("\n" * 2)
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "CORRECCIÓN DE CÁLCULO: Solar Consumido vs Solar Disponible".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    analyze_current_calculation()
    propose_correct_calculation()
    show_data_sources()
    show_implementation_location()
    show_expected_differences()

    print("\n" + "="*80)
    print("RESUMEN EJECUTIVO")
    print("="*80)
    print("""
PROBLEMA: solar_energy_sum = solar_generation bruto (no filtra por uso real)

SOLUCIÓN: Implementar cálculo de solar CONSUMIDO según despacho:
  1. Extraer variables (solar_available, ev_demand, mall_demand, bess_soc)
  2. Aplicar reglas de prioridad (PV→EV, PV→BESS, PV→MALL)
  3. Acumular solo lo consumido (no lo disponible)

IMPACTO:
  - Métrica más honesta del desempeño del sistema
  - Muestra cuánto solar realmente se aprovecha vs se desperdicia
  - Ayuda a el agente RL a tomar mejores decisiones

ARCHIVOS A MODIFICAR:
  - src/iquitos_citylearn/oe3/agents/sac.py (línea ~830)
  - src/iquitos_citylearn/oe3/agents/ppo_sb3.py
  - src/iquitos_citylearn/oe3/agents/a2c_sb3.py
    """)

    print("\nPróximo paso: Implementar la corrección")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
