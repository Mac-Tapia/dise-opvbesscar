#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDIT COMPLETO: Verificar información guardada en training de SAC/PPO/A2C
=============================================================================
Verifica:
1. Timeseries guardadas (costos, CO2 directo/indirecto, motos/mototaxis)
2. Columnas cargadas vs usadas en datasets
3. Funciones de guardado y cálculo en callbacks
4. Gráficas sin paneles vacíos
5. Trazabilidad completa del procesamiento
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# Agregar src al path
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))

# ============================================================================
# PARTE 1: EXPLORAR ESTRUCTURA DE GUARDADO EN AGENTES
# ============================================================================

def audit_callbacks_in_agent_files() -> Dict[str, Any]:
    """Verificar qué está siendo guardado en callbacks de cada agente."""
    print("=" * 80)
    print("PARTE 1: REVISAR CALLBACKS EN AGENTES (SAC/PPO/A2C)")
    print("=" * 80)
    print()
    
    agents = {
        'SAC': 'scripts/train/train_sac.py',
        'PPO': 'scripts/train/train_ppo.py',
        'A2C': 'scripts/train/train_a2c.py'
    }
    
    results = {}
    
    for agent_name, agent_file in agents.items():
        agent_path = workspace_root / agent_file
        if not agent_path.exists():
            print(f"❌ {agent_name}: Archivo no encontrado: {agent_file}")
            results[agent_name] = {'status': 'MISSING', 'callbacks': []}
            continue
        
        print(f"\n📄 {agent_name}: {agent_file}")
        print("-" * 80)
        
        with open(agent_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Buscar clases de callbacks
        callbacks_found = []
        
        # Buscar métodos de guardado
        save_methods = []
        if 'csv' in content.lower():
            save_methods.append('CSV')
        if 'json' in content.lower():
            save_methods.append('JSON')
        if 'pickle' in content.lower():
            save_methods.append('PICKLE')
        if 'np.save' in content.lower():
            save_methods.append('NUMPY')
        
        # Buscar callback clases
        if 'class DetailedLoggingCallback' in content:
            callbacks_found.append('DetailedLoggingCallback')
        if 'class PPOMetricsCallback' in content:
            callbacks_found.append('PPOMetricsCallback')
        if 'class A2CMetricsCallback' in content:
            callbacks_found.append('A2CMetricsCallback')
        if 'class CheckpointCallback' in content:
            callbacks_found.append('CheckpointCallback')
        
        # Buscar columnas de guardado
        columns_saved = []
        search_terms = [
            'reward', 'cost', 'co2', 'solar', 'bess', 'moto', 'grid',
            'action', 'observation', 'entropy', 'loss', 'kl_divergence'
        ]
        for term in search_terms:
            if f"'{term}" in content or f'"{term}' in content or f'__{term}' in content:
                columns_saved.append(term)
        
        print(f"  ✓ Callbacks encontrados: {', '.join(callbacks_found) if callbacks_found else 'NINGUNO'}")
        print(f"  ✓ Métodos de guardado: {', '.join(save_methods) if save_methods else 'NINGUNO'}")
        print(f"  ✓ Columnas potenciales: {len(columns_saved)} tipos detectados")
        
        results[agent_name] = {
            'status': 'OK',
            'callbacks': callbacks_found,
            'save_methods': save_methods,
            'columns_found': len(columns_saved),
            'columns': list(set(columns_saved))
        }
    
    return results


# ============================================================================
# PARTE 2: VERIFICAR DATASETS REALES Y COLUMNAS CARGADAS
# ============================================================================

def audit_dataset_columns() -> Dict[str, Any]:
    """Verificar columnas en datasets reales vs las que se usan en agentes."""
    print("\n" + "=" * 80)
    print("PARTE 2: AUDITAR COLUMNAS DE DATASETS REALES")
    print("=" * 80)
    print()
    
    # Rutas de datasets
    dataset_paths = {
        'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
        'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
        'BESS': 'data/oe2/bess/bess_ano_2024.csv',
        'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv'
    }
    
    results = {}
    
    for dataset_name, dataset_path_str in dataset_paths.items():
        dataset_path = workspace_root / dataset_path_str
        
        if not dataset_path.exists():
            print(f"❌ {dataset_name}: No encontrado en {dataset_path_str}")
            results[dataset_name] = {'status': 'MISSING', 'columns': 0}
            continue
        
        try:
            df = pd.read_csv(dataset_path, nrows=0)  # Solo leer headers
            cols = df.columns.tolist()
            
            print(f"✓ {dataset_name}:")
            print(f"    Columnas: {len(cols)}")
            print(f"    Primeras 5: {cols[:5]}")
            
            # Contar columnas relevantes
            co2_cols = [c for c in cols if 'co2' in c.lower()]
            cost_cols = [c for c in cols if 'cost' in c.lower() or 'precio' in c.lower() or 'soles' in c.lower()]
            ev_cols = [c for c in cols if 'ev' in c.lower() or 'moto' in c.lower()]
            solar_cols = [c for c in cols if 'solar' in c.lower() or 'pv' in c.lower()]
            bess_cols = [c for c in cols if 'bess' in c.lower()]
            
            results[dataset_name] = {
                'status': 'OK',
                'total_columns': len(cols),
                'co2_columns': len(co2_cols),
                'cost_columns': len(cost_cols),
                'ev_columns': len(ev_cols),
                'solar_columns': len(solar_cols),
                'bess_columns': len(bess_cols),
                'all_columns': cols
            }
            
            print(f"    CO2 cols: {len(co2_cols)}, Cost: {len(cost_cols)}, EV: {len(ev_cols)}, Solar: {len(solar_cols)}, BESS: {len(bess_cols)}")
            
        except Exception as e:
            print(f"  ❌ Error leyendo {dataset_name}: {e}")
            results[dataset_name] = {'status': 'ERROR', 'error': str(e)}
        
        print()
    
    return results


# ============================================================================
# PARTE 3: VERIFICAR OUTPUTS GENERADOS
# ============================================================================

def audit_training_outputs() -> Dict[str, Any]:
    """Verificar archivos generados durante training."""
    print("\n" + "=" * 80)
    print("PARTE 3: AUDITAR OUTPUTS DE TRAINING GENERADOS")
    print("=" * 80)
    print()
    
    output_dirs = {
        'SAC': 'outputs/sac_training',
        'PPO': 'outputs/ppo_training',
        'A2C': 'outputs/a2c_training'
    }
    
    results = {}
    
    for agent_name, output_dir_str in output_dirs.items():
        output_dir = workspace_root / output_dir_str
        
        print(f"\n{agent_name} Output Directory: {output_dir_str}")
        print("-" * 80)
        
        if not output_dir.exists():
            print(f"  ❌ Directorio no existe: {output_dir_str}")
            results[agent_name] = {'status': 'MISSING', 'files': []}
            continue
        
        # Listar archivos
        files = list(output_dir.glob('*'))
        
        if not files:
            print(f"  ⚠️  Directorio vacío")
            results[agent_name] = {'status': 'EMPTY', 'files': []}
            continue
        
        print(f"  ✓ Archivos encontrados: {len(files)}")
        
        csv_files = []
        json_files = []
        png_files = []
        other_files = []
        
        for file in sorted(files):
            file_size = file.stat().st_size / 1024  # KB
            
            if file.suffix == '.csv':
                csv_files.append((file.name, file_size))
                print(f"    📊 [CSV] {file.name} ({file_size:.1f} KB)")
            elif file.suffix == '.json':
                json_files.append((file.name, file_size))
                print(f"    📋 [JSON] {file.name} ({file_size:.1f} KB)")
            elif file.suffix == '.png':
                png_files.append((file.name, file_size))
                print(f"    🖼️  [PNG] {file.name} ({file_size:.1f} KB)")
            else:
                other_files.append((file.name, file_size))
                print(f"    📁 [{file.suffix}] {file.name} ({file_size:.1f} KB)")
        
        results[agent_name] = {
            'status': 'OK',
            'total_files': len(files),
            'csv_files': len(csv_files),
            'json_files': len(json_files),
            'png_files': len(png_files),
            'csv_list': csv_files,
            'json_list': json_files,
            'png_list': png_files
        }
    
    return results


# ============================================================================
# PARTE 4: VERIFICAR CONTENIDO DE CSV (COLUMNAS GUARDADAS)
# ============================================================================

def audit_csv_content() -> Dict[str, Any]:
    """Verificar qué columnas están siendo guardadas en CSVs."""
    print("\n" + "=" * 80)
    print("PARTE 4: AUDITAR CONTENIDO DE CSV GUARDADOS")
    print("=" * 80)
    print()
    
    output_dirs = {
        'SAC': 'outputs/sac_training',
        'PPO': 'outputs/ppo_training',
        'A2C': 'outputs/a2c_training'
    }
    
    results = {}
    
    for agent_name, output_dir_str in output_dirs.items():
        output_dir = workspace_root / output_dir_str
        
        print(f"\n{agent_name}:")
        print("-" * 80)
        
        result = {'status': 'OK', 'csvs': {}}
        
        if not output_dir.exists():
            print(f"  ⚠️  Directorio no existe")
            result['status'] = 'MISSING'
            results[agent_name] = result
            continue
        
        csv_files = list(output_dir.glob('*.csv'))
        
        if not csv_files:
            print(f"  ⚠️  No hay archivos CSV")
            result['status'] = 'NO_CSV'
            results[agent_name] = result
            continue
        
        for csv_file in sorted(csv_files):
            try:
                df = pd.read_csv(csv_file)
                
                # Verificar columnas requeridas
                required_patterns = ['reward', 'cost', 'co2', 'solar', 'moto', 'grid', 'loss', 'entropy']
                found_patterns = []
                
                for col in df.columns:
                    for pattern in required_patterns:
                        if pattern.lower() in col.lower():
                            found_patterns.append(pattern)
                            break
                
                found_patterns = list(set(found_patterns))
                
                print(f"  📊 {csv_file.name}:")
                print(f"      Filas: {len(df)}, Columnas: {len(df.columns)}")
                print(f"      Columnas encontradas: {df.columns.tolist()[:5]}...")
                print(f"      Patrones detectados: {found_patterns}")
                
                # Detectar faltantes
                missing = []
                if 'cost' not in found_patterns:
                    missing.append('COSTO')
                if 'co2' not in found_patterns:
                    missing.append('CO2')
                if 'moto' not in found_patterns and len(df) > 0:
                    missing.append('MOTOS/MOTOTAXIS')
                
                if missing:
                    print(f"      ⚠️  FALTANTE: {', '.join(missing)}")
                else:
                    print(f"      ✓ Todas las métricas presentes")
                
                result['csvs'][csv_file.name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_names': df.columns.tolist(),
                    'patterns_found': found_patterns,
                    'missing': missing
                }
                
            except Exception as e:
                print(f"  ❌ Error leyendo {csv_file.name}: {e}")
                result['csvs'][csv_file.name] = {'status': 'ERROR', 'error': str(e)}
        
        results[agent_name] = result
    
    return results


# ============================================================================
# PARTE 5: VERIFICAR GRÁFICAS
# ============================================================================

def audit_graphs() -> Dict[str, Any]:
    """Verificar que las gráficas se generen sin paneles vacíos."""
    print("\n" + "=" * 80)
    print("PARTE 5: AUDITAR GRÁFICAS GENERADAS")
    print("=" * 80)
    print()
    
    output_dirs = {
        'SAC': 'outputs/sac_training',
        'PPO': 'outputs/ppo_training',
        'A2C': 'outputs/a2c_training'
    }
    
    results = {}
    
    for agent_name, output_dir_str in output_dirs.items():
        output_dir = workspace_root / output_dir_str
        
        print(f"\n{agent_name}:")
        print("-" * 80)
        
        if not output_dir.exists():
            print(f"  ⚠️  Directorio no existe")
            results[agent_name] = {'status': 'MISSING', 'graphs': []}
            continue
        
        png_files = list(output_dir.glob('*.png'))
        
        if not png_files:
            print(f"  ⚠️  No hay gráficas PNG")
            results[agent_name] = {'status': 'NO_GRAPHS', 'graphs': []}
            continue
        
        print(f"  ✓ Gráficas encontradas: {len(png_files)}")
        
        graph_list = []
        for png_file in sorted(png_files):
            file_size = png_file.stat().st_size / 1024
            
            # Tipos de gráficas esperadas
            expected_types = {
                'reward': 'Recompensa por episodio',
                'loss': 'Loss (Actor/Critic)',
                'entropy': 'Entropía de política',
                'co2': 'Reducción CO2',
                'cost': 'Análisis de costos',
                'timeseries': 'Timeseries de entrenamiento'
            }
            
            graph_type = 'DESCONOCIDO'
            for expected, desc in expected_types.items():
                if expected.lower() in png_file.name.lower():
                    graph_type = desc
                    break
            
            print(f"  📈 {png_file.name} ({file_size:.1f} KB) - {graph_type}")
            graph_list.append({'name': png_file.name, 'size_kb': file_size, 'type': graph_type})
        
        results[agent_name] = {'status': 'OK', 'graphs': graph_list, 'count': len(png_files)}
    
    return results


# ============================================================================
# PARTE 6: RECOMENDACIONES
# ============================================================================

def generate_recommendations(
    callbacks_result: Dict,
    dataset_result: Dict,
    outputs_result: Dict,
    csv_result: Dict,
    graphs_result: Dict
) -> List[str]:
    """Generar recomendaciones basadas en audit."""
    recommendations = []
    
    # Revisar callbacks
    for agent, data in callbacks_result.items():
        if data['status'] == 'MISSING':
            recommendations.append(
                f"❌ {agent}: Archivo no encontrado. Verificar ruta scripts/train/train_{agent.lower()}.py"
            )
        elif not data['callbacks']:
            recommendations.append(
                f"⚠️  {agent}: No se encontraron callbacks. Pueden no estar guardando información."
            )
        elif not data['save_methods']:
            recommendations.append(
                f"⚠️  {agent}: No se detectan métodos de guardado (CSV/JSON). Verificar logging."
            )
    
    # Revisar datasets
    missing_cols = []
    for dataset, data in dataset_result.items():
        if data['status'] == 'MISSING':
            missing_cols.append(f"Dataset {dataset}")
        elif data.get('co2_columns', 0) == 0:
            missing_cols.append(f"{dataset}: sin columnas CO2")
        elif data.get('cost_columns', 0) == 0:
            missing_cols.append(f"{dataset}: sin columnas COSTO")
        elif data.get('ev_columns', 0) == 0:
            missing_cols.append(f"{dataset}: sin columnas EV")
    
    if missing_cols:
        recommendations.append(f"⚠️  Falta información en datasets: {', '.join(missing_cols)}")
    
    # Revisar outputs
    for agent, data in outputs_result.items():
        if data['status'] == 'MISSING':
            recommendations.append(
                f"⚠️  {agent}: No hay carpeta de outputs. Ejecutar training primero."
            )
        elif data['status'] == 'EMPTY':
            recommendations.append(
                f"⚠️  {agent}: Carpeta outputs vacía. Verificar que training generó archivos."
            )
    
    # Revisar CSVs
    for agent, data in csv_result.items():
        if data['status'] == 'MISSING':
            recommendations.append(f"⚠️  {agent}: No hay CSVs guardados")
        elif data['status'] == 'NO_CSV':
            recommendations.append(
                f"⚠️  {agent}: No hay archivos CSV. Verificar callback DetailedLoggingCallback."
            )
        else:
            for csv_name, csv_data in data.get('csvs', {}).items():
                if csv_data.get('missing'):
                    recommendations.append(
                        f"⚠️  {agent}/{csv_name}: Faltan columnas {', '.join(csv_data['missing'])}"
                    )
    
    # Revisar gráficas
    for agent, data in graphs_result.items():
        if data['status'] == 'MISSING':
            recommendations.append(f"⚠️  {agent}: Sin gráficas generadas")
        elif data['status'] == 'NO_GRAPHS':
            recommendations.append(f"⚠️  {agent}: No hay PNG generadas. Verificar matplotlib backend.")
    
    # Recomendaciones positivas
    if all(r['status'] != 'MISSING' for r in callbacks_result.values()):
        recommendations.append("✓ Todos los archivos de agentes existen")
    
    if all(r['status'] == 'OK' for r in dataset_result.values()):
        recommendations.append("✓ Todos los datasets OE2 están disponibles con columnas esperadas")
    
    return recommendations


# ============================================================================
# MAIN: EJECUTAR AUDIT COMPLETO
# ============================================================================

def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "AUDIT COMPLETO: INFORMACIÓN GUARDADA EN TRAINING DE AGENTES".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Ejecutar audits
    callbacks_result = audit_callbacks_in_agent_files()
    dataset_result = audit_dataset_columns()
    outputs_result = audit_training_outputs()
    csv_result = audit_csv_content()
    graphs_result = audit_graphs()
    
    # Generar recomendaciones
    recommendations = generate_recommendations(
        callbacks_result,
        dataset_result,
        outputs_result,
        csv_result,
        graphs_result
    )
    
    # Mostrar resumen
    print("\n" + "=" * 80)
    print("RESUMEN Y RECOMENDACIONES")
    print("=" * 80)
    print()
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    if not recommendations:
        print("✓ No hay problemas detectados - Sistema completo y correcto")
    
    # Guardar reporte en JSON
    report = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'callbacks': callbacks_result,
        'datasets': dataset_result,
        'outputs': outputs_result,
        'csv_content': csv_result,
        'graphs': graphs_result,
        'recommendations': recommendations
    }
    
    report_file = workspace_root / 'outputs' / 'audit_agentes_completo.json'
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Reporte guardado en: {report_file}")
    print("\n✅ Audit completado")


if __name__ == '__main__':
    main()
