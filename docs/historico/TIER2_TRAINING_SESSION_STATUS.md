# TIER 2 TRAINING SESSION - RESUMEN EJECUTIVO

**Fecha**: 18 Enero 2026
**Estado**: 🟢 EN EJECUCIÓN (A2C iniciado)
**Objetivo**: 2 episodios cada agente en serie (A2C → PPO → SAC)

---

## ✅ COMPLETADO

### 1. Configuraciones TIER 2 Aplicadas

#### PPO (`ppo_sb3.py`)

- Learning Rate: 3e-4 → **2.5e-4**
- Batch Size: 128 → **256**
- N Epochs: 10 → **15**
- Entropy Coef: 0.01 → **0.02**
- Hidden Layers: (256,256) → **(512,512)**
- Activation: tanh → **relu**
- LR Schedule: constant → **linear**
- **NEW**: use_sde=**True**, sde_sample_freq=-1

#### A2C (`a2c_sb3.py`)

- Learning Rate: 3e-4 → **2.5e-4**
- N Steps: 512 → **1024**
- Entropy Coef: 0.01 → **0.02**
- Hidden Layers: (256,256) → **(512,512)**
- Activation: tanh → **relu**
- LR Schedule: constant → **linear**

#### SAC (`sac.py`) - Previo

- Learning Rate: 3e-4 → **2.5e-4**
- Batch Size: 512 → **256**
- Entropy Coef: 0.01 → **0.02**
- Hidden Layers: (256,256) → **(512,512)**
- Update Per Timestep: 1 → **2**
- Dropout: 0 → **0.1**

### 2. Documentación Actualizada (4 archivos)

- ✅ `PPO_A2C_TIER2_MASTER_PLAN.md` - Plan de implementación
- ✅ `COMPARATIVA_AGENTES_FINAL_TIER2.md` - Tabla comparativa detallada
- ✅ `EJECUTAR_ENTRENAMIENTO_TIER2.md` - Guía de ejecución y monitoreo
- ✅ `COMIENZA_AQUI_TIER2.md` - Punto de entrada actualizado

### 3. Scripts de Entrenamiento

- ✅ `train_tier2_serial_fixed.py` - Script corregido con parámetros válidos para `simulate()`

### 4. Git Commits

- ✅ Commit 1: "PPO & A2C TIER 2: Updated configs" (4 files, 180 insertions)
- ✅ Commit 2: "TIER 2 DOCS: Updated COMPARATIVA..." (4 files, 921 insertions)

---

## 🟢 EN EJECUCIÓN

### Entrenamiento Serial

**[1/3] A2C - 2 Episodios**

- Status: ▶️ INICIADO (19:25:49)
- Config: LR=2.5e-4, n_steps=1024, ent=0.02
- Expected Duration: 15-20 min (GPU)
- Expected CO2: <1.8M kg
- Expected Peak Import: <250 kWh/h

**[2/3] PPO - 2 Episodios**

- Status: ⏳ EN COLA
- Config: LR=2.5e-4, batch=256, n_epochs=15, use_sde=True
- Expected Duration: 20-25 min (GPU)
- Expected CO2: <1.9M kg
- Expected Peak Import: <280 kWh/h

**[3/3] SAC - 2 Episodios**

- Status: ⏳ EN COLA
- Config: LR=2.5e-4, batch=256, update_freq=2, dropout=0.1
- Expected Duration: 10-15 min (GPU)
- Expected CO2: <1.7M kg
- Expected Peak Import: <240 kWh/h

**Total Expected**: 45-60 minutos

---

## 🔧 CAMBIOS TÉCNICOS CLAVE

### Función simulate()

**Problema**: Script inicial usaba parámetro inválido `agent_config=...`
**Solución**: Updated script para usar parámetros específicos por agente

```python
# CORRECTO:
result_a2c = simulate(
    schema_path=schema_pv,
    agent_name="A2C",
    a2c_timesteps=2*8760,
    a2c_n_steps=1024,
    a2c_learning_rate=2.5e-4,
    a2c_entropy_coef=0.02,
    # ... más parámetros
)
```text

### Multiobjetivo Reward (Balanceado)

- CO2: 0.35 (↑ de 0.50)
- Costo: 0.25
- Solar: 0.20
- EV: 0.15
- Grid: 0.05

---

## 📊 MONITOREO EN VIVO

**Terminal**: `bcbad086-ec29-433c-b4c4-d25563704e8e`

```text
2026-01-18 19:25:49,385 - INFO - Loading configuration...
2026-01-18 19:25:54,891 - INFO - [MULTIOBJETIVO] Pesos activados
2026-01-18 19:25:54,893 - INFO - Creando modelo A2C en dispositivo: cuda
```text

---

## 📋 PRÓXIMOS PASOS

1. ✅ Permitir que A2C complete 2 episodios
2. ⏳ Permitir que PPO complete 2 episodios
3. ⏳ Permitir que SAC complete 2 episodios
4. ⏳ Commit de resultados: "Training: 2-ep test run TIER 2 (A2C/PPO/SAC)"
5. ⏳ Generar reporte comparativo final
6. ⏳ Análisis de performance relativo

---

## 🎯 METAS DE CONVERGENCIA

**Esperadas tras 2 episodios** (benchmarks indicativos):

| Métrica | A2C | PPO | SAC | Target |
| --------- | ----- | ----- | ----- | -------- |
| Avg Reward | 0.45-0.55 | 0.40-0.50 | 0.55-0.65 | SAC > PPO > A2C |
| CO2 (kg) | 1.75-1.85M | 1.85-2.0M | 1.65-1.80M | SAC < A2C < PPO |
| Peak Import (kWh/h) | 240-260 | 260-290 | 220-250 | SAC < A2C < PPO |
| Grid Stability | 0.70-0.80 | 0.75-0.85 | 0.80-0.90 | ↑ (TIER 2 benefit) |

---

## 📁 ARCHIVOS PRINCIPALES

```text
src/iquitos_citylearn/oe3/agents/
├── ppo_sb3.py          ✅ TIER 2
├── a2c_sb3.py          ✅ TIER 2
└── sac.py              ✅ TIER 2 (prev)

src/iquitos_citylearn/oe3/
├── simulate.py         (función frame)
├── rewards.py          ✅ Multiobjetivo
└── dataset_builder.py

outputs/oe3/training/tier2_2ep_serial/
├── a2c/                ← EN EJECUCIÓN
├── ppo/                ← EN COLA
└── sac/                ← EN COLA
```text

---

**Status**: 🟢 ENTRENAMIENTO EN PROGRESO
**Última actualización**: 2026-01-18 19:25:54
**Monitoreo**: Verificar terminal bcbad086-ec29-433c-b4c4-d25563704e8e cada 5 min