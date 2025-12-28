# Quick Reference: Agent Training Commands

## Basic Commands

```bash
# Train all agents with default config (2 episodes)
python -m scripts.run_oe3_train_agents

# Train specific agents
python -m scripts.run_oe3_train_agents --agents SAC PPO
python -m scripts.run_oe3_train_agents --agents SAC

# Custom episodes/timesteps
python -m scripts.run_oe3_train_agents --agents SAC --episodes 10
python -m scripts.run_oe3_train_agents --agents PPO A2C --timesteps 50000

# Specify device
python -m scripts.run_oe3_train_agents --device cuda      # GPU
python -m scripts.run_oe3_train_agents --device cpu       # CPU
python -m scripts.run_oe3_train_agents --device cuda:0    # GPU 0
python -m scripts.run_oe3_train_agents --device cuda:1    # GPU 1
```

## Configuration

Edit `configs/default.yaml`:

```yaml
oe3:
  evaluation:
    agents: ["SAC", "PPO", "A2C"]
    
    sac:
      episodes: 10
      device: cuda
      checkpoint_freq_steps: 8760
      
    ppo:
      timesteps: 87600
      device: cuda
      
    a2c:
      timesteps: 87600
      device: cuda
```

## Output Locations

```
analyses/oe3/training/
├── checkpoints/{agent}/{agent}_final.zip  # Trained models
├── progress/{agent}_progress.csv          # Training metrics
├── {agent}_training_metrics.csv           # Episode history
└── {agent}_training.png                   # Learning curve
```

## Common Workflows

**Quick test (1 min):**
```bash
python -m scripts.run_oe3_train_agents --agents SAC --episodes 1 --device cpu
```

**Production training (1-2 hours with GPU):**
```bash
python -m scripts.run_oe3_train_agents --agents SAC PPO A2C --episodes 10 --device cuda
```

**Hyperparameter tuning:**
1. Edit `configs/default.yaml`
2. Run: `python -m scripts.run_oe3_train_agents`
3. Check: `analyses/oe3/training/*_training_metrics.csv`
4. Repeat until converged

## Verification

```bash
# Check syntax
python -m py_compile scripts/run_oe3_train_agents.py

# View examples
python -m scripts.example_train_agents

# List trained models
ls -lh analyses/oe3/training/checkpoints/*/
```

## Load Pre-trained Models

```python
from iquitos_citylearn.oe3.agents import make_sac, make_ppo, make_a2c

# SAC
agent = make_sac(env)
agent.load("analyses/oe3/training/checkpoints/sac/sac_final")

# PPO
agent = make_ppo(env)
agent.load("analyses/oe3/training/checkpoints/ppo/ppo_final")

# A2C
agent = make_a2c(env)
agent.load("analyses/oe3/training/checkpoints/a2c/a2c_final")

# Use agent
action = agent.predict(observation, deterministic=True)
```

## Troubleshooting

**CUDA out of memory:**
```yaml
sac:
  batch_size: 128  # Reduce from 256
ppo:
  n_steps: 1024    # Reduce from 2048
```

**Slow training:**
- Use GPU: `--device cuda`
- Reduce episodes: `--episodes 5`
- Reduce timesteps: `--timesteps 43800`

**Not converging:**
```yaml
sac:
  learning_rate: 0.0001  # Reduce LR
ppo:
  ent_coef: 0.05         # Increase exploration
```

## More Info

- Full guide: `docs/TRAINING_AGENTS.md`
- Integration: `docs/PIPELINE_INTEGRATION.md`
- Examples: `scripts/example_train_agents.py`
