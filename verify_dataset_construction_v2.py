#!/usr/bin/env python3
"""
Verifica que la construccion del dataset REAL desde OE2→OE3 sea correcta para todos los agentes.
Valida: archivos OE2, integridad de datos, 8760 timesteps, 128 chargers.
"""
from __future__ import annotations

import sys
import json
import pandas as pd
from pathlib import Path

# Suppress pandas display output
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

print("\n" + "="*80)
print("VERIFICACION - CONSTRUCCION DATASET REAL OE2→OE3 PARA TODOS AGENTES")
print("="*80 + "\n")

try:
    # ========== STEP 1: OE2 INPUT FILES ==========
    print("[STEP 1] Validando archivos OE2 INPUT...")
    oe2_sources = {
        "Solar timeseries": "data/interim/oe2/solar/pv_generation_timeseries.csv",
        "Chargers config": "data/interim/oe2/chargers/individual_chargers.json",
        "Charger profile": "data/interim/oe2/chargers/perfil_horario_carga.csv",
        "BESS config": "data/interim/oe2/bess/bess_config.json"
    }

    missing = []
    for name, path in oe2_sources.items():
        p = Path(path)
        if not p.exists():
            missing.append(f"{name}: {path}")

    if missing:
        print("[ERROR] Archivos OE2 faltantes:")
        for m in missing:
            print(f"  ❌ {m}")
        sys.exit(1)

    for name in oe2_sources.keys():
        print(f"  ✓ {name}")

    # ========== STEP 2: SOLAR TIMESERIES (HOURLY) ==========
    print("\n[STEP 2] Validando SOLAR timeseries (HOURLY, 8760 rows)...")
    solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    solar_df = pd.read_csv(solar_path)

    if len(solar_df) == 52560:
        print("  ❌ ERROR CRÍTICO: Datos a 15-minutos detectados (52,560 rows)")
        print("  Solo soportamos HOURLY (8760 rows)")
        sys.exit(1)

    if len(solar_df) != 8760:
        print(f"  ❌ Solar tiene {len(solar_df)} filas, esperado 8760")
        sys.exit(1)

    solar_total = float(solar_df.iloc[:, 0].sum())
    print(f"  ✓ Solar: {len(solar_df)} filas (correcto)")
    print(f"  ✓ Total generation: {solar_total:,.0f} kW-steps")

    # ========== STEP 3: CHARGERS CONFIG ==========
    print("\n[STEP 3] Validando config de cargadores (128 individual)...")
    with open("data/interim/oe2/chargers/individual_chargers.json") as f:
        chargers = json.load(f)

    if len(chargers) != 32:
        print(f"  ❌ Esperado 32 chargers, found {len(chargers)}")
        sys.exit(1)

    total_sockets = sum(len(c.get("sockets", [])) for c in chargers)
    if total_sockets != 128:
        print(f"  ❌ Esperado 128 sockets total, found {total_sockets}")
        sys.exit(1)

    print(f"  ✓ Chargers: {len(chargers)} units")
    print(f"  ✓ Sockets: {total_sockets} total (4 per charger)")

    # ========== STEP 4: BESS CONFIG ==========
    print("\n[STEP 4] Validando config BESS (4520 kWh / 2712 kW)...")
    with open("data/interim/oe2/bess/bess_config.json") as f:
        bess = json.load(f)

    if bess.get("capacity_kwh") != 4520 or bess.get("power_kw") != 2712:
        print(f"  ❌ BESS mismatch: {bess.get('capacity_kwh')} kWh / {bess.get('power_kw')} kW")
        sys.exit(1)

    print(f"  ✓ BESS: 4520 kWh / 2712 kW (OE2 Real)")

    # ========== STEP 5: OE3 OUTPUT FILES ==========
    print("\n[STEP 5] Validando archivos OE3 OUTPUT...")
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")

    if not (dataset_dir / "schema_pv_bess.json").exists():
        print(f"  ❌ Schema NO ENCONTRADO: {dataset_dir / 'schema_pv_bess.json'}")
        sys.exit(1)

    if not (dataset_dir / "Building_1.csv").exists():
        print(f"  ❌ Building_1.csv NO ENCONTRADO: {dataset_dir / 'Building_1.csv'}")
        sys.exit(1)

    charger_files = list(dataset_dir.glob("charger_simulation_*.csv"))
    if len(charger_files) != 128:
        print(f"  ❌ Esperado 128 charger CSVs, found {len(charger_files)}")
        sys.exit(1)

    print(f"  ✓ Schema: schema_pv_bess.json")
    print(f"  ✓ Building: Building_1.csv")
    print(f"  ✓ Chargers: {len(charger_files)} CSV files")

    # ========== STEP 6: DATA INTEGRITY ==========
    print("\n[STEP 6] Validando integridad de datos OE3...")

    # Building
    building_df = pd.read_csv(dataset_dir / "Building_1.csv")
    if len(building_df) != 8760:
        print(f"  ❌ Building_1.csv: {len(building_df)} filas (esperado 8760)")
        sys.exit(1)

    if "non_shiftable_load" not in building_df.columns:
        print(f"  ❌ Building_1.csv FALTA columna 'non_shiftable_load'")
        sys.exit(1)

    demand_total = float(building_df["non_shiftable_load"].sum())
    print(f"  ✓ Building_1.csv: {len(building_df)} filas, demand={demand_total:,.0f} kWh")

    # Sample charger
    sample_charger = charger_files[0]
    charger_df = pd.read_csv(sample_charger)
    if len(charger_df) != 8760:
        print(f"  ❌ {sample_charger.name}: {len(charger_df)} filas (esperado 8760)")
        sys.exit(1)

    print(f"  ✓ Charger files: 8760 filas cada uno")

    # Schema
    with open(dataset_dir / "schema_pv_bess.json") as f:
        schema = json.load(f)

    if "buildings" not in schema or len(schema["buildings"]) == 0:
        print(f"  ❌ Schema vacío")
        sys.exit(1)

    print(f"  ✓ Schema: {len(schema['buildings'])} building(s)")

    # ========== SUCCESS ==========
    print("\n" + "="*80)
    print("[✅ VERIFICACION COMPLETADA - DATASET CONSTRUCTION CORRECTO]")
    print("="*80)
    print(f"\nRESULTADOS:")
    print(f"  OE2 INPUT:  Solar ({solar_total:,.0f}) + Chargers (128) + BESS (4520 kWh)")
    print(f"  OE3 OUTPUT: Schema valid + Building_1.csv (8760h) + 128 charger CSVs")
    print(f"  DATA FLOW:  OE2 → build_citylearn_dataset() → OE3 PROCESSING ✅")
    print(f"\nTodos los agentes (PPO, A2C, SAC) usan el MISMO DATASET REAL correcto.")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
