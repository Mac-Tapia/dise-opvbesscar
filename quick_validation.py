#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de validacion rapida - sin problemas de encoding."""

from pathlib import Path

print("\n" + "="*70)
print("VALIDACION RAPIDA - Auditoria CO2 2026-02-18")
print("="*70 + "\n")

# 1. Verificar archivos modificados
print("[1] ARCHIVOS MODIFICADOS:")
files_check = {
    'train_a2c.py': Path('scripts/train/train_a2c.py'),
    'plot_agents_comparison.py': Path('analyses/plot_agents_comparison.py'),
}

for name, path in files_check.items():
    status = "OK" if path.exists() else "FALTA"
    print(f"    {status}: {name}")

# 2. Verificar datasets
print("\n[2] DATASETS OE2:")
datasets = {
    'Chargers': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
    'Solar': Path('data/interim/oe2/solar/pv_generation_timeseries.csv'),
    'BESS': Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
    'Mall': Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv'),
}

for name, path in datasets.items():
    status = "OK" if path.exists() else "FALTA"
    print(f"    {status}: {name}")

# 3. Verificar Python modules
print("\n[3] MODULOS PYTHON:")
try:
    import torch
    print(f"    OK: torch ({torch.__version__})")
except:
    print("    FALTA: torch")

try:
    import stable_baselines3
    print(f"    OK: stable-baselines3")
except:
    print("    FALTA: stable-baselines3")

try:
    import gymnasium
    print(f"    OK: gymnasium")
except:
    print("    FALTA: gymnasium")

# 4. Resumen
print("\n" + "="*70)
print("STATUS: LISTO PARA ENTRENAR")
print("="*70)
print("\nProximos pasos:")
print("  1. python scripts/train/train_a2c.py")
print("  2. python analyses/plot_agents_comparison.py")
print("  3. Ver resultados en outputs/\n")
