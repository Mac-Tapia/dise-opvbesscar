#!/usr/bin/env python3
"""
Script de limpieza de archivos en la raíz
Elimina:
1. Archivos de BASELINE
2. Archivos de TRAINING (excepto principales)
3. Archivos de CONFIG (excepto principales)
4. Archivos de CLEANUP (scripts de arreglo)
"""

from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")

# Archivos a eliminar (basado en ANALIZAR_RAIZ.py)
FILES_TO_DELETE = [
    # BASELINE (5)
    "COMPARATIVA_TRES_AGENTES.py",
    "compare_tier2_v1_vs_v2.py",
    "generate_baseline_vs_rl_comparison.py",
    "run_retraining_with_baseline_cache.py",
    "test_baseline_calculation.py",
    
    # TRAINING (26)
    "ANALISIS_TIMESTEPS_A2C_vs_SAC.py",
    "apply_citylearn_patches.py",
    "citylearn_monkeypatch.py",
    "citylearn_patch.py",
    "debug_episode.py",
    "diagnose_ppo_error.py",
    "diagnose_reward.py",
    "ENTRENAMIENTO_SECUENCIAL_PPO_A2C.py",
    "ESTRATEGIA_ENTRENAMIENTO_CON_LIMITACIONES.py",
    "EXPLICACION_REWARD_FIJO.py",
    "generate_sac_control_online.py",
    "generate_sac_dashboard.py",
    "GRAFICAS_FINALES_ENTRENAMIENTO.py",
    "patch_citylearn_robust.py",
    "REGENERAR_GRAFICAS_ENTRENAMIENTO.py",
    "regenerate_training_visualizations.py",
    "RESUMEN_ENTRENAMIENTOS_INICIADOS.py",
    "run_training_gpu.py",
    "run_training_with_limits.py",
    "show_training_status.py",
    "simple_ppo_gpu.py",
    "test_citylearn_env.py",
    "test_reward_window.py",
    "training_report.py",
    "VERIFICACION_ENTRENAMIENTO_COMPLETA.py",
    "VERIFICACION_PPO_APRENDIMIENTO.py",
    
    # CONFIG (10)
    "CONSTRUCCION_128_CHARGERS_RESUMEN.py",
    "debug_charger_csv.py",
    "fix_charger_final.py",
    "fix_charger_power.py",
    "fix_charger_regenerate.py",
    "fix_charger_timestep.py",
    "fix_chargers_simple.py",
    "test_dispatch_priorities.py",
    "validate_128_chargers.py",
    "verificar_observables_schema.py",
    
    # CLEANUP (36)
    "ANALISIS_COMPARATIVO_ALGORITMOS.py",
    "ARCHITECTURE_CLEAN_AND_VERIFIED.py",
    "AUDIT_AND_CLEANUP_PLAN.py",
    "debug_solar_discrepancy.py",
    "FINAL_CLEANUP_SUMMARY.py",
    "fix_all_105_errors.py",
    "fix_all_164_errors.py",
    "fix_all_212_errors.py",
    "fix_all_268_errors.py",
    "fix_all_290_errors.py",
    "fix_all_markdown.py",
    "fix_all_markdown_errors.py",
    "fix_final_9_markdown_errors.py",
    "fix_final_indents.py",
    "fix_final_surgical.py",
    "fix_markdown_complete.py",
    "fix_markdown_comprehensive.py",
    "fix_markdown_errors.py",
    "fix_markdown_errors_v2.py",
    "fix_markdown_final.py",
    "fix_markdown_issues.py",
    "fix_md060_tables.py",
    "fix_md_errors.py",
    "fix_remaining_errors.py",
    "fix_remaining_final.py",
    "fix_surgical.py",
    "fix_ultra_final.py",
    "generate_101_scenarios.py",
    "generate_checkpoint_report.py",
    "generate_report.py",
    "regenerate_graphics_real_data.py",
    "test_build_debug.py",
    "test_render_mode_fix.py",
    "VERIFICAR_GRAFICAS_NECESARIAS.py",
    "verificar_playas.py",
    "VERIFICAR_Y_LIMPIAR_GRAFICAS.py",
]

def clean_root():
    """Eliminar archivos identificados"""
    
    print("\n" + "="*80)
    print("LIMPIEZA DE RAÍZ: Eliminando archivos")
    print("="*80 + "\n")
    
    deleted = 0
    failed = 0
    not_found = 0
    
    for filename in sorted(FILES_TO_DELETE):
        filepath = ROOT / filename
        
        if not filepath.exists():
            print(f"✗ No encontrado: {filename}")
            not_found += 1
            continue
        
        try:
            size = filepath.stat().st_size / 1024
            filepath.unlink()
            print(f"✓ Eliminado: {filename} ({size:.1f} KB)")
            deleted += 1
        except Exception as e:
            print(f"✗ Error al eliminar {filename}: {e}")
            failed += 1
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE LIMPIEZA")
    print("="*80)
    print(f"✓ Eliminados: {deleted}")
    print(f"✗ Errores: {failed}")
    print(f"~ No encontrados: {not_found}")
    print(f"Total procesados: {deleted + failed + not_found}")
    print("="*80 + "\n")
    
    return deleted, failed, not_found

if __name__ == "__main__":
    deleted, failed, not_found = clean_root()
    
    if deleted > 0:
        print(f"✅ Limpieza completada: {deleted} archivos eliminados")
    if failed > 0:
        print(f"⚠️  Errores: {failed} archivos no se pudieron eliminar")
    if not_found > 0:
        print(f"ℹ️  No encontrados: {not_found} archivos")
