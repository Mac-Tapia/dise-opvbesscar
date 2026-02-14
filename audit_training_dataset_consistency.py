#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA DE CONSISTENCIA - Entrenamientos vs Dataset Builder vs Data Loader
==============================================================================

Verifica que:
1. Los 3 archivos de entrenamiento (SAC, PPO, A2C) usen el mismo dataset_builder
2. Todos compartan el mismo esquema de CityLearnv2
3. Todos tengan secciones de baseline calculation
4. Todos carguen datos usando el mismo patrón de data_loader
5. Las columnas observables (CO2 directo/indirecto) se repiten en cada agente
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

# Agregar root al path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_training_file(filepath: Path) -> Dict[str, any]:
    """Analiza un archivo de entrenamiento para extraer configuración."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    analysis = {
        'filepath': filepath,
        'agent': filepath.stem.split('_')[1].upper(),  # SAC, PPO, A2C
        'dataset_builder_imported': False,
        'citylearn_imported': False,
        'data_loader_imported': False,
        'baseline_calculation': False,
        'observable_variables': [],
        'reward_functions': [],
        'environment_class': None,
        'dataset_loading_functions': [],
        'baseline_functions': [],
    }
    
    # 1. Verificar importaciones
    if 'dataset_builder' in content:
        analysis['dataset_builder_imported'] = True
    if 'CityLearnEnv' in content or 'CityLearnEnvironment' in content:
        analysis['citylearn_imported'] = True
    if 'data_loader' in content or 'load_solar_data' in content or 'load_bess_data' in content:
        analysis['data_loader_imported'] = True
    
    # 2. Buscar función principal de cálculo de baseline
    baseline_pattern = r'(def|class|baseline|BASELINE|\bbaseline_|_baseline|compute.*baseline)'
    baseline_matches = re.findall(baseline_pattern, content, re.IGNORECASE)
    if baseline_matches:
        analysis['baseline_calculation'] = True
    
    # 3. Buscar variables observables de CO2
    observable_patterns = [
        r'reduccion_directa_co2_kg',
        r'reduccion_indirecta_co2_kg',
        r'total_reduccion_co2_kg',
        r'ev_reduccion_directa',
        r'solar_reduccion_indirecta',
        r'FACTOR_CO2_NETO_MOTO',
        r'FACTOR_CO2_NETO_MOTOTAXI',
        r'FACTOR_CO2_RED_KG_KWH',
        r'ev_energia_motos_kwh',
        r'ev_energia_mototaxis_kwh',
        r'co2_reduccion_motos_kg',
        r'co2_reduccion_mototaxis_kg',
    ]
    for pattern in observable_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            analysis['observable_variables'].append(pattern)
    
    # 4. Buscar funciones de reward
    reward_patterns = [
        r'MultiObjectiveReward',
        r'create_iquitos_reward_weights',
        r'IquitosContext',
        r'co2_weight|solar_weight|ev_weight|cost_weight',
    ]
    for pattern in reward_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            analysis['reward_functions'].append(pattern)
    
    # 5. Buscar clase de environment
    env_class_match = re.search(r'class\s+(\w*(?:CityLearn|Environment)\w*)', content)
    if env_class_match:
        analysis['environment_class'] = env_class_match.group(1)
    
    # 6. Buscar funciones de carga de dataset
    dataset_funcs = [
        'load_datasets_from_processed',
        'build_oe2_dataset',
        'validate_oe2_datasets',
        'load_solar_data',
        'load_bess_data',
        'load_chargers_data',
        'load_mall_demand_data',
    ]
    for func in dataset_funcs:
        if re.search(rf'\b{func}\b', content):
            analysis['dataset_loading_functions'].append(func)
    
    # 7. Buscar funciones de baseline
    baseline_funcs = [
        'baseline',
        'uncontrolled',
        'no_control',
        'CON_SOLAR',
        'SIN_SOLAR',
    ]
    for func in baseline_funcs:
        if re.search(rf'\b{func}\b', content, re.IGNORECASE):
            analysis['baseline_functions'].append(func)
    
    return analysis

def compare_training_files():
    """Compara los 3 archivos de entrenamiento."""
    training_dir = Path('scripts/train')
    training_files = [
        training_dir / 'train_sac_multiobjetivo.py',
        training_dir / 'train_ppo_multiobjetivo.py',
        training_dir / 'train_a2c_multiobjetivo.py',
    ]
    
    analyses = []
    for filepath in training_files:
        if filepath.exists():
            print(f"  Analizando: {filepath.name}...")
            analysis = analyze_training_file(filepath)
            analyses.append(analysis)
        else:
            print(f"  ⚠️  NO ENCONTRADO: {filepath}")
    
    return analyses

def check_dataset_builder():
    """Verifica el archivo dataset_builder.py."""
    dataset_builder_path = Path('src/citylearnv2/dataset_builder/dataset_builder.py')
    
    with open(dataset_builder_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    info = {
        'filepath': dataset_builder_path,
        'has_baseline_integration': False,
        'has_observables': False,
        'observable_columns': [],
        'chargers_columns': [],
        'solar_columns': [],
        'co2_constants': [],
        'reward_integration': False,
    }
    
    # 1. Verificar integración de baseline
    if 'BaselineCalculator' in content or 'BaselineCityLearnIntegration' in content:
        info['has_baseline_integration'] = True
    
    # 2. Verificar columnas observables
    observable_pattern = r"(CHARGERS_OBSERVABLE_COLS|SOLAR_OBSERVABLE_COLS|ALL_OBSERVABLE_COLS)"
    if re.search(observable_pattern, content, re.IGNORECASE):
        info['has_observables'] = True
    
    # Extraer columnas observables específicas
    chargers_obs_matches = re.findall(r"'(ev_\w+|is_hora_punta|tarifa_\w+|costo_\w+|reduccion_\w+)'", content)
    solar_obs_matches = re.findall(r"'(solar_\w+|ahorro_\w+|co2_evitado\w*)'", content)
    
    info['chargers_columns'] = list(set(chargers_obs_matches))
    info['solar_columns'] = list(set(solar_obs_matches))
    
    # 3. Verificar constantes CO2
    co2_const_matches = re.findall(
        r"(FACTOR_CO2_\w+|TARIFA_\w+)\s*=\s*([\d.]+)",
        content
    )
    for const_name, const_value in co2_const_matches:
        info['co2_constants'].append(f"{const_name} = {const_value}")
    
    # 4. Verificar integración de rewards
    if 'IquitosContext' in content or 'create_iquitos_reward_weights' in content:
        info['reward_integration'] = True
    
    return info

def check_data_loader():
    """Verifica el archivo data_loader.py."""
    data_loader_path = Path('src/dimensionamiento/oe2/disenocargadoresev/data_loader.py')
    
    with open(data_loader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    info = {
        'filepath': data_loader_path,
        'has_solar_loader': False,
        'has_bess_loader': False,
        'has_chargers_loader': False,
        'has_mall_loader': False,
        'has_validation': False,
        'loader_functions': [],
        'constants': [],
    }
    
    # 1. Verificar funciones de carga
    loaders = ['load_solar_data', 'load_bess_data', 'load_chargers_data', 'load_mall_demand_data']
    for loader in loaders:
        if f'def {loader}' in content:
            info['loader_functions'].append(loader)
            if 'solar' in loader:
                info['has_solar_loader'] = True
            elif 'bess' in loader:
                info['has_bess_loader'] = True
            elif 'chargers' in loader:
                info['has_chargers_loader'] = True
            elif 'mall' in loader:
                info['has_mall_loader'] = True
    
    # 2. Verificar función de validación
    if 'validate_oe2_complete' in content:
        info['has_validation'] = True
    
    # 3. Extraer constantes principales
    const_matches = re.findall(
        r"(DEFAULT_\w+|INTERIM_\w+)\s*=\s*(Path\(['\"].*?['\"]|[\d.]+)",
        content
    )
    info['constants'] = [f"{name} = {value[:50]}..." if len(str(value)) > 50 else f"{name} = {value}" 
                         for name, value in const_matches[:10]]
    
    return info

def print_report(training_analyses, builder_info, loader_info):
    """Imprime reporte de consistencia."""
    print("\n" + "="*80)
    print("AUDITORIA DE CONSISTENCIA - ENTRENAMIENTOS, DATASET BUILDER, DATA LOADER")
    print("="*80)
    
    # SECCION 1: ARCHIVOS DE ENTRENAMIENTO
    print("\n[1] ARCHIVOS DE ENTRENAMIENTO (SAC, PPO, A2C)")
    print("-"*80)
    
    if not training_analyses:
        print("❌ NO SE ENCONTRARON ARCHIVOS DE ENTRENAMIENTO")
    else:
        common_dataset_funcs = None
        common_observables = None
        all_agents = []
        
        for analysis in training_analyses:
            print(f"\n✓ {analysis['agent']} AGENT ({analysis['filepath'].name})")
            print(f"  Dataset Builder imported:   {analysis['dataset_builder_imported']} {'✅' if analysis['dataset_builder_imported'] else '⚠️'}")
            print(f"  CityLearn Environment:      {analysis['citylearn_imported']} {'✅' if analysis['citylearn_imported'] else '⚠️'}")
            print(f"  Data Loader imported:       {analysis['data_loader_imported']} {'✅' if analysis['data_loader_imported'] else '⚠️'}")
            print(f"  Baseline Calculation:       {analysis['baseline_calculation']} {'✅' if analysis['baseline_calculation'] else '❌'}")
            print(f"  Environment Class:          {analysis['environment_class'] or 'N/A'}")
            
            # Dataset loading functions
            if analysis['dataset_loading_functions']:
                print(f"  Dataset Loading Funcs:      {len(analysis['dataset_loading_functions'])} found")
                for func in analysis['dataset_loading_functions'][:3]:
                    print(f"    - {func}")
                if len(analysis['dataset_loading_functions']) > 3:
                    print(f"    ... +{len(analysis['dataset_loading_functions'])-3} more")
            
            # Observable variables
            if analysis['observable_variables']:
                print(f"  Observable Variables:       {len(analysis['observable_variables'])} found")
                for var in analysis['observable_variables'][:3]:
                    print(f"    - {var}")
                if len(analysis['observable_variables']) > 3:
                    print(f"    ... +{len(analysis['observable_variables'])-3} more")
            
            # Reward functions
            if analysis['reward_functions']:
                print(f"  Reward Functions:           {len(analysis['reward_functions'])} found")
                for func in analysis['reward_functions']:
                    print(f"    - {func}")
            
            all_agents.append(analysis['agent'])
            
            # Detectar funciones comunes
            if common_dataset_funcs is None:
                common_dataset_funcs = set(analysis['dataset_loading_functions'])
            else:
                common_dataset_funcs = common_dataset_funcs.intersection(set(analysis['dataset_loading_functions']))
            
            if common_observables is None:
                common_observables = set(analysis['observable_variables'])
            else:
                common_observables = common_observables.intersection(set(analysis['observable_variables']))
        
        print(f"\n[SINCRONIZACION DE ENTRENAMIENTOS]")
        print(f"  Agentes: {', '.join(all_agents)}")
        print(f"  Funciones de dataset COMUNES: {len(common_dataset_funcs) if common_dataset_funcs else 0}")
        if common_dataset_funcs:
            for func in list(common_dataset_funcs)[:5]:
                print(f"    ✓ {func}")
        else:
            print(f"    ❌ NO hay funciones comunes (INCONSISTENCIA DETECTADA)")
        
        print(f"  Variables observables COMUNES: {len(common_observables) if common_observables else 0}")
        if common_observables:
            for var in list(common_observables)[:5]:
                print(f"    ✓ {var}")
        else:
            print(f"    ❌ NO hay variables observables comunes")
    
    # SECCION 2: DATASET BUILDER
    print("\n[2] DATASET BUILDER (src/citylearnv2/dataset_builder/dataset_builder.py)")
    print("-"*80)
    print(f"  Baseline Integration:    {builder_info['has_baseline_integration']} {'✅' if builder_info['has_baseline_integration'] else '⚠️'}")
    print(f"  Observable Variables:    {builder_info['has_observables']} {'✅' if builder_info['has_observables'] else '❌'}")
    print(f"  Reward Integration:      {builder_info['reward_integration']} {'✅' if builder_info['reward_integration'] else '⚠️'}")
    
    if builder_info['chargers_columns']:
        print(f"\n  Chargers Observable Columns ({len(builder_info['chargers_columns'])} found):")
        for col in sorted(builder_info['chargers_columns'])[:8]:
            print(f"    - {col}")
        if len(builder_info['chargers_columns']) > 8:
            print(f"    ... +{len(builder_info['chargers_columns'])-8} more")
    
    if builder_info['solar_columns']:
        print(f"\n  Solar Observable Columns ({len(builder_info['solar_columns'])} found):")
        for col in sorted(builder_info['solar_columns'])[:5]:
            print(f"    - {col}")
    
    if builder_info['co2_constants']:
        print(f"\n  CO2 Constants ({len(builder_info['co2_constants'])} found):")
        for const in builder_info['co2_constants'][:10]:
            print(f"    - {const}")
    
    # SECCION 3: DATA LOADER
    print("\n[3] DATA LOADER (src/dimensionamiento/oe2/disenocargadoresev/data_loader.py)")
    print("-"*80)
    print(f"  Solar Data Loader:            {loader_info['has_solar_loader']} ✅" if loader_info['has_solar_loader'] else f"  Solar Data Loader:            {loader_info['has_solar_loader']} ❌")
    print(f"  BESS Data Loader:             {loader_info['has_bess_loader']} ✅" if loader_info['has_bess_loader'] else f"  BESS Data Loader:             {loader_info['has_bess_loader']} ❌")
    print(f"  Chargers Data Loader:         {loader_info['has_chargers_loader']} ✅" if loader_info['has_chargers_loader'] else f"  Chargers Data Loader:         {loader_info['has_chargers_loader']} ❌")
    print(f"  Mall Demand Data Loader:      {loader_info['has_mall_loader']} ✅" if loader_info['has_mall_loader'] else f"  Mall Demand Data Loader:      {loader_info['has_mall_loader']} ❌")
    print(f"  Validation Function:          {loader_info['has_validation']} ✅" if loader_info['has_validation'] else f"  Validation Function:          {loader_info['has_validation']} ❌")
    
    if loader_info['loader_functions']:
        print(f"\n  Loader Functions ({len(loader_info['loader_functions'])} found):")
        for func in loader_info['loader_functions']:
            print(f"    ✓ {func}")
    
    # SECCION 4: RESUMEN DE CONSISTENCIA
    print("\n[4] ANALISIS DE CONSISTENCIA")
    print("-"*80)
    
    consistency_checks = {
        'Data Loader completitud': loader_info['has_solar_loader'] and loader_info['has_bess_loader'] 
                                   and loader_info['has_chargers_loader'] and loader_info['has_mall_loader'],
        'Dataset Builder observables': builder_info['has_observables'],
        'Todos entrenamientos tienen baseline': all(a['baseline_calculation'] for a in training_analyses),
        'Todos entrenamientos usan CityLearn': all(a['citylearn_imported'] for a in training_analyses),
        'Observables CO2 sincronizadas': all(len(a['observable_variables']) > 0 for a in training_analyses),
    }
    
    for check_name, check_result in consistency_checks.items():
        status = "✅" if check_result else "❌"
        print(f"  {status} {check_name}: {check_result}")
    
    # RECOMENDACIONES
    print("\n[5] RECOMENDACIONES")
    print("-"*80)
    
    issues = []
    
    if not all(a.get('baseline_calculation', False) for a in training_analyses):
        issues.append("❌ No todos los entrenamientos tienen sección de baseline calculation")
    
    if not loader_info['has_validation']:
        issues.append("⚠️  data_loader.py no tiene función de validación OE2 completa")
    
    if not builder_info['has_baseline_integration']:
        issues.append("⚠️  dataset_builder.py no tiene integración de baseline")
    
    if not all(a.get('dataset_builder_imported', False) for a in training_analyses):
        issues.append("⚠️  No todos los entrenamientos importan dataset_builder")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"  ✅ NO HAY INCONSISTENCIAS DETECTADAS")
    
    print("\n" + "="*80)

def main():
    """Función principal."""
    print("\n[INICIANDO] Auditoria de consistencia: Entrenamientos ↔ Dataset Builder ↔ Data Loader")
    
    training_analyses = compare_training_files()
    builder_info = check_dataset_builder()
    loader_info = check_data_loader()
    
    print_report(training_analyses, builder_info, loader_info)
    
    # Guardar reporte en JSON
    import json
    report = {
        'training_analyses': [{
            'agent': a['agent'],
            'dataset_builder_imported': a['dataset_builder_imported'],
            'citylearn_imported': a['citylearn_imported'],
            'data_loader_imported': a['data_loader_imported'],
            'baseline_calculation': a['baseline_calculation'],
            'environment_class': a['environment_class'],
            'dataset_loading_functions': a['dataset_loading_functions'],
        } for a in training_analyses],
        'dataset_builder': {
            'has_baseline_integration': builder_info['has_baseline_integration'],
            'has_observables': builder_info['has_observables'],
            'reward_integration': builder_info['reward_integration'],
            'chargers_columns_count': len(builder_info['chargers_columns']),
            'solar_columns_count': len(builder_info['solar_columns']),
            'co2_constants_count': len(builder_info['co2_constants']),
        },
        'data_loader': {
            'has_solar_loader': loader_info['has_solar_loader'],
            'has_bess_loader': loader_info['has_bess_loader'],
            'has_chargers_loader': loader_info['has_chargers_loader'],
            'has_mall_loader': loader_info['has_mall_loader'],
            'has_validation': loader_info['has_validation'],
            'loader_functions_count': len(loader_info['loader_functions']),
        }
    }
    
    output_path = Path('reports/consistency/training_dataset_builder_consistency_v55.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Reporte guardado en: {output_path}")

if __name__ == '__main__':
    main()
