"""
Calcula baseline sin control de agentes para comparación.
"""

import sys
from pathlib import Path
import logging

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config, load_paths
from src.iquitos_citylearn.oe3.simulate import run_episodes_baseline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Ejecuta simulación baseline sin control de agentes."""

    logger.info("=" * 80)
    logger.info("BASELINE: Simulación sin control de agentes")
    logger.info("=" * 80)

    # Cargar config
    cfg = load_config()
    rp = load_paths(cfg)

    logger.info(f"Workspace: {PROJECT_ROOT}")
    logger.info(f"Outputs: {rp.outputs_dir}")

    # Ejecutar simulación baseline (10 episodios)
    logger.info("\nEjecutando 10 episodios de baseline...")
    try:
        metrics_baseline = run_episodes_baseline(
            cfg=cfg,
            rp=rp,
            n_episodes=10,
            output_dir=rp.oe3_simulations_dir
        )

        logger.info("\n" + "=" * 80)
        logger.info("BASELINE COMPLETADO")
        logger.info("=" * 80)
        logger.info(f"CO2 medio (kg): {metrics_baseline['co2_kg_mean']:.2f}")
        logger.info(f"Costo medio (USD): {metrics_baseline['cost_usd_mean']:.2f}")
        logger.info(f"Importación red (kWh): {metrics_baseline['grid_import_kwh_mean']:.2f}")

    except Exception as e:
        logger.error(f"Error en baseline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
