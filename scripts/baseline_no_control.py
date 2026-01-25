"""
Baseline: Simulación sin control (chargers always on, no optimization).
"""

import sys
from pathlib import Path
import logging
import json
import numpy as np
import pandas as pd

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config, load_paths
from citylearn.citylearn import CityLearnEnv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Ejecuta baseline: simulación sin control de agentes."""

    logger.info("=" * 80)
    logger.info("BASELINE: Simulación sin control (todas las acciones=1.0)")
    logger.info("=" * 80)

    # Cargar config
    cfg = load_config()
    rp = load_paths(cfg)

    # Buscar el schema más reciente
    dataset_root = Path(rp.processed_dir) / "citylearn"
    if not dataset_root.exists():
        logger.error(f"No dataset found in {dataset_root}. Run dataset builder first.")
        raise FileNotFoundError(f"Dataset not found in {dataset_root}")

    # Buscar en subdirectorios (iquitos_ev_mall, etc)
    schema_files = list(dataset_root.glob("*/schema_*.json"))
    if not schema_files:
        logger.error(f"No schema files found in {dataset_root}")
        raise FileNotFoundError("schema_*.json not found")

    schema_path = sorted(schema_files)[-1]  # Más reciente
    logger.info(f"Using schema: {schema_path}")

    # Crear ambiente
    env = CityLearnEnv(schema=str(schema_path))

    # Ejecutar baseline (5 episodios)
    logger.info("\nRunning 5 baseline episodes (no control, actions=1.0)...")

    results = []

    for ep in range(5):
        logger.info(f"\n[Episode {ep+1}/5]")
        obs, info = env.reset()

        # Acciones: Obtener número de acciones del entorno
        num_actions = env.action_space.shape[0] if hasattr(env.action_space, 'shape') else 130
        actions = [np.ones((num_actions,), dtype=np.float32)]  # Una acción por building

        episode_metrics = {
            "episode": ep + 1,
            "total_carbon_kg": 0.0,
            "total_cost_usd": 0.0,
            "total_grid_import_kwh": 0.0,
            "total_solar_generated_kwh": 0.0,
            "total_ev_charging_kwh": 0.0,
            "timesteps": 0,
        }

        done = False
        step = 0

        while not done:
            obs, reward, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            step += 1

            # Acumular métricas si están disponibles
            if hasattr(env, 'net_electricity_consumption'):
                episode_metrics["total_grid_import_kwh"] += max(0.0, env.net_electricity_consumption)

            if step % 1000 == 0:
                logger.info(f"  Step {step}/8760")

        episode_metrics["timesteps"] = step
        results.append(episode_metrics)
        logger.info(f"  Carbon: {episode_metrics['total_carbon_kg']:.2f} kg | "
                   f"Cost: ${episode_metrics['total_cost_usd']:.2f} | "
                   f"Grid import: {episode_metrics['total_grid_import_kwh']:.2f} kWh")

    # Guardar resultados
    output_dir = rp.oe3_simulations_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_file = output_dir / "baseline_results.json"
    with open(baseline_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "=" * 80)
    logger.info(f"BASELINE COMPLETADO - Resultados guardados en {baseline_file}")
    logger.info("=" * 80)

    # Mostrar resumen
    df = pd.DataFrame(results)
    logger.info("\nBASELINE SUMMARY:")
    logger.info(f"  Mean grid import: {df['total_grid_import_kwh'].mean():.2f} kWh/episode")
    logger.info(f"  Mean cost: ${df['total_cost_usd'].mean():.2f}/episode")
    logger.info(f"  Mean carbon: {df['total_carbon_kg'].mean():.2f} kg/episode")


if __name__ == "__main__":
    main()
