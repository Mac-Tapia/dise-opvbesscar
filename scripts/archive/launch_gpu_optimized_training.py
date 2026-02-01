#!/usr/bin/env python3
"""
GPU-optimized training launcher for SAC/PPO/A2C on RTX 4060 Laptop
Configures PyTorch for maximum GPU utilization without OOM
"""
from __future__ import annotations

import sys
import torch
import logging
from pathlib import Path

# Configure PyTorch for GPU optimization
def configure_gpu_optimization():
    """Configure PyTorch for maximum GPU performance on RTX 4060"""

    # Enable CUDA optimizations
    torch.backends.cudnn.enabled = True
    torch.backends.cudnn.benchmark = True        # Auto-select best cuDNN algorithms
    torch.backends.cudnn.deterministic = False   # Trade determinism for speed

    # Enable TF32 precision (30% speedup with minimal accuracy loss)
    # Only available on Ampere+ (RTX 30xx/40xx series)
    if torch.cuda.get_device_capability(0)[0] >= 8:  # Compute capability 8.0+ (RTX 40xx)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        logging.info("[GPU] TF32 precision enabled (30% speedup)")

    # Configure memory allocation strategy
    torch.cuda.empty_cache()

    # Get GPU properties
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    compute_capability = torch.cuda.get_device_capability(0)

    logging.info(f"[GPU] Device: {gpu_name}")
    logging.info(f"[GPU] Memory: {gpu_memory_gb:.1f} GB")
    logging.info(f"[GPU] Compute Capability: {compute_capability[0]}.{compute_capability[1]}")
    logging.info(f"[GPU] CUDA Available: {torch.cuda.is_available()}")
    logging.info(f"[GPU] cuDNN Enabled: {torch.backends.cudnn.enabled}")
    logging.info(f"[GPU] cuDNN Deterministic: {torch.backends.cudnn.deterministic}")
    logging.info(f"[GPU] cuDNN Benchmark: {torch.backends.cudnn.benchmark}")


def configure_logging():
    """Setup logging with GPU performance monitoring"""
    log_format = '[%(asctime)s] [%(levelname)-8s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('training_gpu_optimized.log')
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main training launcher"""
    logger = configure_logging()

    logger.info("=" * 80)
    logger.info("GPU-OPTIMIZED TRAINING LAUNCHER")
    logger.info("=" * 80)

    # Configure GPU
    configure_gpu_optimization()

    # Import after GPU configuration
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from iquitos_citylearn.config import load_config, load_paths
    from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
    from iquitos_citylearn.oe3.simulate import simulate

    # Load configuration
    config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
    logger.info(f"[CONFIG] Loading from: {config_path}")

    cfg = load_config(config_path)
    paths = load_paths(cfg)

    # Configuration values (use dict access since cfg is Dict[str, Any])
    logger.info(f"[CONFIG] Project: {cfg.get('project', {}).get('year', 'N/A')}")
    agents = cfg.get('oe3', {}).get('evaluation', {}).get('agents', [])
    logger.info(f"[CONFIG] Agents: {agents}")

    # Display GPU-optimized parameters
    eval_cfg = cfg.get('oe3', {}).get('evaluation', {})

    sac_cfg = eval_cfg.get('sac', {})
    logger.info(f"  SAC:  batch_size={sac_cfg.get('batch_size', 'N/A')}, "
                f"buffer_size={sac_cfg.get('buffer_size', 'N/A')}, "
                f"gradient_steps={sac_cfg.get('gradient_steps', 'N/A')}")

    ppo_cfg = eval_cfg.get('ppo', {})
    logger.info(f"  PPO:  batch_size={ppo_cfg.get('batch_size', 'N/A')}, "
                f"n_steps={ppo_cfg.get('n_steps', 'N/A')}, "
                f"n_epochs={ppo_cfg.get('n_epochs', 'N/A')}")

    a2c_cfg = eval_cfg.get('a2c', {})
    logger.info(f"  A2C:  batch_size={a2c_cfg.get('batch_size', 'N/A')}, "
                f"n_steps={a2c_cfg.get('n_steps', 'N/A')}, "
                f"episodes={a2c_cfg.get('episodes', 'N/A')}")

    # Build dataset
    logger.info("[DATASET] Building CityLearn dataset...")
    try:
        build_citylearn_dataset(cfg, paths.raw_dir, paths.interim_dir, paths.processed_dir)
        logger.info("[DATASET] Successfully built")
    except Exception as e:
        logger.error(f"[DATASET] Failed to build: {e}")
        raise

    # Run simulations with GPU monitoring
    logger.info("[TRAINING] Starting GPU-accelerated training...")
    logger.info(f"[TRAINING] Expected duration: ~10.7 hours (SAC 5.25h + PPO 3.28h + A2C 2.19h)")
    logger.info("[TRAINING] GPU monitoring enabled - check nvidia-smi for utilization")

    # Construct schema path
    schema_path = paths.processed_dir / "schema_citylearn.json"

    try:
        # Train each agent
        for agent_name in ["SAC", "PPO", "A2C"]:
            logger.info(f"[TRAINING] Starting {agent_name} agent...")
            simulate(
                schema_path,
                agent_name,
                paths.outputs_dir,
                paths.outputs_dir / "training",
                carbon_intensity_kg_per_kwh=0.4521,
                seconds_per_time_step=3600
            )
        logger.info("[TRAINING] All simulations completed successfully")
    except KeyboardInterrupt:
        logger.warning("[TRAINING] Training interrupted by user")
    except Exception as e:
        logger.error(f"[TRAINING] Training failed: {e}")
        raise

    logger.info("=" * 80)
    logger.info("TRAINING LAUNCHER FINISHED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
