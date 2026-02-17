#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDACION ROBUSTA: Verificar parámetros SAC ANTES de entrenar"""

from pathlib import Path
import sys

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

# Import config
from scripts.train.train_sac_multiobjetivo import SACConfig

print("="*80)
print("VALIDACION ROBUSTA: PARAMETROS SAC")
print("="*80)
print()

# Test 1: Crear config para GPU
print("[1] Creating SACConfig.for_gpu()...")
config_gpu = SACConfig.for_gpu()

print("[✓] SACConfig.for_gpu() created successfully")
print()

# Test 2: Validar OPCION B parameters
print("[2] Validating OPCION B Parameters:")
print("-" * 80)

defaults = {
    'learning_rate': (1e-4, "CONSERVADOR para estabilidad"),
    'buffer_size': (1_000_000, "Máxima diversidad (1M)"),
    'batch_size': (256, "Robusto, menos noise"),
    'train_freq': ((1, 'episode'), "Estable: entrenar al final episodio"),
    'gradient_steps': (-1, "AUTO - SAC elige óptimamente"),
    'tau': (0.025, "Soft updates más suave"),
    'gamma': (0.99, "Standard discount"),
    'ent_coef': ('auto', "Adaptativo"),
    'target_entropy': (None, "AUTO-CALCULAR -dim(A)/2"),
    'use_sde': (True, "Exploración 38D"),
}

all_correct = True
for param, (expected_value, reason) in defaults.items():
    actual_value = getattr(config_gpu, param)
    is_correct = actual_value == expected_value
    status = "✓" if is_correct else "✗"
    
    print(f"{status} {param:20s} = {actual_value}")
    if not is_correct:
        print(f"    [ERROR] Expected: {expected_value}")
        print(f"    [REASON] {reason}")
        all_correct = False
    else:
        print(f"    [OK] {reason}")
    print()

# Test 3: Policy kwargs
print("[3] Policy Network Architecture:")
print("-" * 80)
policy_kwargs = config_gpu.policy_kwargs
print(f"  Actor network:  {policy_kwargs['net_arch']['pi']}")
print(f"  Critic network: {policy_kwargs['net_arch']['qf']}")
print(f"  Activation:     {policy_kwargs['activation_fn'].__name__}")
print(f"  Log std init:   {policy_kwargs['log_std_init']}")
print()

expected_net = [512, 512]
if policy_kwargs['net_arch']['pi'] == expected_net and policy_kwargs['net_arch']['qf'] == expected_net:
    print("  [✓] Networks are 512x512 (correct)")
else:
    print(f"  [✗] Networks not 512x512! Got {policy_kwargs['net_arch']['pi']}")
    all_correct = False

print()

# Test 4: Convert to SAC kwargs (simulate what train script does)
print("[4] Converting to SAC kwargs (as train script does):")
print("-" * 80)
sac_kwargs = {
    'learning_rate': config_gpu.learning_rate,
    'buffer_size': config_gpu.buffer_size,
    'learning_starts': config_gpu.learning_starts,
    'batch_size': config_gpu.batch_size,
    'tau': config_gpu.tau,
    'gamma': config_gpu.gamma,
    'ent_coef': config_gpu.ent_coef,
    'train_freq': config_gpu.train_freq,
    'gradient_steps': config_gpu.gradient_steps,
    'policy_kwargs': config_gpu.policy_kwargs,
}
if config_gpu.target_entropy is not None:
    sac_kwargs['target_entropy'] = config_gpu.target_entropy

print(f"  learning_rate:  {sac_kwargs['learning_rate']}")
print(f"  buffer_size:    {sac_kwargs['buffer_size']:,}")
print(f"  batch_size:     {sac_kwargs['batch_size']}")
print(f"  train_freq:     {sac_kwargs['train_freq']}")
print(f"  gradient_steps: {sac_kwargs['gradient_steps']}")
print(f"  tau:            {sac_kwargs['tau']}")
print()

# Final validation
print("="*80)
if all_correct:
    print("✓ ALL PARAMETERS VALIDATED - SAFE TO TRAIN")
    print("  OPCION B configuration is CORRECT")
    sys.exit(0)
else:
    print("✗ PARAMETER VALIDATION FAILED - DO NOT TRAIN")
    print("  Check errors above")
    sys.exit(1)
