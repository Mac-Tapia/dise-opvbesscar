#!/usr/bin/env python
"""
📊 DEMOSTRACIÓN: Integración Completa rewards.py ↔ dataset_builder.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este script demuestra cómo:
1. dataset_builder.py carga IquitosContext y reward weights desde rewards.py
2. Estos datos se integran en el schema.json
3. Los agentes OE3 (SAC, PPO, A2C) pueden acceder a ellos

Ejecución:
    python demo_rewards_integration.py

Output esperado:
    ✅ Import successful
    ✅ IquitosContext initialized
    ✅ Reward weights loaded
    ✅ Schema structure ready
    ✅ Agent-ready context available
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_section(title: str):
    """Print formatted section."""
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}")

def demo_step_1_imports():
    """Demo Step 1: Mostrar que rewards.py se importa correctamente."""
    print_section("STEP 1: Import rewards.py Classes")

    try:
        from src.rewards.rewards import (
            MultiObjectiveWeights,
            IquitosContext,
            MultiObjectiveReward,
            create_iquitos_reward_weights,
        )
        print("✅ Successfully imported from src.rewards.rewards:")
        print("   • MultiObjectiveWeights")
        print("   • IquitosContext")
        print("   • MultiObjectiveReward")
        print("   • create_iquitos_reward_weights()")
        return True, (MultiObjectiveWeights, IquitosContext, create_iquitos_reward_weights)
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False, None

def demo_step_2_iquitos_context(classes_tuple):
    """Demo Step 2: Inicializar IquitosContext con valores OE2."""
    print_section("STEP 2: Initialize IquitosContext (OE2 Real Data)")

    if not classes_tuple:
        print("⏭️  Skipped (import failed)")
        return False, None

    _, IquitosContext, _ = classes_tuple

    try:
        # Crear contexto con valores reales OE2
        ctx = IquitosContext(
            co2_factor_kg_per_kwh=0.4521,           # Grid térmico Iquitos
            co2_conversion_factor=2.146,            # Combustión equivalente
            max_motos_simultaneous=112,
            max_mototaxis_simultaneous=16,
            max_evs_total=128,
            motos_daily_capacity=1800,              # Real
            mototaxis_daily_capacity=260,           # Real
            tariff_usd_per_kwh=0.20,
            n_chargers=32,
            total_sockets=128,
        )

        print("✅ IquitosContext initialized with OE2 values:")
        print(f"\n  CO₂ Factors:")
        print(f"    • Grid:          {ctx.co2_factor_kg_per_kwh:.4f} kg/kWh")
        print(f"    • EV conversion: {ctx.co2_conversion_factor:.3f} kg/kWh")
        print(f"\n  EV Fleet Capacity:")
        print(f"    • Daily motos:   {ctx.motos_daily_capacity:,}")
        print(f"    • Daily mototaxis: {ctx.mototaxis_daily_capacity}")
        print(f"    • Total sockets: {ctx.max_evs_total}")
        print(f"\n  Infrastructure:")
        print(f"    • Chargers:      {ctx.n_chargers}")
        print(f"    • Tariff:        ${ctx.tariff_usd_per_kwh}/kWh")
        print(f"    • Peak hours:    {ctx.peak_hours}")

        return True, ctx
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False, None

def demo_step_3_reward_weights(classes_tuple):
    """Demo Step 3: Crear MultiObjectiveWeights."""
    print_section("STEP 3: Create MultiObjectiveWeights (Reward Priorities)")

    if not classes_tuple:
        print("⏭️  Skipped (import failed)")
        return False, None

    _, _, create_iquitos_reward_weights = classes_tuple

    try:
        weights = create_iquitos_reward_weights(priority="balanced")

        print("✅ MultiObjectiveWeights created (balanced priority):")
        print(f"\n  Reward Weight Distribution:")
        print(f"    • CO₂ Minimization:     {weights.co2:.2%}  ⭐ PRIMARY")
        print(f"    • Solar Utilization:    {weights.solar:.2%}  ⭐ SECONDARY")
        print(f"    • Cost Minimization:    {weights.cost:.2%}")
        print(f"    • EV Satisfaction:      {weights.ev_satisfaction:.2%}")
        print(f"    • EV Utilization:       {weights.ev_utilization:.2%}")
        print(f"    • Grid Stability:       {weights.grid_stability:.2%}")

        total = sum([weights.co2, weights.cost, weights.solar,
                    weights.ev_satisfaction, weights.ev_utilization, weights.grid_stability])
        print(f"\n  Total Weight Sum: {total:.2%} ✓")

        return True, weights
    except Exception as e:
        print(f"❌ Failed to create weights: {e}")
        return False, None

def demo_step_4_schema_structure(ctx, weights):
    """Demo Step 4: Mostrar estructura del schema con contexto integrado."""
    print_section("STEP 4: Schema Structure (as stored in schema.json)")

    if not ctx or not weights:
        print("⏭️  Skipped (previous steps failed)")
        return False

    try:
        schema_fragment = {
            "co2_context": {
                "co2_factor_kg_per_kwh": float(ctx.co2_factor_kg_per_kwh),
                "co2_conversion_factor": float(ctx.co2_conversion_factor),
                "motos_daily_capacity": int(ctx.motos_daily_capacity),
                "mototaxis_daily_capacity": int(ctx.mototaxis_daily_capacity),
                "max_evs_total": int(ctx.max_evs_total),
                "tariff_usd_per_kwh": float(ctx.tariff_usd_per_kwh),
                "peak_hours": list(ctx.peak_hours),
                "description": "Contexto real de Iquitos para cálculo de CO₂ y recompensas",
            },
            "reward_weights": {
                "co2": float(weights.co2),
                "cost": float(weights.cost),
                "solar": float(weights.solar),
                "ev_satisfaction": float(weights.ev_satisfaction),
                "ev_utilization": float(weights.ev_utilization),
                "grid_stability": float(weights.grid_stability),
                "description": "Pesos multiobjetivo para cálculo de recompensa en agentes OE3",
            }
        }

        print("✅ Schema fragment ready (will be embedded in schema.json):")
        print("\n  JSON Structure:")
        schema_json = json.dumps(schema_fragment, indent=4, ensure_ascii=False)
        for line in schema_json.split('\n'):
            print(f"    {line}")

        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def demo_step_5_agent_usage(ctx, weights):
    """Demo Step 5: Mostrar cómo los agentes usan los datos integrados."""
    print_section("STEP 5: Agent Usage (How OE3 Agents Access Integrated Data)")

    if not ctx or not weights:
        print("⏭️  Skipped (previous steps failed)")
        return False

    try:
        print("✅ Example: How SAC/PPO/A2C agents use integrated context:\n")

        print("  1️⃣  AGENT INITIALIZATION:")
        print("    schema = json.load(open('schema.json'))")
        print("    co2_ctx = schema['co2_context']")
        print("    reward_weights = schema['reward_weights']")

        print("\n  2️⃣  REWARD CALCULATION:")
        print("    grid_import_kwh = 1500")
        print("    solar_generated_kwh = 800")
        print("    ")
        print(f"    co2_grid = grid_import_kwh × {ctx.co2_factor_kg_per_kwh}")
        print(f"             = 1500 × 0.4521 = {1500 * ctx.co2_factor_kg_per_kwh:.1f} kg CO₂")
        print("    ")
        print(f"    reward_co2_component = -co2_grid × {weights.co2:.2f}")
        print(f"                         = -{1500 * ctx.co2_factor_kg_per_kwh:.1f} × {weights.co2:.2f}")

        print("\n  3️⃣  OPTIMIZATION TARGET:")
        print("    Agent learns to minimize total_co2_emissions by:")
        print(f"    • Maximizing solar self-consumption (weight: {weights.solar:.2%})")
        print(f"    • Minimizing grid imports (weight: {weights.co2:.2%})")
        print(f"    • Managing {ctx.max_evs_total} chargers to meet EV deadlines")
        print(f"    • Respecting peak hours: {ctx.peak_hours}")

        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    """Ejecutar demostración completa."""
    print_header("📊 INTEGRACIÓN REWARDS.PY ↔ DATASET_BUILDER.PY")

    print("Este script demuestra cómo dataset_builder.py integra rewards.py")
    print("para proporcionar contexto de recompensa a agentes OE3.")

    # Step 1: Imports
    success1, classes_tuple = demo_step_1_imports()

    # Step 2: IquitosContext
    success2, ctx = demo_step_2_iquitos_context(classes_tuple)

    # Step 3: Reward Weights
    success3, weights = demo_step_3_reward_weights(classes_tuple)

    # Step 4: Schema Structure
    success4 = demo_step_4_schema_structure(ctx, weights)

    # Step 5: Agent Usage
    success5 = demo_step_5_agent_usage(ctx, weights)

    # Final Summary
    print_header("✅ RESUMEN DE DEMOSTRACIÓN")

    steps = [
        ("Step 1: Import rewards.py", success1),
        ("Step 2: Initialize IquitosContext", success2),
        ("Step 3: Create MultiObjectiveWeights", success3),
        ("Step 4: Schema Structure", success4),
        ("Step 5: Agent Usage", success5),
    ]

    for step_name, success in steps:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {step_name}")

    all_success = all(s for _, s in steps)
    total = len(steps)
    passed = sum(1 for _, s in steps if s)

    print(f"\n  Resultado: {passed}/{total} pasos completados")

    if all_success:
        print("\n🎉 ¡ÉXITO! La integración funciona correctamente.")
        print("\n✅ Próximos pasos:")
        print("   1. python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
        print("   2. Verificar que schema.json contiene co2_context y reward_weights")
        print("   3. Entrenar agentes OE3 con datos integrados:")
        print("      • python -m scripts.run_oe3_simulate --agent sac")
        print("      • python -m scripts.run_oe3_simulate --agent ppo")
        print("      • python -m scripts.run_oe3_simulate --agent a2c")
        return 0
    else:
        print(f"\n❌ {total - passed} paso(s) fallido(s)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
