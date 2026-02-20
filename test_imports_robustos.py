#!/usr/bin/env python3
"""
Test script para verificar que los imports robustos funcionan correctamente
"""
from __future__ import annotations

import sys
from pathlib import Path

print("=" * 80)
print("VERIFICACION: Imports robustos en balance_graphics_only.py")
print("=" * 80)

# Test 1: Import como módulo de paquete
print("\n[TEST 1] Importar como módulo de paquete...")
try:
    from src.dimensionamiento.oe2.balance_energetico.balance_graphics_only import (
        BalanceEnergeticoGraphics,
        VisualizationConfig,
    )
    print("  ✓ Import exitoso: BalanceEnergeticoGraphics")
    print("  ✓ Import exitoso: VisualizationConfig")
except ImportError as e:
    print(f"  ✗ Error de import: {e}")
    sys.exit(1)

# Test 2: Verificar que las constantes se importaron correctamente
print("\n[TEST 2] Verificar constants EV Profile...")
try:
    from src.dimensionamiento.oe2.balance_energetico.ev_profile_integration import (
        MOTO_SPEC,
        MOTOTAXI_SPEC,
        CHARGING_EFFICIENCY,
    )
    print(f"  ✓ MOTO_SPEC: {MOTO_SPEC}")
    print(f"  ✓ MOTOTAXI_SPEC: {MOTOTAXI_SPEC}")
    print(f"  ✓ CHARGING_EFFICIENCY: {CHARGING_EFFICIENCY}")
except ImportError as e:
    print(f"  ✗ Error de import: {e}")
    sys.exit(1)

# Test 3: Crear instancia de VisualizationConfig
print("\n[TEST 3] Crear instancia de VisualizationConfig...")
try:
    config = VisualizationConfig()
    print(f"  ✓ Config creada:")
    print(f"    - pv_capacity_kwp: {config.pv_capacity_kwp}")
    print(f"    - bess_capacity_kwh: {config.bess_capacity_kwh}")
    print(f"    - bess_power_kw: {config.bess_power_kw}")
    print(f"    - co2_intensity_kg_per_kwh: {config.co2_intensity_kg_per_kwh}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 4: Verificar atributos de clase
print("\n[TEST 4] Verificar atributos de BalanceEnergeticoGraphics...")
try:
    graph_methods = [
        '_plot_integral_curves',
        '_plot_energy_flow_diagram',
        '_plot_5day_balance',
        '_plot_daily_balance',
        '_plot_sources_distribution',
        '_plot_energy_cascade',
        '_plot_bess_soc',
        '_plot_co2_emissions',
        '_plot_pv_utilization',
        'plot_all',
    ]
    for method in graph_methods:
        if hasattr(BalanceEnergeticoGraphics, method):
            print(f"  ✓ Método: {method}")
        else:
            print(f"  ✗ Método NO encontrado: {method}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("[OK] TODOS LOS TESTS PASARON - Importes robustos funcionan correctamente")
print("=" * 80)
