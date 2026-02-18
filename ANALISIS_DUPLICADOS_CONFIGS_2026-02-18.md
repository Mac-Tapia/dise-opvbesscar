# Análisis de Duplicados en Carpeta `configs/` 

**Fecha:** 2026-02-18  
**Objetivo:** Evaluar y eliminar archivos/datos duplicados en `configs/`

---

## 📊 RESUMEN EJECUTIVO

| Categoría | Hallazgo | Riesgo | Recomendación |
|-----------|----------|--------|---------------|
| Archivos de configuración principal | 3 archivos YAML muy similares (default.yaml, default_optimized.yaml, test_minimal.yaml) | ⚠️ **ALTO** | Consolidar a 1-2 archivos |
| Reward weights | Duplicados idénticos en 4 archivos | ⚠️ **ALTO** | Centralizar en 1 archivo base |
| Tariffs | Duplicados idénticos en 3 archivos | ⚠️ **MEDIO** | Centralizar |
| SAC config | sac_config.yaml + sac_optimized.json (formatos diferentes, contenido similar) | ⚠️ **MEDIO** | Mantener 1, eliminar el otro |
| Infrastructure specs | Duplicadas en agents_config.yaml y sac_optimized.json | ⚠️ **MEDIO** | Centralizar |

**Total de duplicaciones halladas: 12+**

---

## 🔴 DUPLICADOS DETECTADOS

### 1. **Archivos de Configuración Principal (ALTO RIESGO)**

#### Problema:
```
default.yaml              409 líneas ❌ DUPLICADO
default_optimized.yaml    305 líneas ❌ DUPLICADO  
test_minimal.yaml         307 líneas ❌ DUPLICADO
```

#### Análisis:
- Los 3 archivos tienen **estructura idéntica** (oe1 + oe2)
- **Contenido casi idéntico**:
  - oe1.grid_connection: IDÉNTICO
  - oe1.site: IDÉNTICO (mismo nombre, áreas, vehículos)
  - oe2.bess: IDÉNTICO (2000 kWh, 400 kW, DoD 0.80)
  - oe2.dispatch_rules: CASI IDÉNTICO

#### Diferencias Mínimas:
- `default.yaml` contiene `oe2.data` (rutas de archivos) - **MÁS COMPLETO**
- `test_minimal.yaml` tiene `min_soc_percent: 25.86` vs otros `20.0` (ligera diferencia)
- `default_optimized.yaml` carece de sección `oe2.data`

#### Recomendación:
```
✅ MANTENER: default.yaml (más completo, con rutas de datos)
❌ ELIMINAR: default_optimized.yaml (duplicado de default.yaml sin beneficio)
⚠️ EVALUAR: test_minimal.yaml (si se usa para tests específicos, mantener; sino, eliminar)
```

---

### 2. **Reward Weights (ALTO RIESGO)**

#### Duplicados Encontrados:

**Ubicación 1:** `agents/agents_config.yaml` (líneas 19-24)
```yaml
reward_weights:
  co2: 0.5
  solar: 0.2
  ev: 0.15
  grid: 0.1
  cost: 0.05
```

**Ubicación 2:** `agents/sac_config.yaml` (líneas 37-42)
```yaml
multi_objective_weights:
  co2: 0.5
  solar: 0.2
  ev_satisfaction: 0.15
  grid_stability: 0.1
  cost: 0.05
```

**Ubicación 3:** `agents/ppo_config.yaml` (líneas 47-52)
```yaml
multi_objective_weights:
  co2: 0.5
  solar: 0.2
  ev: 0.15
  grid: 0.1
  cost: 0.05
```

**Ubicación 4:** `agents/a2c_config.yaml` (líneas 37-42)
```yaml
multi_objective_weights:
  co2: 0.5
  solar: 0.2
  ev: 0.15
  grid: 0.1
  cost: 0.05
```

**Ubicación 5:** `sac_optimized.json` (rewards section)
```json
{
  "co2_weight": 0.5,
  "solar_weight": 0.2,
  "cost_weight": 0.05,
  "ev_satisfaction_weight": 0.15,
  "grid_stability_weight": 0.1
}
```

#### Impacto:
- Si cambias rewards en UNA ubicación, las otras **quedan desincronizadas**
- Riesgo de entrenar con pesos inconsistentes

#### Recomendación:
```
✅ CREAR: configs/rewards_v55.yaml (archivo centralizado)
❌ ELIMINAR: Repeticiones de reward_weights en cada config específico
📝 REFERENCIA: Que cada config haga "include: rewards_v55.yaml" o simialr
```

---

### 3. **Tariffs (MEDIO RIESGO)**

#### Duplicados Encontrados:

**Ubicación 1:** `agents/sac_config.yaml` (líneas 43-48)
```yaml
tariffs_osinergmin_usd_per_kwh:
  generation_solar: 0.1
  storage_bess: 0.06
  distribution_ev_charge: 0.12
  integrated_tariff: 0.28
```

**Ubicación 2:** `agents/ppo_config.yaml` (líneas 53-58)
```yaml
tariffs_osinergmin_usd_per_kwh:
  generation_solar: 0.1
  storage_bess: 0.06
  distribution_ev_charge: 0.12
  integrated_tariff: 0.28
```

**Ubicación 3:** `agents/a2c_config.yaml` (líneas 43-48)
```yaml
tariffs_osinergmin_usd_per_kwh:
  generation_solar: 0.1
  storage_bess: 0.06
  distribution_ev_charge: 0.12
  integrated_tariff: 0.28
```

#### Recomendación:
```
✅ CREAR: configs/tariffs_osinergmin_v55.yaml
❌ ELIMINAR: Repeticiones en SAC/PPO/A2C configs
```

---

### 4. **SAC Config (MEDIO RIESGO)**

#### Duplicados Encontrados:

**Archivo 1:** `agents/sac_config.yaml` (91 líneas, YAML)
- Contiene: training params, entropy, network, stability, multi_objective_weights, tariffs, dispatch_hierarchy

**Archivo 2:** `sac_optimized.json` (151 líneas, JSON)
- Contiene: training params, data specs, rewards, dispatch_hierarchy

#### Análisis:
```
sac_config.yaml:
  - Más granular (network.hidden_sizes, stability params)
  - Tiene dispatch_hierarchy

sac_optimized.json:
  - Tiene data specs (rutas de files)
  - Tiene descripción detallada
  - Formato JSON vs YAML (gestión difícil)
```

#### Problema:
- Si actualizas learning_rate en SAC, ¿cuál archivo es la verdad?
- JSON vs YAML = confusión de formatos

#### Recomendación:
```
✅ MANTENER: agents/sac_config.yaml (YAML, nativo del proyecto)
❌ ELIMINAR: sac_optimized.json (duplicado en formato diferente)
📍 MIGRAR: Data specs desde sac_optimized.json → default.yaml
```

---

### 5. **Infrastructure Specs (MEDIO RIESGO)**

#### Duplicados Encontrados:

**Ubicación 1:** `agents/agents_config.yaml` (líneas 25-38)
```yaml
infrastructure:
  solar_capacity_kwp: 4050.0
  bess_capacity_kwh: 2000
  bess_power_kw: 400.0
  bess_min_soc_percent: 20.0
  num_chargers: 19
  num_sockets: 38
  charger_power_kw_per_socket: 7.4
  bess_capacity_nominal_kwh: 2000.0
  chargers_total: 19
  sockets_total: 38
  motos_daily: 270
  mototaxis_daily: 39
```

**Ubicación 2:** `sac_optimized.json` (data section)
```json
"chargers_total": 19,
"chargers_motos": 15,
"chargers_mototaxis": 4,
"sockets_total": 38,
"sockets_motos": 30,
"sockets_mototaxis": 8,
"bess_capacity_nominal_kwh": 2000.0,
"bess_capacity_usable_kwh": 1600,
"bess_power_kw": 400.0,
"bess_dod": 0.8,
"bess_soc_min": 0.2
```

#### Recomendación:
```
✅ CENTRALIZAR: En una sección de infrastructure (default.yaml)
❌ ELIMINAR: Repeticiones en sac_optimized.json
```

---

## 📋 PLAN DE CONSOLIDACIÓN

### **FASE 1: Crear Archivos de Referencia Centralizados**

```
configs/
├── _base/                                      [NUEVA CARPETA]
│   ├── infrastructure_v55.yaml                 [NUEVO]
│   ├── rewards_v55.yaml                        [NUEVO]
│   ├── tariffs_v55.yaml                        [NUEVO]
│   └── dispatch_rules_v55.yaml                 [NUEVO]
```

**Contenido de `_base/infrastructure_v55.yaml`:**
```yaml
# Infrastructure v5.5 Specifications (Single Source of Truth)
oe1:
  grid_connection:
    available_capacity_kva: null
    continuity: sistema aislado termico (diesel)
    power_factor: 0.95
    co2_factor_kg_per_kwh: 0.4521
  site:
    name: BESS Mall Iquitos
    vehicles_peak_motos: 270
    vehicles_peak_mototaxis: 39

oe2:
  bess:
    fixed_capacity_kwh: 2000.0
    fixed_power_kw: 400.0
    c_rate: 0.200
    dod: 0.80
    min_soc_percent: 20.0
  infrastructure:
    solar_capacity_kwp: 4050.0
    num_chargers: 19
    num_sockets: 38
    charger_power_kw_per_socket: 7.4
```

**Contenido de `_base/rewards_v55.yaml`:**
```yaml
# v5.5 Unified Reward Weighting (Single Source of Truth)
reward_weights:
  co2: 0.5              # PRIMARY: Grid CO2 minimization
  solar: 0.2            # SECONDARY: Solar self-consumption
  ev: 0.15              # TERTIARY: EV charge satisfaction
  grid: 0.1             # TERTIARY: Grid stability
  cost: 0.05            # TERTIARY: Cost minimization
```

### **FASE 2: Consolidación de Archivos**

| Archivo Actual | Acción | Por Qué |
|----------------|--------|--------|
| default.yaml | ✅ MANTENER (principal) | Más completo, incluye data paths |
| default_optimized.yaml | ❌ ELIMINAR | Duplicado de default.yaml |
| test_minimal.yaml | ⚠️ EVALUAR | Si se usa, mantener; sino, eliminar |
| agents_config.yaml | ↔️ REFACTORIZAR | Consolidar refs a `_base/*.yaml` |
| sac_config.yaml | ✅ MANTENER | Específico para SAC |
| ppo_config.yaml | ✅ MANTENER | Específico para PPO |
| a2c_config.yaml | ✅ MANTENER | Específico para A2C |
| sac_optimized.json | ❌ ELIMINAR | Duplicado de sac_config.yaml |

### **FASE 3: Refactorizar Imports**

**Antes (Duplicado):**
```yaml
# agents/sac_config.yaml  
reward_weights:
  co2: 0.5
  solar: 0.2
  ...
```

**Después (Centralizado):**
```yaml
# agents/sac_config.yaml
# Reference: _base/rewards_v55.yaml
sac:
  # ... (rest of SAC-specific config)
  
# At runtime, loader merges _base/rewards_v55.yaml
```

---

## ✅ CHECKLIST DE ACCIONES

### **Inmediato (Rápido):**
- [ ] Eliminar `configs/default_optimized.yaml` (duplicado de default.yaml)
- [ ] Eliminar `configs/sac_optimized.json` (duplicado de sac_config.yaml)

### **Corto Plazo (Recomendado):**
- [ ] Crear carpeta `configs/_base/`
- [ ] Crear `configs/_base/rewards_v55.yaml` (de agents_config.yaml)
- [ ] Crear `configs/_base/tariffs_v55.yaml` (de SAC/PPO/A2C)
- [ ] Crear `configs/_base/infrastructure_v55.yaml` (de agents_config.yaml)
- [ ] Actualizar SAC/PPO/A2C para referenciar `_base/` (no duplicar)
- [ ] Evaluar si eliminar `test_minimal.yaml`

### **Validación:**
- [ ] Verificar que training scripts cargan configs correctamente post-consolidación
- [ ] Verificar que todos los agentes usan los mismos reward_weights
- [ ] Crear test para detectar duplicados en futuro (diff de archivos)

---

## 📊 IMPACTO ESTIMADO

**Archivos que se pueden eliminar:** 2-3
**Espacio liberado:** ~50-100 KB
**Beneficio principal:** 
- ✅ Single Source of Truth para rewards, tariffs
- ✅ Menos mantenimiento (cambios en 1 lugar)
- ✅ Menos riesgo de inconsistencias entre agentes

**Tiempo estimado de consolidación:** 30-45 minutos

---

## 🚀 RECOMENDACIÓN FINAL

**ACCIÓN INMEDIATA:**
1. Eliminar `default_optimized.yaml` (copia exacta de default.yaml)
2. Eliminar `sac_optimized.json` (duplicado JSON de sac_config.yaml)

**ACCIÓN CORTO PLAZO:**
1. Crear `configs/_base/` con archivos centralizados
2. Refactorizar SAC/PPO/A2C para importar desde `_base/`
3. Documentar estrategia de config inheritance en README

**RESULTADO:**
- Configuraciones más limpias y mantenibles
- Una única fuente de verdad para specs/rewards
- Menos confusión entre archivos duplicados

---

**Generado:** 2026-02-18  
**Responsable:** Auditoría Proyecto pvbesscar v5.5
