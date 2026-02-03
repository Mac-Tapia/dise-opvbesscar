# 🚀 PPO Production Pipeline Guide

## Descripción

Pipeline de producción para entrenar el agente **PPO (Proximal Policy Optimization)** en el proyecto pvbesscar. PPO es un algoritmo **on-policy** que ofrece excelente estabilidad y es ideal para problemas con espacios de acción continuos.

## Características PPO vs SAC

| Característica | PPO | SAC |
|---------------|-----|-----|
| **Tipo** | On-Policy | Off-Policy |
| **Replay Buffer** | No (solo rollouts) | Sí (200k transiciones) |
| **Eficiencia de Datos** | Menor | Mayor |
| **Estabilidad** | Alta | Media-Alta |
| **Exploración** | Via entropy coef | Via entropy automática |
| **Mejor Para** | Estabilidad, problemas nuevos | Eficiencia, fine-tuning |

## Uso Rápido

```bash
# Entrenamiento estándar (100k timesteps ~ 30 min)
python -m scripts.train_ppo_production

# Entrenamiento extendido (500k timesteps ~ 2-3 horas)
python -m scripts.train_ppo_production --timesteps 500000

# Entrenamiento rápido para testing (10k timesteps ~ 3 min)
python -m scripts.train_ppo_production --timesteps 10000

# Continuar desde checkpoint
python -m scripts.train_ppo_production --resume

# Solo evaluación (sin entrenamiento)
python -m scripts.train_ppo_production --eval-only
```

## Hiperparámetros (Optimizados para RTX 4060)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `n_steps` | 2,048 | Rollout buffer size |
| `batch_size` | 256 | Mini-batch para SGD |
| `n_epochs` | 10 | Épocas por rollout |
| `learning_rate` | 1e-4 | Con decay lineal |
| `gamma` | 0.99 | Factor de descuento |
| `gae_lambda` | 0.98 | GAE para advantage |
| `clip_range` | 0.2 | PPO clipping |
| `ent_coef` | 0.01 | Coef. de entropía (decaying) |
| `vf_coef` | 0.5 | Coef. value function |
| `hidden_sizes` | (256, 256) | Arquitectura de red |

## Tiempos Estimados (RTX 4060)

| Timesteps | Duración | Episodios |
|-----------|----------|-----------|
| 10,000 | ~3 min | ~1 |
| 50,000 | ~15 min | ~6 |
| 100,000 | ~30 min | ~11 |
| 500,000 | ~2-3 h | ~57 |

## Estructura de Archivos

```
checkpoints/
└── ppo/
    ├── ppo_step_1000.zip    # Checkpoint cada 1000 steps
    ├── ppo_step_2000.zip
    └── ppo_final.zip        # Checkpoint final

outputs/agents/ppo/
├── ppo_summary.json         # Resumen de métricas
├── result_ppo.json          # Resultados detallados
├── timeseries_ppo.csv       # Serie temporal completa
└── trace_ppo.csv            # Traza obs/actions/rewards
```

## Métricas Multi-Objetivo

PPO usa la misma función de reward multi-objetivo que SAC:

```
reward = 0.50 × r_co2      (Minimizar CO₂)
       + 0.20 × r_solar    (Maximizar autoconsumo)
       + 0.15 × r_cost     (Minimizar costo)
       + 0.10 × r_ev       (Satisfacción EV)
       + 0.05 × r_grid     (Estabilidad red)
```

## Monitoreo de Entrenamiento

### Métricas de Log (cada 500 steps)

```
[PPO] step 500 | ep~0 | reward_avg=0.25 | policy_loss=-0.012 | 
value_loss=45.2 | entropy_loss=0.85 | approx_kl=0.008 |
explained_var=0.65 | clip_fraction=0.12
```

**Interpretación:**
- `reward_avg > 0`: Aprendiendo correctamente
- `approx_kl < 0.02`: Policy estable (no diverge)
- `explained_var > 0.5`: Value function predice bien
- `clip_fraction < 0.3`: Clipping efectivo

### Señales de Problema

| Síntoma | Causa Probable | Solución |
|---------|----------------|----------|
| `approx_kl > 0.05` | Policy cambia muy rápido | Reducir lr a 5e-5 |
| `explained_var < 0` | VF no predice well | Aumentar vf_coef a 0.7 |
| `entropy_loss → 0` | Exploración colapsó | Aumentar ent_coef a 0.02 |
| `clip_fraction > 0.5` | Updates muy grandes | Reducir clip_range a 0.1 |

## Diferencias con SAC Pipeline

1. **Timesteps vs Episodes**: PPO usa timesteps (no episodios)
2. **Sin Replay Buffer**: PPO es on-policy
3. **GAE**: PPO usa Generalized Advantage Estimation
4. **KL Divergence**: PPO monitorea KL para estabilidad

## Troubleshooting

### Error: "Dataset incompleto"
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```

### GPU Out of Memory
Reduce batch_size en código o usa `--timesteps` menor para testing.

### Reward negativo persistente
1. Verificar que dataset tiene 8,760 timesteps
2. Revisar que solar_generation > 0
3. Aumentar exploración: incrementar ent_coef

## Comparación Post-Entrenamiento

Después de entrenar SAC, PPO y A2C, genera tabla comparativa:
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

## Referencias

- [PPO Paper (Schulman et al. 2017)](https://arxiv.org/abs/1707.06347)
- [Stable-Baselines3 PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)
- [GAE Paper](https://arxiv.org/abs/1506.02438)
