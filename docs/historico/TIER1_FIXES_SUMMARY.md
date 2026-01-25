# ✅ TIER 1 FIXES APPLIED - REWARDS & HYPERPARAMS AUDIT

**Fecha**: 2026-01-18 19:15
**Commit**: `3d41ca7f`
**Status**: 🟢 TIER 1 COMPLETE - Listo para relanzar entrenamiento

---

## Resumen de Cambios

Se identificaron y **corrigieron 4 problemas críticos** que impedían que SAC
aprendiera:

### 1️⃣ Pesos Multiobjetivo Rebalanceados

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py][ref]

<!-- markdownlint-disable MD013 -->
[ref]: src/iquitos_citylearn/oe3/rewards.py#L30 | Métrica | Antes | Después | Razón | | --- | --- | --- | --- | | **CO₂** | 0.45 | **0.50** | PRIMARY: matriz térmica... | | **Solar** | 0.15 | **0.20** | SECONDARY: FV limpia... | | **Costo** | 0.15 | **0.10** | REDUCIDO: tarifa baja, no es bottleneck | | **Grid Stability** | 0.20 | **0.10** | REDUCIDO: implícito en CO₂ + Solar | | **EV Satisfaction** | 0.05 | **0.10** | Aumentado: operación balanceada | **Beneficio**: Agente ahora enfoca en **minimizar importación de grid** (CO₂)
**maximizando solar**.

---

### 2️⃣ CO₂ Baselines Realistas (CRÍTICO)

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py][ref]

[ref]: src/iquitos_citylearn/oe3/rewards.py#L152-L165

#### ❌ PROBLEMA ORIGINAL - Issue

<!-- markdownlint-disable MD013 -->
```python
co2_baseline = 500.0  # ¡¡¡ARBITRARIO!!!
# Típico demanda mall: 100 kW
# 500.0 es 5x la demanda típica
# Resultado: reward casi siempre positivo → SIN GRADIENTES para learning
```text
<!-- markdownlint-enable MD013 -->

#### ✅ SOLUCIÓN APLICADA - Fix

<!-- markdownlint-disable MD013 -->
```python
# Baselines reales de Iquitos:
co2_baseline_offpeak = 130.0   # Mall ~100kW + Chargers ~30kW = 130 kWh...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

**Beneficio**: Reward ahora varía en rango COMPLETO [-1, +1] → **claros
gradientes para SAC**.

**Impacto esperado**:

1. Paso 100: r_co2 mejora de -0.05 a +0.15 (visible learning)
2. Paso 500: r_co2 mejora a +0.25+ (convergencia)

---

### 3️⃣ SOC Reserve Penalty Normalizada

**Archivo**: [src/iquitos_citylearn/oe3/rewards.py][ref]

[ref]: src/iquitos_citylearn/oe3/rewards.py#L215-L230

#### ❌ PROBLEMA ORIGINAL - Issue (2)

<!-- markdownlint-disable MD013 -->
```python
# Penalización sumada SIN ponderación
if hour in pre_peak_hours and bess_soc < 0.5:
    soc_penalty = -0.5  # Directamente sumado a reward

# RESULTADO: Si reward_componentes = [-0.5 del CO₂, -0.5 del SOC]
# ¡SOC tiene IGUAL peso que CO₂ a pesar de ser mucho menos importante!
```text
<!-- markdownlint-enable MD013 -->

#### ✅ SOLUCIÓN APLICADA - Fix (2)

<!-- markdownlint-disable MD013 -->
```pyth...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

**Beneficio**: SOC penalty ahora tiene peso EXPLÍCITO y balanceado.

---

### 4️⃣ Entropía Reducida (SAC - PARTE DE TIER 1)

**Archivo**: [src/iquitos_citylearn/oe3/agents/sac.py][ref]

<!-- markdownlint-disable MD013 -->
[ref]: src/iquitos_citylearn/oe3/agents/sac.py#L136-L138 | Parámetro | Antes | Después | Razón | | --- | --- | --- | --- | | `ent_coef` | `"auto"` | **`0.01`** | Fijo: evita exploración EXCESIVA | | `target_entropy` | `-126.0` | **`-50.0`** | Menos ruido, más EXPLOTACIÓN | **Por qué**: Con rewards bien escalados ahora, SAC NO necesita exploración
salvaje. Entropy bajo = más focus en políticas buenas.

**Beneficio**: SAC dedica más capacidad a **APRENDER** patrones que a
**EXPLORAR** ruido.

---

## Qué Esperar en Próximo Entrenamiento

### Métricas a Monitorear

#### 1. Componente `r_co2` (CRÍTICO)

<!-- markdownlint-disable MD013 -->
```text
Paso 25:   r_co2 = -0.2 a 0.0   (baseline, learning iniciado)
Paso 100:  r_co2 = +0.1 a +0.2  (clara MEJORA vs antes -0.1)
Paso 250:  r_co2 = +0.2 a +0.3  (convergencia visible)
Paso 500:  r_co2 = +0.3+        (estable alto)
```text
<!-- markdownlint-enable MD013 -->

#### 2. Componente `r_grid` (INDICADOR)

<!-- markdownlint-disable MD013 -->
```text
Antes:  r_grid variaba wildly [-1, +1] (mal es...
```

[Ver código completo en GitHub]text
Paso 100:  reward_total = 0.56-0.60  (mejora vs 0.5600 plano)
Paso 500:  reward_total = 0.60-0.65  (tendencia CLARA al alza)
```text
<!-- markdownlint-enable MD013 -->

#### 4. `grid_import` en Peak Hours (18-21h)

<!-- markdownlint-disable MD013 -->
```text
Baseline SAC paso 500: ~180 kWh/hora pico
Esperado con TIER 1:   ~150 kWh/hora pico (25% reduction)
```text
<!-- markdownlint-enable MD013 -->

#### 5. `bess_soc` Pre-Peak (horas 16-17)

<!-- markdownlint-disable MD013 -->
```text
Actual: ~0.50 (justo target)
Esperado: ~0.6...
```

[Ver código completo en GitHub]bash
```powershellv\\Scripts\\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml
<!-- markdownlint-enable MD013 -->
<!-- markdownlint-disable MD013 -->
```text

**Nota**: Checkpoints SAC anterior (con valores malos) pueden ser ignorados automáticamente o limpiados:

```bash
<!-- markdownlint-enable MD013 -->
RempowershellItem -Path
"d:\diseñopvbesscar\analyses\oe3\training\checkpoints\sac" -Recurse -Force
<!-- markdownlint-disable MD013 -->
```text

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

[url1]: src/iquitos_citylearn/oe3/agents/sac.py
[url2]: AUDIT_REWARDS_OBSERVABLES_HYPERPARAMS.md