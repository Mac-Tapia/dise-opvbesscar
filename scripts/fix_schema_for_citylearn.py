#!/usr/bin/env python
"""Fix schema.json para que sea compatible con CityLearn."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def fix_schema():
    """Actualiza schema.json con estructura correcta para CityLearn."""

    schema_path = Path("data/interim/oe3/schema.json")
    dataset_dir = Path("data/interim/oe3").resolve()

    logger.info(f"Cargando schema desde {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # CRÍTICO: Agregar central_agent (requerido por CityLearn)
    if "central_agent" not in schema:
        logger.warning("⚠️  'central_agent' faltaba en schema. Agregando...")
        schema["central_agent"] = {
            "type": "central",
            "active": True,
            "attributes": {}
        }

    # Corregir rutas a paths correctas
    if "buildings" in schema and len(schema["buildings"]) > 0:
        building = schema["buildings"][0]

        # Asegurar que solar_generation apunta al archivo correcto
        if "energy_simulation" in building:
            sim = building["energy_simulation"]
            solar_file = dataset_dir / "pv_generation_timeseries.csv"
            if solar_file.exists():
                sim["solar_generation"] = str(solar_file.resolve())
                logger.info(f"✓ Solar generation: {sim['solar_generation']}")
            else:
                logger.error(f"❌ Solar file not found: {solar_file}")

            # Asegurar que non_shiftable_load apunta al archivo correcto
            mall_file = dataset_dir / "mall_demand_hourly.csv"
            if mall_file.exists():
                sim["non_shiftable_load"] = str(mall_file.resolve())
                logger.info(f"✓ Non-shiftable load: {sim['non_shiftable_load']}")
            else:
                logger.error(f"❌ Mall demand file not found: {mall_file}")

    # Verificar chargers
        if "controllable_charging" in building:
            n_chargers = len(building["controllable_charging"])
            logger.info(f"✓ Controllable chargers: {n_chargers}")

        # CRÍTICO: Agregar observaciones (requeridas por CityLearn)
        if "observations" not in building:
            logger.warning("⚠️  'observations' faltaba. Agregando...")
            building["observations"] = {
                "energy_simulation": ["solar_generation", "non_shiftable_load"],
                "electrical_storage": ["soc"],
                "controllable_charging": ["available", "current_soc", "max_power_kw"],
            }
            logger.info("✓ Observaciones agregadas")

    # Asegurar que root_directory es correcto
    if "root_directory" not in schema:
        schema["root_directory"] = str(dataset_dir)
        logger.info(f"✓ root_directory: {schema['root_directory']}")

    # Guardar schema corregido
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"✅ Schema guardado en {schema_path}")

    # VALIDACIÓN CRÍTICA
    logger.info("\n[VALIDACIÓN CRÍTICA]")
    errors = []

    # Verificar que archivos existen
    solar_file = Path(schema.get("buildings", [{}])[0].get("energy_simulation", {}).get("solar_generation", ""))
    if not solar_file.exists():
        errors.append(f"Solar file not found: {solar_file}")
    else:
        logger.info(f"✓ Solar file exists: {solar_file.name}")

    mall_file = Path(schema.get("buildings", [{}])[0].get("energy_simulation", {}).get("non_shiftable_load", ""))
    if not mall_file.exists():
        errors.append(f"Mall file not found: {mall_file}")
    else:
        logger.info(f"✓ Mall file exists: {mall_file.name}")

    # Verificar central_agent
    if "central_agent" not in schema:
        errors.append("'central_agent' missing from schema")
    else:
        logger.info("✓ central_agent defined")

    # Verificar root_directory
    if "root_directory" not in schema:
        errors.append("'root_directory' missing from schema")
    else:
        logger.info(f"✓ root_directory: {schema['root_directory']}")

    # Resultado
    if errors:
        logger.error("\n❌ ERRORES CRÍTICOS ENCONTRADOS:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    else:
        logger.info("\n✅ Schema validado correctamente para CityLearn")
        return True


if __name__ == "__main__":
    success = fix_schema()
    exit(0 if success else 1)
