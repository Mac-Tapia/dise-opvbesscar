# 🔍 Tracing Quick Reference Card

**Last Updated:** 2026-02-05

## 🚀 Quick Start (30 seconds)

### Run PPO Training with Tracing (VS Code)
```
Press F5 → Select "Python: PPO Training (Debug with Tracing)"
```

### Run from Terminal with Full Tracing
```bash
export LOG_LEVEL=TRACE
python -m scripts.ppo_training_pipeline --config configs/default.yaml --verbose
```

## 📝 Common Code Patterns

### 1. Basic Logging Setup
```python
from src.utils import setup_logging, get_tracer

setup_logging(level="DEBUG")  # or "TRACE" for maximum detail
logger = get_tracer(__name__)
logger.info("Training started")
```

### 2. Trace Function Execution
```python
from src.utils import trace_function

@trace_function  # Automatically logs entry/exit with timing
def load_dataset():
    return dataset
```

### 3. Trace Performance of Code Block
```python
from src.utils import trace_operation

with trace_operation("data_loading", batch_size=32):
    data = load_data()
    # Automatically logs: time, memory, CPU usage
```

### 4. Training Loop Tracing
```python
from src.utils import TrainingTracer

tracer = TrainingTracer(log_dir="logs/traces")

for episode in range(n_episodes):
    with tracer.trace_episode(episode):
        train_episode()

tracer.log_training_summary()  # Prints performance stats
```

## 🔧 VS Code Shortcuts

| Action | Shortcut |
|--------|----------|
| Start Debugging | `F5` |
| Toggle Breakpoint | `F9` |
| Step Over | `F10` |
| Step Into | `F11` |
| Continue | `F5` |
| Run Task | `Ctrl+Shift+B` |
| Open Tasks List | `Ctrl+Shift+P` → "Tasks: Run Task" |

## 📊 Available Debug Configurations

1. **PPO Training (Debug with Tracing)** - Full PPO training with TRACE logging
2. **SAC Training (Debug with Tracing)** - Full SAC training with TRACE logging
3. **Run Baseline (with Tracing)** - Baseline comparison with DEBUG logging
4. **Python: Current File** - Debug any Python file
5. **Python: Attach to Running Process** - Attach to running process (port 5678)

## 🛠️ Available Tasks

1. **PPO Training (with Tracing)** - Run PPO in dedicated terminal
2. **SAC Training (with Tracing)** - Run SAC in dedicated terminal
3. **Run Dual Baselines (with Tracing)** - Run WITH/WITHOUT solar baselines
4. **Verify Installation** - Check dependencies
5. **Clean Cache** - Remove `.mypy_cache`, `.pytest_cache`, `__pycache__`
6. **Lint with Pylint** - Code quality checks

## 🎯 Log Levels (from most to least verbose)

- `TRACE` - Very detailed execution flow (function entry/exit, timing)
- `DEBUG` - Debugging information (intermediate values, state)
- `INFO` - General progress updates (default)
- `WARNING` - Unexpected but recoverable situations
- `ERROR` - Serious problems requiring attention
- `CRITICAL` - Critical failures

## 📁 Where Logs Are Saved

- Console: Always visible in terminal/output panel
- File: `logs/training.log` (when file logging enabled)
- Traces: `logs/traces/` (with TrainingTracer)
- Examples: `logs/examples/` (from example script)

## 🐛 Debugging Workflow

1. **Set breakpoints** - Click gutter or press F9
2. **Run debug config** - Press F5, select configuration
3. **Inspect variables** - Hover or check Variables panel
4. **Step through code** - F10 (over), F11 (into)
5. **Check traces** - View timing/memory in console
6. **Fix issues** - Make changes and rerun

## 💡 Pro Tips

### Add Conditional Breakpoint
```
Right-click breakpoint → Edit Breakpoint → Add condition
Example: episode > 50 and loss < 0.1
```

### Attach Debugger to Running Process
```python
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()  # Add where you want to debug
```
Then use "Python: Attach to Running Process" configuration.

### Quick Trace Any Function
```python
from src.utils import trace_performance

@trace_performance("expensive_operation")
def compute_heavy_stuff():
    # Automatically logs duration, memory, CPU
    pass
```

### Save Logs to File
```python
from pathlib import Path
from src.utils import setup_logging

setup_logging(
    level="DEBUG",
    log_file=Path("logs/my_experiment.log")
)
```

## 🔗 See Also

- **Full Guide:** `docs/TRACING_GUIDE.md` - Comprehensive documentation
- **Example Script:** `examples/tracing_example.py` - Working examples
- **VS Code Configs:** `.vscode/launch.json`, `.vscode/tasks.json`

## 🆘 Troubleshooting

**Q: Logs not appearing?**
- Check `LOG_LEVEL` environment variable
- Verify `setup_logging()` called at script start

**Q: Breakpoints not hitting?**
- Ensure "justMyCode": false in launch.json (already set)
- Check correct Python interpreter selected

**Q: Performance tracer failing?**
- Verify psutil installed: `pip show psutil`
- Check memory profiling not conflicting with other tools

**Q: VS Code not finding modules?**
- Set `PYTHONPATH`: Already configured in launch.json
- Check Python interpreter: Should be `.venv/Scripts/python.exe`

---

**Quick Help:** For detailed information, see `docs/TRACING_GUIDE.md`
