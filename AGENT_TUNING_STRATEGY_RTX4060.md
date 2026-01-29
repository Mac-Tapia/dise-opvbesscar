# Estrategia de Tuning de Agentes RL para RTX 4060 (8GB VRAM)
## Basado en Papers Académicos y Naturaleza de Cada Algoritmo

**Contexto:**
- Problema: CityLearn 534-dim obs, 126-dim action, 8,760 timesteps/año
- Hardware: RTX 4060, 8GB VRAM (6-7GB usable)
- Objetivo: Entrenamiento estable sin OOM, convergencia en 3 episodios

---

## 1. SAC (Soft Actor-Critic) - OFF-POLICY

**Naturaleza:** Entrena dos Q-networks con actor separado. Alto sample-efficiency. Requiere large replay buffer.

**Paper:** Haarnoja et al. 2018 "Soft Actor-Critic: Off-Policy Deep RL with a Stochastic Actor"

**Restricciones RTX 4060:**
- Replay buffer crítico pero limitado por memoria
- Batch size pequeño para caber en VRAM
- Learning rate muy conservador (off-policy puede divergir rápido)

**Configuración Óptima SAC:**
```yaml
# Memory Budget: ~2.5GB (buffer + models + activations)
batch_size: 32                    # Paper: 256, RTX4060: 32 (1/8)
buffer_size: 50000               # Paper: 1M, RTX4060: 50k (~4% compression)
learning_rate: 5e-5              # Paper: 3e-4, RTX4060: 5e-5 (conservative off-policy)
gamma: 0.99                       # Paper standard
tau: 0.005                        # Paper: 0.005 (soft update)
ent_coef: 0.001                   # Paper: auto, RTX4060: fixed 0.001 (low entropy)
hidden_sizes: [128, 128]          # Paper: [256,256], RTX4060: [128,128]
gradient_steps: 1                 # Paper: per timestep, RTX4060: 1
learning_starts: 2000             # Paper: 10k, RTX4060: 2k (fewer steps)
target_update_interval: 1         # Every step (tau handles smoothing)
```

**Justificación:**
- Batch 32 vs 256: 8x reducción para memory pressure
- Buffer 50k vs 1M: Aceptable trade-off. SAC sample-efficient, menos buffer OK
- LR 5e-5: Off-policy puede explotar sin cuidado. 5e-5 previene gradient explosion
- Tau 0.005: Paper standard, más stability que averaging
- Ent coef 0.001: Bajo. EV charging task tiene clear optimal actions (no necesita alta exploración)

---

## 2. PPO (Proximal Policy Optimization) - ON-POLICY

**Naturaleza:** Entrena actor + critic (value func) on-policy. Stable, trustworthy. Requiere on-policy data (no replay buffer).

**Paper:** Schulman et al. 2017 "Proximal Policy Optimization Algorithms"

**Restricciones RTX 4060:**
- On-policy = no replay buffer, pero large batch para value estimation
- Clipping mechanism previene large updates
- Critic needs stable value estimates

**Configuración Óptima PPO:**
```yaml
# Memory Budget: ~1.5GB (batch + models)
n_steps: 256                      # Paper: 2048, RTX4060: 256 (on-policy batch)
batch_size: 64                    # Paper: 64-128, RTX4060: 64
n_epochs: 3                        # Paper: 3-10, RTX4060: 3 (fewer updates per batch)
learning_rate: 1e-4               # Paper: 3e-4, RTX4060: 1e-4 (on-policy more stable)
gamma: 0.99                        # Paper standard
gae_lambda: 0.95                   # Paper: 0.95 (Generalized Advantage Est)
clip_range: 0.2                    # Paper: 0.2 (clipping prevents large updates)
hidden_sizes: [128, 128]           # Paper: [64,64], RTX4060: [128,128]
max_grad_norm: 0.5                 # Paper: 0.5
normalize_advantage: true          # Paper standard
normalize_observations: true       # Stabilize input
```

**Justificación:**
- N_steps 256: On-policy batch. PPO estable con pequeños batches
- PPO LR 1e-4 > SAC 5e-5: On-policy más stable inherentemente, puede usar LR más alto
- 3 epochs: Paper says 3-10, RTX4060 limiting, 3 es suficiente
- Clip 0.2: Core mechanism de PPO. Previene policy collapse
- Advantage normalization: Crítico para estabilidad (paper recomendation)

---

## 3. A2C (Advantage Actor-Critic) - ON-POLICY, SIMPLE

**Naturaleza:** Actor + critic, actualización cada step. Más simple que PPO. Menos stable pero rápido.

**Paper:** Mnih et al. 2016 "Asynchronous Methods for Deep RL" (A3C, A2C variant)

**Restricciones RTX 4060:**
- Simplest algorithm, smallest memory footprint
- Can use highest LR (on-policy + simple = stable)
- Faster training per episode

**Configuración Óptima A2C:**
```yaml
# Memory Budget: ~1.0GB (smallest of 3)
n_steps: 128                      # Paper: variable, RTX4060: 128 (short trajectory)
learning_rate: 1e-4               # Paper: 1e-4, RTX4060: 1e-4 (can match PPO)
gamma: 0.99                        # Paper standard
gae_lambda: 0.95                   # Paper: 0.95 (same as PPO)
hidden_sizes: [128, 128]           # Paper: [128,128], RTX4060: [128,128]
max_grad_norm: 0.5                 # Paper: 0.5 (gradient clipping)
normalize_advantage: true          # Standard practice
normalize_observations: true       # Input stabilization
use_rms_prop: true                 # Paper: RMSProp optimizer (more stable)
```

**Justificación:**
- Smallest memory: A2C << PPO << SAC
- LR 1e-4: On-policy simple, can afford higher
- N_steps 128: Short rollouts, fast updates
- RMSProp: Paper standard for A3C/A2C (more stable than Adam)

---

## Memory Breakdown (RTX 4060 = 8GB total)

| Component | Usage | Allocation |
|-----------|-------|-----------|
| OS/CityLearn Base | ~1.5GB | Fixed |
| SAC Training | ~2.5GB | 50k buffer + batch 32 + [128,128] networks |
| PPO Training | ~1.5GB | batch 64 + n_steps 256 + [128,128] networks |
| A2C Training | ~1.0GB | batch 64 + n_steps 128 + [128,128] networks |
| **Max Concurrent** | ~5GB | SAC > PPO > A2C (sequential, not parallel) |

---

## Convergence Expectations

**SAC (Off-Policy):**
- Episode 1: Reward 5.5-6.0 (random exploration)
- Episode 2: Reward 6.0-6.5 (learning starts)
- Episode 3: Reward 6.5-7.0+ (mature policy)
- Metrics: Actor loss stable <10, Critic loss <1.0

**PPO (On-Policy, Stable):**
- Episode 1: Reward 5.8-6.2 (warm-up)
- Episode 2: Reward 6.5-7.0 (convergence)
- Episode 3: Reward 7.0+ (polished)
- Metrics: Policy loss <0.1, Value loss <0.5

**A2C (On-Policy, Simple):**
- Episode 1: Reward 5.5-6.0 (fast initial learning)
- Episode 2: Reward 6.5-7.0 (stabilization)
- Episode 3: Reward 7.0+ (mature)
- Metrics: Most stable overall, low variance

---

## Key Differences Per Algorithm

| Aspect | SAC | PPO | A2C |
|--------|-----|-----|-----|
| **Data Efficiency** | Highest (off-policy) | Medium (on-policy, replay via batch) | Low (on-policy, one-shot) |
| **Stability** | Medium (entropy reg helps) | Highest (clipping, conservative) | High (simple) |
| **Memory** | ~2.5GB | ~1.5GB | ~1.0GB |
| **Best For** | Sample-limited tasks | Stable convergence | Fast training |
| **Paper LR** | 3e-4 | 3e-4 | 1e-4 |
| **RTX4060 LR** | 5e-5 | 1e-4 | 1e-4 |
| **Paper Batch** | 256 | 64-128 | variable |
| **RTX4060 Batch** | 32 | 64 | 64 |

---

## Implementation Strategy

1. **SAC first:** Off-policy learns fastest, sets baseline
2. **PPO second:** Stable on-policy, should improve on SAC
3. **A2C third:** Verify convergence, should be competitive

All configured for **zero divergence** on RTX 4060.
