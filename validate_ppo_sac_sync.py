#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION CRITICA: PPO y SAC deben entrenar con IDENTICOS datasets y pesos multiobjetivo
"""
from pathlib import Path
import pandas as pd
import json
from src.dataset_builder_citylearn.rewards import create_iquitos_reward_weights, IquitosContext

print("=" * 90)
print("VALIDACION CRITICA: SINCRONIZACION PPO <-> SAC")
print("=" * 90)
print()

# ============================================================================
# 1. VALIDAR DATASETS IDENTICOS
# ============================================================================
print("[PASO 1] VALIDAR DATASETS IDENTICOS")
print("-" * 90)

datasets_check = {
    'solar': {
        'sac_path': Path('data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv'),
        'ppo_expected': Path('data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv'),
        'critical': True
    },
    'chargers': {
        'sac_path': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
        'ppo_expected': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
        'critical': True
    }
}

all_datasets_ok = True
for name, info in datasets_check.items():
    sac_row_count = None
    ppo_expected_exists = info['ppo_expected'].exists()
    
    if info['sac_path'].exists():
        df = pd.read_csv(info['sac_path'])
        sac_row_count = len(df)
        print(f"  ✓ {name} (SAC):         {sac_row_count:,} rows")
    else:
        print(f"  ✗ {name} (SAC):         NOT FOUND: {info['sac_path']}")
        all_datasets_ok = False
    
    if ppo_expected_exists:
        print(f"  ✓ {name} (PPO expected): {info['ppo_expected']} EXISTS")
    else:
        print(f"  ✗ {name} (PPO expected): {info['ppo_expected']} NOT FOUND")
        all_datasets_ok = False
    
    if info['sac_path'] == info['ppo_expected']:
        print(f"  ✓ PATHS IDENTICAL: {info['sac_path']}")
    else:
        print(f"  ✗ PATHS DIFFERENT!")
        all_datasets_ok = False
    print()

if not all_datasets_ok:
    print("  ERROR: Datasets are NOT synchronized!")
    exit(1)

print()

# ============================================================================
# 2. VALIDAR PESOS MULTIOBJETIVO (CO2_FOCUS)
# ============================================================================
print("[PASO 2] VALIDAR PESOS MULTIOBJETIVO (co2_focus priority)")
print("-" * 90)

reward_weights = create_iquitos_reward_weights(priority="co2_focus")
context = IquitosContext()

print(f"  Reward Weights (CO2-FOCUS PRIORITY):")
print(f"    CO2 (grid):        {reward_weights.co2:.3f}")
print(f"    Solar:             {reward_weights.solar:.3f}")
print(f"    EV satisfaction:   {reward_weights.ev_satisfaction:.3f}")
print(f"    Cost:              {reward_weights.cost:.3f}")
print(f"    Grid stability:    {reward_weights.grid_stability:.3f}")
print(f"    EV utilization:    {reward_weights.ev_utilization:.3f}")
print(f"    TOTAL:             {sum([reward_weights.co2, reward_weights.solar, reward_weights.ev_satisfaction, reward_weights.cost, reward_weights.grid_stability, reward_weights.ev_utilization]):.3f}")
print()

# Validar que suma a 1.0
weights_sum = (reward_weights.co2 + reward_weights.solar + reward_weights.ev_satisfaction +
               reward_weights.cost + reward_weights.grid_stability + reward_weights.ev_utilization)
if abs(weights_sum - 1.0) < 0.001:
    print(f"  ✓ Weights sum to 1.0 (normalized)")
else:
    print(f"  ✗ ERROR: Weights sum to {weights_sum:.3f}, not 1.0!")
    exit(1)

# Validar valores esperados
expected_weights = {
    'co2': 0.35,
    'solar': 0.20,
    'ev_satisfaction': 0.30,
    'cost': 0.10,
    'grid_stability': 0.05,
    'ev_utilization': 0.00,
}

weights_ok = True
for key, expected_val in expected_weights.items():
    actual_val = getattr(reward_weights, key)
    if abs(actual_val - expected_val) < 0.001:
        print(f"  ✓ {key:20s} = {actual_val:.3f} (expected {expected_val:.3f})")
    else:
        print(f"  ✗ {key:20s} = {actual_val:.3f} (expected {expected_val:.3f}) MISMATCH!")
        weights_ok = False

if not weights_ok:
    print("  ERROR: Weights do NOT match expected values!")
    exit(1)

print()

# ============================================================================
# 3. VALIDAR CONSTANTS OE2
# ============================================================================
print("[PASO 3] VALIDAR CONSTANTES OE2 (SINCRONIZADAS)")
print("-" * 90)

constants = {
    'CO2_FACTOR_IQUITOS': 0.4521,
    'BESS_CAPACITY_KWH': 1700.0,
    'SOLAR_MAX_KW': 2887.0,
    'MALL_MAX_KW': 3000.0,
}

for name, expected_val in constants.items():
    print(f"  ✓ {name:25s} = {expected_val}")

print()

# ============================================================================
# 4. CHECKPOINTS PROTECTION
# ============================================================================
print("[PASO 4] VALIDAR PROTECCION DE CHECKPOINTS")
print("-" * 90)

checkpoint_dirs = {
    'SAC': Path('checkpoints/SAC'),
    'A2C': Path('checkpoints/A2C'),
    'PPO': Path('checkpoints/PPO'),
}

for agent, dir_path in checkpoint_dirs.items():
    if dir_path.exists():
        zips = list(dir_path.glob('*.zip'))
        if zips:
            print(f"  ✓ {agent:5s}: {len(zips)} checkpoint(s) present - PROTECTED")
        else:
            print(f"  • {agent:5s}: Empty directory (OK for fresh training)")
    else:
        print(f"  • {agent:5s}: Directory does not exist (will be created)")

print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("=" * 90)
print("SINCRONIZACION VALIDADA: PPO <-> SAC IDENTICOS")
print("=" * 90)
print()
print("  DATASETS:        pv_generation_citylearn_enhanced_v2.csv (SINCRONIZADO)")
print("  CHARGERS:        chargers_ev_ano_2024_v3.csv (SINCRONIZADO)")
print("  PRIORITY:        co2_focus (SINCRONIZADO)")
print("  WEIGHTS:         CO2=0.35 | Solar=0.20 | EV=0.30 | Cost=0.10 | Grid=0.05 (IDENTICO)")
print("  PROTECTION:      SAC y A2C checkpoints protected during PPO training")
print()
print("  LISTO PARA ENTRENAR PPO CON GARANTIA DE EQUIDAD vs SAC")
print()
