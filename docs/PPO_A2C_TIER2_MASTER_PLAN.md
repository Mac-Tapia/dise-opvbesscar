# PPO & A2C TIER 2 OPTIMIZATION - PARALLEL IMPLEMENTATION

**Date**: 2026-01-18
**Objetivo**: Aplicar TIER 2 fixes (SAC) a PPO y A2C + regenerar docs +
reentrenar
**Status**: 🚀 EN PROGRESO

---

## 🎯 TIER 2 CHANGES FOR PPO & A2C

### Equivalentes SAC → PPO/A2C | SAC TIER 2 | PPO TIER 2 | A2C TIER 2 | | ----------- | ----------- | ----------- | | ent_coef: 0.01→0.02 | ent_coef: 0.01→0.02 | ent_coef: 0.01→0.02 | |learning_rate: 3e-4→2.5e-4|learning_rate: 3e-4→2.5e-4|learning_rate: 3e-4→2.5e-4| | batch_size: 512→256 | batch_size: 128→256 | n_steps: 512→1024 | |hidden: 256,256→512,512|hidden: 256,256→512,512|hidden: 256,256→512,512| | tau: 0.005→0.005 | clip_range: 0.2→0.2 | No equivalente | | | n_epochs: 10→15 (↑) | |
| | lr_schedule: const→linear | lr_schedule: const→linear | ### ACTUALIZAR CONFIGS

#### PPOConfig (`ppo_sb3.py`)

```python
@dataclass
class PPOConfig:
    # TIER 2 UPDATED
    learning_rate: float = 2.5e-4  # ↓ de 3e-4
    batch_size: int = 256          # ↑ de 128
    n_epochs: int = 15             # ↑ de 10 (más updates)
    ent_coef: float = 0.02         # ↑ de 0.01 (más exploración)
    clip_range: float = 0.2        # mantener
    hidden_sizes: tuple = (512, 512)  # ↑ de (256, 256)
    activation: str = "relu"       # cambiar de tanh → relu
    lr_schedule: str = "linear"    # cambiar de constant → linear

    # NEW: Normalización adaptativa
    normalize_advantage: bool = True  # mantener
    use_sde: bool = True           # NEW: Exploration via SDE
    sde_sample_freq: int = -1      # Sample every step
```text

#### A2CConfig (`a2c_sb3.py`)

```python
@dataclass
class A2CConfig:
    # TIER 2 UPDATED
    learning_rate: float = 2.5e-4  # ↓ de 3e-4
    n_steps: int = 1024            # ↑ de 512 (más steps/update)
    ent_coef: float = 0.02         # ↑ de 0.01
    hidden_sizes: tuple = (512, 512)  # ↑ de (256, 256)
    activation: str = "relu"       # cambiar de tanh
    lr_schedule: str = "linear"    # cambiar de constant

    # NEW: Normalización rewards
    normalize_rewards: bool = True  # mantener
    reward_scale: float = 0.01     # mantener
    clip_obs: float = 10.0         # mantener
```text

---

## 📄 DOCUMENTOS A ACTUALIZAR/REGENERAR

### 1. **COMPARATIVA_AGENTES_FINAL.md** (REGENERAR)

- Actualizar configs con TIER 2 values
- Comparar: A2C vs PPO vs SAC (post-TIER 2)
- Tabla: Hiperparámetros lado-a-lado
- Resultados esperados

### 2. **ARQUITECTURA_UN_EDIFICIO_DOS_PLAYAS.md** (ACTUALIZAR)

- Mencionar TIER 2 fixes aplicados
- Actualizar configs de agentes

### 3. **DOCKER_GUIDE.md** (ACTUALIZAR)

- Actualizar referencias a configs
- Agregar TIER 2 notes

### 4. **EJECUTAR_ENTRENAMIENTO_GPU.txt** (REGENERAR)

- Scripts actualizados con TIER 2
- A2C, PPO, SAC en paralelo

### 5. **CHECKPOINT_QUICK_REFERENCE.md** (ACTUALIZAR)

- Checkpoints post-TIER 2

### 6. **COMIENZA_AQUI.md** (REGENERAR)

- Overview con TIER 2 info

---

## 🔧 CAMBIOS EN CÓDIGO (3 ARCHIVOS)

### A. `ppo_sb3.py` - PPO TIER 2

**Cambios**:

1. PPOConfig: learning_rate, batch_size, n_epochs, ent_coef, hidden_sizes,
activation, lr_schedule, use_sde
2. Verificar que normalize_advantage = True
3. Verificar weights multiobjetivo (ya correctos)

### B. `a2c_sb3.py` - A2C TIER 2

**Cambios**:

1. A2CConfig: learning_rate, n_steps, ent_coef, hidden_sizes, activation,
lr_schedule
2. Verificar normalización rewards
3. Verificar weights multiobjetivo

### C. `rewards.py` - YA ACTUALIZADO (SAC)

- Usar mismo recompensa para PPO/A2C (adaptive stats)

---

## 📊 PLAN EJECUCIÓN

### FASE 1: CÓDIGO (1 hora)

```text
[ ] Actualizar PPOConfig (ppo_sb3.py)
[ ] Actualizar A2CConfig (a2c_sb3.py)
[ ] Verificar rewards.py (compartida)
[ ] Syntax check
[ ] Commit: "PPO & A2C TIER 2: Updated configs"
```text

### FASE 2: DOCUMENTOS (2 horas)

```text
[ ] Regenerar: COMPARATIVA_AGENTES_FINAL.md
[ ] Actualizar: ARQUITECTURA_UN_EDIFICIO_DOS_PLAYAS.md
[ ] Actualizar: DOCKER_GUIDE.md
[ ] Regenerar: EJECUTAR_ENTRENAMIENTO_GPU.txt
[ ] Actualizar: CHECKPOINT_QUICK_REFERENCE.md
[ ] Regenerar: COMIENZA_AQUI.md
[ ] Commit: "Docs: Updated with PPO & A2C TIER 2"
```text

### FASE 3: REENTRENAMIENTO (variable)

```text
[ ] A2C: 2 episodios
[ ] PPO: 2 episodios
[ ] SAC: 2 episodios
[ ] Monitor: GPU, reward, convergence
[ ] Commit: "Training: 2-episode test run all agents TIER 2"
```text

---

## 🚀 COMIENZA AQUÍ

**Próximo paso**: Implementar cambios código (FASE 1)