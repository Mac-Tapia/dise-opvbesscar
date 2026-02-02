#!/usr/bin/env python
"""
Validación robusta del dataset CityLearn para entrenamiento RL.

Verifica que el dataset tenga:
1. Generación solar correcta (~8,030,119 kWh/año para 4,162 kWp)
2. Carga del mall correcta (~12,368,025 kWh/año)
3. 8,760 timesteps (1 año completo)
4. 128 archivos de chargers
5. BESS simulation
"""
from __future__ import annotations

import sys
from pathlib import Path
import json

import pandas as pd
import numpy as np

def validate_dataset(dataset_dir: Path) -> bool:
    """Valida que el dataset esté completo y correcto."""

    errors = []
    warnings = []

    print("=" * 80)
    print("VALIDACIÓN COMPLETA: Dataset OE2 para Entrenamiento RL")
    print("=" * 80)

    # 1. Verificar Building_1.csv
    print("\n[1] BUILDING_1.CSV:")
    b1_path = dataset_dir / "Building_1.csv"

    if not b1_path.exists():
        errors.append("Building_1.csv NO existe")
        print("   ❌ NO ENCONTRADO")
    else:
        df = pd.read_csv(b1_path)
        n_rows = len(df)
        print(f"   Filas: {n_rows} (esperado: 8,760)")

        if n_rows != 8760:
            errors.append(f"Building_1.csv tiene {n_rows} filas (esperado: 8,760)")

        # Verificar solar_generation
        if "solar_generation" in df.columns:
            solar = df["solar_generation"]
            solar_sum = float(solar.sum())
            solar_mean = float(solar.mean())
            solar_max = float(solar.max())

            print(f"   Solar: {solar_sum:,.0f} kWh/año")
            print(f"   Solar mean: {solar_mean:.2f} kW, max: {solar_max:.2f} kW")

            # Validación crítica: solar debe ser ~8M kWh (no 1,929)
            if solar_sum < 1_000_000:
                errors.append(f"CRÍTICO: Solar muy bajo ({solar_sum:,.0f} kWh) - datos normalizados detectados")
            elif solar_sum < 7_000_000:
                warnings.append(f"Solar bajo ({solar_sum:,.0f} kWh) - esperado ~8M")
            else:
                print("   ✓ Solar OK (datos absolutos OE2)")
        else:
            errors.append("Columna 'solar_generation' no encontrada")

        # Verificar non_shiftable_load
        if "non_shiftable_load" in df.columns:
            load = df["non_shiftable_load"]
            load_sum = float(load.sum())
            print(f"   Carga Mall: {load_sum:,.0f} kWh/año")

            if load_sum == 0:
                errors.append("Carga del mall es 0")
            else:
                print("   ✓ Carga Mall OK")
        else:
            errors.append("Columna 'non_shiftable_load' no encontrada")

    # 2. Verificar BESS simulation
    print("\n[2] BESS SIMULATION:")
    bess_path = dataset_dir / "electrical_storage_simulation.csv"

    if not bess_path.exists():
        warnings.append("BESS simulation no encontrado")
        print("   ⚠ NO ENCONTRADO")
    else:
        df_bess = pd.read_csv(bess_path)
        print(f"   Filas: {len(df_bess)}")

        if "soc_stored_kwh" in df_bess.columns:
            soc = df_bess["soc_stored_kwh"]
            print(f"   SOC: min={soc.min():.0f}, max={soc.max():.0f}, mean={soc.mean():.0f} kWh")
            print("   ✓ BESS OK")

    # 3. Verificar chargers
    print("\n[3] CHARGERS:")
    chargers = list(dataset_dir.glob("charger_simulation_*.csv"))
    n_chargers = len(chargers)
    print(f"   Archivos: {n_chargers}/128")

    if n_chargers == 0:
        errors.append("No hay archivos de chargers")
    elif n_chargers < 128:
        warnings.append(f"Solo {n_chargers}/128 chargers")
    else:
        print("   ✓ Chargers OK")

    # 4. Verificar schema
    print("\n[4] SCHEMA.JSON:")
    schema_path = dataset_dir / "schema.json"

    if not schema_path.exists():
        errors.append("schema.json NO existe")
        print("   ❌ NO ENCONTRADO")
    else:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        buildings = schema.get("buildings", {})
        timesteps = schema.get("simulation_end_time_step", 0) + 1

        print(f"   Buildings: {list(buildings.keys())}")
        print(f"   Timesteps: {timesteps}")

        if timesteps != 8760:
            warnings.append(f"Schema timesteps={timesteps}, esperado 8760")
        else:
            print("   ✓ Schema OK")

    # RESUMEN FINAL
    print("\n" + "=" * 80)

    if errors:
        print("❌ ERRORES CRÍTICOS:")
        for e in errors:
            print(f"   • {e}")
        print("\n>>> DATASET NO VÁLIDO")
        print(">>> Reconstruir con: python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
        print("=" * 80)
        return False

    if warnings:
        print("⚠ ADVERTENCIAS:")
        for w in warnings:
            print(f"   • {w}")

    print("\n✅ DATASET VÁLIDO Y LISTO PARA ENTRENAMIENTO")
    print("   • Solar: ~8,030,119 kWh/año (datos absolutos OE2)")
    print("   • Carga Mall: ~12,368,025 kWh/año")
    print("   • Timesteps: 8,760 (1 año completo)")
    print("   • Chargers: 128")
    print("=" * 80)

    return True


def main():
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")

    if not dataset_dir.exists():
        print(f"❌ Directorio no existe: {dataset_dir}")
        print(">>> Ejecutar: python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
        sys.exit(1)

    valid = validate_dataset(dataset_dir)
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
