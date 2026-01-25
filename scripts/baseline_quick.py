"""
Baseline simple: una simulación muy rápida sin control.
"""

import sys
from pathlib import Path
import logging
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config, load_paths
from citylearn.citylearn import CityLearnEnv
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("BASELINE RÁPIDO: Una simulación sin control")
    logger.info("=" * 80)

    cfg = load_config()
    rp = load_paths(cfg)

    dataset_root = Path(rp.processed_dir) / "citylearn"
    schema_files = sorted(dataset_root.glob("*/schema_*.json"))
    schema_path = schema_files[-1]
    logger.info(f"Schema: {schema_path.name}")

    env = CityLearnEnv(schema=str(schema_path))

    logger.info("\n[Baseline] Corriendo 1 episodio completo...")
    _, _ = env.reset()

    # Determinar número de acciones
    num_actions = 130  # Fixed: 128 chargers + 2 reservados
    actions = [np.ones((num_actions,), dtype=np.float32)]

    co2_total = 0.0
    grid_import_total = 0.0
    step = 0
    max_steps = 8760

    while step < max_steps:
        _, _, terminated, truncated, _ = env.step(actions)
        step += 1

        # Extraer métricas del info
        if isinstance(info, list) and len(info) > 0:
            building_info = info[0]
            if isinstance(building_info, dict):
                co2_total += building_info.get('carbon_emissions', 0.0)
                net = building_info.get('net_electricity_consumption', 0.0)
                if net > 0:
                    grid_import_total += net

        if step % 1000 == 0:
            logger.info(f"  Step {step}/{max_steps}")

        if terminated or truncated:
            break

    output_dir = rp.oe3_simulations_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_file = output_dir / "baseline_results.json"
    results = {
        "episodes": 1,
        "total_carbon_kg": float(co2_total),
        "total_grid_import_kwh": float(grid_import_total),
        "average_carbon_kg_per_episode": float(co2_total),
        "steps": step,
        "description": "Baseline sin control: todas las acciones=1.0 (máxima carga)"
    }

    baseline_file.write_text(json.dumps(results, indent=2))

    logger.info("\n" + "=" * 80)
    logger.info("BASELINE COMPLETADO")
    logger.info("=" * 80)
    logger.info(f"Total CO2: {co2_total:.2f} kg")
    logger.info(f"Grid import: {grid_import_total:.2f} kWh")
    logger.info(f"Steps completed: {step}/8760")
    logger.info(f"Results: {baseline_file}")


if __name__ == "__main__":
    main()
