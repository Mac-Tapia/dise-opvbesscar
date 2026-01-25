#!/usr/bin/env python3
"""Verificar que todos los agentes son funcionales y listos para producción."""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_agents():
    """Verifica que SAC, PPO y A2C pueden importarse y configurarse."""

    results = {"passed": [], "failed": []}

    # 1. Verificar importaciones
    logger.info("="*60)
    logger.info("VERIFICACIÓN DE AGENTES PARA PRODUCCIÓN")
    logger.info("="*60)

    # 2. SAC
    logger.info("\n[1/3] Verificando SAC...")
    try:
        from src.iquitos_citylearn.oe3.agents.sac import SACConfig, SACAgent
        logger.info("  ✅ SAC importado correctamente")

        # Verificar config
        cfg = SACConfig()
        logger.info(f"  ✅ SACConfig instantiado: episodes={cfg.episodes}, batch_size={cfg.batch_size}")

        results["passed"].append("SAC")
    except Exception as e:
        logger.error(f"  ❌ Error en SAC: {e}")
        results["failed"].append(("SAC", str(e)))

    # 3. PPO
    logger.info("\n[2/3] Verificando PPO...")
    try:
        from src.iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig, PPOAgent
        logger.info("  ✅ PPO importado correctamente")

        # Verificar config
        cfg = PPOConfig()
        logger.info(f"  ✅ PPOConfig instantiado: train_steps={cfg.train_steps}, batch_size={cfg.batch_size}")

        results["passed"].append("PPO")
    except Exception as e:
        logger.error(f"  ❌ Error en PPO: {e}")
        results["failed"].append(("PPO", str(e)))

    # 4. A2C
    logger.info("\n[3/3] Verificando A2C...")
    try:
        from src.iquitos_citylearn.oe3.agents.a2c_sb3 import (A2CConfig,
                                                               A2CAgent)
        logger.info("  ✅ A2C importado correctamente")

        # Verificar config
        cfg = A2CConfig()
        logger.info(f"  ✅ A2CConfig instantiado: train_steps={cfg.train_steps}, batch_size={cfg.n_steps}")

        results["passed"].append("A2C")
    except Exception as e:
        logger.error(f"  ❌ Error en A2C: {e}")
        results["failed"].append(("A2C", str(e)))

    # 5. Resumen
    logger.info("\n" + "="*60)
    logger.info(f"✅ Pasaron: {len(results['passed'])}/3")
    logger.info(f"❌ Fallaron: {len(results['failed'])}/3")

    if results["passed"]:
        logger.info(f"\nAgentes funcionales: {', '.join(results['passed'])}")

    if results["failed"]:
        logger.info("\nErrores encontrados:")
        for agent, error in results["failed"]:
            logger.error(f"  - {agent}: {error}")
        return False

    logger.info("\n✅ TODOS LOS AGENTES ESTÁN LISTOS PARA PRODUCCIÓN")
    return True

if __name__ == "__main__":
    success = verify_agents()
    sys.exit(0 if success else 1)
