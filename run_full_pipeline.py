#!/usr/bin/env python3
"""Pipeline completo: Dataset → SAC Training → Generación de archivos técnicos."""

import sys
import subprocess
from pathlib import Path

print("\n" + "=" * 80)
print("PIPELINE COMPLETO: Dataset → SAC Training → Archivos Técnicos")
print("=" * 80 + "\n")

# PASO 1: Build Dataset
print("[PASO 1/3] Construyendo dataset CityLearn v2...")
print("-" * 80)
result = subprocess.run(
    [sys.executable, "-m", "scripts.run_oe3_build_dataset", "--config", "configs/default.yaml"],
    cwd=".",
    capture_output=False
)
if result.returncode != 0:
    print("[ERROR] Dataset build failed. Abortando.")
    sys.exit(1)
print("[OK] Dataset construido\n")

# PASO 2: SAC Training
print("[PASO 2/3] Entrenando SAC (1 episodio = 8,760 timesteps)...")
print("-" * 80)
result = subprocess.run(
    [sys.executable, "-m", "scripts.train_sac_production", "--episodes", "1"],
    cwd=".",
    capture_output=False
)
if result.returncode != 0:
    print("[ERROR] SAC training failed.")
    sys.exit(1)
print("[OK] SAC training completado\n")

# PASO 3: Validar archivos
print("[PASO 3/3] Validando archivos técnicos generados...")
print("-" * 80)
files_to_check = [
    "outputs/oe3/result_sac.json",
    "outputs/oe3/timeseries_sac.csv",
    "outputs/oe3/trace_sac.csv",
]
all_exist = True
for fpath in files_to_check:
    p = Path(fpath)
    if p.exists():
        size_kb = p.stat().st_size / 1024
        print(f"[OK] {fpath} ({size_kb:.1f} KB)")
    else:
        print(f"[MISSING] {fpath}")
        all_exist = False

print("-" * 80)
if all_exist:
    print("\n[SUCCESS] Todos los 3 archivos técnicos generados correctamente!")
else:
    print("\n[ERROR] Faltan algunos archivos técnicos")
    sys.exit(1)

print("\n" + "=" * 80)
print("PIPELINE COMPLETADO EXITOSAMENTE")
print("=" * 80 + "\n")
