# 🔍 ANÁLISIS DE DUPLICACIÓN Y PLAN DE CONSOLIDACIÓN

**Fecha**: 2026-02-14  
**Estado**: Análisis llevado a cabo

---

## 1. SITUACIÓN ACTUAL

### Estructura Duplicada
```
VIEJO: src/citylearnv2/dataset_builder/
├─ dataset_builder.py (2,701 LOC) - GRAN builder monolítico
│  ├─ Carga datos OE2
│  ├─ Valida datasets
│  ├─ Generaliza columnas  
│  ├─ Crea environment CityLearn
│  └─ Tracking CO₂ directo + indirecto
├─ data_loader.py (53 LOC) - Solo re-exports de dataset_builder
├─ rewards.py - Funciones de recompensa (USADO)
├─ progress.py - Progreso/gráficos (USADO)
├─ metrics_extractor.py - Métricas de episodios (USADO)
├─ transition_manager.py - Gestión transiciones (USADO)
├─ fixed_schedule.py - Baseline agent (USADO)
└─ __init__.py - Exports

NUEVO: src/dataset_builder_citylearn/
├─ enrich_chargers.py - Enriquecimiento CHARGERS
├─ integrate_datasets.py - Integración SOLAR
├─ analyze_datasets.py - Análisis
├─ catalog_datasets.py - Catálogo de metadatos (350+ LOC)
├─ main_build_citylearn.py - Orquestador
├─ __init__.py - Exports catálogo
└─ README.md
```

### Propósitos Diferentes
```
VIEJO (src/citylearnv2/dataset_builder/):
├─ Propósito: Cargar datos OE2 y crear CityLearn environment
├─ Entrada: CSV raw de OE2
├─ Salida: Environment listo para agentes RL
└─ Usuarios: SAC, PPO, A2C agents

NUEVO (src/dataset_builder_citylearn/):
├─ Propósito: Enriquecer y catalogar datos OE2
├─ Entrada: CSV raw de OE2
├─ Salida: CSV enriquecidos + catálogo de metadatos
└─ Usuarios: OE2 documentation, future OE3 integrations
```

---

## 2. ANÁLISIS DE DEPENDENCIAS ACTIVAS

### ¿Qué se importa del VIEJO en código activo?
✅ **USADO en agentes**:
- `rewards.py` → en `agents/__init__.py`, `agents/rbc.py`
- `progress.py` → en `agents/sac.py`, `agents/ppo_sb3.py`, `agents/a2c_sb3.py`
- `metrics_extractor.py` → dynamic import en agents (sac, ppo, a2c)
- `transition_manager.py` → re-export en `agents/transition_manager.py`
- `fixed_schedule.py` → re-export en `agents/fixed_schedule.py`

✅ **USADO en baselines**:
- `build_citylearn_dataset` → en `src/baseline/example_agent_training_with_baseline.py`

❓ **AMBIGUO** (posiblemente obsoleto):
- `dataset_builder.py` (2,701 LOC) - Monolítico, ¿se usa directamente?
- `data_loader.py` (53 LOC) - Solo re-exports, posible duplicación

### ¿Qué se importa del NUEVO?
❌ **NO USADO todavía**:
- `catalog_datasets.py` - Creado recientemente
- `main_build_citylearn.py` - Orquestador nuevo
- Ningún agente lo usa aún

---

## 3. PROBLEMAS IDENTIFICADOS

| # | Problema | Impacto | Severidad |
|---|----------|--------|-----------|
| 1 | Dos builders: `dataset_builder.py` (VIEJO) vs `main_build_citylearn.py` (NUEVO) | Confusión sobre cuál usar | 🔴 Alta |
| 2 | No hay una única "source of truth" de datasets enriquecidos | Riesgo de desincronización | 🔴 Alta |
| 3 | `dataset_builder.py` tiene 2,701 LOC (monolítico) | Difícil mantener y debuggear | 🟡 Media |
| 4 | No está claro qué datasets genera VIEJO vs NUEVO | Pipeline confuso | 🟡 Media |
| 5 | Catálogo NUEVO no está integrado en pipeline de agentes | Metadatos no usados | 🟠 Baja |

---

## 4. PLAN DE CONSOLIDACIÓN

### FASE 1: Unificar construcción de datasets
**Objetivo**: Una única ruta de construcción, desde datos raw a datasets listos

```
Paso 1a: Expandir NUEVO builder
├─ Mover lógica de carga OE2 de VIEJO → NUEVO
├─ Mover lógica de validación de VIEJO → NUEVO
├─ Mover constantes OSINERGMIN/CO₂ a NUEVO
└─ Resultado: NUEVO puede hacer TODO lo que VIEJO hace para construcción

Paso 1b: Actualizar VIEJO data_loader
├─ data_loader.py ahora lee desde catálogo (NUEVO)
├─ En lugar de hardcodear rutas, usa get_dataset(id)
├─ Los constantes CO₂/tarifa vienen del catálogo
└─ Resultado: VIEJO solo orquesta, NUEVO proporciona datos

Paso 1c: Reducir VIEJO dataset_builder.py
├─ Eliminar lógica de enriquecimiento (ahora en NUEVO)
├─ Eliminar lógica de validación OE2 (ahora en NUEVO)
├─ Mantener solo: Construcción de CityLearn environment
├─ Nuevo tamaño estimado: ~800 LOC (70% reducción)
└─ Resultado: dataset_builder.py más enfocado
```

### FASE 2: Integrar catálogo en pipeline
**Objetivo**: Los agentes usan datos desde catálogo

```
Paso 2a: Actualizar agents/__init__.py
├─ En lugar de importar rewards de VIEJO
├─ Importar rewards DEL VIEJO pero con factores del catálogo
└─ Resultado: Agentes usan factores centralizados

Paso 2b: Actualizar baseline
├─ En lugar de llamar build_citylearn_dataset(raw paths)
├─ Llamar build_citylearn_dataset(catalog_paths)
└─ Resultado: Baselines también usan datos enriquecidos

Paso 2c: Documentación del flujo
├─ Crear PIPELINE.md con diagrama claro
├─ Paso 1: python -m src.dataset_builder_citylearn.main_build_citylearn
├─ Paso 2: python -m src.agents.sac (carga desde catálogo)
└─ Resultado: Usuarios entienden qué ejecutar y en qué orden
```

### FASE 3: Limpieza
**Objetivo**: Eliminar código duplicado

```
Paso 3a: Identificar archivos descartables
├─ Si dataset_builder.py reducido < 500 LOC: mantener en VIEJO
├─ Si > 500 LOC: considerar mover a NUEVO
└─ Resultado: Claridad sobre qué goes where

Paso 3b: Eliminar duplicados
├─ ¿enrich_chargers.py y lógica en VIEJO son iguales?
├─ ¿integrate_datasets.py duplica VIEJO? 
└─ Resultado: Una sola implementación por feature

Paso 3c: Consolidar exports
├─ NUEVO.__init__.py: Exporta todo lo necesario (catálogo, builder, etc)
├─ VIEJO.__init__.py: Importa desde NUEVO donde sea relevante
└─ Resultado: Clear API surface
```

---

## 5. PLAN DE EJECUCIÓN RECOMENDADO

### Opción A: Rápida (Mínimo riesgo)
```
1. Dejar VIEJO como está (funciona con agentes)
2. NUEVO genera datos enriquecidos + catálogo
3. Crear documento de flujo: "Siempre ejecuta NUEVO builder primero"
4. Agentes continúan usando VIEJO (sin cambios)
5. Tiempo: 1 hora
6. Riesgo: Bajo (sin cambios a código activo)
```

### Opción B: Moderada (Unificar data_loader)
```
1. Actualizar VIEJO.data_loader para leer del catálogo (NUEVO)
2. Mantener todo lo demás igual
3. Resultado: Catálogo es source of truth
4. Tiempo: 3-4 horas
5. Riesgo: Medio (cambio a data_loader, usado por todos)
```

### Opción C: Completa (Reestructuración)
```
1. Mover lógica OE2 de VIEJO → NUEVO
2. Reducir dataset_builder.py a solo CityLearn construction
3. Unificar imports en todos los agents
4. Eliminar duplicados
5. Tiempo: 2-3 días
6. Riesgo: Alto (refactor grande)
```

---

## 6. MI RECOMENDACIÓN

**Opción B (Moderada)** - Mejor balance:

1. **Bajo riesgo**: Solo cambio en `data_loader.py` lineal
2. **Alto impacto**: Catálogo es source of truth
3. **Mantenible**: VIEJO sigue siendo "utilidades", NUEVO es "datos"
4. **Documentable**: Flujo claro: NUEVO genera → VIEJO consume
5. **Tiempo razonable**: 3-4 horas de trabajo

### Pasos específicos:
1. Actualizar `src/citylearnv2/dataset_builder/data_loader.py`:
   - En lugar de cargar paths HARDCODED
   - Usar `get_dataset()` del catálogo NUEVO
   - Leer constantes CO₂/tarifa del catálogo

2. Crear `docs/DATA_PIPELINE_FLOW.md`:
   - Diagrama: NUEVO → (dataset enriquecidos) → VIEJO → (agents)
   - Comandos: qué ejecutar y en qué orden
   - Validaciones: verificar integridad

3. Actualizar docstrings en:
   - `agents/__init__.py`
   - `baseline/`
   - README.md

4. Test end-to-end:
   - Ejecutar NUEVO builder
   - Entrenar SAC
   - Verificar que usa datos enriquecidos

---

## 7. DETALLES DE IMPLEMENTACIÓN (Opción B)

### Cambio en `data_loader.py`

**ANTES**:
```python
DEFAULT_SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
DEFAULT_CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")

def load_solar_data(path=None):
    path = path or DEFAULT_SOLAR_PATH
    return pd.read_csv(path)
```

**DESPUÉS**:
```python
from src.dataset_builder_citylearn.catalog_datasets import get_dataset

def load_solar_data(path=None):
    if path:
        return pd.read_csv(path)
    # Usar catálogo como default
    solar_catalog = get_dataset("SOLAR_v2")
    return pd.read_csv(solar_catalog.path)

def load_chargers_data(path=None):
    if path:
        return pd.read_csv(path)
    # Usar catálogo como default
    chargers_catalog = get_dataset("CHARGERS_v2")
    return pd.read_csv(chargers_catalog.path)
```

### Beneficios:
- Catálogo es source of truth
- Paths resueltos automáticamente
- Columnas verificadas por catálogo
- Fácil debuggear si hay problemas

---

## 8. DECISIÓN REQUERIDA

**¿Cuál opción prefieres?**

A. **Rápida** (NUEVO genera, VIEJO igual)  
B. **Moderada** (VIEJO usa catálogo del NUEVO) ← RECOMENDADA  
C. **Completa** (reestructuración grande)

---

**Próximo paso**: Una vez decidido, implemento el plan.
