# Backup de Archivos Obsoletos
**Fecha**: 2026-01-31 06:41:29

## Archivos Movidos (59 total)

### Archivos de Test/Análisis
- analisis_simple.py
- analisis_carga_baseline.py
- test_obs_structure_direct.py
- test_fix_idx0_vs_neg1.py
- test_citylearn_obs.py
- validate_sac_ppo_optimizations.py
- validate_ppo_learning.py
- validate_integration.py
- validar_sistema_produccion.py
- diagnostico_citylearn.py
- inspect_bess.py
- inspect_dataset_components.py
- inspect_pv.py

### Scripts Antiguos de Ejecución
- run_ppo_only.py
- run_ppo_simulation_only.py
- launch_sac_ppo_training.py
- ejemplo_entrenamiento_incremental.py
- save_result.py
- reporte_baseline_real.py

### Scripts de Tabla Comparativa (Duplicados)
- tabla_comparativa_final.py
- tabla_comparativa_FINAL_CORREGIDA.py
- tabla_comparativa_normalizada.py
- tabla_comparativa_resultados_reales.py

### Logs Obsoletos
- baseline_citylearn_real.log
- baseline_corrected.log
- baseline_execution.log
- baseline_full_execution_2026.log
- baseline_full_simulation.log
- baseline_full_year.log
- baseline_full_year_error.log
- baseline_full_year_output.log
- baseline_full_year_simulation.log
- baseline_robust_error.log
- baseline_robust_output.log
- build_baseline_execution.log
- entrenamiento_limpio_20260130_100647.log
- oe3_simulate_20260129_072244.log
- ppo_entrenamiento_20260129_072726.log
- ppo_fast.log
- ppo_relaunch.log
- ppo_run.log
- ppo_simulation_rerun_20260129_064435.log
- ppo_solo_20260129_072211.log
- sac_training_test.txt
- simulation_20260129_071803.log
- simulation_ppo_20260129_072052.log
- simulation_run_20260129_071702.log
- training_20260128_185059.log
- training_20260128_190148.log
- training_20260128_190902.log
- training_20260129_071852.log
- training_ppo_a2c_20260130_165414.log
- training_run_20260128_110027.log
- training_session_2026-01-28_184846.log

### JSON/TXT Temporales
- training_results_archive.json
- validation_results.json
- ESTADO_ANALISIS_CARGA_2026_01_28.txt
- VALIDACION_CORRECCIONES_APPLIED.txt
- GIT_COMMIT_MESSAGE_DATOS_REALES.txt

## Archivos NO Encontrados (0 total)


## Razón de Limpieza
Estos archivos fueron movidos para evitar conflictos con el sistema de 128 cargadores actualizado.
Los archivos principales que deben usarse están en:
- `scripts/run_oe3_build_dataset.py`: Build dataset
- `scripts/run_uncontrolled_baseline.py`: Baseline
- `scripts/run_sac_ppo_a2c_only.py`: Entrenamiento 3 agentes
- `scripts/run_oe3_co2_table.py`: Tabla comparativa

## Restauración
Si necesitas restaurar algún archivo:
```bash
cp _archivos_obsoletos_backup/20260131_064129/<archivo> .
```
