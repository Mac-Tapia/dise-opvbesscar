# 🚀 PRÓXIMOS PASOS - PLAN DE EJECUCIÓN

**Creado:** 2026-02-17  
**Estado del Proyecto:** ✅ Auditoría completada  
**Recomendación:** Ejecutar AC-1 y AC-2 antes de entrenar

---

## 📋 ORDEN DE EJECUCIÓN RECOMENDADO

### FASE 1: FIX CRÍTICOS (Hoy - 2026-02-17)

#### ✅ AC-1: Ruta Solar en sac_optimized.json
- **Status:** ✅ COMPLETADO
- **Cambio:** `data/oe2/Generacionsolar/...` → `data/interim/oe2/solar/pv_generation_citylearn_v2.csv`
- **Verificación:** `git diff configs/sac_optimized.json` ✓

---

### FASE 2: VALIDACIONES CRÍTICAS (Mañana - 2026-02-18)

#### AC-2: Validación Cruzada SOC Tracking (URGENTE)

**Objetivo:** Verificar que PPO/A2C/SAC producen **conteos IDÉNTICOS** de vehículos por SOC

**Implementación:**

```bash
# 1. Train PPO para 1 episodio (8,760 steps = 1 hora script)
python scripts/train/train_ppo_multiobjetivo.py \
  --episodes 1 \
  --output outputs/validate_ppo_episode1

# 2. Train A2C para mismo
python scripts/train/train_a2c_multiobjetivo.py \
  --episodes 1 \
  --output outputs/validate_a2c_episode1

# 3. Train SAC para mismo
python scripts/train/train_sac_multiobjetivo.py \
  --episodes 1 \
  --output outputs/validate_sac_episode1

# 4. Comparar resultados
python scripts/validate_cross_agent_consistency.py \
  --ppo outputs/validate_ppo_episode1/result_ppo.json \
  --a2c outputs/validate_a2c_episode1/result_a2c.json \
  --sac outputs/validate_sac_episode1/result_sac.json \
  --tolerance 0.05  # 5% difference tolerance
```

**Métricas a Comparar:**
1. **Dataset Loads** (deben ser IDÉNTICOS):
   - Solar: sum, mean, shape
   - Chargers: shape (8760, 38), sum per socket
   - BESS: sum, mean SOC
   - Mall: sum

2. **Energy Balance**: solar + grid_import = ev + mall + losses
   - PPO formula
   - A2C formula  
   - SAC formula
   - Tolerance: ±0.01%

3. **Vehículos por SOC** (CRÍTICO):
   - motos_10, motos_20, ..., motos_100
   - mototaxis_10, ..., mototaxis_100
   - Tolerance: ±5% (se permite porque metodología diferente)

4. **CO₂ Calculations**:
   - co2_grid_kg (debe ser idéntico)
   - co2_avoided_indirect_kg (debe ser nearly idéntico, ±0.5%)
   - co2_avoided_direct_kg (puede variar ±2% por EV dispatch)

5. **KPI Metrics**:
   - grid_import_kwh
   - bess_charge/discharge
   - Cost calculation
   - Tolerance: ±2%

**Deliverable:**
```
VALIDACION_CRUZADA_PPO_A2C_SAC_2026-02-17.md
├─ Dataset validation (5 sources)
├─ Energy balance check
├─ SOC vehicle tracking comparison
├─ CO2 calculation verification
├─ KPI metrics comparison
└─ Conclusion: PASS ✓ / FAIL ✗ with details
```

**Resultado Esperado:**
- Si **tolerance met** → ✅ Agentes sincronizados, OK para producción
- Si **tolerance exceeded** → 🔴 Problema detectado, investigación necesaria

---

### FASE 3: ENTRENAMIENTOS INICIALES (2026-02-18 PM)

Una vez completados AC-1 y AC-2, ejecutar:

```bash
# Train todos los 3 agentes en paralelo (si GPU lo permite)
# O secuencial (más seguro)

# PPO (4-5 min)
python scripts/train/train_ppo_multiobjetivo.py --episodes 10

# A2C (3-4 min)  
python scripts/train/train_a2c_multiobjetivo.py --episodes 10

# SAC (8-10 min)
python scripts/train/train_sac_multiobjetivo.py --episodes 10

# Total: ~20-25 minutos (secuencial) o ~10 minutos (GPU paralelo)
```

**Output esperado:**
- 3 carpetas: `outputs/ppo_training/`, `outputs/a2c_training/`, `outputs/sac_training/`
- Cada carpeta contiene:
  - `result_{agent}.json` (metrics resumen)
  - `timeseries_{agent}.csv` (step-by-step data)
  - `trace_{agent}.csv` (detailed trace)
  - `{agent}_dashboard.png` (résumé visual)
  - 6+ gráficas KPI adicionales

---

### FASE 4: EVALUACIÓN COMPARATIVA (2026-02-19)

```bash
# Generar matriz de comparación
python scripts/compare_agents_final.py \
  --ppo outputs/ppo_training/result_ppo.json \
  --a2c outputs/a2c_training/result_a2c.json \
  --sac outputs/sac_training/result_sac.json \
  --output reports/COMPARACION_FINAL_3AGENTES.md
```

**Matriz esperada:**
```
| Métrica | PPO | A2C | SAC | Winner |
|---------|-----|-----|-----|--------|
| Avg Reward | X | Y | Z | A2C? |
| CO₂ Grid (kg) | X | Y | Z | ↓ Lower |
| Solar % | X% | Y% | Z% | ↑ Higher |
| Cost (USD) | X | Y | Z | ↓ Lower |
| Ramping (kW) | X | Y | Z | ↓ Lower |
| Training Speed (sps) | 350 | 450 | 175 | A2C ✓ |
...
```

**Conclusión esperada:**
- A2C probablemente ganador por **velocidad (450 sps) + reward comparable**
- SAC mejor **convergencia asintótica** pero más lento
- PPO buen balance entre velocidad y estabilidad

---

## 📅 TIMELINE ESTIMADO

| Fase | Tarea | Duración | Fecha |
|------|-------|----------|-------|
| **1** | Fixes críticos (AC-1) | ✅ 0 h | 2026-02-17 |
| **2a** | Train 3×1 episode+logs | 2-3 h | 2026-02-18 AM |
| **2b** | Validación cruzada SOC | 1 h | 2026-02-18 AM |
| **3** | Training final (3×10 ep) | 0.5 h | 2026-02-18 PM |
| **4** | Evaluación + reportes | 1-2 h | 2026-02-19 |
| **5** | (Optional) Consolidar SAC | 0.5 h | 2026-02-19 |
| **6** | (Optional) Config centralized | 2 h | 2026-02-20 |

**Total:** ~7-8 horas de ejecución activa + tiempos de espera de GPU

---

## 🎯 SUCCESS CRITERIA

El proyecto está **LISTO PARA PRODUCCIÓN** cuando:

### Criterios Obligatorios
- [x] AC-1 completado (ruta solar SAC)
- [ ] AC-2 completado (validación cruzada SOC)
- [ ] Todos los datasets cargan correctamente (8,760 rows)
- [ ] Conteos CO₂ dentro de tolerancia ±0.1%
- [ ] SOC vehicle tracking dentro de tolerancia ±5%
- [ ] Gráficas generan sin errores (13-15 PNG por agente)

### Criterios de Calidad
- [ ] Training stabil speeds: PPO 350+ sps, A2C 400+ sps, SAC 150+ sps
- [ ] Reward curves monotónicamente decreciendo en loss (stable training)
- [ ] KPI improvements visible: CO₂ ↓, consumption ↓, peak ↓
- [ ] No NaN/Inf values en métricas

### Criterios Extras
- [ ] AC-3 completado (config centralizado) - _Nice to have_
- [ ] AC-4 completado (SAC versions consolidadas) - _Nice to have_
- [ ] Comparison matrix generada - _Nice to have_

---

## 📌 NOTAS IMPORTANTES

### Dataset Consistency
- ✅ **PPO/A2C:** Uso VehicleChargingSimulator con escenarios pre-definidos
- 🟡 **SAC:** Uso VehicleSOCTracker con spawning dinámico
- ⚠️ Necesario validación cruzada (AC-2) para asegurar conteos equivalentes

### Performance Expectations
- **Baseline (uncontrolled):** ~10,200 kg CO₂/year
- **RL Agents (expected):** 
  - SAC: ~7,500 kg CO₂/year (-26%)
  - PPO: ~7,200 kg CO₂/year (-29%)
  - A2C: ~7,800 kg CO₂/year (-24%)

### Troubleshooting
- Si solar data no carga → verificar ruta en código (línea 2952 PPO, 1885 A2C, 630 SAC)
- Si chargers no carga → verificar 38 sockets en v3.csv
- Si SAC lento → normal, es off-policy (8-10 min vs 3-5 min)

---

## 🔗 REFERENCIAS

- **Auditoría Completa:** `AUDITORIA_COMPLETA_PROYECTO_2026-02-17.md`
- **Validaciones Previas:** `VALIDACION_COLUMNAS_DATASETS_2026-02-14.md`
- **Sincronización PPO↔A2C:** `VERIFICACION_SINCRONIZACION_PPO_A2C_2026-02-14.md`
- **Flow Diagrams:** `MAPA_FLUJO_DATASETS_BESS_2026-02-14.md`

