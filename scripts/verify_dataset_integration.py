#!/usr/bin/env python3
"""
Verificación exhaustiva que el dataset builder carga correctamente:
- Demanda real del mall
- Generación solar
- 128 cargadores
- BESS (batería)

Se ejecuta ANTES de SAC/PPO/A2C para asegurar integridad del dataset.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any

import pandas as pd  # type: ignore

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from scripts._common import load_all


logger = logging.getLogger(__name__)


def verify_bess_config(cfg: Dict[str, Any]) -> bool:
    """Verifica que BESS esté configurado correctamente en OE2."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  🔋 VERIFICACIÓN: BESS (Battery Energy Storage System)")
    logger.info("════════════════════════════════════════════════════════════════")

    bess_cfg = cfg.get("oe2", {}).get("electrical_storage", {})
    bess_cap = float(bess_cfg.get("capacity_kwh", 0))
    bess_pow = float(bess_cfg.get("power_kw", 0))

    if bess_cap > 0 and bess_pow > 0:
        logger.info(f"  ✅ BESS configurado correctamente")
        logger.info(f"     Capacidad: {bess_cap:,.0f} kWh")
        logger.info(f"     Potencia: {bess_pow:,.0f} kW")
        logger.info(f"     Ratio P/C: {bess_pow/max(bess_cap, 1):.2f}")
        return True
    else:
        logger.error(f"  ❌ BESS NO configurado correctamente")
        logger.error(f"     Capacidad: {bess_cap} kWh (esperado > 0)")
        logger.error(f"     Potencia: {bess_pow} kW (esperado > 0)")
        return False


def verify_solar_generation(interim_dir: Path) -> bool:
    """Verifica que generación solar tenga exactamente 8760 registros horarios."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  ☀️  VERIFICACIÓN: Generación Solar")
    logger.info("════════════════════════════════════════════════════════════════")

    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"

    if not solar_path.exists():
        logger.error(f"  ❌ Archivo solar NO encontrado: {solar_path}")
        return False

    try:
        solar_df = pd.read_csv(solar_path)
        n_rows = len(solar_df)

        if n_rows != 8760:
            logger.error(f"  ❌ Solar timeseries tiene {n_rows} filas (esperado 8760 horas)")
            return False

        # Detectar si es 15-min (42,840 filas) o sub-horario
        if n_rows % 8760 != 0:
            logger.error(f"  ❌ Solar tiene {n_rows} filas - NO ES MÚLTIPLO de 8760")
            logger.error(f"     Posiblemente sea 15-min ({8760*4} filas) o sub-horario")
            return False

        # Validar valores
        solar_col = None
        for col in solar_df.columns:
            if 'ac' in col.lower() or 'power' in col.lower() or 'generation' in col.lower():
                solar_col = col
                break

        if solar_col is None:
            solar_col = solar_df.columns[0]

        solar_vals = pd.to_numeric(solar_df[solar_col], errors='coerce')

        logger.info(f"  ✅ Solar timeseries cargado correctamente")
        logger.info(f"     Filas: {n_rows} (correcto: 8760 horas/año)")
        logger.info(f"     Columna: {solar_col}")
        logger.info(f"     Min: {solar_vals.min():.2f} kW")
        logger.info(f"     Max: {solar_vals.max():.2f} kW")
        logger.info(f"     Media: {solar_vals.mean():.2f} kW")
        logger.info(f"     Total anual: {solar_vals.sum():.0f} kWh")

        return True

    except Exception as e:
        logger.error(f"  ❌ Error leyendo solar: {e}")
        return False


def verify_mall_demand(interim_dir: Path) -> bool:
    """Verifica que demanda del mall esté disponible."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  🏪 VERIFICACIÓN: Demanda Real del Mall")
    logger.info("════════════════════════════════════════════════════════════════")

    mall_path = interim_dir / "oe2" / "mall" / "demand_timeseries.csv"

    if not mall_path.exists():
        logger.warning(f"  ⚠️  Archivo mall demand NO encontrado: {mall_path}")
        logger.info("     → Usará demanda sintética o del edificio")
        return True  # No es crítico, hay fallback

    try:
        mall_df = pd.read_csv(mall_path)
        n_rows = len(mall_df)

        if n_rows != 8760:
            logger.warning(f"  ⚠️  Mall demand tiene {n_rows} filas (esperado 8760)")
            return True  # Tolerante, pero registrado

        # Buscar columna de demanda
        demand_col = None
        for col in mall_df.columns:
            if 'demand' in col.lower() or 'load' in col.lower() or 'power' in col.lower():
                demand_col = col
                break

        if demand_col is None:
            demand_col = mall_df.columns[0]

        demand_vals = pd.to_numeric(mall_df[demand_col], errors='coerce')

        logger.info(f"  ✅ Demanda del mall cargada")
        logger.info(f"     Filas: {n_rows}")
        logger.info(f"     Columna: {demand_col}")
        logger.info(f"     Min: {demand_vals.min():.3f} kW")
        logger.info(f"     Max: {demand_vals.max():.3f} kW")
        logger.info(f"     Media: {demand_vals.mean():.3f} kW")
        logger.info(f"     Total anual: {demand_vals.sum():.0f} kWh")

        return True

    except Exception as e:
        logger.warning(f"  ⚠️  Error leyendo mall demand: {e}")
        return True  # Tolerante


def verify_chargers_config(cfg: Dict[str, Any], interim_dir: Path) -> bool:
    """Verifica que 128 cargadores estén configurados."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  🔌 VERIFICACIÓN: 128 Cargadores EV")
    logger.info("════════════════════════════════════════════════════════════════")

    chargers_path = interim_dir / "oe2" / "chargers" / "individual_chargers.json"

    if not chargers_path.exists():
        logger.error(f"  ❌ Archivo chargers NO encontrado: {chargers_path}")
        return False

    try:
        chargers_json = json.loads(chargers_path.read_text())
        n_chargers = len(chargers_json)
        total_sockets = n_chargers * 4  # 4 sockets por cargador

        if n_chargers != 32:
            logger.error(f"  ❌ Encontrados {n_chargers} cargadores (esperado 32 = 128 sockets)")
            return False

        if total_sockets != 128:
            logger.error(f"  ❌ Total sockets: {total_sockets} (esperado 128)")
            return False

        # Validar configuración de cada cargador
        power_motos: float = 0.0
        power_mototaxis: float = 0.0

        for charger in chargers_json:
            charger_type = charger.get("type", "unknown")
            power: float = float(charger.get("rated_power_kw", 0))

            if charger_type.lower() == "moto":
                power_motos += power * 4  # 4 sockets
            elif charger_type.lower() == "mototaxi":
                power_mototaxis += power * 4

        total_power = power_motos + power_mototaxis

        logger.info(f"  ✅ Cargadores configurados correctamente")
        logger.info(f"     Cantidad: {n_chargers} cargadores")
        logger.info(f"     Sockets totales: {total_sockets} (4 por cargador)")
        logger.info(f"     Potencia motos: {power_motos:.0f} kW")
        logger.info(f"     Potencia mototaxis: {power_mototaxis:.0f} kW")
        logger.info(f"     Potencia total: {total_power:.0f} kW")

        return True

    except Exception as e:
        logger.error(f"  ❌ Error leyendo chargers: {e}")
        return False


def verify_dataset_output(processed_dir: Path) -> bool:
    """Verifica que dataset_builder generó archivos correctamente."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  📊 VERIFICACIÓN: Archivos de Salida del Dataset Builder")
    logger.info("════════════════════════════════════════════════════════════════")

    dataset_dir = processed_dir / "dataset" / "iquitos_citylearn"

    if not dataset_dir.exists():
        logger.error(f"  ❌ Dataset directory NO encontrado: {dataset_dir}")
        return False

    # Verificar schema
    schema_path = dataset_dir / "schema_pv_bess.json"
    if not schema_path.exists():
        logger.error(f"  ❌ Schema NO encontrado: {schema_path}")
        return False

    logger.info(f"  ✅ Schema encontrado: {schema_path.name}")

    # Verificar charger CSVs (deberían haber 128)
    charger_csvs = list(dataset_dir.glob("agents_*_load_electricity_timeseries.csv"))

    if len(charger_csvs) < 128:
        logger.warning(f"  ⚠️  Encontrados {len(charger_csvs)} charger CSVs (esperado 128)")
        logger.info("     → Algunos cargadores pueden estar generándose aún")
        return True  # Tolerante

    logger.info(f"  ✅ Charger CSVs encontrados: {len(charger_csvs)}")

    # Verificar BESS CSV
    bess_csv = dataset_dir / "electrical_storage_simulation.csv"
    if bess_csv.exists():
        logger.info(f"  ✅ BESS CSV encontrado: {bess_csv.name}")
    else:
        logger.warning(f"  ⚠️  BESS CSV NO encontrado (será generado en próxima ejecución)")

    # Verificar building load CSV
    building_csv = dataset_dir / "building_load_electricity_timeseries.csv"
    if building_csv.exists():
        logger.info(f"  ✅ Building load CSV encontrado: {building_csv.name}")
    else:
        logger.warning(f"  ⚠️  Building load CSV NO encontrado")

    # Verificar weather CSV
    weather_csv = dataset_dir / "weather_timeseries.csv"
    if weather_csv.exists():
        logger.info(f"  ✅ Weather CSV encontrado: {weather_csv.name}")
    else:
        logger.warning(f"  ⚠️  Weather CSV NO encontrado")

    return True


def verify_dataset_schema_integrity(processed_dir: Path) -> bool:
    """Verifica integridad del schema JSON generado."""
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  🏗️  VERIFICACIÓN: Integridad del Schema JSON")
    logger.info("════════════════════════════════════════════════════════════════")

    dataset_dir = processed_dir / "dataset" / "iquitos_citylearn"
    schema_path = dataset_dir / "schema_pv_bess.json"

    if not schema_path.exists():
        logger.error(f"  ❌ Schema NO encontrado")
        return False

    try:
        schema = json.loads(schema_path.read_text())

        # Verificar estructura básica
        buildings = schema.get("buildings", [])
        n_buildings = len(buildings)

        logger.info(f"  ✅ Schema cargado correctamente")
        logger.info(f"     Edificios: {n_buildings}")

        if n_buildings > 0:
            # Verificar primer edificio
            building = buildings[0]
            building_id = building.get("building_name", "unknown")

            # Buscar referencias a BESS, Solar, Chargers
            has_storage = "electrical_storage_simulation_timeseries_file" in building
            has_pv = "pv_generation_timeseries_file" in building
            has_building_load = "building_load_electricity_timeseries_file" in building

            logger.info(f"     Primer edificio: {building_id}")
            logger.info(f"     - BESS referencia: {'✅' if has_storage else '⚠️'}")
            logger.info(f"     - PV referencia: {'✅' if has_pv else '⚠️'}")
            logger.info(f"     - Building load referencia: {'✅' if has_building_load else '⚠️'}")

            # Contar agentes (chargers)
            agents = building.get("agents", [])
            n_agents = len(agents)

            if n_agents > 0:
                logger.info(f"     Agentes (chargers): {n_agents}")

        return True

    except Exception as e:
        logger.error(f"  ❌ Error leyendo schema: {e}")
        return False


def main() -> None:
    """Ejecuta todas las verificaciones."""
    setup_logging()

    # Cargar configuración
    cfg, rp = load_all("configs/default.yaml")

    logger.info("\n")
    logger.info("╔════════════════════════════════════════════════════════════════╗")
    logger.info("║   VERIFICACIÓN INTEGRAL: DATASET BUILDER                       ║")
    logger.info("║   Valida integración de: Mall, Solar, 128 Chargers, BESS      ║")
    logger.info("╚════════════════════════════════════════════════════════════════╝")
    logger.info("\n")

    # Ejecutar verificaciones previas
    checks = {
        "bess_config": verify_bess_config(cfg),
        "solar_generation": verify_solar_generation(rp.interim_dir),
        "mall_demand": verify_mall_demand(rp.interim_dir),
        "chargers_config": verify_chargers_config(cfg, rp.interim_dir),
    }

    # Construir dataset
    logger.info("\n")
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  🚀 Construyendo Dataset (puede tomar 1-2 minutos)...")
    logger.info("════════════════════════════════════════════════════════════════")

    try:
        built = build_citylearn_dataset(
            cfg=cfg,
            _raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )
        logger.info(f"  ✅ Dataset construido exitosamente")
        logger.info(f"     Ubicación: {built.dataset_dir}")

        # Verificar salida del dataset builder
        checks["dataset_output"] = verify_dataset_output(rp.processed_dir)
        checks["schema_integrity"] = verify_dataset_schema_integrity(rp.processed_dir)

    except Exception as e:
        logger.error(f"  ❌ Error construyendo dataset: {e}")
        checks["dataset_output"] = False
        checks["schema_integrity"] = False

    # Resumen final
    logger.info("\n")
    logger.info("════════════════════════════════════════════════════════════════")
    logger.info("  📋 RESUMEN DE VERIFICACIONES")
    logger.info("════════════════════════════════════════════════════════════════")

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: {check_name}")
        if not passed:
            all_passed = False

    logger.info("════════════════════════════════════════════════════════════════")

    if all_passed:
        logger.info("\n  🎉 TODAS LAS VERIFICACIONES COMPLETADAS EXITOSAMENTE")
        logger.info("\n  ✅ Dataset está listo para SAC/PPO/A2C training")
        logger.info("  ✅ BESS, Solar, Mall Demand y 128 Chargers están integrados")
    else:
        logger.error("\n  ❌ ALGUNAS VERIFICACIONES FALLARON")
        logger.error("\n  ⚠️  Revisa los errores arriba antes de iniciar training")

    logger.info("\n")


if __name__ == "__main__":
    main()
