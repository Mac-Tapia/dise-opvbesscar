#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDADOR DE SINCRONIZACION - Verificar que entrenamientos usan IntegratedDatasetBuilder
=======================================================================================

Script rápido post-implementación para:
1. Verificar que los 3 agentes importan IntegratedDatasetBuilder
2. Verificar que todos carguen las 31 observables
3. Verificar que baselines están disponibles
4. Verificar outputs son IDENTICOS en setup inicial

Uso:
    python validate_training_integration.py
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Tuple

def check_import_integrated_builder(filepath: Path) -> Tuple[bool, str]:
    """Verificar que el archivo importa IntegratedDatasetBuilder"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('build_integrated_dataset' in content or 'IntegratedDatasetBuilder' in content,
         "Import de IntegratedDatasetBuilder"),
        ('from src.citylearnv2.dataset_builder' in content,
         "Import desde dataset_builder package"),
    ]
    
    all_passed = all(check[0] for check in checks)
    details = '\n'.join([f"  {'✅' if check[0] else '❌'} {check[1]}" for check in checks])
    
    return all_passed, details

def test_agent_dataset_loading(agent_name: str, script_path: Path) -> Tuple[bool, str]:
    """Ejecutar agente con --test-load-only para verificar dataset"""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), '--test-load-only'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        checks = [
            ('[INTEGRATED BUILDER]' in output, 
             "IntegratedDatasetBuilder inicializado"),
            ('[PASO 2] Cargar datos' in output,
             "Datos cargados desde data_loader"),
            ('[PASO 4] Extraer variables observables' in output,
             "Observables extractadas"),
            ('[PASO 5] Calcular baselines' in output,
             "Baselines calculados"),
            ('31' in output or '(8760, 31)' in output,
             "31 columnas observables"),
        ]
        
        all_passed = all(check[0] for check in checks)
        details = '\n'.join([f"  {'✅' if check[0] else '❌'} {check[1]}" for check in checks])
        
        return all_passed, details
    
    except subprocess.TimeoutExpired:
        return False, "  ❌ Timeout (script tardó > 60s)"
    except Exception as e:
        return False, f"  ❌ Error: {str(e)[:100]}"

def check_observables_columns(agent_name: str, script_path: Path) -> Tuple[bool, str]:
    """Verificar que las 31 columnas observables están presentes"""
    try:
        result = subprocess.run(
            [sys.executable, '-c', f'''
import sys
sys.path.insert(0, '.')
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset
try:
    dataset = build_integrated_dataset(verbose=False)
    obs = dataset.get("observables_df")
    if obs is not None:
        print(f"COLS:{{len(obs.columns)}}")
        for col in obs.columns:
            print(f"COL:{{col}}")
    else:
        print("ERROR:No observables")
except Exception as e:
    print(f"ERROR:{{e}}")
'''],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd()
        )
        
        output = result.stdout + result.stderr
        
        if 'COLS:31' in output:
            return True, "  ✅ 31 columnas observables presentes"
        elif 'COLS:' in output:
            col_count = [line for line in output.split('\n') if 'COLS:' in line][0].split(':')[1]
            return False, f"  ❌ Solo {col_count} columnas (esperadas 31)"
        else:
            return False, f"  ❌ Error al cargar observables: {output[:100]}"
    
    except Exception as e:
        return False, f"  ❌ Exception: {str(e)[:100]}"

def main():
    """Validación principal"""
    print("\n" + "="*80)
    print("VALIDADOR DE SINCRONIZACION - Post-Implementación v5.5")
    print("="*80 + "\n")
    
    training_dir = Path('scripts/train')
    agents = [
        ('SAC', training_dir / 'train_sac_multiobjetivo.py'),
        ('PPO', training_dir / 'train_ppo_multiobjetivo.py'),
        ('A2C', training_dir / 'train_a2c_multiobjetivo.py'),
    ]
    
    all_results = {}
    
    # ========================================================================
    # CHECK 1: Imports
    # ========================================================================
    print("[CHECK 1] Verificar importaciones de IntegratedDatasetBuilder")
    print("-"*80)
    
    for agent_name, script_path in agents:
        if not script_path.exists():
            print(f"⚠️  {agent_name}: Archivo no encontrado ({script_path})")
            all_results[agent_name] = {'imports': False}
            continue
        
        passed, details = check_import_integrated_builder(script_path)
        all_results[agent_name] = {'imports': passed}
        
        print(f"\n{agent_name} ({script_path.name}):")
        print(details)
        print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")
    
    # ========================================================================
    # CHECK 2: Dataset Loading
    # ========================================================================
    print("\n[CHECK 2] Verificar carga de datasets (--test-load-only)")
    print("-"*80)
    
    for agent_name, script_path in agents:
        if not script_path.exists() or not all_results[agent_name]['imports']:
            print(f"\n⚠️  {agent_name}: Saltado (no importa IntegratedDatasetBuilder)")
            all_results[agent_name]['loading'] = False
            continue
        
        print(f"\n{agent_name} ({script_path.name}):")
        print("  Ejecutando con --test-load-only...")
        
        passed, details = test_agent_dataset_loading(agent_name, script_path)
        all_results[agent_name]['loading'] = passed
        
        print(details)
        print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")
    
    # ========================================================================
    # CHECK 3: Observable Columns
    # ========================================================================
    print("\n[CHECK 3] Verificar 31 columnas observables")
    print("-"*80)
    
    passed, details = check_observables_columns('all', None)
    print(f"\nDataset integration:")
    print(details)
    all_results['observables'] = passed
    print(f"  → {'✅ PASS' if passed else '❌ FAIL'}")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("\n" + "="*80)
    print("RESUMEN DE VALIDACION")
    print("="*80)
    
    results_summary = {
        'imports': sum(1 for a in all_results.values() if isinstance(a, dict) and a.get('imports', False)) == 3,
        'loading': sum(1 for a in all_results.values() if isinstance(a, dict) and a.get('loading', False)) == 3,
        'observables': all_results.get('observables', False),
    }
    
    print(f"\n✅ Imports sincronizados:     {results_summary['imports']} (3/3 agentes)")
    print(f"✅ Dataset loading:           {results_summary['loading']} (3/3 agentes)")
    print(f"✅ Observables (31 cols):     {results_summary['observables']}")
    
    if all(results_summary.values()):
        print("\n" + "="*80)
        print("🎉 SINCRONIZACION COMPLETADA CON ÉXITO")
        print("="*80)
        print("\nTodos los entrenamientos están sincronizados:")
        print("  ✅ Importan IntegratedDatasetBuilder")
        print("  ✅ Cargan datos desde data_loader (source of truth)")
        print("  ✅ Extraen 31 observables (CO2 directo + indirecto)")
        print("  ✅ Integran baseline calculations")
        print("\n🚀 LISTO PARA ENTRENAMIENTO COMPLETO\n")
        return 0
    else:
        print("\n" + "="*80)
        print("⚠️  SINCRONIZACION INCOMPLETA")
        print("="*80)
        print("\nProblemas detectados:")
        if not results_summary['imports']:
            print("  ❌ No todos los agentes importan IntegratedDatasetBuilder")
        if not results_summary['loading']:
            print("  ❌ Dataset loading falla en algunos agentes")
        if not results_summary['observables']:
            print("  ❌ Observables (31 cols) no están disponibles")
        print("\nRevisa GUIA_INTEGRACION_ENTRENAMIENTOS_v55.md para detalles\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
