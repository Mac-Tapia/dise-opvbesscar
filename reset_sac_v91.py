#!/usr/bin/env python3
"""
Limpieza segura para v9.2 - Reset completo
"""
import shutil
from pathlib import Path

print("=" * 70)
print("SAC v9.2 RESET - Limpieza y preparación RADICAL")
print("=" * 70)

# Limpiar checkpoints SAC
print("\nPASO 1: Limpiando checkpoints SAC...")
sac_dir = Path("checkpoints/SAC")
if sac_dir.exists():
    for checkpoint in sac_dir.glob("*.zip"):
        checkpoint.unlink()
        print(f"  ✓ {checkpoint.name}")

# Limpiar datos
print("\nPASO 2: Limpiando datos de entrenamiento...")
sac_output = Path("outputs/sac_training")
if sac_output.exists():
    shutil.rmtree(sac_output)
    print(f"  ✓ Eliminado: {sac_output}")

# Crear directorio limpio
sac_output.mkdir(parents=True, exist_ok=True)
print(f"  ✓ Creado: {sac_output}")

print("\n" + "=" * 70)
print("✓ LISTO PARA SAC v9.2 - Reward ultrasimple (grid-only)")
print("=" * 70)
