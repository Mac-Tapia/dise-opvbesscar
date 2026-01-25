#!/usr/bin/env python3
"""
Verificador de Configuraciones Individuales Optimizadas para Máxima Potencia
2026-01-24 - Verificación Completa de SAC, PPO, A2C
"""

import sys
import os
from pathlib import Path
from dataclasses import asdict

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def verify_agent_configs():
    """Verifica que todas las configuraciones individuales estén optimizadas."""

    print("=" * 80)
    print("⚡ VERIFICACIÓN DE CONFIGURACIONES INDIVIDUALES MÁXIMA POTENCIA ⚡")
    print("=" * 80)
    print()

    all_passed = True

    try:
        from iquitos_citylearn.oe3.agents.sac import SACConfig
        from iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig
        from iquitos_citylearn.oe3.agents.a2c_sb3 import A2CConfig
    except ImportError as e:
        print(f"❌ Error importando configuraciones: {e}")
        return False

    # ========== SAC ==========
    print("🔴 SAC (Soft Actor-Critic) - OFF-POLICY MÁXIMA ESTABILIDAD")
    print("-" * 80)

    sac_config = SACConfig()
    sac_checks = {
        "Learning Rate (1.5e-4)": (sac_config.learning_rate == 1.5e-4, sac_config.learning_rate),
        "Batch Size (512)": (sac_config.batch_size == 512, sac_config.batch_size),
        "Buffer Size (1M)": (sac_config.buffer_size == 1000000, sac_config.buffer_size),
        "Gamma (0.999)": (sac_config.gamma == 0.999, sac_config.gamma),
        "Tau (0.001)": (sac_config.tau == 0.001, sac_config.tau),
        "Hidden Sizes (1024,1024)": (sac_config.hidden_sizes == (1024, 1024), sac_config.hidden_sizes),
        "Entropy Coef (0.01)": (sac_config.ent_coef == 0.01, sac_config.ent_coef),
        "Gradient Steps (1)": (sac_config.gradient_steps == 1, sac_config.gradient_steps),
        "Episodes (50)": (sac_config.episodes == 50, sac_config.episodes),
    }

    for check_name, (passed, value) in sac_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {value}")
        if not passed:
            all_passed = False

    print()
    print("  SAC Multiobjetivo:")
    print(f"    CO₂ Weight:        {sac_config.weight_co2} (0.50)")
    print(f"    Cost Weight:       {sac_config.weight_cost} (0.15)")
    print(f"    Solar Weight:      {sac_config.weight_solar} (0.20)")
    print(f"    EV Weight:         {sac_config.weight_ev_satisfaction} (0.10)")
    print(f"    Grid Weight:       {sac_config.weight_grid_stability} (0.05)")
    print()

    # ========== PPO ==========
    print("🟢 PPO (Proximal Policy Optimization) - ON-POLICY MÁXIMA CONVERGENCIA")
    print("-" * 80)

    ppo_config = PPOConfig()
    ppo_checks = {
        "Learning Rate (2.0e-4)": (ppo_config.learning_rate == 2.0e-4, ppo_config.learning_rate),
        "Batch Size (128)": (ppo_config.batch_size == 128, ppo_config.batch_size),
        "N Steps (2048)": (ppo_config.n_steps == 2048, ppo_config.n_steps),
        "N Epochs (20)": (ppo_config.n_epochs == 20, ppo_config.n_epochs),
        "Gamma (0.999)": (ppo_config.gamma == 0.999, ppo_config.gamma),
        "GAE Lambda (0.98)": (ppo_config.gae_lambda == 0.98, ppo_config.gae_lambda),
        "Clip Range (0.1)": (ppo_config.clip_range == 0.1, ppo_config.clip_range),
        "Hidden Sizes (1024,1024)": (ppo_config.hidden_sizes == (1024, 1024), ppo_config.hidden_sizes),
        "Entropy Coef (0.01)": (ppo_config.ent_coef == 0.01, ppo_config.ent_coef),
        "VF Coef (0.7)": (ppo_config.vf_coef == 0.7, ppo_config.vf_coef),
        "Train Steps (1M)": (ppo_config.train_steps == 1000000, ppo_config.train_steps),
        "SDE Enabled": (ppo_config.use_sde == True, ppo_config.use_sde),
    }

    for check_name, (passed, value) in ppo_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {value}")
        if not passed:
            all_passed = False

    print()
    print("  PPO Multiobjetivo:")
    print(f"    CO₂ Weight:        {ppo_config.weight_co2} (0.50)")
    print(f"    Cost Weight:       {ppo_config.weight_cost} (0.15)")
    print(f"    Solar Weight:      {ppo_config.weight_solar} (0.20)")
    print(f"    EV Weight:         {ppo_config.weight_ev_satisfaction} (0.10)")
    print(f"    Grid Weight:       {ppo_config.weight_grid_stability} (0.05)")
    print()

    # ========== A2C ==========
    print("🔵 A2C (Advantage Actor-Critic) - ON-POLICY MÁXIMA VELOCIDAD")
    print("-" * 80)

    a2c_config = A2CConfig()
    a2c_checks = {
        "Learning Rate (1.5e-4)": (a2c_config.learning_rate == 1.5e-4, a2c_config.learning_rate),
        "N Steps (2048)": (a2c_config.n_steps == 2048, a2c_config.n_steps),
        "Gamma (0.999)": (a2c_config.gamma == 0.999, a2c_config.gamma),
        "GAE Lambda (0.95)": (a2c_config.gae_lambda == 0.95, a2c_config.gae_lambda),
        "Entropy Coef (0.01)": (a2c_config.ent_coef == 0.01, a2c_config.ent_coef),
        "VF Coef (0.7)": (a2c_config.vf_coef == 0.7, a2c_config.vf_coef),
        "Max Grad Norm (1.0)": (a2c_config.max_grad_norm == 1.0, a2c_config.max_grad_norm),
        "Hidden Sizes (1024,1024)": (a2c_config.hidden_sizes == (1024, 1024), a2c_config.hidden_sizes),
        "Train Steps (1M)": (a2c_config.train_steps == 1000000, a2c_config.train_steps),
    }

    for check_name, (passed, value) in a2c_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {value}")
        if not passed:
            all_passed = False

    print()
    print("  A2C Multiobjetivo:")
    print(f"    CO₂ Weight:        {a2c_config.weight_co2} (0.50)")
    print(f"    Cost Weight:       {a2c_config.weight_cost} (0.15)")
    print(f"    Solar Weight:      {a2c_config.weight_solar} (0.20)")
    print(f"    EV Weight:         {a2c_config.weight_ev_satisfaction} (0.10)")
    print(f"    Grid Weight:       {a2c_config.weight_grid_stability} (0.05)")
    print()

    # ========== GPU/CUDA INFO ==========
    print("=" * 80)
    print("🎮 INFORMACIÓN GPU/CUDA")
    print("=" * 80)

    try:
        import torch
        print(f"  PyTorch Version:         {torch.__version__}")
        print(f"  CUDA Available:          {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA Version:            {torch.version.cuda}")
            print(f"  GPU Name:                {torch.cuda.get_device_name(0)}")
            print(f"  GPU Memory:              {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            print(f"  CuDNN Version:           {torch.backends.cudnn.version()}")
            print(f"  📊 Current GPU Memory:   {torch.cuda.memory_allocated() / 1e9:.2f} GB / {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    except Exception as e:
        print(f"  ❌ Error checking GPU: {e}")

    print()

    # ========== DATOS ==========
    print("=" * 80)
    print("📁 INFORMACIÓN DE DATOS")
    print("=" * 80)

    try:
        data_dir = Path(__file__).parent.parent / "data"

        # Contar cargadores
        chargers_file = data_dir / "solar" / "chargingStations.json"
        if chargers_file.exists():
            import json
            with open(chargers_file) as f:
                chargers_data = json.load(f)
                num_chargers = len(chargers_data)
                print(f"  ✅ Cargadores EV:        {num_chargers}")

        # Contar schemas
        schemas_dir = data_dir / "schemas"
        if schemas_dir.exists():
            schema_files = list(schemas_dir.glob("*.json"))
            print(f"  ✅ Archivos Schemas:     {len(schema_files)}")
    except Exception as e:
        print(f"  ⚠️  Error checking data: {e}")

    print()

    # ========== RESULTADO FINAL ==========
    print("=" * 80)
    if all_passed:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print()
        print("🎯 CONFIGURACIONES INDIVIDUALES OPTIMIZADAS PARA MÁXIMA POTENCIA:")
        print("   🔴 SAC:  Off-policy   | Buffer 1M | Batch 512 | Tau 0.001 | 1024x1024 hidden")
        print("   🟢 PPO:  On-policy    | N Steps 2048 | Batch 128 | Clip 0.1 | 1024x1024 hidden")
        print("   🔵 A2C:  On-policy    | N Steps 2048 | GAE 0.95 | VF 0.7 | 1024x1024 hidden")
        print()
        print("📊 PESOS MULTIOBJETIVO COMPARTIDOS:")
        print("   CO₂: 0.50 | Solar: 0.20 | Cost: 0.15 | EV: 0.10 | Grid: 0.05")
        print()
        print("🚀 LISTO PARA ENTRENAR")
        return True
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        return False

if __name__ == "__main__":
    success = verify_agent_configs()
    sys.exit(0 if success else 1)
