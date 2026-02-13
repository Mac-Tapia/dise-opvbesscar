# 🗺️ HOJA DE RUTA: Integración de Componentes en learn() Methods
**Status:** 📋 PLANIFICACIÓN - Lista de próximas implementaciones  
**Fecha:** 2026-02-01  
**Fase Actual:** 1 ✅ COMPLETADA (Config aggregation)  
**Fase Próxima:** 2 ⏳ PENDIENTE (learn() method integration)  

---

## 📌 RESUMEN EJECUTIVO

**Lo que se implementó (Fase 1):**
- ✅ 3 nuevos componentes en PPOConfig
- ✅ 6 nuevos componentes en A2CConfig
- ✅ Validación post-init en ambos

**Lo que falta (Fase 2):**
- ⏳ Integración de entropy schedule en PPO.learn()
- ⏳ Integración de VF schedule en PPO.learn()
- ⏳ Integración de Huber loss en PPO.learn()
- ⏳ Split actor/critic optimizers en A2C.learn()
- ⏳ Integración de entropy schedule en A2C.learn()
- ⏳ Integración de advantage normalization en A2C.learn()
- ⏳ Integración de Huber loss en A2C.learn()
- ⏳ Implementación de optimizer selection en A2C.learn()

**Duración estimada:** 2-3 horas de implementación + 1-2 horas testing

---

## 🎯 TAREAS ESPECÍFICAS

### TAREA 1: PPO - Entropy Coefficient Decay Schedule

**Ubicación:** `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` - método `learn()`  
**Línea aproximada:** ~470-500 (dentro del training loop)

**Pseudocódigo:**
```python
def learn(self, episodes: int):
    """Entrenamiento PPO con entropy decay schedule."""
    
    for episode in range(episodes):
        # NUEVO: Calcular entropy schedule
        current_progress = episode / episodes
        
        if self.config.ent_coef_schedule == "linear":
            current_ent_coef = (
                self.config.ent_coef -
                (self.config.ent_coef - self.config.ent_coef_final) * current_progress
            )
        elif self.config.ent_coef_schedule == "exponential":
            # Exponential decay: fast early, slow late
            decay_rate = 3.0  # Adjust for more/less aggressive decay
            current_ent_coef = (
                self.config.ent_coef_final +
                (self.config.ent_coef - self.config.ent_coef_final) *
                np.exp(-current_progress * decay_rate)
            )
        else:  # constant
            current_ent_coef = self.config.ent_coef
        
        # NUEVO: Aplicar entropy schedule al modelo SB3
        # SB3 PPO model tiene policy.optimizer
        for param_group in self.model.policy_optimizer.param_groups:
            param_group['ent_coef'] = current_ent_coef
        
        logger.debug(
            f"[PPO] Episode {episode}/{episodes}: "
            f"ent_coef={current_ent_coef:.6f} (progress={current_progress:.2%})"
        )
        
        # ... rest of training loop
```

**Integración en SB3:**
```python
# Acceso a SB3 PPO model:
self.model = PPO(...)  # PPO agente
self.model.policy_optimizer  # Access optimizer
self.model.policy  # Access policy network

# Modificar entropy coefficient en optimizer:
for param_group in self.model.policy_optimizer.param_groups:
    param_group['ent_coef'] = new_value
```

**Testing:**
```python
def test_ppo_entropy_schedule():
    cfg = PPOConfig(
        ent_coef_schedule="linear",
        ent_coef=0.01,
        ent_coef_final=0.001
    )
    agent = PPOAgent(..., config=cfg)
    
    # Verify entropy decay
    ent_values = []
    for ep in range(100):
        progress = ep / 100
        expected_ent = (
            0.01 - (0.01 - 0.001) * progress
        )
        ent_values.append(expected_ent)
    
    # Should start at 0.01 and end at 0.001
    assert ent_values[0] == approx(0.01)
    assert ent_values[99] == approx(0.001)
    assert ent_values[50] == approx(0.0055)  # Mid-training
```

---

### TAREA 2: PPO - VF Coefficient Schedule

**Ubicación:** `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` - método `learn()`  
**Línea aproximada:** ~500-530

**Pseudocódigo:**
```python
def learn(self, episodes: int):
    """Entrenamiento PPO con VF coefficient schedule."""
    
    for episode in range(episodes):
        current_progress = episode / episodes
        
        # NUEVO: Calcular VF coefficient schedule
        if self.config.vf_coef_schedule == "decay":
            # Decay from vf_coef_init to vf_coef_final
            current_vf_coef = (
                self.config.vf_coef_final +
                (self.config.vf_coef_init - self.config.vf_coef_final) *
                (1.0 - current_progress)  # Reverse progress for decay
            )
        else:  # constant
            current_vf_coef = self.config.vf_coef_init
        
        # NUEVO: Aplicar VF schedule al modelo
        # Access SB3 model's ent_coef (may need custom handling)
        self.model.policy.vf_coef = current_vf_coef
        
        logger.debug(
            f"[PPO] Episode {episode}/{episodes}: "
            f"vf_coef={current_vf_coef:.4f} (progress={current_progress:.2%})"
        )
```

**Nota:** VF coefficient in SB3 PPO may require custom callback for modification.

---

### TAREA 3: PPO - Huber Loss for Value Function

**Ubicación:** `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` - método `make_ppo()`  
**Línea aproximada:** ~460-480 (durante inicialización del modelo)

**Pseudocódigo:**
```python
def learn(self, episodes: int):
    """Entrenamiento PPO con Huber loss."""
    
    # NUEVO: Configurar loss function al inicializar modelo
    if self.config.use_huber_loss:
        from torch.nn import HuberLoss
        self.criterion = HuberLoss(delta=self.config.huber_delta, reduction='mean')
        logger.info(f"[PPO] Using Huber loss (delta={self.config.huber_delta})")
    else:
        from torch.nn import MSELoss
        self.criterion = MSELoss(reduction='mean')
        logger.info("[PPO] Using MSE loss")
    
    # NUEVO: Usar criterion en VF update
    # En SB3 PPO, el VF loss se calcula así:
    # vf_loss = 0.5 * F.mse_loss(value_net(obs), returns)
    
    # Necesitaría custom policy para cambiar esto:
    # self.model.policy._build_vf_loss = lambda obs, returns: \
    #     self.criterion(self.model.value_net(obs), returns)
```

**Implementación Custom Policy:**
```python
from stable_baselines3.ppo import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
import torch.nn as nn

class HuberPPOPolicy(ActorCriticPolicy):
    def __init__(self, *args, huber_loss=True, huber_delta=1.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_huber_loss = huber_loss
        if huber_loss:
            self.criterion = nn.HuberLoss(delta=huber_delta, reduction='mean')
        else:
            self.criterion = nn.MSELoss(reduction='mean')
    
    def evaluate_actions(self, obs, actions):
        """Override to use custom loss function."""
        # Get value estimates
        values = self.value_net(obs)
        
        # ... existing policy logic ...
        
        # Use custom criterion instead of MSE
        # value_loss = self.criterion(values, returns)
        
        return actions_log_prob, entropy, values
```

---

### TAREA 4: A2C - Split Actor/Critic Optimizers

**Ubicación:** `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - método `learn()`  
**Línea aproximada:** ~310-340 (durante inicialización del modelo)

**Pseudocódigo:**
```python
def learn(self, total_timesteps: int):
    """Entrenamiento A2C con actor/critic learning rate split."""
    
    # NUEVO: Identificar parámetros de actor vs critic
    actor_params = []
    critic_params = []
    
    for name, param in self.model.policy.named_parameters():
        if 'actor' in name or 'action' in name:
            actor_params.append(param)
            logger.debug(f"Actor param: {name}")
        elif 'critic' in name or 'value' in name:
            critic_params.append(param)
            logger.debug(f"Critic param: {name}")
    
    # NUEVO: Crear optimizer con learning rates separados
    if self.config.optimizer_type == "adam":
        optimizer = torch.optim.Adam([
            {'params': actor_params, 'lr': self.config.actor_learning_rate},
            {'params': critic_params, 'lr': self.config.critic_learning_rate},
        ])
    elif self.config.optimizer_type == "rmsprop":
        optimizer = torch.optim.RMSprop([
            {'params': actor_params, 'lr': self.config.actor_learning_rate},
            {'params': critic_params, 'lr': self.config.critic_learning_rate},
        ], **self.config.optimizer_kwargs or {})
    
    logger.info(
        f"[A2C] Using {self.config.optimizer_type} optimizer: "
        f"actor_lr={self.config.actor_learning_rate}, "
        f"critic_lr={self.config.critic_learning_rate}"
    )
    
    self.model.policy.optimizer = optimizer  # Override SB3 optimizer
```

**Alternativa Simplificada (Sin Split):**
Si split de optimizers es muy complejo, usar param groups después:
```python
# After model initialization:
optimizer = self.model.policy.optimizer  # SB3's default optimizer

# Modify learning rates via param groups:
for param_group in optimizer.param_groups:
    if 'actor_params' in param_group:  # If we tracked them
        param_group['lr'] = self.config.actor_learning_rate
    elif 'critic_params' in param_group:
        param_group['lr'] = self.config.critic_learning_rate
```

---

### TAREA 5: A2C - Entropy Decay Schedule

**Ubicación:** `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - método `learn()`  
**Línea aproximada:** ~350-380

**Pseudocódigo:**
```python
def learn(self, total_timesteps: int):
    """Entrenamiento A2C con entropy decay schedule."""
    
    total_steps = 0
    
    for step in range(total_timesteps):
        current_progress = step / total_timesteps
        
        # NUEVO: Calcular entropy schedule
        if self.config.ent_coef_schedule == "linear":
            current_ent_coef = (
                self.config.ent_coef -
                (self.config.ent_coef - self.config.ent_coef_final) * current_progress
            )
        elif self.config.ent_coef_schedule == "exponential":
            current_ent_coef = (
                self.config.ent_coef_final +
                (self.config.ent_coef - self.config.ent_coef_final) *
                np.exp(-current_progress * 3.0)
            )
        else:  # constant
            current_ent_coef = self.config.ent_coef
        
        # NUEVO: Aplicar entropy coefficient
        self.model.ent_coef = current_ent_coef
        
        if step % 1000 == 0:
            logger.debug(
                f"[A2C] Step {step}/{total_timesteps}: "
                f"ent_coef={current_ent_coef:.6f}"
            )
```

---

### TAREA 6: A2C - Advantage Normalization

**Ubicación:** `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - método `learn()`  
**Línea aproximada:** ~390-410 (durante batch processing)

**Pseudocódigo:**
```python
def learn(self, total_timesteps: int):
    """Entrenamiento A2C con advantage normalization."""
    
    for batch in data_batches:
        # Extract batch data
        obs_batch = batch['observations']
        actions_batch = batch['actions']
        rewards_batch = batch['rewards']
        
        # NUEVO: Calcular advantages y normalizarlas
        values_batch = self.model.policy.value_net(obs_batch)
        advantages = compute_gae(rewards_batch, values_batch, ...)
        
        # Normalize advantages
        if self.config.normalize_advantages:
            adv_mean = advantages.mean()
            adv_std = advantages.std()
            advantages = (advantages - adv_mean) / (adv_std + self.config.advantage_std_eps)
            logger.debug(
                f"[A2C] Normalized advantages: mean={adv_mean:.4f}, std={adv_std:.4f}"
            )
        
        # Use normalized advantages in training
        actor_loss = -log_probs * advantages
        critic_loss = (values_batch - returns_batch) ** 2
```

---

### TAREA 7: A2C - Huber Loss for Value Function

**Ubicación:** `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - método `learn()`  
**Línea aproximada:** ~420-440

**Pseudocódigo:**
```python
def learn(self, total_timesteps: int):
    """Entrenamiento A2C con Huber loss."""
    
    # NUEVO: Configurar loss function
    if self.config.use_huber_loss:
        self.criterion = torch.nn.HuberLoss(
            delta=self.config.huber_delta,
            reduction='mean'
        )
        logger.info(f"[A2C] Using Huber loss (delta={self.config.huber_delta})")
    else:
        self.criterion = torch.nn.MSELoss(reduction='mean')
        logger.info("[A2C] Using MSE loss")
    
    for batch in data_batches:
        # Get value estimates
        values = self.model.policy.value_net(obs_batch)
        returns = compute_returns(rewards_batch, ...)
        
        # NUEVO: Usar criterion en lugar de MSE
        if self.config.vf_scale != 1.0:
            # Scale returns before computing loss
            returns_scaled = returns * self.config.vf_scale
        else:
            returns_scaled = returns
        
        vf_loss = self.criterion(values, returns_scaled)
        
        logger.debug(f"[A2C] VF loss: {vf_loss:.4f}")
```

---

### TAREA 8: A2C - Optimizer Selection

**Ubicación:** `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - método `learn()`  
**Línea aproximada:** ~310-330 (durante inicialización del modelo)

**Pseudocódigo:**
```python
def learn(self, total_timesteps: int):
    """Entrenamiento A2C con selección de optimizer."""
    
    # NUEVO: Seleccionar optimizer
    if self.config.optimizer_type == "adam":
        optimizer_cls = torch.optim.Adam
        logger.info("[A2C] Using Adam optimizer")
    elif self.config.optimizer_type == "rmsprop":
        optimizer_cls = torch.optim.RMSprop
        logger.info("[A2C] Using RMSprop optimizer (original A2C paper)")
    else:
        logger.warning(f"[A2C] Unknown optimizer: {self.config.optimizer_type}, defaulting to Adam")
        optimizer_cls = torch.optim.Adam
    
    # NUEVO: Pasar kwargs personalizados
    opt_kwargs = self.config.optimizer_kwargs or {}
    
    optimizer = optimizer_cls(
        self.model.policy.parameters(),
        lr=self.config.actor_learning_rate,
        **opt_kwargs
    )
    
    self.model.policy.optimizer = optimizer
    
    logger.info(
        f"[A2C] Optimizer config: type={self.config.optimizer_type}, "
        f"kwargs={opt_kwargs}"
    )
```

---

## 📋 CRONOGRAMA DE IMPLEMENTACIÓN

### Semana 1: PPO Integration
- **Lunes:** Tarea 1 (Entropy schedule)
- **Martes:** Tarea 2 (VF schedule)
- **Miércoles:** Tarea 3 (Huber loss)
- **Jueves:** Testing & debugging PPO
- **Viernes:** Benchmarking PPO

### Semana 2: A2C Integration
- **Lunes:** Tarea 4 (Split optimizers)
- **Martes:** Tarea 5 (Entropy schedule)
- **Miércoles:** Tarea 6 (Advantage normalization)
- **Jueves:** Tarea 7-8 (Huber loss + optimizer selection)
- **Viernes:** Testing & debugging A2C

### Semana 3: Final Validation
- **Full Week:** Integration tests, benchmarking, documentation

---

## 🧪 TESTING STRATEGY

### Unit Tests (Individually)
```python
# Test 1: Entropy decay computation
def test_entropy_schedule():
    values = []
    for progress in np.linspace(0, 1, 11):
        ent = 0.01 - (0.01 - 0.001) * progress
        values.append(ent)
    assert values[0] == 0.01
    assert values[10] == 0.001

# Test 2: VF schedule computation
def test_vf_schedule():
    values = []
    for progress in np.linspace(0, 1, 11):
        vf = 0.1 + (0.3 - 0.1) * (1 - progress)
        values.append(vf)
    assert values[0] == 0.3
    assert values[10] == 0.1

# Test 3: Advantage normalization
def test_advantage_normalization():
    adv = np.array([1, 2, 3, 4, 5])
    adv_norm = (adv - adv.mean()) / (adv.std() + 1e-8)
    assert abs(adv_norm.mean()) < 1e-6
    assert abs(adv_norm.std() - 1.0) < 1e-6
```

### Integration Tests (Full Training)
```python
# Test PPO with entropy decay
def test_ppo_with_entropy_decay():
    cfg = PPOConfig(ent_coef_schedule="linear")
    agent = make_ppo(env, config=cfg)
    agent.learn(episodes=3)
    # Verify agent still trains without errors
    assert agent.model is not None

# Test A2C with actor/critic split
def test_a2c_with_split_lr():
    cfg = A2CConfig(
        actor_learning_rate=1e-4,
        critic_learning_rate=2e-4
    )
    agent = make_a2c(env, config=cfg)
    agent.learn(total_timesteps=100)
    # Verify agent still trains without errors
    assert agent.model is not None
```

### Regression Tests
```python
# Verify old configs still work
def test_backward_compatibility():
    # Old config without schedules
    cfg = PPOConfig()  # All defaults
    assert cfg.ent_coef_schedule == "linear"  # New but with sensible default
    
    # Should not break existing code
    agent = make_ppo(env, config=cfg)
    agent.learn(episodes=1)
```

---

## 📊 SUCCESS CRITERIA

### ✅ PPO Integration
- [ ] Entropy schedule implemented and tested
- [ ] VF schedule implemented and tested
- [ ] Huber loss implemented and tested
- [ ] PPO trains without errors on small 3-episode test
- [ ] Regression tests pass (old configs still work)
- [ ] Benchmark: PPO with schedules > PPO without (or equal)

### ✅ A2C Integration
- [ ] Actor/critic LR split implemented and tested
- [ ] Entropy schedule implemented and tested
- [ ] Advantage normalization implemented and tested
- [ ] Huber loss implemented and tested
- [ ] Optimizer selection implemented and tested
- [ ] A2C trains without errors on small 3-episode test
- [ ] Regression tests pass
- [ ] Benchmark: A2C with components > A2C without (or equal)

### ✅ Final Validation
- [ ] All 8 tasks completed
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All regression tests pass
- [ ] Benchmarking shows improvement or no degradation
- [ ] Documentation updated
- [ ] Ready for full training run

---

## 📝 NOTAS IMPORTANTES

### Compatibilidad SB3
- SB3 PPO y A2C tienen architecture específica
- Algunos parámetros puede que requieran custom policies
- Huber loss específicamente puede necesitar custom implementation

### Order of Operations
1. Entropy schedule ← Easiest, do first
2. Advantage normalization ← Easy
3. VF schedule / Optimizer selection ← Medium
4. Huber loss ← Hardest, requires custom policy
5. Actor/critic split ← Hardest, requires optimizer restructuring

### Logging
- Add detailed logging en cada tarea
- Track entropy/VF values en cada epoch/step
- Log optimizer configuration al iniciar training

---

## 🎯 SIGUIENTES PASOS

1. **Comienza con Tarea 1 (PPO Entropy):** Es la más fácil y demás tareas dependen de patterns similares
2. **Implementa tests mientras trabajas:** No dejes testing para el final
3. **Mantén backward compatibility:** Default behavior no debe cambiar
4. **Documenta mientras avanzas:** Comments inline + update docstrings

---

**Hoja de Ruta Creada:** 2026-02-01  
**Status:** 📋 PLANIFICACIÓN COMPLETADA - LISTO PARA IMPLEMENTACIÓN  
**Próximo Hito:** Comenzar Tarea 1 (PPO Entropy Schedule)  
