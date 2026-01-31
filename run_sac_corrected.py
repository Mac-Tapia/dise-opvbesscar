#!/usr/bin/env python3
"""
SCRIPT DE REINICIO DE ENTRENAMIENTO SAC CON CORRECCIONES - 2026-01-31

Inicia entrenamiento SAC con todas las correcciones aplicadas.
Monitorea:
  ✓ CO₂ DIRECTO sincronizado
  ✓ EV demand desde building real
  ✓ Motos/Mototaxis proporcionales
  ✓ Sin duplicación de cálculos

Uso: python run_sac_corrected.py [--episodes 50] [--resume]
"""

from __future__ import annotations

import sys
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='SAC Training with Corrected Energy Sync')
    parser.add_argument('--episodes', type=int, default=10, help='Número de episodios a entrenar')
    parser.add_argument('--config', default='configs/default.yaml', help='Config file')
    parser.add_argument('--resume', action='store_true', help='Resume from latest checkpoint')
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("ENTRENAMIENTO SAC CON CORRECCIONES ROBUSTAS - 2026-01-31")
    logger.info("=" * 80)

    # Pre-flight checks
    logger.info("\n📋 PRE-FLIGHT CHECKS:")

    checks = [
        ("Verificar SAC correcciones", verify_sac_fixes),
        ("Verificar baseline data", verify_baseline),
        ("Verificar config", lambda: verify_file('configs/default.yaml')),
        ("Verificar checkpoints dir", lambda: Path('checkpoints/sac').mkdir(parents=True, exist_ok=True) or True),
    ]

    for check_name, check_fn in checks:
        try:
            if check_fn():
                logger.info(f"   ✓ {check_name}")
            else:
                logger.error(f"   ❌ {check_name}")
                return 1
        except Exception as e:
            logger.error(f"   ❌ {check_name}: {e}")
            return 1

    logger.info("\n" + "=" * 80)
    logger.info("✅ TODOS LOS CHECKS PASADOS - INICIANDO ENTRENAMIENTO")
    logger.info("=" * 80 + "\n")

    # Import after checks
    from src.iquitos_citylearn.config import load_config, load_paths
    from src.iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
    from src.iquitos_citylearn.oe3.simulate import simulate
    from src.iquitos_citylearn.oe3.agents import SACConfig

    # Load config
    cfg = load_config(args.config)
    paths = load_paths(cfg)

    logger.info(f"\n📁 Rutas:")
    logger.info(f"   Dataset: {paths.dataset_dir}")
    logger.info(f"   Checkpoints: {paths.checkpoint_dir}")

    # Build or load dataset
    logger.info(f"\n🏗️ Dataset:")
    try:
        if not (paths.dataset_dir / 'schema_citylearn.json').exists():
            logger.info("   Construyendo dataset...")
            built = build_citylearn_dataset(cfg, paths)
            logger.info(f"   ✓ Dataset construido: {built.schema_path}")
        else:
            logger.info(f"   ✓ Dataset existente cargado")
    except Exception as e:
        logger.error(f"   ❌ Error en dataset: {e}")
        return 1

    # Configure SAC agent
    logger.info(f"\n🤖 SAC Agent:")
    sac_config = SACConfig(
        n_timesteps=args.episodes * 8760,
        learning_rate=1e-4,
        batch_size=64,
        buffer_size=10000,
        learning_starts=100,
        target_update_interval=1,
        tau=0.005,
        gamma=0.99,
        device='auto',
    )
    logger.info(f"   Episodes: {args.episodes}")
    logger.info(f"   Timesteps: {sac_config.n_timesteps}")
    logger.info(f"   Device: {sac_config.device}")

    # Train
    logger.info(f"\n🚀 INICIANDO ENTRENAMIENTO:")
    logger.info(f"   Config: {args.config}")
    logger.info(f"   Resume: {args.resume}")
    logger.info("")

    try:
        results = simulate(
            config_path=args.config,
            agents=['SAC'],
            n_episodes=args.episodes,
            reset_checkpoints=not args.resume,
        )

        logger.info("\n" + "=" * 80)
        logger.info("✅ ENTRENAMIENTO COMPLETADO")
        logger.info("=" * 80)
        logger.info("\nResultados guardados en:")
        logger.info(f"   {paths.results_dir}")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Entrenamiento interrumpido por usuario")
        return 0
    except Exception as e:
        logger.error(f"\n❌ Error durante entrenamiento: {e}", exc_info=True)
        return 1


def verify_sac_fixes():
    """Verificar que SAC tiene correcciones aplicadas"""
    sac_path = Path("src/iquitos_citylearn/oe3/agents/sac.py")
    content = sac_path.read_text(encoding='utf-8')

    checks = [
        "ev_power_delivered_kw = min(ev_demand_kw, solar_available_kw + bess_discharge_kw)",
        "motos_fraction = 112.0 / 128.0",
        "[SAC CO2 DIRECTO SYNC]",
        "chargers = getattr(b, 'electric_vehicle_chargers'",
    ]

    return all(check in content for check in checks)


def verify_baseline():
    """Verificar que baseline existe y es válido"""
    baseline_path = Path("outputs/oe3/baseline_full_year_hourly.csv")
    if not baseline_path.exists():
        return False

    import pandas as pd
    df = pd.read_csv(baseline_path)
    return len(df) == 8760 and df['ev_demand'].max() > 0


def verify_file(path):
    """Verificar que archivo existe"""
    return Path(path).exists()


if __name__ == '__main__':
    sys.exit(main())
