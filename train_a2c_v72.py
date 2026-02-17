#!/usr/bin/env python
"""
A2C Training v7.2 - Corrected CO2 Calculations with Improvements
Entrenar A2C con CO2 alineado con PPO/SAC y mejoras de v7.2
"""

import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import sys
import subprocess

print("╔═══════════════════════════════════════════════════════════════╗")
print("║  A2C TRAINING v7.2 - CORRECTED CO2 + IMPROVEMENTS           ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()
print("Phase 3 Actions:")
print("  ✓ A2C Checkpoints: Cleaned")
print("  ✓ Dataset: OE2 validated (8,760 × 4 sources)")
print("  ✓ Code: CO2 aligned with PPO/SAC (lines 2968-3003)")
print()
print("v7.2 Improvements:")
print("  • Vehicles_charged weight: 0.35 (was 0.30)")
print("  • Grid_stable weight: 0.15 (was 0.05)")
print("  • Entropy coefficient: 0.0002 (was 0.0001)")
print("  • Episodes: 13 (was 10)")
print()
print("Starting training...")
print()

# Ejecutar el script de entrenamiento con salida en vivo
result = subprocess.run(
    [sys.executable, "scripts/train/train_a2c_multiobjetivo.py"],
    text=True,
)

sys.exit(result.returncode)
