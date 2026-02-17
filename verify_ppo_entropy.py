#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar que PPO guarda valores de entropía en los CSVs.
Script de validación para train_ppo_multiobjetivo.py v7.3

Verifica:
1. Que timeseries_ppo.csv contiene columnas de entropía
2. Que trace_ppo.csv contiene columnas de entropía
3. Que los valores de entropía NO son todos ceros
4. Que la entropía decae apropiadamente durante el entrenamiento
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

def verify_ppo_entropy_in_csvs() -> bool:
    """Verifica que los CSVs de PPO contienen datos de entropía correctos."""
    
    output_dir = Path('outputs/ppo_training')
    
    print('=' * 80)
    print('[VERIFICACION] Valores de entropía en CSVs de PPO')
    print('=' * 80)
    print()
    
    # =====================================================================
    # 1. VERIFICAR result_ppo.json
    # =====================================================================
    result_file = output_dir / 'result_ppo.json'
    if not result_file.exists():
        print(f'❌ ERROR: No encontrado {result_file}')
        return False
    
    with open(result_file, 'r') as f:
        result = json.load(f)
    
    print(f'✓ result_ppo.json encontrado')
    print(f'  Timestamp: {result.get("timestamp", "N/A")}')
    print(f'  Agent: {result.get("agent_type", "N/A")}')
    print(f'  Episodes: {result.get("num_episodes", "N/A")}')
    print()
    
    # =====================================================================
    # 2. VERIFICAR timeseries_ppo.csv
    # =====================================================================
    timeseries_file = output_dir / 'timeseries_ppo.csv'
    if not timeseries_file.exists():
        print(f'❌ ERROR: No encontrado {timeseries_file}')
        return False
    
    print(f'✓ timeseries_ppo.csv encontrado')
    df_timeseries = pd.read_csv(timeseries_file)
    
    # Verificar columnas de entropía
    entropy_cols = ['entropy', 'approx_kl', 'clip_fraction', 'policy_loss', 'value_loss', 'explained_variance']
    missing_cols = [col for col in entropy_cols if col not in df_timeseries.columns]
    
    if missing_cols:
        print(f'  ❌ FALTAN COLUMNAS DE ENTROPÍA: {missing_cols}')
        print(f'  Columnas disponibles: {list(df_timeseries.columns)[:10]}...')
        return False
    
    print(f'  ✓ Todas las columnas de entropía presentes: {entropy_cols}')
    print(f'  Total registros: {len(df_timeseries):,}')
    print()
    
    # Estadísticas de entropía
    print('  ESTADÍSTICAS DE ENTROPÍA:')
    entropy_stats = df_timeseries['entropy'].describe()
    print(f'    Min: {entropy_stats["min"]:.6f}')
    print(f'    Q25: {df_timeseries["entropy"].quantile(0.25):.6f}')
    print(f'    Med: {entropy_stats["50%"]:.6f}')
    print(f'    Q75: {df_timeseries["entropy"].quantile(0.75):.6f}')
    print(f'    Max: {entropy_stats["max"]:.6f}')
    print(f'    Mean: {entropy_stats["mean"]:.6f}')
    print(f'    Std: {entropy_stats["std"]:.6f}')
    
    # Verificar que NO son todos ceros
    non_zero_entropy = (df_timeseries['entropy'] != 0).sum()
    if non_zero_entropy == 0:
        print(f'  ❌ ERROR: TODOS los valores de entropía son CERO (no se está calculando)')
        return False
    else:
        pct_nonzero = (non_zero_entropy / len(df_timeseries)) * 100
        print(f'  ✓ {non_zero_entropy:,} valores de entropía NO-CERO ({pct_nonzero:.1f}%)')
    print()
    
    # Analizar tendencia de entropía
    print('  ANÁLISIS DE DECAIMIENTO DE ENTROPÍA:')
    entropy_by_episode = df_timeseries.groupby('episode')['entropy'].agg(['mean', 'min', 'max', 'std'])
    if len(entropy_by_episode) > 1:
        first_ep_entropy = entropy_by_episode.iloc[0]['mean']
        last_ep_entropy = entropy_by_episode.iloc[-1]['mean']
        decay = ((first_ep_entropy - last_ep_entropy) / first_ep_entropy * 100) if first_ep_entropy != 0 else 0
        
        print(f'    Episodio 0: entropy_mean = {first_ep_entropy:.6f}')
        print(f'    Episodio {len(entropy_by_episode)-1}: entropy_mean = {last_ep_entropy:.6f}')
        print(f'    Decaimiento: {decay:.1f}%')
        
        if decay < 5:
            print(f'    ⚠️  ADVERTENCIA: Entropía casi no decae (< 5%), puede estar congelada')
        elif decay > 99:
            print(f'    ⚠️  ADVERTENCIA: Entropía cae demasiado rápido (> 99%), puede colapsar')
        else:
            print(f'    ✓ Decaimiento normal')
    print()
    
    # =====================================================================
    # 3. VERIFICAR trace_ppo.csv
    # =====================================================================
    trace_file = output_dir / 'trace_ppo.csv'
    if not trace_file.exists():
        print(f'❌ ERROR: No encontrado {trace_file}')
        return False
    
    print(f'✓ trace_ppo.csv encontrado')
    df_trace = pd.read_csv(trace_file)
    
    # Verificar columnas de entropía
    missing_cols_trace = [col for col in entropy_cols if col not in df_trace.columns]
    if missing_cols_trace:
        print(f'  ❌ FALTAN COLUMNAS DE ENTROPÍA: {missing_cols_trace}')
        return False
    
    print(f'  ✓ Todas las columnas de entropía presentes')
    print(f'  Total registros: {len(df_trace):,}')
    print()
    
    # =====================================================================
    # 4. MUESTRA DE DATOS
    # =====================================================================
    print('  MUESTRA DE DATOS (primeras 3 filas de timeseries_ppo.csv):')
    print()
    
    sample_cols = ['timestep', 'episode', 'hour', 'reward', 'entropy', 'approx_kl', 
                   'clip_fraction', 'policy_loss', 'explained_variance']
    sample_data = df_timeseries[sample_cols].head(3)
    
    for idx, row in sample_data.iterrows():
        print(f'    Fila {idx}:')
        print(f'      timestep={int(row["timestep"])}, episode={int(row["episode"])}, hour={int(row["hour"])}')
        print(f'      reward={row["reward"]:.4f}')
        print(f'      entropy={row["entropy"]:.6f}, approx_kl={row["approx_kl"]:.6f}')
        print(f'      clip_fraction={row["clip_fraction"]:.4f}')
        print(f'      policy_loss={row["policy_loss"]:.6f}, explained_variance={row["explained_variance"]:.6f}')
        print()
    
    return True


if __name__ == '__main__':
    success = verify_ppo_entropy_in_csvs()
    
    print('=' * 80)
    if success:
        print('✅ VERIFICACIÓN EXITOSA: Entropía se guarda correctamente en CSVs')
        print('=' * 80)
        sys.exit(0)
    else:
        print('❌ VERIFICACIÓN FALLIDA: Problemas encontrados con los datos de entropía')
        print('=' * 80)
        sys.exit(1)
