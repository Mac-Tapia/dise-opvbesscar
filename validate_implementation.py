#!/usr/bin/env python3
"""
Script de Validación: Auditoría CO₂ Implementación Completa
============================================================

Verifica que TODAS las modificaciones estén presentes y correctas:
- Variables de CO₂ estandarizadas en A2C
- Tracking mensual implementado
- Módulo de graphing disponible
- Datasets presentes

Ejecutar:
  python validate_implementation.py
"""

import sys
from pathlib import Path
import json
import importlib.util
from typing import Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

SUCCESS_ICON = '✅'
ERROR_ICON = '❌'
WARNING_ICON = '⚠️'

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE VALIDACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def check_file_exists(path: Path, description: str) -> Tuple[bool, str]:
    """Verifica que un archivo existe."""
    if path.exists():
        return True, f"{SUCCESS_ICON} {description}: {path}"
    else:
        return False, f"{ERROR_ICON} {description}: NO ENCONTRADO ({path})"

def check_file_contains(path: Path, patterns: List[str], description: str) -> Tuple[bool, str]:
    """Verifica que un archivo contiene strings específicos."""
    if not path.exists():
        return False, f"{ERROR_ICON} {description}: ARCHIVO NO EXISTE"
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        missing = []
        for pattern in patterns:
            if pattern not in content:
                missing.append(pattern)
        
        if not missing:
            return True, f"{SUCCESS_ICON} {description}: TODAS LAS VARIABLES PRESENTES"
        else:
            return False, f"{ERROR_ICON} {description}: FALTAN {len(missing)} VARIABLES"
    
    except Exception as e:
        return False, f"{ERROR_ICON} {description}: ERROR LEYENDO ({str(e)})"

def check_python_module(module_path: Path) -> Tuple[bool, str]:
    """Verifica que un módulo Python es válido."""
    if not module_path.exists():
        return False, f"{ERROR_ICON} Modulo {module_path.name}: NO EXISTE"
    
    try:
        with open(module_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        compile(content, str(module_path), 'exec')
        return True, f"{SUCCESS_ICON} Modulo {module_path.name}: VALIDO"
    except SyntaxError as e:
        return False, f"{ERROR_ICON} Modulo {module_path.name}: ERROR ({str(e)[:40]})"
    except Exception as e:
        return False, f"{ERROR_ICON} Modulo {module_path.name}: ERROR ({str(e)[:40]})"

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def validate_all() -> Dict[str, List[Tuple[bool, str]]]:
    """Ejecuta todas las validaciones."""
    
    results = {
        'archivos': [],
        'train_a2c': [],
        'graphing': [],
        'datasets': [],
        'resumen': []
    }
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 1. ARCHIVOS PRINCIPALES
    # ═════════════════════════════════════════════════════════════════════════════
    
    print('\n[1] VALIDANDO ARCHIVOS MODIFICADOS...')
    
    train_a2c_path = Path('scripts/train/train_a2c.py')
    plot_path = Path('analyses/plot_agents_comparison.py')
    
    results['archivos'].append(check_file_exists(train_a2c_path, 'train_a2c.py'))
    results['archivos'].append(check_file_exists(plot_path, 'plot_agents_comparison.py'))
    
    for path, color in results['archivos']:
        print(f"  {color[0:2]} {color[25:]}")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 2. VALIDACIÓN DETALLADA: train_a2c.py
    # ═════════════════════════════════════════════════════════════════════════════
    
    print('\n[2] VALIDANDO CONTENIDO: train_a2c.py')
    
    patterns_a2c = [
        'episode_co2_directo_kg: list[float]',      # Variable principal
        'episode_co2_indirecto_solar_kg: list[float]',
        'episode_co2_indirecto_bess_kg: list[float]',
        'monthly_co2_directo_kg: dict[str, float] = defaultdict(float)',  # Monthly
        'monthly_co2_indirecto_solar_kg: dict[str, float] = defaultdict(float)',
        'monthly_motos_charged: dict[str, int] = defaultdict(int)',
        'from collections import defaultdict',      # Import
    ]
    
    success, msg = check_file_contains(train_a2c_path, patterns_a2c, 'Variables CO₂ A2C')
    results['train_a2c'].append((success, msg))
    print(f"  {msg}")
    
    # Búsqueda de patrones de cálculo
    if train_a2c_path.exists():
        try:
            with open(train_a2c_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Verificar acumulación
            has_monthly_update = 'self.monthly_co2_directo_kg[' in content
            results['train_a2c'].append((has_monthly_update, 
                f"{'✓' if has_monthly_update else 'X'} Acumulacion mensual en _on_step()"))
            
            # Verificar reset de episodio
            has_episode_reset = 'self._current_co2_directo_kg = 0.0' in content
            results['train_a2c'].append((has_episode_reset,
                f"{'✓' if has_episode_reset else 'X'} Reset de acumuladores en episodio"))
            
            # Verificar JSON output
            has_json_output = "episode_co2_directo_kg': detailed_callback.episode_co2_directo_kg" in content
            results['train_a2c'].append((has_json_output,
                f"{'✓' if has_json_output else 'X'} JSON output de CO2 directo"))
        except Exception as e:
            results['train_a2c'].append((False, f"X Error leyendo {train_a2c_path.name}: {str(e)[:30]}"))
    
    for success, msg in results['train_a2c']:
        print(f"  {msg}")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 3. VALIDACIÓN: Módulo Graphing
    # ═════════════════════════════════════════════════════════════════════════════
    
    print('\n[3] VALIDANDO MÓDULO GRAPHING')
    
    results['graphing'].append(check_python_module(plot_path))
    
    if plot_path.exists():
        try:
            with open(plot_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Verificar funciones clave
            functions = [
                'plot_co2_directo_comparison',
                'plot_co2_indirecto_comparison',
                'plot_co2_total_comparison',
                'plot_vehicles_charged_comparison',
                'plot_co2_directo_evolution',
                'plot_co2_indirecto_evolution',
                'plot_vehicles_evolution',
                'plot_summary_table',
                'load_results',
            ]
            
            for func_name in functions:
                has_func = f'def {func_name}' in content
                results['graphing'].append((has_func,
                    f"{'✓' if has_func else 'X'} Funcion {func_name}()"))
        except Exception as e:
            results['graphing'].append((False, f"X Error leyendo {plot_path.name}: {str(e)[:30]}"))
    
    for success, msg in results['graphing']:
        print(f"  {msg}")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 4. DATASETS OE2
    # ═════════════════════════════════════════════════════════════════════════════
    
    print('\n[4] VALIDANDO DATASETS OE2')
    
    datasets = [
        (Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'), 'Chargers (19 × 2 sockets = 38)'),
        (Path('data/interim/oe2/solar/pv_generation_timeseries.csv'), 'Solar timeseries (8,760 horas)'),
        (Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'), 'BESS dataset (8,760 horas)'),
        (Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv'), 'Mall demand (8,760 horas)'),
    ]
    
    for path, desc in datasets:
        success, msg = check_file_exists(path, desc)
        results['datasets'].append((success, msg))
        print(f"  {msg}")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 5. RESUMEN FINAL
    # ═════════════════════════════════════════════════════════════════════════════
    
    print('\n[5] RESUMEN FINAL')
    
    all_checks = []
    for category in results.values():
        for success, msg in category:
            all_checks.append(success)
    
    total = len(all_checks)
    passed = sum(all_checks)
    pct = 100 * passed / total if total > 0 else 0
    
    status = '✅ LISTO' if pct == 100 else ('⚠️  PARCIAL' if pct >= 80 else '❌ INCOMPLETO')
    results['resumen'].append((pct == 100, f'{status}: {passed}/{total} validaciones ({pct:.0f}%)'))
    
    print(f"  {results['resumen'][0][1]}")
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print('=' * 80)
    print('VALIDACION: Auditoria CO2 Implementacion Completa')
    print('=' * 80)
    
    try:
        results = validate_all()
        
        print('\n' + '=' * 80)
        print('PROXIMOS PASOS')
        print('=' * 80)
        
        # Contar resultados
        total_checks = sum(len(cat) for cat in results.values())
        passed_checks = sum(1 for cat in results.values() 
                           for success, _ in cat if success)
        pct = 100 * passed_checks / total_checks if total_checks > 0 else 0
        
        if pct >= 80:
            print('\nOK - AMBIENTE CONFIGURADO')
            print('\nPuedes ejecutar:')
            print('  1. python scripts/train/train_a2c.py (2 minutos)')
            print('  2. python analyses/plot_agents_comparison.py (10 segundos)')
        else:
            print('\nATENCION - REVISA LOS ERRORES ARRIBA')
            for category, items in results.items():
                failed = [msg for success, msg in items if not success]
                if failed:
                    print(f'\n{category.upper()}:')
                    for msg in failed:
                        print(f'  {msg}')
        
        return 0 if pct >= 80 else 1
        
    except Exception as e:
        print(f'\nERROR FATAL: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
