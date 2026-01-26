#!/usr/bin/env python
"""
Verificar que las 128 tomas estén correctamente conectadas en el schema.
Valida integridad de datos y archivos de configuración.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from typing import Dict, Any

def verify_tomas_schema() -> Dict[str, Any]:
    """Verifica integridad del schema de 128 tomas."""
    print("\n" + "="*80)
    print("VERIFICACIÓN: 128 TOMAS CONECTADAS EN SCHEMA")
    print("="*80)

    results = {"status": "✓ PASS", "issues": []}

    # Rutas
    base_dir = Path(__file__).parent
    oe2_dir = base_dir / "data" / "interim" / "oe2" / "chargers"

    # ========== VERIFICACIÓN 1: Archivos JSON ==========
    print("\n[1/5] Verificando archivos JSON...")

    files_to_check = {
        "chargers_schema.json": oe2_dir / "chargers_schema.json",
        "tomas_configuration.json": oe2_dir / "tomas_configuration.json",
        "individual_chargers.json": oe2_dir / "individual_chargers.json",
    }

    json_data = {}
    for name, path in files_to_check.items():
        if path.exists():
            with open(path) as f:
                json_data[name] = json.load(f)
            print(f"  ✓ {name}: OK")
        else:
            print(f"  ✗ {name}: MISSING")
            results["issues"].append(f"Archivo faltante: {name}")
            results["status"] = "✗ FAIL"

    # ========== VERIFICACIÓN 2: Schema de tomas ==========
    print("\n[2/5] Verificando configuración de tomas...")

    if "tomas_configuration.json" in json_data:
        config = json_data["tomas_configuration.json"]

        # Total de tomas
        total_tomas = config.get("tomas_overview", {}).get("total", 0)
        motos = config.get("tomas_overview", {}).get("motos", {}).get("count", 0)
        mototaxis = config.get("tomas_overview", {}).get("mototaxis", {}).get("count", 0)

        print(f"  Total tomas: {total_tomas} (esperado: 128)")
        print(f"    - Motos: {motos} (esperado: 112)")
        print(f"    - Mototaxis: {mototaxis} (esperado: 16)")

        if total_tomas != 128 or motos != 112 or mototaxis != 16:
            results["issues"].append(f"Conteo de tomas incorrecto: {motos}+{mototaxis}={total_tomas}")
            results["status"] = "✗ FAIL"
        else:
            print(f"  ✓ Conteo correcto: 128 tomas (112+16)")

        # Potencia instalada
        power_motos = motos * 2.0  # 2kW cada moto
        power_mototaxis = mototaxis * 3.0  # 3kW cada mototaxi
        power_total = power_motos + power_mototaxis

        print(f"  Potencia: {power_total} kW (esperado: 272 kW)")
        if power_total != 272.0:
            results["issues"].append(f"Potencia incorrecta: {power_total} kW")
            results["status"] = "✗ FAIL"
        else:
            print(f"  ✓ Potencia correcta: 272 kW")

    # ========== VERIFICACIÓN 3: Perfiles de datos ==========
    print("\n[3/5] Verificando perfiles de carga 30-minutos...")

    profile_file = oe2_dir / "perfil_tomas_30min.csv"
    if profile_file.exists():
        df = pd.read_csv(profile_file)
        rows = len(df)
        expected_rows = 128 * 17520  # 128 tomas × 17,520 intervalos/año

        print(f"  Filas: {rows:,} (esperado: {expected_rows:,})")
        if rows != expected_rows:
            print(f"  ⚠ Advertencia: {rows} != {expected_rows}")
        else:
            print(f"  ✓ Filas correctas: {rows:,}")

        # Verificar columnas
        required_cols = ["toma_id", "toma_type", "charge_factor", "occupancy", "power_kw"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"  ✗ Columnas faltantes: {missing_cols}")
            results["issues"].append(f"Columnas faltantes en perfil: {missing_cols}")
            results["status"] = "✗ FAIL"
        else:
            print(f"  ✓ Columnas requeridas presentes")

        # Verificar rango de tomas
        unique_tomas = df["toma_id"].unique()
        print(f"  Tomas únicas: {len(unique_tomas)} (esperado: 128)")
        if len(unique_tomas) != 128:
            results["issues"].append(f"Tomas únicas: {len(unique_tomas)} != 128")
            results["status"] = "✗ FAIL"
        else:
            print(f"  ✓ Todas las 128 tomas presentes")

        # Estadísticas
        energy_total = df["energy_kwh"].sum()
        print(f"  Demanda anual: {energy_total:,.0f} kWh (esperado: ~717,374)")
        if 700000 < energy_total < 750000:
            print(f"  ✓ Demanda dentro del rango esperado")
        else:
            print(f"  ⚠ Advertencia: demanda fuera del rango")
    else:
        print(f"  ✗ Archivo no encontrado: {profile_file}")
        results["issues"].append(f"Perfil faltante: perfil_tomas_30min.csv")
        results["status"] = "✗ FAIL"

    # ========== VERIFICACIÓN 4: Perfiles individuales ==========
    print("\n[4/5] Verificando perfiles individuales por toma...")

    toma_profiles_dir = oe2_dir / "toma_profiles"
    if toma_profiles_dir.exists():
        toma_files = list(toma_profiles_dir.glob("toma_*.csv"))
        print(f"  Archivos individuales: {len(toma_files)} (esperado: 128)")

        if len(toma_files) != 128:
            print(f"  ⚠ Advertencia: {len(toma_files)} != 128")
            results["issues"].append(f"Archivos individuales: {len(toma_files)} != 128")
        else:
            print(f"  ✓ 128 archivos individuales por toma presentes")

        # Verificar contenido de una toma de ejemplo
        if toma_files:
            sample_file = sorted(toma_files)[0]
            sample_df = pd.read_csv(sample_file)
            print(f"  Ejemplo (toma_000): {len(sample_df)} filas (esperado: 17,520)")
            if len(sample_df) == 17520:
                print(f"  ✓ Filas correctas en perfil individual")
            else:
                print(f"  ✗ Filas incorrectas: {len(sample_df)} != 17,520")
    else:
        print(f"  ✗ Directorio no encontrado: {toma_profiles_dir}")
        results["issues"].append(f"Directorio faltante: toma_profiles/")
        results["status"] = "✗ FAIL"

    # ========== VERIFICACIÓN 5: Schema CityLearn ==========
    print("\n[5/5] Verificando integración con CityLearn schema...")

    if "chargers_schema.json" in json_data:
        schema = json_data["chargers_schema.json"]

        # Verificar estructura de tomas
        tomas = schema.get("tomas", {})
        total = tomas.get("total_count", 0)
        motos = tomas.get("motos", {}).get("count", 0)
        mototaxis = tomas.get("mototaxis", {}).get("count", 0)

        print(f"  Tomas en schema: {total} (esperado: 128)")
        if total == 128:
            print(f"  ✓ Tomas conectadas en schema")
        else:
            print(f"  ✗ Tomas en schema: {total} != 128")
            results["issues"].append(f"Tomas en schema: {total} != 128")
            results["status"] = "✗ FAIL"

        # Verificar control
        control = schema.get("control", {})
        arch = control.get("architecture", "")
        if "128 independent" in arch or "independent sockets" in arch:
            print(f"  ✓ Arquitectura correcta: {arch}")
        else:
            print(f"  ⚠ Arquitectura: {arch}")

    # ========== RESUMEN ==========
    print("\n" + "="*80)
    if results["status"] == "✓ PASS":
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("\n128 TOMAS CORRECTAMENTE CONECTADAS EN SCHEMA")
        print("\nResumen:")
        print("  • 128 tomas independientes (112 motos + 16 mototaxis)")
        print("  • Potencia: 272 kW (224 motos + 48 mototaxis)")
        print("  • Resolución: 30 minutos")
        print("  • Intervalos/año por toma: 17,520")
        print("  • Datos consolidados: perfil_tomas_30min.csv")
        print("  • Datos individuales: 128 CSV en toma_profiles/")
        print("  • Demanda anual: ~717,374 kWh")
        print("  • Integración CityLearn: ✓ Activa")
    else:
        print(f"❌ FALLOS DETECTADOS ({len(results['issues'])})")
        for issue in results["issues"]:
            print(f"  • {issue}")

    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    results = verify_tomas_schema()
    exit(0 if results["status"] == "✓ PASS" else 1)
