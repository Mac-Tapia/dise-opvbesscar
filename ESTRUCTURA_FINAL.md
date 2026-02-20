# ESTRUCTURA FINAL - SIN DUPLICIDADES
## Flujo Correcto: BESS → DATASET → GRÁFICAS

---

## ✅ ARCHIVOS QUE EXISTEN Y DEBEN EXISTIR

### 1. **bess.py** (ÚNICO archivo de simulación)
**Ubicación:** `src/dimensionamiento/oe2/disenobess/bess.py`

**Responsabilidad:**
- ✅ Simula operación BESS con **6 FASES inmutables** (líneas 986-1209)
- ✅ Calcula flujos energéticos (PV, EV, MALL, RED)
- ✅ Genera **dataset**: `bess_timeseries.csv` (8,760 × 12+ columnas)

**Función principal:**
```python
simulate_bess_solar_priority(pv_kwh, ev_kwh, mall_kwh)
→ retorna: (DataFrame BESS, métricas)
```

**Output:**
- `data/iquitos_ev_mall/bess_timeseries.csv`

---

### 2. **balance.py** (ÚNICO archivo de visualización)
**Ubicación:** `src/dimensionamiento/oe2/balance_energetico/balance.py`

**Responsabilidad:**
- ✅ LEE `bess_timeseries.csv` (dataset del BESS)
- ✅ GENERA **16 gráficas PNG** (visualización)

**Función principal:**
```python
BalanceEnergeticoSystem(df_bess, config).plot_energy_balance(out_dir)
→ genera: 16 gráficas PNG
```

**Output:**
- `outputs/balance_energetico/*.png` (16 archivos)

---

## 🚀 FLUJO DE USO (CORRECTO)

```
PASO 1: Ejecutar bess.py
├─ Carga: PV, EV, MALL (8,760 horas)
├─ Simula: 6 FASES
└─ Genera: bess_timeseries.csv

PASO 2: Ejecutar balance.py
├─ Lee: bess_timeseries.csv
├─ Grafica: 16 PNG
└─ Guarda: outputs/balance_energetico/
```

---

## ❌ ARCHIVOS ELIMINADOS (NO USAR)

- ❌ `validate_bess_6fases.py` (innecesario)
- ❌ `run_bess_balance_pipeline.py` (innecesario)
- ❌ `generate_bess_graphics.py` (duplica balance.py)
- ❌ `integrate_bess_balance.py` (confuso)
- ❌ Documentos de FASE 7 (muy verbose)

---

## ✅ 6 FASES (DENTRO DE BESS.PY)

Las 6 FASES están **implementadas SOLO en bess.py** (líneas 986-1209):

1. **FASE 1** (6-9 AM): EV=0, BESS carga TODO PV
2. **FASE 2** (9-22h, SOC<99%): EV máxima, BESS paralelo
3. **FASE 3** (SOC≥99%): HOLDING IDLE
4. **FASE 4** (MALL>1900kW): Peak shaving
5. **FASE 5** (EV deficit): Dual descarga
6. **FASE 6** (22h-9 AM): Reposo IDLE

---

## 🎯 PRÓXIMO PASO

Cuando el usuario quiera:
1. **Generar dataset**: Ejecuta `bess.py`
2. **Visualizar**: Ejecuta `balance.py`

No hay scripts intermedios. Punto.
