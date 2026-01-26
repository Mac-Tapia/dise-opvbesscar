# Contributing to pvbesscar

## 📋 Commit Message Guidelines

### Format
```
<type>: <subject> [<scope>]

<body>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation updates
- **refactor**: Code restructuring (no logic change)
- **perf**: Performance improvements
- **test**: Adding/updating tests
- **chore**: Build/config changes
- **ci**: CI/CD pipeline changes

### Examples

**Training Updates:**
```
feat: add SAC agent with optimal hyperparams

- batch_size=512, buffer=1M, LR=1.5e-4, tau=0.005
- GPU auto-detection (CUDA/MPS/CPU)
- Checkpoint resume with reset_num_timesteps=False
```

**Type Safety Fixes:**
```
fix: add type hints and narrowing in data_loader.py

- isinstance() guards for type narrowing
- Explicit float() casting at boundaries
- 35→0 type errors via pyrightconfig: basic
```

**Documentation:**
```
docs: consolidate root markdown files (42→11)

- Removed outdated status/verification docs
- Consolidated training summaries
- Kept essential README, QUICKSTART, config guides
```

---

## 🔍 Code Standards

### Python Type Safety
- **Requirement**: Python 3.11+
- **Type hints**: Required for all function parameters and returns
- **Type narrowing**: Use `isinstance()` guards before operations
- **No suppressions**: Never use `# type: ignore` without explicit approval
- **Configuration**: `pyrightconfig.json` with `typeCheckingMode: basic`

### Example:
```python
from __future__ import annotations

def process_config(config: dict[str, Any]) -> float:
    if not isinstance(config.get('value'), (int, float)):
        raise TypeError(f"Expected number, got {type(config['value'])}")
    return float(config['value'])
```

### Unused Variables
```python
# Prefix with underscore to indicate intentional non-use
_unused_var = something()
_fig, ax = plt.subplots()
```

---

## 📊 Agent Configuration Standards

### Multi-Objective Reward Weights
All weights must sum to 1.0 (auto-normalized in `MultiObjectiveWeights.__post_init__`):

```python
@dataclass
class MultiObjectiveWeights:
    co2: float = 0.50              # Primary: grid CO₂ intensity
    solar: float = 0.20            # Secondary: PV self-consumption
    cost: float = 0.10             # Tertiary: tariff minimization
    ev_satisfaction: float = 0.10  # Service level maintenance
    grid_stability: float = 0.10   # Avoid sudden demand spikes
```

### Agent Hyperparameters

**SAC (Off-policy, sample-efficient):**
```python
batch_size=512
buffer_size=1000000
learning_rate=1.5e-4
tau=0.005  # Target network update rate
```

**PPO (On-policy, stable):**
```python
n_steps=2048
gae_lambda=0.95
learning_rate=3e-4
clip_range=0.2
```

**A2C (On-policy, simple):**
```python
n_steps=5
learning_rate=7e-4
vf_coeff=0.25  # Value function weight
```

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Type Checking
```bash
pyright .                    # Check all files
pyright src/               # Check specific directory
```

### Dataset Validation
```bash
# Solar timeseries must be exactly 8,760 rows (hourly)
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); assert len(df)==8760"
```

---

## 🚀 Execution Pipeline

### Full Training (All Agents)
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Individual Components
```bash
# Build dataset only
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Baseline simulation (no intelligent control)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Agent comparison
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## 📝 Pull Request Checklist

- [ ] Code follows Python 3.11+ type safety standards
- [ ] No `# type: ignore` suppressions without justification
- [ ] Unused variables prefixed with `_`
- [ ] All function signatures include type hints
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Type check passes: `pyright .`
- [ ] Commit message follows guidelines
- [ ] Updated DOCUMENTATION_CONSOLIDATION_PLAN.md if docs changed

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Type errors with pandas Series | Cast with `bool()` before comparisons |
| "Cannot access member" errors | Use `isinstance()` guard before operation |
| Circular imports | Check import order in agent modules |
| GPU out of memory | Reduce batch_size, n_steps; use CPU for debugging |
| Reward divergence | Check MultiObjectiveWeights sum to 1.0 |
| Solar timeseries wrong length | Must be exactly 8,760 rows (hourly, not 15-min) |

---

## 📚 References

- **Architecture**: [ARQUITECTURA_TOMAS_INDEPENDIENTES.md](ARQUITECTURA_TOMAS_INDEPENDIENTES.md)
- **Agent Configs**: [CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md](CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md)
- **Commands**: [COMANDOS_EJECUTABLES.md](COMANDOS_EJECUTABLES.md)
- **Type Safety**: [pyrightconfig.json](pyrightconfig.json)

