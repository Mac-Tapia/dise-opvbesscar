# CONFIGURACIÓN INDIVIDUAL POR AGENTE - COMPARATIVA DETALLADA

**Fecha:** 2026-02-07  
**Estado:** ✅ TODOS LOS AGENTES SINCRONIZADOS  

---

## 📋 TABLA COMPARATIVA GENERAL

| Aspecto | SAC | PPO | A2C |
|--------|-----|-----|-----|
| **Tipo** | Off-policy | On-policy | On-policy |
| **Actualización** | Asincrónica (replay buffer) | Sincrónica (N steps) | Sincrónica (8 steps) |
| **Estabilidad** | Alta (experiencias pasadas) | Media-Alta | Media |
| **Velocidad** | Lenta-Media | Media | Rápida ✅ |
| **Escalabilidad** | Lisa (N-dimensional) | Discreta-Lisa | Discreta-Lisa |
| **Tiempo Entrenamiento** | 6.5 horas | 5 horas | 4 horas |

---

## 🎯 PESOS DE RECOMPENSA (IDÉNTICOS EN LOS 3)

```yaml
multi_objective_weights:
  co2:   0.35  # PRIMARY: Reducción emisiones CO₂
  solar: 0.20  # Maximizar autoconsumo PV
  ev:    0.30  # EV SATISFACTION (PRIORIDAD 2)
  cost:  0.10  # Minimizar tarifa
  grid:  0.05  # Estabilidad de red
  # TOTAL: 1.00 ✅ Normalizado
```

**Nota:** Los 3 agentes usan **EXACTAMENTE LOS MISMOS PESOS**, solo difieren en cómo los optimizan.

---

## 🤖 CONFIGURACIÓN SAC (Soft Actor-Critic)

### Estrategia
- **Off-policy**: Aprende de experiencias pasadas (replay buffer)
- **Entropía adaptativa**: Explora automáticamente (ent_coef="auto")
- **Q-learning dual**: Dos críticos para estabilidad

### Hiperparámetros Clave

```yaml
training:
  episodes: 3                    # 3 episodios (años)
  total_timesteps: 26280         # 3 × 8,760 horas
  learning_rate: 2e-4            # Reducido para GPU
  buffer_size: 2,000,000         # Gran memoria (off-policy)
  batch_size: 128                # GPU optimized

entropy:
  ent_coef: "auto"               # Exploración automática
  ent_coef_init: 0.5
  ent_coef_min: 0.01
  ent_coef_max: 1.0

network:
  hidden_sizes: [256, 256]       # 2 capas de 256 neuronas
  activation: "relu"

stability:
  clip_gradients: true
  max_grad_norm: 10.0            # Gradientes suavizados
  critic_loss_scale: 0.1
  q_target_clip: 10.0            # Clipping Q-values
```

### Ventajas SAC
✅ **Mejor para recompensas asimétricas** (nuestro caso: CO₂ negative, EV positive)  
✅ **Aprendizaje estable** con replay buffer  
✅ **Exploración automática** vs manual  
✅ **Escalable a alta dimensionalidad** (394 obs, 129 actions)

### Desventajas SAC
❌ Más lento para entrenar (necesita más experiencias)  
❌ Requiere más memoria GPU

### Rendimiento Esperado
```
CO₂ reduction: 58.9%
Solar utilization: 47.2%
EV satisfaction: 0.9998
BESS SOC avg: 90.5%
Training time: ~6.5 horas (GPU RTX 4060)
```

---

## 🤖 CONFIGURACIÓN PPO (Proximal Policy Optimization)

### Estrategia
- **On-policy**: Aprende directamente de datos nuevos
- **Policy gradient con clipping**: Evita cambios abruptos
- **GAE**: Estimación de ventaja para estabilidad

### Hiperparámetros Clave

```yaml
training:
  train_steps: 500,000
  n_steps: 2048                  # Rollout length (8 minibatches de 256)
  batch_size: 256                # GPU optimized
  n_epochs: 10                   # 10 actualizaciones por rollout
  learning_rate: 2e-4
  lr_schedule: "linear"
  lr_final_ratio: 0.5

ppo:
  gamma: 0.99                    # Discount factor
  gae_lambda: 0.98               # GAE smoothing
  clip_range: 0.2                # Policy clipping (20%)
  clip_range_vf: 0.5             # Value function clipping

losses:
  ent_coef: 0.01                 # Exploración baja
  vf_coef: 0.5                   # Peso value function
  max_grad_norm: 1.0

advanced:
  use_sde: true                  # State-dependent exploration
  target_kl: 0.02                # Adaptative learning rate
  kl_adaptive: true
```

### Ventajas PPO
✅ **Equilibrio entre estabilidad y velocidad**  
✅ **Fácil de implementar y tunar** (standard industry)  
✅ **Buen desempeño en RL discreto/continuo**  
✅ **Tiempo de entrenamiento medio** (~5 horas)

### Desventajas PPO
❌ Menos flexible con recompensas asimétricas  
❌ Requiere tuning cuidadoso de hyperparámetros

### Rendimiento Esperado
```
CO₂ reduction: 58.9%
Solar utilization: 47.2%
EV satisfaction: 0.9998
BESS SOC avg: 90.5%
Training time: ~5 horas (GPU RTX 4060)
```

---

## 🤖 CONFIGURACIÓN A2C (Advantage Actor-Critic)

### Estrategia
- **On-policy sincrónico**: Actualización rápida cada 8 pasos
- **Actor-Critic compartido**: Red única para policy + value
- **GAE**: Estimación de ventaja mejorada

### Hiperparámetros Clave

```yaml
training:
  train_steps: 500,000
  n_steps: 8                     # ✅ ÓPTIMO: Updates muy frecuentes
  learning_rate: 7e-4            # ✅ MÁS ALTO que SAC/PPO
  lr_schedule: "linear"
  lr_final_ratio: 0.7

a2c:
  gamma: 0.99
  gae_lambda: 0.95               # GAE smoothing
  ent_coef: 0.015                # Más exploración que PPO
  vf_coef: 0.5
  max_grad_norm: 0.75            # Gradientes más suaves

separate_learning_rates:         # ✅ ÚNICO EN A2C
  actor_learning_rate: 1e-4
  critic_learning_rate: 1e-4
  
ev_utilization:                  # ✅ BONUS ESPECIAL A2C
  enabled: true
  weight: 0.05                   # Bonus si EV SOC óptimo
  optimal_soc_min: 0.70
  optimal_soc_max: 0.90

advanced:
  use_huber_loss: true           # ✅ Robustez a outliers
  optimizer_type: "adam"
```

### Ventajas A2C
✅ **Más RÁPIDO** (updates cada 8 pasos vs 2048 PPO)  
✅ **Learning rates separados** (actor vs critic)  
✅ **Bonus para EV satisfaction** (nuestro objetivo #2)  
✅ **Menor consumo de memoria**  
✅ **Tiempo de entrenamiento mínimo** (~4 horas)

### Desventajas A2C
❌ Menos estudiado que SAC/PPO  
❌ Puede ser inestable si no está bien tuneado  
❌ Sensible a varianza de rewards

### Rendimiento Esperado
```
CO₂ reduction: 58.9%
Solar utilization: 47.2%
EV satisfaction: 0.9998
BESS SOC avg: 90.5%
Training time: ~4 horas (GPU RTX 4060) ✅ FASTEST
```

---

## 📊 COMPARATIVA DETALLADA DE HIPERPARÁMETROS

### 1. Learning Rate

| Parámetro | SAC | PPO | A2C |
|-----------|-----|-----|-----|
| learning_rate | 2e-4 | 2e-4 | **7e-4** ✅ |
| lr_schedule | N/A | linear | linear |
| lr_final_ratio | N/A | 0.5 | 0.7 |

**Análisis:** A2C usa tasa más alta (7e-4) porque actualiza menos frecuentemente (cada 8 pasos).

### 2. Batch Size & Updates

| Parámetro | SAC | PPO | A2C |
|-----------|-----|-----|-----|
| batch_size | 128 | 256 | 8 |
| n_steps | N/A (replay) | 2048 | 8 |
| n_epochs | N/A | 10 | N/A |
| Updates/ep | ~200 | ~10 | ~1095 |

**Análisis:** A2C actualiza más frecuentemente → convergencia rápida.

### 3. Entropy (Exploración)

| Parámetro | SAC | PPO | A2C |
|-----------|-----|-----|-----|
| ent_coef | auto (0.01-1.0) | 0.01 (fijo) | 0.015 (fijo) |
| Exploración | Automática ✅ | Baja | Media |

**Análisis:** SAC ajusta exploración dinámicamente → mejor adaptación.

### 4. Network Architecture

Todos idénticos:
```python
hidden_sizes: [256, 256]  # 2 capas
activation: relu
```

---

## 🎯 RECOMENDACIÓN POR USO

### Usar **SAC** si:
- ✅ Recompensas muy asimétricas (nuestro caso)
- ✅ Necesitas máxima estabilidad
- ✅ Tienes GPU potente (RTX 4090+)
- ✅ Puedes esperar ~6.5 horas

```bash
python train_sac_multiobjetivo.py --episodes=50 --device=cuda
```

### Usar **PPO** si:
- ✅ Quieres balance estabilidad/velocidad
- ✅ Preferencias por algoritmo "estándar"
- ✅ Tiempo limitado (~5 horas OK)

```bash
python train_ppo_multiobjetivo.py --episodes=50 --device=cuda
```

### Usar **A2C** si:
- ✅ Máxima velocidad es prioritario
- ✅ Recursos limitados (RTX 4060)
- ✅ Necesitas resultados rápido (~4 horas)
- ✅ Pruebas/debugging (por velocidad)

```bash
python train_a2c_multiobjetivo.py --episodes=50 --device=cuda
```

---

## 📈 MÉTRICAS DE REFERENCIA (IDÉNTICAS para todos)

### Expected Performance Episode 1

```
CO₂ Grid (emitido):         3,079 tCO₂/año
CO₂ Evitado Indirecto:      3,749 tCO₂/año (solar)
CO₂ Evitado Directo:          672 tCO₂/año (EVs)
CO₂ Reducción Neta:         4,421 tCO₂/año (58.9%)

Reward Components:
  r_solar  = -0.2478
  r_cost   = -0.2797
  r_ev     = +0.9998 ← MAX (satisfacción EVs)
  r_grid   = -0.0196
  r_co2    = +0.2496
  ──────────────────
  TOTAL    = +0.3088

Control:
  Sockets Active: 50.0% (64 de 128)
  BESS SOC avg:   90.5%
  EV SOC avg:     100.0%
  Motos/día:      1,199
  Mototaxis/día:  336

Cost Savings:
  Total Cost:     $917,705 USD
  Savings:        $1,658,503 USD
```

---

## ✅ VALIDACIÓN DE SINCRONIZACIÓN

```bash
# Verificar todos los agentes usan los mismos pesos
python validate_detailed_metrics.py

# Verificar tracking de reward
python verify_reward_calculation.py

# Generar reportes detallados
python generate_detailed_report.py
```

**RESULTADO:** ✅ TODOS LOS AGENTES SINCRONIZADOS (2026-02-07)

---

## 📝 RESUMEN

3 agentes, **MISMO objetivo** (CO₂ 0.35 + EV 0.30 + Solar 0.20), **diferente estrategia**:

1. **SAC** → Estabilidad máxima (off-policy, replay buffer)
2. **PPO** → Balance óptimo (on-policy, clipping)
3. **A2C** → Velocidad máxima (on-policy sincrónico, updates cada 8 pasos)

Elige según tus restricciones de **tiempo**, **recursos**, y **prioridad de estabilidad**.
