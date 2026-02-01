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

<!-- markdownlint-disable MD013 -->
#### 4. **Hiperparámetros Estabilizados** ✓ | Parámetro | Valor | Cambio | | ----------- | ------- | -------- | | `entropy_coef` | **0.01 FIJO** | Era 0.02 adaptativo ↓ | | `learning_rate_base` | 2.5e-4 | Igual TIER 2 | | `learning_rate_peak` | **1.5e-4** | NUEVO: -40% en pico | | `normalize_obs` | True | HABILITADO | | `normalize_rewards` | True | HABILITADO | | `clip_obs` | 10.0 | Para estabilidad | #### 5. **Recompensas Normalizadas y Escaladas** ✓

<!-- markdownlint-disable MD013 -->
```python
# Antes: Mal escalado, sin clipping final
reward = w1*r1 + w2*r2 + ...  # [-5, +5]

# Después: Normalizado y clipeado
reward_base = w1*r1 + w2*r2 + ...  # [-1, 1] cada componente
total_penalty = sum(penalties)  # [-1, 0]
reward = CLIP(reward_base + penalty, -1, 1)  # Salida final [-1, 1]
```text
<!-- markdownlint-enable MD013 -->

---

## Archivos Creados/Modificados

### Nuevos

1. **`rewards_imp...
```

[Ver código completo en GitHub]python
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
<!-- markdownlint-enable MD013 -->

### Cambios en Pesos (si necesitas ajustar)

<!-- markdownlint-disable MD013 -->
```python
config_custom = TIER2V2Config(
    co2_weight=0.60,  # Aumentar si necesitas más énfasis
    peak_power_penalty=0.40,  # Aumentar para penalización más fuerte
    soc_reserve_penalty=0.25,  # Aumentar para preparación pre-pico
)
env = ImprovedRewardWrapper(env, config=conf...
```

[Ver código completo en GitHub]text
 [Step 1000] Hour=19 | CO2=0.850 | Reward=0.123 | Peak=1 
                                                  ↑ Es hora pico
```text
<!-- markdownlint-enable MD013 -->

Si `Reward` es negativo en pico pero importación está baja (< 150 kWh/h):

- ✓ Recompensa funciona correctamente
- Agente aprendió a minimizar importación

Si `Reward` es positivo en pico pero importación está alta (> 250 kWh/h):

- ⚠️ Ajustar `co2_weight` o `peak_power_penalty` hacia arriba