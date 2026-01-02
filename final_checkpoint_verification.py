#!/usr/bin/env python3
"""
Verificación FINAL de checkpoints - Resumen Ejecutivo
======================================================

Este script verifica el estado COMPLETO del sistema de checkpoints.
"""

import json
from pathlib import Path
import subprocess

print("\n" + "="*80)
print("VERIFICACIÓN FINAL - SISTEMA DE CHECKPOINTS")
print("="*80)

# 1. Verificar configuración
print("\n1. CONFIGURACIÓN DE CHECKPOINTS:")
print("-" * 40)

from src.iquitos_citylearn.config import load_config, load_paths

cfg = load_config(Path("configs/default.yaml"))
eval_cfg = cfg["oe3"]["evaluation"]

for agent in ["sac", "ppo", "a2c"]:
    agent_cfg = eval_cfg.get(agent, {})
    freq = agent_cfg.get("checkpoint_freq_steps", 0)
    save_final = agent_cfg.get("save_final", False)
    episodes = agent_cfg.get("episodes", 0)
    
    total_steps = episodes * 8760 if episodes > 0 else 0
    expected_checkpoints = total_steps // freq if freq > 0 else 0
    
    print(f"\n{agent.upper()}:")
    print(f"  ✓ checkpoint_freq_steps: {freq}")
    print(f"  ✓ save_final: {save_final}")
    print(f"  ✓ episodes: {episodes}")
    print(f"  → Total steps: {total_steps}")
    print(f"  → Expected checkpoints: {expected_checkpoints + (1 if save_final else 0)}")

# 2. Verificar archivos generados
print("\n\n2. ARCHIVOS GENERADOS:")
print("-" * 40)

training_dir = Path("analyses/oe3/training")
if training_dir.exists():
    print(f"✓ Training directory exists: {training_dir}")
    
    # Config files
    configs = list(training_dir.glob("*_config.json"))
    print(f"  Config files: {len(configs)}")
    for c in configs:
        print(f"    - {c.name}")
    
    # Metrics CSV
    metrics = list(training_dir.glob("*_training_metrics.csv"))
    print(f"  Metrics CSV: {len(metrics)}")
    for m in metrics:
        lines = m.read_text().strip().split("\n")
        print(f"    - {m.name}: {len(lines)-1} records")
    
    # Plots
    plots = list(training_dir.glob("*.png"))
    print(f"  Plot files: {len(plots)}")
    
    # Checkpoint directory
    checkpoint_base = training_dir / "checkpoints"
    if checkpoint_base.exists():
        all_zips = list(checkpoint_base.rglob("*.zip"))
        print(f"  Checkpoint .zip files: {len(all_zips)} FOUND ✓")
        
        for agent in ["sac", "ppo", "a2c"]:
            agent_zips = list(checkpoint_base.glob(f"{agent}/*.zip"))
            print(f"    - {agent.upper()}: {len(agent_zips)}")
    else:
        print(f"  Checkpoint directory: NOT CREATED ✗")
else:
    print(f"✗ Training directory not found")

# 3. Verificar si el callback test file existe
print("\n\n3. CALLBACK DIAGNOSTIC LOG:")
print("-" * 40)

test_file = Path("checkpoint_callback_test.txt")
if test_file.exists():
    content = test_file.read_text()
    lines = content.strip().split("\n")
    print(f"✓ Callback test file exists ({len(lines)} lines):")
    print(content)
else:
    print("✗ Callback test file NOT found (callback not instantiated)")

# 4. Resultado
print("\n\n4. CONCLUSIÓN:")
print("-" * 40)

checkpoint_base = training_dir / "checkpoints" if training_dir.exists() else None
if checkpoint_base and checkpoint_base.exists():
    all_zips = list(checkpoint_base.rglob("*.zip"))
    if all_zips:
        print(f"\n✓✓✓ SUCCESS ✓✓✓")
        print(f"{len(all_zips)} checkpoint files created!")
    else:
        print(f"\n✗ Checkpoints NOT created")
        print("  → Callback may not be invoked or saving failed")
else:
    print(f"\n✗ Checkpoint system not working")
    print("  → No checkpoint directory created")

print("\n" + "="*80 + "\n")
