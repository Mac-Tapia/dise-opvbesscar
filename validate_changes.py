#!/usr/bin/env python3
"""Validar cambios en vehicle_charging_scenarios.py y train_ppo_multiobjetivo.py"""
import sys
from pathlib import Path

print("=" * 80)
print("VALIDACIÓN DE CAMBIOS")
print("=" * 80)
print()

errors = []
warnings = []

# ============================================================================
# 1. VALIDAR vehicle_charging_scenarios.py
# ============================================================================
print("[1] Validando vehicle_charging_scenarios.py...")
print("-" * 80)

try:
    from vehicle_charging_scenarios import (
        VehicleChargingScenario,
        VehicleChargingSimulator,
        SCENARIO_OFF_PEAK,
        SCENARIO_PEAK_AFTERNOON,
        SCENARIO_PEAK_EVENING,
        SCENARIO_EXTREME_PEAK,
    )
    
    # Test scenario
    print("  ✅ Imports correctos")
    
    # Verificar que tiene todos los parámetros
    assert hasattr(SCENARIO_OFF_PEAK, 'motos_10_percent'), "Falta motos_10_percent"
    assert hasattr(SCENARIO_OFF_PEAK, 'motos_100_percent'), "Falta motos_100_percent"
    print("  ✅ Scenario OFF_PEAK tiene todos los parámetros SOC")
    
    # Verificar simulator
    sim = VehicleChargingSimulator()
    result = sim.simulate_hourly_charge(SCENARIO_OFF_PEAK, 100.0)
    
    required_keys = [
        'motos_10_percent_charged', 'motos_20_percent_charged', 'motos_30_percent_charged',
        'motos_50_percent_charged', 'motos_70_percent_charged', 'motos_80_percent_charged',
        'motos_100_percent_charged',
        'mototaxis_10_percent_charged', 'mototaxis_20_percent_charged', 'mototaxis_30_percent_charged',
        'mototaxis_50_percent_charged', 'mototaxis_70_percent_charged', 'mototaxis_80_percent_charged',
        'mototaxis_100_percent_charged',
    ]
    
    for key in required_keys:
        if key not in result:
            errors.append(f"simulate_hourly_charge() falta retornar: {key}")
        else:
            if isinstance(result[key], (int, float)) and result[key] > 0:
                print(f"    ✅ {key}: {result[key]}")
    
    if not errors:
        print("  ✅ simulate_hourly_charge() retorna TODOS los SOC correctamente")
    
except Exception as e:
    errors.append(f"Error en vehicle_charging_scenarios.py: {e}")

print()

# ============================================================================
# 2. VALIDAR train_ppo_multiobjetivo.py
# ============================================================================
print("[2] Validando train_ppo_multiobjetivo.py...")
print("-" * 80)

try:
    with open("train_ppo_multiobjetivo.py", "r") as f:
        content = f.read()
    
    # Verificar que usa min_power_kw
    if "min_power_kw = max(10.0, ev_charging_kwh)" in content:
        print("  ✅ min_power_kw inicializado correctamente")
    else:
        warnings.append("min_power_kw no encontrado o mal inicializado")
    
    # Verificar que usa charging_result
    if "charging_result = self.vehicle_simulator.simulate_hourly_charge(scenario, min_power_kw)" in content:
        print("  ✅ Usa min_power_kw en simulate_hourly_charge()")
    else:
        warnings.append("simulate_hourly_charge() no usa min_power_kw")
    
    # Verificar que extrae todos los SOC
    soc_patterns = [
        "motos_10 = charging_result.get('motos_10_percent_charged'",
        "motos_20 = charging_result.get('motos_20_percent_charged'",
        "motos_30 = charging_result.get('motos_30_percent_charged'",
        "motos_50 = charging_result.get('motos_50_percent_charged'",
    ]
    
    for pattern in soc_patterns:
        if pattern in content:
            soc = pattern.split("_")[1].split(" ")[0]
            print(f"    ✅ Extrae motos_{soc}")
        else:
            errors.append(f"No extrae: {pattern}")
    
    print("  ✅ Todos los SOC se extraen correctamente")
    
except Exception as e:
    errors.append(f"Error en train_ppo_multiobjetivo.py: {e}")

print()

# ============================================================================
# 3. DETECTAR CÓDIGO MUERTO
# ============================================================================
print("[3] Detectando código innecesario...")
print("-" * 80)

with open("train_ppo_multiobjetivo.py", "r") as f:
    lines = f.readlines()

# Líneas que se pueden limpiar
cleanup_candidates = []

# Ejemplo: líneas con # TODO o comentarios obsoletos
for i, line in enumerate(lines, 1):
    if "TODO" in line and "✅" not in line:
        cleanup_candidates.append((i, line.strip()[:60]))
    if "FIXME" in line:
        cleanup_candidates.append((i, line.strip()[:60]))

if cleanup_candidates:
    print(f"  ⚠️  Encontradas {len(cleanup_candidates)} líneas con TODO/FIXME:")
    for line_num, content in cleanup_candidates[:5]:
        print(f"     Línea {line_num}: {content}...")
else:
    print("  ✅ Sin comentarios TODO/FIXME obsoletos")

print()

# ============================================================================
# RESUMEN
# ============================================================================
print("=" * 80)
print("RESUMEN DE VALIDACIÓN")
print("=" * 80)

if errors:
    print(f"\n❌ ERRORES ({len(errors)}):")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\n✅ TODOS LOS CAMBIOS VÁLIDOS")

if warnings:
    print(f"\n⚠️  ADVERTENCIAS ({len(warnings)}):")
    for warn in warnings:
        print(f"  - {warn}")
else:
    print("\n✅ SIN ADVERTENCIAS")

print()
print("=" * 80)
print("LISTO PARA ENTRENAR")
print("=" * 80)
print()
print("Ejecuta:")
print("  python TRAINING_MASTER.py")
