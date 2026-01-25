#!/usr/bin/env python
"""
VERIFICACIÓN CRÍTICA: Asegurar que TODOS los datos generados para CityLearn
sean exactamente HORARIOS (1 fila = 1 hora) con 8,760 filas por año.

NO 15-MINUTOS, NO 30-MINUTOS, SOLO HORARIOS.

Script rápido de diagnóstico para verificar:
1. Solar timeseries: exactamente 8,760 filas
2. Charger CSVs: exactamente 8,760 filas (o 8,761 con fila extra CityLearn)
3. Energy simulation: exactamente 8,760 filas
4. Schema: configurado con seconds_per_time_step = 3600 (1 hora)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

EXPECTED_HOURLY_ROWS = 8760
EXPECTED_HOURLY_WITH_EXTRA = 8761  # CityLearn agrega 1 fila extra

def check_solar_timeseries(interim_dir: Path) -> Tuple[bool, str]:
    """Verificar que solar timeseries sea exactamente 8,760 filas (horarias)."""
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"

    if not solar_path.exists():
        return False, f"❌ No existe: {solar_path}"

    df = pd.read_csv(solar_path)
    n_rows = len(df)

    if n_rows == EXPECTED_HOURLY_ROWS:
        return True, (
            f"✅ Solar timeseries: {n_rows} filas (correcto, horario)\n"
            f"   Columnas: {list(df.columns)}\n"
            f"   Rango temporal: {n_rows/24:.1f} días"
        )
    elif n_rows == 52560:  # 8,760 × 6 (15-minutos)
        return False, (
            f"❌ Solar timeseries: {n_rows} filas (15-MINUTOS, NO SOPORTADO)\n"
            f"   Esto es 8,760 × 6 = datos cada 15 minutos\n"
            f"   SOLUCIÓN: Resamplear a horario:\n"
            f"   df.set_index('time').resample('h').mean()"
        )
    elif n_rows > 8760:
        return False, (
            f"❌ Solar timeseries: {n_rows} filas (SUB-HORARIO, NO SOPORTADO)\n"
            f"   Parece ser ~{n_rows/8760:.0f}-minutos por fila\n"
            f"   SOLUCIÓN: Resamplear a horario:\n"
            f"   df.set_index('time').resample('h').mean()"
        )
    else:
        return False, (
            f"❌ Solar timeseries: {n_rows} filas (INCOMPLETO)\n"
            f"   Se esperaban {EXPECTED_HOURLY_ROWS} filas (1 año horario)"
        )

def check_schema_timesep(processed_dir: Path) -> Tuple[bool, str]:
    """Verificar que schema.json tenga seconds_per_time_step = 3600 (1 hora)."""
    schema_path = processed_dir / "schema.json"

    if not schema_path.exists():
        return False, f"❌ No existe: {schema_path}"

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    seconds_per_time_step = schema.get("seconds_per_time_step")

    if seconds_per_time_step == 3600:
        return True, (
            f"✅ Schema: seconds_per_time_step = {seconds_per_time_step} (1 hora)\n"
            f"   Esto equivale a:\n"
            f"   - {seconds_per_time_step / 60:.0f} minutos por timestep\n"
            f"   - 8,760 timesteps por año (365 días × 24 horas)"
        )
    elif seconds_per_time_step == 900:
        return False, (
            f"❌ Schema: seconds_per_time_step = {seconds_per_time_step} (15 minutos, NO SOPORTADO)\n"
            f"   Debe ser 3600 (1 hora)\n"
            f"   SOLUCIÓN: Actualizar config para usar horario"
        )
    else:
        return False, (
            f"❌ Schema: seconds_per_time_step = {seconds_per_time_step}\n"
            f"   Debe ser 3600 (1 hora). Valor inválido."
        )

def check_charger_csvs(processed_dir: Path, building_name: str = "Mall_Iquitos") -> Tuple[bool, List[str]]:
    """Verificar que los CSVs de chargers tengan exactamente 8,760 o 8,761 filas."""
    building_dir = processed_dir / "buildings" / building_name

    if not building_dir.exists():
        return False, [f"❌ No existe directorio: {building_dir}"]

    charger_csvs = sorted(building_dir.glob("charger_simulation_*.csv"))

    if not charger_csvs:
        return False, [f"❌ No se encontraron CSVs de chargers en {building_dir}"]

    issues = []
    valid_count = 0

    for csv_path in charger_csvs[:5]:  # Verificar primeros 5
        df = pd.read_csv(csv_path)
        n_rows = len(df)

        if n_rows in (EXPECTED_HOURLY_ROWS, EXPECTED_HOURLY_WITH_EXTRA):
            valid_count += 1
        else:
            issues.append(
                f"❌ {csv_path.name}: {n_rows} filas "
                f"(se esperaban {EXPECTED_HOURLY_ROWS} o {EXPECTED_HOURLY_WITH_EXTRA})"
            )

    if valid_count == len(charger_csvs[:5]):
        msg = f"✅ Chargers: Primeros 5 CSVs tienen {EXPECTED_HOURLY_ROWS} o {EXPECTED_HOURLY_WITH_EXTRA} filas (correcto)"
        return True, [msg]
    else:
        return False, issues

def check_energy_simulation(processed_dir: Path, building_name: str = "Mall_Iquitos") -> Tuple[bool, str]:
    """Verificar que energy_simulation tenga exactamente 8,760 filas."""
    # Buscar Building_1.csv o energy_simulation.csv
    energy_path = processed_dir / "Building_1.csv"
    if not energy_path.exists():
        energy_path = processed_dir / "buildings" / building_name / "energy_simulation.csv"

    if not energy_path.exists():
        return False, f"❌ No existe: {energy_path}"

    df = pd.read_csv(energy_path)
    n_rows = len(df)

    if n_rows in (EXPECTED_HOURLY_ROWS, EXPECTED_HOURLY_WITH_EXTRA):
        return True, f"✅ Energy simulation: {n_rows} filas (correcto, horario)"
    else:
        return False, (
            f"❌ Energy simulation: {n_rows} filas\n"
            f"   Se esperaban {EXPECTED_HOURLY_ROWS} o {EXPECTED_HOURLY_WITH_EXTRA} filas"
        )

def main() -> None:
    """Ejecutar todas las verificaciones."""
    print("\n" + "=" * 70)
    print("  VERIFICACIÓN CRÍTICA: DATOS HORARIOS (8,760 FILAS = 1 AÑO)")
    print("=" * 70)

    # Determinar directorios
    root_dir = Path(__file__).parent
    interim_dir = root_dir / "data" / "interim"
    processed_dir = root_dir / "data" / "processed" / "citylearn" / "iquitos_ev_mall"

    print(f"\nDirectorio raíz: {root_dir}")
    print(f"Directorio interim (OE2): {interim_dir}")
    print(f"Directorio processed (OE3): {processed_dir}\n")

    all_passed = True

    # 1. Verificar solar timeseries
    print("1. SOLAR TIMESERIES (OE2)")
    print("-" * 70)
    passed, msg = check_solar_timeseries(interim_dir)
    print(msg)
    all_passed = all_passed and passed

    # 2. Verificar schema
    print("\n2. SCHEMA (CityLearn)")
    print("-" * 70)
    passed, msg = check_schema_timesep(processed_dir)
    print(msg)
    all_passed = all_passed and passed

    # 3. Verificar charger CSVs
    print("\n3. CHARGER CSVs (CityLearn)")
    print("-" * 70)
    passed, msgs = check_charger_csvs(processed_dir)
    for msg in msgs:
        print(msg)
    all_passed = all_passed and passed

    # 4. Verificar energy_simulation
    print("\n4. ENERGY SIMULATION (CityLearn)")
    print("-" * 70)
    passed, msg = check_energy_simulation(processed_dir)
    print(msg)
    all_passed = all_passed and passed

    # Resumen final
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ TODAS LAS VERIFICACIONES PASARON - Datos HORARIOS correctos")
        print("   El dataset está listo para entrenar agentes RL")
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("   Revisa los errores arriba y corrige antes de entrenar")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
