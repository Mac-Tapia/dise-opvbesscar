# REPORTE DE INCONSISTENCIA - Entrenamientos vs Dataset Builder v5.5
**FECHA:** 2026-02-13  
**ESTADO:** ❌ INCONSISTENCIAS DETECTADAS - Requiere sincronización

---

## 📊 RESUMEN EJECUTIVO

### ✅ Lo que EXISTE y FUNCIONA:
- **Data Loader:** Completo con 4 funciones (solar, BESS, chargers, mall) ✅
- **Dataset Builder:** Integrado con observables, baseline, rewards ✅  
- **3 Entrenamientos:** Todos tienen baseline calculations ✅
- **CityLearnv2:** Todos usan environment de CityLearn ✅
- **CO2 Tracking:** Dataset Builder tiene 9 constantes CO2 ✅

### ❌ Lo que NO ESTÁ SINCRONIZADO:
1. **Funciones de carga de dataset DIFERENTES en cada agente:**
   - SAC: `load_datasets_from_processed()` ← Custom function SAC-specific
   - PPO: `validate_oe2_datasets()` ← Custom function PPO-specific
   - A2C: `build_oe2_dataset()` ← Custom function A2C-specific

2. **NINGÚN agente importa dataset_builder.py** 
   - Dataset builder existe pero **NO SE UTILIZA** en entrenamientos
   - Cada agente reinventa la rueda de carga de datos

3. **Variables observables NO extraídas en entrenamientos**
   - Dataset Builder define 18 variables observables chargers + 13 solar
   - Entrenamientos **NO usan estas variables**
   - Pierden tracking de CO2 directo/indirecto

4. **Baseline calculations INCOMPLETAS**
   - Dataset Builder tiene integración de `BaselineCalculator`
   - Entrenamientos NO llaman esa integración
   - Baselines calculados por separado (sin sincronización)

---

## 🔍 ANÁLISIS DETALLADO

### AGENTE SAC
```python
# ACTUAL - train_sac_multiobjetivo.py
def load_datasets_from_processed():
    """Custom function - NO usa data_loader"""
    # Carga manual desde data/processed/citylearn/iquitos_ev_mall
    # Reinventa validación de datos
    # Ignora observables del dataset_builder
```

**PROBLEMA:** Código duplicado, no sincronizado con dataset_builder

---

### AGENTE PPO
```python
# ACTUAL - train_ppo_multiobjetivo.py
def validate_oe2_datasets():
    """Custom validation - crea diccionario de rutas OE2"""
    # Carga manual, validación separada
    # NO usa data_loader.py y sus SAC_DATA estructuras
```

**PROBLEMA:** Validación propia, no usa data_loader.validate_oe2_complete()

---

### AGENTE A2C
```python
# ACTUAL - train_a2c_multiobjetivo.py
def build_oe2_dataset(interim_oe2_dir):
    """Custom builder - reconstruye dataset desde cero"""
    # Carga desde data/interim/oe2/ (no datos procesados)
    # Diferente flujo que SAC y PPO
```

**PROBLEMA:** Origen de datos diferente (data/interim vs data/processed)

---

## 📋 VARIABLES OBSERVABLES NO SINCRONIZADAS

### Dataset Builder DEFINE (31 columnas):
```
CHARGERS_OBSERVABLE_COLS (10):
  - is_hora_punta
  - tarifa_aplicada_soles
  - ev_energia_total_kwh
  - costo_carga_ev_soles
  - ev_energia_motos_kwh
  - ev_energia_mototaxis_kwh
  - co2_reduccion_motos_kg       ← CO2 DIRECTO (motos)
  - co2_reduccion_mototaxis_kg   ← CO2 DIRECTO (mototaxis)
  - reduccion_directa_co2_kg     ← TOTAL DIRECTO
  - ev_demand_kwh

SOLAR_OBSERVABLE_COLS (6):
  - is_hora_punta
  - tarifa_aplicada_soles
  - ahorro_solar_soles
  - reduccion_indirecta_co2_kg   ← CO2 INDIRECTO (solar)
  - co2_evitado_mall_kg          ← Asignado mall (67%)
  - co2_evitado_ev_kg            ← Asignado EV (33%)

ALL_OBSERVABLE_COLS (31 finales - prefijadas):
  ev_*, solar_*, total_*
```

### Entrenamientos USAN: 
```
❌ Ninguno usa estas columnas observables
❌ Pierden CO2 directo/indirecto de base de datos
❌ Recalculan sin usar datos preprocesados

RESULTADO: Doble trabajo, inconsistencia en tracking CO2
```

---

## 🔧 INSTANCIA DE BASELINE

### Dataset Builder INTEGRA:
```python
from src.baseline.baseline_calculator_v2 import BaselineCalculator
from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration

BASELINE_AVAILABLE = True  # Flag de disponibilidad
```

### Entrenamientos USAN:
```python
❌ SAC: No importa, pero tiene lógicas separadas de baseline
❌ PPO: No importa, pero tiene lógicas separadas de baseline
❌ A2C: No importa, pero tiene lógicas separadas de baseline

RESULTADO: Baselines NO INTEGRADOS con dataset_builder
```

---

## 📊 CO2 CONSTANTS - INCONSISTENCIA POTENCIAL

Dataset Builder define 9 constantes:
```
FACTOR_CO2_RED_KG_KWH = 0.4521       ✅ Grid Iquitos
FACTOR_CO2_GASOLINA_KG_L = 2.31      ✅ IPCC AR5
FACTOR_CO2_NETO_MOTO_KG_KWH = 0.87   ✅ Moto fuel switch
FACTOR_CO2_NETO_MOTOTAXI_KG_KWH = 0.47  ✅ Mototaxi fuel switch
TARIFA_ENERGIA_HP_SOLES = 0.45       ✅ OSINERGMIN MT3
TARIFA_ENERGIA_HFP_SOLES = 0.28      ✅ OSINERGMIN MT3
```

**RIESGO:** Si entrenamientos usan valores hardcoded, pueden divergir de dataset_builder

---

## 📂 FLUJO ACTUAL vs FLUJO CORRECTO

### FLUJO ACTUAL (INCONSISTENTE):
```
Data Loader (load_solar_data, load_bess_data, ...)
    ↓
    ↙ SAC usa: load_datasets_from_processed()
    ↙ PPO usa: validate_oe2_datasets()
    ↙ A2C usa: build_oe2_dataset()
    
    (3 funciones DIFERENTES, NO sincronizadas)
    ↓
Dataset Builder (NO USADO por entrenamientos)
    |
    ├─ BaselineCalculator (IMPORTADO pero NO USADO)
    ├─ Observable extraction (DEFINIDO pero NO USADO)
    └─ CO2 constants (DEFINIDO pero POSIBLEMENTE DIVERGENTE)
```

### FLUJO CORRECTO (PROPUESTO):
```
Data Loader (source of truth)
    ↓
Dataset Builder (unified dataset construction)
    ├─ Baseline Calculation (integrado)
    ├─ Observable Extraction
    └─ CO2 Constants (centralizadas)
    ↓
    ↙ SAC Agent (consume dataset_builder output)
    ↙ PPO Agent (consume dataset_builder output)
    ↙ A2C Agent (consume dataset_builder output)
    
    (1 función COMÚN, 3 consumidores sincronizados)
```

---

## 🎯 PLAN DE ACCIÓN

### FASE 1: Crear constructor UNIFICADO (1 día)
```python
# NEW: src/citylearnv2/dataset_builder/integrated_dataset_builder.py
class IntegratedDatasetBuilder:
    def __init__(self, config_path=None):
        self.data_loader = DataLoader()  # from data_loader.py
        self.baseline_calc = BaselineCalculator()
        
    def build(self) -> Dict[str, Any]:
        """Construye dataset completo: datos + baselines + observables"""
        # 1. Cargar datos usando data_loader (source of truth)
        solar = self.data_loader.load_solar_data()
        bess = self.data_loader.load_bess_data()
        chargers = self.data_loader.load_chargers_data()
        mall = self.data_loader.load_mall_demand_data()
        
        # 2. Validar con validate_oe2_complete()
        validation = self.data_loader.validate_oe2_complete()
        
        # 3. Calcular baselines usando BaselineCalculator
        baseline_con_solar = self.baseline_calc.calculate_baseline(with_solar=True)
        baseline_sin_solar = self.baseline_calc.calculate_baseline(with_solar=False)
        
        # 4. Extraer observables usando _extract_observable_variables()
        observables = self._extract_observable_variables(...)
        
        # 5. Retornar dataset completo SINCRONIZADO
        return {
            'solar': solar,
            'bess': bess,
            'chargers': chargers,
            'mall': mall,
            'baselines': {'con_solar': ..., 'sin_solar': ...},
            'observables': observables,
            'validation': validation,
        }
```

### FASE 2: Actualizar 3 entrenamientos (1-2 horas)
1. **train_sac_multiobjetivo.py**: Reemplazar `load_datasets_from_processed()` con `IntegratedDatasetBuilder().build()`
2. **train_ppo_multiobjetivo.py**: Reemplazar `validate_oe2_datasets()` con `IntegratedDatasetBuilder().build()`
3. **train_a2c_multiobjetivo.py**: Reemplazar `build_oe2_dataset()` con `IntegratedDatasetBuilder().build()`

### FASE 3: Extraer observables en entrenamientos (30 min)
Cada agente debe usar:
```python
dataset = IntegratedDatasetBuilder().build()
observables_df = dataset['observables']  # Contiene co2_directo, co2_indirecto

# En reward calculation:
reward_info['direct_co2'] = observables_df['ev_reduccion_directa_co2_kg'].iloc[hour]
reward_info['indirect_co2'] = observables_df['solar_reduccion_indirecta_co2_kg'].iloc[hour]
```

### FASE 4: Integrar baseline calculations (30 min-1 hora)
Cada agente debe usar:
```python
dataset = IntegratedDatasetBuilder().build()
baseline_con_solar = dataset['baselines']['con_solar']
baseline_sin_solar = dataset['baselines']['sin_solar']

# En evaluación:
improvement_con_solar = (baseline_con_solar.co2 - agent_co2) / baseline_con_solar.co2 * 100%
improvement_sin_solar = (baseline_sin_solar.co2 - agent_co2) / baseline_sin_solar.co2 * 100%
```

---

## 📌 CONCLUSIÓN

### Estado Actual: ⚠️ FUNCIONAL PERO NO SINCRONIZADO
- 3 entrenamientos funcionan **pero independientemente**
- Dataset Builder existe pero **NO SE USA**
- Data Loader existe pero **CADA AGENTE carga diferente**
- Baselines calculados **pero NO integrados**

### Resultado Esperado Después de Sincronización: ✅ COMPLETAMENTE INTEGRADO
- **1 Constructor unificado** (IntegratedDatasetBuilder)
- **3 Agentes consumidores** idénticos
- **Baseline calculations centralizadas**
- **Observable extraction unificada**
- **CO2 track sincronizado** en todos los agentes

### Nivel de Riesgo: 🟡 MEDIO
- Sin sincronización actual, baselines y observables pueden diverger
- Comparaciones entre agentes pueden ser inválidas
- Tracking de CO2 directo/indirecto **incompleto**

