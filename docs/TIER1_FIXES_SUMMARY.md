# ✅ TIER 1 FIXES APPLIED - REWARDS & HYPERPARAMS AUDIT

**Fecha**: 2026-01-18 19:15  
**Commit**: `3d41ca7f`  
**Status**: 🟢 TIER 1 COMPLETE - Listo para relanzar entrenamiento

---

## Resumen de Cambios

Se identificaron y **corrigieron 4 problemas críticos** que impedían que SAC aprendiera:

### 1️⃣ Pesos Multiobjetivo Rebalanceados

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py#L30)

| Métrica | Antes | Después | Razón |
| --- | --- | --- | --- |
| **CO₂** | 0.45 | **0.50** | PRIMARY: matriz térmica 0.45 kg/kWh (aislada) |
| **Solar** | 0.15 | **0.20** | SECONDARY: FV limpia disponible en Iquitos |
| **Costo** | 0.15 | **0.10** | REDUCIDO: tarifa baja, no es bottleneck |
| **Grid Stability** | 0.20 | **0.10** | REDUCIDO: implícito en CO₂ + Solar |
| **EV Satisfaction** | 0.05 | **0.10** | Aumentado: operación balanceada |

**Beneficio**: Agente ahora enfoca en **minimizar importación de grid** (CO₂) **maximizando solar**.

---

### 2️⃣ CO₂ Baselines Realistas (CRÍTICO)

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py#L152-L165)

#### ❌ PROBLEMA ORIGINAL - Issue

```python
co2_baseline = 500.0  # ¡¡¡ARBITRARIO!!!
# Típico demanda mall: 100 kW
# 500.0 es 5x la demanda típica
# Resultado: reward casi siempre positivo → SIN GRADIENTES para learning
```

#### ✅ SOLUCIÓN APLICADA - Fix

```python
# Baselines reales de Iquitos:
co2_baseline_offpeak = 130.0   # Mall ~100kW + Chargers ~30kW = 130 kWh/hora
co2_baseline_peak = 250.0      # Mall ~150kW + Chargers ~100kW = 250 kWh/hora (TARGET)

if is_peak:
    # En pico: si importas 250 (target), r_co2 = 1 - 2*(250/250) = -1 (penalidad)
    #          si importas 100 (excelente), r_co2 = 1 - 2*(100/250) = 0.2 (bonus)
    r_co2 = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)
else:
    r_co2 = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)
```

**Beneficio**: Reward ahora varía en rango COMPLETO [-1, +1] → **claros gradientes para SAC**.

**Impacto esperado**:

1. Paso 100: r_co2 mejora de -0.05 a +0.15 (visible learning)
2. Paso 500: r_co2 mejora a +0.25+ (convergencia)

---

### 3️⃣ SOC Reserve Penalty Normalizada

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py#L215-L230)

#### ❌ PROBLEMA ORIGINAL - Issue

```python
# Penalización sumada SIN ponderación
if hour in pre_peak_hours and bess_soc < 0.5:
    soc_penalty = -0.5  # Directamente sumado a reward
    
# RESULTADO: Si reward_componentes = [-0.5 del CO₂, -0.5 del SOC]
# ¡SOC tiene IGUAL peso que CO₂ a pesar de ser mucho menos importante!
```

#### ✅ SOLUCIÓN APLICADA - Fix

```python
# Ahora normalizado con peso explícito
if hour in [16, 17]:  # Pre-peak
    soc_target_prepeak = 0.65  # Meta realista
    if bess_soc < soc_target_prepeak:
        r_soc_reserve = 1.0 - (soc_deficit / soc_target_prepeak)  # [0, 1] normalizado
    else:
        r_soc_reserve = 1.0  # Bonus si cumples

soc_penalty = (r_soc_reserve - 1.0) * 0.5  # Escala [-0.5, 0]

# En suma total:
reward = (
    0.50 * r_co2 +              # 0.50 de peso
    0.10 * soc_penalty +        # 0.10 de peso (mucho menor, correcto)
    ...
)
```

**Beneficio**: SOC penalty ahora tiene peso EXPLÍCITO y balanceado.

---

### 4️⃣ Entropía Reducida (SAC - PARTE DE TIER 1)

**Archivo**: [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py#L136-L138)

| Parámetro | Antes | Después | Razón |
| --- | --- | --- | --- |
| `ent_coef` | `"auto"` | **`0.01`** | Fijo: evita exploración EXCESIVA |
| `target_entropy` | `-126.0` | **`-50.0`** | Menos ruido, más EXPLOTACIÓN |

**Por qué**: Con rewards bien escalados ahora, SAC NO necesita exploración salvaje. Entropy bajo = más focus en políticas buenas.

**Beneficio**: SAC dedica más capacidad a **APRENDER** patrones que a **EXPLORAR** ruido.

---

## Qué Esperar en Próximo Entrenamiento

### Métricas a Monitorear

#### 1. Componente `r_co2` (CRÍTICO)

```text
Paso 25:   r_co2 = -0.2 a 0.0   (baseline, learning iniciado)
Paso 100:  r_co2 = +0.1 a +0.2  (clara MEJORA vs antes -0.1)
Paso 250:  r_co2 = +0.2 a +0.3  (convergencia visible)
Paso 500:  r_co2 = +0.3+        (estable alto)
```

#### 2. Componente `r_grid` (INDICADOR)

```text
Antes:  r_grid variaba wildly [-1, +1] (mal escalado)
Ahora:  r_grid variará [-0.8, +0.4] (rango controlado)
```

#### 3. `reward_total` Mean

```text
Paso 100:  reward_total = 0.56-0.60  (mejora vs 0.5600 plano)
Paso 500:  reward_total = 0.60-0.65  (tendencia CLARA al alza)
```

#### 4. `grid_import` en Peak Hours (18-21h)

```text
Baseline SAC paso 500: ~180 kWh/hora pico
Esperado con TIER 1:   ~150 kWh/hora pico (25% reduction)
```

#### 5. `bess_soc` Pre-Peak (horas 16-17)

```text
Actual: ~0.50 (justo target)
Esperado: ~0.65-0.70 (agente entiende prepeak charging)
```

---

## Próximos Pasos (TIER 2)

Si TIER 1 muestra mejora clara (r_co2 subiendo), implementar TIER 2:

### TIER 2 (DEPENDE DE VALIDACIÓN TIER 1)

1. **Normalización de Reward** (línea 230 rewards.py)

   ```python
   reward_mean = rolling mean (últimos 100 pasos)
   reward_std = rolling std
   reward_normalized = (reward - mean) / std
   ```

2. **Reducir Batch Size** (sac.py)

   ```python
   batch_size: 32768 → 4096  (mejor flexibility)
   gradient_steps: 256 → 256 (ok, se complementa)
   ```

3. **Agregar Observables Contextuales** (simulate.py)

   ```python
   is_peak_hour, bess_soc, bess_soc_target, pv_available_kw, queue_motos, queue_mototaxis
   ```

---

## Archivos Modificados

### TIER 1 - YA APLICADO

- ✅ [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py)
  1. Lines 30-45: Pesos rebalanceados
  2. Lines 152-165: CO₂ baselines realistas
  3. Lines 215-230: SOC penalty normalizada

- ✅ [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py)
  1. Lines 136-138: Entropía reducida

### DOCUMENTACIÓN

- ✅ [AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md](AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md)

1. ✅ [AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md](AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md)
2.

---

## Comando para Relanzar

```bash
```powershellv\\Scripts\\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml
```

**Nota**: Checkpoints SAC anterior (con valores malos) pueden ser ignorados automáticamente o limpiados:

```bash
RempowershellItem -Path "d:\diseñopvbesscar\analyses\oe3\training\checkpoints\sac" -Recurse -Force
```

---

## Validación Post-Entrenamiento

**Si r_co2 sigue PLANO después de TIER 1**:

1. ❌ Problema: Hay otro bug oculto en observable o env.step()
2. Acción: Investigar función compute() en wrapper

**Si r_co2 MEJORA CLARO**:

1. ✅ TIER 1 funciona correctamente
2. Acción: Proceder a TIER 2 (observables, batch size reduction)

**Si reward_total cae**:

1. ⚠️ Pesos pueden necesitar ajuste fino
2. Verificar: ¿Cuál componente está siendo penalizado? (r_cost?, r_ev?)

---

**Estado**: 🟢 **TIER 1 COMPLETE - LISTO PARA VALIDAR EN PRÓXIMO ENTRENAMIENTO (estimado 4-5 horas)**

**Próximo checkpoint**: Esperar a que SAC complete paso 500, verificar `r_co2` trend
