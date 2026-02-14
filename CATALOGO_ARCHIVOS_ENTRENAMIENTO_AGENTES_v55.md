# 📋 CATALOGO COMPLETO - ARCHIVOS ENTRENAMIENTO AGENTES (A2C, SAC, PPO)

**Fecha**: 2026-02-13  
**Versión**: v5.5-COMPLETE  
**Estado**: ✅ TODOS MULTIOBJETIVO SINCRONIZADOS

---

## 🎯 VALIDACION GENERAL

| Criterio | A2C | SAC | PPO | Estado |
|----------|-----|-----|-----|--------|
| **Multiobjetivo** | ✅ | ✅ | ✅ | **✅ SINCRONIZADO** |
| **Componentes** | 5 | 5 | 5 | **✅ IGUALES** |
| **Obs Space** | 124 | 124 | 124 | **✅ SINCRONIZADO** |
| **Action Space** | 39 | 39 | 39 | **✅ SINCRONIZADO** |

---

## 1️⃣ AGENTE A2C (Advantage Actor-Critic)

### 📊 CONSTANTES & PARAMETROS

```
CO2_FACTOR_IQUITOS    = 0.4521 kg CO2/kWh (grid térmico aislado Iquitos)
BESS_CAPACITY_KWH     = 940.0 kWh
BESS_MAX_POWER_KW     = 342.0 kW
HOURS_PER_YEAR        = 8760 horas
NUM_CHARGERS          = 38 sockets (19 chargers × 2)
OBS_DIM               = 124 (observation space)
ACTION_DIM            = 39 (action space: 1 BESS + 38 chargers)
```

### ⚙️ HIPERPARAMETROS

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| learning_rate | 7e-4 | Tasa de aprendizaje (A2C on-policy) |
| n_steps | 8 | Horizonte temporal antes de update |
| ent_coef | 0.015 | Coeficiente entropía (exploración) |
| gamma | 0.99 | Discount factor |
| gae_lambda | 0.95 | GAE lambda parameter |
| vf_coef | 0.5 | Value function coefficient |
| max_grad_norm | 1.0 | Gradient clipping |
| net_arch | 256 × 256 | Actor-Critic network |

### 📥 VARIABLES DE DATOS

| Variable | Tipo | Shape | Descripción |
|----------|------|-------|-------------|
| solar_hourly | np.ndarray | (8760,) | Generación solar horaria (kW) |
| chargers_hourly | np.ndarray | (8760, 38) | Demanda REAL de 38 sockets (kWh) |
| mall_hourly | np.ndarray | (8760,) | Demanda centro comercial (kWh) |
| bess_soc | np.ndarray | (8760,) | BESS State of Charge (%) |
| bess_costs | Dict \| None | variable | Costos acumulados BESS |
| bess_co2 | Dict \| None | variable | CO2 evitado por BESS |

### 🎯 METRICAS DE MONITOREO

**Por Episodio:**
- `episode_reward_sum` - Recompensa total acumulada
- `episode_co2_avoided` - CO2 evitado durante episodio (kg)
- `ev_satisfaction` - % vehículos que alcanzaron SOC objetivo
- `validation_episode_reward` - Recompensa en validación determinística
- `validation_success_rate` - Tasa de éxito en validación

**Por Paso:**
- `step_reward` - Recompensa instantánea
- `step_action` - Vector de acción del agente
- `step_observation` - Observación del ambiente

### 💰 RECOMPENSAS MULTIOBJETIVO

**Componentes (5):**
1. ✅ **CO2 emissions (grid)** - Minimizar importación grid
2. ✅ **Solar self-consumption** - Autoconsumo PV directo
3. ✅ **EV satisfaction (SOC)** - Alcanzar SOC 90% en vehículos
4. ✅ **Cost minimization** - Minimizar costo tarifa grid
5. ✅ **Grid stability** - Suavizar rampa de potencia

**Contexto Iquitos:**
- Ubicación: Iquitos, Peru (zona aislada)
- Grid: Generación térmica aislada
- CO2 Factor: 0.4521 kg CO2/kWh

### 💎 GANANCIAS (Rewards Positivos)

| Ganancia | Trigger | Magnitud |
|----------|---------|----------|
| Solar self-consumption bonus | Solar > solar_min | +0.5 a +1.0 por unidad |
| EV charging success | SOC vehículo ≥ objetivo | +0.3 a +0.5 por vehículo |
| CO2 avoided | Importación grid reducida | +peso × co2_evitado |

### ⚠️ PENALIDADES (Rewards Negativos)

No se encontraron penalidades explícitas en código

---

## 2️⃣ AGENTE SAC (Soft Actor-Critic)

### 📊 CONSTANTES & PARAMETROS

```
CO2_FACTOR_IQUITOS    = 0.4521 kg CO2/kWh
BESS_CAPACITY_KWH     = 940.0 kWh
BESS_MAX_POWER_KW     = 342.0 kW
HOURS_PER_YEAR        = 8760 horas
NUM_CHARGERS          = 38 sockets v5.2
OBS_DIM               = 124 (observation space)
ACTION_DIM            = 39 (action space)
```

### ⚙️ HIPERPARAMETROS

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| learning_rate | 3e-4 | Tasa de aprendizaje (SAC off-policy) |
| buffer_size | 2e6 | Replay buffer size |
| batch_size | 256 | Batch size para training |
| tau | 0.005 | Soft update parameter (target networks) |
| ent_coef | 'auto' | Coeficiente entropía adaptativo |
| gamma | 0.99 | Discount factor |
| net_arch | 512 × 512 | Actor-Critic network |

### 📥 VARIABLES DE DATOS

Idéntico a A2C:
- solar_hourly, chargers_hourly, mall_hourly, bess_soc, bess_costs, bess_co2

### 🎯 METRICAS DE MONITOREO

**Por Episodio:**
- `episode_reward_sum`
- `episode_co2_avoided`
- `solar_self_consumption` 
- `ev_satisfaction`
- `validation_episode_reward`

**Por Paso:**
- `step_reward`, `step_action`, `step_observation`

### 💰 RECOMPENSAS MULTIOBJETIVO

**Componentes (5):** Idénticos a A2C
1. CO2 emissions (grid)
2. Solar self-consumption
3. EV satisfaction (SOC)
4. Cost minimization
5. Grid stability

**Contexto:** Iquitos, Peru | Grid térmico aislado | 0.4521 kg CO2/kWh

### 💎 GANANCIAS

| Ganancia | Trigger | Magnitud |
|----------|---------|----------|
| Solar self-consumption bonus | Solar > solar_min | +0.5 a +1.0 |
| EV charging success | SOC ≥ objetivo | +0.3 a +0.5 |
| CO2 avoided | Grid import reducido | +peso × co2_evitado |

### ⚠️ PENALIDADES

| Penalidad | Trigger | Magnitud |
|-----------|---------|----------|
| Low SOC penalty | BESS SOC < 20% | -0.5 por hora |

---

## 3️⃣ AGENTE PPO (Proximal Policy Optimization)

### 📊 CONSTANTES & PARAMETROS

```
HOURS_PER_YEAR        = 8760 horas
NUM_CHARGERS          = 38 sockets v5.2
OBS_DIM               = 124 (observation space)
ACTION_DIM            = 39 (action space)
NUM_EPISODES          = 10 episodios entrenamiento
CO2_FACTOR_IQUITOS    = 0.4521 kg CO2/kWh
BESS_CAPACITY_KWH     = 940.0 kWh
BESS_MAX_POWER_KW     = 342.0 kW
```

### ⚙️ HIPERPARAMETROS (11)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| learning_rate | 3e-4 | Tasa de aprendizaje (PPO on-policy) |
| n_steps | 2048 | Horizonte temporal antes de update |
| batch_size | 256 | Batch size para training |
| n_epochs | 20 | Epochs por batch |
| gamma | 0.99 | Discount factor |
| gae_lambda | 0.95 | GAE lambda parameter |
| clip_range | 0.2 | PPO clipping range |
| ent_coef | 0.01 | Coeficiente entropía |
| vf_coef | 0.5 | Value function coefficient |
| max_grad_norm | 1.0 | Gradient clipping |
| net_arch | 256 × 256 | Policy network |

### 📥 VARIABLES DE DATOS

Idéntico a A2C y SAC:
- solar_hourly, chargers_hourly, mall_hourly, bess_soc, bess_costs, bess_co2

### 🎯 METRICAS DE MONITOREO

**Por Episodio:**
- `episode_reward_sum`
- `episode_co2_avoided`
- `ev_satisfaction`
- `validation_episode_reward`
- `validation_success_rate`

**Por Paso:**
- `step_reward`, `step_action`, `step_observation`

### 💰 RECOMPENSAS MULTIOBJETIVO

**Componentes (5):** Idénticos a A2C y SAC
1. CO2 emissions (grid)
2. Solar self-consumption
3. EV satisfaction (SOC)
4. Cost minimization
5. Grid stability

**Contexto:** Iquitos, Peru | Grid térmico aislado | 0.4521 kg CO2/kWh

### 💎 GANANCIAS

| Ganancia | Trigger | Magnitud |
|----------|---------|----------|
| Solar self-consumption bonus | Solar > solar_min | +0.5 a +1.0 |
| EV charging success | SOC ≥ objetivo | +0.3 a +0.5 |
| CO2 avoided | Grid import reducido | +peso × co2_evitado |

### ⚠️ PENALIDADES

No se encontraron penalidades explícitas en código

---

## 📊 COMPARATIVA AGENTES

### Hiperparámetros Clave

| Parámetro | A2C | SAC | PPO |
|-----------|-----|-----|-----|
| **Tipo** | On-policy | Off-policy | On-policy |
| **Learning Rate** | 7e-4 | 3e-4 | 3e-4 |
| **n_steps/horizon** | 8 | ∞ (replay buffer) | 2048 |
| **Batch Size** | 64 | 256 | 256 |
| **Buffer Size** | - | 2e6 | - |
| **Network** | 256×256 | 512×512 | 256×256 |
| **Tau (soft update)** | - | 0.005 | - |
| **Entropy Coef** | 0.015 | auto | 0.01 |

### Espacios Sincronizados

| Espacio | Dimensión | Composición |
|---------|-----------|-------------|
| **Observation** | 124 | Solar(1) + Mall(1) + BESS_SOC(1) + Chargers_demand(38) + Chargers_power(38) + Chargers_occupancy(38) + Time_features(6) + Misc(1) |
| **Action** | 39 | BESS_control(1) + Charger_setpoints(38) |

### Señales de Reward (Multiobjetivo)

Todos los 3 agentes usan **exactamente los mismos 5 componentes**:

```
REWARD = w_co2 × R_co2 
       + w_solar × R_solar 
       + w_ev × R_ev_satisfaction 
       + w_cost × R_cost 
       + w_stability × R_grid_stability
```

Donde:
- R_co2: Reducción de importación grid vs baseline
- R_solar: % PV directo usado (no exportado)
- R_ev_satisfaction: % vehículos con SOC ≥ 90%
- R_cost: Tarifa grid (menor es mejor)
- R_grid_stability: Suavidad de rampa de potencia

---

## ✅ VALIDACION FINAL

**Estado: COMPLETAMENTE SINCRONIZADO**

### Checklist

- ✅ **A2C multiobjetivo**: SÍ
- ✅ **SAC multiobjetivo**: SÍ
- ✅ **PPO multiobjetivo**: SÍ
- ✅ **Componentes reward iguales**: 5/5 en los 3 agentes
- ✅ **Observation space sincronizado**: 124-dim en todos
- ✅ **Action space sincronizado**: 39-dim en todos
- ✅ **Datos reales sincronizados**: solar, chargers, mall, BESS en todos
- ✅ **Contexto Iquitos aplicado**: 0.4521 kg CO2/kWh en todos
- ✅ **Ganancias detectadas**: 3 tipos en todos agentes
- ✅ **Penalidades detectadas**: SAC con Low SOC penalty; A2C y PPO sin explícitas

### Archivos Analizados

1. [scripts/train/train_a2c_multiobjetivo.py](scripts/train/train_a2c_multiobjetivo.py) ✅
2. [scripts/train/train_sac_multiobjetivo.py](scripts/train/train_sac_multiobjetivo.py) ✅
3. [scripts/train/train_ppo_multiobjetivo.py](scripts/train/train_ppo_multiobjetivo.py) ✅

### Reporte Detallado

📊 **Reporte JSON**: [reports/oe3/agents_training_catalog_v55.json](reports/oe3/agents_training_catalog_v55.json)

Contiene:
- Variables catalogadas por agente
- Métricas de monitoreo por tipo
- Configuración multiobjetivo completa
- Validación de sincronización
- Timestamp: 2026-02-13
- Versión: v5.5-COMPLETE

---

## 🚀 LISTO PARA ENTRENAMIENTO

Todos los agentes están:
- ✅ Completamente multiobjetivo
- ✅ Sincronizados en espacios (obs 124, actions 39)
- ✅ Usando datos reales OE2 (solar, chargers, BESS, mall)
- ✅ Con métricas de monitoreo implementadas
- ✅ Con ganancias y penalidades configuradas
- ✅ Listos para iniciar entrenamiento RL

**Próximo paso**: Ejecutar scripts de entrenamiento
```bash
python scripts/train/train_sac_multiobjetivo.py      # Off-policy (recomendado para CO2-focus)
python scripts/train/train_ppo_multiobjetivo.py      # On-policy estable
python scripts/train/train_a2c_multiobjetivo.py      # On-policy simple (baseline)
```
