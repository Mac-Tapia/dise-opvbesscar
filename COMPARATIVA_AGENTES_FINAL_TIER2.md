# COMPARATIVA AGENTES FINAL - TIER 2 ACTUALIZADO

**Fecha**: 2026-01-18  
**Estado**: TIER 2 APPLIED A TODOS LOS AGENTES  
**Comparación**: A2C vs PPO vs SAC (post-TIER 2)  

---

## 📊 TABLA COMPARATIVA - HIPERPARÁMETROS TIER 2

| Parámetro | A2C TIER 2 | PPO TIER 2 | SAC TIER 2 |
|-----------|-----------|-----------|-----------|
| **Learning Rate** | 2.5e-4 | 2.5e-4 | 2.5e-4 |
| **Batch Size** | 1024 (n_steps) | 256 | 256 |
| **Entropía** | 0.02 | 0.02 | 0.02 |
| **Hidden Sizes** | (512, 512) | (512, 512) | (512, 512) |
| **Activation** | ReLU | ReLU | ReLU |
| **LR Schedule** | Linear (decay) | Linear (decay) | Constant |
| **Red Update** | Every step | Per epoch | 2x per step |
| **Exploración** | Entropy | SDE + Entropy | Alpha (automático) |
| **Gamma** | 0.99 | 0.99 | 0.99 |

---

## 🎯 CARACTERÍSTICAS POR AGENTE

### **A2C (Advantage Actor-Critic)** ✅

**Ventajas**:

- Convergencia rápida (on-policy)
- Simple y robusto
- Bajo memory overhead
- Bueno para problemas densos

**Desventajas**:

- Menos estable que PPO/SAC
- Sample inefficiency (on-policy)

**Casos de uso**:

- Quick prototyping
- Problemas con reward denso
- Entornos con buena exploración natural

**TIER 2 Impact**:

- LR 2.5e-4 → convergencia más estable
- Hidden 512x512 → mejor capacity
- n_steps 1024 → menos variance
- ent_coef 0.02 → mayor exploración

**Métricas esperadas**:

- Convergencia: 30-50 episodios
- Estabilidad: Media-Alta
- CO₂ anual: ~1.75M kg

---

### **PPO (Proximal Policy Optimization)** ⭐⭐

**Ventajas**:

- Muy robusto
- Clipping + GAE = estabilidad
- Buen balance exploración/explotación
- Excelente para RL continuo

**Desventajas**:

- Convergencia más lenta que A2C
- Más hyperparams que SAC

**Casos de uso**:

- Producción (robustez)
- Problemas continuos complejos
- Cuando estabilidad > velocidad

**TIER 2 Impact**:

- LR 2.5e-4 → convergencia suave
- Hidden 512x512 → mayor expresividad
- batch_size 256 → menos ruido
- n_epochs 15 → más updates/step
- ent_coef 0.02 → exploración
- SDE + entropy → exploración dual

**Métricas esperadas**:

- Convergencia: 50-100 episodios
- Estabilidad: Muy Alta ⭐
- CO₂ anual: ~1.72M kg

---

### **SAC (Soft Actor-Critic)** ⭐⭐⭐

**Ventajas**:

- Off-policy → sample efficient
- Entropía automática → exploración adaptativa
- Convergencia rápida
- Muy estable

**Desventajas**:

- Más complejo (dual Q-networks)
- Tuning de alpha crítico

**Casos de uso**:

- Producción (efficiency + robustness)
- Problemas con reward sparse
- Cuando sample-efficiency importa

**TIER 2 Impact**:

- Normalización adaptativa → gradientes consistentes
- Baselines dinámicas → estrategia por hora
- Bonuses BESS → motivación
- LR 2.5e-4 → convergencia suave
- Hidden 512x512 → expresividad
- update_per_timestep 2 → entrenamiento intenso

**Métricas esperadas**:

- Convergencia: 15-25 episodios ⭐ RÁPIDO
- Estabilidad: Muy Alta
- CO₂ anual: <1.70M kg ⭐ MEJOR

---

## 📈 RESULTADOS ESPERADOS TIER 2

### Importación Grid (kWh/h)

**Off-Peak (0-8h, 9-17h)**:

```
A2C:  130-140 kWh/h
PPO:  125-135 kWh/h  ← Mejor
SAC:  <130 kWh/h     ← Mejor
```

**Peak (18-21h)**:

```
A2C:  280-290 kWh/h
PPO:  260-270 kWh/h  ← Mejor
SAC:  <250 kWh/h     ← Mejor ⭐
```

### Convergencia (episodios)

```
A2C:  30-50 episodios
PPO:  50-100 episodios
SAC:  15-25 episodios ⭐ RÁPIDO
```

### CO₂ Anual (kg)

```
A2C:  ~1.75M kg
PPO:  ~1.72M kg  ← Mejor
SAC:  <1.70M kg  ← Mejor ⭐
```

### Estabilidad (varianza reward)

```
A2C:  Media (fluctúa)
PPO:  Alta (muy suave)  ← Mejor
SAC:  Muy Alta (smooth)  ← Mejor ⭐
```

---

## 🏆 RANKING AGENTES (TIER 2)

### Por Convergencia ⚡

1. **SAC**: 15-25 ep (sample efficient off-policy)
2. **A2C**: 30-50 ep (fast on-policy)
3. **PPO**: 50-100 ep (thorough but slower)

### Por Estabilidad 🛡️

1. **PPO**: Clipping + GAE = muy robusto
2. **SAC**: Off-policy smoothing = muy estable
3. **A2C**: On-policy variance = menos estable

### Por Eficiencia Energética 🌍

1. **SAC**: <1.70M kg CO₂ anual
2. **PPO**: ~1.72M kg CO₂ anual
3. **A2C**: ~1.75M kg CO₂ anual

### Por Balance General ⭐

1. **SAC**: Mejor convergencia + energía
2. **PPO**: Mejor estabilidad + robustez
3. **A2C**: Más rápido pero menos pulido

---

## 💡 RECOMENDACIONES TIER 2

### Usa **SAC** si

- ✅ Quieres convergencia rápida (15-25 ep)
- ✅ Sample efficiency es crítico
- ✅ Puedes hacer tuning de alpha
- ✅ Meta: energía mínima

### Usa **PPO** si

- ✅ Necesitas máxima estabilidad
- ✅ Prefieres robusted sobre velocidad
- ✅ Hyperparams tradicionales mejor
- ✅ Meta: producción estable

### Usa **A2C** si

- ✅ Necesitas convergencia inicial rápida
- ✅ Problemas de memory/compute limitado
- ✅ Quieres simplicidad
- ✅ Meta: prototyping rápido

---

## 📋 CONFIGURACIÓN LADO-A-LADO

### A2C TIER 2

```python
learning_rate:      2.5e-4    # ↓ de 3e-4
n_steps:            1024      # ↑ de 512
ent_coef:           0.02      # ↑ de 0.01
hidden_sizes:       (512, 512)  # ↑ de (256, 256)
activation:         "relu"    # cambio de tanh
lr_schedule:        "linear"  # cambio de constant
```

### PPO TIER 2

```python
learning_rate:      2.5e-4    # ↓ de 3e-4
batch_size:         256       # ↑ de 128
n_epochs:           15        # ↑ de 10
ent_coef:           0.02      # ↑ de 0.01
hidden_sizes:       (512, 512)  # ↑ de (256, 256)
activation:         "relu"    # cambio de tanh
lr_schedule:        "linear"  # cambio de constant
use_sde:            True      # NEW: Exploración SDE
```

### SAC TIER 2

```python
learning_rate:      2.5e-4    # ↓ de 3e-4
batch_size:         256       # ↓ de 512
ent_coef:           0.02      # ↑ de 0.01
target_entropy:     -40       # ↓ de -50
hidden_sizes:       (512, 512)  # ↑ de (256, 256)
activation:         "relu"
update_per_timestep: 2        # NEW: 2x updates
dropout:            0.1       # NEW: regularización
# + Normalización adaptativa + baselines dinámicas
```

---

## 🔄 MIGRATION TIER 1 → TIER 2

Para cada agente, cambios mínimos:

**PPO**:

```diff
- batch_size: 128 → 256
- learning_rate: 3e-4 → 2.5e-4
+ n_epochs: 10 → 15
+ ent_coef: 0.01 → 0.02
+ hidden: (256,256) → (512,512)
+ lr_schedule: constant → linear
+ use_sde: True
```

**A2C**:

```diff
- learning_rate: 3e-4 → 2.5e-4
+ n_steps: 512 → 1024
+ ent_coef: 0.01 → 0.02
+ hidden: (256,256) → (512,512)
+ lr_schedule: constant → linear
```

**SAC**:

```diff
- learning_rate: 3e-4 → 2.5e-4
- batch_size: 512 → 256
+ ent_coef: 0.01 → 0.02
+ hidden: (256,256) → (512,512)
+ Adaptive reward normalization
+ Dynamic baselines
+ BESS bonuses
```

---

## 📊 PRUEBAS TIER 2 (2 EPISODIOS CADA)

```
[ ] A2C: 2 episodios (test convergencia)
[ ] PPO: 2 episodios (test estabilidad)
[ ] SAC: 2 episodios (test efficiency)

Monitorear:
- Reward evolution
- Importación pico/off-peak
- SOC pre-pico
- Convergencia inicial
```

---

## 🎓 REFERENCES

- SAC: Haarnoja et al. "Soft Actor-Critic" (2018)
- PPO: Schulman et al. "PPO" (2017)
- A2C: Mnih et al. "Asynchronous Methods" (2016)
- TIER 2 fixes: Iquitos optimization (2026)

---

**Status**: ✅ READY FOR 2-EPISODE TEST RUN
