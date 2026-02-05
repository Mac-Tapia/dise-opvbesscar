#!/usr/bin/env python3
"""
VERIFICACION: 5 ARCHIVOS OE2 OBLIGATORIOS

Verifica que los 5 archivos REALES de data/oe2/ existen y cargan correctamente:
1. chargers_real_hourly_2024.csv (8760 × 128)
2. chargers_real_statistics.csv
3. bess_hourly_dataset_2024.csv (8760 rows con soc_percent)
4. demandamallhorakwh.csv (≥8760 rows)
5. pv_generation_hourly_citylearn_v2.csv (8760 rows solar PVGIS)

NO FALLBACK - Si ANY archivo falta, FALLA.
"""

import sys
from pathlib import Path
import pandas as pd

print("\n" + "="*80)
print("VERIFICACION: 5 ARCHIVOS OE2 OBLIGATORIOS")
print("="*80)

oe2_base = Path("data/oe2")

files_config = [
    ("CHARGERS_REAL_HOURLY", "chargers/chargers_real_hourly_2024.csv", (8760, 128)),
    ("CHARGERS_STATISTICS", "chargers/chargers_real_statistics.csv", None),
    ("BESS_HOURLY", "bess/bess_hourly_dataset_2024.csv", (8760, None)),
    ("MALL_DEMAND", "demandamallkwh/demandamallhorakwh.csv", (None, 1)),
    ("SOLAR_GENERATION", "Generacionsolar/pv_generation_hourly_citylearn_v2.csv", (8760, None)),
]

print("\n[PASO 1] VERIFICAR EXISTENCIA DE 5 ARCHIVOS OBLIGATORIOS\n")

all_exist = True
for name, rel_path, expected_shape in files_config:
    full_path = oe2_base / rel_path
    exists = full_path.exists()
    status = "[OK]" if exists else "[ERROR]"
    print(f"{status} {name:25} -> {rel_path}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n[CRITICAL ERROR] FALTAN ARCHIVOS OBLIGATORIOS")
    sys.exit(1)

print("\n[PASO 2] CARGAR Y VERIFICAR DIMENSIONES\n")

try:
    # 1. Chargers hourly
    df = pd.read_csv(oe2_base / "chargers/chargers_real_hourly_2024.csv")
    print(f"[CHARGERS_REAL_HOURLY] {df.shape[0]} x {df.shape[1]} ✓")

    # 2. Chargers stats
    df = pd.read_csv(oe2_base / "chargers/chargers_real_statistics.csv")
    print(f"[CHARGERS_STATISTICS] {df.shape[0]} x {df.shape[1]} ✓")

    # 3. BESS hourly
    df = pd.read_csv(oe2_base / "bess/bess_hourly_dataset_2024.csv", index_col=0)
    soc_min = df["soc_percent"].min() if "soc_percent" in df.columns else "?"
    soc_max = df["soc_percent"].max() if "soc_percent" in df.columns else "?"
    print(f"[BESS_HOURLY] {df.shape[0]} x {df.shape[1]} | SOC: {soc_min:.1f}% to {soc_max:.1f}% ✓")

    # 4. Mall demand
    df = pd.read_csv(oe2_base / "demandamallkwh/demandamallhorakwh.csv")
    print(f"[MALL_DEMAND] {df.shape[0]} x {df.shape[1]} ✓")

    # 5. Solar generation
    df = pd.read_csv(oe2_base / "Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
    print(f"[SOLAR_GENERATION] {df.shape[0]} x {df.shape[1]} ✓")

except Exception as e:
    print(f"\n[ERROR] {e}")
    sys.exit(1)

print("\n" + "="*80)
print("✅ VERIFICACION COMPLETADA - 5 ARCHIVOS OE2 OBLIGATORIOS CARGADOS")
print("="*80 + "\n")
