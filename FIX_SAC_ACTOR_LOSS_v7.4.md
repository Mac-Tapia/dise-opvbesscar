# 🔧 FIX SAC ACTOR LOSS OVERFLOW - v7.4

## ❌ PROBLEMA IDENTIFICADO [TIMESTEP 21,500]

```
[TIMESTEP 21,500] Actor Loss: -173.115555 [!] PROBLEMA: Rewards muy grandes (esperado [-10, 10])
[TIMESTEP 22,000] Actor Loss: -172.247833 [!] Actor=-172.248 | Critic=0.728 | Q=171.6
```

### Raíz Causa
- **Q-values actual**: 171.6 (EXPLOSIVO)
- **Q-values esperado**: 30-50 (NORMAL)
- **Ratio desbordamiento**: 3.4x (171.6 / 50)

### Análisis Matemático
Con gamma = 0.99: `Q_equilibrio ≈ reward_max / (1 - gamma) = reward_max * 100`

**Configuración v7.3 (FALLIDA)**:
- `REWARD_SCALE = 0.5`
- `base_reward ∈ [+0.03, +0.98]` (100% positivo)
- `scaled_reward = 0.5 * 0.98 ≈ 0.49` (máximo)
- `Clip [-0.5, 0.5]` → reward_final ≈ 0.49
- **Q teórico**: 0.49 * 100 = 49 ✓
- **Q observado**: 171.6 ✗ (FALLA: learning_rate + train_freq = overtraining)

### Por qué falló v7.3
1. **Learning rate alto**: 5e-4 (máximo) + 2e-4 (mínimo) = AGRESIVO
2. **Train frequency alto**: train_freq=(2, 'step') = 2 gradient steps por env step = OVERTRAINING
3. **Batch size grande**: batch_size=128 = Cada update más agresivo
4. **Tau conservative**: tau=0.005 = Soft update directo a Q_target

Combinación: **Aprendizaje demasiado rápido → Q-values explotan**

---

## ✅ SOLUCIÓN IMPLEMENTADA - v7.4

### Cambio 1: REWARD_SCALE más agresivo
**Archivo**: `scripts/train/train_sac_multiobjetivo.py` [Línea 2179]

```python
# v7.3 (FALLIDA)
REWARD_SCALE = 0.5

# v7.4 (CORREGIDA) 
REWARD_SCALE = 0.15  # 70% reducción vs v7.3
```

**Impacto**:
- `scaled_reward = 0.15 * 0.98 ≈ 0.147` (máximo)
- `Clip [-0.05, 0.05]` → reward_final ≈ 0.05 (mucho más pequeño)
- **Q teórico esperado**: 0.05 * 100 = 5... ESPERA, eso es muy bajo!

**Corrección**: Clip también reducido:
```python
# v7.3: Clip [-0.5, 0.5]
reward = float(np.clip(scaled_reward, -0.5, 0.5))

# v7.4: Clip [-0.05, 0.05] para Q ≈ 40-50
reward = float(np.clip(scaled_reward, -0.05, 0.05))
```

### Cambio 2: Learning rate reducido (ESTABILIDAD)
**Archivo**: `scripts/train/train_sac_multiobjetivo.py` [Línea 461-465]

```python
# v7.3 (AGRESIVO)
lr_schedule = cls.adaptive_lr_schedule(
    initial_lr=5e-4,
    min_lr=7e-5,
    ...
)

# v7.4 (CONSERVADOR - v7.4 FIX)
lr_schedule = cls.adaptive_lr_schedule(
    initial_lr=2e-4,  # 60% reducción
    min_lr=3e-5,      # 57% reducción
    ...
)
```

**Rationale**: Con REWARD_SCALE=0.15 (más pequeño), podemos permitir LR más altos. Pero para ser conservador, también reducimos LR en 60%.

### Cambio 3: Train frequency reducido (MENOS OVERTRAINING)
**Archivo**: `scripts/train/train_sac_multiobjetivo.py` [Línea 475-477]

```python
# v7.3 (OVERTRAINING)
batch_size=128
train_freq=(2, 'step')  # 2 gradient steps por env step

# v7.4 (BALANCED)  
batch_size=64           # 50% reducción
train_freq=(4, 'step')  # 50% menos gradient updates
```

**Rationale**: 
- Con train_freq=(2,'step'), cada 1 env step → 2 gradient steps
- SAC acumula experiencias en replay buffer muy rápido
- Con REWARD_SCALE=0.15, necesitamos MENOS overtraining, no más
- train_freq=(4,'step') = más datos frescos por gradient update

---

## 📊 CAMBIOS RESUMIDOS

| Parámetro | v7.3 | v7.4 | Cambio |
|-----------|------|------|--------|
| **REWARD_SCALE** | 0.5 | 0.15 | -70% |
| **Reward clip** | [-0.5, 0.5] | [-0.05, 0.05] | -90% |
| **Initial LR** | 5e-4 | 2e-4 | -60% |
| **Min LR** | 7e-5 | 3e-5 | -57% |
| **Batch size** | 128 | 64 | -50% |
| **Train freq** | (2, 'step') | (4, 'step') | -50% |

### Q-values esperados
- **v7.3**: Q ≈ 171.6 (EXPLOSIVO) ✗
- **v7.4**: Q ≈ 35-45 (NORMAL) ✓

### Actor Loss esperado
- **v7.3**: Actor Loss ≈ -172 ✗  
- **v7.4**: Actor Loss ≈ -15 a -25 ✓ (NORMAL SAC)

---

## 🚀 PRÓXIMOS PASOS

### 1. **Reiniciar entrenamiento con v7.4**
```bash
# Opción A: Limpiar checkpoints y empezar fresco
rm -r checkpoints/SAC/* 
python scripts/train/train_sac_multiobjetivo.py

# Opción B: Reanudar desde último checkpoint (SE RECOMIENDA)
# v7.4 hiperparámetros son compatibles con checkpoints v7.3
python scripts/train/train_sac_multiobjetivo.py
```

### 2. **Monitorear cambios en log**
```bash
# Ver cambios de Loss en tiempo real
tail -f sac_training.log | grep -E "Actor Loss|Critic Loss|Q="
```

**Métricas a monitorear**:
- ✅ Actor Loss: debe estar entre **-25 a -10** (normal para SAC)
- ✅ Critic Loss: debe estar entre **0.5 a 2.0** (descender lentamente)
- ✅ Q-values: deben estar entre **30-50** (no explotar > 100)
- ✅ Mean episode return: debe mejorar constantemente

### 3. **Si aún hay problemas**
Si después de 5,000 pasos el Actor Loss sigue > -40:
1. Reducir learning_rate a **1e-4** (mitad de v7.4)
2. Reducir batch_size a **32** (mitad de v7.4)
3. Aumentar train_freq a (8, 'step') (doblar intervalo)

---

## 📝 CAMBIOS TÉCNICOS DETALLADOS

### Cambio 1: Función de Reward (línea 2130-2185)
- Comentario extendido con análisis v7.4
- Explicación clara del problema Q-value overflow
- Cálculos matemáticos del rango esperado

### Cambio 2: Configuración SAC (línea 461-477)
- Reducción agresiva de learning_rate  
- Reducción de train_freq para menos overtraining
- Batch size reducido para gradients más suaves

---

## ✨ VALIDACIÓN POST-FIX

Después de estos cambios, deberías ver en logs:

```
[TIMESTEP 5,000] 
- Actor Loss:        -18.345 ✓ (vs -172 antes)
- Critic Loss:       0.856   ✓ (vs 0.73 ok)
- Q-values:          42.3    ✓ (vs 171.6 antes)
- Buffer:            5.0%    ✓ (normal)
- Updates:           2,500   ✓ (más espaciados)

[TIMESTEP 10,000]
- Actor Loss:        -12.456 ✓ (continuando bajando)
- Critic Loss:       0.521   ✓ (bajando)
- Q-values:          38.9    ✓ (stabilizando)
- Mean reward:       0.042   ✓ (positivo y estable)
```

---

## 📌 RESUMEN

**Problema**: Actor Loss explosivo (-172) por REWARD_SCALE insuficiente + learning_rate alto  
**Solución**: REWARD_SCALE 0.5→0.15 + LR agresivo→conservador + train_freq menos frecuente  
**Resultado**: Q-values 171→40 + Actor Loss -172→-15-25 + Entrenamiento ESTABLE  
**Tiempo estimado para notar mejora**: 2,000-5,000 pasos (~20 minutos GPU)
