# Tracing and Debugging Guide

This document explains the tracing and debugging capabilities added to the workspace.

## 🎯 Overview

The workspace now includes comprehensive tracing infrastructure to monitor performance, debug training, and track system metrics during RL agent training.

## 📋 Features

### 1. Enhanced Logging

**Location:** `src/utils/logging.py`

- **TRACE level logging**: More granular than DEBUG for detailed execution traces
- **File logging support**: Logs can be written to files in addition to console
- **Structured formatting**: Consistent timestamp, level, module name, and message format

**Usage:**
```python
from src.utils.logging import setup_logging, get_tracer, trace_function

# Setup logging with TRACE level
setup_logging(level="TRACE", log_file=Path("logs/training.log"))

# Get a tracer logger
logger = get_tracer(__name__, level="TRACE")

# Use trace-level logging
logger.trace("Detailed execution info")
logger.debug("Debug information")
logger.info("General information")

# Decorator for automatic function tracing
@trace_function
def my_function(arg1, arg2):
    # Function execution is automatically traced
    return result
```

### 2. Performance Tracing

**Location:** `src/utils/tracing.py`

- **Performance metrics**: Track execution time, memory usage, and CPU utilization
- **Context managers**: Easy-to-use tracing for code blocks
- **Training-specific tracers**: Specialized for ML training workflows

**Usage:**
```python
from src.utils.tracing import trace_operation, PerformanceTracer, TrainingTracer

# Trace a specific operation
with trace_operation("data_loading", episode=10) as metrics:
    # Your code here
    load_data()
    # Metrics are automatically collected and logged

# Use performance tracer directly
tracer = PerformanceTracer("training_step")
with tracer as metrics:
    train_step()
    # Access metrics.duration_seconds, metrics.peak_memory_mb, etc.

# Training-specific tracing
training_tracer = TrainingTracer(log_dir="logs/traces")

with training_tracer.trace_episode(episode=1):
    # Train episode 1
    pass

# Log summary at the end
training_tracer.log_training_summary()
```

### 3. VS Code Debug Configurations

**Location:** `.vscode/launch.json`

Pre-configured debugging setups:

1. **PPO Training (Debug with Tracing)**
   - Launch PPO training in debug mode
   - Automatic TRACE-level logging
   - Integrated terminal for easy monitoring

2. **SAC Training (Debug with Tracing)**
   - Launch SAC training in debug mode
   - Full tracing enabled

3. **Run Baseline (with Tracing)**
   - Debug baseline comparisons
   - DEBUG-level logging

4. **Python: Current File**
   - Debug any Python file
   - Full workspace integration

5. **Python: Attach to Running Process**
   - Attach debugger to running training processes
   - Useful for long-running jobs

**How to use:**
1. Press `F5` or go to Run > Start Debugging
2. Select the configuration from the dropdown
3. Debugging starts with breakpoint support and variable inspection

### 4. VS Code Tasks

**Location:** `.vscode/tasks.json`

Quick-run tasks for common operations:

1. **PPO Training (with Tracing)**
   - Run: `Ctrl+Shift+B` → Select "PPO Training"
   - Runs in dedicated terminal with full tracing

2. **SAC Training (with Tracing)**
   - Quick SAC training with debugging output

3. **Run Dual Baselines (with Tracing)**
   - Default test task
   - Compare WITH/WITHOUT solar scenarios

4. **Verify Installation**
   - Check that all dependencies are installed

5. **Clean Cache**
   - Remove `.mypy_cache`, `.pytest_cache`, `__pycache__`

6. **Lint with Pylint**
   - Run code quality checks

**How to use:**
1. Press `Ctrl+Shift+P` → "Tasks: Run Task"
2. Select the task from the list
3. Task runs in integrated terminal

### 5. Enhanced VS Code Settings

**Location:** `.vscode/settings.json`

New debugging and tracing settings:

- **Debug inline values**: Show variable values inline during debugging
- **Breakpoint indicators**: Enhanced visibility in the overview ruler
- **File watchers**: Exclude cache and output directories for better performance
- **Search exclusions**: Skip irrelevant directories in search

## 🚀 Quick Start

### Running PPO Training with Tracing

**Option 1: Using VS Code Tasks**
```
1. Press Ctrl+Shift+P
2. Type "Tasks: Run Task"
3. Select "PPO Training (with Tracing)"
4. Training runs with full logging in dedicated terminal
```

**Option 2: Using Debug Configuration**
```
1. Press F5
2. Select "Python: PPO Training (Debug with Tracing)"
3. Set breakpoints if needed
4. Training runs with debugger attached
```

**Option 3: Command Line**
```bash
# With verbose tracing
python -m scripts.ppo_training_pipeline --config configs/default.yaml --verbose

# Set environment variable for trace level
export LOG_LEVEL=TRACE
python -m scripts.ppo_training_pipeline --config configs/default.yaml
```

### Adding Tracing to Your Code

**Minimal integration:**
```python
from src.utils import setup_logging, trace_operation

# At the start of your script
setup_logging(level="DEBUG")

# Wrap important operations
def train_agent():
    with trace_operation("agent_initialization"):
        agent = create_agent()
    
    for episode in range(num_episodes):
        with trace_operation(f"episode_{episode}", episode=episode):
            train_episode(agent)
```

**Advanced integration:**
```python
from src.utils import setup_logging, TrainingTracer, trace_performance

# Setup with file logging
setup_logging(level="TRACE", log_file=Path("logs/training.log"))

# Create training tracer
tracer = TrainingTracer(log_dir="logs/traces")

# Decorate expensive functions
@trace_performance("model_forward")
def forward_pass(model, batch):
    return model(batch)

# Use in training loop
for episode in range(num_episodes):
    with tracer.trace_episode(episode):
        for step in range(steps_per_episode):
            with tracer.trace_step(step):
                # Your training code
                pass

# Print summary
tracer.log_training_summary()
```

## 📊 Tracing Output Examples

### Console Output with Tracing

```
2026-02-05 10:30:15 | INFO     | scripts.ppo_training_pipeline | ======================================================================
2026-02-05 10:30:15 | INFO     | scripts.ppo_training_pipeline | PPO TRAINING PIPELINE
2026-02-05 10:30:15 | INFO     | scripts.ppo_training_pipeline | ======================================================================
2026-02-05 10:30:15 | TRACE    | src.agents.ppo_sb3 | → Entering make_ppo
2026-02-05 10:30:16 | DEBUG    | src.agents.ppo_sb3 | GPU CUDA detectada: NVIDIA GeForce RTX 4060
2026-02-05 10:30:16 | INFO     | src.utils.tracing | ⏱ Tracing: agent_initialization
2026-02-05 10:30:18 | INFO     | src.utils.tracing | ✓ agent_initialization: 2.1234s | Memory: 1024.50MB | CPU: 45.3%
2026-02-05 10:30:18 | TRACE    | src.agents.ppo_sb3 | ← Exiting make_ppo (elapsed: 2.1250s)
```

### Performance Summary

```
======================================================================
TRAINING PERFORMANCE SUMMARY
======================================================================
Total training time: 3600.25s (60.00m)
Episodes completed: 100
Average episode time: 36.0025s
Steps completed: 876000
Average step time: 0.004110s
======================================================================
```

## 🔧 Configuration

### Environment Variables

- `LOG_LEVEL`: Set logging level (TRACE, DEBUG, INFO, WARNING, ERROR)
- `PYTHONUNBUFFERED`: Set to "1" for immediate output (already configured in tasks/launch)

### Python Code Configuration

```python
from src.utils import setup_logging

# Minimal setup
setup_logging(level="INFO")

# With file logging
setup_logging(
    level="DEBUG",
    log_file=Path("logs/training.log"),
    include_trace=True
)
```

## 📚 API Reference

### Logging Functions

- `setup_logging(level, log_file, include_trace)`: Configure logging system
- `get_tracer(name, level)`: Get logger with tracing capabilities
- `trace_function(func)`: Decorator for function-level tracing
- `trace_performance(name)`: Decorator for performance tracing with custom name

### Tracing Classes

- `TraceMetrics`: Container for performance metrics
- `PerformanceTracer`: Context manager for operation tracing
- `trace_operation(name, log_level, **metadata)`: Context manager for quick tracing
- `TrainingTracer`: Specialized tracer for ML training workflows

## 🎓 Best Practices

1. **Use appropriate log levels:**
   - TRACE: Very detailed execution flow
   - DEBUG: Debugging information
   - INFO: General progress updates
   - WARNING: Unexpected but recoverable situations
   - ERROR: Serious problems

2. **Trace expensive operations:**
   - Data loading
   - Model forward/backward passes
   - Environment steps
   - Checkpoint saving/loading

3. **Use context managers:**
   - Cleaner code
   - Automatic cleanup
   - Guaranteed metric collection

4. **Add metadata to traces:**
   ```python
   with trace_operation("training", episode=10, lr=0.001):
       # metadata is included in logs
       pass
   ```

5. **Avoid over-tracing:**
   - Don't trace every single line
   - Focus on major operations
   - Use TRACE level for fine-grained debugging

## 🐛 Debugging Tips

1. **Set breakpoints in VS Code:**
   - Click in the gutter next to line numbers
   - Or press F9 on the line

2. **Use conditional breakpoints:**
   - Right-click breakpoint → Edit Breakpoint
   - Add condition: `episode > 50`

3. **Inspect variables:**
   - Hover over variables during debugging
   - Use Debug Console to evaluate expressions
   - Check Variables panel for all locals/globals

4. **Attach to running process:**
   - Add `import debugpy; debugpy.listen(5678); debugpy.wait_for_client()` to your code
   - Use "Python: Attach to Running Process" configuration

5. **Review trace logs:**
   - Check console output for timing information
   - Look for performance bottlenecks
   - Identify memory leaks or high CPU usage

## 📝 Examples

See the following files for usage examples:
- `scripts/ppo_training_pipeline.py` - Basic logging integration
- `src/agents/ppo_sb3.py` - Logger usage in agents
- `src/utils/logging.py` - Logging utilities implementation
- `src/utils/tracing.py` - Tracing utilities implementation

## 🤝 Contributing

When adding new features:
1. Use the logging utilities consistently
2. Add tracing to expensive operations
3. Update this documentation
4. Test with different log levels
