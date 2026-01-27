#!/usr/bin/env python3
"""
Script para ejecutar la secuencia completa de entrenamiento:
1. Dataset
2. Baseline
3. PPO
4. A2C
5. SAC
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list[str], description: str) -> int:
    """Ejecutar comando y esperar a que termine."""
    print(f"\n{'='*80}")
    print(f"🚀 {description.upper()}")
    print(f"{'='*80}\n")

    result = subprocess.run(cmd, cwd=Path.cwd())

    if result.returncode != 0:
        print(f"\n❌ Error en {description}")
        return result.returncode

    print(f"\n✓ {description} completado")
    return 0


def main():
    """Ejecutar secuencia completa."""

    # Secuencia de entrenamiento: Dataset → Baseline → PPO → A2C → SAC
    steps = [
        ([sys.executable, "-m", "scripts.run_ppo_a2c_only", "--config", "configs/default.yaml"],
         "PPO y A2C"),

        ([sys.executable, "-m", "scripts.run_sac_only", "--config", "configs/default.yaml"],
         "SAC"),
    ]

    for cmd, desc in steps:
        # Usar Python 3.11
        cmd = ["py", "-3.11"] + cmd[1:]

        ret = run_command(cmd, desc)
        if ret != 0:
            print(f"\n❌ La secuencia se detiene en {desc}")
            return ret

    print(f"\n{'='*80}")
    print("✅ ENTRENAMIENTO COMPLETO FINALIZADO")
    print(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
