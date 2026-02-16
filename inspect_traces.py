import pandas as pd
import os

traces = {
    'SAC': 'outputs/sac_training/trace_sac.csv',
    'PPO': 'outputs/ppo_training/trace_ppo.csv',  
    'A2C': 'outputs/a2c_training/trace_a2c.csv',
}

for agent, path in traces.items():
    print(f"\n{agent}:")
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            print(f"  Filas: {len(df)}")
            print(f"  Columnas: {list(df.columns)}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print(f"  ARCHIVO NO EXISTE")
