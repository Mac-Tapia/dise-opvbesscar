# EJECUTAR ENTRENAMIENTO - TIER 2 ACTUALIZADO

**Fecha**: 2026-01-18
**Modo**: Serial (A2C → PPO → SAC en series)
**Episodes c/agente**: 2 (test rápido)
**GPU**: CUDA

---

## 🚀 QUICK START - ENTRENAR TODO

### Opción 1: Script MASTER (TODO EN UNO)

```powershell
# En: d:\diseñopvbesscar

# A2C - 2 episodios
python -m src.train_a2c_cuda --episodes=2 --verbose=1

# PPO - 2 episodios
python -m src.train_ppo_cuda --episodes=2 --verbose=1

# SAC - 2 episodios
python -m src.train_sac_cuda --episodes=2 --verbose=1
```text

---

## 📋 CONFIG TIER 2 PARA CADA AGENTE

### A2C TIER 2 CONFIG

```python
A2CConfig(
    train_steps=500000,
    n_steps=1024,              # ↑ TIER 2: de 512
    learning_rate=2.5e-4,      # ↓ TIER 2: de 3e-4
    lr_schedule="linear",      # TIER 2: de constant
    ent_coef=0.02,             # ↑ TIER 2: de 0.01
    hidden_sizes=(512, 512),   # ↑ TIER 2: de (256, 256)
    activation="relu",         # TIER 2: de tanh

    # Multiobjetivo (igual)
    weight_co2=0.50,
    weight_cost=0.15,
    weight_solar=0.20,
    weight_ev_satisfaction=0.10,
    weight_grid_stability=0.05,
)
```text

### PPO TIER 2 CONFIG

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
    activation="relu",         # TIER 2: de tanh
    use_sde=True,              # NEW TIER 2
    sde_sample_freq=-1,        # Sample every step

    # Multiobjetivo (igual)
    weight_co2=0.50,
    weight_cost=0.15,
    weight_solar=0.20,
    weight_ev_satisfaction=0.10,
    weight_grid_stability=0.05,
)
```text

### SAC TIER 2 CONFIG

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
    use_dropout=True,          # NEW TIER 2
    dropout_rate=0.1,          # NEW TIER 2

    # Multiobjetivo + Adaptive normalization (rewards.py)
    weight_co2=0.50,
    weight_cost=0.05,          # ↓ TIER 2: de 0.15
    weight_solar=0.20,
    weight_ev_satisfaction=0.10,
    weight_grid_stability=0.15, # ↑ TIER 2: de 0.10
)
```text

---

## 🔄 PASOS EJECUCIÓN

### 1. Verificar Setup GPU

```powershell
# En terminal PowerShell
nvidia-smi

# Debería mostrar: NVIDIA GPU con CUDA disponible
```text

### 2. Limpiar Checkpoints Anteriores (OPCIONAL)

```powershell
# Backup viejo
mkdir backups_tier1
mv checkpoints_a2c backups_tier1/
mv checkpoints_ppo backups_tier1/
mv checkpoints_sac backups_tier1/
```text

### 3. Entrenar A2C (2 episodios)

```powershell
cd "d:\diseñopvbesscar"
python -m src.train_a2c_cuda --episodes=2 --verbose=1
```text

**Expected Output**:

```text
Episode 1/2: Reward=..., Import=..., CO2=...
Episode 2/2: Reward=..., Import=..., CO2=...
✅ A2C training complete
```text

**Tiempo**: ~15-20 minutos GPU

### 4. Entrenar PPO (2 episodios)

```powershell
python -m src.train_ppo_cuda --episodes=2 --verbose=1
```text

**Expected Output**:

```text
Episode 1/2: Reward=..., Stability=...
Episode 2/2: Reward=..., Stability=...
✅ PPO training complete
```text

**Tiempo**: ~15-20 minutos GPU

### 5. Entrenar SAC (2 episodios)

```powershell
python -m src.train_sac_cuda --episodes=2 --verbose=1
```text

**Expected Output**:

```text
Episode 1/2: Reward=..., Convergence=...
Episode 2/2: Reward=..., Convergence=...
✅ SAC training complete
```text

**Tiempo**: ~10-15 minutos GPU (SAC más rápido)

---

## 📊 MONITOREO DURANTE ENTRENAMIENTO

### En Terminal (Real-time)

```powershell
# Monitor GPU
while($true) { nvidia-smi; Start-Sleep 5 }

# Debería ver:
# - GPU-Util: 80-100%
# - Memory: Aumentando gradualmente
# - Temp: <80°C idealmente
```text

### Métricas a Esperar

| Agente | Ep 1 Reward | Ep 2 Reward | Trend |
| -------- | ------------- | ------------- | ------- |
| **A2C** | -0.5 a 0.0 | -0.2 a 0.1 | ↑ Mejorando |
| **PPO** | -0.3 a 0.1 | 0.0 a 0.3 | ↑ Mejorando |
| **SAC** | 0.0 a 0.3 | 0.2 a 0.5 | ↑↑ Rápido |

**SAC debería convergir más rápido** (reward mejor en menos episodios)

---

## 💾 CHECKPOINTS GENERADOS

Después de entrenamientos:

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

---

## 📈 ANÁLISIS POST-ENTRENAMIENTO

### Generar Reportes

```powershell
# Comparar 3 agentes
python -c "
from src.analyze_agents import compare_tier2_results
compare_tier2_results(
    checkpoints=['checkpoints_a2c/FINAL',
                 'checkpoints_ppo/FINAL',
                 'checkpoints_sac/FINAL'],
    episodes=2
)
"
```text

### Resultados Esperados

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

---

## 🔧 TROUBLESHOOTING

### Si GPU Memory Error

```powershell
# Bajar batch_size
# PPO: batch_size 256 → 128
# A2C: n_steps 1024 → 512
# SAC: batch_size 256 → 128
```text

### Si Reward diverge

```powershell
# Bajar learning_rate
# 2.5e-4 → 2.0e-4
# Subir entropy (ya está en 0.02)
```text

### Si Muy lento

```powershell
# Verificar GPU está siendo usado:
nvidia-smi
# GPU-Util debe estar >80%

# Si no:
# Bajar episode length o sample rate
```text

---

## ✅ CHECKLIST PRE-ENTRENAMIENTO

```text
[ ] GPU CUDA disponible (nvidia-smi)
[ ] Configs TIER 2 aplicados (ppo_sb3.py, a2c_sb3.py, sac.py)
[ ] Repos clean (git status limpio)
[ ] ~10GB GPU memory libre
[ ] ~2 horas disponibles (2ep × 3 agentes)
[ ] Checkpoints dir vacío o backuped
```text

---

## 📋 COMANDOS RÁPIDO COPY-PASTE

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