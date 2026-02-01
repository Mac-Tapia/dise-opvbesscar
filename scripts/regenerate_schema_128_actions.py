#!/usr/bin/env python
"""
Regenerar schema CityLearn con 128 acciones individuales para cada cargador.

Este script crea un schema donde CADA socket tiene su propia acción controlable:
- 112 acciones para motos (2 kW cada una)
- 16 acciones para mototaxis (3 kW cada una)

Total: 128 acciones individuales para control granular de carga EV.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def generate_128_charger_schema():
    """Genera schema con 128 chargers individuales (1 acción por socket)."""

    base_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    schema_path = base_dir / "schema_pv_bess.json"
    output_path = base_dir / "schema_128_actions.json"

    # Cargar schema base
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    logger.info("Schema base cargado")

    # Configuración de potencias por tipo
    MOTO_POWER_KW = 2.0        # 112 motos × 2 kW = 224 kW total
    MOTOTAXI_POWER_KW = 3.0    # 16 mototaxis × 3 kW = 48 kW total
    N_MOTOS = 112
    N_MOTOTAXIS = 16
    TOTAL_CHARGERS = N_MOTOS + N_MOTOTAXIS  # 128

    # Crear nuevo diccionario de chargers (usando 'chargers' que es la key que CityLearn reconoce)
    new_chargers = {}

    for i in range(1, TOTAL_CHARGERS + 1):
        is_mototaxi = i > N_MOTOS

        if is_mototaxi:
            charger_id = f"mototaxi_{i - N_MOTOS:03d}"
            power = MOTOTAXI_POWER_KW
            charger_type = 1  # Mototaxi
        else:
            charger_id = f"moto_{i:03d}"
            power = MOTO_POWER_KW
            charger_type = 0  # Moto

        # Archivo CSV correspondiente
        csv_file = f"charger_simulation_{i:03d}.csv"

        new_chargers[charger_id] = {
            "type": "citylearn.electric_vehicle_charger.Charger",
            "charger_simulation": csv_file,
            "autosize": False,
            "attributes": {
                "nominal_power": power,
                "efficiency": 0.95,
                "charger_type": charger_type,
                "max_charging_power": power,
                "min_charging_power": 0.0,  # Permite apagar completamente
                "max_discharging_power": 0.0,  # Sin V2G
                "min_discharging_power": 0.0
            }
        }

    logger.info(f"Generados {len(new_chargers)} chargers individuales")
    logger.info(f"  - Motos (2 kW): {N_MOTOS}")
    logger.info(f"  - Mototaxis (3 kW): {N_MOTOTAXIS}")

    # Actualizar building con nuevos chargers
    building = schema['buildings']['Mall_Iquitos']

    # Remover keys antiguas
    if 'chargers' in building:
        del building['chargers']
    if 'electric_vehicle_chargers' in building:
        del building['electric_vehicle_chargers']

    # Usar la key 'chargers' que CityLearn reconoce para acciones
    building['chargers'] = new_chargers

    # Actualizar sección de acciones para habilitar control individual
    schema['actions'] = {
        "cooling_storage": {"active": False},
        "heating_storage": {"active": False},
        "dhw_storage": {"active": False},
        "electrical_storage": {"active": True},  # BESS control
        "electric_vehicle_storage": {"active": True}  # EV charger control
    }

    # Remover washing_machine si existe (no es parte del sistema)
    if 'washing_machine' in schema['actions']:
        del schema['actions']['washing_machine']
    if 'washing_machines' in building:
        del building['washing_machines']

    # Guardar nuevo schema
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)

    logger.info(f"Schema guardado: {output_path}")

    # Verificar resultado
    logger.info("\n=== VERIFICACIÓN ===")
    with open(output_path, 'r') as f:
        test_schema = json.load(f)

    n_chargers = len(test_schema['buildings']['Mall_Iquitos']['chargers'])
    logger.info(f"Chargers en schema: {n_chargers}")
    logger.info(f"Actions config: {json.dumps(test_schema['actions'], indent=2)}")

    # Test con CityLearn
    logger.info("\n=== TEST CITYLEARN ===")
    try:
        from citylearn.citylearn import CityLearnEnv
        env = CityLearnEnv(schema=test_schema)

        action_space = env.action_space
        if isinstance(action_space, list):
            action_shape = action_space[0].shape
        else:
            action_shape = action_space.shape

        logger.info(f"Action space shape: {action_shape}")
        logger.info(f"Action names: {env.action_names}")
        logger.info(f"Total actions: {action_shape[0] if len(action_shape) > 0 else 1}")

    except Exception as e:
        logger.error(f"Error al crear CityLearnEnv: {e}")

    return output_path


if __name__ == "__main__":
    generate_128_charger_schema()
