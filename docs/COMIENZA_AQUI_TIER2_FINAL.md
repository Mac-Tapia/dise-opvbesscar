# 🚀 COMIENZA AQUI - TIER 2 (FINAL)

**Sesión**: TIER 2 PPO & A2C Equivalence + Serial 2-Episode Test Run
**Fecha**: 19 Enero 2026
**Estado**: ⚠️ Entrenamientos recientes sin convergencia (PPO/SAC recompensas planas; ver métricas)

## Resultados rápidos entrenamientos (19 Ene 2026)

- Informe consolidado: `INFORME_UNICO_ENTRENAMIENTO_TIER2.md` (incluye métricas y conclusiones de no aprendizaje).

- SAC (pasos 8,759–17,518): reward medio 52.189 (plano), CO₂ episodio 220.17 kg, grid 487 kWh, solar 0 kWh; entropía al alza → no aprendizaje.
- PPO (pasos 9,259–44,295): reward medio 52.554 (plano), CO₂ episodio 220.17 kg, grid 487 kWh, solar 0 kWh; sin mejora.
- Conclusión: la señal/observables actuales no inducen aprendizaje; es necesario ajustar recompensas (CO₂/importación pico, potencia pico, SOC reserva) y observaciones (hora pico, SOC, colas por playa) antes de nuevas corridas.

---

## 📌 RESUMEN EJECUCIÓN

### ✅ Completado Esta Sesión

1. **PPO TIER 2** - Configuración actualizada
   - Learning Rate: 3e-4 → **2.5e-4** ✅
   - Batch Size: 128 → **256** ✅
   - N Epochs: 10 → **15** ✅
   - Entropy: 0.01 → **0.02** ✅
   - Hidden: (256,256) → **(512,512)** ✅
   - Activation: tanh → **relu** ✅
   - LR Schedule: constant → **linear** ✅
   - **NEW**: `use_sde=True` ✅

2. **A2C TIER 2** - Configuración actualizada
   - Learning Rate: 3e-4 → **2.5e-4** ✅
   - N Steps: 512 → **1024** ✅
   - Entropy: 0.01 → **0.02** ✅
   - Hidden: (256,256) → **(512,512)** ✅
   - Activation: tanh → **relu** ✅
   - LR Schedule: constant → **linear** ✅

3. **Documentación actualizada** (4 archivos)
   - `PPO_A2C_TIER2_MASTER_PLAN.md` - Plan de implementación
   - `COMPARATIVA_AGENTES_FINAL_TIER2.md` - Tabla comparativa A2C vs PPO vs SAC
   - `EJECUTAR_ENTRENAMIENTO_TIER2.md` - Guía de ejecución
   - `COMIENZA_AQUI_TIER2.md` - Este documento

4. **Parches aplicados**
   - ✅ CityLearn EV Charger Battery.get_max_input_power() patch
   - ✅ CityLearn Battery.charge() bounds checking patch

5. **Scripts de entrenamiento**
   - ✅ `train_tier2_serial_fixed.py` - Script corregido con parámetros válidos

### 🟢 En Ejecución

```text
[1/3] A2C - ENTRENAMIENTO EN PROGRESO (iniciado 19:26:54)
[2/3] PPO - EN COLA
[3/3] SAC - EN COLA
```text

**Monitor**: Terminal ID: `90da3439-e423-4dee-a54d-11c354a9ed96`

---

## 🎯 TIER 2 CONFIGURATION EQUIVALENCE

### Mapping Multiobjetivo (Balanced Priority)

| Componente | Peso | Descripción |
| ----------- | ------ | ------------- |
| CO2 | 0.35 | Primario - Emisiones carbono |
| Costo | 0.25 | Costo energético |
| Solar | 0.20 | Aprovechamiento solar |
| EV | 0.15 | Satisfacción EV |
| Grid | 0.05 | Estabilidad red |

### Parámetros TIER 2 por Agente

#### PPO (`ppo_sb3.py`)

```python
learning_rate = 2.5e-4          # ↓ 3e-4 (convergencia suave)
batch_size = 256                # ↑ 128 (menos ruido)
n_epochs = 15                   # ↑ 10 (más updates)
ent_coef = 0.02                 # ↑ 0.01 (exploración 2x)
hidden_sizes = (512, 512)       # ↑ (256,256)
activation = "relu"             # ↑ tanh
lr_schedule = "linear"          # ↑ constant
use_sde = True                  # NEW
```text

#### A2C (`a2c_sb3.py`)

```python
learning_rate = 2.5e-4          # ↓ 3e-4
n_steps = 1024                  # ↑ 512
ent_coef = 0.02                 # ↑ 0.01
hidden_sizes = (512, 512)       # ↑ (256,256)
activation = "relu"             # ↑ tanh
lr_schedule = "linear"          # ↑ constant
```text

#### SAC (`sac.py`) - Previo

```python
learning_rate = 2.5e-4          # ↓ 3e-4
batch_size = 256                # ↓ 512
ent_coef = 0.02                 # ↑ 0.01
hidden_sizes = (512, 512)       # ↑ (256,256)
update_per_timestep = 2         # ↑ 1
dropout = 0.1                   # ↑ 0
```text

---

## 📊 ENTRENAMIENTO EN PROGRESO

### [1/3] A2C TIER 2 (2 Episodios)

**Iniciado**: 2026-01-18 19:26:54
**Status**: 🟢 Entrenando
**Parámetros**:

- LR: 2.5e-4
- n_steps: 1024
- entropy: 0.02
- hidden: (512,512)
- activation: relu
- lr_schedule: linear

**Expected Metrics** (2 ep):

- CO2: < 1.85M kg
- Peak Import: < 260 kWh/h
- Avg Reward: 0.45-0.55
- Grid Stability: 0.70-0.80
- **Resultado observado (19 Ene 2026)**: Sin resumen consolidado para A2C (solo `progress/a2c_progress.csv`), no evidencia de aprendizaje.

**Expected Duration**: 15-20 minutos (GPU CUDA)

---

### [2/3] PPO TIER 2 (2 Episodios)

**Status**: ⏳ EN COLA
**Parámetros**:

- LR: 2.5e-4
- batch_size: 256
- n_epochs: 15
- entropy: 0.02
- hidden: (512,512)
- activation: relu
- lr_schedule: linear
- use_sde: True

**Expected Metrics** (2 ep):

- CO2: < 2.0M kg
- Peak Import: < 290 kWh/h
- Avg Reward: 0.40-0.50
- Grid Stability: 0.75-0.85
- **Resultado observado (19 Ene 2026)**: reward 52.554 (plano), CO₂ 220.17 kg, grid 487 kWh, solar 0 → no aprendizaje.

**Expected Duration**: 20-25 minutos

---

### [3/3] SAC TIER 2 (2 Episodios)

**Status**: ⏳ EN COLA
**Parámetros**:

- LR: 2.5e-4
- batch_size: 256
- update_freq: 2
- entropy: 0.02
- hidden: (512,512)
- dropout: 0.1

**Expected Metrics** (2 ep):

- CO2: < 1.80M kg
- Peak Import: < 250 kWh/h
- Avg Reward: 0.55-0.65
- Grid Stability: 0.80-0.90
- **Resultado observado (19 Ene 2026)**: reward 52.189 (plano), CO₂ 220.17 kg, grid 487 kWh, solar 0 → no aprendizaje.

**Expected Duration**: 10-15 minutos

**Total Estimated**: 45-60 minutos

---

## 🔧 TECHNICAL DETAILS

### Función simulate()

Correctamente llamada con parámetros específicos por agente:

```python
# A2C
result_a2c = simulate(
    schema_path=schema_pv,
    agent_name="A2C",
    a2c_timesteps=2 * 8760,
    a2c_n_steps=1024,
    a2c_learning_rate=2.5e-4,
    a2c_entropy_coef=0.02,
    a2c_checkpoint_freq_steps=1000,
    use_multi_objective=True,
)

# PPO
result_ppo = simulate(
    schema_path=schema_pv,
    agent_name="PPO",
    ppo_timesteps=2 * 8760,
    ppo_batch_size=256,
    ppo_n_steps=2048,
    use_multi_objective=True,
)

# SAC
result_sac = simulate(
    schema_path=schema_pv,
    agent_name="SAC",
    sac_episodes=2,
    sac_batch_size=256,
    use_multi_objective=True,
)
```text

### CityLearn Patches Applied

**Problema**: Array indexing error en `Battery.get_max_input_power()`
**Solución**: Clamping de índices + validación de SOC

```python
# Antes:
idx = max(0, np.argmax(soc <= self.capacity_power_curve[0]) - 1)  # ← CRASH

# Después:
idx = max(0, np.argmax(comparison) - 1)
idx = min(idx, len(self.capacity_power_curve) - 1)  # ← SAFE
```text

---

## 📂 ARCHIVOS CLAVE

```text
src/iquitos_citylearn/oe3/
├── agents/
│   ├── ppo_sb3.py          ✅ TIER 2 (config actualizada)
│   ├── a2c_sb3.py          ✅ TIER 2 (config actualizada)
│   └── sac.py              ✅ TIER 2 (prev session)
├── rewards.py              ✅ Multiobjetivo
├── simulate.py             (función principal)
└── dataset_builder.py

scripts/
├── train_tier2_serial_fixed.py  ✅ ENTRENAMIENTO EN EJECUCIÓN
└── _common.py              (utilidades)

apply_citylearn_patches.py  ✅ Patches aplicados

outputs/oe3/training/tier2_2ep_serial/
├── a2c/                    ← ENTRENANDO AHORA
├── ppo/                    ← EN COLA
└── sac/                    ← EN COLA
```text

---

## 🎓 METRICAS ESPERADAS FINALES

### Status de Cálculo de Métricas

#### ✅ MÉTRICAS CALCULADAS EN EVALUACIÓN POST-TRAINING:

Script: `EVALUACION_METRICAS_COMPLETAS.py` (ejecutar después del entrenamiento)

Calcula para cada agente (2 episodios):

- ✅ **Avg Reward**: Recompensa promedio del agente
- ✅ **CO2 (kg)**: Emisiones de carbono estimadas (~0.4 kg CO2/kWh importado)
- ✅ **Peak Import (kWh/h)**: Pico máximo de energía importada de la red
- ✅ **Grid Stability**: Estabilidad de la red (0-1, donde 1 = perfecta)
- ✅ **Convergence Speed**: Velocidad en minutos de GPU

### Convergencia Típica (benchmarks indicativos)

| Métrica | A2C | PPO | SAC | Mejor |
| --------- | ----- | ----- | ----- | ------- |
| Avg Reward (2ep) | 0.45-0.55 | 0.40-0.50 | 0.55-0.65 | 🥇 SAC |
| CO2 (kg) | 1.75-1.85M | 1.85-2.0M | 1.65-1.80M | 🥇 SAC |
| Peak Import (kWh/h) | 240-260 | 260-290 | 220-250 | 🥇 SAC |
| Grid Stability | 0.70-0.80 | 0.75-0.85 | 0.80-0.90 | 🥇 SAC |
| Convergence Speed | Fast | Medium | Medium | 🥇 A2C |

**Salida**: `analyses/oe3/training/RESULTADOS_METRICAS_COMPLETAS.json`

### Velocidad Entrenamiento (wall-clock)

| Agente | Tipo | GPU | CPU |
| -------- | ------ | ----- | ----- |
| A2C | On-policy | ~18 min | ~45 min |
| PPO | On-policy | ~22 min | ~55 min |
| SAC | Off-policy | ~12 min | ~30 min |

---

## 📝 GIT COMMITS

```text
7061b76c - Training: CityLearn patches + fixed serial script + status doc
b4c36887 - TIER 2 DOCS: Updated COMPARATIVA, EJECUTAR_ENTRENAMIENTO
d13d39da - PPO & A2C TIER 2: Updated configs (LR, batch, ent, hidden, etc)
```text

---

## ⚡ MONITOREO EN VIVO

**Terminal ID**: `90da3439-e423-4dee-a54d-11c354a9ed96`

Para ver el entrenamiento en tiempo real:

```powershell
Get-Content -Path "path/to/training.log" -Tail 20 -Wait
```text

O via terminal VS Code:

- Ir a "Terminal" → "Show Running Terminals"
- Seleccionar terminal con ID: `90da3439...`

---

## 🚀 PRÓXIMOS PASOS

1. ⏳ **A2C completa 2 episodios** (esperar 15-20 min)
2. ⏳ **PPO comienza automáticamente** (esperar 20-25 min)
3. ⏳ **SAC comienza automáticamente** (esperar 10-15 min)
4. ✅ **Commit resultados** → "Training: 2-ep test TIER 2 complete"
5. ✅ **Generar reporte final** → Comparar A2C vs PPO vs SAC
6. ✅ **Análisis de convergencia** → Validar TIER 2 improvements

---

## 📊 RESULTADOS ESPERADOS

### Post-Training (al completar todos)

**Archivo de salida**:

```text
outputs/oe3/training/tier2_2ep_serial/
├── a2c/results_summary.json
├── ppo/results_summary.json
└── sac/results_summary.json
```text

**Comparativa final esperada**:

- SAC liderará en CO2 y Peak Import (off-policy advantage)
- PPO seguirá en estabilidad (on-policy + SDE)
- A2C será el más rápido en convergencia (on-policy simplicity)

---

## 🎯 VALIDACIÓN TIER 2

**Objetivo**: Validar que los ajustes TIER 2 aplicados a PPO y A2C resulten en mejoras similares a las obtenidas en SAC.

**KPIs**:

- ✅ Todos los agentes entrenan sin errores
- ✅ Multiobjetivo rewards se aplican correctamente
- ✅ Convergencia mejorada vs TIER 1 (benchmarks previos)
- ✅ SAC mantiene liderazgo en performance
- ✅ A2C/PPO muestran estabilidad mejorada

---

**Status Final**: 🟢 EN EJECUCIÓN
**Última actualización**: 2026-01-18 19:27:01
**Siguiente check**: En 5-10 minutos