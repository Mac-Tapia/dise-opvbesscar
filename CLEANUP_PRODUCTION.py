#!/usr/bin/env python3
"""
LIMPIEZA Y REORGANIZACIÓN: Mover archivos innecesarios a archive/ para producción limpia
========================================================================================

Este script:
1. Crea directorio archive/ para documentación temporal
2. Mueve scripts de debugging a archive/
3. Mueve documentación temporal a archive/
4. Archiva logs para referencia
5. Deja solo lo esencial en raíz
"""

import shutil
import os
from pathlib import Path

def cleanup_for_production():
    """Reorganiza proyecto para producción limpia"""
    
    print('\n' + '='*100)
    print('🧹 LIMPIEZA Y REORGANIZACIÓN PARA PRODUCCIÓN')
    print('='*100 + '\n')
    
    # Crear directorio archive
    archive_dir = Path('archive')
    archive_dir.mkdir(exist_ok=True)
    print(f'✅ Creado directorio: {archive_dir}/\n')
    
    # Archivos a mover
    debug_scripts = [
        '_build_oe3_temp.py',
        'analisis_optimo_100porciento.py',
        'analisis_solar_real.py',
        'cargar_27_observables_reales.py',
        'check_a2c_ppo_ev.py',
        'check_sac_ev_charging.py',
        'check_timeseries.py',
        'cleanup_and_prep_ppo.py',
        'compare_peak_shaving_impact.py',
        'create_unified_methodology_docs.py',
        'final_cleanup_ppo.py',
        'launch_ppo_robust.py',
        'launch_ppo_training.py',
        'regenerate_unified_co2_images.py',
        'run_a2c_training.py',
        'test_peak_shaving_logic.py',
        'validate_oe2_data.py',
        'validate_sac_dataset_integration.py',
        'validate_solar_flow_cascade.py',
        'verify_sac_dataset_builder_connection.py',
        'verify_sac_dataset_connection.py',
        'visualize_peak_shaving.py',
    ]
    
    temp_docs = [
        'AJUSTE_HIPERPARAMETROS_BASADO_EN_PAPERS.md',
        'ARQUITECTURA_VISUAL_COMPLETA.md',
        'CAMBIOS_HIPERPARAMETROS_PPO_v53_DESCRIPCION.md',
        'CAMBIOS_HIPERPARAMETROS_PPO_VISUAL_SUMARIO.md',
        'CHECKLIST_INICIO_v6.md',
        'COMIENZA_AQUI.md',
        'CONSOLIDACION_FINAL_v6.md',
        'DATASETS_SAC_PPO_A2C_SUMMARY.md',
        'DESGLOSE_COBERTURA_SOLAR_248%_DETALLADO.md',
        'ENTREGA_FINAL_v6.md',
        'ENTRENAMIENTO_PPO_PRODUCCION.md',
        'ESTADO_ENTRENAMIENTO_PPO_FINAL.md',
        'ESTADO_RAPIDO_2026-02-14.md',
        'FIX_SUMMARY_DetailedLoggingCallback_v5.5.md',
        'FLUJO_CASCADA_SOLAR_VALIDADO.md',
        'INDICE_COMPLETO_v6.md',
        'INICIO_RAPIDO_v6.md',
        'LIMPIEZA_COMPLETADA_2026-02-14.md',
        'LISTA_ARCHIVOS_ELIMINADOS_DETALLADA.md',
        'MAPA_NAVEGACION_v6.md',
        'PEAK_SHAVING_FINAL_SUMMARY.md',
        'PROGRESO_ENTRENAMIENTO_PPO_VIVO.md',
        'REAL_METRICS_EXTRACTION_v2.1_RESUMEN.md',
        'REPORTE_FINAL_PPO_ENTRENAMIENTO_2026-02-14.md',
        'RESPUESTA_DATASETS_SAC_PPO_A2C.md',
        'RESPUESTA_FINAL_CITYLEARN_PREDICCION_CONTROL.md',
        'RESPUESTA_RAPIDA_CITYLEARN_V2_PREDICCION.md',
        'RESUMEN_EJECUTIVO_CITYLEARN.md',
        'RESUMEN_FINAL_COMPLETE_ENTRENAMIENTO_SAC.md',
        'SAC_DATASET_INTEGRATION_VERIFIED.md',
        'SAC_v6_CAMBIOS_RESUMEN.md',
        'SISTEMA_LISTO_PARA_ENTRENAR_2026-02-14.md',
        'VERIFICACION_SAC_DATASET_BUILDER_CONEXION.md',
        'VERIFICACION_SAC_DATASET_RESUMEN.md',
    ]
    
    temp_logs = [
        'train_check_soc.log',
        'train_output_ppo.log',
        'train_ppo_live.log',
        'train_ppo_monitored.log',
        'train_ppo_vivo_20260214_083448.log',
        'output.txt',
    ]
    
    scripts_to_keep = [
        'AUDIT_PROJECT.py',  # Este script y sus versiones mejoradas
    ]
    
    # Mover archivos de debugging
    print('📦 Moviendo scripts de debugging...')
    for script in debug_scripts:
        path = Path(script)
        if path.exists() and not any(keep in script for keep in scripts_to_keep):
            try:
                dest = archive_dir / 'scripts_debug' / script
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
                print(f'   ✓ {script}')
            except Exception as e:
                print(f'   ✗ {script}: {e}')
    
    # Mover documentación temporal
    print('\n📚 Moviendo documentación temporal...')
    for doc in temp_docs:
        path = Path(doc)
        if path.exists():
            try:
                dest = archive_dir / 'docs_temp' / doc
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
                print(f'   ✓ {doc}')
            except Exception as e:
                print(f'   ✗ {doc}: {e}')
    
    # Mover logs
    print('\n📋 Archivando logs de entrenamiento...')
    for log in temp_logs:
        path = Path(log)
        if path.exists():
            try:
                dest = archive_dir / 'logs' / log
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
                print(f'   ✓ {log}')
            except Exception as e:
                print(f'   ✗ {log}: {e}')
    
    # Limpiar el script de audit
    audit_path = Path('AUDIT_PROJECT.py')
    if audit_path.exists():
        try:
            dest = archive_dir / 'AUDIT_PROJECT.py'
            shutil.move(str(audit_path), str(dest))
            print(f'\n   ✓ AUDIT_PROJECT.py (movido a archive)')
        except:
            pass
    
    # Crear archivo .gitkeep en archive
    gitkeep = archive_dir / '.gitkeep'
    gitkeep.write_text('# Archive directory for temporary files')
    
    # Mostrar estructura final
    print('\n' + '='*100)
    print('✅ ESTRUCTURA FINAL - PRODUCCIÓN LIMPIA')
    print('='*100 + '\n')
    
    print('📁 RAÍZ (limpia):')
    root_files = [f for f in Path('.').glob('*') if f.is_file() and not f.name.startswith('.')]
    for f in sorted(root_files)[:20]:
        print(f'  • {f.name}')
    
    print('\n📁 archive/ (archivos temporales):')
    if archive_dir.exists():
        subdirs = list(archive_dir.glob('*'))
        for subdir in sorted(subdirs):
            if subdir.is_dir():
                count = len(list(subdir.glob('*')))
                print(f'  📁 {subdir.name:20s} ({count} items)')
    
    print('\n' + '='*100)
    print('🎯 PRÓXIMOS PASOS')
    print('='*100 + '\n')
    print('1. Revisar que archive/ tiene todos los archivos temporales')
    print('2. Ejecutar: git add archive/ && git commit -m "Archive: temp files for cleanup"')
    print('3. Ahora la raíz está limpia para desarrollo de producción')
    print('4. Scripts principales están en scripts/train/')
    print('5. Datos en data/, outputs en outputs/, checkpoints en checkpoints/')
    print('\n' + '='*100 + '\n')

if __name__ == '__main__':
    cleanup_for_production()
