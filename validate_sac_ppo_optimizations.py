#!/usr/bin/env python
"""
VALIDACIÓN EXHAUSTIVA: SAC + PPO Optimizations
Verifica que los 21 cambios estén correctamente implementados
ANTES de reentrenar.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.iquitos_citylearn.oe3.agents.sac import SACConfig
from src.iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig

def check_sac_optimizations() -> dict:
    """Validar 9 cambios SAC."""
    print("\n" + "="*80)
    print("🔍 VALIDACIÓN SAC - 9 CAMBIOS ESPERADOS")
    print("="*80)

    config = SACConfig()
    results = {}

    checks = [
        ("buffer_size", 100000, config.buffer_size, "Buffer 10x mayor (reduce contamination)"),
        ("learning_rate", 5e-5, config.learning_rate, "LR 4x menor (mejor convergencia)"),
        ("tau", 0.01, config.tau, "Tau 10x mayor (gradual updates)"),
        ("hidden_sizes[0]", 512, config.hidden_sizes[0], "Network 2x capacity para 126 acciones"),
        ("batch_size", 256, config.batch_size, "Batch 4x mayor (stable gradients)"),
        ("ent_coef", "auto", config.ent_coef, "Entropy adaptativo (auto-tune)"),
        ("max_grad_norm", 1.0, config.max_grad_norm, "Gradient clipping (prevent divergence)"),
        ("use_prioritized_replay", True, config.use_prioritized_replay, "PER enabled (focus important)"),
        ("lr_schedule", "linear", config.lr_schedule, "Linear LR decay (smooth convergence)"),
    ]

    for i, (name, expected, actual, description) in enumerate(checks, 1):
        status = "✅" if actual == expected else "❌"
        results[name] = actual == expected

        print(f"\n{status} CAMBIO {i}: {name}")
        print(f"   Descripción: {description}")
        print(f"   Esperado: {expected}")
        print(f"   Actual:   {actual}")

        if actual != expected:
            print(f"   ⚠️  ERROR: Valor no coincide!")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n{'─'*80}")
    print(f"SAC: {passed}/{total} cambios correctos")

    return results

def check_ppo_optimizations() -> dict:
    """Validar 12 cambios PPO."""
    print("\n" + "="*80)
    print("🔍 VALIDACIÓN PPO - 12 CAMBIOS ESPERADOS")
    print("="*80)

    config = PPOConfig()
    results = {}

    checks = [
        ("n_steps", 8760, config.n_steps, "⭐ FULL EPISODE (ver causal chains completas!)"),
        ("clip_range", 0.5, config.clip_range, "Clip 2.5x mayor (policy flexibility)"),
        ("clip_range_vf", 0.5, config.clip_range_vf, "VF clip 2.5x (value stability)"),
        ("batch_size", 256, config.batch_size, "Batch 4x mayor (stable gradients)"),
        ("n_epochs", 10, config.n_epochs, "Epochs 5x mayor (more training passes)"),
        ("learning_rate", 1e-4, config.learning_rate, "LR 2x mayor (balance con clip)"),
        ("max_grad_norm", 1.0, config.max_grad_norm, "Gradient clipping (safety)"),
        ("ent_coef", 0.01, config.ent_coef, "Entropy 10x mayor (exploration)"),
        ("normalize_advantage", True, config.normalize_advantage, "Advantage normalization (consistency)"),
        ("use_sde", True, config.use_sde, "State-dependent exploration (enabled)"),
        ("target_kl", 0.02, config.target_kl, "KL safety limit (0.02)"),
        ("gae_lambda", 0.98, config.gae_lambda, "GAE lambda 0.98 (long-term advantages)"),
    ]

    for i, (name, expected, actual, description) in enumerate(checks, 1):
        status = "✅" if actual == expected else "❌"
        results[name] = actual == expected

        print(f"\n{status} CAMBIO {i}: {name}")
        print(f"   Descripción: {description}")
        print(f"   Esperado: {expected}")
        print(f"   Actual:   {actual}")

        if actual != expected:
            print(f"   ⚠️  ERROR: Valor no coincide!")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n{'─'*80}")
    print(f"PPO: {passed}/{total} cambios correctos")

    return results

def check_multi_objective() -> dict:
    """Validar pesos multi-objetivo."""
    print("\n" + "="*80)
    print("🎯 VALIDACIÓN MULTI-OBJETIVO")
    print("="*80)

    sac_config = SACConfig()
    ppo_config = PPOConfig()
    results = {}

    # SAC weights
    sac_weights = {
        "weight_co2": sac_config.weight_co2,
        "weight_solar": sac_config.weight_solar,
        "weight_cost": sac_config.weight_cost,
        "weight_ev_satisfaction": sac_config.weight_ev_satisfaction,
        "weight_grid_stability": sac_config.weight_grid_stability,
    }
    sac_total = sum(sac_weights.values())

    print(f"\nSAC Weights (suma debe ser 1.0):")
    for k, v in sac_weights.items():
        print(f"  {k}: {v}")
    print(f"  SUMA: {sac_total}")
    results["sac_weights_sum"] = 0.99 <= sac_total <= 1.01  # Allow small float error

    # PPO weights (should be same)
    ppo_weights = {
        "weight_co2": ppo_config.weight_co2,
        "weight_solar": ppo_config.weight_solar,
        "weight_cost": ppo_config.weight_cost,
        "weight_ev_satisfaction": ppo_config.weight_ev_satisfaction,
        "weight_grid_stability": ppo_config.weight_grid_stability,
    }
    ppo_total = sum(ppo_weights.values())

    print(f"\nPPO Weights (suma debe ser 1.0):")
    for k, v in ppo_weights.items():
        print(f"  {k}: {v}")
    print(f"  SUMA: {ppo_total}")
    results["ppo_weights_sum"] = 0.99 <= ppo_total <= 1.01

    status_sac = "✅" if results["sac_weights_sum"] else "❌"
    status_ppo = "✅" if results["ppo_weights_sum"] else "❌"

    print(f"\n{status_sac} SAC multi-objetivo: VÁLIDO" if results["sac_weights_sum"] else f"❌ SAC: INVÁLIDO (suma={sac_total})")
    print(f"{status_ppo} PPO multi-objetivo: VÁLIDO" if results["ppo_weights_sum"] else f"❌ PPO: INVÁLIDO (suma={ppo_total})")

    return results

def check_numerical_stability() -> dict:
    """Validar estabilidad numérica."""
    print("\n" + "="*80)
    print("🔢 VALIDACIÓN ESTABILIDAD NUMÉRICA")
    print("="*80)

    sac_config = SACConfig()
    ppo_config = PPOConfig()
    results = {}

    # SAC stability checks
    print(f"\nSAC Estabilidad Numérica:")

    checks_sac = [
        ("clip_gradients", True, sac_config.clip_gradients, "Gradient clipping habilitado"),
        ("max_grad_norm > 0", True, sac_config.max_grad_norm > 0, f"max_grad_norm={sac_config.max_grad_norm}"),
        ("learning_rate <= 1e-4", True, sac_config.learning_rate <= 1e-4, f"lr={sac_config.learning_rate}"),
        ("warmup_steps > 0", True, sac_config.warmup_steps > 0, f"warmup={sac_config.warmup_steps}"),
    ]

    for name, expected, actual, description in checks_sac:
        status = "✅" if actual == expected else "❌"
        results[f"sac_{name}"] = actual == expected
        print(f"  {status} {name}: {actual} ({description})")

    # PPO stability checks
    print(f"\nPPO Estabilidad Numérica:")

    checks_ppo = [
        ("max_grad_norm > 0", True, ppo_config.max_grad_norm > 0, f"max_grad_norm={ppo_config.max_grad_norm}"),
        ("learning_rate <= 1e-4", True, ppo_config.learning_rate <= 1e-4, f"lr={ppo_config.learning_rate}"),
        ("normalize_advantage", True, ppo_config.normalize_advantage, "Advantage normalization"),
        ("target_kl > 0", True, ppo_config.target_kl > 0 if ppo_config.target_kl else False, f"target_kl={ppo_config.target_kl}"),
    ]

    for name, expected, actual, description in checks_ppo:
        status = "✅" if actual == expected else "❌"
        results[f"ppo_{name}"] = actual == expected
        print(f"  {status} {name}: {actual} ({description})")

    return results

def check_temporal_context() -> dict:
    """Validar temporal context."""
    print("\n" + "="*80)
    print("⏱️  VALIDACIÓN CONTEXTO TEMPORAL")
    print("="*80)

    ppo_config = PPOConfig()
    results = {}

    print(f"\nPPO n_steps (Trajectory horizon):")
    print(f"  Valor: {ppo_config.n_steps}")
    print(f"  Esperado: 8760 (= full episode de 365 días × 24 horas)")
    print(f"  Beneficio: Agente ve mediodía (carga BESS) → noche (usa BESS) causality completa")

    results["ppo_n_steps"] = ppo_config.n_steps == 8760

    if ppo_config.n_steps == 8760:
        print(f"\n✅ TEMPORAL CONTEXT: CORRECTO")
        print(f"   PPO puede ver:")
        print(f"   • 09:00 - Inicio: Demanda empieza")
        print(f"   • 12:00 - Pico solar: Decidir cargar BESS")
        print(f"   • 18:00 - Pico demanda: Usar BESS cargado")
        print(f"   • 22:00 - Cierre: Evaluación completa")
    else:
        print(f"\n❌ TEMPORAL CONTEXT: ERROR")
        print(f"   n_steps={ppo_config.n_steps} no permite ver cadena causal completa")

    return results

def check_exploration_capacity() -> dict:
    """Validar capacidad de exploración para 126 dimensiones."""
    print("\n" + "="*80)
    print("🔍 VALIDACIÓN EXPLORACIÓN (126D ACTION SPACE)")
    print("="*80)

    sac_config = SACConfig()
    ppo_config = PPOConfig()
    results = {}

    # SAC exploration
    print(f"\nSAC Exploración:")
    print(f"  hidden_sizes: {sac_config.hidden_sizes}")
    print(f"  Esperado: (512, 512) para 126 acciones")
    print(f"  ent_coef: {sac_config.ent_coef}")
    print(f"  Esperado: 'auto' (adaptive entropy)")
    print(f"  use_prioritized_replay: {sac_config.use_prioritized_replay}")
    print(f"  Esperado: True (focus on important transitions)")

    results["sac_hidden"] = sac_config.hidden_sizes == (512, 512)
    results["sac_entropy"] = sac_config.ent_coef == "auto" or isinstance(sac_config.ent_coef, str)
    results["sac_per"] = sac_config.use_prioritized_replay == True

    sac_ok = all([results["sac_hidden"], results["sac_entropy"], results["sac_per"]])
    status_sac = "✅" if sac_ok else "❌"

    print(f"\n  {status_sac} SAC Exploración: {'VÁLIDA' if sac_ok else 'INCOMPLETA'}")

    # PPO exploration
    print(f"\nPPO Exploración:")
    print(f"  hidden_sizes: {ppo_config.hidden_sizes}")
    print(f"  Esperado: (256, 256) [menor que SAC pero suficiente]")
    print(f"  use_sde: {ppo_config.use_sde}")
    print(f"  Esperado: True (state-dependent exploration)")
    print(f"  ent_coef: {ppo_config.ent_coef}")
    print(f"  Esperado: 0.01 (exploration incentive)")

    results["ppo_hidden"] = ppo_config.hidden_sizes == (256, 256)
    results["ppo_sde"] = ppo_config.use_sde == True
    results["ppo_entropy"] = ppo_config.ent_coef == 0.01

    ppo_ok = all([results["ppo_hidden"], results["ppo_sde"], results["ppo_entropy"]])
    status_ppo = "✅" if ppo_ok else "❌"

    print(f"\n  {status_ppo} PPO Exploración: {'VÁLIDA' if ppo_ok else 'INCOMPLETA'}")

    return results

def main() -> int:
    """Ejecutar validación completa."""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "VALIDACIÓN EXHAUSTIVA: SAC + PPO OPTIMIZATIONS".center(78) + "║")
    print("║" + "21 cambios (9 SAC + 12 PPO) antes de reentrenar".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "═"*78 + "╝")

    all_results = {}

    # Run all validations
    all_results["sac_changes"] = check_sac_optimizations()
    all_results["ppo_changes"] = check_ppo_optimizations()
    all_results["multi_objective"] = check_multi_objective()
    all_results["numerical_stability"] = check_numerical_stability()
    all_results["temporal_context"] = check_temporal_context()
    all_results["exploration"] = check_exploration_capacity()

    # Summary
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL")
    print("="*80)

    all_checks = {}
    for category, checks in all_results.items():
        all_checks[category] = checks

    # Flatten and count
    total_checks = 0
    passed_checks = 0

    for category, results in all_checks.items():
        if isinstance(results, dict):
            for check, result in results.items():
                total_checks += 1
                if result:
                    passed_checks += 1

    print(f"\n✅ Checks pasados: {passed_checks}/{total_checks}")

    # Overall status
    if passed_checks == total_checks:
        print("\n" + "🟢 " * 20)
        print("\n✅ VALIDACIÓN EXITOSA: Todos los 21 cambios están correctamente implementados")
        print("✅ SAC y PPO están listos para reentrenamiento")
        print("✅ Configuraciones óptimas y robustas verificadas")
        print("\n" + "🟢 " * 20)
        return 0
    else:
        missing = total_checks - passed_checks
        print(f"\n" + "🔴 " * 20)
        print(f"\n❌ VALIDACIÓN FALLIDA: {missing} checks fallaron")
        print("⚠️  Revisar los cambios antes de reentrenar")
        print("\n" + "🔴 " * 20)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
