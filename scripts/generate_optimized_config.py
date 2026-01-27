#!/usr/bin/env python3
"""
Script para generar configs/default_optimized.yaml con hiperparámetros justificados.
Basado en papers SAC, PPO, A2C y best practices Stable Baselines3.
"""
from __future__ import annotations

import yaml
from pathlib import Path

def main() -> None:
    """Lee config actual y genera versión optimizada con cambios sugeridos."""

    config_path = Path("configs/default.yaml")

    # Leer configuración actual
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # CAMBIOS OPTIMIZADOS - Justificados en docs/HYPERPARAMETERS_JUSTIFICATION.md

    # 1. SAC Optimizado (off-policy, sample-efficient)
    print("[SAC] Aplicando optimizaciones...")
    cfg["oe3"]["evaluation"]["sac"]["learning_rate_actor"] = 0.001  # Mantener
    cfg["oe3"]["evaluation"]["sac"]["learning_rate_critic"] = 0.0025  # ↑ de 0.002
    cfg["oe3"]["evaluation"]["sac"]["tau"] = 0.005  # ↓ de 0.01 (soft update más rápido)
    cfg["oe3"]["evaluation"]["sac"]["buffer_size"] = 20000000  # ↑ de 10M (duplicar)
    cfg["oe3"]["evaluation"]["sac"]["entropy_coef_init"] = 0.1  # ↓ de 0.2 (menos random inicial)
    cfg["oe3"]["evaluation"]["sac"]["episodes"] = 5  # ↑ de 3
    cfg["oe3"]["evaluation"]["sac"]["gradient_steps"] = 2048  # Mantener
    print("  ✓ Critic LR aumentado 25% (0.002→0.0025)")
    print("  ✓ Tau reducido 50% (0.01→0.005) para updates más rápidas")
    print("  ✓ Buffer duplicado (10M→20M) para mejor Q-estimation")
    print("  ✓ Entropía inicial reducida 50% (0.2→0.1, pero learnable)")
    print("  ✓ Episodes aumentados (3→5)")

    # 2. PPO Optimizado (on-policy, estable)
    print("\n[PPO] Aplicando optimizaciones...")
    cfg["oe3"]["evaluation"]["ppo"]["learning_rate"] = 0.0005  # ↑ de 0.0003 (67% más)
    cfg["oe3"]["evaluation"]["ppo"]["n_steps"] = 8192  # ↑ de 4096 (duplicar, 1 episodio full)
    cfg["oe3"]["evaluation"]["ppo"]["n_epochs"] = 20  # ↓ de 25 (20% menos overfitting)
    cfg["oe3"]["evaluation"]["ppo"]["ent_coef"] = 0.002  # ↑ de 0.001 (duplicar exploración)
    cfg["oe3"]["evaluation"]["ppo"]["gae_lambda"] = 0.98  # ↑ de 0.95 (más estabilidad)
    cfg["oe3"]["evaluation"]["ppo"]["episodes"] = 5  # ↑ de 3
    print("  ✓ Learning rate aumentado 67% (0.0003→0.0005) para convergencia multi-objetivo")
    print("  ✓ N-steps duplicado (4096→8192) para GAE estimation perfecto")
    print("  ✓ N-epochs reducido 20% (25→20) para evitar overfitting")
    print("  ✓ Entropy aumentado 100% (0.001→0.002) para mejor exploración")
    print("  ✓ GAE lambda aumentado (0.95→0.98) para estabilidad")
    print("  ✓ Episodes aumentados (3→5)")

    # 3. A2C Optimizado (on-policy, reactivo)
    print("\n[A2C] Aplicando optimizaciones...")
    cfg["oe3"]["evaluation"]["a2c"]["learning_rate"] = 0.003  # ↑ de 0.002 (50% más)
    cfg["oe3"]["evaluation"]["a2c"]["n_steps"] = 8  # ↓ de 16 (50% menos, updates 2× frecuentes)
    cfg["oe3"]["evaluation"]["a2c"]["entropy_coef"] = 0.03  # ↑ de 0.02 (50% más)
    cfg["oe3"]["evaluation"]["a2c"]["gae_lambda"] = 0.92  # ↑ de 0.9 (más ventaja estable)
    cfg["oe3"]["evaluation"]["a2c"]["episodes"] = 5  # ↑ de 3
    print("  ✓ Learning rate aumentado 50% (0.002→0.003) para convergencia rápida")
    print("  ✓ N-steps reducido 50% (16→8) para updates 2× más frecuentes (~1 min real)")
    print("  ✓ Entropy aumentado 50% (0.02→0.03) para exploración agresiva")
    print("  ✓ GAE lambda aumentado (0.9→0.92) para ventaja más estable")
    print("  ✓ Episodes aumentados (3→5)")

    # Guardar configuración optimizada
    output_path = Path("configs/default_optimized.yaml")
    with open(output_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Configuración optimizada guardada: {output_path}")
    print("\nComandos para entrenar con optimizaciones:")
    print("  python -m scripts.run_all_agents --config configs/default_optimized.yaml")
    print("\nO individualmente:")
    print("  python -m scripts.run_sac_only --config configs/default_optimized.yaml")
    print("  python -m scripts.run_ppo_a2c_only --config configs/default_optimized.yaml")
    print("  python -m scripts.run_a2c_only --config configs/default_optimized.yaml")

    # Mostrar resumen de cambios
    print("\n" + "="*80)
    print("RESUMEN DE CAMBIOS")
    print("="*80)
    print("\n[SAC - Soft Actor-Critic]")
    print(f"  Critic LR:          0.002 → 0.0025 (↑25%)")
    print(f"  Soft Update (tau):  0.01  → 0.005  (↓50%)")
    print(f"  Buffer Size:        10M   → 20M    (↑100%)")
    print(f"  Init Entropy:       0.2   → 0.1    (↓50%)")
    print(f"  Episodes:           3     → 5      (↑67%)")

    print("\n[PPO - Proximal Policy Optimization]")
    print(f"  Learning Rate:      0.0003 → 0.0005 (↑67%)")
    print(f"  N-Steps:            4096   → 8192   (↑100%)")
    print(f"  N-Epochs:           25     → 20     (↓20%)")
    print(f"  Entropy Coef:       0.001  → 0.002  (↑100%)")
    print(f"  GAE Lambda:         0.95   → 0.98   (↑0.3%)")
    print(f"  Episodes:           3      → 5      (↑67%)")

    print("\n[A2C - Advantage Actor-Critic]")
    print(f"  Learning Rate:      0.002 → 0.003 (↑50%)")
    print(f"  N-Steps:            16    → 8     (↓50%, 2× freq)")
    print(f"  Entropy Coef:       0.02  → 0.03  (↑50%)")
    print(f"  GAE Lambda:         0.9   → 0.92  (↑0.2%)")
    print(f"  Episodes:           3     → 5     (↑67%)")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
