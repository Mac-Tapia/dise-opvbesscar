# SAC TIER 2 OPTIMIZATION - POST-RELANZAMIENTO

**Estado**: PLAN EJECUTABLE (SAC relanzado con LR corregido)
**Fecha**: 2025-02-13
**Objetivo**: Maximizar convergencia SAC después del relanzamiento LR 3e-4

---

## 📋 ANÁLISIS SITUACIÓN ACTUAL

### ✅ ESTADO SAC AHORA

- **Learning Rate**: 3e-4 (corregido de 1e-3)
- **Entropía**: ent_coef=0.01 fijo (no auto)
- **Target Entropy**: -50.0 (menos exploración que -126.0)
- **Batch Size**: 512
- **Buffer**: 100k transitions
- **Episodes**: 50 (mínimo para ~900 obs dims × 126 act dims)

### ⚠️ PROBLEMAS IDENTIFICADOS EN TIER 1

1. **Recompensa**: Pesos mal distribuidos, sin normalización adaptativa
2. **Observables**: Faltan flags de pico, SOC dinámica, colas por playa
3. **Hiperparámetros**: ent_coef podría ser aún mayor; target_entropy podría
ajustarse

---

## 🎯 TIER 2 FIXES - IMPLEMENTACIÓN INMEDIATA

### A. RECOMPENSA - NORMALIZACIÓN ADAPTATIVA

**Cambio**: Implementar running statistics y normalización por percentiles

```python
# En src/iquitos_citylearn/oe3/rewards.py: MultiObjectiveReward.__init__

class MultiObjectiveReward:
    def __init__(self, weights=None, context=None, adapt_rewards=True):
        # ... código existente ...

        # NEW: Estadísticas adaptativas por componente
        self._component_history = {
            "r_co2": [],
            "r_cost": [],
            "r_solar": [],
            "r_ev": [],
            "r_grid": [],
        }
        self._history_size = 500  # Rolling window
        self._adapt_rewards = adapt_rewards
        self._reward_percentiles = {k: (0.0, 1.0) for k in self._component_history}
```text

**Lógica**:

- Guardar último 500 rewards por componente
- Calcular p25 y p75
- Normalizar cada componente al rango [p25, p75] → [-1, 1]

---

### B. FUNCIÓN COMPUTE() - BASELINES DINÁMICAS

**Cambio**: Ajustar baselines según hora y estado

```python
def compute(self, grid_import_kwh, grid_export_kwh, solar_generation_kwh,
            ev_charging_kwh, ev_soc_avg, bess_soc, hour, ev_demand_kwh=0.0):

    components = {}
    is_peak = hour in self.context.peak_hours  # [18, 19, 20, 21]

    # ========== CO₂ RECOMPENSA (50% del peso) ==========
    co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh

    # BASELINES DINÁMICAS (no fijas)
    co2_baseline_offpeak = 130.0  # kWh/hora típico off-peak
    co2_baseline_peak = 250.0     # kWh/hora target con BESS en pico

    if is_peak:
        # Penalidad EXPONENCIAL en pico (no lineal)
        # Si importas 250 → r_co2 = 1 - 2*(250/250) = -1
        # Si importas 100 → r_co2 = 1 - 2*(100/250) = 0.2
        # Si importas 50  → r_co2 = 1 - 2*(50/250) = 0.6
        r_co2_raw = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)

        # BONUS si battería contribuyó a bajar importación
        bess_contribution = max(0, bess_soc - 0.40)  # SOC > 40% en pico
        r_co2 = r_co2_raw + 0.3 * bess_contribution  # Bonus +0.3 si SOC bien
    else:
        r_co2_raw = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)
        r_co2 = r_co2_raw  # Sin bonus off-peak

    r_co2 = np.clip(r_co2, -1.0, 1.0)
    components["r_co2"] = r_co2
    components["co2_kg"] = co2_kg

    # ========== ESTABILIDAD GRID (10% → aumentar a 15%) ==========
    demand_ratio = grid_import_kwh / self.context.peak_demand_limit_kw

    if is_peak:
        # Penalidad MUY fuerte en pico si superas 200 kW
        if demand_ratio > 1.0:
            r_grid = -1.0  # Violación severa
        else:
            r_grid = 1.0 - 3.0 * demand_ratio  # Gradientes más fuertes
    else:
        r_grid = 1.0 - 1.5 * min(1.0, demand_ratio)

    r_grid = np.clip(r_grid, -1.0, 1.0)
    components["r_grid"] = r_grid

    # ... resto de componentes igual ...

    # RECOMPENSA TOTAL - TIER 2: Pesos rebalanceados
    reward = (
        0.50 * r_co2 +      # PRIMARY: minimizar CO₂
        0.15 * r_grid +     # SECUNDARIO: estabilidad (+5%)
        0.20 * r_solar +    # Autoconsumo
        0.10 * r_ev +       # Satisfacción EV
        0.05 * r_cost       # Costo mínimo
    )

    reward = np.clip(reward, -1.0, 1.0)
    components["reward_total"] = reward
    return reward, components
```text

**Cambios clave**:

1. ✅ Bonus por SOC en pico (anima a cargar batería)
2. ✅ Penalidad exponencial si superas límite (violación severa = -1.0)
3. ✅ Grid stability peso +5% (0.10 → 0.15)

---

### C. OBSERVABLES - ENRIQUECIMIENTO

**Cambio**: Incluir flags operacionales en observation space

**Ubicación**: `src/iquitos_citylearn/oe3/enriched_observables.py`

**Observables a añadir** (ya existen, solo asegurar inclusión):

```python
enriched_state = {
    "is_peak_hour": 1 if hour in [18,19,20,21] else 0,           # Flag pico
    "hour_of_day": float(hour),                                    # Hora [0-23]
    "bess_soc_current": bess_soc,                                  # SOC [0-1]
    "bess_soc_target": soc_target_dinamico,                       # SOC objetivo dinámico
    "bess_soc_reserve_deficit": max(0, soc_target - bess_soc),   # Déficit reserva
    "pv_power_available_kw": pv_power,                            # FV disponible
    "pv_power_ratio": pv_power / (ev_power + 0.1),              # Cobertura FV
    "grid_import_kw": grid_import,                                # Importación actual
    "ev_power_motos_kw": power_motos,                            # Motos [kW]
    "ev_power_mototaxis_kw": power_mototaxis,                    # Mototaxis [kW]
    "ev_power_fairness_ratio": max_power / min_power,            # Equilibrio playas
}
```text

**Dimensión**:

- Base (CityLearn): ~900 dims
- - Enriquecimiento: +15 dims
- **Total**: ~915 dims (aún dentro de capacidad)

**Utilidad**:

- ✅ Red aprende a reconocer horas pico automáticamente
- ✅ SOC target dinámico → estrategia preparación pre-pico
- ✅ Fairness flag → evita sobrecargar una playa
- ✅ PV ratio → incentiva uso solar en tiempo real

---

### D. HIPERPARÁMETROS - AJUSTES TIER 2

#### D.1 Entropía

**Cambio Propuesto**:

```python
ent_coef: float = 0.02        # Aumentar de 0.01 (más exploración inicial)
target_entropy: float = -40.0  # Reducir penalidad (de -50.0)
```text

**Justificación**:

- `ent_coef=0.02` → 2x exploración (evita mínimos locales)
- `target_entropy=-40.0` → Red puede ser más determinística (mejor control)
- Rango exploración sigue siendo restringido (vs -126.0)

#### D.2 Learning Rates

**Cambio Propuesto**:

```python
# En SACConfig dataclass:
learning_rate: float = 2.5e-4  # Bajar de 3e-4 (más estable)
critic_lr: float = 2.5e-4      # Critic LR
actor_lr: float = 2.5e-4       # Actor LR
alpha_lr: float = 1e-4         # LR para alpha (entropía)
```text

**Justificación**:

- SAC es sensible a LR (mejor convergencia con LR menor)
- 2.5e-4 es sweet spot entre velocidad y estabilidad
- alpha_lr pequeño (1e-4) → ajuste lento de entropía

#### D.3 Batch & Buffer

**Cambio Propuesto**:

```python
batch_size: int = 256           # Bajar de 512 (menos ruido)
buffer_size: int = 150000       # Aumentar de 100k (más diversidad)
update_per_timestep: int = 2    # 2 updates por step (vs 1)
```text

**Justificación**:

- Batch menor → gradientes menos ruidosos
- Buffer mayor → experiencia más diversa
- 2 updates → crítico entrenado más frecuentemente

#### D.4 Red Neuronal

**Cambio Propuesto**:

```python
hidden_sizes: tuple = (512, 512)  # Aumentar de (256, 256)
hidden_activation: str = "relu"   # Mantener
use_dropout: bool = True          # NUEVO: regularización
dropout_rate: float = 0.1         # 10% regularización
```text

**Justificación**:

- Redes 512x512 más expresivas (alto-dimensional obs)
- Dropout evita overfitting en pesos
- SAC combina bien con redes grandes + dropout

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Código (2 horas)

- [ ] **rewards.py**:
  - Agregar `_component_history` y stats adaptativas
  - Modificar `compute()` con baselines dinámicas y bonuses
  - Rebalancear pesos (0.50/0.15/0.20/0.10/0.05)

- [ ] **sac.py**:
  - Actualizar `SACConfig` (ent_coef, learning_rates, batch_size, etc.)
  - Verificar que observables enriquecidos se pasan al modelo

- [ ] **enriched_observables.py**:
  - Asegurar que todos los 15 features se incluyen
  - Testar `get_enriched_state()` con valores reales

### Fase 2: Validación (1 hora)

- [ ] Cargar checkpoint actual de SAC
- [ ] Ejecutar 1 episodio de test
- [ ] Verificar:
  - ✅ Observation shape = (915,)
  - ✅ Reward en rango [-1, 1]
  - ✅ Sin NaN/Inf

### Fase 3: Entrenamiento (24 horas en GPU)

- [ ] Entrenar con Fase 1 fixes
- [ ] Monitorear:
  - Reward promedio por hora (especialmente picos)
  - Importación grid (target: <250 kWh en pico)
  - SOC pre-pico (target: >60% en horas 16-17)

### Fase 4: Análisis (2 horas)

- [ ] Comparar vs baseline (A2C, SAC sin fixes)
- [ ] Generar reporte de mejoras
- [ ] Graficar convergencia

---

## 📊 MÉTRICAS ÉXITO TIER 2 | Métrica | Baseline | Target TIER 2 | Cómo Medir | | --- | ---------- | --- | ----------- | | **Importación Pico (kWh/hora)** | 280-300 | <250 | Promedio horas 18-21 | | **Importación Off-Peak (kWh/hora)** | 120-140 | <130 | Promedio horas 0-8 | | **SOC Pre-Pico (16-17h)** | 0.45-0.55 | >0.65 | Promedio horas 16-17 | | **SOC Pico (18-21h)** | 0.20-0.30 | >0.35 | Promedio horas 18-21 | | **CO₂ Total Año (kg)** | ~1.8e6 | <1.7e6 | Integración anual | |**Reward Convergencia**|Lento (~ep 30)|Rápido (~ep 15)|Episode smoothed| | **Fairness (motos/mototaxis)** | 1.2-1.5 | <1.1 | Ratio máx/mín | ---

## 🔍 DEBUGGING ESPERADO

### Si Reward diverge

- Bajar `ent_coef` a 0.01
- Reducir `learning_rate` a 2e-4

### Si Importación sigue alta

- Aumentar peso CO₂ de 0.50 a 0.60
- Bajar baseline pico de 250 a 220

### Si SOC se drena

- Aumentar bonus BESS en `r_co2` de 0.3 a 0.5
- Penalizar más si `bess_soc < 0.30` en pico

### Si converge muy lento

- Aumentar `batch_size` a 512
- Aumentar `update_per_timestep` a 3

---

## 📝 CHECKLIST EJECUCIÓN

```text
FASE 1: CÓDIGO
---
[ ] Crear archivo: SAC_TIER2_IMPLEMENTATION.md (paso a paso)
[ ] Editar rewards.py - componentes adaptativas
[ ] Editar rewards.py - baselines dinámicas
[ ] Editar rewards.py - pesos rebalanceados
[ ] Editar sac.py - SACConfig actualizado
[ ] Editar sac.py - incluir observables enriquecidos
[ ] Compilar/Linter check
[ ] Commit: "SAC TIER 2: Normalización adaptativa + observables enriquecidos"

FASE 2: VALIDACIÓN
---
[ ] Test reshape observation: esperado (915,)
[ ] Test reward output: rango [-1, 1]
[ ] Test step(): sin NaN/Inf
[ ] Cargar checkpoint SAC existente
[ ] 1 episodio forward pass
[ ] Verificar gradientes (no exploding/vanishing)

FASE 3: ENTRENAMIENTO
---
[ ] Ejecutar: python -m src.train_sac_cuda --episodes=50
[ ] Monitorear GPU: nvidia-smi
[ ] Graficar progreso cada 2 episodios
[ ] Checkpoint cada episodio

FASE 4: ANÁLISIS
---
[ ] Generar dashboard de convergencia
[ ] Comparar vs A2C baseline
[ ] Reportar mejoras
[ ] Identificar próximos fixes (TIER 3)

```text

---

## 🎓 REFERENCIAS TEÓRICAS

### Por qué estos cambios funcionan

1. **Normalización Adaptativa** (rewards.py)
   - SAC es algoritmo on-policy (sensible a escala)
   - Normalizar por percentiles evita saturation
   - Permite pesos más simples (no necesita tuning manual)

2. **Baselines Dinámicas** (rewards.py)
   - Baselines fijos ignoran contexto temporal
   - Baselines = target realista por hora
   - Diferencia = (actual - target) = signal RL

3. **Observables Enriquecidos** (enriched_obs.py)
   - Red neuronal explora mejor con **state features**
   - Flags de pico = aprender scheduling
   - SOC dinámico = aprender reserva
   - Fairness = aprender coordinación multi-playa

4. **Hiperparámetros TIER 2** (sac.py)
   - SAC necesita alta entropía (exploración)
   - LR menor = convergencia más estable
   - Batch pequeño = menos correlación
   - Redes grandes = capacidad expresiva

---

## 📞 CONTACTO PARA ISSUES

Si durante implementación encuentras:

- **Valores NaN**: Check normalización dividir por cero
- **Reward siempre negativo**: Ajustar baselines
- **GPU memory**: Reducir batch_size de 256 a 128
- **Convergencia lenta**: Aumentar update_per_timestep

---

**Próximas fases**: TIER 3 (model-based predictions), TIER 4 (multi-agent
coordination)
