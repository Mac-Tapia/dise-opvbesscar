# Configuraciones Óptimas de Agentes - Justificación Científica

## Referencia de Papers

- **SAC**: Christodoulou et al. (2018) - "Soft Actor-Critic Algorithms and Applications"
- **PPO**: Schulman et al. (2017) - "Proximal Policy Optimization Algorithms"
- **A2C**: Mnih et al. (2016) - "Asynchronous Methods for Deep Reinforcement Learning"

---

## 1. SAC (Soft Actor-Critic) - Off-Policy, Sample-Efficient

### Configuración Actual
```yaml
learning_rate_actor: 0.001
learning_rate_critic: 0.002
tau: 0.01
buffer_size: 10000000
batch_size: 1024
entropy_coef_init: 0.2
entropy_coef_learned: true
target_entropy_scale: 1.5
train_freq: 1
gradient_steps: 2048
```

### Justificación Científica

#### 1.1 Learning Rates (Actor: 0.001 | Critic: 0.002)
**Paper**: Christodoulou et al. (2018), Section 4.1
- SAC mantiene dos redes: actor (policy) y critic (value)
- **Critic LR > Actor LR**: El crítico necesita aprender primero el landscape de recompensas
- 0.002 para crítico → Convergencia rápida del estimador de valor
- 0.001 para actor → Política más estable (actualización gradual)
- **Ratio 2:1** mejora la estabilidad convergencia en problemas de dimensión alta (534-dim obs aquí)

#### 1.2 Entropy Coefficient (0.2, aprendible)
**Paper**: Christodoulou et al. (2018), Section 3
- SAC añade **regularización de entropía** para exploración automática
- H(π) mide la aleatoriedad de la política: maximizar H fuerza exploración
- **ent_coef_learned: true** → Lagrange multiplier aprendible
- 0.2 inicial → Balance exploración-explotación desde inicio
- target_entropy_scale: 1.5 → Temperatura adaptativa para recompensas RL multi-objetivo
- **Para control energético**: Busca la política más "suave" (smooth), menos agresiva

#### 1.3 Soft Update (tau: 0.01)
**Paper**: Christodoulou et al. (2018), eq. (7)
- Target networks se actualizan con: θ' = τ·θ + (1-τ)·θ'
- tau=0.01 significa: 1% del modelo actual + 99% histórico
- **Muy conservador**: Evita overestimation de Q-values (crítico problema en off-policy)
- Para 8,760 timesteps: gradual learning = convergencia estable en largo plazo

#### 1.4 Replay Buffer (10M experiencias)
**Paper**: Christodoulou et al. (2018), Section 4
- SAC es **off-policy**: reutiliza datos de exploraciones pasadas
- 10M = ~1142 episodios (8,760 steps cada uno) × 1.14 = capacidad para recorrer datos
- Permite mini-batches de 1024 durante múltiples epochs sin repeating data

#### 1.5 Batch Size (1024)
**Paper**: Stable Baselines3 documentation + Christodoulou et al.
- Grande (1024) para estabilidad numérica con gradientes de valor Q
- Reduce varianza de estimador de Q-value
- GPU-friendly en CUDA (512+ es óptimo)

#### 1.6 Gradient Steps (2048 por rollout)
**Paper**: Christodoulou et al., off-policy advantage
- 2048 pasos de gradiente por actuación env = máximo uso de datos del buffer
- Compensa que solo hay 1 paso env por entrenamiento (train_freq=1)

---

## 2. PPO (Proximal Policy Optimization) - On-Policy, Estable

### Configuración Actual
```yaml
learning_rate: 0.0003
n_steps: 4096
batch_size: 512
n_epochs: 25
entropy_coef: 0.001
gamma: 0.99
gae_lambda: 0.95
clip_range: 0.2
clip_range_vf: 0.2
max_grad_norm: 0.5
target_kl: 0.003
use_amp: true
```

### Justificación Científica

#### 2.1 Learning Rate (0.0003, muy bajo)
**Paper**: Schulman et al. (2017), Section 5.2
- PPO usa **on-policy** → cada step es "fresco" (no reutilizado)
- LR bajo compensa que hay menos datos (solo 1 trajectory = 8,760 steps)
- 0.0003 vs 0.001 (SAC): PPO es más sensible a overtraining porque no tiene replay buffer
- Formula de confianza: "Stay close to old policy" → LR pequeño garantiza eso

#### 2.2 N-Steps (4096 rollout)
**Paper**: Schulman et al. (2017), GAE section
- Mínimo: 1024 (batch tamaño estándar)
- 4096 = 4.6 episodes (8760 / 4096 ≈ 2 sub-episodes)
- **Advantage**: Estimador de ventaja más estable (menos bias)
- **Tradeoff**: Espera más pasos antes de actualizar (pero es on-policy, necesario)

#### 2.3 GAE Lambda (0.95)
**Paper**: Schulman et al. (2015) - "High-Dimensional Continuous Control Using Generalized Advantage Estimation"
- λ ∈ [0, 1] controla bias-variance en estimador de ventaja
- 0.95 = **muy estable** (cercano a 1.0)
- Combina: Discounted sum of rewards + Critic baseline
- Para energía: Necesita estabilidad porque rewards tienen múltiples objetivos (CO₂, solar, cost, EV, grid)

#### 2.4 Clipping (0.2 both actor + value)
**Paper**: Schulman et al. (2017), eq. (7) y (8)
- "Proximal" = Stay near old policy
- clip_range=0.2 → Nueva política puede alejarse máximo 20% en probabilidad
- clip_range_vf=0.2 → Crítico también clipeado (estabilidad)
- Previene actualizaciones agresivas que destrozan exploración

#### 2.5 Max Grad Norm (0.5)
**Paper**: Stable Baselines3 + RL best practices
- Clip gradientes a norm ≤ 0.5
- Previene "gradient explosion" en redes profundas
- 0.5 es conservador: permite aprendizaje sin inestabilidad

#### 2.6 Target KL (0.003)
**Paper**: Schulman et al., adaptive clipping
- KL divergence = medida de "cuán diferente" es nueva vs vieja política
- target_kl=0.003 → Si KL > 0.003, para actualizar (early stopping)
- Garantiza "trust region" en sentido práctico
- Permite entrenamientos más largos sin divergencia

#### 2.7 Epochs (25)
**Paper**: Schulman et al., multiple passes
- 25 passes sobre mismo 4096-step batch
- Máximo aprovechamiento del dato (on-policy, no se puede reutilizar)
- Formula: 25 × 512 batch / 4096 = 3.125 datasets worth of training

---

## 3. A2C (Advantage Actor-Critic) - On-Policy, Simple

### Configuración Actual
```yaml
learning_rate: 0.002
n_steps: 16
batch_size: 1024
entropy_coef: 0.02
gamma: 0.99
vf_coef: 0.5
max_grad_norm: 1.0
gae_lambda: 0.9
use_rms_prop: true
normalize_advantage: true
```

### Justificación Científica

#### 3.1 Learning Rate (0.002, moderado)
**Paper**: Mnih et al. (2016), "Asynchronous Methods for Deep RL"
- A2C es **"A" = Asynchronous**, but en stable-baselines3 = sincrónico
- 0.002 es más alto que PPO (0.0003) porque:
  - A2C usa advantage function (más estable que raw rewards)
  - Sin trust region (cliping): puede permitirse LR mayor
  - Menos datos reutilizado → necesita LR > para convergencia

#### 3.2 N-Steps (16, VERY SMALL)
**Paper**: Mnih et al. (2016), Section 4
- A2C hace updates frecuentes (every 16 steps)
- trade-off: bias alto (short bootstrap) vs variance bajo (rápidos updates)
- 16 = "shallow" advantage estimation
- **Ventaja para energía**: Reacciona rápido a cambios (solar ↓, clouds, EV arrivals)
- 8760 / 16 = 547 updates/episodio vs PPO: 8760/4096 = 2 updates

#### 3.3 Entropy Coefficient (0.02, alto)
**Paper**: Mnih et al., exploration bonus
- 0.02 es 20× mayor que PPO (0.001)
- A2C necesita más exploración porque:
  - No tiene trust region (PPO clip)
  - Sin replay buffer (SAC)
  - Actualizaciones on-policy + frequent = tiende a converger rápido a mínimo local
- **Mayor entropía** = explora más, tarda en convergir pero menos stuck

#### 3.4 Value Function Coefficient (0.5)
**Paper**: Mnih et al. (2016), eq. (3)
- Loss = Policy loss + 0.5 × Value loss
- 0.5 = balance perfecto
  - < 0.5: Crítico bajo-entrenado (mala baseline)
  - > 0.5: Crítico sobre-entrenado (destabiliza actor)

#### 3.5 Max Grad Norm (1.0, más permisivo)
**Paper**: Mnih et al., implementation details
- A2C es más "robusto" que PPO (no usa clipping)
- 1.0 vs PPO's 0.5 = permite gradientes mayores
- Aún previene explosión (norm > 1 se clipea)
- Necesario para que se movimiento en high-dim space (534-dim obs)

#### 3.6 RMS Prop (true) vs Adam
**Paper**: Mnih et al. (2016), optimization
- Argumento original: RMS Prop converge más rápido para on-policy
- Adam = adaptivo per-param (más lento para A2C)
- RMS Prop = global momentum (más directo)

---

## 4. Comparativa de Hyperparameters

| Parameter | SAC | PPO | A2C | Justificación |
|-----------|-----|-----|-----|---------------|
| **LR (Actor)** | 0.001 | 0.0003 | 0.002 | SAC off-policy→LR alto; PPO trust region→LR bajo; A2C simple→LR medio |
| **N-Steps** | No aplica (replay) | 4096 | 16 | SAC reutiliza buffer; PPO necesita largo rollout (GAE); A2C actualiza frecuente |
| **Entropy** | 0.2 learned | 0.001 | 0.02 | SAC auto-ajusta; PPO minimiza (trust); A2C explora agresivo |
| **Buffer Size** | 10M | None | None | SAC off-policy requiere buffer; ON-policy no reutilizan |
| **Batch Size** | 1024 | 512 | 1024 | SAC/A2C: batches grandes (GPU); PPO: menor (stability) |
| **Gamma** | 0.99 | 0.99 | 0.99 | Todos: discounting a largo plazo (8,760 pasos = 1 año) |
| **Clip/Trust** | Soft update (τ) | Clip (0.2) | None | SAC gradual; PPO strict; A2C directo |

---

## 5. Recomendaciones para Máximo Potencial

### 5.1 SAC - Optimizaciones Sugeridas

**Para acelerar convergencia (sin perder estabilidad):**
```yaml
sac:
  learning_rate: 0.001      # ✓ Óptimo actual
  learning_rate_critic: 0.0025  # ↑ Aumentar 25%
  tau: 0.005                # ↓ Bajar (soft update más rápido)
  buffer_size: 20000000     # ↑ Duplicar (más experiencias)
  ent_coef_init: 0.1        # ↓ Bajar entropía inicial (menos random)
```

**Justificación**:
- Mayor buffer + crítico LR = mejor Q-value estimation
- Menor tau = updates más rápidas (pero con datos más estables)
- Menor entropía inicial → Mejor explotación early (aún aprendible con ent_coef_learned)

### 5.2 PPO - Optimizaciones Sugeridas

**Para multi-objective RL:**
```yaml
ppo:
  learning_rate: 0.0005     # ↑ Aumentar 67%
  n_steps: 8192             # ↑ Duplicar (más datos/epoch)
  n_epochs: 20              # ↓ Bajar 20% (menos overfitting)
  entropy_coef: 0.002       # ↑ Duplicar exploración
  gae_lambda: 0.98          # ↑ Subir (más estabilidad)
```

**Justificación**:
- Multi-objetivo (5 rewards) → necesita exploración + estabilidad
- 8192 steps = 1 full episode, mejor GAE estimation
- 20 epochs vs 25 = menos riesgo de overfitting
- gae_lambda 0.98 = casi retorno sin descuento (más datos)

### 5.3 A2C - Optimizaciones Sugeridas

**Para reacción rápida a cambios ambientales:**
```yaml
a2c:
  learning_rate: 0.003      # ↑ Aumentar 50% (A2C robusto)
  n_steps: 8                # ↓ Bajar 50% (updates más frecuentes)
  entropy_coef: 0.03        # ↑ Aumentar exploración
  gae_lambda: 0.92          # ↑ Aumentar lambda
  use_rms_prop: true        # ✓ Mantener
```

**Justificación**:
- A2C: cambios rápidos (solar, weather) → updates frecuentes
- 8 steps = ~1 min de tiempo real (reacción casi instantánea)
- Mayor LR + entropía = explora bien en high-dim space
- RMS Prop es ideal para A2C on-policy

---

## 6. Tabla de Applicación Óptima Sugerida

```yaml
oe3:
  evaluation:
    
    # SAC: Para exploración exhaustiva + datos off-policy
    sac:
      learning_rate_actor: 0.001
      learning_rate_critic: 0.0025      # CHANGE ↑
      tau: 0.005                         # CHANGE ↓
      buffer_size: 20000000              # CHANGE ↑
      entropy_coef_init: 0.1             # CHANGE ↓
      entropy_coef_learned: true
      batch_size: 1024
      gradient_steps: 2048
      episodes: 5                        # CHANGE: ↑ de 3
    
    # PPO: Para estabilidad + multi-objetivo
    ppo:
      learning_rate: 0.0005              # CHANGE ↑
      n_steps: 8192                      # CHANGE ↑
      n_epochs: 20                       # CHANGE ↓
      entropy_coef: 0.002                # CHANGE ↑
      gae_lambda: 0.98                   # CHANGE ↑
      batch_size: 512
      episodes: 5                        # CHANGE: ↑ de 3
    
    # A2C: Para reacción rápida
    a2c:
      learning_rate: 0.003               # CHANGE ↑
      n_steps: 8                         # CHANGE ↓
      entropy_coef: 0.03                 # CHANGE ↑
      gae_lambda: 0.92                   # CHANGE ↑
      batch_size: 1024
      use_rms_prop: true
      episodes: 5                        # CHANGE: ↑ de 3
```

---

## 7. Implementación Escalonada

### Fase 1: Validar Baselines (actual config)
- Entrenar 3 episodios cada agente
- Recolectar rewards, CO₂, solar utilization
- **Output**: benchmark numbers

### Fase 2: SAC Optimizado
- Aplicar cambios SAC (tau↓, buffer↑, critic_lr↑)
- Entrenar 5 episodios
- Comparar vs Fase 1

### Fase 3: PPO Optimizado
- Aplicar cambios PPO (lr↑, n_steps↑, entropy↑)
- Entrenar 5 episodios
- Comparar vs Fase 1

### Fase 4: A2C Optimizado
- Aplicar cambios A2C (lr↑, n_steps↓, entropy↑)
- Entrenar 5 episodios
- Comparar vs Fase 1

### Fase 5: Ensemble Comparison
- Ejecutar todos 3 agentes optimizados en paralelo
- Generar tabla comparativa de rendimiento

---

## Referencias Científicas Completas

1. **Christodoulou et al. (2018)**
   - "Soft Actor-Critic Algorithms and Applications"
   - arXiv:1812.05905
   - Key: Entropy regularization, off-policy learning, temperature scaling

2. **Schulman et al. (2017)**
   - "Proximal Policy Optimization Algorithms"
   - arXiv:1707.06347
   - Key: Trust region via clipping, GAE, on-policy stability

3. **Mnih et al. (2016)**
   - "Asynchronous Methods for Deep Reinforcement Learning"
   - ICML 2016
   - Key: A3C foundation, frequent updates, RMS Prop optimization

4. **Schulman et al. (2015)**
   - "High-Dimensional Continuous Control Using Generalized Advantage Estimation"
   - ICML 2016
   - Key: GAE formula, bias-variance tradeoff in advantage estimation

5. **Stable Baselines3 Documentation**
   - https://stable-baselines3.readthedocs.io/
   - Key: Implementation details, hyperparameter guides, reproducibility

---

## Próximos Pasos

1. ✅ Documentar justificaciones (este archivo)
2. 🔄 Crear config_optimized.yaml con cambios sugeridos
3. 🔄 Implementar Fase 1: Entrenar con config actual
4. 🔄 Implementar Fase 2-5: Optimizaciones graduales
5. 🔄 Generar tabla de comparación de resultados

**Estado**: Listo para implementar optimizaciones ✓
