#!/usr/bin/env python
"""Fix schema.json - Agregar 'observations' a nivel raíz (requerido por CityLearn)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def fix_schema_observations():
    """Corrige schema.json con 'observations' a nivel raíz."""

    schema_path = Path("data/interim/oe3/schema.json")

    logger.info(f"Cargando schema desde {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # CRÍTICO: Agregar 'observations' a nivel raíz (no solo en buildings)
    if "observations" not in schema:
        logger.warning("⚠️  'observations' faltaba a nivel raíz. Agregando...")
        schema["observations"] = {
            "energy_simulation": ["solar_generation", "non_shiftable_load"],
            "electrical_storage": ["soc"],
            "controllable_charging": ["available", "current_soc", "max_power_kw"],
        }
        logger.info("✓ Observaciones a nivel raíz agregadas")

    # Verificar que building también tiene observations
    if "buildings" in schema and len(schema["buildings"]) > 0:
        building = schema["buildings"][0]
        if "observations" not in building:
            logger.warning("⚠️  'observations' en building también faltaba. Agregando...")
            building["observations"] = {
                "energy_simulation": ["solar_generation", "non_shiftable_load"],
                "electrical_storage": ["soc"],
                "controllable_charging": ["available", "current_soc", "max_power_kw"],
            }

    # Asegurar central_agent
    if "central_agent" not in schema:
        logger.warning("⚠️  'central_agent' faltaba. Agregando...")
        schema["central_agent"] = {"type": "central", "active": True, "attributes": {}}

    # Guardar schema corregido
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"✅ Schema guardado en {schema_path}")

    # VALIDACIÓN
    logger.info("\n[VALIDACIÓN]")
    if "observations" in schema:
        logger.info("✓ 'observations' en nivel raíz")
    else:
        logger.error("❌ 'observations' NO en nivel raíz")
        return False

    if "central_agent" in schema:
        logger.info("✓ 'central_agent' definido")
    else:
        logger.error("❌ 'central_agent' NO definido")
        return False

    logger.info("\n✅ Schema corregido para CityLearn")
    return True


if __name__ == "__main__":
    success = fix_schema_observations()
    exit(0 if success else 1)
