# Mejoras TIER 2 V2 - Resumen Ejecutivo

## Fecha: 18-enero-2026

### Objetivos Alcanzados

#### 1. **Recompensa: Énfasis en CO₂ y Picos** ✓

- **CO₂ weight**: Aumentado a **0.55** (primario)
- **Penalización en pico**: **2.5x** más fuerte (vs 1.0x off-peak)
- **Baseline realista**:
  - Off-peak: 130 kWh/h (mall + chargers)
  - Peak: 250 kWh/h (target con BESS)
- **Clipping**: Todas las recompensas normalizadas [-1, 1]

#### 2. **Penalizaciones Explícitas de Potencia Pico** ✓

- Penalidad si **EV power > 150 kW en hora pico**
- Escala: -0.30 (weight) × [-1 a 0] = hasta -0.30 de penalización
- Independiente del peso de CO₂ (suma de penalizaciones)

#### 3. **Observables Enriquecidos** ✓

Ahora disponibles en `info["reward_components"]`:

- `is_peak_hour`: 1 si 18-21h, 0 c.c.
- `is_pre_peak`: 1 si 16-17h (preparación)
- `is_valley`: 1 si 9-11h
- `bess_soc_current`: SOC actual [0-1]
- `bess_soc_target`: Target dinámico por hora
- `bess_soc_reserve_deficit`: max(0, target - actual)
- `pv_power_available_kw`: Potencia FV disponible
- `pv_power_ratio`: FV / total_ev_power
- `ev_power_motos_kw`: Potencia motos
- `ev_power_mototaxis_kw`: Potencia mototaxis
- `ev_power_fairness_ratio`: max/min potencia

#### 4. **Hiperparámetros Estabilizados** ✓

  | Parámetro | Valor | Cambio |  
| ----------- | ------- | -------- |
  | `entropy_coef` | **0.01 FIJO** | Era 0.02 adaptativo ↓ |  
  | `learning_rate_base` | 2.5e-4 | Igual TIER 2 |  
  | `learning_rate_peak` | **1.5e-4** | NUEVO: -40% en pico |  
  | `normalize_obs` | True | HABILITADO |  
  | `normalize_rewards` | True | HABILITADO |  
  | `clip_obs` | 10.0 | Para estabilidad |  

#### 5. **Recompensas Normalizadas y Escaladas** ✓

```python
# Antes: Mal escalado, sin clipping final
reward = w1*r1 + w2*r2 + ...  # [-5, +5]

# Después: Normalizado y clipeado
reward_base = w1*r1 + w2*r2 + ...  # [-1, 1] cada componente
total_penalty = sum(penalties)  # [-1, 0]
reward = CLIP(reward_base + penalty, -1, 1)  # Salida final [-1, 1]
```text

---

## Archivos Creados/Modificados

### Nuevos

1. **`rewards_improved_v2.py`** (156 líneas)
   - Clase `ImprovedMultiObjectiveReward`
   - Pesos `ImprovedWeights` con penalizaciones explícitas
   - Cálculo normalizado de recompensas

2. **`tier2_v2_config.py`** (89 líneas)
   - Configuración unificada V2
   - Métodos para LR dinámico, entropy coef, SOC target
   - Compatible con A2C, PPO, SAC

3. **`rewards_wrapper_v2.py`** (161 líneas)
   - Wrapper que integra observables enriquecidos
   - Step mejorado con tracking de componentes
   - Métodos para acceder a parámetros dinámicos

### Modificados

- Referencia en `simulate.py` para usar wrapper V2
- Documentación de agentes (PPO, A2C, SAC) actualizada

---

## Cómo Usar

### En Script de Entrenamiento

```python
from src.iquitos_citylearn.oe3.tier2_v2_config import TIER2V2Config
from src.iquitos_citylearn.oe3.rewards_wrapper_v2 import ImprovedRewardWrapper

# Crear wrapper mejorado
config_v2 = TIER2V2Config()
env = ImprovedRewardWrapper(env, config=config_v2, verbose=1)

# Acceder a parámetros dinámicos
entropy_coef = env.get_adjusted_entropy_coef()  # 0.01 siempre
lr_actual = env.get_adjusted_lr(hour=19)  # 1.5e-4 en pico
soc_target = env.get_soc_target()  # Dinámico por hora

# Inspeccionar componentes de recompensa
info = env.step(action)
components = info["reward_components"]
print(f"CO2 reward: {components['r_co2']:.3f}")
print(f"Peak penalty: {components['r_peak_power_penalty']:.3f}")
```text

### Cambios en Pesos (si necesitas ajustar)

```python
config_custom = TIER2V2Config(
    co2_weight=0.60,  # Aumentar si necesitas más énfasis
    peak_power_penalty=0.40,  # Aumentar para penalización más fuerte
    soc_reserve_penalty=0.25,  # Aumentar para preparación pre-pico
)
env = ImprovedRewardWrapper(env, config=config_custom)
```text

---

## Comparativa: V1 vs V2

  | Aspecto | V1 (Anterior) | V2 (Nuevo) |  
| --------- | -------------- | ----------- |
  | **CO₂ weight** | 0.50 | **0.55** ↑ |  
  | **Penalización CO₂ pico** | 2.0x | **2.5x** ↑ |  
  | **Potencia pico explícita** | Implícita | **Explícita** ✓ |  
  | **SOC reserve** | Fijo 0.65 | **Dinámico** (0.40-0.85) |  
  | **Entropy coef** | 0.02 adaptativo | **0.01 fijo** |  
  | **LR pico** | No ajustado | **1.5e-4** (reducido) |  
  | **Normalización final** | Parcial | **Completa [-1,1]** |  
  | **Observables** | Básicos | **Enriquecidos** (12+) |  

---

## Próximos Pasos

1. **Reentrenar A2C, PPO, SAC** con wrapper V2
   - Esperar 2 episodios para validación
   - Monitor: Importación en pico vs target (250 kWh/h)

2. **Análisis Pareto** post-entrenamiento
   - CO₂ vs Costo vs Satisfacción EV
   - Usar método `reward_fn.get_pareto_metrics()`

3. **Ajustes finos por feedback**
   - Si CO₂ sigue alto: incrementar `co2_weight` a 0.60
   - Si picos persisten: incrementar `peak_power_penalty` a 0.40

---

## Referencia Rápida - Horas Críticas Iquitos

  | Hora | Tipo | SOC Target | Penalización CO₂ |  
| ------ | ------ | ----------- | ------------------ |
  | 0-8 | Noche | 0.60 | 1.2x |  
  | 9-11 | Valle | 0.60 | 1.2x |  
  | 12-15 | Normal | 0.60 | 1.2x |  
  | **16-17** | **Pre-pico** | **0.85** | **1.5x** |  
  | **18-21** | **PICO** | **0.40** | **2.5x** |  
  | 22-23 | Noche | 0.60 | 1.2x |  

**Peak Demand Limit**: 150 kW (hard limit en pico)

---

## Validación en Entrenamiento

El wrapper reportará automáticamente:

```text
 [Step 1000] Hour=19 | CO2=0.850 | Reward=0.123 | Peak=1 
                                                  ↑ Es hora pico
```text

Si `Reward` es negativo en pico pero importación está baja (< 150 kWh/h):

- ✓ Recompensa funciona correctamente
- Agente aprendió a minimizar importación

Si `Reward` es positivo en pico pero importación está alta (> 250 kWh/h):

- ⚠️ Ajustar `co2_weight` o `peak_power_penalty` hacia arriba