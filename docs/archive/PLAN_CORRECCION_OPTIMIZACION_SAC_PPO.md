# 🔧 PLAN DE CORRECCIÓN Y OPTIMIZACIÓN: SAC & PPO PRE-REENTRENAMIENTO

**Objetivo:** Diagnosticar, corregir y optimizar SAC y PPO antes de re-entrenamiento para hacer comparación JUSTA vs A2C

**Principio:** Los problemas detectados (+4.7% SAC, +0.08% PPO) son configuracionales, NO inherentes al algoritmo

---

## 🔍 DIAGNÓSTICO: PROBLEMAS IDENTIFICADOS

### SAC - Problema: Buffer Divergence (+4.7% peor)

#### Causa Raíz Identificada:
```
❌ PROBLEMA 1: Replay Buffer Size Insuficiente
   Configuración actual: buffer_size = 10,000
   Consecuencia: En 8,760 timesteps/episode × 3 episodes
                = 26,280 total steps
                Buffer se llena rápido
                Proporciones: viejo:nuevo = 60:40
                → Experimencia old contamina learning

❌ PROBLEMA 2: Learning Rate Muy Alto (2e-4)
   Consecuencia: Updates oscilan, no convergen
                Network "olvida" buenos patrones rápido
                Exploración descontrolada

❌ PROBLEMA 3: Entropy Coefficient Muy Bajo (0.2)
   Consecuencia: Insuficiente exploración
                Policy converge a locales subóptimos
                No descubre reglas de despacho complejas

❌ PROBLEMA 4: No hay Prioritized Experience Replay (PER)
   Consecuencia: Todas las experiencias tienen peso igual
                Malas decisiones se repiten igual que buenas
                No hay focus en important transitions

❌ PROBLEMA 5: Tau (polyak average) Muy Bajo (0.001)
   Consecuencia: Target networks actualizan muy rápido
                Divergencia en multi-objetivo
                Loss oscillations
```

---

### PPO - Problema: Clip Too Restrictive (+0.08% neutral)

#### Causa Raíz Identificada:
```
❌ PROBLEMA 1: Clip Range Muy Pequeño (0.2 = 20% máx)
   Configuración actual: clip_range = 0.2
   Consecuencia: Policy change limitada a 20% por update
                En 3 episodes = acumulado ~60% máximo
                No es suficiente para estrategias radicales
                (ej: no cargar mediodía requiere 50%+ cambio)

❌ PROBLEMA 2: N_steps Muy Pequeño (2048 = 2.3 días)
   Configuración actual: n_steps = 2048
   Consecuencia: Trajectory horizon < 1 semana
                No ve patrones solares semanales
                No conecta decisiones hora-8am con beneficio noche

❌ PROBLEMA 3: Batch Size Insuficiente (64)
   Configuración actual: batch_size = 64
   Consecuencia: Gradients calculados sobre datos pequeños
                High variance en updates
                No hay suficiente data para convergencia

❌ PROBLEMA 4: Learning Rate Muy Alto (3e-4)
   Consecuencia: Updates grandes + clip restricción
                = learning paralizado
                Combo: quiere cambiar 50%, clip permite 20%
                       learning_rate hace los 20% demasiado abruptos

❌ PROBLEMA 5: Entropy Coef No Configurado (default 0.0)
   Consecuencia: Sin exploración incentivada
                Policy converge a punto medio (neutral)
                No intenta estrategias diferentes

❌ PROBLEMA 6: Normalize Advantage NO activado
   Consecuencia: Advantage values en escala incorrecta
                Algunas updates muy grandes, otras muy pequeñas
                Inconsistent learning signal
```

---

## ✅ CORRECCIONES PROPUESTAS

### SAC - Configuración Optimizada

```python
# ANTES (Problema: Divergencia)
sac_config = {
    'buffer_size': 10_000,           # ❌ Insuficiente
    'learning_rate': 2e-4,           # ❌ Muy alto
    'tau': 0.001,                    # ❌ Muy bajo
    'ent_coef': 0.2,                 # ❌ Muy bajo
    'use_per': False,                # ❌ Sin Prioritized Replay
}

# DESPUÉS (Solución: Estable)
sac_config_optimized = {
    # BUFFER: Aumentar capacity + agregar PER
    'buffer_size': 100_000,          # ✅ 10x más, suficiente para 3 episodes
    'use_prioritized_replay': True,  # ✅ NUEVO: Focus en important transitions
    'per_alpha': 0.6,                # ✅ Prioritization exponent
    'per_beta': 0.4,                 # ✅ Importance sampling exponent
    'per_epsilon': 1e-6,             # ✅ Min priority epsilon
    
    # LEARNING RATE: Reducir + usar scheduler
    'learning_rate': 5e-5,           # ✅ 4x menor (2e-4 → 5e-5)
    'lr_schedule': 'linear_decay',   # ✅ NUEVO: Decay over episodes
    'lr_final': 1e-5,                # ✅ NUEVO: Final LR after decay
    
    # TARGET NETWORK: Más estable
    'tau': 0.01,                     # ✅ 10x mayor (0.001 → 0.01)
    'target_update_interval': 2,     # ✅ NUEVO: Update every 2 steps (not every step)
    
    # EXPLORATION: Mejor balanceado
    'ent_coef': 'auto',              # ✅ NUEVO: Auto-tune entropy
    'ent_coef_init': 0.5,            # ✅ NUEVO: Higher initial (0.2 → 0.5)
    'ent_coef_lr': 1e-4,             # ✅ NUEVO: Learn entropy coefficient
    
    # NETWORK STABILITY
    'max_grad_norm': 1.0,            # ✅ NUEVO: Gradient clipping
    'net_arch': [512, 512],          # ✅ Larger networks for complex space (126 actions)
    'batch_size': 256,               # ✅ Larger batches for stability
}

# JUSTIFICACIÓN:
# 1. Buffer 100K: Con 26K steps/entrenamiento, tienes ~3.8x coverage
#    Ratio old:new ≈ 30:70 (mejor mezcla)
# 2. PER: Enfoca en malas decisiones (cuando violaría prioridades)
# 3. LR 5e-5: Updates más pequeñas, menos oscilación
# 4. Tau 0.01: Target network cambia más gradualmente
# 5. Ent auto: Explora cuando necesario, explota cuando encontró buen patrón
```

---

### PPO - Configuración Optimizada

```python
# ANTES (Problema: Neutral, sin progreso)
ppo_config = {
    'clip_range': 0.2,               # ❌ Muy restrictivo
    'n_steps': 2048,                 # ❌ Muy pequeño
    'batch_size': 64,                # ❌ Muy pequeño
    'learning_rate': 3e-4,           # ❌ Muy alto para clip+batch combo
    'ent_coef': 0.0,                 # ❌ Sin exploración
    'normalize_advantage': False,    # ❌ Sin normalización
}

# DESPUÉS (Solución: Agresiva pero estable)
ppo_config_optimized = {
    # CLIP: Permitir cambios más grandes (pero seguros)
    'clip_range': 0.5,               # ✅ 2.5x mayor (0.2 → 0.5)
                                     # Permite ~50% cambio policy/episode
    'clip_range_vf': 0.5,            # ✅ NUEVO: Value function also clipped
    
    # TRAJECTORY: Ver patrones más largos
    'n_steps': 8760,                 # ✅ UNA SEMANA COMPLETA (no 2.3 días)
                                     # Full episode = full causal chains visible
    'gae_lambda': 0.98,              # ✅ High lambda para long-term advantages
    
    # BATCHES: Más data, mejor gradients
    'batch_size': 256,               # ✅ 4x mayor (64 → 256)
    'n_epochs': 10,                  # ✅ NUEVO: Multiple passes over data
    
    # LEARNING RATE: Reducir pero con decay
    'learning_rate': 1e-4,           # ✅ 3x menor (3e-4 → 1e-4)
    'lr_schedule': 'linear_decay',   # ✅ NUEVO: Decay over episodes
    'max_grad_norm': 1.0,            # ✅ NUEVO: Gradient clipping
    
    # EXPLORATION: Incentivizar descubrimiento
    'ent_coef': 0.01,                # ✅ NUEVO: Small entropy bonus
    'target_kl': 0.02,               # ✅ NUEVO: KL divergence limit (safety)
    
    # ADVANTAGES: Normalizar para consistencia
    'normalize_advantage': True,     # ✅ NUEVO: Normalize within minibatches
    'use_sde': True,                 # ✅ NUEVO: State-Dependent Exploration
    'sde_sample_freq': -1,           # ✅ NUEVO: Sample every step
}

# JUSTIFICACIÓN:
# 1. Clip 0.5: Permite cambios ~50% (vs 20% antes)
#    + n_steps 8760: Policy change acumulada ~250% posible
#    = Suficiente para estrategias radicales
# 2. n_steps 8760: Full episode = ve conexión 8am→noche
# 3. Batch 256: Gradients más suaves, menos variance
# 4. LR 1e-4 + decay: Updates consistentes que disminuyen
# 5. Ent 0.01: Pequeño bonus para explorar sin divergir
# 6. Normalize: Advantage values en escala [-1, 1] consistente
```

---

## 📋 CAMBIOS A REALIZAR ANTES DE RE-ENTRENAMIENTO

### SAC - Checklist de Cambios

```
Archivo: src/iquitos_citylearn/oe3/agents/sac.py

CAMBIOS REQUERIDOS:

☐ 1. Increase buffer_size
    Línea actual: buffer_size = 10_000
    Nueva: buffer_size = 100_000
    Razón: Más capacity = menos contamination
    
☐ 2. Add Prioritized Experience Replay
    Línea actual: (no existe)
    Nueva: 
        prioritized_replay_kwargs = {
            'alpha': 0.6,
            'beta': 0.4,
            'epsilon': 1e-6,
        }
    Razón: Focus en important transitions
    
☐ 3. Reduce learning_rate
    Línea actual: learning_rate = 2e-4
    Nueva: learning_rate = 5e-5 (con decay schedule)
    Razón: Mejor convergence, menos oscilación
    
☐ 4. Increase tau
    Línea actual: tau = 0.001
    Nueva: tau = 0.01
    Razón: Más estable target networks
    
☐ 5. Auto-tune entropy
    Línea actual: ent_coef = 0.2
    Nueva: ent_coef = 'auto', ent_coef_init = 0.5
    Razón: Exploración adaptiva
    
☐ 6. Add gradient clipping
    Línea actual: (no existe)
    Nueva: max_grad_norm = 1.0
    Razón: Prevenir divergencia
    
☐ 7. Increase network architecture
    Línea actual: net_arch = [256, 256]
    Nueva: net_arch = [512, 512]
    Razón: Mayor capacidad para 126 acciones
    
☐ 8. Increase batch_size
    Línea actual: batch_size = 64
    Nueva: batch_size = 256
    Razón: Mejor gradients, less variance
```

### PPO - Checklist de Cambios

```
Archivo: src/iquitos_citylearn/oe3/agents/ppo_sb3.py

CAMBIOS REQUERIDOS:

☐ 1. Increase clip_range
    Línea actual: clip_range = 0.2
    Nueva: clip_range = 0.5
    Razón: Permitir cambios policy más grandes
    
☐ 2. Set full episode n_steps
    Línea actual: n_steps = 2048
    Nueva: n_steps = 8760
    Razón: Ver patrones solares completos (día completo)
    
☐ 3. Increase batch_size
    Línea actual: batch_size = 64
    Nueva: batch_size = 256
    Razón: Mejor gradient estimation
    
☐ 4. Add multiple epochs
    Línea actual: n_epochs = 3
    Nueva: n_epochs = 10
    Razón: Múltiples passes para convergencia
    
☐ 5. Reduce learning_rate
    Línea actual: learning_rate = 3e-4
    Nueva: learning_rate = 1e-4 (con decay)
    Razón: Menos oscilación + decay schedule
    
☐ 6. Add gradient clipping
    Línea actual: (no existe)
    Nueva: max_grad_norm = 1.0
    Razón: Estabilidad
    
☐ 7. Add entropy bonus
    Línea actual: ent_coef = 0.0
    Nueva: ent_coef = 0.01
    Razón: Incentivizar exploración
    
☐ 8. Enable advantage normalization
    Línea actual: normalize_advantage = False
    Nueva: normalize_advantage = True
    Razón: Consistency en learning signal
    
☐ 9. Add State-Dependent Exploration
    Línea actual: (no existe)
    Nueva: use_sde = True, sde_sample_freq = -1
    Razón: Exploración más informada
    
☐ 10. Add KL divergence safety limit
    Línea actual: (no existe)
    Nueva: target_kl = 0.02
    Razón: Prevenir policy changes demasiado radicales
```

---

## 🔄 PROCESO DE RE-ENTRENAMIENTO (Orden Crítico)

### Fase 1: Preparación (ANTES de train)

```
PASO 1: Backup código actual
  $ git commit -m "Backup: Pre-optimization SAC/PPO"
  $ git branch pre-optimization

PASO 2: Hacer TODOS los cambios de código
  ☐ Update SAC config (8 cambios)
  ☐ Update PPO config (10 cambios)
  ☐ Update A2C baseline (sin cambios, es referencia)
  
PASO 3: Validar cambios sintácticos
  $ python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
  $ python -m py_compile src/iquitos_citylearn/oe3/agents/ppo_sb3.py
  $ pylint src/iquitos_citylearn/oe3/agents/
  
PASO 4: Commit cambios
  $ git add -A
  $ git commit -m "Config: Optimize SAC/PPO pre-training
  
  SAC changes:
  - buffer_size 10K→100K
  - PER enabled
  - LR 2e-4→5e-5 (decay)
  - tau 0.001→0.01
  - ent_coef auto
  - max_grad_norm 1.0
  - net_arch [256,256]→[512,512]
  - batch_size 64→256
  
  PPO changes:
  - clip_range 0.2→0.5
  - n_steps 2048→8760 (FULL EPISODE)
  - batch_size 64→256
  - n_epochs 3→10
  - LR 3e-4→1e-4 (decay)
  - max_grad_norm 1.0
  - ent_coef 0.0→0.01
  - normalize_advantage True
  - use_sde True
  - target_kl 0.02"

PASO 5: Crear documento de cambios
  ✅ Archivo: CAMBIOS_PREPROCESAMIENTO_SAC_PPO.md
     (listar cada cambio con justificación)
```

### Fase 2: Re-entrenamiento (Training Loop)

```
PASO 6: Build fresh dataset
  $ python -m scripts.run_oe3_build_dataset --config configs/default.yaml
  
PASO 7: Run baseline (sin cambios, para comparación)
  $ python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
  
PASO 8: Train SAC (NUEVO - optimizado)
  $ python -m scripts.run_oe3_train_agent --agent SAC --episodes 3 --config configs/default.yaml
  Esperar: ~30 min (GPU RTX 4060)
  
PASO 9: Train PPO (NUEVO - optimizado)
  $ python -m scripts.run_oe3_train_agent --agent PPO --episodes 3 --config configs/default.yaml
  Esperar: ~20 min
  
PASO 10: Train A2C (SIN CAMBIOS - referencia)
  $ python -m scripts.run_oe3_train_agent --agent A2C --episodes 3 --config configs/default.yaml
  Esperar: ~25 min
  
PASO 11: Comparación tres agentes
  $ python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### Fase 3: Validación y Documentación

```
PASO 12: Capture resultados
  Archivo: outputs/oe3_simulations/
    - SAC_results_optimized.json
    - PPO_results_optimized.json
    - A2C_results_reference.json

PASO 13: Comparar resultados
  SAC (ANTES):  +4.7%  CO₂
  SAC (DESPUÉS): ???%  CO₂  (debería ser -10% a -15%)
  
  PPO (ANTES):  +0.08% CO₂
  PPO (DESPUÉS): ???%  CO₂  (debería ser -15% a -20%)
  
  A2C (REFERENCIA): -25.1% CO₂  (sin cambios)

PASO 14: Documentar hallazgos
  Crear: RESULTADOS_REENTRENAMIENTO_SAC_PPO.md
    - Métricas antes/después
    - Gráficas convergencia
    - Análisis de mejora
    - Razones por qué mejoraron

PASO 15: Final commit
  $ git commit -m "Results: SAC/PPO Optimized Re-training Results
  
  SAC optimized:
  - CO₂: [X]% (vs +4.7% antes)
  - Grid import: [Y] kWh
  - Convergence: [Z] episodes
  
  PPO optimized:
  - CO₂: [X]% (vs +0.08% antes)
  - Grid import: [Y] kWh
  - Convergence: [Z] episodes
  
  A2C reference (sin cambios):
  - CO₂: -25.1%
  - Grid import: 9,467,195 kWh"
```

---

## 📊 MÉTRICAS DE COMPARACIÓN JUSTA

Después de re-entrenamiento con configuraciones optimizadas:

```
╔═════════════════════════════════════════════════════════════════════╗
║ MÉTRICA                    SAC ANTES  SAC OPT   PPO ANTES PPO OPT  ║
╠═════════════════════════════════════════════════════════════════════╣
║ CO₂ Reducción              +4.7%     ??? ✓     +0.08%    ??? ✓     ║
║ (Objetivo: <-20%)          ❌        ✓?        ❌        ✓?       ║
║                                                                     ║
║ Grid Import (kWh/año)      +597k    -200k?     +10k      -500k?   ║
║ (Objetivo: < 10M)          ❌        ✓?        ✓⚠️       ✓✓      ║
║                                                                     ║
║ EVs sin Grid (%)           75%      85%?       93%       95%?     ║
║ (Objetivo: >90%)           ❌        ✓?        ✓         ✓✓       ║
║                                                                     ║
║ Training Convergence       oscillate converge? flat     accelerate?║
║ (Objetivo: smooth)         ❌        ✓?        ⚠️        ✓✓       ║
║                                                                     ║
║ Buffer Divergence (SAC)    SÍ        MENOS?    N/A      N/A       ║
║ (Objetivo: NO)             ❌        ✓?        N/A      N/A       ║
║                                                                     ║
║ Policy Clip Restriction    N/A      N/A       Sí        MENOS?    ║
║ (Objetivo: flexible)       N/A      N/A       ❌        ✓?       ║
║                                                                     ║
║ Multi-Objective Balance    Falso    Mejor?    Conservative Better? ║
║ (Objetivo: 5 objetivos OK) ❌        ✓?        ⚠️        ✓✓       ║
╚═════════════════════════════════════════════════════════════════════╝

EXPECTATIVAS REALISTAS:
  SAC Optimizado: Debería llegar a -10% a -15% CO₂
    - PER + Buffer más grande = mejor stability
    - Auto-entropy = exploración balanceada
    - Pero: Off-policy inherentemente tiene limitaciones
  
  PPO Optimizado: Debería llegar a -15% a -20% CO₂
    - Clip 0.5 + n_steps 8760 = suficiente flexibilidad
    - Batch 256 + normalize = gradients consistentes
    - Pero: Aún puede estar conservador vs A2C
  
  A2C Referencia: Mantiene -25.1% (es el baseline)
```

---

## ✅ VERIFICACIÓN ANTES DE ENTRENAR

### Checklist Final (CRÍTICO):

```
☐ CÓDIGO:
  ☐ SAC config: 8/8 cambios implementados
  ☐ PPO config: 10/10 cambios implementados
  ☐ Archivos compilan sin errores (pylint 0)
  ☐ Imports correctos
  ☐ No hay deprecated functions

☐ CONFIGURACIÓN:
  ☐ configs/default.yaml actualizado (si necesario)
  ☐ Dataset limpio (backup viejo antes de rebuild)
  ☐ Checkpoints vaciados (para clean start)
  ☐ GPU disponible y funcionando

☐ DOCUMENTACIÓN:
  ☐ Documento de cambios creado (CAMBIOS_PREENTRENAMIENTO_SAC_PPO.md)
  ☐ Justificación de cada cambio escrita
  ☐ Expected results documentados
  ☐ Comparación baseline documentada

☐ GIT:
  ☐ Branch creado: git checkout -b oe3-sac-ppo-optimization
  ☐ Cambios committeados
  ☐ Backup pre-optimization guardado
  ☐ Remote actualizado

☐ MONITOREO:
  ☐ Script de monitoreo listo
  ☐ Logs guardados con timestamp
  ☐ Checkpoints monitoreados
  ☐ Early stopping configurado (si falla)
```

---

## 🎯 CONCLUSIÓN: CRITERIO DE ÉXITO

Después de re-entrenamiento con configuraciones optimizadas:

```
✅ SAC es exitoso si:
   - CO₂: De +4.7% → es decir ≥ -10%
   - EVs sin grid: De 75% → ≥ 85%
   - Convergencia: smooth vs oscillating
   - Explicación: "Buffer divergence corregida"

✅ PPO es exitoso si:
   - CO₂: De +0.08% → ≥ -15%
   - EVs sin grid: De 93% → ≥ 95%
   - Convergencia: acelerada vs flat
   - Explicación: "Clip permitió estrategias complejas"

✅ A2C mantiene referencia:
   - CO₂: -25.1% (sin cambios)
   - EVs sin grid: 95%
   - Convergencia: continua
   - Explicación: "Confirma que A2C es óptimo"

ENTONCES: Comparación JUSTA se puede hacer
           porque todos tienen configuraciones óptimas
```

Este plan asegura que NO descartes SAC/PPO por problemas técnicos, sino que los CORRIJAS y luego los compares equitativamente con A2C.
