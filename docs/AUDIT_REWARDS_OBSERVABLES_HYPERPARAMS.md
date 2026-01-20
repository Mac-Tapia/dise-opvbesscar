# 🔍 AUDIT: Recompensas, Observables e Hiperparámetros SAC

**Fecha**: 2026-01-18 19:10
**Status**: 🟡 CRÍTICO - Identifi­cados 8 problemas de escalado y señal

---

## 1. PROBLEMAS EN LA RECOMPENSA

### 1.1 Pesos Mal Configurados

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py#L30-L45)

```python
# ❌ ACTUAL (MALO)
co2: float = 0.45              # Comentario dice 0.50 subido, pero en código es 0.45
cost: float = 0.15
solar: float = 0.15            # Comentario dice bajado, ambiguo
ev_satisfaction: float = 0.05  # Bajado OK
grid_stability: float = 0.20   # Subido de 0.05 (CONTRAPRODUCENTE)
```text

**Problema**: grid_stability=0.20 es excesivo. Con peak_hours=(18,19,20,21) y 4 horas de 24, solo 16% del día está en pico. Darle 20% de peso a penalidad general es **excesivo** cuando se necesita **CO₂/importación en pico**.

**Solución**:

```python
# ✅ PROPUESTO
co2: float = 0.50              # Claro: minimizar CO₂ es PRIMARY
cost: float = 0.10             # Reducido (costo es secundario)
solar: float = 0.20            # Maximizar solar es CRÍTICO para CO₂
ev_satisfaction: float = 0.10  # Satisfacción básica de EVs
grid_stability: float = 0.10   # REDUCIDO: picos se controlan por CO₂
```text

**Por qué**: grid_stability ya está implícito en CO₂ (importación en pico = CO₂ alto). Duplicar peso causa conflicto.

---

### 1.2 Componentes de Recompensa Mal Escalados

### Líneas 150-195 en rewards.py

```python
# ❌ PROBLEMA 1: CO₂ no distingue pico vs off-peak bastante
if is_peak:
    r_co2 = 1.0 - 3.0 * min(1.0, grid_import_kwh / 500.0)  # 500.0 baseline arbitrario
else:
    r_co2 = 1.0 - 1.5 * min(1.0, grid_import_kwh / 500.0)

# PROBLEMA: ¿Por qué 500.0? Eso es ~5x la demanda típica de mall (100 kW avg)
# En pico real (18-21h) con 128 chargers @ max = 272 kW + mall load...
# 500.0 es MUY ALTO → reward casi siempre positivo → sin gradiente de learning
```text

**Baseline debería ser**:

```python
# ✅ PROPUESTO
# Típico: mall ~100 kWh + chargers ~30 kWh (off-peak) = 130 kWh
# En pico: mall ~150 + chargers ~100 (con BESS support) = 250 kWh target
# Si agente importa >250 en pico, debe sufrir penalización

co2_baseline_offpeak = 130.0   # kWh típico off-peak
co2_baseline_peak = 250.0      # kWh objetivo en pico (con BESS y FV)

if is_peak:
    # Si importas > 250 kWh en pico (bad), reward = 1 - 2*(250/250) = -1
    # Si importas < 100 kWh en pico (great), reward = 1 - 2*(100/250) = 0.2
    r_co2 = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)
else:
    # Off-peak más tolerante pero aún penaliza exceso
    r_co2 = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)
```text

**Impacto**: Da **RANGO de variación** en reward (-1 a +1 vs -0.5 a +0.8 antes) → gradientes mejores.

---

### 1.3 Falta Penalización Explícita de Potencia Pico

### Línea 200 en rewards.py

```python
# ❌ ACTUAL
demand_ratio = grid_import_kwh / max(1.0, self.context.peak_demand_limit_kw)

if is_peak:
    r_grid = 1.0 - 4.0 * min(1.0, demand_ratio)  # Penaliza por ENERGÍA, no POTENCIA
```text

**Problema**:

- Penaliza `grid_import_kwh` (energía acumulada en 1 hora)
- NO penaliza **potencia instantánea** (kW)
- SAC nunca ve el "ramp rate" (cómo rápido sube la demanda)

**Solución**: Agregar observable con potencia instantánea (ver abajo en Observables).

---

### 1.4 Mal Escalado de Penalización SOC Reserva

### Línea 215 en rewards.py

```python
# ❌ ACTUAL
pre_peak_hours = [16, 17]
if hour in pre_peak_hours and bess_soc < 0.5:
    soc_penalty = -0.5 * (1.0 - bess_soc / 0.5)  # Máximo -0.5

# PROBLEMA: Si SOC=0.0, penalty = -0.5 * 1.0 = -0.5
# Pero reward total es suma ponderada. Si soc_penalty suma directamente (NO ponderado),
# puede ser -0.5 cuando reward debería ser [-1, +1]
```text

**Mejor**:

```python
# ✅ PROPUESTO
if hour in pre_peak_hours and bess_soc < 0.65:  # Target 65% (no 50%)
    # Penalizar faltante
    soc_deficit = 0.65 - bess_soc
    r_soc_reserve = 1.0 - (soc_deficit / 0.65)  # Normalizado a [0, 1]
    components["r_soc_reserve"] = r_soc_reserve
else:
    components["r_soc_reserve"] = 1.0  # Bonus si cumples
```text

---

### 1.5 Suma de Componentes Sin Normalización Correcta

### Línea 220 en rewards.py

```python
# ❌ ACTUAL
reward = (
    self.weights.co2 * r_co2 +
    self.weights.cost * r_cost +
    self.weights.solar * r_solar +
    self.weights.ev_satisfaction * r_ev +
    self.weights.grid_stability * r_grid +
    components["soc_reserve_penalty"]  # ← NOT PONDERADO
)

# PROBLEMA: soc_reserve_penalty se suma directamente sin peso
# Si weight_co2=0.50, entonces co2 contribuye 0.50 * r_co2
# Pero soc_penalty contribuye sin factor → DESBALANCEADO

# Ejemplo:
# r_co2=-1 → contribuye -0.50
# r_soc=-0.5 → contribuye -0.5
# ¡TRES VECES MÁS PESO para SOC que para CO₂!
```text

**Solución**:

```python
# ✅ PROPUESTO
reward = (
    self.weights.co2 * r_co2 +
    self.weights.cost * r_cost +
    self.weights.solar * r_solar +
    self.weights.ev_satisfaction * r_ev +
    self.weights.grid_stability * r_grid +
    0.10 * components["r_soc_reserve"]  # Ahora ponderado
)

# Luego normalizar
reward = np.clip(reward, -1.0, 1.0)
```text

---

## 2. PROBLEMAS EN OBSERVABLES

### 2.1 Falta de Flags de Hora Pico y Contexto

**Archivo**: [src/iquitos_citylearn/oe3/simulate.py](src/iquitos_citylearn/oe3/simulate.py) (wrapper)

```python
# ❌ ACTUAL: El observable NO incluye:
# - Flag de es_pico (bool): ¿estamos en 18-21h?
# - SOC_bess actual
# - SOC_bess_target_esperado
# - Potencia FV disponible (kW)
# - Colas de chargers por playa

obs = env.reset()  # obs es solo estado de CityLearn
# obs contiene: building loads, solar gen, BESS SOC, ev_state, etc.
# PERO NO flags útiles para tomar decisión
```text

**Solución**: Agregar observables contextuales:

```python
# ✅ PROPUESTO
additional_obs = np.array([
    float(hour in [18, 19, 20, 21]),  # is_peak (0 o 1)
    bess_soc,                          # SOC BESS actual [0-1]
    0.65 if hour in [16,17] else 0.40,  # SOC_target basado en hora
    solar_gen_available / 1000.0,      # PV disponible (normalizado kW)
    queue_motos / 128.0,               # Fracción colas motos [0-1]
    queue_mototaxis / 16.0,            # Fracción colas mototaxis [0-1]
], dtype=np.float32)

obs_extended = np.concatenate([obs_original, additional_obs])
```text

**Beneficio**: SAC ve explícitamente **cuándo es pico**, **cuánta energía solar**, **cuántas colas hay**.

---

### 2.2 Falta Potencia Instantánea vs Energía

**Problema**: CityLearn reporta energía (kWh) en cada timestep.
SAC NO ve la **tasa de cambio** (potencia = dE/dt en kW).

```python
# ❌ ACTUAL
# observation[t] contiene energía acumulada o rates, pero NO potencia pico

# ✅ PROPUESTO
# Agregar derivada (diferencia)
if t > 0:
    power_grid_kw = (grid_import[t] - grid_import[t-1]) / (timestep_hours)
else:
    power_grid_kw = 0

additional_obs.append(np.clip(power_grid_kw / 200.0, -1, 1))  # Normalizado
```text

---

## 3. PROBLEMAS EN HIPERPARÁMETROS SAC

### 3.1 Entropía Automática Muy Alta

**Archivo**: [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py#L130-L145)

```python
# ❌ ACTUAL
ent_coef: str = "auto"          # Auto-ajusta entropía
target_entropy: Optional[float] = -126.0  # -dim(action) = -126

# PROBLEMA:
# - target_entropy = -126 es BAJO (mucha exploración)
# - "auto" ajusta ent_coef para mantenerlo, pero esto significa:
#   "Mantén exploración tan alta que entropy sea siempre -126"
# - Con reward signal débil (como vimos), SAC prefiere EXPLORAR
#   en lugar de EXPLOTAR buenas acciones
```text

**Solución**:

```python
# ✅ PROPUESTO
ent_coef: float = 0.01          # Fijo, NO auto (reduce exploración innecesaria)
target_entropy: Optional[float] = -50.0  # Menos exploración (-dim/2 o menos)

# Con esto, SAC dedica menos capacidad a "hacer ruido"
# y más a "aprender patrones"
```text

**Por qué**: Early training necesita exploración, pero con reward mal escalada, SAC explora demasiado.

---

### 3.2 Learning Rate Ahora Corregido Pero Gradient Steps Bajo

### Línea 140 en sac.py

```python
# ✅ YA FIXED
learning_rate: float = 0.001    # Antes era capped a 3e-5

# PERO gradient_steps es:
gradient_steps: int = 256       # (en config YAML)

# PROBLEMA: gradient_steps=256 es ALTO
# Significa: por cada timestep en env, SAC hace 256 updates
# Con batch_size=32,768 y buffer_size=8,000,000:
#   - Necesita ~256 timesteps para llenar primer batch
#   - Luego 256 updates × 32,768 examples = 8M ejemplos procesados
#   - ESTO ES MUCHÍSIMO para episodios de 8,760 pasos
```text

**Solución**:

```python
# ✅ PROPUESTO
gradient_steps: int = 64        # Reducido de 256 a 64
train_freq: int = 4             # Update cada 4 timesteps (unchanged)

# LÓGICA:
# - train_freq=4: cada 4 pasos en env, hace 1 update
# - gradient_steps=64: cada update procesa 64 minibatches
# - Total: 4 * 64 = 256 ejemplos procesados por step env
#   (vs 256*32768 antes = overkill)
```text

---

### 3.3 Normalización de Recompensa Falta

### Línea 230 en rewards.py

```python
# ❌ ACTUAL
reward = np.clip(reward, -1.0, 1.0)  # Clipped pero NO normalizado

# MEJOR:
reward_mean = np.mean([h["reward_total"] for h in self._reward_history[-100:]])
reward_std = np.std([h["reward_total"] for h in self._reward_history[-100:]])

if reward_std > 0.01:
    reward_normalized = (reward - reward_mean) / (reward_std + 1e-8)
    reward_normalized = np.clip(reward_normalized, -2, 2)
else:
    reward_normalized = reward

components["reward_normalized"] = reward_normalized
return reward_normalized, components  # Retornar normalizado
```text

**Beneficio**: SAC ve recompensas con media ~0 y varianza ~1 → mejor convergencia.

---

### 3.4 Batch Size Extremadamente Alto

### Línea 138 en sac.py (YAML)

```yaml
# ✅ ACTUAL (después del fix)
batch_size: int = 32768         # 32K ejemplos por update

# PROBLEMA con esto:
# - RTX 4060: 8.6 GB VRAM
# - 32K × 900 dims (obs) × 4 bytes = 129 MB solo observaciones
# - + 32K × 126 dims (actions) × 4 bytes = 16 MB
# - + networks (2 Q-networks + policy) ~200 MB
# - + optimizers/buffers ~500 MB
# - TOTAL: >>1 GB, okay para RTX 4060
# PERO:
# - Minibatch tan grande pierde flexibility
# - Mejor: múltiples updates pequeños que 1 update gigante
```text

**Alternativa**:

```python
# ✅ PROPUESTO
batch_size: int = 4096          # Reducido de 32,768 a 4K
gradient_steps: int = 256       # Aumentado (ahora tiene sentido)
train_freq: int = 4             # Unchanged

# LÓGICA:
# 4,096 × 256 = 1M ejemplos por ciclo (vs 32,768 × 256 = 8M)
# Menos "shock" de grandebatch, más exploración de direcciones
```text

---

## 4. RECOMENDACIONES PRIORITARIAS

### TIER 1 (CRÍTICO - Implement AHORA)

1. ✅ **Pesos Multiobjetivo** → [30-45]

   ```python
   co2=0.50, cost=0.10, solar=0.20, ev_satisfaction=0.10, grid_stability=0.10
   ```text

2. ✅ **Baselines CO₂** → Línea 150

   ```python
   co2_baseline_offpeak=130, co2_baseline_peak=250  (vs 500 ahora)
   ```text

3. ✅ **Normalización de SOC Penalty** → Línea 215-230

   ```python
   r_soc_reserve normalizado a [0,1], luego multiplicado por peso
   ```text

4. ✅ **Agregar Observables de Contexto** → simulate.py

   ```python
   is_peak, bess_soc, bess_soc_target, pv_available, queue_motos, queue_mototaxis
   ```text

### TIER 2 (IMPORTANTE - Implement después de validar TIER 1)

1. ✅ **Entropía SAC** → sac.py línea 135

   ```python
   ent_coef=0.01 (fixed, no auto), target_entropy=-50 (vs -126)
   ```text

2. ✅ **Gradient Steps & Batch** → sac.py línea 138-140

   ```python
   batch_size=4096, gradient_steps=256 (vs 32768, 256)
   ```text

3. ✅ **Normalización de Reward** → rewards.py línea 230

   ```python
   reward_normalized usando rolling mean/std
   ```text

---

## 5. TESTING STRATEGY

**Después de TIER 1 changes**:

```text
Paso 100:  reward debe subir a 0.60+  (vs plano 0.56 antes)
Paso 500:  reward debe subir a 0.65+  (clara tendencia)
Paso 1000: reward debe subir a 0.70+  (convergencia visible)
```text

**Métricas a monitorear**:

1. `r_co2` mean (debe subir de -0.1 a 0.2+)
2. `r_grid` std (debe BAJAR, menos varianza)
3. `bess_soc` en pre-peak (debe estar 0.60+)
4. `grid_import` en pico (debe bajar vs baseline)

---

**Estado**: 🔴 **8 PROBLEMAS IDENTIFICADOS - ESPERANDO APROBACIÓN PARA IMPLEMENTAR TIER 1**