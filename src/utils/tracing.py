from __future__ import annotations

import time
import psutil
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TraceMetrics:
    """Container for performance metrics during tracing."""
    
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finalize(self) -> None:
        """Finalize metrics collection."""
        self.end_time = time.perf_counter()
        self.duration_seconds = self.end_time - self.start_time
        
        # Collect system metrics
        try:
            process = psutil.Process()
            self.peak_memory_mb = process.memory_info().rss / (1024 * 1024)
            self.cpu_percent = process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
    
    def __str__(self) -> str:
        """Human-readable representation."""
        metrics_str = f"{self.name}: {self.duration_seconds:.4f}s"
        if self.peak_memory_mb:
            metrics_str += f" | Memory: {self.peak_memory_mb:.2f}MB"
        if self.cpu_percent:
            metrics_str += f" | CPU: {self.cpu_percent:.1f}%"
        return metrics_str


class PerformanceTracer:
    """Context manager for tracing performance of code blocks."""
    
    def __init__(self, name: str, log_level: int = logging.INFO, **metadata):
        """Initialize tracer.
        
        Args:
            name: Name of the traced operation
            log_level: Logging level for trace output
            **metadata: Additional metadata to store
        """
        self.name = name
        self.log_level = log_level
        self.metrics = TraceMetrics(name=name, metadata=metadata)
    
    def __enter__(self) -> TraceMetrics:
        """Enter context - start tracing."""
        logger.log(self.log_level, f"⏱ Tracing: {self.name}")
        return self.metrics
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - finalize and log metrics."""
        self.metrics.finalize()
        
        if exc_type is None:
            logger.log(self.log_level, f"✓ {self.metrics}")
        else:
            logger.error(f"✗ {self.name} failed after {self.metrics.duration_seconds:.4f}s: {exc_val}")
        
        return False  # Don't suppress exceptions


@contextmanager
def trace_operation(name: str, log_level: int = logging.INFO, **metadata):
    """Context manager for tracing operations with performance metrics.
    
    Usage:
        with trace_operation("training_step", episode=10):
            # your code here
            pass
    
    Args:
        name: Name of the operation
        log_level: Logging level
        **metadata: Additional context to log
    """
    tracer = PerformanceTracer(name, log_level, **metadata)
    with tracer as metrics:
        yield metrics


class TrainingTracer:
    """Specialized tracer for ML training with episode/step tracking."""
    
    def __init__(self, log_dir: Optional[str] = None):
        """Initialize training tracer.
        
        Args:
            log_dir: Optional directory to save trace logs
        """
        self.log_dir = log_dir
        self.episode_metrics: list[TraceMetrics] = []
        self.step_times: list[float] = []
        self.start_time = time.perf_counter()
    
    def trace_episode(self, episode: int, **metadata):
        """Trace a single training episode."""
        return trace_operation(
            f"Episode {episode}",
            log_level=logging.INFO,
            episode=episode,
            **metadata
        )
    
    def trace_step(self, step: int, **metadata):
        """Trace a single training step."""
        return trace_operation(
            f"Step {step}",
            log_level=logging.DEBUG,
            step=step,
            **metadata
        )
    
    def log_training_summary(self) -> None:
        """Log summary of training performance."""
        total_time = time.perf_counter() - self.start_time
        logger.info("=" * 70)
        logger.info("TRAINING PERFORMANCE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total training time: {total_time:.2f}s ({total_time/60:.2f}m)")
        
        if self.episode_metrics:
            avg_episode_time = sum(m.duration_seconds or 0 for m in self.episode_metrics) / len(self.episode_metrics)
            logger.info(f"Episodes completed: {len(self.episode_metrics)}")
            logger.info(f"Average episode time: {avg_episode_time:.4f}s")
        
        if self.step_times:
            avg_step_time = sum(self.step_times) / len(self.step_times)
            logger.info(f"Steps completed: {len(self.step_times)}")
            logger.info(f"Average step time: {avg_step_time:.6f}s")
        
        logger.info("=" * 70)
