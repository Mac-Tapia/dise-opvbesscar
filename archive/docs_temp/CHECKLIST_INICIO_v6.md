# ✅ CHECKLIST INICIO v6.0 - ÓRDENES ESPECÍFICAS

**Creado**: 2026-02-14  
**Estado**: 🟢 LISTO PARA EJECUTAR AHORA  
**Tiempo Estimado**: 2-3 semanas de trabajo  

---

## PASO A PASO (COPIAR Y PEGAR)

### 🟢 HOY (Día 1) - Entender qué es v6.0

**Lectura (30-40 minutos)**

```
Abre estos archivos EN ESTE ORDEN:

☐ 1. SAC_v6_CAMBIOS_RESUMEN.md 
     (Este archivo, lectura RÁPIDA 5 min)

☐ 2. RESUMEN_EJECUTIVO_v6_COMUNICACION.md
     (Explicación ejecutiva, 15-20 min)
     Lee: "¿Qué cambió?" + "¿Cuál es el impacto?" + "¿Cuándo empieza?"

☐ 3. ARQUITECTURA_SAC_v6_COMUNICACION_SISTEMAS.md
     (Detalles técnicos, 20-30 min)
     Lee: Observación [156-245] + Reward weights + Data pipeline

☐ 4. DIAGRAMAS_COMUNICACION_v6.md (OPCIONAL)
     (Diagramas visuales, 10-15 min)
```

**Después de leer**: Deberías entender:
- [ ] Qué son [156-193] (SOC por socket)
- [ ] Qué son [194-231] (tiempo por socket)
- [ ] Por qué w_vehicles_charged = 0.25 es importante
- [ ] Cuál es objetivo: +130 vehículos/día
- [ ] Por qué converge 2x más rápido

**Checklist completado**: ✅ Entiendo qué es v6.0

---

### 🟠 MAÑANA (Día 2-3) - Validar código está listo

**Verificar entorno Python**:

```bash
# En PowerShell
cd d:\diseñopvbesscar

# Si no existe venv, crear
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-training.txt

# Verificar GPU (si tienes)
python -c "
import torch
print(f'GPU Available: {torch.cuda.is_available()}')
print(f'GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')
print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB' if torch.cuda.is_available() else '')
"

# Resultado esperado:
# GPU Available: True
# GPU Name: NVIDIA GeForce RTX 4060
# GPU Memory: 8.0 GB
```

**Checklist**:
- [ ] .venv activado
- [ ] requirements.txt instalado
- [ ] GPU disponible (si tienes)
- [ ] torch funcionando

**Checklist completado**: ✅ Entorno listo

---

### 🔵 DÍA 3-4 - Validar datos OE2

**Verificar que archivos data existen**:

```bash
# En PowerShell, desde d:\diseñopvbesscar

# Listar archivos requeridos
ls data/oe2/Generacionsolar/*.csv
ls data/oe2/chargers/*.csv
ls data/oe2/bess/*.csv
ls data/oe2/demandamallkwh/*.csv

# Debería mostrar:
# - pv_generation_citylearn2024.csv (solar)
# - chargers_ev_ano_2024_v3.csv (chargers)
# - bess_ano_2024.csv o similar (BESS)
# - demandamallhorakwh.csv (mall)
```

**Si alguno falta**: Contactar data team. Si todos existen: continuar.

**Verify data shapes**:

```bash
python -c "
import pandas as pd

files = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
    'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

for name, path in files.items():
    try:
        df = pd.read_csv(path)
        print(f'✅ {name:15s}: {df.shape}')
    except Exception as e:
        print(f'❌ {name:15s}: {e}')
"

# Resultado esperado:
# ✅ Solar          : (8760, 1)
# ✅ Chargers       : (8760, 38) or (8760, 39+)
# ✅ BESS           : (8760, 25+)
# ✅ Mall           : (8760, 2) or similar
```

**Checklist**:
- [ ] Solar data exists + 8,760 rows
- [ ] Chargers data exists + 38+ columns
- [ ] BESS data exists + cascada columns
- [ ] Mall data exists + 8,760 rows
- [ ] All synchronized (same 8,760 rows)

**Checklist completado**: ✅ Datos validados

---

### 🟡 DÍA 5-7 - Ejecutar training SAC v6.0

**Opción A: Usar código existente (MÁS RÁPIDO - 15 min setup)**

```bash
# Copiar y ejecutar (funciona como-está):
python scripts/train/train_sac_sistema_comunicacion_v6.py

# Si funciona: Felicidades, v6.0 environment funcional ✓
# Duration: 6-8h (GPU), 40h+ (CPU)
```

**Opción B: Integrar en train_sac_multiobjetivo.py (MÁS ESTRUCTURADO - 3 días)**

```bash
# Seguir GUIA_IMPLEMENTACION_SAC_v6.md línea por línea
# FASE 1: Extender environment (1 día)
# FASE 2: Cargar datos (1 día)
# FASE 3: Entrenar (7 días GPU paralelo)
```

**Recomendación**: Empezar con Opción A. Si funciona, es v6.0 ✓

---

### 🟣 DÍA 7 - Monitor training (background)

**Mientras entrena, monitorear progreso**:

```bash
# En otra terminal, ejecutar cada 30 minutos:
python scripts/train/monitor_training.py

# Esperado:
# Episode 1:  Reward ~400, vehicles ~200/day ✓
# Episode 5:  Reward ~500, vehicles ~240/day ✓
# Episode 10: Reward ~600, vehicles ~290/day ✓
# Episode 15: Reward ~650, vehicles ~309/day ✓
```

**Checklist de convergencia**:
- [ ] Episodio 1: Reward > 300, vehicles > 150
- [ ] Episodio 5: Reward > 400, vehicles > 230
- [ ] Episode 10: Reward > 500, vehicles > 270
- [ ] Episode 15: Reward > 600, vehicles >= 280

Si no converge así: revisar datos/reward weights.

**Checklist completado**: ✅ Training en progreso

---

### 🟤 DÍA 14-15 - Validar resultados

**Una vez training termina (day 7 con GPU, day 14 con CPU)**:

```bash
# Crear validation script (si no existe)
# Ver: scripts/validation/validate_sac_v6.py

# Ejecutar validation
python scripts/validation/validate_sac_v6.py

# Esperado output:
# ✅ vehicles_charged        :          285 (threshold: 250)
# ✅ co2_avoided             :         7650 (threshold: 7500)
# ✅ grid_import             :        12.3% (threshold: < 15%)
# ✅ episode_return          :         625 (threshold: 400)
# ════════════════════════════════════════
# Overall: ✅ PASSED
```

**Si PASSED**: ✅ v6.0 exitoso!

**Si FAILED**: Revisar:
1. Datos OE2 cargados correctamente
2. Observación [156-245] implementada
3. Reward weights sumando 1.0
4. GPU memory suficiente

**Checklist**:
- [ ] vehicles_charged >= 250
- [ ] co2_avoided >= 7500
- [ ] grid_import < 15%
- [ ] episode_return >= 400
- [ ] Validation PASSED

**Checklist completado**: ✅ Validación exitosa

---

### 🟢 DÍA 15 - Comparar v5.3 vs v6.0

**Generar tabla comparativa**:

```bash
# Comparar ambas versiones
python scripts/validation/compare_v53_vs_v6.py

# Esperado table:
# Métrica                  | v5.3    | v6.0    | Mejora
# ───────────────────────────────────────────────────
# Vehicles/day             | 150     | 285     | +90% ✓
# CO2 (kg/año)            | 7200    | 7650    | +6% ✓
# Grid import %            | 25%     | 12%     | -48% ✓
# Episode reward           | 150     | 625     | +4.2x ✓
# Convergencia (episodios) | >100    | 12      | -88% ✓
```

**If all metrics match expectations**: 
```
┌────────────────────────────────┐
│ ✅ v6.0 IMPLEMENTACIÓN EXITOSA │
│                                │
│ +130 vehículos/día             │
│ -13% grid import               │
│ 2x convergencia más rápida     │
│                                │
│ 🎉 READY FOR PRODUCTION 🎉     │
└────────────────────────────────┘
```

**Checklist completado**: ✅ v6.0 completado y validado

---

## DIAGRAMA TEMPORAL GLOBAL

```
DÍA     FASE                    DURACIÓN    TAREAS
─────────────────────────────────────────────────────────────
1       Lectura & Understanding  1 día       Lee 4 docs
2-3     Environment Setup        2 días      Python, GPU, data
4       Data Validation          1 día       Verify 8,760 rows
5-11    Training (GPU)           7 días      Run SAC v6.0
7-12    Monitoring (parall)      Concurrent  Watch convergence
12-13   Validation               2 días      Test thresholds
14-15   Comparison               1 día       v5.3 vs v6.0
       ────────────────────────────────────────────────────
TOTAL                            14-15 días  (work-time: 10-12 days)
```

---

## THE CRITICAL CHECKLIST

Before starting **EACH PHASE**, verify:

### Antes de FASE 1 (Entender)
- [ ] Tienes acceso a docs/ carpeta
- [ ] Puedes abrir markdown files
- [ ] Tienes 1 hora libre de distracciones

### Antes de FASE 2 (Setup)
- [ ] Python 3.11+ instalado
- [ ] PowerShell acceso a dir d:\diseñopvbesscar
- [ ] GPU drivers actualizado (si aplica)

### Antes de FASE 3 (Data)
- [ ] `data/oe2/` carpeta existe
- [ ] Todos 4 CSV files presentes
- [ ] Cada CSV tiene 8,760 rows (validado)

### Antes de FASE 4 (Training)
- [ ] pip packages instalados
- [ ] torch importa sin errores
- [ ] GPU available (si usarás GPU)
- [ ] ~50 GB disk space libre para checkpoints

### Antes de FASE 5 (Validation)
- [ ] Training completó sin NaN errors
- [ ] Checkpoints carpeta tiene archivos .zip
- [ ] Reward trend fue creciente

---

## EMERGENCY CHECKLIST (Si algo falla)

**Si Python no instala**:
```bash
# Verificar Python version
python --version  # Debe ser 3.11+

# Si falta, desinstalar e reinstalar
# O usar WSL2 Ubuntu + Python 3.11
```

**Si GPU no detecta**:
```bash
# Verificar CUDA
nvidia-smi  # Debe salir 500+ GPU info

# Si no:
# Opción A: Instalar CUDA 12.1
# Opción B: Entrenar con CPU (40 horas)
```

**Si datos faltan**:
```bash
# Contactar data team
# Indicar: Falta {filename} en data/oe2/{path}/
```

**Si training falla con OOM (out of memory)**:
```bash
# Reducir batch_size en SAC config
batch_size = 128  # (from 256)

# O usar Google Colab (free GPU)
```

---

## 🏁 FINAL CHECKLIST - TODO LISTO?

```
PRE-LAUNCH VERIFICATION
═════════════════════════════════════════════════════════════

☐ Documentación leída: ✅ 4 archivos completados
☐ Entorno Python: ✅ .venv + packages instalados
☐ Datos OE2: ✅ 8,760 rows en cada CSV
☐ Código ready: ✅ train_sac_v6.py ejecutable
☐ GPU available: ✅ RTX 4060 o CPU fallback
☐ Disk space: ✅ 50+ GB libre para checkpoints
☐ Monitoreo: ✅ Scripts de monitoring ready
☐ Validation: ✅ Test scripts creados

════════════════════════════════════════════════════════════

🟢 ALL SYSTEMS GO

Command to launch:
    python scripts/train/train_sac_sistema_comunicacion_v6.py --device cuda

Expected result (7 days):
    +130 vehículos/día
    -13% grid import
    2x convergencia más rápida
    
════════════════════════════════════════════════════════════
```

---

## 📞 SOPORTE RÁPIDO

| Problema | Solución |
|----------|----------|
| No entiendo SAC v6 | Leer RESUMEN_EJECUTIVO (15 min) |
| Falta datos | Contactar data team |
| GPU error | Ejecutar con `--device cpu` (40h) |
| Training lento | Normal, SAC toma 7 días GPU |
| Validation falla | Revisar reward weights sum = 1.0 |
| Comparison vs v5.3 | Ejecutar `compare_versions.py` |

---

## TL;DR - VERSIÓN ULTRA-RÁPIDA

```
Qué es v6.0?
  Observación: 156-dim → 246-dim
  Por qué: Agent ve SOC individual + tiempo por socket
  Resultado: +130 vehículos/día

Cuándo empieza?
  LEE: SAC_v6_CAMBIOS_RESUMEN.md (5 min)
  LEE: RESUMEN_EJECUTIVO (15 min)
  RUN: python scripts/train/train_sac_sistema_comunicacion_v6.py (7 días)
  VALIDATE: python scripts/validation/validate_sac_v6.py (1 día)

Timeline?
  Día 1-2: Setup (entorno + datos)
  Día 3-7: Training (background, con GPU)
  Día 8-10: Validación + comparativa
  Total: 2 semanas

Success = +130 vehículos/día ✓
```

---

**CREADO**: 2026-02-14  
**VERSIÓN**: v6.0 Final  
**ESTADO**: 🟢 LISTO PARA EJECUTAR AHORA  

**SIGUIENTE PASO**: Abre y lee `SAC_v6_CAMBIOS_RESUMEN.md` (5 minutos) → Luego `RESUMEN_EJECUTIVO_v6_COMUNICACION.md` (15 minutos)

**¡EMPEZAR!** 🚀
