# EJECUTAR ENTRENAMIENTO - TIER 2 ACTUALIZADO

**Fecha**: 2026-01-18
**Modo**: Serial (A2C → PPO → SAC en series)
**Episodes c/agente**: 2 (test rápido)
**GPU**: CUDA

---

## 🚀 QUICK START - ENTRENAR TODO

### Opción 1: Script MASTER (TODO EN UNO)

<!-- markdownlint-disable MD013 -->
```powershell
# En: d:\diseñopvbesscar

# A2C - 2 episodios
python -m src.train_a2c_cuda --episodes=2 --verbose=1

# PPO - 2 episodios
python -m src.train_ppo_cuda --episodes=2 --verbose=1

# SAC - 2 episodios
python -m src.train_sac_cuda --episodes=2 --verbose=1
```text
<!-- markdownlint-enable MD013 -->

---

## 📋 CONFIG TIER 2 PARA CADA AGENTE

### A2C TIER 2 CONFIG

<!-- markdownlint-disable MD013 -->
```py...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

### PPO TIER 2 CONFIG

<!-- markdownlint-disable MD013 -->
```python
PPOConfig(
    train_steps=500000,
    n_steps=1024,
    batch_size=256,            # ↑ TIER 2: de 128
    n_epochs=15,               # ↑ TIER 2: de 10
    learning_rate=2.5e-4,      # ↓ TIER 2: de 3e-4
    lr_schedule="linear",      # TIER 2: de constant
    ent_coef=0.02,             # ↑ TIER 2: de 0.01
    hidden_sizes=(512, 512),   # ↑ TIER 2: de (256, 256)
    activation="relu",         # TIE...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

### SAC TIER 2 CONFIG

<!-- markdownlint-disable MD013 -->
```python
SACConfig(
    episodes=2,
    batch_size=256,            # ↓ TIER 2: de 512
    buffer_size=150000,        # ↑ TIER 2: de 100k
    learning_rate=2.5e-4,      # ↓ TIER 2: de 3e-4
    ent_coef=0.02,             # ↑ TIER 2: de 0.01
    target_entropy=-40,        # ↓ TIER 2: de -50
    hidden_sizes=(512, 512),   # ↑ TIER 2: de (256, 256)
    update_per_timestep=2,     # NEW TIER 2
    use_dropout=Tru...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

## 🔄 PASOS EJECUCIÓN

### 1. Verificar Setup GPU

<!-- markdownlint-disable MD013 -->
```powershell
# En terminal PowerShell
nvidia-smi

# Debería mostrar: NVIDIA GPU con CUDA disponible
```text
<!-- markdownlint-enable MD013 -->

### 2. Limpiar Checkpoints Anteriores (OPCIONAL)

<!-- markdownlint-disable MD013 -->
```powershell
# Backup viejo
mkdir backups_tier1
mv checkpoints_a2c backups_tier1/
mv checkpoints_ppo backups_tier1/
mv checkpoints_sac backups_tier1/
```text
<!-- markdownlint-enable...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

**Expected Output**:

<!-- markdownlint-disable MD013 -->
```text
Episode 1/2: Reward=..., Import=..., CO2=...
Episode 2/2: Reward=..., Import=..., CO2=...
✅ A2C training complete
```text
<!-- markdownlint-enable MD013 -->

**Tiempo**: ~15-20 minutos GPU

### 4. Entrenar PPO (2 episodios)

<!-- markdownlint-disable MD013 -->
```powershell
python -m src.train_ppo_cuda --episodes=2 --verbose=1
```text
<!-- markdownlint-enable MD013 -->

**Expected Output**:

<!-- ...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

**Tiempo**: ~15-20 minutos GPU

### 5. Entrenar SAC (2 episodios)

<!-- markdownlint-disable MD013 -->
```powershell
python -m src.train_sac_cuda --episodes=2 --verbose=1
```text
<!-- markdownlint-enable MD013 -->

**Expected Output**:

<!-- markdownlint-disable MD013 -->
```text
Episode 1/2: Reward=..., Convergence=...
Episode 2/2: Reward=..., Convergence=...
✅ SAC training complete
```text
<!-- markdownlint-enable MD013 -->

**Tiempo**: ~10-15 minutos GPU (SAC más rápido)

---

## 📊 MONITOREO DURANTE ENTRENAMI...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

<!-- markdownlint-disable MD013 -->
### Métricas a Esperar | Agente | Ep 1 Reward | Ep 2 Reward | Trend | | -------- | ------------- | ------------- | ------- | | **A2C** | -0.5 a 0.0 | -0.2 a 0.1 | ↑ Mejorando | | **PPO** | -0.3 a 0.1 | 0.0 a 0.3 | ↑ Mejorando | | **SAC** | 0.0 a 0.3 | 0.2 a 0.5 | ↑↑ Rápido | **SAC debería convergir más rápido** (reward mejor en menos episodios)

---

## 💾 CHECKPOINTS GENERADOS

Después de entrenamientos:

<!-- markdownlint-disable MD013 -->
```text
checkpoints_a2c/
  └─ episode_1/
  └─ episode_2/
  └─ FINAL/

checkpoints_ppo/
  └─ episode_1/
  └─ episode_2/
  └─ FINAL/

checkpoints_sac/
  └─ episode_1/
  └─ episode_2/
  └─ FINAL/
```text
<!-- markdownlint-enable MD013 -->

---

## 📈 ANÁLISIS POST-ENTRENAMIENTO

### Generar Reportes

<!-- markdownlint-disable MD013 -->
```powershell
# Comparar 3 agentes
python -c "
from src.analyze_agents imp...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

### Resultados Esperados

<!-- markdownlint-disable MD013 -->
```text
A2C TIER 2:
  - Avg Reward: 0.05-0.15
  - Import Peak: 260-280 kWh/h
  - Convergence: Medium

PPO TIER 2:
  - Avg Reward: 0.10-0.20
  - Import Peak: 240-260 kWh/h
  - Convergence: Slow but Stable

SAC TIER 2:
  - Avg Reward: 0.20-0.35 ⭐
  - Import Peak: <240 kWh/h ⭐
  - Convergence: Fast ⭐
```text
<!-- markdownlint-enable MD013 -->

---

## 🔧 TROUBLESHOOTING

### Si GPU Memory Error

<!-- markdown...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

### Si Reward diverge

<!-- markdownlint-disable MD013 -->
```powershell
# Bajar learning_rate
# 2.5e-4 → 2.0e-4
# Subir entropy (ya está en 0.02)
```text
<!-- markdownlint-enable MD013 -->

### Si Muy lento

<!-- markdownlint-disable MD013 -->
```powershell
# Verificar GPU está siendo usado:
nvidia-smi
# GPU-Util debe estar >80%

# Si no:
# Bajar episode length o sample rate
```text
<!-- markdownlint-enable MD013 -->

---

## ✅ CHECKLIST PRE-ENTRENAMIENTO

<!-- markdo...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

## 📋 COMANDOS RÁPIDO COPY-PASTE

<!-- markdownlint-disable MD013 -->
```powershell
# Setup
cd "d:\diseñopvbesscar"

# A2C
python -m src.train_a2c_cuda --episodes=2 --verbose=1

# PPO
python -m src.train_ppo_cuda --episodes=2 --verbose=1

# SAC
python -m src.train_sac_cuda --episodes=2 --verbose=1

# Commit after
git add -A
git commit -m "Training: 2-episode test run A2C, PPO, SAC TIER 2"
git push origin main
```text
<!-- markdownlint-enable MD013 -->

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Ejecutar 2 episodios c/agente
2. ✅ Recopilar métricas
3. ✅ Comparar A2C vs PPO vs SAC
4. ✅ Decidir: ¿producción con SAC? ¿continuación con PPO?
5. ✅ TIER 3: Model-based learning (si tiempo)

---

**Status**: ✅ READY TO TRAIN
**Estimated Duration**: 40-60 minutes (2ep × 3 agents)
**Expected Best**: SAC (convergencia + eficiencia)