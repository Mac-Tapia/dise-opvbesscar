#!/usr/bin/env python
"""Example script demonstrating tracing capabilities.

This script shows how to use the tracing infrastructure for debugging
and performance monitoring in the pvbesscar project.

Usage:
    python examples/tracing_example.py
"""

from __future__ import annotations

import time
import numpy as np
from pathlib import Path

# Import tracing utilities
from src.utils import (
    setup_logging,
    get_tracer,
    trace_function,
    trace_performance,
    trace_operation,
    TrainingTracer,
    TRACE,
)


# Example 1: Basic function tracing
@trace_function
def load_data(n_samples: int = 1000) -> np.ndarray:
    """Simulate loading data with automatic tracing."""
    time.sleep(0.1)  # Simulate I/O
    return np.random.randn(n_samples, 10)


# Example 2: Performance tracing with custom name
@trace_performance("model_training")
def train_model(data: np.ndarray, epochs: int = 5) -> dict:
    """Simulate model training with performance tracking."""
    results = {"loss": []}
    
    for epoch in range(epochs):
        time.sleep(0.05)  # Simulate computation
        loss = np.random.random() * (1 / (epoch + 1))
        results["loss"].append(loss)
    
    return results


def main():
    """Run tracing examples."""
    # Setup logging with TRACE level and file output
    log_dir = Path("logs/examples")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    setup_logging(
        level="TRACE",
        log_file=log_dir / "tracing_example.log",
        include_trace=True
    )
    
    logger = get_tracer(__name__, level="TRACE")
    
    logger.info("=" * 70)
    logger.info("TRACING EXAMPLES")
    logger.info("=" * 70)
    
    # Example 1: Function tracing
    logger.info("\n[Example 1] Function tracing with @trace_function decorator")
    data = load_data(n_samples=5000)
    logger.info(f"Loaded data shape: {data.shape}")
    
    # Example 2: Performance tracing
    logger.info("\n[Example 2] Performance tracing with @trace_performance decorator")
    results = train_model(data, epochs=3)
    logger.info(f"Training losses: {results['loss']}")
    
    # Example 3: Context manager tracing
    logger.info("\n[Example 3] Context manager tracing with trace_operation()")
    with trace_operation("data_preprocessing", n_samples=data.shape[0]) as metrics:
        # Simulate preprocessing
        time.sleep(0.2)
        normalized_data = (data - data.mean()) / data.std()
        logger.debug(f"Data normalized: mean={normalized_data.mean():.4f}, std={normalized_data.std():.4f}")
    
    # Example 4: Training tracer
    logger.info("\n[Example 4] Training-specific tracing with TrainingTracer")
    tracer = TrainingTracer(log_dir="logs/traces")
    
    n_episodes = 5
    steps_per_episode = 10
    
    for episode in range(n_episodes):
        with tracer.trace_episode(episode, total_episodes=n_episodes):
            episode_reward = 0
            
            for step in range(steps_per_episode):
                with tracer.trace_step(step, episode=episode):
                    # Simulate environment step
                    time.sleep(0.01)
                    reward = np.random.random()
                    episode_reward += reward
            
            logger.info(f"Episode {episode} total reward: {episode_reward:.4f}")
    
    # Log training summary
    tracer.log_training_summary()
    
    # Example 5: Nested tracing
    logger.info("\n[Example 5] Nested tracing for complex operations")
    with trace_operation("full_pipeline"):
        with trace_operation("stage_1_data_loading"):
            data = load_data(n_samples=1000)
        
        with trace_operation("stage_2_preprocessing"):
            time.sleep(0.1)
            processed_data = data * 2
        
        with trace_operation("stage_3_training"):
            results = train_model(processed_data, epochs=2)
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ All examples completed successfully!")
    logger.info(f"📄 Logs saved to: {log_dir / 'tracing_example.log'}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
