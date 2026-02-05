#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

print("=" * 90)
print("VERIFICACION: DATOS REALES OBLIGATORIOS DE data/oe2/")
print("=" * 90)
print()

oe2_base = Path("d:\\diseñopvbesscar\\data\\oe2")
basedir = Path("d:\\diseñopvbesscar")

obligatory = {
    "CHARGERS_REAL_HOURLY": oe2_base / "chargers" / "chargers_real_hourly_2024.csv",
    "CHARGERS_STATISTICS": oe2_base / "chargers" / "chargers_real_statistics.csv",
    "BESS_HOURLY": oe2_base / "bess" / "bess_hourly_dataset_2024.csv",
    "MALL_DEMAND": oe2_base / "demandamallkwh" / "demandamallhorakwh.csv",
}

print("[PASO 1] VERIFICAR EXISTENCIA")
print("-" * 90)

all_exist = True
for name, path in obligatory.items():
    exists = path.exists()
    status = "OK" if exists else "FALTA"
    rel = path.relative_to(basedir)
    print("[{}] {} -> {}".format(status, name, rel))
    if not exists:
        all_exist = False
        print("     ERROR CRITICO: Este archivo es OBLIGATORIO")

print()

if not all_exist:
    print("ERROR: Faltan archivos. Rutas son FIJAS, no se pueden mover")
    sys.exit(1)

print("[PASO 2] CARGAR Y VERIFICAR CONTENIDO")
print("-" * 90)

try:
    import pandas as pd

    for name, path in obligatory.items():
        print("\n[{}]".format(name))

        if "BESS" in name:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
        else:
            df = pd.read_csv(path)

        print("  Shape: {} x {}".format(df.shape[0], df.shape[1]))

        if "CHARGERS_REAL_HOURLY" in name and df.shape == (8760, 128):
            energy = df.sum().sum()
            print("  OK: 8760 rows x 128 cols | Energy: {:.0f} kWh".format(energy))
        elif "BESS" in name and len(df) == 8760:
            if "soc_percent" in df.columns:
                soc_min = df["soc_percent"].min()
                soc_max = df["soc_percent"].max()
                print("  OK: 8760 rows | SOC: {:.1f}% to {:.1f}%".format(soc_min, soc_max))
        elif "MALL_DEMAND" in name and len(df) >= 8760:
            print("  OK: {} rows".format(len(df)))
        elif "CHARGERS_STATISTICS" in name:
            print("  OK: {} rows".format(len(df)))
        else:
            print("  WARNING: Verificar dimensiones")

except Exception as e:
    print("ERROR: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 90)
print("RESUMEN: 4 ARCHIVOS REALES OBLIGATORIOS VERIFICADOS")
print("=" * 90)
print()
print("Usados en:")
print("  - Entrenamiento SAC/PPO/A2C")
print("  - Metricas baseline")
print("  - Validacion CO2")
print()
print("Rutas FIJAS (NO mover):")
print("  - data/oe2/chargers/chargers_real_hourly_2024.csv")
print("  - data/oe2/chargers/chargers_real_statistics.csv")
print("  - data/oe2/bess/bess_hourly_dataset_2024.csv")
print("  - data/oe2/demandamallkwh/demandamallhorakwh.csv")
print()
print("=" * 90)
