# Historical Scripts Archive

This folder contains one-time Python scripts used during development and debugging phases. These scripts are not part of the main codebase pipeline but are preserved for reference and historical tracking.

## 📂 Contents Summary

**Total archived scripts:** 43 Python files

### Categories

#### Analysis Scripts (8)
```
analyze_bess_structure.py           - BESS configuration analysis
analyze_solar_scaling.py            - Solar timeseries scaling study
check_bess_profile.py               - BESS profile validation
check_structure.py                  - Data structure verification
compare_solar_oe2_vs_oe3.py         - Cross-version solar comparison
analizar_chargers_json.py           - Charger JSON analysis
```

#### Fixes & Corrections (12)
```
fix_bess_encoding.py                - BESS data encoding fixes
fix_chargers_comprehensive.py       - Comprehensive charger fixes
fix_chargers_types.py               - Charger type corrections
fix_simulate_docstring.py           - Docstring formatting fixes
fix_solar_15min_to_hourly.py        - 15-min to hourly conversion
fix_types_direct.py                 - Direct type fixes
suppress_sac_errors.py              - SAC error suppression attempts
update_chargers.py                  - Charger data updates
```

#### Verification & Validation (18)
```
verify_15min_schema.py              - 15-min schema verification (deprecated)
verify_and_generate_bess_data.py    - BESS data generation
verify_and_generate_chargers_data.py - Charger data generation
verify_chargers_playas_datasets.py  - Playas charger datasets check
verify_cuda.py                      - CUDA environment check
verify_final_summary.py             - Final data summary
verify_hourly_citylearn_final.py    - Hourly CityLearn verification
verify_hourly_citylearn_integration.py - Integration check
verify_hourly_requirement.py        - Hourly format requirement check
verify_hourly_revert.py             - Revert from 15-min operations
verify_hourly_to_schema.py          - Hourly to schema conversion
verify_playas_sockets_final.py      - Playas socket verification
verify_tomas_schema.py              - Tomas schema validation
verify_update_json_oe2.py           - OE2 JSON updates
validate_solar_format.py            - Solar data format validation
validate_solar_hourly_annual.py     - Solar hourly annual validation
validate_syntax.py                  - Python syntax validation
verificar_preentrenamiento.py       - Pre-training verification
```

#### Training & Configuration (5)
```
LAUNCH_TRAINING_CUDA_FORCED.py      - CUDA training launcher (forced)
LAUNCH_TRAINING_OPTIMIZED.py        - Optimized training launcher
OPTIMIZACION_AGENTES_GPU_MANUAL.py  - Manual GPU agent optimization
run_training_optimizado.py          - Optimized training execution
CUDA_SETUP_SUMMARY.py               - CUDA setup summary
```

#### Data Generation (2)
```
generate_toma_profiles_30min.py      - 30-min profile generation (deprecated)
regenerate_solar_oe2_hourly.py      - Solar OE2 hourly regeneration
```

#### Reports & Summaries (5)
```
CORRECTIONS_SUMMARY_PHASE7.py       - Phase 7 corrections summary
INDICE_TABLA_COMPARATIVA.py         - Comparison table index
RESUMEN_CORRECCION_SOLAR_HORARIA.py - Solar hourly corrections summary
RESUMEN_JSONS_ACTUALIZADOS.py       - Updated JSONs summary
display_playas_verification.py      - Playas verification display
show_playas_summary.py              - Playas summary display
```

#### Utilities (1)
```
install_pytorch_cuda.py             - PyTorch CUDA installation helper
```

---

## 🔍 Why Archived?

These scripts served specific purposes during development:

1. **One-time Fixes**: Used to correct data formatting or structure issues (no longer needed)
2. **Debugging**: Verification scripts created for specific issues (resolved in code)
3. **Experimentation**: Training variations and optimization attempts (best practices documented)
4. **Historical Reference**: Shows evolution of solutions (useful for learning)

## 📌 Usage

If you need to reference or run any archived script:

```bash
python historical/verify_chargers_playas_datasets.py
```

**Note:** These scripts may depend on outdated data formats or codebase states. Check dates and comments before execution.

## 🗑️ Consolidation Decision

**Decision Date:** 2026-01-25  
**Reason:** Root directory cleanup to reduce file clutter and improve project organization  
**Alternative:** Kept in `historical/` rather than deleted to preserve development history  
**Impact:** Scripts no longer clutter root directory but remain available for reference  

---

## 📚 Related Files

- **Active Pipeline:** See [COMANDOS_EJECUTABLES.md](../COMANDOS_EJECUTABLES.md) for current commands
- **Development Standards:** See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Project Status:** See [STATUS_ACTUAL_2026_01_25.md](../STATUS_ACTUAL_2026_01_25.md)

