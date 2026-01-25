"""
Calcula baseline sin control de agentes para comparación.
"""

import sys
from pathlib import Path
import logging
import numpy as np
from citylearn.citylearn import CityLearnEnv

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.iquitos_citylearn.config import load_config, load_paths

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

    # Ejecutar simulación baseline (1 episodio simple)
    logger.info("\nEjecutando baseline sin control...")
    try:
        # Encontrar schema
        schema_path = rp.processed_dir / "citylearnv2_dataset" / "schema.json"
        if not schema_path.exists():
            logger.error(f"Schema no encontrado: {schema_path}")
            return 1

        env = CityLearnEnv(schema=str(schema_path))
        _, _ = env.reset()

        # Acciones baseline: máxima potencia (1.0)
        if isinstance(env.action_space, list):
            num_actions = sum(sp.shape[0] if hasattr(sp, 'shape') else 1 for sp in env.action_space)
        else:
            num_actions = 126  # Default

        actions = [np.ones((num_actions,), dtype=np.float32)]

        _ = 0.0
        _ = 0.0
        _ = 0.0

        for _ in range(8760):
            _, _, terminated, truncated, _ = env.step(actions)
            if terminated or truncated:
                break

        logger.info("\n" + "=" * 80)
        logger.info("BASELINE COMPLETADO")
        logger.info("=" * 80)
        logger.info(f"Status: Baseline ejecutado sin errores")
        env.close()
        return 0

    except Exception as e:
        logger.error(f"Error en baseline: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    main()
