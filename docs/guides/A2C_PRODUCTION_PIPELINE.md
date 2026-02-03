# 🚀 A2C Production Pipeline Guide

## Iquitos EV/Solar/BESS Optimization - Advantage Actor-Critic

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura A2C](#arquitectura-a2c)
3. [Comparativa SAC/PPO/A2C](#comparativa-sacppoa2c)
4. [Hiperparámetros](#hiperparámetros)
5. [Uso del Pipeline](#uso-del-pipeline)
6. [Flujo de Entrenamiento](#flujo-de-entrenamiento)
7. [Troubleshooting](#troubleshooting)
8. [Métricas CO₂](#métricas-co₂)

---

## 🎯 Descripción General

El pipeline A2C está diseñado para optimizar el sistema de carga EV con solar y BESS en Iquitos, utilizando el algoritmo **Advantage Actor-Critic**.

### ¿Por qué A2C?

| Característica | A2C | PPO | SAC |
|----------------|-----|-----|-----|
| **Velocidad (wall-clock)** | ★★★★★ Más rápido | ★★★☆☆ Medio | ★★☆☆☆ Más lento |
| **Sample Efficiency** | ★★☆☆☆ Menor | ★★★★☆ Alta | ★★★★★ Mejor |
| **Estabilidad** | ★★★☆☆ Media | ★★★★★ Muy alta | ★★★★☆ Alta |
| **Memoria GPU** | ★★★★★ Baja | ★★★★☆ Media | ★★★☆☆ Alta |

**A2C es ideal cuando:**
- ⚡ El tiempo de entrenamiento es crítico
- 💻 Hardware limitado (< 8GB VRAM)
- 🧪 Iteración rápida de experimentos
- 📊 Pruebas de concepto iniciales

---

## 🏗️ Arquitectura A2C

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────────┐
│                     A2C AGENT ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────────────────────────────┐   │
│  │ Environment │◄────│     CityLearn Wrapper               │   │
│  │ (CityLearn) │     │  • Observation Normalization        │   │
│  └──────┬──────┘     │  • Reward Scaling (×0.1)            │   │
│         │            │  • Action Smoothing                 │   │
│         ▼            └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   A2C NETWORK                           │   │
│  │                                                         │   │
│  │   ┌──────────────┐         ┌──────────────┐            │   │
│  │   │    ACTOR     │         │    CRITIC    │            │   │
│  │   │   (Policy)   │         │   (Value)    │            │   │
│  │   │              │         │              │            │   │
│  │   │  obs (394)   │         │  obs (394)   │            │   │
│  │   │     ↓        │         │     ↓        │            │   │
│  │   │  FC(256)     │         │  FC(256)     │            │   │
│  │   │  ReLU        │         │  ReLU        │            │   │
│  │   │     ↓        │         │     ↓        │            │   │
│  │   │  FC(256)     │         │  FC(256)     │            │   │
│  │   │  ReLU        │         │  ReLU        │            │   │
│  │   │     ↓        │         │     ↓        │            │   │
│  │   │ actions(129) │         │  value(1)    │            │   │
│  │   └──────────────┘         └──────────────┘            │   │
│  │                                                         │   │
│  │   ADVANTAGE = Reward + γ·V(s') - V(s)                  │   │
│  │   LOSS = Actor_Loss + vf_coef·Critic_Loss              │   │
│  │        - ent_coef·Entropy                               │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Observaciones (394 dimensiones)

| Grupo | Dimensiones | Descripción |
|-------|-------------|-------------|
| Solar/Grid | 8 | PV generation, grid metrics |
| BESS | 4 | SOC, power, capacity |
| Chargers (×128) | 128×3 = 384 | Estado de cada cargador |
| Tiempo | 3 | hour, day_of_week, month |
| Extras | 5 | Agregaciones y features |

### Acciones (129 dimensiones)

| Acción | Dimensión | Rango | Descripción |
|--------|-----------|-------|-------------|
| BESS setpoint | 1 | [0, 1] | Control de carga/descarga |
| Charger 1-112 | 112 | [0, 1] | Setpoints motos |
| Charger 113-128 | 16 | [0, 1] | Setpoints mototaxis |

---

## ⚔️ Comparativa SAC/PPO/A2C

### Tiempos de Entrenamiento Estimados (RTX 4060)

| Timesteps | A2C | PPO | SAC |
|-----------|-----|-----|-----|
| 50,000 | ~3 min | ~5 min | ~8 min |
| 100,000 | ~6 min | ~12 min | ~20 min |
| 500,000 | ~30 min | ~1 hora | ~2 horas |
| 1,000,000 | ~1 hora | ~2 horas | ~4 horas |

### Características de cada Algoritmo

#### A2C (Advantage Actor-Critic)
- ✅ **Ventajas:**
  - Entrenamiento más rápido
  - Menor consumo de memoria
  - Actualizaciones síncronas (predecibles)
- ❌ **Desventajas:**
  - Alta varianza en gradientes
  - Menos sample-efficient
  - Puede converger a óptimos locales

#### PPO (Proximal Policy Optimization)
- ✅ **Ventajas:**
  - Muy estable (clipped objective)
  - Buen balance eficiencia/velocidad
  - KL-adaptive para estabilidad extra
- ❌ **Desventajas:**
  - Más lento que A2C
  - Más hiperparámetros que ajustar

#### SAC (Soft Actor-Critic)
- ✅ **Ventajas:**
  - Mejor exploration (entropy maximization)
  - Off-policy (replay buffer)
  - State-of-the-art en muchos benchmarks
- ❌ **Desventajas:**
  - Más lento
  - Mayor consumo de memoria
  - Más complejo de debuggear

---

## ⚙️ Hiperparámetros

### Configuración Optimizada A2C (RTX 4060)

```python
# Hiperparámetros A2C - Optimizados para Iquitos EV/Solar/BESS
A2CConfig(
    train_steps=500_000,        # Total timesteps
    n_steps=2048,               # Rollout buffer (similar a PPO)
    learning_rate=1e-4,         # Con linear decay
    lr_schedule="linear",       # Decay hacia 0

    # GAE (Generalized Advantage Estimation)
    gamma=0.99,                 # Discount factor
    gae_lambda=0.95,            # λ para GAE (reduce varianza)

    # Entropy & Value Function
    ent_coef=0.01,              # Coef. entropy (exploration)
    ent_coef_schedule="linear", # Decay: 0.01 → 0.001
    ent_coef_final=0.001,
    vf_coef=0.5,                # Coef. value function loss
    max_grad_norm=0.5,          # Gradient clipping

    # Network Architecture
    hidden_sizes=(256, 256),    # 2 capas hidden

    # Normalization (CRÍTICO para estabilidad)
    normalize_observations=True,
    normalize_rewards=True,
    reward_scale=0.1,
    clip_obs=10.0,
)
```

### Explicación de Parámetros Clave

| Parámetro | Valor | Por qué |
|-----------|-------|---------|
| `n_steps` | 2048 | Buffer suficiente para capturar patrones diarios |
| `gae_lambda` | 0.95 | Balance bias-varianza en estimación de ventajas |
| `ent_coef` | 0.01→0.001 | Exploration inicial, explotación al final |
| `vf_coef` | 0.5 | Peso relativo del critic vs actor |
| `reward_scale` | 0.1 | Escala rewards a rango manejable |

---

## 🎮 Uso del Pipeline

### Comandos Básicos

```bash
# Entrenamiento estándar (500k timesteps, ~30 min)
python -m scripts.train_a2c_production

# Entrenamiento rápido para testing (50k, ~3 min)
python -m scripts.train_a2c_production --timesteps 50000

# Entrenamiento extendido (1M timesteps, ~1 hora)
python -m scripts.train_a2c_production --timesteps 1000000

# Continuar desde checkpoint
python -m scripts.train_a2c_production --resume

# Solo evaluación (sin entrenar)
python -m scripts.train_a2c_production --eval-only

# Con configuración personalizada
python -m scripts.train_a2c_production --config configs/custom.yaml
```

### Opciones CLI

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--config` | `configs/default.yaml` | Archivo de configuración |
| `--timesteps` | `500000` | Total de pasos de entrenamiento |
| `--resume` | `False` | Continuar desde último checkpoint |
| `--eval-only` | `False` | Solo evaluar, no entrenar |

---

## 📈 Flujo de Entrenamiento

### Pipeline Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                   A2C TRAINING PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣ INICIALIZACIÓN                                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ • Cargar configs/default.yaml                          │    │
│  │ • Detectar GPU (CUDA/MPS/CPU)                          │    │
│  │ • Validar dataset (128 chargers, 8760 timesteps)       │    │
│  │ • Configurar logging y directorios                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                          ↓                                      │
│  2️⃣ ENTRENAMIENTO                                               │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ FOR step in range(timesteps):                          │    │
│  │   │                                                     │    │
│  │   ├─ Collect n_steps experiences (rollout)             │    │
│  │   │   • Execute actions in CityLearn env               │    │
│  │   │   • Store (obs, action, reward, done)              │    │
│  │   │                                                     │    │
│  │   ├─ Compute Advantages (GAE)                          │    │
│  │   │   • δ_t = r_t + γ·V(s_{t+1}) - V(s_t)             │    │
│  │   │   • Â_t = Σ (γλ)^k · δ_{t+k}                       │    │
│  │   │                                                     │    │
│  │   ├─ Update Networks                                   │    │
│  │   │   • Actor: ∇ log π(a|s) · Â                        │    │
│  │   │   • Critic: (V(s) - R_target)²                     │    │
│  │   │   • Entropy: -π log π                              │    │
│  │   │                                                     │    │
│  │   └─ Checkpoint (cada 1000 steps)                      │    │
│  │       • Guardar modelo: a2c_step_XXXXX.zip             │    │
│  └────────────────────────────────────────────────────────┘    │
│                          ↓                                      │
│  3️⃣ EVALUACIÓN FINAL                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ • Ejecutar 1 episodio completo (8760 steps)            │    │
│  │ • Calcular métricas CO₂ (3-component)                  │    │
│  │ • Generar timeseries CSV                               │    │
│  │ • Guardar a2c_summary.json                             │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Archivos Generados

```
checkpoints/
└── a2c/
    ├── a2c_step_001000.zip    # Checkpoint paso 1000
    ├── a2c_step_002000.zip    # Checkpoint paso 2000
    ├── ...
    └── a2c_final.zip          # Modelo final

outputs/oe3_simulations/a2c/
├── result_a2c.json            # Métricas detalladas
├── timeseries_a2c.csv         # Serie temporal horaria
├── trace_a2c.csv              # Trace de entrenamiento
└── a2c_summary.json           # Resumen ejecutivo
```

---

## 🔧 Troubleshooting

### Problemas Comunes

#### ❌ Alta varianza en rewards

**Síntomas:** Rewards oscilando fuertemente entre episodios

**Solución:**
```python
# Reducir learning rate
a2c_learning_rate=5e-5  # En lugar de 1e-4

# Aumentar batch size efectivo
a2c_n_steps=4096  # En lugar de 2048
```

#### ❌ Convergencia a óptimo local

**Síntomas:** Reward estancado, no mejora

**Solución:**
```python
# Aumentar exploration
a2c_entropy_coef=0.02  # En lugar de 0.01

# Usar schedule más lento
ent_coef_schedule="linear"
ent_coef_final=0.005  # En lugar de 0.001
```

#### ❌ GPU out of memory

**Síntomas:** CUDA OOM error

**Solución:**
```python
# Reducir n_steps
a2c_n_steps=1024  # En lugar de 2048

# O usar CPU
a2c_device="cpu"
```

#### ❌ Entrenamiento muy lento

**Síntomas:** Progreso lento, GPU subutilizada

**Solución:**
```bash
# Verificar que PyTorch usa GPU
python -c "import torch; print(torch.cuda.is_available())"

# Aumentar batch size si hay VRAM disponible
a2c_n_steps=4096
```

### Logs de Diagnóstico

```bash
# Ver progreso en tiempo real
tail -f checkpoints/progress/a2c_progress.csv

# Verificar checkpoints
ls -la checkpoints/a2c/

# Inspeccionar último checkpoint
python -c "
from stable_baselines3 import A2C
model = A2C.load('checkpoints/a2c/a2c_final.zip')
print(model.policy)
print(f'Timesteps: {model.num_timesteps}')
"
```

---

## 🌍 Métricas CO₂

### 3-Component Breakdown

El sistema calcula CO₂ con metodología de 3 componentes:

```
┌─────────────────────────────────────────────────────────────────┐
│                 CO₂ CALCULATION (3-COMPONENT)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣ CO₂ EMITIDO POR GRID                                        │
│  ────────────────────────                                       │
│  = Grid Import × 0.4521 kg CO₂/kWh                              │
│  (Central térmica Iquitos - combustibles fósiles)               │
│                                                                 │
│  2️⃣ REDUCCIONES INDIRECTAS (Evita grid import)                  │
│  ─────────────────────────────────────────────                  │
│  = (Solar consumido + BESS descargado) × 0.4521                 │
│  (Energía que NO viene del grid térmico)                        │
│                                                                 │
│  3️⃣ REDUCCIONES DIRECTAS (Reemplaza gasolina)                   │
│  ──────────────────────────────────────────────                 │
│  = EV total cargada × 2.146 kg CO₂/kWh                          │
│  (EVs evitan vehículos de combustión)                           │
│                                                                 │
│  📊 CO₂ NETO = Emitido - Indirectas - Directas                  │
│                                                                 │
│  Si CO₂ NETO < 0 → ✅ SISTEMA CARBONO-NEGATIVO                  │
│  Si CO₂ NETO > 0 → ⚠️  Sistema carbono-positivo                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Objetivos de Entrenamiento

| Métrica | Baseline (sin RL) | Objetivo A2C | Unidad |
|---------|-------------------|--------------|--------|
| CO₂ Emitido Grid | ~640,000 | < 200,000 | kg/año |
| Reducciones Indirectas | ~380,000 | > 400,000 | kg/año |
| Reducciones Directas | ~509,000 | ~509,000 | kg/año |
| CO₂ Neto | +131,000 | < 0 (negativo) | kg/año |

### Multi-Objetivo Pesos

```python
# Configuración CO₂_FOCUS para A2C
multi_objective_priority = "co2_focus"

# Pesos resultantes:
co2_weight: 0.50         # PRIMARY: Minimizar importación grid
solar_weight: 0.20       # Maximizar autoconsumo solar
cost_weight: 0.15        # Minimizar costo eléctrico
ev_satisfaction: 0.10    # Satisfacer demanda EV
grid_stability: 0.05     # Estabilidad de red
```

---

## 📊 Resultados Esperados

### Benchmark A2C (RTX 4060, 500k timesteps)

| Métrica | Valor Esperado |
|---------|----------------|
| Tiempo entrenamiento | ~30 min |
| Steps ejecutados | 500,000 |
| Final reward (mean) | 0.03 - 0.08 |
| CO₂ Neto | -200,000 a -400,000 kg |
| Carbon Negative | ✅ Sí |

### Comparativa Final

| Agente | CO₂ Neto (kg/año) | Mejora vs Baseline |
|--------|-------------------|-------------------|
| Baseline (sin control) | +131,000 | - |
| A2C | -200,000 a -300,000 | ~250-350% |
| PPO | -300,000 a -500,000 | ~350-480% |
| SAC | -400,000 a -700,000 | ~400-630% |

---

## 🔗 Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| [train_a2c_production.py](../../scripts/train_a2c_production.py) | Script de entrenamiento |
| [a2c_sb3.py](../../src/iquitos_citylearn/oe3/agents/a2c_sb3.py) | Implementación agente |
| [simulate.py](../../src/iquitos_citylearn/oe3/simulate.py) | Función simulate() |
| [rewards.py](../../src/iquitos_citylearn/oe3/rewards.py) | Multi-objetivo rewards |
| [default.yaml](../../configs/default.yaml) | Configuración principal |

---

**Fecha:** 2026-02-04  
**Versión:** 1.0.0  
**Autor:** pvbesscar-copilot
