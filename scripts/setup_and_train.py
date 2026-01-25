#!/usr/bin/env python3
"""
INSTALACIÓN Y ENTRENAMIENTO COMPLETO
=====================================
Este script instala todas las dependencias y luego entrena 3 agentes.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def run_command(cmd, description):
    """Ejecutar comando y reportar resultado."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"⚠ Error ejecutando: {cmd}")
        return False
    return True

def main():
    print(f"\n{'='*70}")
    print("PVBESSCAR: SETUP Y ENTRENAMIENTO")
    print(f"{'='*70}\n")

    # 1. Instalar dependencias
    commands = [
        ("pip install torch --index-url https://download.pytorch.org/whl/cpu",
         "1. Instalando PyTorch (CPU)"),

        ("pip install gymnasium stable-baselines3[extra]",
         "2. Instalando Gymnasium y stable-baselines3"),

        ("pip install citylearn",
         "3. Instalando CityLearn"),

        (f"python {ROOT}/scripts/EJECUTAR_PIPELINE_MAESTRO.py",
         "4. Ejecutando pipeline OE2 → Dataset"),

        (f"python {ROOT}/scripts/train_complete_agents.py --episodes 5 --device cpu",
         "5. Entrenando agentes (SAC, PPO, A2C × 5 episodios)"),
    ]

    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print(f"✗ Setup fallido en: {desc}")
            sys.exit(1)

    print(f"\n{'='*70}")
    print("✓ ¡INSTALACIÓN Y ENTRENAMIENTO COMPLETADO!")
    print(f"{'='*70}")
    print("\nProximos pasos:")
    print("  1. Ver resultados: python scripts/compare_baseline_vs_retrain.py")
    print("  2. Comparar CO₂: python -m scripts.run_oe3_co2_table")
    print("  3. Monitorear: python scripts/monitor_training_live_2026.py\n")

if __name__ == "__main__":
    main()
