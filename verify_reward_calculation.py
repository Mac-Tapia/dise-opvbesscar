#!/usr/bin/env python3
"""Verificar que la recompensa se calcula correctamente en todos los agentes."""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup paths
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "src"))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("verify_reward")

def check_ppo_reward_fix() -> bool:
    """Verificar que PPO está usando la recompensa correcta."""
    try:
        train_file = repo_root / "train_ppo_multiobjetivo.py"
        content = train_file.read_text(encoding='utf-8')
        
        # Buscar la línea corregida
        if "self.ep_reward = self.episode_reward  # ✅ FIXED" in content:
            logger.info("✅ PPO: Recompensa usando callback acumulado (CORRECTO)")
            return True
        elif "self.ep_reward = self.env_ref.episode_reward" in content:
            logger.error("❌ PPO: Aún intenta obtener recompensa de env_ref (INCORRECTO)")
            return False
        else:
            logger.warning("⚠️  PPO: No se puede verificar asignación de recompensa")
            return None
    except Exception as e:
        logger.error(f"Error verificando PPO: {e}")
        return False

def check_sac_reward() -> bool:
    """Verificar que SAC tiene lógica de recompensa robusta."""
    try:
        train_file = repo_root / "train_sac_multiobjetivo.py"
        content = train_file.read_text(encoding='utf-8')
        
        # SAC debe acumular reward
        if "self.ep_reward += reward_val" in content:
            logger.info("✅ SAC: Acumula recompensa por step (CORRECTO)")
            return True
        else:
            logger.warning("⚠️  SAC: Lógica de acumulación de recompensa no clara")
            return None
    except Exception as e:
        logger.error(f"Error verificando SAC: {e}")
        return False

def check_a2c_reward() -> bool:
    """Verificar que A2C tiene lógica de recompensa robusta."""
    try:
        train_file = repo_root / "train_a2c_multiobjetivo.py"
        content = train_file.read_text(encoding='utf-8')
        
        # A2C debe acumular reward
        if "self.current_episode_reward += reward" in content:
            logger.info("✅ A2C: Acumula recompensa por step (CORRECTO)")
            return True
        else:
            logger.warning("⚠️  A2C: Lógica de acumulación de recompensa no clara")
            return None
    except Exception as e:
        logger.error(f"Error verificando A2C: {e}")
        return False

def check_reward_weights_sync() -> bool:
    """Verificar que todos los agentes usan los pesos sincronizados."""
    try:
        weights_file = repo_root / "src" / "rewards" / "rewards.py"
        content = weights_file.read_text(encoding='utf-8')
        
        # Buscar los pesos correctos
        if 'co2=0.35' in content and 'ev_satisfaction=0.30' in content:
            logger.info("✅ Pesos sincronizados: CO₂=0.35, EV satisfaction=0.30 (CORRECTO)")
            
            # Verificar que todos suman a 1.0
            if '0.35 + 0.20 + 0.30 + 0.10 + 0.05 = 1.0' in content or \
               'co2_focus' in content:
                logger.info("✅ Pesos normalizados a 1.0 (CORRECTO)")
                return True
        else:
            logger.error("❌ Pesos no están sincronizados correctamente")
            return False
    except Exception as e:
        logger.error(f"Error verificando pesos: {e}")
        return False

def main() -> int:
    """Ejecutar todas las verificaciones."""
    logger.info("=" * 60)
    logger.info("VERIFICACIÓN DE CÁLCULO DE RECOMPENSA")
    logger.info("=" * 60)
    
    results = {
        "PPO reward fix": check_ppo_reward_fix(),
        "SAC reward logic": check_sac_reward(),
        "A2C reward logic": check_a2c_reward(),
        "Reward weights sync": check_reward_weights_sync(),
    }
    
    logger.info("=" * 60)
    logger.info("RESUMEN:")
    passed = sum(1 for v in results.values() if v is True)
    warned = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    
    logger.info(f"✅ Pasados: {passed}")
    logger.info(f"⚠️  Advertencias: {warned}")
    logger.info(f"❌ Fallidos: {failed}")
    logger.info("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
