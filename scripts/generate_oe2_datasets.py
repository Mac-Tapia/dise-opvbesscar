#!/usr/bin/env python3
"""generate_oe2_datasets.py — Pipeline integrado OE2 → CityLearn v2.

Ejecuta los 4 módulos OE2 en secuencia y construye el dataset unificado
para el entorno CityLearn v2 (data/iquitos_ev_mall/).

Flujo canónico (orden de dependencias):
  1. [solar]    solar_pvlib.py     → data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
  2. [chargers] chargers.py        → data/oe2/chargers/chargers_ev_ano_2024_v3.csv
  3. [bess]     bess.py            → data/oe2/bess/bess_ano_2024.csv  (usa solar + chargers)
  4. [mall]     (dato externo)     → data/oe2/demandamallkwh/demandamallhorakwh.csv
  5. [loader]   data_loader.py     → data/iquitos_ev_mall/{solar,bess,chargers,mall}*.csv
  6. [validate] test final         → todos los datasets tienen 8760 filas y columnas requeridas

NOTA: El BESS (paso 3) depende de solar (paso 1) y cargadores (paso 2).
      Chargers es independiente de solar; ambos deben existir antes de BESS.

Uso:
    python scripts/generate_oe2_datasets.py [--skip-solar] [--skip-bess] [--skip-chargers] [--loader-only]

Argumentos opcionales:
    --skip-solar     No regenerar solar (usar datos existentes en data/oe2/)
    --skip-bess      No regenerar BESS (usar datos existentes)
    --skip-chargers  No regenerar chargers (usar datos existentes)
    --loader-only    Solo ejecutar paso 5 (build_citylearn_dataset + save) con datos existentes
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Imports ───────────────────────────────────────────────────────────────────
from src.dimensionamiento.oe2._paths import (
    SOLAR_CANONICAL_CSV,
    BESS_CANONICAL_CSV,
    CHARGERS_CANONICAL_CSV,
    MALL_DEMAND_CANONICAL_CSV,
    CITYLEARN_OUTPUT_DIR,
    SOLAR_HOURLY_ROWS,
)


def _step(label: str) -> None:
    print(f"\n{'='*70}\n  {label}\n{'='*70}")


def run_solar() -> None:
    _step("PASO 1/5 — Generación Solar PV (pvlib)")
    from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
        generate_solar_dataset_citylearn_complete,
        generate_pv_csv_datasets,
    )
    from src.dimensionamiento.oe2._paths import SOLAR_OUTPUT_DIR

    df_solar, _ = generate_solar_dataset_citylearn_complete(
        output_dir=SOLAR_OUTPUT_DIR,
        year=2024,
        verbose=True,
    )
    dataset_file = SOLAR_OUTPUT_DIR / "pv_generation_hourly_citylearn_v2.csv"
    if dataset_file.exists():
        generate_pv_csv_datasets(dataset_path=dataset_file, output_dir=SOLAR_OUTPUT_DIR)
    assert SOLAR_CANONICAL_CSV.exists(), f"ERROR: {SOLAR_CANONICAL_CSV} no generado"
    print(f"\n[OK] Solar -> {SOLAR_CANONICAL_CSV} ({len(df_solar)} filas)")


def run_chargers() -> None:
    _step("PASO 2/5 — Dimensionamiento Cargadores EV")
    from src.dimensionamiento.oe2.disenocargadoresev.chargers import (
        generate_socket_level_dataset_v3,
        generate_chargers_csv_datasets,
    )
    from src.dimensionamiento.oe2._paths import CHARGERS_OUTPUT_DIR

    generate_socket_level_dataset_v3(output_dir=CHARGERS_OUTPUT_DIR, random_seed=42)
    generate_chargers_csv_datasets(output_dir=CHARGERS_OUTPUT_DIR)
    assert CHARGERS_CANONICAL_CSV.exists(), f"ERROR: {CHARGERS_CANONICAL_CSV} no generado"
    print(f"\n[OK] Chargers -> {CHARGERS_CANONICAL_CSV}")


def run_bess() -> None:
    _step("PASO 3/5 — Simulación BESS (basado en solar + cargadores EV reales)")
    from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing
    from src.dimensionamiento.oe2._paths import BESS_OUTPUT_DIR

    assert SOLAR_CANONICAL_CSV.exists(), (
        f"ERROR: Solar no generado: {SOLAR_CANONICAL_CSV}\n"
        "       Ejecutar paso 1 (solar) antes del BESS."
    )
    assert CHARGERS_CANONICAL_CSV.exists(), (
        f"ERROR: Cargadores EV no generados: {CHARGERS_CANONICAL_CSV}\n"
        "       Ejecutar paso 2 (chargers) antes del BESS."
    )

    run_bess_sizing(
        out_dir=BESS_OUTPUT_DIR,
        pv_profile_path=SOLAR_CANONICAL_CSV,
        ev_profile_path=CHARGERS_CANONICAL_CSV,
        mall_demand_path=MALL_DEMAND_CANONICAL_CSV,
    )
    assert BESS_CANONICAL_CSV.exists(), f"ERROR: {BESS_CANONICAL_CSV} no generado"
    print(f"\n[OK] BESS -> {BESS_CANONICAL_CSV}")


def run_loader() -> None:
    _step("PASO 5/6 — Construir dataset OE2 unificado (data/iquitos_ev_mall/)")
    from src.dataset_builder_citylearn.data_loader import (
        build_citylearn_dataset,
        save_citylearn_dataset,
    )

    dataset = build_citylearn_dataset(
        solar_path=SOLAR_CANONICAL_CSV,
        bess_path=BESS_CANONICAL_CSV,
        chargers_path=CHARGERS_CANONICAL_CSV,
        demand_path=MALL_DEMAND_CANONICAL_CSV,
    )
    out_dir = save_citylearn_dataset(dataset, output_dir=CITYLEARN_OUTPUT_DIR)
    print(f"\n[OK] Dataset OE2 unificado -> {out_dir}")


def run_schema_builder() -> None:
    """Paso 6: Regenera TODOS los datasets CityLearn v2 desde datos OE2 actualizados.

    Siempre se ejecuta — garantiza que data/interim/citylearn_v2/ esté sincronizado
    con los datos reales de data/iquitos_ev_mall/:
      energy_simulation.csv  ← solar_generation.csv + mall_demand.csv
      weather.csv            ← solar_generation.csv (GHI, temperatura)
      carbon_intensity.csv   ← co2_emissions.csv (factor CO2 diesel Iquitos 0.39-0.63)
      pricing.csv            ← tariffs_osinergmin.csv (HP=0.46 / HFP=0.29 S./kWh)
      ev_charger_motos.csv   ← chargers_timeseries.csv (30 sockets motos)
      ev_charger_mototaxis.csv ← chargers_timeseries.csv (8 sockets mototaxis)
      schema_iquitos.json    ← todos los anteriores + BESS/PV specs de OE2Metadata
    """
    _step("PASO 6/6 — Actualizar datasets CityLearn v2 (data/interim/citylearn_v2/)")
    import logging
    from src.citylearnv2.schema_builder import build_citylearn_schema
    from src.dimensionamiento.oe2.oe2_metadata import reload_metadata

    # Recargar metadatos OE2 para capturar valores recién generados
    reload_metadata()

    # Eliminar schema obsoleto para garantizar regeneración completa
    interim_dir = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2"
    schema_file = interim_dir / "schema_iquitos.json"
    if schema_file.exists():
        schema_file.unlink()

    logging.basicConfig(level=logging.WARNING)  # suprimir INFO redundante
    schema_path = build_citylearn_schema()

    # Verificar archivos generados
    expected = [
        "energy_simulation.csv",
        "weather.csv",
        "carbon_intensity.csv",
        "pricing.csv",
        "ev_charger_motos.csv",
        "ev_charger_mototaxis.csv",
        "schema_iquitos.json",
    ]
    all_ok = True
    for fname in expected:
        p = interim_dir / fname
        status = "OK " if p.exists() else "FAIL"
        print(f"  [{status}] {fname}")
        if not p.exists():
            all_ok = False

    if all_ok:
        print(f"\n[OK] CityLearn v2 datasets actualizados -> {interim_dir}")
    else:
        print("\n[WARN] Algunos datasets CityLearn v2 no se generaron")
        sys.exit(1)


def validate_outputs() -> None:
    _step("VALIDACIÓN FINAL — OE2 + CityLearn v2")
    import pandas as pd

    INTERIM_CL = _PROJECT_ROOT / "data" / "interim" / "citylearn_v2"

    required = {
        # OE2 raw
        "solar OE2":    (SOLAR_CANONICAL_CSV,       "potencia_kw"),
        "bess OE2":     (BESS_CANONICAL_CSV,         "soc_percent"),
        "chargers OE2": (CHARGERS_CANONICAL_CSV,     "ev_energia_motos_kwh"),
        "mall OE2":     (MALL_DEMAND_CANONICAL_CSV,  "mall_demand_kwh"),
        # OE2 procesados (data/iquitos_ev_mall/)
        "solar iqts":   (CITYLEARN_OUTPUT_DIR / "solar_generation.csv",    "potencia_kw"),
        "bess iqts":    (CITYLEARN_OUTPUT_DIR / "bess_timeseries.csv",      "soc_percent"),
        "chargers iqts":(CITYLEARN_OUTPUT_DIR / "chargers_timeseries.csv",  "ev_energia_motos_kwh"),
        "mall iqts":    (CITYLEARN_OUTPUT_DIR / "mall_demand.csv",          "mall_demand_kwh"),
        "co2 iqts":     (CITYLEARN_OUTPUT_DIR / "co2_emissions.csv",        "co2_factor_kg_kwh"),
        "tariffs iqts": (CITYLEARN_OUTPUT_DIR / "tariffs_osinergmin.csv",   "tarifa_total_soles_kwh"),
        # CityLearn v2 (data/interim/citylearn_v2/)
        "energy_sim":   (INTERIM_CL / "energy_simulation.csv",  "solar_generation"),
        "weather":      (INTERIM_CL / "weather.csv",            "outdoor_dry_bulb_temperature"),
        "carbon_int":   (INTERIM_CL / "carbon_intensity.csv",   "carbon_intensity"),
        "pricing":      (INTERIM_CL / "pricing.csv",            "electricity_pricing"),
        "ev_motos":     (INTERIM_CL / "ev_charger_motos.csv",   "electric_vehicle_charger_state"),
        "ev_mototaxis": (INTERIM_CL / "ev_charger_mototaxis.csv","electric_vehicle_charger_state"),
        "schema":       (INTERIM_CL / "schema_iquitos.json",    None),
    }

    all_ok = True
    for name, (path, required_col) in required.items():
        if not path.exists():
            print(f"  [FAIL] {name}: {path.name} — MISSING")
            all_ok = False
            continue
        if path.suffix == ".json":
            print(f"  [OK ] {name}: {path.name}")
            continue
        df = pd.read_csv(path, nrows=1)
        if required_col and required_col not in df.columns:
            print(f"  [FAIL] {name}: columna '{required_col}' no encontrada en {path.name}")
            all_ok = False
            continue
        n = sum(1 for _ in open(path)) - 1  # count data rows
        ok = n == SOLAR_HOURLY_ROWS
        status = "OK " if ok else "WARN"
        print(f"  [{status}] {name}: {n} filas, '{required_col}' presente — {path.name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n[PASS] Todos los datasets validados correctamente.")
    else:
        print("\n[WARN] Algunos datasets tienen problemas — ver detalles arriba.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline integrado OE2 → CityLearn v2")
    parser.add_argument("--skip-solar", action="store_true", help="No regenerar solar")
    parser.add_argument("--skip-bess", action="store_true", help="No regenerar BESS")
    parser.add_argument("--skip-chargers", action="store_true", help="No regenerar chargers")
    parser.add_argument("--loader-only", action="store_true", help="Solo ejecutar data_loader (paso 5)")
    args = parser.parse_args()

    t0 = time.time()

    if not args.loader_only:
        if not args.skip_solar:
            run_solar()
        else:
            print("[SKIP] Solar — usando datos existentes")

        if not args.skip_chargers:
            run_chargers()
        else:
            print("[SKIP] Chargers — usando datos existentes")

        if not args.skip_bess:
            run_bess()
        else:
            print("[SKIP] BESS — usando datos existentes")

        _step("PASO 4/5 — Verificar demanda mall (dato externo)")
        assert MALL_DEMAND_CANONICAL_CSV.exists(), (
            f"ERROR: {MALL_DEMAND_CANONICAL_CSV} no existe. "
            "La demanda mall es un dato externo — debe existir antes de correr el pipeline."
        )
        print(f"  [OK] Mall demand existente: {MALL_DEMAND_CANONICAL_CSV}")

    run_loader()
    run_schema_builder()
    validate_outputs()

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  Pipeline completo en {elapsed:.1f}s")
    print(f"  Datos CityLearn v2 listos en: {CITYLEARN_OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
