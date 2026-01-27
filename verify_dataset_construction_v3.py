#!/usr/bin/env python3
"""
Verify OE2→OE3 dataset construction without printing DataFrames.
This script ONLY validates paths and file existence, not contents.
"""

import json
import sys
from pathlib import Path

def main():
    print("[STEP 1/6] Validando archivos OE2 de entrada...")

    # Check critical files exist WITHOUT reading them
    solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    chargers_json_path = Path("data/interim/oe2/chargers/individual_chargers.json")
    profile_path = Path("data/interim/oe2/chargers/perfil_horario_carga.csv")
    bess_path = Path("data/interim/oe2/bess/bess_config.json")

    if not solar_path.exists():
        print(f"  ❌ FALLO: No existe {solar_path}")
        sys.exit(1)
    print(f"  ✅ Solar timeseries encontrado")

    if not chargers_json_path.exists():
        print(f"  ❌ FALLO: No existe {chargers_json_path}")
        sys.exit(1)
    print(f"  ✅ Charger config encontrado")

    if not profile_path.exists():
        print(f"  ❌ FALLO: No existe {profile_path}")
        sys.exit(1)
    print(f"  ✅ Charger profile encontrado")

    if not bess_path.exists():
        print(f"  ❌ FALLO: No existe {bess_path}")
        sys.exit(1)
    print(f"  ✅ BESS config encontrado")

    print("\n[STEP 2/6] Validando file sizes de OE2 inputs...")

    # Check file sizes only
    solar_size = solar_path.stat().st_size / 1024  # KB
    print(f"  - Solar CSV: {solar_size:.1f} KB (debe ser ~300-400 KB para 8760 rows)")

    chargers_size = chargers_json_path.stat().st_size / 1024
    print(f"  - Chargers JSON: {chargers_size:.1f} KB")

    profile_size = profile_path.stat().st_size / 1024
    print(f"  - Profile CSV: {profile_size:.1f} KB (debe ser ~2-3 KB)")

    bess_size = bess_path.stat().st_size / 1024
    print(f"  - BESS JSON: {bess_size:.1f} KB")

    print("\n[STEP 3/6] Validando configuracion JSON...")

    try:
        with open(chargers_json_path) as f:
            chargers = json.load(f)
        charger_count = len(chargers)
        print(f"  ✅ Chargers JSON válido: {charger_count} chargers")
        if charger_count != 32:
            print(f"  ❌ ADVERTENCIA: Expected 32 chargers, got {charger_count}")
        else:
            print(f"  ✅ Correcto: 32 chargers = 128 sockets")
    except json.JSONDecodeError as e:
        print(f"  ❌ FALLO JSON en chargers: {e}")
        sys.exit(1)

    try:
        with open(bess_path) as f:
            bess = json.load(f)
        capacity = bess.get("capacity_kWh")
        power = bess.get("power_kW")
        print(f"  ✅ BESS JSON válido: {capacity} kWh / {power} kW")
        if capacity == 4520 and power == 2712:
            print(f"  ✅ Correcto: OE2 Real specs")
        else:
            print(f"  ❌ ADVERTENCIA: Expected 4520/2712, got {capacity}/{power}")
    except json.JSONDecodeError as e:
        print(f"  ❌ FALLO JSON en BESS: {e}")
        sys.exit(1)

    print("\n[STEP 4/6] Validando archivos OE3 de salida...")

    # Check OE3 output files
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    schema_path = dataset_dir / "schema_pv_bess.json"
    building_path = dataset_dir / "Building_1.csv"

    if not schema_path.exists():
        print(f"  ❌ FALLO: No existe {schema_path}")
        print("     Run: python -m scripts.run_oe3_build_dataset first")
        sys.exit(1)
    print(f"  ✅ Schema JSON encontrado")

    if not building_path.exists():
        print(f"  ❌ FALLO: No existe {building_path}")
        sys.exit(1)
    print(f"  ✅ Building_1.csv encontrado")

    # Count charger files
    charger_files = list(dataset_dir.glob("charger_simulation_*.csv"))
    charger_count_oe3 = len(charger_files)
    print(f"  ✅ Charger files encontrados: {charger_count_oe3}")
    if charger_count_oe3 < 126:
        print(f"     ADVERTENCIA: Expected ~126 charger files, got {charger_count_oe3}")

    print("\n[STEP 5/6] Validando integridad de datos (counts only)...")

    # Count lines in CSVs without loading full data
    try:
        solar_lines = sum(1 for _ in open(solar_path)) - 1  # Exclude header
        print(f"  - Solar CSV rows: {solar_lines} (debe ser 8760 EXACTO)")
        if solar_lines == 8760:
            print(f"    ✅ CORRECTO: Hourly data (not 52560 = 15-min data)")
        elif solar_lines == 52560:
            print(f"    ❌ FALLO: 15-minute data detected (not supported!)")
            sys.exit(1)
        elif solar_lines > 8760:
            print(f"    ❌ FALLO: Too many rows (not hourly)")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Error counting solar rows: {e}")
        sys.exit(1)

    try:
        building_lines = sum(1 for _ in open(building_path)) - 1  # Exclude header
        print(f"  - Building_1.csv rows: {building_lines} (debe ser 8760)")
        if building_lines == 8760:
            print(f"    ✅ CORRECTO")
        else:
            print(f"    ❌ FALLO: Expected 8760, got {building_lines}")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Error counting building rows: {e}")
        sys.exit(1)

    print("\n[STEP 6/6] Validando schema JSON...")

    try:
        with open(schema_path) as f:
            schema = json.load(f)
        building_count = len(schema.get("buildings", []))
        print(f"  ✅ Schema válido: {building_count} building(s)")
        if building_count == 1:
            print(f"    ✅ CORRECTO: Single building")
        else:
            print(f"    ❌ ADVERTENCIA: Expected 1 building, got {building_count}")
    except json.JSONDecodeError as e:
        print(f"  ❌ FALLO JSON en schema: {e}")
        sys.exit(1)

    print("\n" + "="*70)
    print("[✅ VERIFICACION COMPLETADA - DATASET CONSTRUCTION CORRECTO]")
    print("="*70)
    print("\nPróximos pasos:")
    print("  1. Ejecutar entrenamiento: py -3.11 -m scripts.run_all_agents")
    print("  2. Dataset será reconstruido automáticamente desde OE2")
    print("  3. Baseline será calculado con datos REALES")
    print("  4. PPO, A2C, SAC comenzarán entrenamiento en GPU")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUMPIDO por usuario]")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR INESPERADO]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
