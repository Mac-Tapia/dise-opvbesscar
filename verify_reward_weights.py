#!/usr/bin/env python3
"""
VERIFICACIÓN DE PESOS DE RECOMPENSA ACTUALIZADO
Validar que los pesos sumen 1.0 y reflejen prioridades documentadas.
"""

import sys
sys.path.insert(0, '/d/diseñopvbesscar')

from src.rewards.rewards import MultiObjectiveWeights

print("=" * 80)
print("VERIFICACIÓN DE PESOS DE RECOMPENSA")
print("=" * 80)
print()

# Crear con nuevos pesos
weights = MultiObjectiveWeights()

print("[NUEVOS PESOS - 2026-02-05]")
print("-" * 80)
print(f"  co2: {weights.co2:.2f}              (ERA 0.50 → {weights.co2} [REDUCIDO])")
print(f"  cost: {weights.cost:.2f}            (ERA 0.15 → {weights.cost} [REDUCIDO])")
print(f"  solar: {weights.solar:.2f}          (MANTENER)")
print(f"  ev_satisfaction: {weights.ev_satisfaction:.2f}     (ERA 0.10 → {weights.ev_satisfaction} [TRIPLICADO] ✅)")
print(f"  ev_utilization: {weights.ev_utilization:.2f}    (MANTENER)")
print(f"  grid_stability: {weights.grid_stability:.2f}     (MANTENER)")
print()

# Verificar suma
total = (weights.co2 + weights.cost + weights.solar +
         weights.ev_satisfaction + weights.ev_utilization + weights.grid_stability)
print(f"💾 Suma de pesos: {total:.4f}")
print()

if abs(total - 1.0) < 0.01:
    print("✅ PESOS NORMALIZADOS CORRECTAMENTE (suma ≈ 1.0)")
else:
    print(f"⚠️  ADVERTENCIA: Suma != 1.0 ({total:.4f})")
    print("   (Se normalizará automáticamente en __post_init__)")
print()

print("[IMPACTO EN COMPORTAMIENTO DEL AGENTE]")
print("-" * 80)
print()
print("✅ Con ev_satisfaction = 0.30 (TRIPLICADO):")
print("   - Agente priorizará CARGAR EVs a SOC máximo (90%+)")
print("   - Penalizará fuertemente si EVs < 80% SOC")
print("   - Urgencia extrema en últimas horas (20-21h, cierre)")
print()
print("✅ Con co2 = 0.35 (REDUCIDO de 0.50):")
print("   - No sobre-penalizará minimizar grid a costa de EVs")
print("   - Mejor balance entre CO₂ grid y carga EV")
print()
print("✅ Con cost = 0.10 (REDUCIDO de 0.15):")
print("   - Tarifa baja (0.20 USD/kWh) no es limiting factor")
print()

print()
print("[COMPARACIÓN ANTES vs DESPUÉS]")
print("-" * 80)
print()
print(f"{'Métrica':<25} {'ANTES':<20} {'DESPUÉS':<20}")
print("-" * 80)
print(f"{'CO₂ PRIMARY':<25} {'0.50 (50%)':<20} {f'{weights.co2:.2f} (35%)':<20}")
print(f"{'EV SATISFACTION':<25} {'0.10 (10%)':<20} {f'{weights.ev_satisfaction:.2f} (30%)':<20}")
print(f"{'EV PRIORITIZATION':<25} {'BAJA':<20} {'MÁXIMA (3x)':<20}")
print()

print("[PRÓXIMOS PASOS]")
print("-" * 80)
print()
print("1. ✅ Pesos actualizados en MultiObjectiveWeights")
print("2. ⏳ Falta: Validar en entrenamiento SAC (100 steps)")
print("3. ⏳ Falta: Comparar rewards contra baseline (sin RL)")
print("4. ⏳ Falta: Verificar CO₂ directo vs. indirecto")
print()

as_dict = {
    'co2': weights.co2,
    'cost': weights.cost,
    'solar': weights.solar,
    'ev_satisfaction': weights.ev_satisfaction,
    'ev_utilization': weights.ev_utilization,
    'grid_stability': weights.grid_stability,
}

print("[JSON SERIALIZABLE]")
print("-" * 80)
import json
print(json.dumps(as_dict, indent=2))

print()
print("=" * 80)
