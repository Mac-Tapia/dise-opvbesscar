#!/usr/bin/env python3
"""Copiar datasets a ubicación correcta para training"""
import shutil
from pathlib import Path

print("=" * 80)
print("PREPARANDO DATASETS PARA TRAINING")
print("=" * 80)
print()

# Definir rutas
src_chargers = Path("data/interim/oe2/chargers/chargers_real_hourly_2024.csv")
dst_chargers = Path("data/interim/oe2/chargers/chargers_hourly_dataset.csv")

src_mall = Path("data/interim/oe2/mall_demand_hourly.csv")
dst_mall = Path("data/interim/oe2/mall/mall_demand_hourly.csv")

# Copiar chargers
if src_chargers.exists():
    shutil.copy2(src_chargers, dst_chargers)
    print(f"✅ Copiado: {dst_chargers}")
else:
    print(f"❌ No encontrado: {src_chargers}")

# Copiar mall
if src_mall.exists():
    dst_mall.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_mall, dst_mall)
    print(f"✅ Copiado: {dst_mall}")
else:
    print(f"❌ No encontrado: {src_mall}")

print()
print("Verificación:")
print(f"{'✅' if dst_chargers.exists() else '❌'} {dst_chargers}")
print(f"{'✅' if dst_mall.exists() else '❌'} {dst_mall}")
print()

# Ahora ejecutar training
print("=" * 80)
print("Iniciando TRAINING PPO...")
print("=" * 80)
print()

import subprocess
import sys

result = subprocess.run([sys.executable, "TRAINING_MASTER.py"])
sys.exit(result.returncode)
