#!/usr/bin/env python3
"""Monitor SAC v9.2 en tiempo real - Verifica convergencia cada 30 min"""
import pandas as pd
import numpy as np
import time
from datetime import datetime
from pathlib import Path

def monitor_sac():
    """Monitoreo contínuo de SAC v9.2"""
    
    print("="*80)
    print("MONITOR SAC v9.2 - CONVERGENCE TRACKING")
    print("="*80)
    print(f"Inicio: {datetime.now()}")
    print()
    
    checks_completed = 0
    max_checks = 4  # 4 checks = ~2 horas (30 min cada uno)
    
    while checks_completed < max_checks:
        time.sleep(1800)  # Esperar 30 minutos
        checks_completed += 1
        
        csv_path = Path('outputs/sac_training/trace_sac.csv')
        if not csv_path.exists():
            print(f"[{datetime.now()}] CSV no encontrado aún...")
            continue
        
        try:
            df = pd.read_csv(csv_path)
        except:
            print(f"[{datetime.now()}] Error leyendo CSV, reintentando...")
            continue
        
        print(f"\n{'='*80}")
        print(f"CHECK #{checks_completed}/4 - {datetime.now()}")
        print(f"{'='*80}")
        
        # Estadísticas globales
        total_steps = len(df)
        total_eps = int(df['episode'].max()) + 1
        percent = (total_steps / 131400) * 100
        
        print(f"\n✓ PROGRESO:")
        print(f"  Pasos ejecutados: {total_steps:,} / 131,400 ({percent:.1f}%)")
        print(f"  Episodios completados: {total_eps}")
        print(f"  Tiempo estimado restante: {((131400-total_steps)/1000):.1f} horas")
        
        # Validación de recompensas
        reward_min = df['reward'].min()
        reward_max = df['reward'].max()
        reward_mean = df['reward'].mean()
        
        print(f"\n✓ REWARD SIGNAL (v9.2):")
        print(f"  Mean: {reward_mean:+.8f}")
        print(f"  Min-Max: [{reward_min:+.6f}, {reward_max:+.6f}]")
        
        # Check: ¿En rango esperado?
        if reward_min >= -0.0005 and reward_max <= 0.0005:
            print(f"  Status: ✓ RANGO VALIDO ([-0.0005, 0.0005])")
        else:
            print(f"  Status: ⚠ FUERA DE RANGO (revisar si hay overflow)")
        
        # Análisis por episodio - últimos 3
        print(f"\n✓ ÚLTIMOS 3 EPISODIOS:")
        for ep in sorted(df['episode'].unique())[-3:]:
            ep_data = df[df['episode'] == ep]
            ep_reward = ep_data['reward'].sum()
            ep_steps = len(ep_data)
            ep_grid = ep_data['grid_import_kwh'].mean()
            
            print(f"  Ep {int(ep):2d}: steps={ep_steps:5d}, total_rwd={ep_reward:+.6f}, grid={ep_grid:7.1f}kW")
        
        # Grid import trend - ¿Mejorando?
        if total_eps > 2:
            first_3_eps = df[df['episode'] <= 2]
            last_eps = df[df['episode'] >= max(0, df['episode'].max()-1)]
            
            grid_early = first_3_eps['grid_import_kwh'].mean()
            grid_late = last_eps['grid_import_kwh'].mean()
            grid_improvement = ((grid_early - grid_late) / grid_early) * 100
            
            print(f"\n✓ LEARNING TREND:")
            print(f"  Grid import (early): {grid_early:.1f} kW")
            print(f"  Grid import (late):  {grid_late:.1f} kW")
            print(f"  Improvement: {grid_improvement:+.1f}% {'✓ LEARNING' if grid_improvement > 0 else '⚠ No clear'}")
        
        # Health check
        nan_count = df.isna().sum().sum()
        inf_count = np.isinf(df.select_dtypes([np.number])).sum().sum()
        
        print(f"\n✓ HEALTH CHECK:")
        print(f"  NaN values: {nan_count} (expected: 0)")
        print(f"  Inf values: {inf_count} (expected: 0)")
        
        if nan_count == 0 and inf_count == 0:
            print(f"  Status: ✓ HEALTHY")
        else:
            print(f"  Status: ✗ ANOMALY")
        
        print()
    
    print(f"\n{'='*80}")
    print(f"MONITOREO COMPLETADO - {datetime.now()}")
    print(f"Total checks: {checks_completed}")
    print(f"{'='*80}")

if __name__ == "__main__":
    monitor_sac()
