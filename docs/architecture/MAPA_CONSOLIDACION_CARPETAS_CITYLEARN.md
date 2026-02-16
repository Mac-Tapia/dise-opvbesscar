# 🗺️ MAPA DE DISPERSIÓN - CARPETAS CITYLEARN

**Estado:** Identificación de carpetas duplicadas/obsoletas  
**Fecha:** 14 Febrero 2026

---

## 📍 UBICACIONES ACTUALES DE CARPETAS CITYLEARN

### 1️⃣ `src/citylearnv2/` (VIEJA - PARCIALMENTE LIMPIADA)
```
src/citylearnv2/
├─ climate_zone/          ✅ MANTENER (utilidad de zona climática)
├─ dataset_builder/       ❌ ELIMINADA (consolidada en nuevo builder)
├─ environment/           ⚠️ VERIFICAR (posibles imports)
└─ __pycache__/
```

**Status:** Parcialmente limpiada. Aún tiene `climate_zone/` que es útil.

---

### 2️⃣ `src/dataset_builder_citylearn/` (NUEVA - CANÓNICA)
```
src/dataset_builder_citylearn/
├─ data_loader.py         ✅ CANONICAL source for OE2 data
├─ rewards.py            ✅ CANONICAL source for multi-objective
├─ catalog_datasets.py   ✅ Dataset metadata
├─ observations.py       ✅ NEW - Unified observation builder
├─ main_build_citylearn.py
├─ enrich_chargers.py
├─ integrate_datasets.py
├─ analyze_datasets.py
└─ __init__.py           ✅ Re-exports everything
```

**Status:** Completamente funcional, es la ÚNICA fuente canónica.

---

## 🔴 ARCHIVOS CON IMPORTS PROBLEMÁTICOS

Estos archivos aún importan del viejo `citylearnv2` o referencias rotas:

| Archivo | Línea | Import Problemático | Acción |
|---------|-------|-------------------|--------|
| `src/baseline/example_agent_training_with_baseline.py` | 160, 198 | `from src.citylearnv2.dataset_builder import build_citylearn_env_from_oe2` | 🔄 ACTUALIZAR |
| `scripts/analysis/extract_ppo_timeseries.py` | 69-70 | `from src.citylearnv2.dataset_builder.dataset_builder import DatasetBuilder` `from src.citylearnv2.environment.environment import create_citylearn_env` | 🔄 ACTUALIZAR |
| `src/dimensionamiento/oe2/disenocargadoresev/test/test_chargers_real_integration.py` | 96 | `from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset` | 🔄 ACTUALIZAR |
| `src/dimensionamiento/oe2/disenocargadoresev/run/run_integration_test.py` | 92 | Path check to non-existent file | 🔄 ACTUALIZAR |
| `src/dimensionamiento/oe2/disenocargadoresev/run/verify_charger_integration.py` | 188 | Path check to non-existent file | 🔄 ACTUALIZAR |

---

## 📋 MAPA DE CONSOLIDACIÓN RECOMENDADO

### Fase 1: Identificar Dependencias
- ✅ DONE - Mapa creado
- 🔄 Identificar qué necesita cada archivo

### Fase 2: Actualizar Imports
1. `src/baseline/example_agent_training_with_baseline.py`
   - OLD: `from src.citylearnv2.dataset_builder import build_citylearn_env_from_oe2`
   - NEW: `from src.dataset_builder_citylearn import ...`

2. `scripts/analysis/extract_ppo_timeseries.py`
   - OLD: `from src.citylearnv2.dataset_builder.dataset_builder import DatasetBuilder`
   - NEW: `from src.dataset_builder_citylearn import ...`

3. Test scripts en `dimensionamiento/oe2/`
   - OLD: `from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset`
   - NEW: Usar nuevo builder

### Fase 3: Limpiar Carpeta
1. Mantener `src/citylearnv2/climate_zone/` (es útil)
2. Eliminar otros restos de `src/citylearnv2/`
3. Actualizar documentación (referencias a rutas viejas)

---

## 🎯 PLAN DE ACCIÓN INMEDIATO

### PASO 1: Verificar Climate Zone
```python
# Verificar si climate_zone se está usando
grep -r "climate_zone" src/
grep -r "climate_zone" scripts/
```

### PASO 2: Actualizar 5 Archivos con Imports Rotos
```bash
# 1. src/baseline/example_agent_training_with_baseline.py
# 2. scripts/analysis/extract_ppo_timeseries.py
# 3. src/dimensionamiento/oe2/disenocargadoresev/test/test_chargers_real_integration.py
# 4. src/dimensionamiento/oe2/disenocargadoresev/run/run_integration_test.py
# 5. src/dimensionamiento/oe2/disenocargadoresev/run/verify_charger_integration.py
```

### PASO 3: Eliminar Archivos Obsoletos
```bash
# Después de actualizar imports:
rm -rf src/citylearnv2/environment/      # Si no se usa
rm -rf src/citylearnv2/dataset_builder/  # Ya eliminado
# Mantener: src/citylearnv2/climate_zone/
```

### PASO 4: Limpiar Documentación
- Actualizar referencias en `README.md`
- Actualizar referencias en archivos `.md` de documentación
- Actualizar `copilot-instructions.md`

---

## 📊 ESPERADO POST-CONSOLIDACIÓN

```
ANTES:
src/citylearnv2/
├─ dataset_builder/       ❌ Monolítico, duplicado
├─ environment/           ⚠️ Fragmentado
├─ climate_zone/          ✅ Útil
└─ Muchas importaciones rotas

DESPUÉS:
src/citylearnv2/
└─ climate_zone/          ✅ SOLO ESTO QUEDA

src/dataset_builder_citylearn/  ✅ ÚNICA FUENTE DE VERDAD
├─ data_loader.py
├─ rewards.py
├─ observations.py        ✅ NEW
├─ catalog_datasets.py
└─ __init__.py

Resultado:
✅ SSOT establecido
✅ Cero imports rotos
✅ Código consolidado
```

---

**Próximo paso:** Ejecutar consolidación (actualizar imports + limpiar)
