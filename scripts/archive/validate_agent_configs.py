#!/usr/bin/env python3
"""
VALIDATION SCRIPT: Verifica que cada agente RL tenga configuración óptima según su naturaleza algorítmica.
Previene errores de entrenamiento detectando misconfigurations antes de iniciar.

Ejecución:
    python scripts/validate_agent_configs.py

Status esperado: ✅ ALL VALIDATIONS PASSED
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

def validate_sac_config() -> bool:
    """Valida configuración SAC (off-policy, sample-efficient)."""
    logger.info("=" * 70)
    logger.info("VALIDATING SAC (Off-Policy Algorithm)")
    logger.info("=" * 70)

    from src.iquitos_citylearn.oe3.agents.sac import SACConfig
    cfg = SACConfig()
    errors = []
    warnings = []

    # CRÍTICO: Learning rate para off-policy
    if cfg.learning_rate == 5e-4:
        logger.info("✅ SAC learning_rate = 5e-4 (off-policy optimized)")
    elif cfg.learning_rate >= 1e-3:
        errors.append(f"❌ SAC LR = {cfg.learning_rate} TOO HIGH (risk gradient explosion)")
    elif cfg.learning_rate < 1e-4:
        warnings.append(f"⚠️  SAC LR = {cfg.learning_rate} too conservative (slower convergence)")
    else:
        logger.info(f"✓ SAC learning_rate = {cfg.learning_rate}")

    # CRÍTICO: Reward scaling (causa TRILLION losses si está mal)
    if cfg.reward_scale == 1.0:
        logger.info("✅ SAC reward_scale = 1.0 (proper normalization)")
    else:
        errors.append(f"❌ SAC reward_scale = {cfg.reward_scale} MUST BE 1.0 (was 0.01 before)")

    # Validar batch size apropiado para RTX 4060
    if cfg.batch_size <= 256:
        logger.info(f"✅ SAC batch_size = {cfg.batch_size} (safe for RTX 4060)")
    else:
        warnings.append(f"⚠️  SAC batch_size = {cfg.batch_size} (may OOM on 8GB)")

    # Validar buffer size
    if cfg.buffer_size <= 500000:
        logger.info(f"✅ SAC buffer_size = {cfg.buffer_size} (memory efficient)")
    else:
        warnings.append(f"⚠️  SAC buffer_size = {cfg.buffer_size} (large, verify memory)")

    # Validar tau (soft updates) para SAC
    if cfg.tau == 0.001:
        logger.info(f"✅ SAC tau = {cfg.tau} (soft targets)")
    else:
        warnings.append(f"⚠️  SAC tau = {cfg.tau} (should be 0.001)")

    # Validar gamma
    if cfg.gamma >= 0.99:
        logger.info(f"✅ SAC gamma = {cfg.gamma} (long-term dependencies)")
    else:
        warnings.append(f"⚠️  SAC gamma = {cfg.gamma} (low, short-term only)")

    # Validar normalize_observations y normalize_rewards
    if cfg.normalize_observations and cfg.normalize_rewards:
        logger.info("✅ SAC normalization enabled (prevents gradient explosion)")
    else:
        errors.append("❌ SAC normalization MUST be enabled")

    # Validar clip_obs
    if cfg.clip_obs >= 5.0:
        logger.info(f"✅ SAC clip_obs = {cfg.clip_obs} (proper outlier clipping)")
    else:
        warnings.append(f"⚠️  SAC clip_obs = {cfg.clip_obs} (may be too restrictive)")

    # Network size
    if all(h <= 512 for h in cfg.hidden_sizes):
        logger.info(f"✅ SAC hidden_sizes = {cfg.hidden_sizes} (efficient for 8GB GPU)")
    else:
        warnings.append(f"⚠️  SAC hidden_sizes = {cfg.hidden_sizes} (large)")

    # Resumen SAC
    logger.info("")
    if errors:
        logger.error(f"❌ SAC VALIDATION FAILED: {len(errors)} critical error(s)")
        for e in errors:
            logger.error(f"   {e}")
        return False
    elif warnings:
        logger.warning(f"⚠️  SAC VALIDATION: {len(warnings)} warning(s) (not critical)")
        for w in warnings:
            logger.warning(f"   {w}")

    logger.info("✅ SAC Configuration VALID")
    return True


def validate_ppo_config() -> bool:
    """Valida configuración PPO (on-policy, conservative)."""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATING PPO (On-Policy Algorithm - Conservative)")
    logger.info("=" * 70)

    from src.iquitos_citylearn.oe3.agents.ppo_sb3 import PPOConfig
    cfg = PPOConfig()
    errors = []
    warnings = []

    # CRÍTICO: Learning rate para on-policy
    if cfg.learning_rate == 1e-4:
        logger.info("✅ PPO learning_rate = 1e-4 (on-policy conservative)")
    elif cfg.learning_rate > 5e-4:
        errors.append(f"❌ PPO LR = {cfg.learning_rate} TOO HIGH (on-policy divergence risk)")
    else:
        logger.info(f"✓ PPO learning_rate = {cfg.learning_rate}")

    # CRÍTICO: Reward scaling (MUST BE 1.0, not 0.01)
    if cfg.reward_scale == 1.0:
        logger.info("✅ PPO reward_scale = 1.0 (proper normalization)")
    elif cfg.reward_scale == 0.01:
        errors.append(f"❌ PPO reward_scale = {cfg.reward_scale} MUST BE 1.0 (GRADIENT EXPLOSION RISK)")
    else:
        warnings.append(f"⚠️  PPO reward_scale = {cfg.reward_scale} (should be 1.0)")

    # Validar batch size
    if cfg.batch_size <= 128:
        logger.info(f"✅ PPO batch_size = {cfg.batch_size} (safe for RTX 4060)")
    else:
        warnings.append(f"⚠️  PPO batch_size = {cfg.batch_size} (may OOM on 8GB)")

    # Validar n_steps (for on-policy GAE)
    if cfg.n_steps >= 512 and cfg.n_steps <= 2048:
        logger.info(f"✅ PPO n_steps = {cfg.n_steps} (appropriate for trajectory)")
    else:
        warnings.append(f"⚠️  PPO n_steps = {cfg.n_steps} (should be 512-2048)")

    # Validar clip_range (trust region constraint)
    if cfg.clip_range == 0.2:
        logger.info(f"✅ PPO clip_range = {cfg.clip_range} (standard PPO)")
    else:
        warnings.append(f"⚠️  PPO clip_range = {cfg.clip_range} (should be 0.2)")

    # Validar max_grad_norm (gradient clipping)
    if cfg.max_grad_norm > 0.1:
        logger.info(f"✅ PPO max_grad_norm = {cfg.max_grad_norm} (prevents exploding grads)")
    else:
        warnings.append(f"⚠️  PPO max_grad_norm = {cfg.max_grad_norm} (low, may slow)")

    # Validar gamma
    if cfg.gamma >= 0.99:
        logger.info(f"✅ PPO gamma = {cfg.gamma} (long-term dependencies)")
    else:
        warnings.append(f"⚠️  PPO gamma = {cfg.gamma} (low, short-term only)")

    # Validar gae_lambda (GAE parameter)
    if 0.9 <= cfg.gae_lambda <= 0.99:
        logger.info(f"✅ PPO gae_lambda = {cfg.gae_lambda} (good bias-variance)")
    else:
        warnings.append(f"⚠️  PPO gae_lambda = {cfg.gae_lambda} (should be 0.9-0.99)")

    # Validar normalize_observations
    if cfg.normalize_observations:
        logger.info("✅ PPO normalize_observations enabled")
    else:
        errors.append("❌ PPO normalize_observations MUST be enabled")

    # Resumen PPO
    logger.info("")
    if errors:
        logger.error(f"❌ PPO VALIDATION FAILED: {len(errors)} critical error(s)")
        for e in errors:
            logger.error(f"   {e}")
        return False
    elif warnings:
        logger.warning(f"⚠️  PPO VALIDATION: {len(warnings)} warning(s) (not critical)")
        for w in warnings:
            logger.warning(f"   {w}")

    logger.info("✅ PPO Configuration VALID")
    return True


def validate_a2c_config() -> bool:
    """Valida configuración A2C (on-policy simple)."""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATING A2C (On-Policy Simple Algorithm)")
    logger.info("=" * 70)

    from src.iquitos_citylearn.oe3.agents.a2c_sb3 import A2CConfig
    cfg = A2CConfig()
    errors = []
    warnings = []

    # CRÍTICO: Learning rate para on-policy simple (higher than PPO)
    if cfg.learning_rate == 3e-4:
        logger.info("✅ A2C learning_rate = 3e-4 (on-policy simple, 3x PPO)")
    elif cfg.learning_rate > 5e-4:
        errors.append(f"❌ A2C LR = {cfg.learning_rate} TOO HIGH")
    elif cfg.learning_rate == 1e-4:
        warnings.append(f"⚠️  A2C LR = {cfg.learning_rate} too conservative (should be 3e-4)")
    else:
        logger.info(f"✓ A2C learning_rate = {cfg.learning_rate}")

    # CRÍTICO: Reward scaling (MUST BE 1.0, not 0.01)
    if cfg.reward_scale == 1.0:
        logger.info("✅ A2C reward_scale = 1.0 (proper normalization)")
    elif cfg.reward_scale == 0.01:
        errors.append(f"❌ A2C reward_scale = {cfg.reward_scale} MUST BE 1.0 (GRADIENT EXPLOSION RISK)")
    else:
        warnings.append(f"⚠️  A2C reward_scale = {cfg.reward_scale} (should be 1.0)")

    # Validar n_steps (buffer para A2C)
    if cfg.n_steps <= 256:
        logger.info(f"✅ A2C n_steps = {cfg.n_steps} (safe buffer for 8GB)")
    else:
        warnings.append(f"⚠️  A2C n_steps = {cfg.n_steps} (large, may OOM)")

    # Validar max_grad_norm
    if cfg.max_grad_norm > 0.0:
        logger.info(f"✅ A2C max_grad_norm = {cfg.max_grad_norm} (gradient clipping)")
    else:
        errors.append("❌ A2C max_grad_norm MUST be > 0")

    # Validar gamma
    if cfg.gamma >= 0.99:
        logger.info(f"✅ A2C gamma = {cfg.gamma} (long-term dependencies)")
    else:
        warnings.append(f"⚠️  A2C gamma = {cfg.gamma} (low)")

    # Validar gae_lambda
    if cfg.gae_lambda >= 0.8:
        logger.info(f"✅ A2C gae_lambda = {cfg.gae_lambda}")
    else:
        warnings.append(f"⚠️  A2C gae_lambda = {cfg.gae_lambda} (low)")

    # Network size
    if all(h <= 512 for h in cfg.hidden_sizes):
        logger.info(f"✅ A2C hidden_sizes = {cfg.hidden_sizes} (efficient)")
    else:
        warnings.append(f"⚠️  A2C hidden_sizes = {cfg.hidden_sizes} (large)")

    # Resumen A2C
    logger.info("")
    if errors:
        logger.error(f"❌ A2C VALIDATION FAILED: {len(errors)} critical error(s)")
        for e in errors:
            logger.error(f"   {e}")
        return False
    elif warnings:
        logger.warning(f"⚠️  A2C VALIDATION: {len(warnings)} warning(s) (not critical)")
        for w in warnings:
            logger.warning(f"   {w}")

    logger.info("✅ A2C Configuration VALID")
    return True


def validate_reward_function() -> bool:
    """Valida que la función de recompensa esté normalizada correctamente."""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATING Reward Function (Multi-Objective)")
    logger.info("=" * 70)

    from src.iquitos_citylearn.oe3.agents.sac import SACConfig
    cfg = SACConfig()

    total_weight = (
        cfg.weight_co2 +
        cfg.weight_cost +
        cfg.weight_solar +
        cfg.weight_ev_satisfaction +
        cfg.weight_grid_stability
    )

    logger.info(f"Weights breakdown:")
    logger.info(f"  CO₂:             {cfg.weight_co2:.2f} (primary: minimizar emisiones)")
    logger.info(f"  Cost:            {cfg.weight_cost:.2f}")
    logger.info(f"  Solar:           {cfg.weight_solar:.2f} (secondary)")
    logger.info(f"  EV satisfaction: {cfg.weight_ev_satisfaction:.2f}")
    logger.info(f"  Grid stability:  {cfg.weight_grid_stability:.2f}")
    logger.info(f"  TOTAL:           {total_weight:.2f}")

    if abs(total_weight - 1.0) < 1e-6:
        logger.info("✅ Reward weights normalized (sum = 1.0)")
        return True
    else:
        logger.error(f"❌ Reward weights NOT normalized: {total_weight}")
        return False


def main() -> int:
    """Main validation function."""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " COMPREHENSIVE AGENT CONFIGURATION VALIDATION ".center(68) + "║")
    logger.info("╚" + "=" * 68 + "╝")
    logger.info("")

    results = {
        "SAC":    validate_sac_config(),
        "PPO":    validate_ppo_config(),
        "A2C":    validate_a2c_config(),
        "Reward": validate_reward_function(),
    }

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("FINAL VALIDATION SUMMARY")
    logger.info("=" * 70)

    for agent, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {agent:10s}: {status}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("")
        logger.info("✅ ALL VALIDATIONS PASSED - READY FOR TRAINING")
        logger.info("")
        return 0
    else:
        logger.info("")
        logger.error("❌ VALIDATION FAILED - FIX ERRORS BEFORE TRAINING")
        logger.info("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
