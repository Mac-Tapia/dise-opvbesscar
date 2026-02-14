# GUIA DE INTEGRACION - Sincronizar 3 Entrenamientos v5.5
**FECHA:** 2026-02-13  
**OBJETIVO:** Conectar train_sac_multiobjetivo.py, train_ppo_multiobjetivo.py, train_a2c_multiobjetivo.py al mismo constructor (IntegratedDatasetBuilder)  
**TIEMPO ESTIMADO:** 2-3 horas

---

## 📌 RESUMEN EJECUTIVO

### ANTES (Actual - Inconsistente):
```python
# train_sac_multiobjetivo.py
def load_datasets_from_processed():
    # Custom function SAC-specific
    # NO usa data_loader, NO usa dataset_builder
    
# train_ppo_multiobjetivo.py  
def validate_oe2_datasets():
    # Custom function PPO-specific
    # NO usa data_loader, NO usa dataset_builder
    
# train_a2c_multiobjetivo.py
def build_oe2_dataset():
    # Custom function A2C-specific
    # NO usa data_loader, NO usa dataset_builder
```

### DESPUÉS (Propuesto - Sincronizado):
```python
# Todos (SAC, PPO, A2C) usan el MISMO constructor
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset

dataset = build_integrated_dataset()

solar = dataset['solar']
chargers = dataset['chargers']
observables = dataset['observables_df'] # CO2 directo/indirecto AQUI
baselines = dataset['baselines']
```

---

## 🔧 PASO 1: Reemplazar importaciones

### SAC (train_sac_multiobjetivo.py) - LÍNEAS 180-370
**ANTES:**
```python
# Lines around 180
def load_datasets_from_processed():
    """Load datasets desde data/processed/citylearn/iquitos_ev_mall"""
    
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        # Error handling
        ...
```

**DESPUÉS:**
```python
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset

# En main() function, reemplazar:
def load_integrated_dataset():
    """Load datasets usando constructor unificado"""
    return build_integrated_dataset(verbose=True)
```

---

### PPO (train_ppo_multiobjetivo.py) - LÍNEAS 125-180
**ANTES:**
```python
def validate_oe2_datasets() -> Dict[str, Any]:
    """
    Validar y cargar los 5 datasets OE2 obligatorios.
    MISMA LOGICA que train_sac_multiobjetivo.py para garantizar consistencia.
    """
    print('=' * 80)
    print('[PRE-PASO] VALIDAR SINCRONIZACION CON 5 DATASETS OE2')
    print('=' * 80)

    OE2_FILES = {
        'solar': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
        # ... más validaciones
```

**DESPUÉS:**
```python
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset

def validate_oe2_datasets() -> Dict[str, Any]:
    """
    Validar y cargar los 5 datasets OE2 usando constructor integrado.
    Garantiza sincronización con SAC y A2C.
    """
    print('=' * 80)
    print('[PRE-PASO] VALIDAR SINCRONIZACION CON 5 DATASETS OE2 (INTEGRADO)')
    print('=' * 80)
    
    dataset = build_integrated_dataset(verbose=True)
    
    # Retornar en formato compatible con PPO
    return {
        'solar': dataset['solar'],
        'chargers': dataset['chargers'],
        'mall': dataset['mall'],
        'bess': dataset['bess'],
        'context': dataset['context'],
        'validation': dataset['validation'],
    }
```

---

### A2C (train_a2c_multiobjetivo.py) - LÍNEAS 210-280
**ANTES:**
```python
def build_oe2_dataset(interim_oe2_dir: Path) -> dict[str, Any]:
    """
    Build complete OE2 dataset from 5 required files.
    
    SECCIÓN CRÍTICA: Carga obligatoriamente 5 archivos REALES desde data/interim/oe2/
    """
    print("\n" + "="*80)
    print("[DATASET BUILD] Cargando 5 archivos OE2 REALES OBLIGATORIOS")
    
    result: dict[str, Any] = {}
    
    # 1. SOLAR (pv_generation_timeseries.csv)
    # 2. CHARGERS
    # ... etc
```

**DESPUÉS:**
```python
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset

def build_oe2_dataset(interim_oe2_dir: Path) -> dict[str, Any]:
    """
    Build complete OE2 dataset usando constructor integrado.
    
    Garantiza sincronización con SAC y PPO.
    data_loader.py es source of truth para todos los 3 agentes.
    """
    print("\n" + "="*80)
    print("[DATASET BUILD] Cargando 5 archivos OE2 REALES (INTEGRADO)")
    print("="*80)
    
    dataset = build_integrated_dataset(verbose=True)
    
    return {
        'solar': dataset['solar'],
        'chargers': dataset['chargers'],
        'mall': dataset['mall'],
        'bess': dataset['bess'],
        'context': dataset['context'],
    }
```

---

## 🎯 PASO 2: Extraer observables en cada agente

### SAC (train_sac_multiobjetivo.py)
**Lugar:** En main(), después de `dataset = load_integrated_dataset()`

**AGREGAR:**
```python
# EXTRAER OBSERVABLES (CO2 directo/indirecto)
observables_df = dataset['observables_df']  # pd.DataFrame (8760, 31)

# Mostrar tracking CO2
if 'ev_reduccion_directa_co2_kg' in observables_df.columns:
    direct_co2_ton = observables_df['ev_reduccion_directa_co2_kg'].sum() / 1000
    print(f"[OBSERVABLES] CO2 directo (EVs): {direct_co2_ton:.1f} ton/año")

if 'solar_reduccion_indirecta_co2_kg' in observables_df.columns:
    indirect_co2_ton = observables_df['solar_reduccion_indirecta_co2_kg'].sum() / 1000
    print(f"[OBSERVABLES] CO2 indirecto (Solar): {indirect_co2_ton:.1f} ton/año")

# Pasar a environment si es necesario
env = RealOE2Environment(
    ...,
    observables=observables_df,  # NUEVO: pasar observables
)
```

### PPO (train_ppo_multiobjetivo.py)
**Lugar:** En main(), después de cargar dataset

**AGREGAR:**
```python
# EXTRAER OBSERVABLES SINCRONIZADAS CON SAC/A2C
observables_df = dataset.get('observables_df')  # De IntegratedDatasetBuilder

if observables_df is not None:
    print(f"[OBSERVABLES] Extractadas {len(observables_df.columns)} columnas")
    
    # Validar CO2 tracking
    if 'ev_reduccion_directa_co2_kg' in observables_df.columns:
        direct_sum = observables_df['ev_reduccion_directa_co2_kg'].sum()
        print(f"  - Direct CO2: {direct_sum/1000:.1f} ton/año")
    
    if 'solar_reduccion_indirecta_co2_kg' in observables_df.columns:
        indirect_sum = observables_df['solar_reduccion_indirecta_co2_kg'].sum()
        print(f"  - Indirect CO2: {indirect_sum/1000:.1f} ton/año")

# Pasar a environment
env: CityLearnEnvironment = CityLearnEnvironment(
    ...,
    observables=observables_df,  # NUEVO
)
```

### A2C (train_a2c_multiobjetivo.py)
**Lugar:** En main(), después de `build_oe2_dataset()`

**AGREGAR:**
```python
# EXTRAER OBSERVABLES DESDE DATASET INTEGRADO
if 'observables' in dataset or hasattr(dataset, 'observables_df'):
    observables = dataset.get('observables_df', None)
    if observables is not None:
        print('[OBSERVABLES] Dataset contiene {} columnas de tracking'.format(len(observables.columns)))
        
        # Mostrar resumen CO2
        total_co2 = 0.0
        if 'ev_reduccion_directa_co2_kg' in observables.columns:
            direct = observables['ev_reduccion_directa_co2_kg'].sum()
            total_co2 += direct
            print(f'  CO2 direct (EVs): {direct/1000:.1f} ton/año')
        
        if 'solar_reduccion_indirecta_co2_kg' in observables.columns:
            indirect = observables['solar_reduccion_indirecta_co2_kg'].sum()
            total_co2 += indirect
            print(f'  CO2 indirect (Solar): {indirect/1000:.1f} ton/año')
        
        print(f'  TOTAL: {total_co2/1000:.1f} ton/año')
else:
    observables = None
```

---

## ⚙️ PASO 3: Integrar baseline calculations

### SAC (train_sac_multiobjetivo.py)
**Lugar:** En main(), después de dataset = load_integrated_dataset()

**AGREGAR:**
```python
# BASELINE CALCULATIONS (integradas en dataset)
baselines = dataset.get('baselines', {})

if baselines.get('con_solar') is not None:
    baseline_con_solar = baselines['con_solar']
    print(f"[BASELINE] CON SOLAR: {baseline_con_solar}")  # Mostrar formato
else:
    print("[BASELINE] ⚠️ No baseline available")

if baselines.get('sin_solar') is not None:
    baseline_sin_solar = baselines['sin_solar']
    print(f"[BASELINE] SIN SOLAR: {baseline_sin_solar}")
```

### PPO (train_ppo_multiobjetivo.py)
**Lugar:** Similar a SAC

```python
baselines = dataset.get('baselines', {})
baseline_con_solar = baselines.get('con_solar')
baseline_sin_solar = baselines.get('sin_solar')

if baseline_con_solar:
    # Usar para comparación later
    print(f"[BASELINE] CON SOLAR loaded")
if baseline_sin_solar:
    print(f"[BASELINE] SIN SOLAR loaded")
```

### A2C (train_a2c_multiobjetivo.py)
**Similar al patrón de PPO**

---

## 📊 PASO 4: Verificar consistencia

Después de hacer cambios en cada archivo, ejecutar:

```bash
# Test SAC
python scripts/train/train_sac_multiobjetivo.py --config configs/default.yaml --test-load-only

# Test PPO
python scripts/train/train_ppo_multiobjetivo.py --config configs/default.yaml --test-load-only

# Test A2C
python scripts/train/train_a2c_multiobjetivo.py --config configs/default.yaml --test-load-only
```

Debería ver en los 3:
```
[INTEGRATED BUILDER] CONSTRUCCION DE DATASET SINCRONIZADO v5.5
[PASO 1] Validar integridad OE2...
[PASO 2] Cargar datos desde data_loader...
[PASO 3] Crear contexto Iquitos...
[PASO 4] Extraer variables observables (CO2 tracking)...
[PASO 5] Calcular baselines (CON_SOLAR / SIN_SOLAR)...
```

Si los 3 muestran **EXACTAMENTE el mismo output**, entonces están **sincronizados ✅**

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### SAC (train_sac_multiobjetivo.py)
- [ ] Importar `build_integrated_dataset` (línea ~200)
- [ ] Reemplazar `load_datasets_from_processed()` con `build_integrated_dataset()`
- [ ] Extraer `observables_df` del dataset
- [ ] Pasar `observables` al environment
- [ ] Mostrar CO2 directo/indirecto en logs
- [ ] Integrar `baselines` si está disponible
- [ ] Test: python scripts/train/train_sac_multiobjetivo.py --test-load-only

### PPO (train_ppo_multiobjetivo.py)
- [ ] Importar `build_integrated_dataset` (línea ~50)
- [ ] Reemplazar `validate_oe2_datasets()` con `build_integrated_dataset()`
- [ ] Extraer `observables_df` del dataset
- [ ] Pasar `observables` al environment (línea ~1310)
- [ ] Mostrar CO2 directo/indirecto en logs
- [ ] Integrar `baselines` si está disponible
- [ ] Test: python scripts/train/train_ppo_multiobjetivo.py --test-load-only

### A2C (train_a2c_multiobjetivo.py)
- [ ] Importar `build_integrated_dataset` (línea ~220)
- [ ] Reemplazar `build_oe2_dataset()` con `build_integrated_dataset()`
- [ ] Extraer `observables` del dataset (línea ~680)
- [ ] Mostrar CO2 directo/indirecto en logs
- [ ] Integrar `baselines` si está disponible (línea ~800)
- [ ] Test: python scripts/train/train_a2c_multiobjetivo.py --test-load-only

---

## 🔍 VALIDACIÓN FINAL

Después de cambios, ejecutar script de auditoría actualizado:

```bash
python audit_training_dataset_consistency.py
```

Debería mostrar:
```
[SINCRONIZACION DE ENTRENAMIENTOS]
  Agentes: SAC, PPO, A2C
  Funciones de dataset COMUNES: 3
    ✓ build_integrated_dataset  ← TODAS USAN LA MISMA
    ✓ IntegratedDatasetBuilder
  Variables observables COMUNES: 31
    ✓ ev_reduccion_directa_co2_kg
    ✓ solar_reduccion_indirecta_co2_kg
    ... +29 more
```

---

## 📁 ARCHIVOS MODIFICADOS

Resumen de cambios requeridos:

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| train_sac_multiobjetivo.py | Reemplazar load_datasets_from_processed() | ~200-370 |
| train_ppo_multiobjetivo.py | Reemplazar validate_oe2_datasets() | ~125-180 |
| train_a2c_multiobjetivo.py | Reemplazar build_oe2_dataset() | ~210-280 |

### Archivos CREADOS (ya listos):
- ✅ src/citylearnv2/dataset_builder/integrated_dataset_builder.py (NEW)
- ✅ audit_training_dataset_consistency.py (NEW)
- ✅ REPORTE_INCONSISTENCIA_ENTRENAMIENTOS_v55.md (NEW)
- ✅ GUIA_INTEGRACION_ENTRENAMIENTOS_v55.md (THIS FILE)

---

## 🚀 BENEFICIOS DE SINCRONIZACIÓN

### ANTES (Inconsistente):
```
❌ 3 funciones diferentes de carga
❌ 3 validaciones independientes
❌ NO hay extracción de observables  
❌ Baselines desvinculados
❌ CO2 tracking INCOMPLETO
```

### DESPUÉS (Sincronizado):
```
✅ 1 constructor unificado (IntegratedDatasetBuilder)
✅ 1 validación centralizada (validate_oe2_complete)
✅ 31 variables observables extraídas
✅ Baselines integrados en dataset
✅ CO2 directo + indirecto COMPLETO
✅ Comparabilidad entre agentes garantizada
```

---

## 📞 SOPORTE

Si encuentras errores durante integración:

1. **ImportError** → dataset_builder path incorrecto
   ```python
   from src.citylearnv2.dataset_builder.integrated_dataset_builder import ...
   ```

2. **OE2ValidationError** → data_loader.py tiene issues
   ```bash
   python -m src.dimensionamiento.oe2.disenocargadoresev.data_loader
   ```

3. **KeyError en observables** → revisar ALL_OBSERVABLE_COLS
   ```python
   observables_df.columns  # Mostrar disponibles
   ```

---

