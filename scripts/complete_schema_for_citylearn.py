#!/usr/bin/env python
"""Fix schema.json completamente - Agregar 'actions' y 'shared_observations' (requeridos por CityLearn)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def complete_schema():
    """Completa schema.json con todas las propiedades requeridas por CityLearn."""

    schema_path = Path("data/interim/oe3/schema.json")

    logger.info(f"Cargando schema desde {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # CRÍTICO 1: Agregar 'observations' a nivel raíz
    if "observations" not in schema:
        logger.warning("⚠️  'observations' faltaba a nivel raíz. Agregando...")
        schema["observations"] = {
            "energy_simulation": ["solar_generation", "non_shiftable_load"],
            "electrical_storage": ["soc"],
            "controllable_charging": ["available", "current_soc", "max_power_kw"],
        }

    # CRÍTICO 2: Agregar 'actions' a nivel raíz
    if "actions" not in schema:
        logger.warning("⚠️  'actions' faltaba a nivel raíz. Agregando...")
        schema["actions"] = {
            "electrical_storage": ["power"],
            "controllable_charging": ["power"],
        }

    # CRÍTICO 3: Agregar 'shared_observations' a nivel raíz (generalmente vacío o específico)
    if "shared_observations" not in schema:
        logger.warning("⚠️  'shared_observations' faltaba. Agregando...")
        schema["shared_observations"] = []

    # Asegurar central_agent
    if "central_agent" not in schema:
        logger.warning("⚠️  'central_agent' faltaba. Agregando...")
        schema["central_agent"] = {"type": "central", "active": True, "attributes": {}}

    # Guardar schema
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"✅ Schema completado y guardado")

    # VALIDACIÓN CRÍTICA
    logger.info("\n[VALIDACIÓN CRÍTICA]")
    required_keys = ["root_directory", "episode_time_steps", "buildings", "observations", "actions", "central_agent"]
    all_good = True

    for key in required_keys:
        if key in schema:
            logger.info(f"✓ '{key}' presente")
        else:
            logger.error(f"❌ '{key}' FALTANTE")
            all_good = False

    if all_good:
        logger.info("\n✅ Schema completamente validado para CityLearn")
    else:
        logger.error("\n❌ Schema incompleto")

    return all_good


if __name__ == "__main__":
    success = complete_schema()
    exit(0 if success else 1)
