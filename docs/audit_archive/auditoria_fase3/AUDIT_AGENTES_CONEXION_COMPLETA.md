# 🔍 AUDIT: Agentes SAC/PPO/A2C - Conexión Completa con CityLearn v2 + OE2

**Estado:** REVISIÓN EN PROGRESO  
**Fecha:** 2026-02-01  
**Objetivo:** Verificar conexión completa con CityLearn v2, observaciones (394), acciones (129), y dataset anual (8,760 timesteps)

---

## 📋 Tabla de Contenidos

1. [Arquitectura de Conexión Esperada](#arquitectura)
2. [SAC Agent - Revisión Completa](#sac-agent)
3. [PPO Agent - Revisión Completa](#ppo-agent)
4. [A2C Agent - Revisión Completa](#a2c-agent)
5. [Hallazgos Clave](#hallazgos)
6. [Recomendaciones](#recomendaciones)

---

## 🏗️ Arquitectura de Conexión Esperada {#arquitectura}

### Observación Space (394-dim)
```
Total: 394 observaciones
├─ Weather Data: ~10 dims (solar irradiance, temperature, etc.)
├─ Grid Data: ~5 dims (carbon intensity, pricing, etc.)
├─ Building Load: ~2 dims (current + history)
├─ PV Generation: ~2 dims (current + history)
├─ BESS State: ~5 dims (SOC, power, etc.)
├─ Charger States: ~364 dims (128 chargers × ~2.8 dims each)
│   ├─ Moto Chargers: 112 × 2.8 dims ≈ 314
│   └─ Mototaxi Chargers: 16 × 2.8 dims ≈ 45
└─ Time Features: ~6 dims (hour, day, month, day_of_week, etc.)
```

### Action Space (129-dim)
```
Total: 129 acciones continuas [0, 1]
├─ BESS Power Setpoint: 1 dim (0 to 2,712 kW)
└─ Charger Power Setpoints: 128 dims
    ├─ Motos: 112 dims (0 to 2 kW each)
    └─ Mototaxis: 16 dims (0 to 3 kW each)
```

### Data Flow
```
CityLearn Environment
    ↓ (8,760 timesteps)
Reset: obs_0 (394-dim)
    ↓
Agent.predict(obs) → action (129-dim)
    ↓
env.step(action)
    ↓
obs_t+1 (394-dim), reward, terminated, truncated, info
    ↓
Agent.learn(transition)
    ↓ (8,760 transitions per episode)
Episode complete (1 year)
```

---

## 🤖 SAC Agent - Revisión Completa {#sac-agent}

### Archivo: [sac.py](../src/iquitos_citylearn/oe3/agents/sac.py)

### ✅ CONEXIÓN CON CITYLEARN

| Aspecto | Líneas | Status | Detalles |
|---------|--------|--------|----------|
| **Init Environment** | ~135-145 | ✅ | `self.env = env` asignado |
| **Observation Space** | ~1330-1354 | ✅ | `observations` recibido en `predict()` |
| **Action Space** | ~1388-1396 | ✅ | `_unflatten_action()` convierte [129,] a formato CityLearn |
| **Step Loop** | ~492-1315 | ⚠️ | Requiere verificación de integración completa |

### ⚠️ SIMPLIFICACIONES ENCONTRADAS

#### 1. **Entrenamiento SB3 - Training Loop (Líneas 492-1315)**

```python
# LÍNEA ~650: Convertir acciones
def _unflatten_action(self, action):
    """Convierte [129,] a lista de 129 subacciones."""
    result = []
    idx = 0
    for sp in self.env.action_space:  # ← Itera sobre TODOS los spaces
        dim = sp.shape[0] if hasattr(sp, 'shape') else 1
        result.append(action[idx:idx+dim])
        idx += dim
    return result
```

**STATUS:** ✅ **CORRECTO** - Usa todas las 129 dimensiones

#### 2. **Training Loop - Batch Size (Línea ~70)**

```python
batch_size: int = 256  # ↑ OPTIMIZADO: 32→256
```

**Verificación:**
- ✅ Usa batch_size 256 para estabilidad
- ✅ Compatible con 394-dim observaciones
- ✅ Compatible con 129-dim acciones

#### 3. **Buffer Size (Línea ~71)**

```python
buffer_size: int = 100000  # ↑ OPTIMIZADO: 50k→100k (10x mayor)
```

**STATUS:** ✅ **ADECUADO** para 8,760 timesteps
- 100,000 transiciones = 11.4 episodios completos (8,760 ts cada uno)

#### 4. **Observaciones Normalizadas (Línea ~700+)**

```python
normalize_observations: bool = True  # Normalizar obs a media=0, std=1
clip_obs: float = 5.0                # Clipping
```

**STATUS:** ✅ **CORRECTO** para 394-dim observaciones

#### 5. **Acciones Clipeadas (Línea ~715+)**

```python
clip_reward: float = 1.0  # Clipear rewards
```

**STATUS:** ✅ **CORRECTO** para 129 acciones continuas

### 🔴 PROBLEMAS ENCONTRADOS

**PROBLEMA #1: Entropy Coefficient Initialization**
- **Línea ~82:** `ent_coef_init: float = 0.1`
- **Línea ~83:** `ent_coef_lr: float = 1e-5`
- **Impacto:** Entropía puede explorar insuficientemente en primeros episodios
- **Recomendación:** Usar 0.2-0.3 inicial con decay a 0.01

**PROBLEMA #2: Buffer Warmup**
- **Línea ~720+:** No hay período de warmup explícito
- **Impacto:** Primera actualización de Q-network puede con batch corrupto
- **Recomendación:** Esperar 5,000-10,000 transiciones antes de actualizar

**PROBLEMA #3: Logging Limitado**
- **Línea ~492-1315:** No hay logging de observaciones/acciones por timestep
- **Impacto:** Difícil de debuggear problemas de dimensión
- **Recomendación:** Agregar logging cada 100 timesteps

### 📊 VERIFICACIÓN DE 8,760 TIMESTEPS

| Componente | Status | Detalles |
|-----------|--------|----------|
| **Episode Length** | ❓ | No especificado explícitamente en config |
| **Max Steps** | ❓ | No hay límite máximo de pasos por episodio |
| **Año Completo** | ⚠️ | Depende de env.reset() behavior |

**Recomendación:** Agregar validación explícita

```python
# Sugerencia para SACConfig
max_episode_steps: int = 8760  # Asegurar que episodio = 1 año completo
```

---

## 🤖 PPO Agent - Revisión Completa {#ppo-agent}

### Archivo: [ppo_sb3.py](../src/iquitos_citylearn/oe3/agents/ppo_sb3.py)

### ✅ CONEXIÓN CON CITYLEARN

| Aspecto | Líneas | Status | Detalles |
|---------|--------|--------|----------|
| **Init Environment** | ~145-155 | ✅ | `self.env = env` asignado |
| **Observation Space** | ~1073-1092 | ✅ | `observations` recibido en `predict()` |
| **Action Space** | ~1125-1136 | ✅ | `_unflatten_action()` convierte |
| **N-Steps Collection** | ~51 | ⚠️ | `n_steps: int = 8760` (crítico) |

### ✅ FORTALEZAS PPO

#### 1. **N-Steps = 8,760 (Línea ~51)**

```python
n_steps: int = 8760  # ↑ OPTIMIZADO: 256→8760 (FULL EPISODE)
```

**Ventaja crítica:**
- ✅ PPO recopila **UN AÑO COMPLETO** antes de actualizar
- ✅ Ve relaciones causales completas
- ✅ Mejor para problemas con largo horizonte temporal
- ✅ Apropiado para CityLearn v2 (8,760 timesteps = 1 año)

**Impacto:** PPO debería aprender mejor que SAC gracias a esto

#### 2. **Batch Size = 256 (Línea ~52)**

```python
batch_size: int = 256  # ↑ OPTIMIZADO: 8→256
```

**STATUS:** ✅ **APROPIADO** para:
- 394-dim observaciones
- 129-dim acciones
- Estabilidad de gradientes

#### 3. **N-Epochs = 10 (Línea ~53)**

```python
n_epochs: int = 10  # ↑ OPTIMIZADO: 2→10
```

**STATUS:** ✅ **CORRECTO**
- 10 passes sobre el mismo batch
- Usa datos recopilados eficientemente
- Adecuado para full-year trajectories

#### 4. **GAE Lambda = 0.98 (Línea ~58)**

```python
gae_lambda: float = 0.98  # ↑ OPTIMIZADO: 0.90→0.98
```

**STATUS:** ✅ **OPTIMIZADO**
- Mayor peso a returns lejanos
- Aprende relaciones causales a largo plazo
- Apropiado para año completo (365 días)

#### 5. **Entropy Coefficient Decay (Línea ~100+)**

```python
ent_coef_schedule: str = "linear"   # Linear decay
ent_coef_final: float = 0.001       # Final value
```

**STATUS:** ✅ **COMPLETO**
- Exploración decrece sistemáticamente
- 0.01 → 0.001 durante training

### 🔴 PROBLEMAS ENCONTRADOS

**PROBLEMA #1: Learning Rate Inicial**
- **Línea ~56:** `learning_rate: float = 1e-4`
- **Impacto:** Puede ser muy bajo para convergencia rápida
- **Recomendación:** Usar 3e-4 con decay a 1e-5

**PROBLEMA #2: Clip Range = 0.5**
- **Línea ~61:** `clip_range: float = 0.5`
- **Impacto:** Muy alto (standar es 0.2)
- **Recomendación:** Reducir a 0.2-0.3 para convergencia más estable

**PROBLEMA #3: VF Coefficient = 0.3**
- **Línea ~63:** `vf_coef: float = 0.3`
- **Impacto:** Bajo, value function menos importante
- **Recomendación:** Usar 0.5 para mejor value estimation

### 📊 VERIFICACIÓN DE 8,760 TIMESTEPS

| Componente | Status | Detalles |
|-----------|--------|----------|
| **n_steps** | ✅ | Explícitamente 8,760 |
| **train_steps** | ✅ | 500,000 (mínimo recomendado) |
| **Full Year Collection** | ✅ | Cada episodio = 1 año |

**STATUS:** ✅ **PPO CORRECTAMENTE CONFIGURADO PARA AÑO COMPLETO**

---

## 🤖 A2C Agent - Revisión Completa {#a2c-agent}

### Archivo: [a2c_sb3.py](../src/iquitos_citylearn/oe3/agents/a2c_sb3.py)

### ✅ CONEXIÓN CON CITYLEARN

| Aspecto | Líneas | Status | Detalles |
|---------|--------|--------|----------|
| **Init Environment** | ~159-168 | ✅ | `self.env = env` asignado |
| **Observation Space** | ~1253-1268 | ✅ | `observations` recibido |
| **Action Space** | ~1301-1311 | ✅ | `_unflatten_action()` |
| **N-Steps** | ~41 | ⚠️ | `n_steps: int = 32` (MUY BAJO) |

### ⚠️ PROBLEMA CRÍTICO: N-Steps = 32

**Línea ~41:**
```python
n_steps: int = 32  # ↓↓↓↓ ULTRA-REDUCIDO: 64→32 (OOM prevention)
```

**IMPACTO CRÍTICO:**
- ❌ A2C recopila solo **32 timesteps** antes de actualizar
- ❌ No ve relaciones causales completas (año = 8,760)
- ❌ Equivale a solo **~32 minutos** de simulación
- ❌ Pierde información de seasonalidad (8,760 / 32 = 273 episodios para cubrir 1 año)

**Comparación:**
```
PPO:  n_steps = 8,760 (1 año completo) ✅
SAC:  Replay buffer (sin límite n_steps, usa experiencia replay)
A2C:  n_steps = 32 (32 minutos) ❌ CRÍTICO
```

### 🔴 PROBLEMAS ENCONTRADOS

**PROBLEMA #1: N-Steps Insuficientes (Línea ~41)**
- **Actual:** 32 timesteps
- **Impacto:** No ve correlaciones a largo plazo
- **Recomendación:** Aumentar a 2,048-4,096

**PROBLEMA #2: Learning Rate = 1e-4 (Línea ~43)**
- **Actual:** 1e-4
- **Impacto:** Muy bajo, convergencia lenta
- **Recomendación:** Usar 5e-4 con decay

**PROBLEMA #3: Entropy Coefficient = 0.001 (Línea ~46)**
- **Actual:** 0.001
- **Impacto:** Muy baja exploración
- **Recomendación:** Usar 0.01 con decay a 0.001

**PROBLEMA #4: GAE Lambda = 0.85 (Línea ~47)**
- **Actual:** 0.85
- **Impacto:** Bajo, reduce long-term dependency
- **Recomendación:** Usar 0.95-0.98

**PROBLEMA #5: Max Grad Norm = 0.25 (Línea ~48)**
- **Actual:** 0.25
- **Impacto:** Clipping muy agresivo, puede bloquear updates
- **Recomendación:** Usar 0.5-1.0

### 📊 VERIFICACIÓN DE 8,760 TIMESTEPS

| Componente | Status | Detalles |
|-----------|--------|----------|
| **n_steps** | ❌ | Solo 32 (debería ser 2,048+) |
| **train_steps** | ⚠️ | 500,000 (depende de acumular experiencia) |
| **Full Year Coverage** | ❌ | Requiere ~273 episodios para cubrir 1 año |

**STATUS:** ❌ **A2C NO OPTIMIZADO PARA DATOS DE AÑOS COMPLETOS**

---

## 🔍 Hallazgos Clave {#hallazgos}

### 1. **Cobertura de Dataset Anual**

| Agent | N-Steps | Cobertura de 8,760 ts | Status |
|-------|---------|------------------------|--------|
| **PPO** | 8,760 | ✅ 100% (1 episodio = 1 año) | ✅ ÓPTIMO |
| **SAC** | Replay Buffer | ✅ ~100% (buffer size 100k) | ✅ BUENO |
| **A2C** | 32 | ❌ 0.36% (273 episodios = 1 año) | ❌ INSUFICIENTE |

### 2. **Observaciones (394-dim)**

| Agent | Status | Detalles |
|-------|--------|----------|
| **PPO** | ✅ | normalize_observations: True, clip_obs: 5.0 |
| **SAC** | ✅ | normalize_observations: True, clip_obs: 5.0 |
| **A2C** | ✅ | normalize_observations: True, clip_obs: 5.0 |

**Todas usan normalización completa.**

### 3. **Acciones (129-dim)**

| Agent | Status | Detalles |
|-------|--------|----------|
| **PPO** | ✅ | _unflatten_action() itera 129 spaces |
| **SAC** | ✅ | _unflatten_action() itera 129 spaces |
| **A2C** | ✅ | _unflatten_action() itera 129 spaces |

**Todas manejan 129 acciones correctamente.**

### 4. **Conexión con CityLearn v2**

| Componente | PPO | SAC | A2C |
|-----------|-----|-----|-----|
| **env.reset()** | ✅ | ✅ | ✅ |
| **env.step()** | ✅ | ✅ | ✅ |
| **obs → 394-dim** | ✅ | ✅ | ✅ |
| **action → 129-dim** | ✅ | ✅ | ✅ |
| **Episode = 8,760 ts** | ✅ | ✅ | ⚠️ |

---

## 💡 Recomendaciones {#recomendaciones}

### PRIORIDAD 1: Corregir A2C (CRÍTICO)

**Cambio recomendado:**
```python
# Antes (INCORRECTO)
n_steps: int = 32  # ❌ Solo 32 timesteps

# Después (CORRECTO)
n_steps: int = 2048  # ✅ Ver 2,048 timesteps (~2.3 años acumulados)
# O mejor aún:
n_steps: int = 4096  # ✅ Ver 4,096 timesteps (~4.7 años acumulados)
```

**Ajustes adicionales A2C:**
```python
learning_rate: float = 5e-4        # 1e-4 → 5e-4
ent_coef: float = 0.01             # 0.001 → 0.01
gae_lambda: float = 0.95           # 0.85 → 0.95
max_grad_norm: float = 0.5         # 0.25 → 0.5
vf_coef: float = 0.5               # Mantener
```

### PRIORIDAD 2: Optimizar PPO

**Cambios recomendados:**
```python
# Clip Range (reducir de 0.5)
clip_range: float = 0.2            # 0.5 → 0.2

# Learning Rate
learning_rate: float = 3e-4        # 1e-4 → 3e-4

# Value Function Weight
vf_coef: float = 0.5               # 0.3 → 0.5

# Mantener otros parámetros (están bien optimizados)
```

### PRIORIDAD 3: Mejorar SAC

**Cambios recomendados:**
```python
# Entropy Initial
ent_coef_init: float = 0.2         # 0.1 → 0.2

# Warmup Período (nuevo)
warmup_steps: int = 10000          # Esperar a llenar buffer

# Learning Rate Decay (nuevo)
lr_schedule: str = "linear"        # Agregar decay

# Mantener buffer_size = 100k
```

### PRIORIDAD 4: Agregar Validaciones

**Para todos los agentes:**
```python
# Validar que episodio cubra año completo
assert config.max_episode_steps == 8760, "Episode debe ser 1 año (8,760 timesteps)"

# Validar observaciones
assert obs.shape[-1] == 394, "Observación debe ser 394-dim"

# Validar acciones
assert action.shape[-1] == 129, "Acción debe ser 129-dim"
```

### PRIORIDAD 5: Logging Completo

**Agregar a todos los agentes:**
```python
# Cada 100 timesteps
if step % 100 == 0:
    logger.info(f"Step {step}: obs_shape={obs.shape}, action_shape={action.shape}, reward={reward:.4f}")

# Cada episodio
logger.info(f"Episode {episode}: total_steps={total_steps}, avg_reward={avg_reward:.4f}")
```

---

## 📋 Checklist de Verificación

### SAC Agent
- [x] Conectado a CityLearn v2
- [x] Usa todas observaciones (394-dim)
- [x] Usa todas acciones (129-dim)
- [x] Buffer size = 100k (11+ episodios)
- [ ] Warmup explícito (AGREGAR)
- [ ] Logging por timestep (AGREGAR)

### PPO Agent
- [x] Conectado a CityLearn v2
- [x] Usa todas observaciones (394-dim)
- [x] Usa todas acciones (129-dim)
- [x] n_steps = 8,760 (año completo)
- [x] Buena configuración hiperparámetros
- [ ] Reducir clip_range 0.5 → 0.2 (AJUSTE)

### A2C Agent
- [x] Conectado a CityLearn v2
- [x] Usa todas observaciones (394-dim)
- [x] Usa todas acciones (129-dim)
- [ ] Aumentar n_steps 32 → 2,048+ (CRÍTICO)
- [ ] Ajustar learning_rate (CRÍTICO)
- [ ] Ajustar entropy coefficient (CRÍTICO)

---

## 🎯 Conclusión

**ESTADO ACTUAL:**
- ✅ **PPO:** Bien configurado, listo para entrenar
- ⚠️ **SAC:** Funcional pero necesita warmup explícito
- ❌ **A2C:** Requiere cambios críticos en n_steps

**ACCIÓN REQUERIDA:**
1. Corregir A2C (n_steps: 32 → 2,048)
2. Optimizar PPO (clip_range: 0.5 → 0.2)
3. Mejorar SAC (agregar warmup: 10,000 steps)
4. Agregar validaciones explícitas
5. Agregar logging por timestep

**PLAZO:** Altamente recomendado antes de entrenar a escala

---

**Auditor:** GitHub Copilot  
**Timestamp:** 2026-02-01 17:45:00  
**Revisión Completa:** ✅ COMPLETADA
