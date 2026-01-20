#!/usr/bin/env python3
"""
Analizar si SAC esta aprendiendo o no.
Verificar evolucion de rewards, losses, y checkpoints.
"""

import sys
import json
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path.cwd()))

def analyze_sac_learning():
    """Analizar progreso de aprendizaje de SAC."""
    
    print("\n" + "="*80)
    print("ANALISIS: Verificar si SAC esta aprendiendo")
    print("="*80 + "\n")
    
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")
    
    # 1. Listar checkpoints
    if checkpoint_dir.exists():
        checkpoints = sorted(checkpoint_dir.glob("sac_step_*.zip"))
        print(f"[1] Checkpoints encontrados: {len(checkpoints)}")
        if checkpoints:
            latest = checkpoints[-1]
            print(f"    Ultimo checkpoint: {latest.name}")
            print(f"    Tamanio: {latest.stat().st_size / 1e6:.1f} MB")
            print()
    else:
        print("[!] No checkpoints directory found\n")
    
    # 2. Verificar archivo de progreso
    progress_csv = checkpoint_dir.parent / "sac_progress.csv"
    if progress_csv.exists():
        print(f"[2] Leyendo progreso: {progress_csv}")
        try:
            df = pd.read_csv(progress_csv)
            print(f"    Filas: {len(df)}")
            
            if len(df) > 0:
                print("\n    Primeras 5 filas:")
                print(df.head(5).to_string())
                
                print("\n    Ultimas 5 filas:")
                print(df.tail(5).to_string())
                
                # Analizar tendencias
                if "reward" in df.columns or "reward_avg" in df.columns:
                    reward_col = "reward_avg" if "reward_avg" in df.columns else "reward"
                    first_reward = df[reward_col].iloc[0]
                    last_reward = df[reward_col].iloc[-1]
                    max_reward = df[reward_col].max()
                    min_reward = df[reward_col].min()
                    
                    print(f"\n    Analisis de Rewards:")
                    print(f"      Primer reward: {first_reward:.4f}")
                    print(f"      Ultimo reward: {last_reward:.4f}")
                    print(f"      Maximo: {max_reward:.4f}")
                    print(f"      Minimo: {min_reward:.4f}")
                    print(f"      Cambio: {last_reward - first_reward:.4f}")
                    
                    if abs(last_reward - first_reward) < 0.01:
                        print("\n    [WARNING] Rewards NO cambiaron - Agente NO esta aprendiendo!")
                    else:
                        print(f"\n    [OK] Rewards cambiaron - Agente esta aprendiendo")
                        
        except Exception as e:
            print(f"    Error leyendo CSV: {e}\n")
    else:
        print(f"[!] Progress CSV no encontrado: {progress_csv}\n")
    
    # 3. Verificar resultado final
    results_json = Path("outputs/oe3/simulations/sac_results.json")
    if results_json.exists():
        print(f"[3] Resultado final SAC:")
        try:
            with open(results_json) as f:
                result = json.load(f)
            print(f"    CO2: {result.get('carbon_kg', 'N/A')} kg")
            print(f"    Reward mean: {result.get('reward_total_mean', 'N/A')}")
            print(f"    Episodes: {result.get('simulated_years', 'N/A')} anos")
        except Exception as e:
            print(f"    Error: {e}")
        print()
    
    print("="*80)
    print("\nRECOMENDACIONES:")
    print("-"*80)
    print("""
Si SAC NO esta aprendiendo (rewards constantes), posibles soluciones:

1. LEARNING RATE MUY BAJO
   - Aumentar de 3e-05 a 3e-04 o 1e-03
   - Comando: editar configs/default.yaml, oe3.evaluation.sac.learning_rate

2. BATCH SIZE INCOMPATIBLE
   - Reducir de 65536 a 32768 o 16384
   - Batch muy grande puede causar gradient collapse

3. EXPLORATION INSUFICIENTE
   - Entropy coefficient (ent_coef) debe permitir exploracion
   - Verificar que empiece bajo (0.1) y aumente gradualmente

4. RECOMPENSA PLANA
   - Verificar que la funcion de recompensa multiobjetivo este activa
   - Los agentes necesitan seniales variadas de aprendizaje

5. REINICIAR CON NUEVOS PARAMETROS
   - Si han pasado muchas iteraciones sin mejora
   - Limpiar checkpoints y entrenar desde cero con params ajustados

COMANDO PARA RELANZAR CON BATCH SIZE MAS PEQUENO:
  
  python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-uncontrolled
""")
    print("="*80 + "\n")

if __name__ == "__main__":
    analyze_sac_learning()
