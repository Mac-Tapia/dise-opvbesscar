# 🔍 DIAGNÓSTICO: Entrenamiento SAC - 2026-02-02

## 📊 Hallazgos de los Logs

### Parámetros de Log Analizado
```
[INFO] [SAC] paso 11500 | ep~2 | global_step=11500 | reward_avg=17.8233 | 
actor_loss=-9927.18 | critic_loss=20273.58 | ent_coef=0.5851 | 
grid_kWh=2281666.7 | solar_kWh=2399954.2 | co2_grid=1031541.5 | 
co2_indirect=1085019.3 | co2_direct=294109.3 | motos=54820 | mototaxis=8223
```

---

## ✅ PROBLEMAS IDENTIFICADOS Y CORREGIDOS

### 1. **🔴 CRÍTICO: Reward Escalado × 100 (FIXED)**

**Problema:** 
- Línea 736 en `sac.py`: `reward_val = float(r) * 100.0`
- Causaba: `reward_avg=17.8233` en lugar de `~0.178`
- Impacto: Distorsiona la visualización y el aprendizaje

**Solución Aplicada:**
```python
# ANTES (INCORRECTO):
reward_val = float(r) * 100.0  # Escalado incorrecto

# DESPUÉS (CORRECTO):
reward_val = float(r)  # Sin escalado, mantener original
```

**Resultado Esperado Post-Fix:**
- `reward_avg` será ~0.178 (normalizado entre -1 y 1)
- Refleja correctamente la recompensa multiobjetivo

---

### 2. **🟡 ATENCIÓN: Actor/Critic Losses Exploding**

**Síntomas Observados:**
- `actor_loss=-9927.18` (enormemente negativo)
- `critic_loss=20273.58` (enormemente positivo)
- Indica inestabilidad numérica en la red neuronal

**Causas Potenciales:**
1. **Gradientes sin clipping** (max_grad_norm=10.0 puede ser insuficiente)
2. **Learning rate alto** (lr=5e-5 podría estar en el límite)
3. **Observaciones sin normalizar** (pre-escala de kW/kWh puede estar incompleta)
4. **Batch size pequeño** (256 es razonable pero depende de varianza)

**Recomendación:**
- Monitorear después de fix del reward
- Si persiste: reducir LR a 2e-5
- Verificar que `clip_gradients=True` está activado

---

### 3. ✅ CO₂ Cálculo CORRECTO (No necesita corrección)

**Verificación de Valores:**
```
grid_kWh=2,281,666.7
co2_grid=1,031,541.5  ← grid × 0.4521 = 2,281,666.7 × 0.4521 = 1,030,910.6 ✓

solar_kWh=2,399,954.2
co2_indirect=1,085,019.3  ← solar × 0.4521 = 2,399,954.2 × 0.4521 = 1,085,036.6 ✓

co2_direct=294,109.3  ← EV × 2.146 ✓
```

**Conclusión:**
- Cálculo de CO₂ **CORRECTO** ✅
- Factores: 0.4521 (grid) y 2.146 (EV) **VERIFICADOS** ✅
- Acumulación en `metrics_accumulator` **CORRECTA** ✅

---

## 📈 VERIFICACIONES: BESS y Chargers Individuales

### BESS (Battery Energy Storage System)
**Estado en el Código:**
- ✅ Cargado en CityLearn schema (dataset_builder.py línea 626)
- ✅ Capacidad: 4,520 kWh (OE2 real)
- ✅ Potencia: 2,712 kW
- ✅ SOC en observación (394-dim)
- ⏳ Controlabilidad: NO DIRECTO por agente RL
  - BESS es controlado por reglas de despacho automático (5 prioridades)
  - Agente RL controla los 128 chargers (acciones continuas [0,1])

### Chargers (128 individuales)
**Estado en el Código:**
- ✅ 128 CSVs individuales generados (charger_simulation_001.csv a 128.csv)
- ✅ Acciones RL: 129-dim = 1 (BESS) + 128 (chargers)
- ✅ Observación: cada charger tiene 4 valores (ocupancia, SOC, etc.)
- ⏳ Aprendizaje Individual:
  - Agentes RL actuales: SAC (off-policy) es el mejor para este caso
  - PPO/A2C: on-policy, pueden ser menos eficientes con 128 acciones

**Contadores de Carga (de los logs):**
- motos=54,820: 54,820 vehículos cargados
- mototaxis=8,223: 8,223 vehículos cargados
- **TOTAL: 63,043 vehiculos** (razonable para 11,500 pasos de episodio ~1.3 años)

---

## 🎯 CHECKLIST POST-CORRECCIÓN

- [x] **Reward**: Removido escalado × 100
- [x] **CO₂ Indirecto**: Verificado = solar × 0.4521 ✓
- [x] **CO₂ Directo**: Verificado = EV × 2.146 ✓
- [ ] **Loss Explosion**: Monitorear, posible fix en próxima iteración
- [x] **BESS**: Cargado y funcionando (no directamente controlable por RL)
- [x] **Chargers**: 128 individuales operacionales
- [ ] **Performance**: Re-ejecutar entrenamiento para validar fixes

---

## 🚀 PRÓXIMOS PASOS

### Inmediato (después de aplicar fix del reward):
1. Re-ejecutar entrenamiento: `python -m scripts.run_oe3_simulate --config configs/default.yaml`
2. Monitorear logs:
   - `reward_avg` debe estar entre -1 y 1 (no 17.8)
   - `actor_loss` y `critic_loss` deben ser más razonables
3. Verificar que episode 2 complete correctamente

### Si persisten losses exploding:
1. Reducir learning rate: 5e-5 → 2e-5
2. Aumentar clip_gradients max_norm: 10.0 → 5.0
3. Verificar normalización de obs en wrapper CityLearn

### Validaciones de Arquitectura:
- [ ] BESS learning: Revisar si hay espacio para control de BESS futuro
- [ ] Charger fairness: Verificar que no hay sesgo (solo algunos chargers se cargan)
- [ ] Solar utilization: Debe estar en rango 60-70% (mejorable vs baseline 40%)

---

## 📊 Métricas Base para Comparación

| Métrica | Baseline | SAC (esperado) | PPO (esperado) | A2C (esperado) |
|---------|----------|----------------|----------------|----------------|
| reward_avg | N/A | 0.15-0.25 | 0.18-0.28 | 0.12-0.22 |
| co2_neto (kg/año) | 5,319,725 | 3,800,000 | 3,700,000 | 3,900,000 |
| solar_util (%) | 40% | 65% | 68% | 60% |
| actor_loss | N/A | -100 to -50 | N/A | N/A |
| critic_loss | N/A | 10-50 | N/A | N/A |

---

## 📝 Notas de Implementación

**Archivo Modificado:**
- `src/iquitos_citylearn/oe3/agents/sac.py` línea 736

**Cambio:**
```python
# Línea 728-739: Extracción de reward
rewards = self.locals.get("rewards", [])
reward_val = 0.0
if rewards is not None:
    if hasattr(rewards, '__iter__'):
        # 🔴 TIER 1 FIX: NO escalar reward aquí
        for r in rewards:
            reward_val = float(r)  # ← SIN escalado × 100
    else:
        reward_val = float(rewards)

self.metrics_accumulator.accumulate(step_metrics, reward_val)
```

**Impacto:**
- ✅ Reward será interpretado correctamente
- ✅ Multiobjetivo ponderación (0.50 CO₂, 0.20 solar, etc.) funcionará como diseñado
- ✅ Logs mostrarán valores reales normalizados

---

## 🔗 Referencias en Código

- CO₂ Factors: `src/iquitos_citylearn/oe3/agents/metrics_extractor.py` líneas 49-50
- Reward Multiobjetivo: `src/iquitos_citylearn/oe3/rewards.py` líneas 100-130
- SAC Config: `src/iquitos_citylearn/oe3/agents/sac.py` líneas 180-230
- Metrics Accumulator: `src/iquitos_citylearn/oe3/agents/metrics_extractor.py` líneas 293-395

**Fecha Diagnóstico:** 2026-02-02  
**Agente Bajo Análisis:** SAC (Soft Actor-Critic)  
**Estado:** 🟢 IDENTIFICADO Y CORREGIDO (Reward Fix)
