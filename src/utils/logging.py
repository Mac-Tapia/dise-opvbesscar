from __future__ import annotations
import logging
import sys
import time
import functools
from pathlib import Path
from typing import Callable, Any, Optional
from datetime import datetime

# Define TRACE level (lower than DEBUG)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message: str, *args, **kwargs) -> None:
    """Log a message with severity 'TRACE'."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


# Add trace method to Logger class
logging.Logger.trace = trace  # type: ignore


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    include_trace: bool = True,
) -> None:
    """Setup logging with enhanced configuration.
    
    Args:
        level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        include_trace: Whether to enable TRACE level logging
    """
    # Convert string level to int
    if level.upper() == "TRACE" and include_trace:
        numeric_level = TRACE
    else:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create handlers
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        handlers.append(file_handler)
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,  # Override any existing configuration
    )


def get_tracer(name: str, level: str = "INFO") -> logging.Logger:
    """Get a logger with tracing capabilities.
    
    Args:
        name: Logger name (typically __name__)
        level: Minimum logging level
    
    Returns:
        Logger instance with trace method
    """
    logger = logging.getLogger(name)
    if level.upper() == "TRACE":
        logger.setLevel(TRACE)
    else:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def trace_function(func: Callable) -> Callable:
    """Decorator to trace function calls with timing information.
    
    Usage:
        @trace_function
        def my_function(arg1, arg2):
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = logging.getLogger(func.__module__)
        logger.log(TRACE, f"→ Entering {func.__name__}")
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.log(TRACE, f"← Exiting {func.__name__} (elapsed: {elapsed:.4f}s)")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.log(TRACE, f"✗ Exception in {func.__name__} (elapsed: {elapsed:.4f}s): {e}")
            raise
    
    return wrapper


def trace_performance(name: str = "") -> Callable:
    """Decorator to trace performance with custom name.
    
    Usage:
        @trace_performance("training_step")
        def train_step():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            trace_name = name or func.__name__
            logger.log(TRACE, f"⏱ Starting {trace_name}")
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.info(f"✓ {trace_name} completed in {elapsed:.4f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"✗ {trace_name} failed after {elapsed:.4f}s: {e}")
                raise
        
        return wrapper
    return decorator
