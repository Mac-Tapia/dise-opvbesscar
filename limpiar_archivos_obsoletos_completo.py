#!/usr/bin/env python3
"""
Limpieza completa de archivos obsoletos que pueden causar conflictos.
Mueve archivos a _archivos_obsoletos_backup/ para seguridad.
"""

from pathlib import Path
import shutil
from datetime import datetime

def main():
    # Crear carpeta de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("_archivos_obsoletos_backup") / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Archivos de test/análisis obsoletos en root
    archivos_test_analisis = [
        'analisis_simple.py',
        'analisis_carga_baseline.py',
        'test_obs_structure_direct.py',
        'test_fix_idx0_vs_neg1.py',
        'test_citylearn_obs.py',
        'validate_sac_ppo_optimizations.py',
        'validate_ppo_learning.py',
        'validate_integration.py',
        'validar_sistema_produccion.py',
        'diagnostico_citylearn.py',
        'inspect_bess.py',
        'inspect_dataset_components.py',
        'inspect_pv.py',
    ]

    # Scripts de ejecución antiguos
    scripts_antiguos = [
        'run_ppo_only.py',
        'run_ppo_simulation_only.py',
        'launch_sac_ppo_training.py',
        'ejemplo_entrenamiento_incremental.py',
        'save_result.py',
        'reporte_baseline_real.py',
    ]

    # Scripts de tabla comparativa (duplicados)
    scripts_tabla = [
        'tabla_comparativa_final.py',
        'tabla_comparativa_FINAL_CORREGIDA.py',
        'tabla_comparativa_normalizada.py',
        'tabla_comparativa_resultados_reales.py',
    ]

    # Logs antiguos (mantener solo los más recientes)
    logs_obsoletos = [
        'baseline_citylearn_real.log',
        'baseline_corrected.log',
        'baseline_execution.log',
        'baseline_full_execution_2026.log',
        'baseline_full_simulation.log',
        'baseline_full_year.log',
        'baseline_full_year_error.log',
        'baseline_full_year_output.log',
        'baseline_full_year_simulation.log',
        'baseline_robust_error.log',
        'baseline_robust_output.log',
        'build_baseline_execution.log',
        'entrenamiento_limpio_20260130_100647.log',
        'oe3_simulate_20260129_072244.log',
        'ppo_entrenamiento_20260129_072726.log',
        'ppo_fast.log',
        'ppo_relaunch.log',
        'ppo_run.log',
        'ppo_simulation_rerun_20260129_064435.log',
        'ppo_solo_20260129_072211.log',
        'sac_training_test.txt',
        'simulation_20260129_071803.log',
        'simulation_ppo_20260129_072052.log',
        'simulation_run_20260129_071702.log',
        'training_20260128_185059.log',
        'training_20260128_190148.log',
        'training_20260128_190902.log',
        'training_20260129_071852.log',
        'training_ppo_a2c_20260130_165414.log',
        'training_run_20260128_110027.log',
        'training_session_2026-01-28_184846.log',
    ]

    # Archivos JSON de resultados antiguos
    json_obsoletos = [
        'training_results_archive.json',
        'validation_results.json',
    ]

    # TXT de estado temporal
    txt_obsoletos = [
        'ESTADO_ANALISIS_CARGA_2026_01_28.txt',
        'VALIDACION_CORRECCIONES_APPLIED.txt',
        'GIT_COMMIT_MESSAGE_DATOS_REALES.txt',
    ]

    # Combinar todas las listas
    todos_obsoletos = (
        archivos_test_analisis +
        scripts_antiguos +
        scripts_tabla +
        logs_obsoletos +
        json_obsoletos +
        txt_obsoletos
    )

    # Mover archivos
    movidos = []
    no_encontrados = []

    for archivo in todos_obsoletos:
        src = Path(archivo)
        if src.exists():
            dst = backup_dir / archivo
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            movidos.append(archivo)
            print(f"✓ Movido: {archivo}")
        else:
            no_encontrados.append(archivo)
            print(f"⊘ No encontrado: {archivo}")

    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE LIMPIEZA")
    print("=" * 80)
    print(f"Archivos movidos: {len(movidos)}")
    print(f"Archivos no encontrados: {len(no_encontrados)}")
    print(f"Backup en: {backup_dir}")
    print("=" * 80)

    # Crear README en backup
    readme_path = backup_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"""# Backup de Archivos Obsoletos
**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Archivos Movidos ({len(movidos)} total)

### Archivos de Test/Análisis
{chr(10).join(f'- {a}' for a in archivos_test_analisis if a in movidos)}

### Scripts Antiguos de Ejecución
{chr(10).join(f'- {a}' for a in scripts_antiguos if a in movidos)}

### Scripts de Tabla Comparativa (Duplicados)
{chr(10).join(f'- {a}' for a in scripts_tabla if a in movidos)}

### Logs Obsoletos
{chr(10).join(f'- {a}' for a in logs_obsoletos if a in movidos)}

### JSON/TXT Temporales
{chr(10).join(f'- {a}' for a in (json_obsoletos + txt_obsoletos) if a in movidos)}

## Archivos NO Encontrados ({len(no_encontrados)} total)
{chr(10).join(f'- {a}' for a in no_encontrados)}

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
cp _archivos_obsoletos_backup/{timestamp}/<archivo> .
```
""")

    print(f"\n✓ README creado: {readme_path}")
    print("\n🎯 SISTEMA LIMPIO - Listo para entrenamiento!")

    return len(movidos), len(no_encontrados)

if __name__ == "__main__":
    movidos, no_encontrados = main()
    print(f"\n✅ COMPLETADO: {movidos} archivos movidos, {no_encontrados} no encontrados")
