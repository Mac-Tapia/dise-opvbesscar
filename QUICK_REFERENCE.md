# QUICK REFERENCE: 6-FASES BESS v5.4
Tarjeta de Bolsillo | 2026-02-19

---

## 🚀 EJECUTA ESTO AHORA

```bash
# Terminal 1: Validar BESS
python scripts/validate_bess_6fases.py

# Terminal 2: Integrar balance.py
python scripts/integrate_bess_balance.py

# Terminal 3: Full pipeline
python scripts/run_complete_pipeline.py
```

**Tiempo total: ~10-15 minutos**

---

## 📊 LAS 6 FASES (INMUTABLE)

| FASE | CUÁNDO | QUÉ PASA |
|---|---|---|
| **1** | 6-9 AM | EV=0, BESS carga TODO PV |
| **2** | 9-22h, SOC<99% | EV máxima, BESS paralelo |
| **3** | 9-22h, SOC≥99% | BESS HOLDING (IDLE) |
| **4** | Cualquier hora, MALL>1900kW | BESS descarga para pico MALL |
| **5** | 9-22h, EV deficit>0 | BESS descarga: EV primero, MALL segundo |
| **6** | 22h-9 AM | BESS reposo total (SOC=20%) |

---

## ✅ ARCHIVOS GENERADOS

**Validador:**
- `scripts/validate_bess_6fases.py` ← Ejecuta BESS, valida 6-FASES

**Integrador:**
- `scripts/integrate_bess_balance.py` ← Sincroniza balance.py, genera gráficas

**Dataset:**
- `data/iquitos_ev_mall/bess_timeseries.csv` ← Salida (12 columnas, 8,760 filas)

**Gráficas:**
- `outputs/balance_energetico/*.png` ← 16 gráficas con 6-FASES

**Documentación:**
- `ARQUITECTURA_BESS_6FASES_FUNDACION_FIJA.md` ← Spec oficial
- `RESUMEN_EJECUTIVO_FASE_7_COMPLETADA.md` ← Resumen
- `CHECKLIST_EJECUCION_FASE_7.md` ← Guía paso a paso

---

## 🔐 LO QUE NO CAMBIA NUNCA

```
❌ Remover FASE
❌ Cambiar orden FASES
❌ Modificar prioridades (EV > MALL > RED)
❌ Cambiar ventanas horarias sin aprobación
❌ Sobreescribir lógica desde otro módulo
```

---

## ✨ LO QUE SÍ PUEDES CAMBIAR

```
✅ SOC min: ±5% (default 20%)
✅ Peak shaving threshold: ±100 kW (default 1900)
✅ Eficiencia BESS: ±2% (default 95%)
✅ Visualizaciones: colores, formatos, gráficas
✅ Métricas: agregar nuevas sin cambiar lógica)
```

---

## 📈 RESULTADOS ESPERADOS

| Métrica | Valor |
|---|---|
| CO₂ WITH SOLAR | ~190,000 kg/año |
| CO₂ WITHOUT SOLAR | ~640,000 kg/año |
| **CO₂ SAVINGS** | **~450,000 kg/año (70%)** |
| Solar self-consumption | ~65-70% |
| EV autosuficiencia | ~40-60% |
| BESS utilización | ~80% |

---

## 🐛 ERRORES COMUNES

| Error | Solución |
|---|---|
| ImportError en bess.py | Verificar `from __future__ import annotations` |
| FileNotFoundError: data/ | Crear archivos: solar_generation.csv, chargers_timeseries.csv, mall_demand.csv |
| "No module named src" | Ejecutar desde raíz: `cd d:\diseñopvbesscar` |
| KeyError: 'soc_percent' | Verificar que simulate_bess_solar_priority() devuelve esa columna |
| OutOfMemory RL training | Reducir n_steps o usar CPU |

---

## 📞 REFERENCIAS RÁPIDAS

**Implementación de 6-FASES:**
- Archivo: `src/dimensionamiento/oe2/disenobess/bess.py`
- Líneas: 986-1209
- Function: `simulate_bess_solar_priority()`

**Validación:**
- Archivo: `scripts/validate_bess_6fases.py`
- Genera: `bess_timeseries.csv`
- Audita: Todas 6-FASES + restricciones

**Integración:**
- Archivo: `scripts/integrate_bess_balance.py`
- Usa: Validador + BESS + balance.py
- Output: 16 gráficas PNG + dataset  
- Integración:**
- Archivo: `scripts/integrate_bess_balance.py`
- Usa: Validador + BESS + balance.py
- Output: 16 gráficas PNG + dataset

---

## 🎯 ESTADO ACTUAL

✅ **bess.py:** 6-FASES implementadas (líneas 986-1209)
✅ **Validador:** Listo en scripts/validate_bess_6fases.py
✅ **Integrador:** Listo en scripts/integrate_bess_balance.py
✅ **Docs:** ARQUITECTURA_BESS_6FASES_FUNDACION_FIJA.md
✅ **Checklist:** CHECKLIST_EJECUCION_FASE_7.md

**PRÓXIMO PASO:** Ejecutar los 3 scripts en secuencia ↑

---

**IMPRESA EN:** 2026-02-19
**VERSIÓN:** QUICK REFERENCE v1.0
