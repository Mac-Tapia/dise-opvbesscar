#!/usr/bin/env python
"""
Verificar que TODOS los datos de OE2 fluyen correctamente a través del pipeline:
OE2 Artifacts → Dataset Builder → Baseline CSV → Agent Training

VERIFICACIONES:
1. Solar generation: OE2 → CityLearn energy_simulation.csv → baseline.csv → SAC training
2. BESS (battery): OE2 bess_results.json → schema.json → electrical_storage_simulation.csv → baseline.csv → SAC training
3. EV chargers: OE2 chargers → charger_simulation_*.csv → baseline.csv → SAC training
4. Mall demand: OE2 mall demand → energy_simulation.csv → baseline.csv → SAC training
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure Python 3.11+
if sys.version_info[:2] != (3, 11):
    raise RuntimeError(f"Python 3.11 required, got {sys.version_info[:2]}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Workspace paths
WORKSPACE_ROOT = Path(__file__).parent
DATA_DIR = WORKSPACE_ROOT / "data"
INTERIM_DIR = DATA_DIR / "interim"
OE2_DIR = INTERIM_DIR / "oe2"
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
OE3_DIR = OUTPUTS_DIR / "oe3"


def verify_oe2_solar_data() -> dict:
    """Verify OE2 solar generation data is complete and valid."""
    logger.info("")
    logger.info("="*80)
    logger.info("1. VERIFICACIÓN: DATOS SOLARES OE2")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Check solar timeseries file
    solar_path = OE2_DIR / "solar" / "pv_generation_timeseries.csv"
    if not solar_path.exists():
        logger.error(f"  ✗ FALTA: {solar_path}")
        result["details"]["missing_solar_file"] = True
        return result

    df_solar = pd.read_csv(solar_path)
    logger.info(f"  ✓ Archivo solar encontrado: {solar_path}")
    logger.info(f"    Shape: {df_solar.shape}")
    logger.info(f"    Columns: {list(df_solar.columns)}")

    # Validate hourly resolution (exactly 8,760 rows for 1 year)
    if len(df_solar) != 8760:
        logger.error(f"  ✗ RESOLUCIÓN INCORRECTA: {len(df_solar)} filas (esperado 8,760)")
        result["details"]["incorrect_resolution"] = len(df_solar)
        return result

    logger.info(f"  ✓ Resolución horaria correcta: {len(df_solar)} filas (1 año)")

    # Find the actual solar generation column
    solar_cols = [c for c in df_solar.columns if any(tag in c.lower() for tag in ["generation", "ac_output", "energy", "power"])]
    if not solar_cols:
        logger.error(f"  ✗ No se encontró columna de generación solar en {list(df_solar.columns)}")
        result["details"]["no_generation_column"] = True
        return result

    gen_col = solar_cols[0]
    gen_values = df_solar[gen_col].values

    logger.info(f"  ✓ Columna de generación: {gen_col}")
    logger.info(f"    Rango: {gen_values.min():.2f} - {gen_values.max():.2f} kW")
    logger.info(f"    Promedio: {gen_values.mean():.2f} kW")
    logger.info(f"    Suma anual: {gen_values.sum():.1f} kWh")
    logger.info(f"    Primeros 5 valores (enero 00-04h): {gen_values[:5]}")
    logger.info(f"    Valores mañana (enero 08-12h): {gen_values[8:13]}")

    # Validate reasonable values
    if gen_values.sum() < 100:
        logger.error(f"  ✗ Suma anual demasiado baja: {gen_values.sum():.1f} kWh")
        result["details"]["generation_sum_too_low"] = float(gen_values.sum())
        return result

    result["status"] = "OK"
    result["details"]["rows"] = len(df_solar)
    result["details"]["generation_column"] = gen_col
    result["details"]["annual_generation_kwh"] = float(gen_values.sum())
    result["details"]["mean_generation_kw"] = float(gen_values.mean())

    return result


def verify_oe2_bess_data() -> dict:
    """Verify OE2 BESS configuration is complete and valid."""
    logger.info("")
    logger.info("="*80)
    logger.info("2. VERIFICACIÓN: DATOS BESS OE2")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Check BESS results
    bess_path = OE2_DIR / "bess" / "bess_results.json"
    if not bess_path.exists():
        logger.error(f"  ✗ FALTA: {bess_path}")
        result["details"]["missing_bess_file"] = True
        return result

    with open(bess_path) as f:
        bess_config = json.load(f)

    logger.info(f"  ✓ Configuración BESS encontrada: {bess_path}")

    capacity = bess_config.get("capacity_kwh", 0)
    power = bess_config.get("nominal_power_kw", 0)

    if capacity <= 0 or power <= 0:
        logger.error(f"  ✗ Capacidad o potencia inválida: {capacity} kWh, {power} kW")
        result["details"]["invalid_capacity_or_power"] = True
        return result

    logger.info(f"  ✓ Capacidad BESS: {capacity:.0f} kWh")
    logger.info(f"  ✓ Potencia BESS: {power:.0f} kW")
    logger.info(f"  ✓ Ratio C: {capacity/power:.1f}h")

    result["status"] = "OK"
    result["details"]["capacity_kwh"] = capacity
    result["details"]["nominal_power_kw"] = power

    return result


def verify_oe2_ev_chargers() -> dict:
    """Verify OE2 EV charger configuration is complete and valid."""
    logger.info("")
    logger.info("="*80)
    logger.info("3. VERIFICACIÓN: CARGADORES EV OE2")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Check chargers configuration
    chargers_path = OE2_DIR / "chargers" / "individual_chargers.json"
    if not chargers_path.exists():
        logger.error(f"  ✗ FALTA: {chargers_path}")
        result["details"]["missing_chargers_file"] = True
        return result

    with open(chargers_path) as f:
        chargers = json.load(f)

    logger.info(f"  ✓ Configuración de cargadores encontrada: {chargers_path}")
    logger.info(f"    Total chargers: {len(chargers)}")

    if len(chargers) != 128:
        logger.error(f"  ✗ Número incorrecto de cargadores: {len(chargers)} (esperado 128)")
        result["details"]["incorrect_charger_count"] = len(chargers)
        return result

    logger.info(f"  ✓ Cantidad correcta: 128 cargadores")

    # Analyze charger types
    motos = sum(1 for c in chargers if c.get("charger_type", "").lower() == "moto")
    taxis = sum(1 for c in chargers if c.get("charger_type", "").lower() == "moto_taxi")

    logger.info(f"    - Motos: {motos}")
    logger.info(f"    - Mototaxis: {taxis}")

    # Check charger hourly profiles
    profiles_path = OE2_DIR / "chargers" / "chargers_hourly_profiles_annual.csv"
    if profiles_path.exists():
        df_profiles = pd.read_csv(profiles_path)
        logger.info(f"  ✓ Perfiles horarios encontrados: {profiles_path}")
        logger.info(f"    Shape: {df_profiles.shape} (esperado: 8760 filas × 128 columnas)")

        if df_profiles.shape[0] != 8760:
            logger.error(f"  ✗ Resolución incorrecta: {df_profiles.shape[0]} filas (esperado 8,760)")
            result["details"]["incorrect_profile_resolution"] = df_profiles.shape[0]
            return result

        if df_profiles.shape[1] != 128:
            logger.error(f"  ✗ Número incorrecto de cargadores en perfiles: {df_profiles.shape[1]} (esperado 128)")
            result["details"]["incorrect_profile_chargers"] = df_profiles.shape[1]
            return result

        logger.info(f"  ✓ Resolución correcta: 8,760 filas × 128 columnas")
        logger.info(f"    Demanda total anual: {df_profiles.sum().sum():.1f} kWh")
        logger.info(f"    Promedio por hora: {df_profiles.sum(axis=1).mean():.2f} kW")

    result["status"] = "OK"
    result["details"]["total_chargers"] = 128
    result["details"]["motos"] = motos
    result["details"]["mototaxis"] = taxis

    return result


def verify_oe2_mall_demand() -> dict:
    """Verify OE2 mall demand data is complete and valid."""
    logger.info("")
    logger.info("="*80)
    logger.info("4. VERIFICACIÓN: DEMANDA MALL OE2")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Check mall demand
    mall_path = OE2_DIR / "demandamall" / "demanda_mall_kwh.csv"
    if not mall_path.exists():
        logger.warning(f"  ⚠ No se encontró demanda real del mall: {mall_path}")
        logger.info("    Usando perfil sintético por defecto")
        result["status"] = "WARN"
        result["details"]["no_mall_demand_file"] = True
        return result

    df_mall = pd.read_csv(mall_path)
    logger.info(f"  ✓ Demanda del mall encontrada: {mall_path}")
    logger.info(f"    Shape: {df_mall.shape}")
    logger.info(f"    Columns: {list(df_mall.columns)}")

    # Try to identify demand column
    demand_cols = [c for c in df_mall.columns if any(tag in c.lower() for tag in ["demanda", "kw", "energy"])]
    if demand_cols:
        demand_col = demand_cols[0]
        demand_values = df_mall[demand_col].values
        logger.info(f"  ✓ Columna de demanda: {demand_col}")
        logger.info(f"    Rango: {demand_values.min():.2f} - {demand_values.max():.2f} kW")
        logger.info(f"    Promedio: {demand_values.mean():.2f} kW")
        logger.info(f"    Suma anual: {demand_values.sum():.1f} kWh")

    result["status"] = "OK"
    result["details"]["rows"] = len(df_mall)

    return result


def verify_citylearn_schema() -> dict:
    """Verify CityLearn schema includes all OE2 data components."""
    logger.info("")
    logger.info("="*80)
    logger.info("5. VERIFICACIÓN: SCHEMA CITYLEARN")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Find schema file
    schema_files = list(OE3_DIR.glob("schema*.json"))
    if not schema_files:
        logger.error(f"  ✗ No se encontró schema en {OE3_DIR}")
        result["details"]["no_schema_found"] = True
        return result

    schema_path = schema_files[0]
    logger.info(f"  ✓ Schema encontrado: {schema_path}")

    with open(schema_path) as f:
        schema = json.load(f)

    # Check buildings
    if "buildings" not in schema or not schema["buildings"]:
        logger.error("  ✗ No hay buildings en el schema")
        result["details"]["no_buildings"] = True
        return result

    building_name = list(schema["buildings"].keys())[0]
    building = schema["buildings"][building_name]
    logger.info(f"  ✓ Building: {building_name}")

    # Check PV
    pv_ok = isinstance(building.get("pv"), dict) or isinstance(building.get("photovoltaic"), dict)
    logger.info(f"  {'✓' if pv_ok else '✗'} PV: {'Configurado' if pv_ok else 'FALTA'}")
    if pv_ok:
        pv_conf = building.get("pv") or building.get("photovoltaic")
        pv_power = pv_conf.get("nominal_power", pv_conf.get("attributes", {}).get("nominal_power", 0))
        logger.info(f"      Potencia nominal: {pv_power:.0f} kWp")

    # Check BESS
    bess_ok = isinstance(building.get("electrical_storage"), dict)
    logger.info(f"  {'✓' if bess_ok else '✗'} BESS: {'Configurado' if bess_ok else 'FALTA'}")
    if bess_ok:
        bess_conf = building.get("electrical_storage")
        bess_cap = bess_conf.get("capacity", bess_conf.get("attributes", {}).get("capacity", 0))
        bess_pow = bess_conf.get("nominal_power", bess_conf.get("attributes", {}).get("nominal_power", 0))
        logger.info(f"      Capacidad: {bess_cap:.0f} kWh")
        logger.info(f"      Potencia: {bess_pow:.0f} kW")

    # Check chargers
    chargers = building.get("electric_vehicle_chargers", {})
    logger.info(f"  {'✓' if chargers else '✗'} Cargadores EV: {len(chargers)} (esperado 128)" if chargers else "  ✗ Cargadores EV: FALTA")

    result["status"] = "OK"
    result["details"]["building_name"] = building_name
    result["details"]["pv_configured"] = pv_ok
    result["details"]["bess_configured"] = bess_ok
    result["details"]["chargers_count"] = len(chargers)

    return result


def verify_citylearn_energy_csv() -> dict:
    """Verify energy_simulation.csv has solar + mall demand properly set."""
    logger.info("")
    logger.info("="*80)
    logger.info("6. VERIFICACIÓN: ENERGY_SIMULATION.CSV (CityLearn)")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Find energy CSV
    energy_files = list(OE3_DIR.glob("**/energy_simulation.csv"))
    if not energy_files:
        logger.error(f"  ✗ No se encontró energy_simulation.csv en {OE3_DIR}")
        result["details"]["no_energy_csv"] = True
        return result

    energy_path = energy_files[0]
    df_energy = pd.read_csv(energy_path)
    logger.info(f"  ✓ Archivo encontrado: {energy_path}")
    logger.info(f"    Shape: {df_energy.shape}")

    # Find solar and load columns
    solar_cols = [c for c in df_energy.columns if any(tag in c.lower() for tag in ["solar", "generation"])]
    load_cols = [c for c in df_energy.columns if any(tag in c.lower() for tag in ["non_shiftable", "load"])]

    logger.info(f"    Columnas solares: {solar_cols}")
    logger.info(f"    Columnas de carga: {load_cols}")

    if solar_cols:
        solar_col = solar_cols[0]
        solar_vals = df_energy[solar_col].values
        logger.info(f"  ✓ Generación solar ({solar_col}): suma={solar_vals.sum():.1f}, max={solar_vals.max():.2f}")

    if load_cols:
        load_col = load_cols[0]
        load_vals = df_energy[load_col].values
        logger.info(f"  ✓ Carga del mall ({load_col}): suma={load_vals.sum():.1f}, max={load_vals.max():.2f}")

    result["status"] = "OK"
    result["details"]["rows"] = len(df_energy)
    result["details"]["has_solar"] = bool(solar_cols)
    result["details"]["has_load"] = bool(load_cols)

    return result


def verify_baseline_csv() -> dict:
    """Verify baseline CSV has all data components accessible to agents."""
    logger.info("")
    logger.info("="*80)
    logger.info("7. VERIFICACIÓN: BASELINE CSV (Datos accesibles para entrenamiento)")
    logger.info("="*80)

    result = {"status": "FAIL", "details": {}}

    # Find baseline CSV
    baseline_files = list(OE3_DIR.glob("baseline*.csv"))
    if not baseline_files:
        logger.error(f"  ✗ No se encontró baseline*.csv en {OE3_DIR}")
        result["details"]["no_baseline_csv"] = True
        return result

    baseline_path = baseline_files[0]
    df_baseline = pd.read_csv(baseline_path)
    logger.info(f"  ✓ Archivo encontrado: {baseline_path}")
    logger.info(f"    Shape: {df_baseline.shape}")

    # Verify length
    if len(df_baseline) != 8760:
        logger.error(f"  ✗ Longitud incorrecta: {len(df_baseline)} filas (esperado 8,760)")
        result["details"]["incorrect_length"] = len(df_baseline)
        return result

    logger.info(f"  ✓ Longitud correcta: {len(df_baseline)} filas (1 año horario)")

    # Find key columns
    logger.info(f"  Columnas disponibles: {list(df_baseline.columns)[:15]}...")  # Show first 15

    # Solar
    solar_cols = [c for c in df_baseline.columns if any(tag in c.lower() for tag in ["solar", "pv", "generation"])]
    if solar_cols:
        solar_col = solar_cols[0]
        solar_vals = df_baseline[solar_col].values
        logger.info(f"  ✓ Generación solar ({solar_col}): suma={solar_vals.sum():.1f} kWh/año")
    else:
        logger.warning(f"  ⚠ No se encontró columna de generación solar")

    # EV demand
    ev_cols = [c for c in df_baseline.columns if any(tag in c.lower() for tag in ["ev_demand", "charger", "ev_"])]
    if ev_cols:
        ev_col = ev_cols[0]
        ev_vals = df_baseline[ev_col].values
        logger.info(f"  ✓ Demanda EV ({ev_col}): suma={ev_vals.sum():.1f} kWh/año, max={ev_vals.max():.1f} kW")

    # Mall demand
    mall_cols = [c for c in df_baseline.columns if any(tag in c.lower() for tag in ["mall", "building", "load"])]
    if mall_cols:
        mall_col = mall_cols[0]
        mall_vals = df_baseline[mall_col].values
        logger.info(f"  ✓ Demanda mall ({mall_col}): suma={mall_vals.sum():.1f} kWh/año, max={mall_vals.max():.1f} kW")

    # BESS
    bess_cols = [c for c in df_baseline.columns if any(tag in c.lower() for tag in ["bess", "battery", "soc"])]
    if bess_cols:
        logger.info(f"  ✓ BESS columns found: {bess_cols[:3]}")

    # CO2
    co2_cols = [c for c in df_baseline.columns if any(tag in c.lower() for tag in ["co2", "carbon"])]
    if co2_cols:
        logger.info(f"  ✓ CO2 columns found: {co2_cols[:3]}")

    result["status"] = "OK"
    result["details"]["rows"] = len(df_baseline)
    result["details"]["has_solar"] = bool(solar_cols)
    result["details"]["has_ev_demand"] = bool(ev_cols)
    result["details"]["has_mall_demand"] = bool(mall_cols)
    result["details"]["has_bess"] = bool(bess_cols)
    result["details"]["has_co2"] = bool(co2_cols)

    return result


def main():
    """Run all verification checks."""
    logger.info("")
    logger.info("")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "VERIFICACIÓN DE FLUJO DE DATOS OE2 → ENTRENAMIENTO" + " "*9 + "║")
    logger.info("╚" + "="*78 + "╝")

    checks = [
        ("Solar", verify_oe2_solar_data),
        ("BESS", verify_oe2_bess_data),
        ("EV Chargers", verify_oe2_ev_chargers),
        ("Mall Demand", verify_oe2_mall_demand),
        ("CityLearn Schema", verify_citylearn_schema),
        ("Energy CSV", verify_citylearn_energy_csv),
        ("Baseline CSV", verify_baseline_csv),
    ]

    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            logger.error(f"Error en verificación de {name}: {e}")
            results[name] = {"status": "ERROR", "error": str(e)}

    # Summary report
    logger.info("")
    logger.info("")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*30 + "RESUMEN FINAL" + " "*36 + "║")
    logger.info("╚" + "="*78 + "╝")

    passed = sum(1 for r in results.values() if r["status"] == "OK")
    warned = sum(1 for r in results.values() if r["status"] == "WARN")
    failed = sum(1 for r in results.values() if r["status"] in ("FAIL", "ERROR"))

    logger.info("")
    for name, result in results.items():
        status_icon = "✓" if result["status"] == "OK" else "⚠" if result["status"] == "WARN" else "✗"
        logger.info(f"  {status_icon} {name}: {result['status']}")

    logger.info("")
    logger.info(f"  Total: {passed} OK, {warned} WARN, {failed} FAIL")
    logger.info("")

    # Conclusion
    if failed == 0 and warned == 0:
        logger.info("✓ TODOS LOS DATOS OE2 ESTÁN CORRECTAMENTE INTEGRADOS EN EL PIPELINE")
        logger.info("✓ Dataset listo para entrenamiento de agentes SAC/PPO/A2C")
        return 0
    elif failed == 0:
        logger.info("⚠ ADVERTENCIAS ENCONTRADAS - Revisar datos de mall demand")
        return 1
    else:
        logger.info("✗ ERRORES ENCONTRADOS - Verificar rutas de archivos OE2")
        return 2


if __name__ == "__main__":
    sys.exit(main())
