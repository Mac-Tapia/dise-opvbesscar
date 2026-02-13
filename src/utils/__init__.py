"""Utilidades compartidas del proyecto."""

from .agent_utils import (
    validate_env_spaces,
    ensure_checkpoint_dir,
    ListToArrayWrapper,
    flatten_action,
    unflatten_action,
    validate_checkpoint,
    clip_observations,
    normalize_observations,
    denormalize_observations,
    scale_reward,
)

from .logging import (
    setup_logging,
    get_tracer,
    trace_function,
    trace_performance,
    TRACE,
)

from .tracing import (
    TraceMetrics,
    PerformanceTracer,
    trace_operation,
    TrainingTracer,
)

__all__ = [
    # Agent utilities
    "validate_env_spaces",
    "ensure_checkpoint_dir",
    "ListToArrayWrapper",
    "flatten_action",
    "unflatten_action",
    "validate_checkpoint",
    "clip_observations",
    "normalize_observations",
    "denormalize_observations",
    "scale_reward",
    # Logging utilities
    "setup_logging",
    "get_tracer",
    "trace_function",
    "trace_performance",
    "TRACE",
    # Tracing utilities
    "TraceMetrics",
    "PerformanceTracer",
    "trace_operation",
    "TrainingTracer",
]
