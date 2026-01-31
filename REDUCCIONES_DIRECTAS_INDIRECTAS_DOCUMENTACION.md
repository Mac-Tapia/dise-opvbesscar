# REDUCCIONES DIRECTAS E INDIRECTAS DE CO₂ - DOCUMENTACIÓN EN ARCHIVOS FUENTE

**Fecha**: 2026-01-31  
**Status**: ✅ **DOCUMENTACIÓN TRASFERIDA A ARCHIVOS FUENTE ORIGINALES**

---

## 📋 Definiciones Críticas (Ahora en Archivos Fuente)

### 1. CO₂ DIRECTO (Demanda de EVs - Tracking)

**Ubicación en código**: 
- `src/iquitos_citylearn/oe3/dataset_builder.py` (docstring inicio)
- `src/iquitos_citylearn/oe3/rewards.py` (sección "CO₂ DIRECTO")
- `configs/default.yaml` (ev_co2_conversion_kg_per_kwh = 2.146)

**Definición**:
```
- Demanda: 50.0 kW constante (13 horas/día = 9AM-10PM)
- Factor: 2.146 kg CO₂/kWh (equivalente a combustión)
- Acumulado/hora: 50 × 2.146 = 107.3 kg CO₂/h
- Acumulado/año: 50 × 2.146 × 8760 = 938,460 kg CO₂/año

Propósito: 
- NO SE REDUCE (es la demanda fija)
- Es tracking para comparar con reducciones indirectas
- Referencia de línea base (baseline)
```

**Fórmula**:
```
CO₂_directo_kg/hora = ev_demand_kw × ev_co2_conversion_kg_per_kwh
                     = 50.0 × 2.146 = 107.3 kg CO₂/h

CO₂_directo_anual = 107.3 kg/h × 8760 h = 938,460 kg CO₂/año
```

---

### 2. CO₂ INDIRECTO (Grid Import - OBJETIVO PRINCIPAL)

**Ubicación en código**:
- `src/iquitos_citylearn/oe3/dataset_builder.py` (docstring inicio)
- `src/iquitos_citylearn/oe3/rewards.py` (sección "CO₂ INDIRECTO")
- `configs/default.yaml` (co2_grid_factor_kg_per_kwh = 0.4521)

**Definición**:
```
- Factor grid Iquitos: 0.4521 kg CO₂/kWh
- Causa: Central térmica aislada (0 grid renovation)
- Reducción indirecta = Solar PV directo × 0.4521

Propósito:
- SE REDUCE por: Maximizar PV directo a EVs
- Objetivo de optimización PRINCIPAL
- Peso en rewards: 0.50 (primary)
```

**Fórmula**:
```
CO₂_indirecto_evitado/año = Solar_PV_directo_anual × 0.4521
                           
Ejemplo:
  Si solar_pv_directo = 1000 kWh
  → CO₂_evitado = 1000 × 0.4521 = 452.1 kg CO₂ evitado
  
Baseline grid import:
  = 50 kW × 8760 h × 0.4521 = 197,262 kg CO₂/año (indirecto)
```

---

### 3. ARQUITECTURA DE REDUCCIONES (INTEGRADA)

**Control del Baseline**:
```
┌─────────────────────────────────────┐
│ BASELINE (Sin Control Inteligente) │
├─────────────────────────────────────┤
│ CO₂ Directo (Tracking):            │
│   50 kW × 8760 h × 2.146           │
│   = 938,460 kg CO₂/año             │
│   (NO se reduce, es fijo)          │
│                                    │
│ CO₂ Grid Import (Indirecto):       │
│   50 kW × 8760 h × 0.4521          │
│   = 197,262 kg CO₂/año             │
│   (TODO por grid, SIN PV directo) │
│                                    │
│ TOTAL BASELINE: ~1,135,722 kg CO₂ │
└─────────────────────────────────────┘
```

**Con Control RL (Optimizado)**:
```
┌──────────────────────────────────────┐
│ CON RL (Con Control Inteligente)    │
├──────────────────────────────────────┤
│ CO₂ Directo (Tracking):             │
│   50 kW × 8760 h × 2.146            │
│   = 938,460 kg CO₂/año              │
│   (NO cambia, demanda fija)         │
│                                     │
│ CO₂ Grid Import (Indirecto Reducido):│
│   (50 - solar_pv_directo) × 8760 × 0.4521 │
│   Ejemplo: 20 kWh solar directo    │
│   = (50-20) × 8760 × 0.4521        │
│   = 119,057 kg CO₂/año (reducido)  │
│                                     │
│ Reducción Neta:                    │
│   = solar_pv_directo × 0.4521 × 8760 │
│   = 20 × 0.4521 × 8760             │
│   = 78,205 kg CO₂/año evitado      │
│                                     │
│ TOTAL CON RL: ~1,057,517 kg CO₂    │
│ REDUCCIÓN: ~6.9% (78,205 kg CO₂)   │
└──────────────────────────────────────┘
```

---

## 🔗 Vinculaciones en Archivos Fuente

### 1. dataset_builder.py (L1-50)
**Docstring con tracking CO₂**:
```python
"""
TRACKING DE REDUCCIONES DIRECTAS E INDIRECTAS DE CO₂:

1. CO₂ DIRECTO: 50 kW × 2.146 = 107.3 kg CO₂/h
2. CO₂ INDIRECTO: Solar PV directo × 0.4521
3. Valores: config.yaml (SOURCE OF TRUTH)
"""
```

### 2. rewards.py (L1-80)
**Docstring con definiciones completas**:
```python
"""
TRACKING REDUCCIONES DIRECTAS E INDIRECTAS DE CO₂:

1. CO₂ DIRECTO (Demanda EV):
   - Factor: 2.146 kg CO₂/kWh
   - Anual: 938,460 kg (NO se reduce)

2. CO₂ INDIRECTO (Grid Import):
   - Factor: 0.4521 kg CO₂/kWh
   - Objetivo: Maximizar PV directo
   - Peso: 0.50 (primary)
"""
```

### 3. config.yaml (oe3.rewards section)
**SOURCE OF TRUTH con documentación**:
```yaml
rewards:
  # COMPONENTES DE TRACKING:
  # 1. CO₂ DIRECTO: ev_co2_conversion_kg_per_kwh: 2.146
  # 2. CO₂ INDIRECTO: co2_grid_factor_kg_per_kwh: 0.4521
  
  co2_grid_factor_kg_per_kwh: 0.4521        # Grid CO₂ [INDIRECTO]
  ev_co2_conversion_kg_per_kwh: 2.146       # Demanda EV [DIRECTO]
  ev_demand_constant_kw: 50.0               # Demanda constante [DIRECTO]
```

### 4. agents/ (SAC, PPO, A2C)
**Usan rewards basados en reducciones indirectas**:
- Observación incluye: `solar_generation` (para calcular PV directo)
- Acción controla: Potencia de chargers (para maximizar PV directo)
- Reward optimiza: Reducciones indirectas (solar directo × 0.4521)

---

## 📊 Tracking en Sistema Integrado

### Flow de Cálculos:

```
config.yaml (SOURCE OF TRUTH)
├─ co2_grid_factor_kg_per_kwh: 0.4521
├─ ev_co2_conversion_kg_per_kwh: 2.146
└─ ev_demand_constant_kw: 50.0
        ↓
        ↓ (cargas automáticamente)
        ↓
dataset_builder.py (VALIDA + DOCUMENTA)
├─ Lee config values
├─ Documenta reducciones directas/indirectas
└─ Genera schema CityLearn
        ↓
        ↓
rewards.py (CALCULA)
├─ CO₂ directo = 50 kW × 2.146 (tracking)
├─ CO₂ indirecto = solar_directo × 0.4521 (objetivo)
└─ Peso: 0.50 para CO₂ indirecto (primary)
        ↓
        ↓
agents (SAC/PPO/A2C) (OPTIMIZA)
├─ Observan solar_generation
├─ Controlan power de chargers
└─ Maximizan rewards (reducciones indirectas)
        ↓
        ↓
simulate.py (ACUMULA + REPORTA)
├─ Acumula CO₂ directo (tracking)
├─ Acumula CO₂ indirecto evitado (beneficio)
└─ Reporta: reducción neta vs baseline
```

---

## ✅ Verificación de Transferencia

Archivos con documentación de reducciones directas/indirectas:

| Archivo | Ubicación | Status |
|---------|-----------|--------|
| `dataset_builder.py` | Docstring (L1-50) | ✅ Transferido |
| `rewards.py` | Docstring (L1-80) | ✅ Transferido |
| `config.yaml` | oe3.rewards section | ✅ Transferido |
| `agents/sac.py` | Sincronizado con rewards | ✅ OK |
| `agents/ppo_sb3.py` | Sincronizado con rewards | ✅ OK |
| `agents/a2c_sb3.py` | Sincronizado con rewards | ✅ OK |

---

## 🎯 Cómo Funciona

### Ejemplo Práctico: Solar PV Directo = 20 kWh/hora

**Cálculo de Reducciones**:
```
CO₂ Directo (Tracking):
  = 50 kW × 2.146 kg/kWh × 1 hora
  = 107.3 kg CO₂/hora (NO se reduce)

CO₂ Grid Import (Indirecto):
  = (50 - 20) × 0.4521 kg/kWh × 1 hora  [20 kWh solar directo]
  = 30 × 0.4521 = 13.563 kg CO₂/hora (reducido)
  
Reducción Indirecta:
  = 20 × 0.4521 = 9.042 kg CO₂/hora (beneficio)

Acumulado anual (suponiendo 20 kWh solar directo constante):
  = 9.042 kg/h × 8760 h
  = 79,208 kg CO₂/año evitado (beneficio neto)
```

**Reward que recibe agente**:
```
r_co2 = función(solar_directo)  # Maximizar solar directo
      ∝ solar_directo × 0.4521   # Proporcional a reducciones indirectas
```

---

## 📝 Resumen Final

### ✅ Transferencias Completadas

**Reducciones Directas**:
- ✅ Documentado en `dataset_builder.py` docstring
- ✅ Documentado en `rewards.py` docstring
- ✅ Sincronizado en `config.yaml` (ev_co2_conversion_kg_per_kwh = 2.146)
- ✅ Tracking: Acumulado pero NO controlado (es fijo)

**Reducciones Indirectas**:
- ✅ Documentado en `dataset_builder.py` docstring
- ✅ Documentado en `rewards.py` docstring
- ✅ Sincronizado en `config.yaml` (co2_grid_factor_kg_per_kwh = 0.4521)
- ✅ Objetivo PRINCIPAL de optimización (peso: 0.50)

**Sincronización**:
- ✅ SOURCE OF TRUTH en `config.yaml`
- ✅ Cargado automáticamente por `dataset_builder.py`
- ✅ Usado en `rewards.py` para calcular
- ✅ Optimizado por `agents` (SAC/PPO/A2C)
- ✅ Reportado en `simulate.py`

---

## 🚀 Cómo Usar

**Verificar documentación**:
```bash
# Ver reducciones en dataset_builder
head -50 src/iquitos_citylearn/oe3/dataset_builder.py | grep -A 30 "TRACKING"

# Ver reducciones en rewards
head -80 src/iquitos_citylearn/oe3/rewards.py | grep -A 50 "TRACKING"

# Ver SOURCE OF TRUTH
grep -A 30 "rewards:" configs/default.yaml
```

**Ejecutar sistema (reducciones se calculan automáticamente)**:
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
python -m scripts.run_sac_ppo_a2c_only --sac-episodes 1 --ppo-episodes 1 --a2c-episodes 1
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

**Status**: ✅ **DOCUMENTACIÓN COMPLETA EN ARCHIVOS FUENTE**  
**Reducciones Directas**: Documentadas y sincronizadas  
**Reducciones Indirectas**: Documentadas y optimizadas  
**Sistema**: Listo para entrenamiento con tracking automático
