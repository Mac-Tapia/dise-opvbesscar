#!/usr/bin/env python3
"""
Quick Start Guide - CityLearn v2 Dataset Builder

Ejemplo rápido mostrando los 3 usos principales:
1. Construir dataset desde OE2
2. Guardar a disco
3. Cargar para training
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dataset_builder_citylearn import (
    build_citylearn_dataset,
    save_citylearn_dataset,
    load_citylearn_dataset,
)

print("\n" + "=" * 80)
print("🚀 QUICK START - CityLearn v2 Dataset Builder")
print("=" * 80)

# ============================================================================
# EXAMPLE 1: Build dataset from OE2 sources (fastest for first-time use)
# ============================================================================
print("\n[EJEMPLO 1] Construir dataset desde OE2 sources")
print("-" * 80)

dataset = build_citylearn_dataset()

# Access components
solar_data = dataset["solar"]
bess_data = dataset["bess"]
chargers_data = dataset["chargers"]
demand_data = dataset["demand"]
combined_df = dataset["combined"]
config = dataset["config"]

print(f"\n✅ Dataset construido con éxito:")
print(f"   • Solar: {solar_data.n_hours} hours @ {solar_data.mean_kw:.1f} kW avg")
print(f"   • BESS: {bess_data.capacity_kwh:.0f} kWh capacity")
print(f"   • Chargers: {chargers_data.total_sockets} sockets")
print(f"   • Combined shape: {combined_df.shape}")
print(f"\nAcceso a datos:")
print(f"   dataset['solar'].df.head():")
print(solar_data.df.head(2))
print(f"\n   dataset['combined'].head():")
print(combined_df.head(2))
print(f"\nConfig (v{config['version']}):")
print(f"   PV capacity: {config['system']['pv_capacity_kwp']:.0f} kWp")
print(f"   BESS capacity: {config['system']['bess_capacity_kwh']:.0f} kWh")
print(f"   CO2 grid factor: {config['co2']['grid_factor_kg_per_kwh']} kg/kWh")

# ============================================================================
# EXAMPLE 2: Save dataset to disk for future sessions
# ============================================================================
print("\n" + "=" * 80)
print("[EJEMPLO 2] Guardar dataset a disco")
print("-" * 80)

output_dir = save_citylearn_dataset(dataset)
print(f"\n✅ Dataset guardado en: {output_dir}")
print(f"   Archivos creados:")
import os
for file in sorted(os.listdir(output_dir)):
    file_path = output_dir / file
    size_kb = os.path.getsize(file_path) / 1024
    print(f"   • {file:<35} ({size_kb:>7.1f} KB)")

# ============================================================================
# EXAMPLE 3: Load dataset from disk (much faster in future runs)
# ============================================================================
print("\n" + "=" * 80)
print("[EJEMPLO 3] Cargar dataset desde disco (para training)")
print("-" * 80)

loaded = load_citylearn_dataset(output_dir)

print(f"\n✅ Dataset cargado con éxito:")
print(f"   Keys disponibles: {list(loaded.keys())}")
print(f"   Combined shape: {loaded['combined'].shape}")

# Example: Access data for training
combined_for_training = loaded["combined"]
config_for_training = loaded["config"]

print(f"\n📊 Ready para training:")
print(f"   • DataFrame shape: {combined_for_training.shape}")
print(f"   • Columns: {list(combined_for_training.columns)[:5]} ... ({len(combined_for_training.columns)} total)")
print(f"   • System: PV={config_for_training['system']['pv_capacity_kwp']:.0f}kWp, BESS={config_for_training['system']['bess_capacity_kwh']:.0f}kWh")

# ============================================================================
# EXAMPLE 4: Advanced - Custom paths
# ============================================================================
print("\n" + "=" * 80)
print("[EJEMPLO 4] Uso avanzado - Rutas personalizadas")
print("-" * 80)

print("""
# Parámetros opcionales para override:
dataset = build_citylearn_dataset(
    solar_path="ruta/alternativa/solar.csv",
    bess_path="ruta/alternativa/bess.csv",
    chargers_path="ruta/alternativa/chargers.csv",
    demand_path="ruta/alternativa/demand.csv",
    cwd=Path(".")
)

# Guardar en ubicación custom:
save_citylearn_dataset(
    dataset,
    output_dir="mis_datos/custom_dataset/"
)

# Cargar desde ubicación custom:
loaded = load_citylearn_dataset(
    input_dir="mis_datos/custom_dataset/"
)
""")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("✅ QUICK START COMPLETADO")
print("=" * 80)
print("""
PRÓXIMOS PASOS:

1. Para training con SAC/PPO/A2C:
   python -m scripts.train.train_ppo_multiobjetivo.py --dataset data/processed/citylearn/iquitos_ev_mall/

2. Para análisis de datos:
   import pandas as pd
   df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/citylearnv2_combined_dataset.csv')
   print(df.describe())

3. Para reproducibilidad:
   # Guardar path de dataset y usarlo consistentemente
   dataset_path = 'data/processed/citylearn/iquitos_ev_mall/'
   loaded = load_citylearn_dataset(dataset_path)

DOCUMENTACIÓN COMPLETA: Ver DATASET_BUILDER_v7.0_RESUMEN.md
""")

print("=" * 80 + "\n")
