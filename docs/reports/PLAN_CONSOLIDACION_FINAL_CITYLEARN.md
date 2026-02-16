# Plan Final de Consolidación CityLearn (2026-02-17)

## 📊 Análisis de Dispersión Actual

### Estado de Carpetas
```
✅ CANÓNICA:
src/dataset_builder_citylearn/         (9 archivos, activos)
  ├── __init__.py                      (re-exports, 30 LOC)
  ├── observations.py                  (NUEVO, 600 LOC) ← Factory pattern
  ├── data_loader.py                   (100+ LOC)
  ├── rewards.py                       (150+ LOC)
  ├── catalog_datasets.py              (activo)
  ├── main_build_citylearn.py          (constructor, 200+ LOC)
  ├── analyze_datasets.py              (utilitario)
  ├── enrich_chargers.py               (utilitario)
  └── integrate_datasets.py            (utilitario)

⚠️  BASELINE (Específico, no consolidar al main builder):
src/baseline/                          (8 archivos)
  ├── __init__.py                      (exports BaselineCalculator, etc)
  ├── baseline_calculator_v2.py        (CONSTRUCTOR: BaselineCalculator class)
  ├── baseline_definitions_v54.py      (CONSTRUCTOR: BaselineScenario, etc)
  ├── citylearn_baseline_integration.py (CONSTRUCTOR: BaselineCityLearnIntegration)
  ├── agent_baseline_integration.py    
  ├── baseline_simulator.py
  ├── example_agent_training_with_baseline.py
  └── BASELINE_INTEGRATION_v54_README.md

❌ OBSOLETA/VACÍA:
src/citylearnv2/                       (0 archivos .py activos)
  ├── climate_zone/                    (VACÍA - eliminar)
  └── __pycache__/ 
  
  ⚠️  Anteriormente tenía:
     - dataset_builder/ (ELIMINADO en consolidación anterior)
     - climate_zone/ (VACÍO - no tiene .py files)

```

### Referencias Cruzadas (Grep Results)
- `src.baseline.*` imports: **LOCALES to baseline/** (self-contained)
- `src.dataset_builder_citylearn.*` imports: **ACTIVOS en agents/, dimensionamiento/**
- `src.citylearnv2.*` imports: **CERO** (carpeta muerta)

## 🎯 Decisión de Consolidación

### ✅ MANTENER (No alterar)
1. **`src/dataset_builder_citylearn/`** 
   - Status: **CANONICAL BUILDER** (SSOT)
   - Action: Keep as-is, it's the single source of truth
   - Key files: observations.py, rewards.py, data_loader.py, catalog_datasets.py

2. **`src/baseline/`**
   - Status: **SPECIFIC BASELINE LOGIC** (self-contained)
   - Action: Keep as-is, not imported from main code
   - Reason: Contains baseline-specific constructors (BaselineCalculator, BaselineScenario)
   - Business logic: Isolated comparison scenarios (CON_SOLAR vs SIN_SOLAR)
   - No duplication with main builder

### ❌ ELIMINAR (Dead code)
1. **`src/citylearnv2/`** - COMPLETE FOLDER
   - Contents: climate_zone/ (empty), __pycache__/
   - Status: Redundant, all functionality in dataset_builder_citylearn/
   - Action: Delete entire directory
   - Impact: ZERO - no active imports found

## 📋 Acciones de Consolidación

### FASE 1: Eliminar Código Muerto (SEGURO)
```bash
# Eliminar carpeta obsoleta
rm -r src/citylearnv2/
```

**Files Affected**: NONE (grep found zero active imports)

### FASE 2: Validar Rutas (CRÍTICO)
Revisar estos 5 archivos que fueron actualizados con NotImplementedError:

1. ✅ `src/baseline/example_agent_training_with_baseline.py`
   - Changed: old_builder import → NotImplementedError
   - Status: Already handled (TODO comment added)
   - Action: No additional changes needed

2. ✅ `scripts/analysis/extract_ppo_timeseries.py`
   - Changed: DatasetBuilder import → rebuild_oe2_datasets_complete + TODO
   - Status: Already handled
   - Action: No additional changes needed

3. ✅ `src/dimensionamiento/oe2/disenocargadoresev/test/test_chargers_real_integration.py`
   - Changed: build_citylearn_dataset → rebuild_oe2_datasets_complete
   - Status: Already handled
   - Action: No additional changes needed

4. ✅ `src/dimensionamiento/oe2/disenocargadoresev/run/run_integration_test.py`
   - Changed: Old citylearnv2 path check → new data_loader path
   - Status: Already handled
   - Action: No additional changes needed

5. ✅ `src/dimensionamiento/oe2/disenocargadoresev/run/verify_charger_integration.py`
   - Changed: builder_path → new location reference
   - Status: Already handled
   - Action: No additional changes needed

### FASE 3: Validar Consolidación (VERIFICACIÓN)
```bash
# 1. Verificar que no hay imports de citylearnv2
grep -r "src.citylearnv2" --include="*.py" .
# Expected: ZERO matches

# 2. Verificar que dataset_builder_citylearn es canónica
grep -r "dataset_builder_citylearn" --include="*.py" . | grep import | wc -l
# Expected: 9+ matches (agents, dimensionamiento, scripts)

# 3. Verificar que baseline es self-contained
grep -r "src.baseline" --include="*.py" . | grep -v "^./src/baseline/" | wc -l
# Expected: 0 matches (no external imports)
```

### FASE 4: Documentar Arquitectura Final
Create: `docs/ARQUITECTURA_CONSOLIDACION_FINAL.md`

## 📁 Estructura Final (Post-Consolidación)

```
✅ FINAL ARCHITECTURE
src/
├── dataset_builder_citylearn/              ← CANONICAL (OE2/OE3 builder)
│   ├── __init__.py                         ← Unified exports
│   ├── observations.py                     ← Factory pattern (4 versions)
│   ├── rewards.py                          ← Multi-objective rewards
│   ├── data_loader.py                      ← OE2 dataset loader
│   ├── catalog_datasets.py                 ← Current year picker
│   ├── main_build_citylearn.py             ← Main constructor
│   ├── analyze_datasets.py                 ← Analysis utilities
│   ├── enrich_chargers.py                  ← Charger enhancement
│   └── integrate_datasets.py                ← Integration utilities
│
├── baseline/                                ← SPECIFIC (Baseline scenarios)
│   ├── __init__.py                         ← Export BaselineCalculator
│   ├── baseline_calculator_v2.py           ← BaselineCalculator class
│   ├── baseline_definitions_v54.py         ← BaselineScenario enum
│   ├── citylearn_baseline_integration.py   ← Baseline CityLearn integration
│   └── [other baseline-specific files]
│
├── agents/                                  ← RL Agents
│   ├── sac.py                              ← SAC implementation
│   ├── ppo_sb3.py                          ← PPO implementation
│   ├── a2c_sb3.py                          ← A2C implementation
│   └── ...
│
├── dimensionamiento/oe2/                    ← Infrastructure design
│   ├── disenocargadoresev/
│   ├── generacionsolar/
│   └── balance_energetico/
│
└── utils/                                   ← Shared utilities
    ├── agent_utils.py
    ├── environment_validator.py
    └── ...

❌ DELETED:
└── citylearnv2/                             ✗ REMOVED (Dead code)
```

## ✅ Consolidation Checklist

- [ ] **STEP 1**: Delete src/citylearnv2/ directory
  - Command: `rm -r src/citylearnv2/`
  - Validation: `ls src/citylearnv2/` → should NOT exist

- [ ] **STEP 2**: Verify zero imports of deleted folder
  - Command: `grep -r "src\.citylearnv2" --include="*.py" src/`
  - Expected: ZERO matches

- [ ] **STEP 3**: Verify 5 updated files have proper TODOs
  - Files to check: baseline example_agent, extract_ppo, test_chargers, run_integration, verify_charger
  - Expected: NotImplementedError or TODO comments in place

- [ ] **STEP 4**: Python import validation
  ```python
  # Test that canonical builder works
  from src.dataset_builder_citylearn import (
      ObservationBuilder,
      validate_observation,
      rebuild_oe2_datasets_complete,
      load_oe2_datasets
  )
  ```

- [ ] **STEP 5**: Test baseline self-containment
  ```python
  # Test that baseline is isolated
  from src.baseline import BaselineCalculator, BASELINE_CON_SOLAR
  ```

## 🔄 Summary of Changes

| Change | Old | New | Status |
|--------|-----|-----|--------|
| Observations | 5 duplicated _make_obs() in scripts | ObservationBuilder class | ✅ Done |
| Data Builder | Scattered across folders | dataset_builder_citylearn/ (CANONICAL) | ✅ Done |
| Baseline | n/a | self-contained in src/baseline/ | ✅ Kept |
| CitylearnV2 | Dead folder with 0 .py files | DELETE | ⏳ TODO |

## 📑 Impact Assessment

### Code Deleted
- `src/citylearnv2/climate_zone/` - EMPTY folder (~0 LOC)
- `src/citylearnv2/__pycache__/` - cache (auto-regenerated)
- Total: ~0 LOC of actual code

### Code Affected
- 0 files will break (no active imports of citylearnv2)

### Code Preserved
- `src/dataset_builder_citylearn/` (600+ LOC, actively used)
- `src/baseline/` (300+ LOC, self-contained)

## ⚠️ Critical Notes

1. **DO NOT DELETE** `src/baseline/` 
   - Contains BaselineCalculator and BaselineScenario constructors
   - Self-contained, no known external imports
   - Business-critical for baseline comparisons

2. **DO NOT TOUCH** `src/dataset_builder_citylearn/`
   - This is the CANONICAL builder
   - All imports depend on it existing as-is

3. **SAFE TO DELETE** `src/citylearnv2/`
   - Search found ZERO active imports
   - Folder is empty (climate_zone has no .py files)
   - Only __pycache__/ remains

4. **5 Files with TODOs** (from previous consolidation phase)
   - These have NotImplementedError placeholders where old imports were
   - Intentional - awaiting future refactoring to use new builders
   - Do NOT remove these TODO comments

---

**Status**: Ready for final cleanup
**Next Step**: Execute FASE 1 (delete src/citylearnv2/)
**Validation**: Run import tests and verify zero impact
