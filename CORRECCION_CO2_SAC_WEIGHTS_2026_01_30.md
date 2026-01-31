# CORRECCIÓN CRÍTICA: PROBLEMA CO2 SAC - 2026-01-30

## 🚨 PROBLEMA IDENTIFICADO

**SAC incrementó CO2 en +7% vs baseline** (5.98M vs 5.59M kg)

### Causas Raíz

1. **Weight de CO2 insuficiente:** 0.50 no es suficiente para priorizar CO2 sobre solar
2. **Weight de solar demasiado alto:** 0.20 compite con CO2 y gana en ciertos timesteps
3. **Convergencia prematura:** SAC converge a óptimo local que maximiza solar pero incrementa grid

### Evidencia

```
SAC Results (3 episodios):
- Grid Import: 12,824,346 kWh (+3.7% vs baseline)
- CO2: 5,980,688 kg (+7.0% vs baseline)
- Solar: 8,030 kWh (+316% vs baseline)
- Reward: 2609.45 (idéntico en 3 episodios)
```

**Diagnóstico:** SAC sobre-optimiza solar (weight 0.20) en detrimento de CO2 (weight 0.50)

---

## ✅ SOLUCIÓN APLICADA

### Cambios en `configs/default.yaml`

**ANTES:**
```yaml
multi_objective_weights:
  co2: 0.50      # Insuficiente
  solar: 0.20    # Compite con CO2
  cost: 0.15     # Innecesario (tarifa baja)
  ev: 0.10
  grid: 0.05
```

**DESPUÉS:**
```yaml
multi_objective_weights:
  co2: 0.75      # ✓ INCREMENTADO +50% (0.50→0.75)
  solar: 0.10    # ✓ REDUCIDO -50% (0.20→0.10)
  cost: 0.05     # ✓ REDUCIDO -67% (0.15→0.05)
  ev: 0.05       # ✓ REDUCIDO -50% (0.10→0.05)
  grid: 0.05     # Mantiene estabilidad mínima
```

### Justificación Matemática

- **CO2 = 0.75:** Domina el 75% de la reward function
- **Solar = 0.10:** Secundario, solo bonus cuando CO2 ya está minimizado
- **Cost = 0.05:** Tarifa de Iquitos es 0.20 USD/kWh (muy baja), no es constraint
- **EV + Grid = 0.10:** Básico operacional

### Impacto Esperado

Con `co2_weight = 0.75`:
- Agente prioriza **minimizar grid_import** sobre todo
- Solar solo se maximiza si **NO incrementa grid_import**
- Reducción esperada CO2: **-15% a -25%** vs baseline (vs +7% actual)

---

## 🔧 CAMBIOS TÉCNICOS APLICADOS

### 1. A2C Weights (`evaluation.a2c.multi_objective_weights`)
```diff
- co2: 0.5
+ co2: 0.75   # ✓ INCREMENTADO
- cost: 0.15
+ cost: 0.05  # ✓ REDUCIDO
- solar: 0.2
+ solar: 0.10 # ✓ REDUCIDO
```

### 2. PPO Weights (`evaluation.ppo.multi_objective_weights`)
```diff
- co2: 0.50
+ co2: 0.75   # ✓ INCREMENTADO
- cost: 0.15
+ cost: 0.05  # ✓ REDUCIDO
- solar: 0.20
+ solar: 0.10 # ✓ REDUCIDO
```

### 3. SAC Weights (`evaluation.sac.multi_objective_weights`)
```diff
- co2: 0.5
+ co2: 0.75   # ✓ INCREMENTADO
- cost: 0.15
+ cost: 0.05  # ✓ REDUCIDO
- solar: 0.2
+ solar: 0.10 # ✓ REDUCIDO
```

---

## 📊 VALIDACIÓN MATEMÁTICA

### Reward Function (simplified)

**ANTES:**
```
R = 0.50*r_co2 + 0.20*r_solar + 0.15*r_cost + 0.10*r_ev + 0.05*r_grid
```

Si `r_co2 = -0.5` (grid alto) y `r_solar = +1.0` (solar máximo):
```
R = 0.50*(-0.5) + 0.20*(+1.0) + ... = -0.25 + 0.20 + ... = cerca de 0
```
→ Agente **tolera penalización CO2** por bonus solar

**DESPUÉS:**
```
R = 0.75*r_co2 + 0.10*r_solar + 0.05*r_cost + 0.05*r_ev + 0.05*r_grid
```

Mismo escenario:
```
R = 0.75*(-0.5) + 0.10*(+1.0) + ... = -0.375 + 0.10 + ... = cerca de -0.25
```
→ Agente **NO tolera penalización CO2**, debe reducir grid_import primero

---

## 🚀 PRÓXIMOS PASOS

1. **Re-entrenar los 3 agentes** con nuevos weights
2. **Comparar resultados:**
   - SAC nuevo vs SAC antiguo
   - Verificar reducción CO2 > baseline
3. **Documentar mejora** en reporte final

---

## 📁 ARCHIVOS MODIFICADOS

- `configs/default.yaml` (3 secciones de weights corregidas)
- Este documento: `CORRECCION_CO2_SAC_WEIGHTS_2026_01_30.md`

---

**Fecha de corrección:** 2026-01-30 17:XX:XX  
**Estado:** ✓ Aplicado, listo para re-entrenamiento
